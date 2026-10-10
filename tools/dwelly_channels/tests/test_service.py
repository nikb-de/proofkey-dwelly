"""Real PostgreSQL ingestion, replay, quarantine and rollback boundaries."""
import base64
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from email.message import EmailMessage
import importlib
import io
import json
import os
import uuid

import psycopg
from psycopg import sql
import pytest

from tools.dwelly_platform.store import PlatformStore, migrate
from tools.dwelly_service.cases import CaseError


def service_module():
    return importlib.import_module('tools.dwelly_channels.service')


def config(channel='chat'):
    return {'schema_version': 'proofkey-channel-config-v1', 'connectors': [{
        'id': 'inbox', 'channel': channel, 'secret_env': 'CHANNEL_TEST_SECRET',
        'routes': {'conversation-private': 'case-one'},
        'contacts': {'client@example.test': 'customer', 'desk@example.test': 'operator'}}]}


def envelope(delivery='delivery-one', **payload):
    return {'schema_version': 'proofkey-inbound-v1', 'delivery_id': delivery,
            'conversation_id': 'conversation-private', 'format': 'message', 'payload': {
                'sender': 'client@example.test', 'recipients': ['desk@example.test'],
                'occurred_at': '2026-10-10T10:00:00Z', 'text': 'Original incoming text.', **payload}}


@pytest.fixture
def store():
    dsn = os.environ.get('PROOFKEY_TEST_DATABASE_URL')
    if not dsn:
        pytest.skip('requires isolated PostgreSQL')
    schema = 'channel_test_' + uuid.uuid4().hex
    active = None
    try:
        migrate(dsn, schema=schema)
        active = PlatformStore(dsn, schema=schema)
        service_module().migrate_channels(active)
        active.create('create', {'case_id': 'case-one', 'links': {
            'order_id': 'order-one', 'customer_id': 'customer', 'operator_id': 'operator'},
            'participants': ['customer', 'operator'], 'language': 'en'})
        yield active
    finally:
        if active:
            active.close()
        with psycopg.connect(dsn, autocommit=True) as connection:
            connection.execute(sql.SQL('DROP SCHEMA IF EXISTS {} CASCADE').format(sql.Identifier(schema)))
            assert not connection.execute('SELECT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name=%s)', (schema,)).fetchone()[0]


def service(store, settings=None):
    return service_module().ChannelService(store, settings or config())


def test_ingest_preserves_source_direction_and_only_creates_evidence(store):
    inbox = service(store)
    receipt = inbox.ingest('inbox', envelope())
    assert set(receipt) == {'receipt_id', 'connector_id', 'delivery_id', 'channel', 'status',
        'reason', 'case_id', 'event_ids', 'revision', 'raw_sha256', 'received_at', 'source', 'provenance'}
    assert receipt['status'] == 'accepted' and receipt['reason'] is None
    assert receipt['source'] == 'operator_import' and receipt['case_id'] == 'case-one'
    assert receipt['revision'] == 1 and len(receipt['event_ids']) == 1
    assert len(receipt['event_ids'][0]) <= 64 and len(receipt['raw_sha256']) == 64
    detail = store.detail('case-one')
    event = detail['snapshot']['events'][0]
    assert event['event_id'] == receipt['event_ids'][0]
    assert event['text'] == 'Original incoming text.'
    assert event['sender_id'] == 'customer' and event['recipient_ids'] == ['operator']
    assert event['channel'] == 'chat' and event['occurred_at'] == '2026-10-10T10:00:00+00:00'
    assert detail['actions'] == detail['decisions'] == detail['reviews'] == []
    assert detail['model_jobs'] == [] and detail['external_effects'] == 0
    assert len(store.analysis_jobs('case-one')) == 2  # create + one append
    assert inbox.provenance('case-one') == [receipt]


def test_exact_redelivery_returns_same_receipt_without_duplicate_events(store):
    inbox = service(store)
    first = inbox.ingest('inbox', envelope())
    assert inbox.ingest('inbox', deepcopy(envelope()), source='signed_webhook') == first
    assert inbox.list() == [first]
    assert store.get('case-one')['revision'] == 1
    assert len(store.analysis_jobs('case-one')) == 2


def test_delivery_identity_with_different_content_conflicts(store):
    inbox = service(store)
    first = inbox.ingest('inbox', envelope())
    with pytest.raises(ValueError, match='^delivery_conflict$'):
        inbox.ingest('inbox', envelope(text='Changed content.'))
    assert inbox.list() == [first]
    assert store.get('case-one')['revision'] == 1


