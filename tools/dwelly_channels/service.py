"""Durable inbound inbox; configured source claims never grant authority.

Receipts and source envelopes are local retained evidence. Accepted promotion
uses the existing canonical transaction and outbox, without model/provider I/O.
"""
from copy import deepcopy
import hashlib
import json
import re
import uuid

from tools.dwelly_service.cases import CaseError, _canonical, _identifier
from .contracts import (ERROR_CODES, NORMALIZER_VERSION, load_config, normalize,
                        validate_envelope_identity)


MAX_RECEIPTS = 1024
MAX_RETAINED_BYTES = 128 * 1024 * 1024
_SOURCES = frozenset({'operator_import', 'signed_webhook'})
_SERVICE_ERRORS = frozenset({'unknown_connector', 'invalid_envelope', 'delivery_conflict',
                            'inbox_capacity', 'receipt_not_found', 'receipt_not_quarantined'})
_CONTENT_ERRORS = ERROR_CODES - {'invalid_channel_config'}
_PROMOTION_ERRORS = frozenset({'case_not_found', 'case_capacity', 'invalid_case_request',
    'event_conflict', 'idempotency_conflict', 'invalid_asset', 'asset_too_large',
    'asset_capacity', 'asset_mismatch'})
_PUBLIC_PROVENANCE = frozenset({'normalizer_version', 'format', 'identity_verification',
    'event_count', 'attachment_count', 'transcript_verification', 'qualification',
    'raw_sha256', 'ignored_html_alternatives'})


class _Quarantine(ValueError):
    """An expected binding failure with a fixed public reason."""


class ChannelError(CaseError):
    """Bounded ingress errors preserved by the shared transaction boundary."""
    def __init__(self, code):
        self.code = code if type(code) is str and code in _SERVICE_ERRORS else 'case_storage_error'
        ValueError.__init__(self, self.code)


def migrate_channels(store):
    """Add the local inbox under the same canonical schema write lock."""
    with store._transaction(write=True) as connection:
        connection.execute('''CREATE TABLE IF NOT EXISTS channel_inbox (
            sequence BIGSERIAL PRIMARY KEY,
            receipt_id TEXT UNIQUE NOT NULL,
            connector_id TEXT NOT NULL,
            delivery_id TEXT NOT NULL,
            raw_sha256 TEXT NOT NULL CHECK (raw_sha256 ~ '^[a-f0-9]{64}$'),
            raw_bytes INTEGER NOT NULL CHECK (raw_bytes > 0),
            raw_envelope TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('accepted', 'quarantined')),
            case_id TEXT,
            received_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
            record TEXT NOT NULL,
            UNIQUE (connector_id, delivery_id)
        )''')


def _public_provenance(normalized, envelope):
    source = normalized['provenance'] if normalized is not None else {}
    value = {key: deepcopy(item) for key, item in source.items() if key in _PUBLIC_PROVENANCE}
    value.update(normalizer_version=NORMALIZER_VERSION,
                 envelope_hash_basis='canonical_json', identity_verification='not_verified')
    if type(envelope.get('format')) is str and envelope['format'] in {'message', 'transcript', 'media', 'email'}:
        value['format'] = envelope['format']
    return value


