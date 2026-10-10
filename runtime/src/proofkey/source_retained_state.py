"""Private logical source images, never provider or activation authority."""
import codecs
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import sqlite3
import stat
import threading

from .execution import ExecutionContext
from .identity import fingerprint, request_fingerprint, validate_json
from pydantic import TypeAdapter
from .contracts import (AuthContext, AuthorityObservation, EnvironmentProfile, Hash, Identifier,
                        NonnegativeInt, OwnerState, Revision, RevisionVector, Timestamp)
from .profiles import validate_profile, is_window_readiness_profile, _window_original_request_id
from .process import material_fields
from .packet_contracts import PacketCatalogV1, PacketAccessSnapshotV1, packet_enabled
from .ownership_contracts import (OwnershipPacketV1, OwnershipGrantV1, TransferArgumentsV1,
                                 TransferPostconditionV1, OriginalTransferIdentityV1,
                                 TransferAcceptedV1, TransferRejectedV1, ownership_enabled)
from .adapters.ownership import SourceTransferRecordV1, SyntheticOwnershipFixtureV1
from .retained_state import RetainedStateClock, RetainedStateLimitsV1

DOMAIN = 'synthetic-world-retained-state-v1'
TABLES = (
    ('effects', ('account_id', 'provider_key', 'case_id', 'object_id', 'operation', 'generation', 'action_id',
                 'fingerprint', 'identity_hash', 'request_id', 'stage', 'observations', 'created_at', 'question_id',
                 'transfer_id', 'packet_id', 'packet_revision')),
    ('facts', ('case_id', 'object_id', 'identity', 'value', 'revision', 'evidence_ref')),
    ('final_rejections', ('account_id', 'provider_key', 'case_id', 'object_id', 'operation', 'generation', 'action_id',
                         'fingerprint', 'identity_hash', 'request_id', 'created_at')),
    ('metadata', ('key', 'value')),
    ('pressure', ('account_id', 'used', 'active', 'ticks', 'blocked_until')),
    ('reservations', ('token', 'account_id', 'expires_at')),
    ('scopes', ('case_id', 'object_id', 'principal_id', 'readers')),
)
_PRIMARY_KEY_WIDTH = {'effects': 2, 'facts': 3, 'final_rejections': 2,
                      'metadata': 1, 'pressure': 1, 'reservations': 1, 'scopes': 2}
# Literal existing source DDL as returned by SQLite, including its whitespace.
_DDL = {
    'metadata': 'CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)',
    'scopes': 'CREATE TABLE scopes(case_id TEXT,object_id TEXT,principal_id TEXT,readers TEXT,\n                    PRIMARY KEY(case_id,object_id))',
    'facts': 'CREATE TABLE facts(case_id TEXT,object_id TEXT,identity TEXT,value TEXT,revision TEXT,\n                    evidence_ref TEXT,PRIMARY KEY(case_id,object_id,identity))',
    'effects': 'CREATE TABLE effects(account_id TEXT,provider_key TEXT,case_id TEXT,object_id TEXT,\n                    operation TEXT,generation TEXT,action_id TEXT,fingerprint TEXT,identity_hash TEXT,\n                    request_id TEXT,stage TEXT,observations TEXT,created_at TEXT,question_id TEXT,\n                    transfer_id TEXT,packet_id TEXT,packet_revision TEXT,PRIMARY KEY(account_id,provider_key))',
    'pressure': 'CREATE TABLE pressure(account_id TEXT PRIMARY KEY,used INTEGER,active INTEGER,\n                    ticks TEXT,blocked_until REAL)',
    'reservations': 'CREATE TABLE reservations(token TEXT PRIMARY KEY,account_id TEXT,expires_at REAL)',
    'final_rejections': 'CREATE TABLE final_rejections(account_id TEXT,provider_key TEXT,case_id TEXT,object_id TEXT,\n                    operation TEXT,generation TEXT,action_id TEXT,fingerprint TEXT,identity_hash TEXT,\n                    request_id TEXT,created_at TEXT,PRIMARY KEY(account_id,provider_key))',
}
SCHEMA = sorted([['table', name, name, sql] for name, sql in _DDL.items()] +
                [['index', 'sqlite_autoindex_' + name + '_1', name, None] for name in _DDL])