@pytest.mark.parametrize('mutate,reason', [
    (lambda e: e.update(conversation_id='unknown-route'), 'unknown_route'),
    (lambda e: e['payload'].update(sender='unknown@example.test'), 'unknown_contact'),
    (lambda e: e['payload'].update(recipients=['unknown@example.test']), 'unknown_contact'),
])
def test_unknown_routing_or_either_direction_is_quarantined(store, mutate, reason):
    incoming = envelope()
    mutate(incoming)
    receipt = service(store).ingest('inbox', incoming)
    assert receipt['status'] == 'quarantined' and receipt['reason'] == reason
    assert receipt['event_ids'] == [] and receipt['revision'] is None
    assert store.get('case-one')['revision'] == 0


def test_bound_contact_must_be_declared_in_case(store):
    settings = config()
    settings['connectors'][0]['contacts']['client@example.test'] = 'stranger'
    receipt = service(store, settings).ingest('inbox', envelope())
    assert receipt['status'] == 'quarantined' and receipt['reason'] == 'participant_mismatch'
    assert store.get('case-one')['revision'] == 0


def test_missing_configured_case_is_quarantined(store):
    settings = config()
    settings['connectors'][0]['routes']['conversation-private'] = 'missing-case'
    receipt = service(store, settings).ingest('inbox', envelope())
    assert receipt['status'] == 'quarantined' and receipt['reason'] == 'case_not_found'


def test_unknown_connector_or_bad_identity_never_creates_receipt(store):
    inbox = service(store)
    with pytest.raises(ValueError, match='^unknown_connector$'):
        inbox.ingest('missing', envelope())
    incoming = envelope()
    incoming['delivery_id'] = ''
    with pytest.raises(ValueError):
        inbox.ingest('inbox', incoming)
    assert inbox.list() == []


def test_known_invalid_content_is_retained_as_bounded_quarantine_reason(store):
    receipt = service(store).ingest('inbox', envelope(text='x' * 4097))
    assert receipt['status'] == 'quarantined'
    assert receipt['reason'] == 'invalid_message'
    assert receipt['event_ids'] == [] and store.get('case-one')['revision'] == 0


def test_retry_uses_frozen_envelope_after_trusted_config_is_corrected(store):
    settings = config()
    settings['connectors'][0]['routes'] = {}
    receipt = service(store, settings).ingest('inbox', envelope())
    assert receipt['reason'] == 'unknown_route'
    inbox = service(store)
    accepted = inbox.retry(receipt['receipt_id'])
    assert accepted['status'] == 'accepted'
    assert accepted['receipt_id'] == receipt['receipt_id']
    assert accepted['raw_sha256'] == receipt['raw_sha256']
    assert accepted['received_at'] == receipt['received_at']
    assert store.get('case-one')['events'][0]['text'] == 'Original incoming text.'
    with pytest.raises(ValueError, match='^receipt_not_quarantined$'):
        inbox.retry(receipt['receipt_id'])
    with pytest.raises(ValueError, match='^receipt_not_found$'):
        inbox.retry('a' * 32)


def test_missing_receipt_retains_public_not_found_code(store):
    with pytest.raises(ValueError, match='^receipt_not_found$'):
        service(store).retry('b' * 32)


def test_quarantine_is_immutable_on_redelivery_until_explicit_retry(store):
    settings = config()
    settings['connectors'][0]['routes'] = {}
    original = service(store, settings).ingest('inbox', envelope())
    restored = service(store)
    assert restored.ingest('inbox', envelope()) == original
    assert store.get('case-one')['revision'] == 0
    assert restored.retry(original['receipt_id'])['status'] == 'accepted'


def test_retry_preserves_original_channel_when_connector_is_reconfigured(store):
    settings = config()
    settings['connectors'][0]['routes'] = {}
    original = service(store, settings).ingest('inbox', envelope())
    accepted = service(store, config('email')).retry(original['receipt_id'])
    assert accepted['status'] == 'accepted' and accepted['channel'] == 'chat'
    assert store.get('case-one')['events'][0]['channel'] == 'chat'


def test_retained_source_hash_mismatch_fails_closed_on_retry(store):
    settings = config()
    settings['connectors'][0]['routes'] = {}
    inbox = service(store, settings)
    original = inbox.ingest('inbox', envelope())
    with store._transaction(write=True) as connection:
        connection.execute('UPDATE channel_inbox SET raw_envelope=? WHERE receipt_id=?',
                           (json.dumps(envelope(text='Tampered input.')), original['receipt_id']))
    with pytest.raises(RuntimeError, match='^channel_retained_source_mismatch$'):
        service(store).retry(original['receipt_id'])
    assert inbox.list() == [original]
    assert store.get('case-one')['revision'] == 0