class ChannelService:
    def __init__(self, store, config):
        self.store = store
        self.config = load_config(config)
        self.connectors = {connector['id']: connector for connector in self.config['connectors']}

    def capabilities(self):
        return [{'id': item['id'], 'channel': item['channel'], 'configured': True,
                 'route_count': len(item['routes']), 'contact_count': len(item['contacts']),
                 'provider_connected': False} for item in self.config['connectors']]

    def list(self):
        with self.store._transaction() as connection:
            return [json.loads(row['record']) for row in connection.execute(
                'SELECT record FROM channel_inbox ORDER BY sequence DESC').fetchall()]

    def provenance(self, case_id):
        _identifier(case_id)
        with self.store._transaction() as connection:
            return [json.loads(row['record']) for row in connection.execute(
                "SELECT record FROM channel_inbox WHERE case_id=? AND status='accepted' ORDER BY sequence",
                (case_id,)).fetchall()]

    def _connector(self, connector_id):
        if type(connector_id) is not str or connector_id not in self.connectors:
            raise ChannelError('unknown_connector')
        return self.connectors[connector_id]

    @staticmethod
    def _normalized(envelope, channel):
        try:
            return normalize(envelope, channel), None
        except ValueError as error:
            if error.args and error.args[0] in _CONTENT_ERRORS:
                return None, error.args[0]
            raise  # Implementation/infrastructure failures are not source quarantine.

    @staticmethod
    def _same_delivery(row, digest):
        if row['raw_sha256'] != digest:
            raise ChannelError('delivery_conflict')
        return json.loads(row['record'])

    def ingest(self, connector_id, envelope, source='operator_import'):
        connector = self._connector(connector_id)
        if source not in _SOURCES:
            raise ChannelError('invalid_envelope')
        identity = validate_envelope_identity(envelope)
        raw = _canonical(envelope)
        digest = hashlib.sha256(raw.encode('utf-8')).hexdigest()
        # Exact redelivery remains a read even if configuration or parsers change.
        with self.store._transaction() as connection:
            row = connection.execute('SELECT raw_sha256,record FROM channel_inbox WHERE connector_id=? AND delivery_id=?',
                                     (connector_id, identity['delivery_id'])).fetchone()
            if row is not None:
                return self._same_delivery(row, digest)
        normalized, reason = self._normalized(envelope, connector['channel'])
        with self.store._transaction(write=True) as connection:
            # Recheck after taking the write lock: concurrent redeliveries share
            # the one receipt and can never append twice.
            row = connection.execute('SELECT raw_sha256,record FROM channel_inbox WHERE connector_id=? AND delivery_id=?',
                                     (connector_id, identity['delivery_id'])).fetchone()
            if row is not None:
                return self._same_delivery(row, digest)
            capacity = connection.execute('SELECT count(*) AS count,COALESCE(sum(raw_bytes),0) AS bytes FROM channel_inbox').fetchone()
            raw_bytes = len(raw.encode('utf-8'))
            if capacity['count'] >= MAX_RECEIPTS or capacity['bytes'] + raw_bytes > MAX_RETAINED_BYTES:
                raise ChannelError('inbox_capacity')
            received_at = connection.execute('SELECT clock_timestamp()').fetchone()[0].isoformat()
            receipt = {'receipt_id': uuid.uuid4().hex, 'connector_id': connector_id,
                       'delivery_id': identity['delivery_id'], 'channel': connector['channel'],
                       'status': 'quarantined', 'reason': reason, 'case_id': None,
                       'event_ids': [], 'revision': None, 'raw_sha256': digest,
                       'received_at': received_at, 'source': source,
                       'provenance': _public_provenance(normalized, envelope)}
            connection.execute('''INSERT INTO channel_inbox
                (receipt_id,connector_id,delivery_id,raw_sha256,raw_bytes,raw_envelope,status,case_id,record)
                VALUES (?,?,?,?,?,?,?,?,?)''', (receipt['receipt_id'], connector_id, identity['delivery_id'],
                    digest, raw_bytes, raw, 'quarantined', None, _canonical(receipt)))
            if reason is None:
                self._attempt(connection, connector, envelope, normalized, receipt)
            self._save(connection, receipt)
            return receipt

    def retry(self, receipt_id):
        if type(receipt_id) is not str or re.fullmatch(r'[a-f0-9]{32}', receipt_id) is None:
            raise ChannelError('receipt_not_found')
        with self.store._transaction(write=True) as connection:
            row = connection.execute('SELECT * FROM channel_inbox WHERE receipt_id=?', (receipt_id,)).fetchone()
            if row is None:
                raise ChannelError('receipt_not_found')
            receipt = json.loads(row['record'])
            if receipt['status'] != 'quarantined':
                raise ChannelError('receipt_not_quarantined')
            # Configuration can correct routing/contact bindings, but cannot
            # retrospectively relabel the transport of an already held source.
            connector = {**self._connector(receipt['connector_id']), 'channel': receipt['channel']}
            # Retry has no caller-supplied replacement envelope. Verify the
            # retained source identity before interpreting it again.
            raw = row['raw_envelope']
            if hashlib.sha256(raw.encode('utf-8')).hexdigest() != row['raw_sha256']:
                raise RuntimeError('channel_retained_source_mismatch')
            envelope = json.loads(raw)
            validate_envelope_identity(envelope)
            normalized, reason = self._normalized(envelope, connector['channel'])
            receipt.update(status='quarantined', reason=reason, case_id=None, event_ids=[], revision=None,
                           provenance=_public_provenance(normalized, envelope))
            if reason is None:
                self._attempt(connection, connector, envelope, normalized, receipt)
            self._save(connection, receipt)
            return receipt

    @staticmethod
    def _save(connection, receipt):
        connection.execute('UPDATE channel_inbox SET status=?,case_id=?,record=? WHERE receipt_id=?',
                           (receipt['status'], receipt['case_id'], _canonical(receipt), receipt['receipt_id']))

    def _attempt(self, connection, connector, envelope, normalized, receipt):
        # A known content failure keeps its inbox receipt but cannot retain an
        # earlier attachment, event, snapshot or outbox write from this batch.
        connection.execute('SAVEPOINT inbound_promotion')
        try:
            self._promote(connection, connector, envelope, normalized, receipt)
        except _Quarantine as error:
            connection.execute('ROLLBACK TO SAVEPOINT inbound_promotion')
            receipt.update(status='quarantined', reason=error.args[0], event_ids=[], revision=None)
        except CaseError as error:
            if error.code not in _PROMOTION_ERRORS:
                raise
            connection.execute('ROLLBACK TO SAVEPOINT inbound_promotion')
            receipt.update(status='quarantined', reason=error.code, event_ids=[], revision=None)
        # On an unexpected error leave rollback to the outer transaction. In
        # particular, don't mask an aborted SQL transaction with RELEASE.
        connection.execute('RELEASE SAVEPOINT inbound_promotion')

    def _promote(self, connection, connector, envelope, normalized, receipt):
        case_id = connector['routes'].get(envelope['conversation_id'])
        if case_id is None:
            raise _Quarantine('unknown_route')
        receipt['case_id'] = case_id
        snapshot = self.store._history(connection, case_id)[-1]
        events = []
        for index, draft in enumerate(normalized['events']):
            external = [draft['sender'], *draft['recipients']]
            if any(contact not in connector['contacts'] for contact in external):
                raise _Quarantine('unknown_contact')
            actors = [connector['contacts'][contact] for contact in external]
            if any(actor not in snapshot['participants'] for actor in actors):
                raise _Quarantine('participant_mismatch')
            identity = hashlib.sha256(_canonical([connector['id'], envelope['delivery_id'], index]).encode()).hexdigest()
            event = {'event_id': 'in-' + identity[:60], 'occurred_at': draft['occurred_at'],
                     'channel': connector['channel'], 'sender_id': actors[0],
                     'recipient_ids': list(dict.fromkeys(actors[1:])), 'kind': draft['kind'],
                     'text': draft['text'], 'media': None}
            events.append((event, draft['asset'], identity))
        for event, asset, identity in events:
            if asset is not None:
                event['media'] = self.store._put_asset(connection, case_id, 'inbound-asset:' + identity,
                    asset['mime_type'], asset['filename'], asset['data'])
            snapshot, _created = self.store._append(connection, case_id, 'inbound-event:' + identity,
                {'expected_revision': snapshot['revision'], 'event': event})
        receipt.update(status='accepted', reason=None, event_ids=[event['event_id'] for event, _, _ in events],
                       revision=snapshot['revision'])