class SourceRetainedStateFailure(ValueError):
    def __init__(self, code):
        if code not in {'scope', 'limit', 'timeout', 'invalid', 'storage'}:
            code = 'invalid'
        self.code = code
        super().__init__(code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('invalid')
        result[key] = value
    return result


def parse(raw):
    def constant(_):
        raise ValueError('invalid')
    result = json.loads(raw, object_pairs_hook=_pairs, parse_constant=constant)
    validate_json(result)
    return result


def _utc(value):
    if type(value) is not datetime or value.utcoffset() is None or not math.isfinite(value.timestamp()):
        raise ValueError('invalid')
    # Detach mutable tzinfo without rounding lawful datetime microseconds through a float.
    return value.astimezone(timezone.utc)


def _tag(value):
    if value is None:
        return ['null']
    if type(value) is str:
        return ['text', value]
    if type(value) is int and -(2 ** 63) <= value < 2 ** 63:
        return ['integer', str(value)]
    if type(value) is float and math.isfinite(value):
        return ['real', value.hex()]
    raise ValueError('invalid')


def _untag(tag):
    if type(tag) is not list or not tag:
        raise ValueError('invalid')
    if tag == ['null']:
        return None
    if len(tag) != 2 or type(tag[1]) is not str:
        raise ValueError('invalid')
    kind, value = tag
    if kind == 'text':
        return value
    if kind == 'integer':
        result = int(value)
    elif kind == 'real':
        result = float.fromhex(value)
    else:
        raise ValueError('invalid')
    if _tag(result) != tag:
        raise ValueError('invalid')
    return result


def _typed(schema, value):
    return TypeAdapter(schema).validate_python(value, strict=True)


def _identifier(value):
    if type(value) is not str:
        raise ValueError('invalid')
    return _typed(Identifier, value)


def _numeric(value):
    if type(value) is int:
        return
    if type(value) is not float or not math.isfinite(value):
        raise ValueError('invalid')


def _timestamp(value):
    if type(value) is not str:
        raise ValueError('invalid')
    return _utc(_typed(Timestamp, value))


def _semantics(context, tables, *, check=lambda: None, connection=None, original_marker=None):
    """Capture-only predicates; no current action or disclosure permission."""
    from .adapters.world import required_material_keys, read_material_revisions

    check()
    profile = validate_profile(EnvironmentProfile.model_validate(context['profile']))
    fixture = context['fixture']
    if (type(fixture) is not dict or fixture.get('version') != 'synthetic-provider-v1'
            or context['fixture_hash'] != fingerprint(fixture) or context['as_of'] != fixture['as_of']):
        raise ValueError('invalid')
    _timestamp(context['as_of'])
    rows = {table['name']: [dict(zip(table['columns'], map(_untag, row))) for row in table['rows']]
            for table in tables}
    registered = ownership_enabled(profile)
    markers = [row['value'] for row in rows['metadata'] if row['key'] == 'fixture']
    if markers != [context['fixture_hash']]:
        raise ValueError('invalid')
    for row in rows['metadata']:
        check()
        if type(row['value']) is not str or row['key'] is not None and type(row['key']) is not str:
            raise ValueError('invalid')
    ownership_markers = [row['value'] for row in rows['metadata'] if row['key'] == 'ownership_fixture']
    owner_fixture = None
    if registered:
        owner_fixture = SyntheticOwnershipFixtureV1.model_validate(fixture['ownership_authority'])
        if len(ownership_markers) != 1:
            raise ValueError('invalid')
        marker = ownership_markers[0]
        retained_fixture = SyntheticOwnershipFixtureV1.model_validate(parse(marker))
        if (retained_fixture != owner_fixture or retained_fixture.model_dump_json() != marker
                or original_marker is not None and marker != original_marker):
            raise ValueError('invalid')
        packet, grant, request = owner_fixture.packet, owner_fixture.grant, owner_fixture.request
        if ((owner_fixture.profile_id, owner_fixture.profile_version, owner_fixture.profile_hash,
             owner_fixture.process_hash, owner_fixture.policy_hash) != (profile.profile_id, profile.version,
             profile.release_hash, profile.process_hash, profile.policy_hash)
                or packet.content_hash is None or request.kind not in profile.processes
                or packet.binding.fingerprint != request_fingerprint(request)
                or any(getattr(request, field) != getattr(packet.binding, field) for field in (
                    'case_id', 'object_id', 'principal_id', 'request_id', 'request_revision', 'consent_revision'))
                or (grant.binding, grant.packet_id, grant.packet_hash, grant.packet_revision, grant.content_hash,
                    grant.owner, grant.epoch, grant.state_revision) != (packet.binding, packet.packet_id,
                    packet.packet_hash, packet.packet_revision, packet.content_hash, packet.accepted_owner,
                    packet.accepted_epoch, packet.accepted_state_revision)
                or grant.actor_id != packet.accepted_owner or grant.issued_at > packet.accepted_at
                or not packet.accepted_at < grant.expires_at <= owner_fixture.case_deadline):
            raise ValueError('invalid')
    elif ownership_markers:
        raise ValueError('invalid')
    facts = {}
    structured = {'operator.packet_catalog': PacketCatalogV1, 'operator.packet_access': PacketAccessSnapshotV1}
    if registered:
        structured.update({'operator.ownership_packet': OwnershipPacketV1, 'operator.ownership_grant': OwnershipGrantV1})
    for row in rows['facts']:
        check()
        for field in ('case_id', 'object_id', 'identity', 'revision', 'evidence_ref'):
            _identifier(row[field])
        RevisionVector(revisions={row['identity']: row['revision']})
        identity = row['identity']
        if identity in profile.authorities and profile.authorities[identity] != identity.partition('.')[0]:
            raise ValueError('invalid')
        value = parse(row['value'])
        if packet_enabled(profile):
            if identity in structured:
                model = structured[identity].model_validate(value)
                binding = getattr(model, 'binding', model)
                if (binding.case_id, binding.object_id) != (row['case_id'], row['object_id']):
                    raise ValueError('invalid')
            if identity in {'ownership.owner', 'ownership.state_revision'}:
                _identifier(value)
            elif identity == 'ownership.state':
                _typed(OwnerState, value)
            elif identity == 'ownership.epoch':
                _typed(NonnegativeInt, value)
        key = (row['case_id'], row['object_id'], identity)
        if key in facts:
            raise ValueError('invalid')
        facts[key] = value
    operations = ('reschedule', 'register_goods_refusal', 'register_service_refusal', 'create_return',
                  'send_clarification', 'send_status', 'enqueue_handoff', 'transfer_owner')
    baseline = set().union(*(material_fields(operation) for operation in operations))
    for row in rows['scopes']:
        check()
        for field in ('case_id', 'object_id', 'principal_id'):
            _identifier(row[field])
        readers = parse(row['readers'])
        if type(readers) is not dict:
            raise ValueError('invalid')
        for caller, proof in readers.items():
            check()
            AuthContext(caller_id=caller, proof_reference=proof)
        binding = facts.get((row['case_id'], row['object_id'], 'case.binding'))
        if type(binding) is not dict:
            raise ValueError('invalid')
        for field in ('case_id', 'object_id', 'principal_id', 'request_id'):
            _identifier(binding.get(field))
        if any(binding[field] != row[field] for field in ('case_id', 'object_id', 'principal_id')):
            raise ValueError('invalid')
        required = set(baseline)
        for operation in operations:
            required.update(required_material_keys(connection, profile, operation, 'retained-validation') or ())
        if any((row['case_id'], row['object_id'], key) not in facts for key in required):
            raise ValueError('invalid')
        if connection is not None and not required <= read_material_revisions(
                connection, required, row['case_id'], row['object_id']).keys():
            raise ValueError('invalid')
    outcomes = {}
    for name in ('effects', 'final_rejections'):
        for row in rows[name]:
            check()
            for field in ('account_id', 'provider_key', 'case_id', 'object_id', 'operation', 'generation', 'action_id', 'request_id'):
                _identifier(row[field])
            for field in ('fingerprint', 'identity_hash'):
                _typed(Hash, row[field])
            _timestamp(row['created_at'])
            if (is_window_readiness_profile(profile) and row['operation'] == 'reschedule'
                    and row['request_id'].startswith('provider:window-envelope-v1:')):
                expected_request_id = _window_original_request_id(**{key: row[key] for key in
                    ('account_id', 'provider_key', 'case_id', 'object_id', 'operation',
                     'generation', 'action_id', 'fingerprint', 'identity_hash')})
            else:
                expected_request_id = 'provider:' + fingerprint({'account': row['account_id'], 'provider_key': row['provider_key']})[:24]
            if row['request_id'] != expected_request_id:
                raise ValueError('invalid')
            key = row['account_id'], row['provider_key']
            if key in outcomes:
                raise ValueError('invalid')
            outcomes[key] = name, row
            if name == 'effects':
                _identifier(row['stage'])
                for field in ('question_id', 'transfer_id', 'packet_id', 'packet_revision'):
                    if row[field] is not None:
                        _identifier(row[field])
                observations = parse(row['observations'])
                if type(observations) is not list:
                    raise ValueError('invalid')
                for value in observations:
                    check()
                    observation = AuthorityObservation.model_validate(value)
                    if (observation.object_id != row['object_id']
                            or observation.evidence_ref != 'synthetic-provider:effect:' + row['action_id']):
                        raise ValueError('invalid')
    for row in rows['pressure']:
        check()
        if row['account_id'] is not None:
            _identifier(row['account_id'])
        for field in ('used', 'active'):
            if type(row[field]) is not int or row[field] < 0:
                raise ValueError('invalid')
        ticks = parse(row['ticks'])
        if type(ticks) is not list:
            raise ValueError('invalid')
        for tick in ticks:
            check()
            _numeric(tick)
        _numeric(row['blocked_until'])
    for row in rows['reservations']:
        check()
        for field in ('token', 'account_id'):
            if row[field] is not None:
                _identifier(row[field])
        _numeric(row['expires_at'])
    if registered:
        _originals(rows['metadata'], outcomes, owner_fixture, profile, check)


def _originals(metadata, outcomes, fixture, profile, check):
    """Pure equivalent of saved-original joins; live capture also calls the public source validator."""
    originals = set()
    for row in metadata:
        key = row['key']
        # SQLite LIKE stops at embedded NUL even though the retained TEXT does
        # not. Preserve the full key; only selection mirrors the public helper.
        if key is None or not re.match(r'^ownership.original:', key.split('\x00', 1)[0],
                                       flags=re.IGNORECASE | re.ASCII | re.DOTALL):
            continue
        check()
        record = SourceTransferRecordV1.model_validate(parse(row['value']))
        effect, receipt = record.effect, record.receipt
        args = TransferArgumentsV1.model_validate(effect.arguments)
        condition = TransferPostconditionV1.model_validate(effect.postcondition)
        original = OriginalTransferIdentityV1(binding=effect.binding, transfer_id=args.intent.transfer_id,
            action_id=effect.action_id, provider_key=effect.provider_key, argument_fingerprint=effect.argument_fingerprint)
        if (effect.operation != 'transfer_owner' or effect.stage != 'request' or args.intent.binding != effect.binding
                or effect.binding != fixture.packet.binding or condition.original != original
                or condition.packet != fixture.packet or condition.target_owner != args.intent.target_owner
                or args.content_hash != fixture.packet.content_hash
                or (args.intent.packet_id, args.intent.packet_hash, args.intent.packet_revision,
                    args.intent.expected_owner, args.intent.expected_epoch, args.intent.expected_state_revision) != (
                    condition.packet.packet_id, condition.packet.packet_hash, condition.packet.packet_revision,
                    condition.packet.accepted_owner, condition.packet.accepted_epoch, condition.packet.accepted_state_revision)
                or args.grant_id != fixture.grant.grant_id or args.grant_revision != fixture.grant_revision
                or effect.consent_revision != effect.binding.consent_revision
                or effect.ownership_epoch != condition.packet.accepted_epoch
                or effect.ownership_state_revision != condition.packet.accepted_state_revision
                or effect.deadline != args.intent.expires_at or args.intent.expires_at > fixture.case_deadline
                or args.intent.expires_at > fixture.grant.expires_at):
            raise ValueError('invalid')
        if (key != 'ownership_original:' + fingerprint(receipt.original.model_dump(mode='json'))
                or record.fixture_hash != fixture.fixture_hash or record.grant != fixture.grant
                or (effect.profile_version, effect.process_version, effect.policy_version) != (
                    profile.version, profile.processes[fixture.request.kind].version, 'v1')
                or not set(profile.capabilities['transfer_owner'].conditional_coverage.covered_fields) <= effect.expected_revisions.revisions.keys()):
            raise ValueError('invalid')
        account = profile.capabilities['transfer_owner'].shared_limits.account_id
        outcome = outcomes.get((account, effect.provider_key))
        rejected = isinstance(receipt, TransferRejectedV1)
        if outcome is None or outcome[0] != ('final_rejections' if rejected else 'effects'):
            raise ValueError('invalid')
        _, saved = outcome
        expected = {'account_id': account, 'provider_key': effect.provider_key, 'case_id': effect.binding.case_id,
                    'object_id': effect.binding.object_id, 'operation': 'transfer_owner', 'generation': effect.binding.generation,
                    'action_id': effect.action_id, 'fingerprint': effect.argument_fingerprint,
                    'identity_hash': fingerprint(effect.model_dump(mode='json'))}
        if any(saved[name] != value for name, value in expected.items()):
            raise ValueError('invalid')
        if rejected:
            if receipt.evidence_ref != 'synthetic-provider:terminal-rejection:' + saved['request_id']:
                raise ValueError('invalid')
        else:
            accepted = isinstance(receipt, TransferAcceptedV1)
            event = receipt.accepted_at if accepted else receipt.pending_at
            observations = parse(saved['observations'])
            if (saved['stage'] != ('accepted' if accepted else 'pending') or saved['transfer_id'] != args.intent.transfer_id
                    or any(saved[name] is not None for name in ('question_id', 'packet_id', 'packet_revision'))
                    or len(observations) != 1):
                raise ValueError('invalid')
            observation = AuthorityObservation.model_validate(observations[0])
            if (observation.authority, observation.fact, observation.value, observation.provider_at, observation.observed_at) != (
                    'operator', 'transfer_receipt', receipt.model_dump(mode='json'), event, event):
                raise ValueError('invalid')
        originals.add((account, effect.provider_key))
    if any(row['operation'] == 'transfer_owner' and key not in originals for key, (_, row) in outcomes.items()):
        raise ValueError('invalid')


@dataclass(frozen=True, slots=True)
class SourceRetainedStateSnapshotV1:
    kind: str
    format_version: int
    schema_hash: str
    payload: bytes
    content_hash: str
    table_counts: tuple[tuple[str, int], ...]
    total_rows: int
    captured_at: datetime
    finished_at: datetime
    elapsed_seconds: float

    def __post_init__(self):
        try:
            if (type(self) is not SourceRetainedStateSnapshotV1 or self.kind != DOMAIN
                    or type(self.kind) is not str or type(self.format_version) is not int
                    or self.format_version != 1 or type(self.payload) is not bytes
                    or len(self.payload) > 4194304):
                raise ValueError('invalid')
            body = parse(self.payload)
            if (type(body) is not dict or set(body) != {'domain', 'format_version', 'context', 'schema', 'tables'}
                    or body['domain'] != DOMAIN or type(body['format_version']) is not int or body['format_version'] != 1
                    or body['schema'] != SCHEMA or canonical(body) != self.payload
                    or type(self.content_hash) is not str or self.content_hash != sha256(self.payload).hexdigest()
                    or type(self.schema_hash) is not str or self.schema_hash != sha256(canonical(SCHEMA)).hexdigest()):
                raise ValueError('invalid')
            context = body['context']
            if (type(context) is not dict or set(context) != {'profile', 'fixture', 'fixture_hash', 'as_of'}
                    or context['fixture_hash'] != fingerprint(context['fixture'])
                    or context['as_of'] != context['fixture']['as_of']):
                raise ValueError('invalid')
            counts = []
            if type(body['tables']) is not list or len(body['tables']) != len(TABLES):
                raise ValueError('invalid')
            for table, (name, columns) in zip(body['tables'], TABLES):
                if (type(table) is not dict or set(table) != {'name', 'columns', 'rows'} or table['name'] != name
                        or table['columns'] != list(columns) or type(table['rows']) is not list):
                    raise ValueError('invalid')
                previous = b''
                keys = set()
                for row in table['rows']:
                    if type(row) is not list or len(row) != len(columns):
                        raise ValueError('invalid')
                    for value in row:
                        _untag(value)
                    key = tuple(_untag(value) for value in row[:_PRIMARY_KEY_WIDTH[name]])
                    if None not in key:
                        if key in keys:
                            raise ValueError('invalid')
                        keys.add(key)
                    raw = canonical(row)
                    if len(raw) > 262144 or raw < previous:
                        raise ValueError('invalid')
                    previous = raw
                counts.append((name, len(table['rows'])))
            if (type(self.table_counts) is not tuple or any(type(item) is not tuple or len(item) != 2
                    or type(item[0]) is not str or type(item[1]) is not int for item in self.table_counts)
                    or self.table_counts != tuple(counts) or type(self.total_rows) is not int
                    or self.total_rows != sum(count for _, count in counts) or self.total_rows > 4096):
                raise ValueError('invalid')
            _semantics(context, body['tables'])
            captured, finished = _utc(self.captured_at), _utc(self.finished_at)
            if (finished < captured or type(self.elapsed_seconds) is not float
                    or not math.isfinite(self.elapsed_seconds) or not 0 <= self.elapsed_seconds <= 5.0
                    or (finished - captured).total_seconds() > 5.0):
                raise ValueError('invalid')
            object.__setattr__(self, 'captured_at', captured)
            object.__setattr__(self, 'finished_at', finished)
        except (ValueError, TypeError, KeyError, OverflowError, RecursionError, UnicodeError):
            raise ValueError('invalid') from None


def _identity(path):
    info = path.lstat()
    parent = path.parent.lstat()
    if not stat.S_ISREG(info.st_mode) or not stat.S_ISDIR(parent.st_mode):
        raise ValueError('invalid')
    return (info.st_dev, info.st_ino, parent.st_dev, parent.st_ino)


def prepare_context(path, profile, fixture, fixture_hash):
    """Capture-only metadata: failure must never reject an old constructor."""
    try:
        raw = canonical({'profile': profile.model_dump(mode='json'), 'fixture': fixture,
                         'fixture_hash': fixture_hash, 'as_of': fixture['as_of']})
        original = Path(path).absolute()
        _identity(original)
        selected = original.resolve(strict=True)
        identity = _identity(selected)
        if len(raw) > 4194304:
            return None
        return raw, selected, identity, threading.get_ident(), threading.Lock()
    except (ValueError, TypeError, OSError, OverflowError, RecursionError):
        return None


class _Window:
    def __init__(self, execution, clock, limits):
        if type(execution) is not ExecutionContext or type(limits) is not RetainedStateLimitsV1:
            raise SourceRetainedStateFailure('scope')
        limits = RetainedStateLimitsV1(**{name: getattr(limits, name) for name in (
            'max_rows', 'max_row_bytes', 'max_payload_bytes', 'max_capture_seconds', 'max_sqlite_steps')})
        if not callable(getattr(clock, 'now', None)) or not callable(getattr(clock, 'monotonic', None)):
            raise SourceRetainedStateFailure('invalid')
        self.clock, self.execution, self.limits = clock, execution, limits
        self.start = _utc(execution.captured_at)
        self.cutoff = min(_utc(execution.deadline), self.start + timedelta(seconds=limits.max_capture_seconds))
        self.mono_cutoff = min(execution.monotonic_deadline, execution.captured_monotonic + limits.max_capture_seconds)
        self.previous_utc, self.previous_mono = self.start, execution.captured_monotonic
        self.steps, self.interrupted = 0, None
        self.sample()

    def sample(self):
        now = _utc(self.clock.now())
        mono = self.clock.monotonic()
        if (type(mono) not in (int, float) or not math.isfinite(mono) or mono < self.previous_mono
                or now < self.previous_utc):
            raise SourceRetainedStateFailure('invalid')
        self.previous_utc, self.previous_mono = now, mono
        if now >= self.cutoff or mono >= self.mono_cutoff:
            raise SourceRetainedStateFailure('timeout')
        return now, float(mono - self.execution.captured_monotonic)

    def progress(self):
        self.steps += 1
        try:
            if self.steps > self.limits.max_sqlite_steps:
                raise SourceRetainedStateFailure('limit')
            self.sample()
        except Exception as error:
            self.interrupted = error if isinstance(error, SourceRetainedStateFailure) else SourceRetainedStateFailure('invalid')
            return 1
        return 0


def _preflight(db, context, window):
    """No full TEXT or JSON/model reads before every table passes this pass."""
    limits = window.limits
    total, row_ids, row_bytes = 0, {}, 0
    for name, columns in TABLES:
        ids = []
        for (rowid,) in db.execute('SELECT rowid FROM ' + name):
            window.sample()
            total += 1
            if total > limits.max_rows:
                raise SourceRetainedStateFailure('limit')
            ids.append(rowid)
            size = 2 + max(0, len(columns) - 1)
            for column in columns:
                kind, length, number = db.execute(
                    'SELECT typeof(' + column + '),length(CAST(' + column + ' AS BLOB)),CASE WHEN typeof(' + column +
                    ") IN ('integer','real') THEN " + column + ' ELSE NULL END FROM ' + name + ' WHERE rowid=?',
                    (rowid,)).fetchone()
                if kind == 'text':
                    if length > limits.max_row_bytes:
                        raise SourceRetainedStateFailure('limit')
                    decoder = codecs.getincrementaldecoder('utf-8')('strict')
                    text_size = 2
                    for offset in range(1, length + 1, 4096):
                        window.sample()
                        chunk = db.execute('SELECT substr(CAST(' + column + ' AS BLOB),?,4096) FROM ' + name +
                                           ' WHERE rowid=?', (offset, rowid)).fetchone()[0]
                        text = decoder.decode(chunk, final=offset + 4096 > length)
                        text_size += len(canonical(text)) - 2
                    size += 9 + text_size
                elif kind == 'null':
                    size += 8
                elif kind in {'integer', 'real'}:
                    size += len(canonical(_tag(number)))
                else:
                    raise SourceRetainedStateFailure('invalid')
                if size > limits.max_row_bytes:
                    raise SourceRetainedStateFailure('limit')
            row_bytes += size + 1
        row_ids[name] = ids
    # The exact envelope overhead can be calculated before materializing rows.
    empty = {'domain': DOMAIN, 'format_version': 1, 'context': context, 'schema': SCHEMA,
             'tables': [{'name': name, 'columns': list(columns), 'rows': []} for name, columns in TABLES]}
    estimated = len(canonical(empty)) + row_bytes - sum(bool(ids) for ids in row_ids.values())
    if estimated > limits.max_payload_bytes:
        raise SourceRetainedStateFailure('limit')
    return row_ids


def capture(prepared, *, execution: ExecutionContext, clock: RetainedStateClock,
            limits: RetainedStateLimitsV1, ownership=None):
    if prepared is None or threading.get_ident() != prepared[3] or not prepared[4].acquire(blocking=False):
        raise SourceRetainedStateFailure('scope')
    db = None
    window = None
    try:
        window = _Window(execution, clock, limits)
        context_raw, path, identity, _, _ = prepared
        if _identity(path) != identity:
            raise SourceRetainedStateFailure('storage')
        context = parse(context_raw)
        db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=0.0)
        db.row_factory = sqlite3.Row
        db.set_progress_handler(window.progress, 1)
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')
        if db.execute('SELECT count(*) FROM sqlite_master').fetchone()[0] != 14:
            raise SourceRetainedStateFailure('invalid')
        if db.execute('SELECT sum(length(CAST(sql AS BLOB))) FROM sqlite_master').fetchone()[0] > limits.max_payload_bytes:
            raise SourceRetainedStateFailure('limit')
        schema = sorted([list(row) for row in db.execute('SELECT type,name,tbl_name,sql FROM sqlite_master')])
        if schema != SCHEMA:
            raise SourceRetainedStateFailure('invalid')
        for name, columns in TABLES:
            if [row[1] for row in db.execute('PRAGMA table_info(' + name + ')')] != list(columns):
                raise SourceRetainedStateFailure('invalid')
        ids = _preflight(db, context, window)
        tables = []
        for name, columns in TABLES:
            rows = []
            for rowid in ids[name]:
                window.sample()
                row = list(db.execute('SELECT * FROM ' + name + ' WHERE rowid=?', (rowid,)).fetchone())
                if name == 'facts':
                    parse(row[3])
                rows.append([_tag(value) for value in row])
            tables.append({'name': name, 'columns': list(columns), 'rows': sorted(rows, key=canonical)})
        _semantics(context, tables, check=window.sample, connection=db,
                   original_marker=ownership.fixture.model_dump_json() if ownership is not None else None)
        if ownership is not None:
            window.sample()
            ownership.validate_records(db)
        body = {'domain': DOMAIN, 'format_version': 1, 'context': context, 'schema': schema, 'tables': tables}
        payload = canonical(body)
        if len(payload) > limits.max_payload_bytes:
            raise SourceRetainedStateFailure('limit')
        db.close()
        db = None
        if _identity(path) != identity:
            raise SourceRetainedStateFailure('storage')
        finished, elapsed = window.sample()
        counts = tuple((table['name'], len(table['rows'])) for table in tables)
        result = SourceRetainedStateSnapshotV1(DOMAIN, 1, sha256(canonical(schema)).hexdigest(), payload,
            sha256(payload).hexdigest(), counts, sum(count for _, count in counts), window.start, finished, elapsed)
        finished, elapsed = window.sample()
        # The complete immutable projection has passed validation. Only its
        # final, already bounded clock observations are assigned before escape.
        object.__setattr__(result, 'finished_at', finished)
        object.__setattr__(result, 'elapsed_seconds', elapsed)
        return result
    except SourceRetainedStateFailure:
        raise
    except sqlite3.Error:
        if window is not None and window.interrupted is not None:
            raise window.interrupted from None
        raise SourceRetainedStateFailure('storage') from None
    except OSError:
        raise SourceRetainedStateFailure('storage') from None
    except Exception:
        raise SourceRetainedStateFailure('invalid') from None
    finally:
        try:
            if db is not None:
                db.close()
        except (sqlite3.Error, OSError):
            raise SourceRetainedStateFailure('storage') from None
        except Exception:
            raise SourceRetainedStateFailure('invalid') from None
        finally:
            prepared[4].release()