def email_envelope():
    message = EmailMessage()
    message['From'] = 'client@example.test'
    message['To'] = 'desk@example.test'
    message['Date'] = 'Sat, 10 Oct 2026 10:00:00 +0000'
    message.set_content('The original email body.')
    # A real decodable 1x1 PNG, not a MIME-signature-only fixture.
    from PIL import Image
    image = io.BytesIO()
    Image.new('RGB', (1, 1), 'white').save(image, format='PNG')
    message.add_attachment(image.getvalue(), maintype='image', subtype='png', filename='photo.png')
    return {'schema_version': 'proofkey-inbound-v1', 'delivery_id': 'email-one',
            'conversation_id': 'conversation-private', 'format': 'email',
            'payload': {'raw_base64': base64.b64encode(message.as_bytes()).decode()}}


def test_multievent_email_assets_snapshots_outbox_and_receipt_are_atomic(store):
    receipt = service(store, config('email')).ingest('inbox', email_envelope())
    assert receipt['status'] == 'accepted' and len(receipt['event_ids']) == 2
    detail = store.detail('case-one')
    assert detail['snapshot']['revision'] == 2
    assert [e['kind'] for e in detail['snapshot']['events']] == ['message', 'photo']
    assert len(detail['assets']) == 1 and len(store.analysis_jobs('case-one')) == 3
    asset = detail['snapshot']['events'][1]['media']
    meta, data = store.get_asset('case-one', asset['asset_id'])
    assert meta['sha256'] == asset['sha256'] and len(data) == asset['size_bytes']


@pytest.mark.parametrize('unexpected', [False, True])
def test_partial_promotion_rolls_back_assets_events_outbox_and_receipt(store, monkeypatch, unexpected):
    inbox = service(store, config('email'))
    original = store._append
    count = 0
    def fail_second(connection, case_id, key, body):
        nonlocal count
        count += 1
        if count == 2:
            if unexpected:
                raise RuntimeError('unexpected failure: never quarantine this')
            raise CaseError('case_capacity')
        return original(connection, case_id, key, body)
    monkeypatch.setattr(store, '_append', fail_second)
    if unexpected:
        with pytest.raises(RuntimeError, match='unexpected failure'):
            inbox.ingest('inbox', email_envelope())
        assert inbox.list() == []
    else:
        receipt = inbox.ingest('inbox', email_envelope())
        assert receipt['status'] == 'quarantined' and receipt['reason'] == 'case_capacity'
        assert receipt['event_ids'] == [] and receipt['revision'] is None
    detail = store.detail('case-one')
    assert detail['snapshot']['revision'] == 0 and detail['assets'] == []
    assert len(store.analysis_jobs('case-one')) == 1


def test_unexpected_normalizer_error_never_becomes_quarantine(store, monkeypatch):
    module = service_module()
    def broken(*args):
        raise ValueError('programming_error')
    monkeypatch.setattr(module, 'normalize', broken)
    inbox = service(store)
    with pytest.raises(ValueError, match='programming_error'):
        inbox.ingest('inbox', envelope())
    assert inbox.list() == []


def test_parallel_duplicate_delivery_has_one_receipt_and_one_event(store):
    inbox = service(store)
    with ThreadPoolExecutor(max_workers=2) as workers:
        receipts = list(workers.map(lambda _: inbox.ingest('inbox', envelope()), range(2)))
    assert receipts[0] == receipts[1]
    assert len(inbox.list()) == 1 and store.get('case-one')['revision'] == 1


def test_inbox_bounds_refuse_new_receipt_but_allow_exact_replay(store, monkeypatch):
    module = service_module()
    monkeypatch.setattr(module, 'MAX_RECEIPTS', 1)
    inbox = service(store)
    first = inbox.ingest('inbox', envelope())
    with pytest.raises(ValueError, match='^inbox_capacity$'):
        inbox.ingest('inbox', envelope('delivery-two'))
    assert inbox.ingest('inbox', envelope()) == first
    assert len(inbox.list()) == 1


def test_raw_byte_budget_refuses_before_any_case_change(store, monkeypatch):
    module = service_module()
    monkeypatch.setattr(module, 'MAX_RETAINED_BYTES', 1)
    inbox = service(store)
    with pytest.raises(ValueError, match='^inbox_capacity$'):
        inbox.ingest('inbox', envelope())
    assert inbox.list() == [] and store.get('case-one')['revision'] == 0


def test_public_output_omits_content_external_contacts_and_secret_names(store):
    inbox = service(store)
    receipt = inbox.ingest('inbox', envelope())
    public = json.dumps({'connectors': inbox.capabilities(), 'receipts': inbox.list(),
                         'provenance': inbox.provenance('case-one')})
    for private in ('Original incoming text.', 'client@example.test', 'desk@example.test',
                    'conversation-private', 'CHANNEL_TEST_SECRET', 'raw_envelope', 'payload'):
        assert private not in public
    assert inbox.capabilities() == [{'id': 'inbox', 'channel': 'chat', 'configured': True,
                                     'route_count': 1, 'contact_count': 2, 'provider_connected': False}]
    assert inbox.provenance('case-one') == [receipt]
