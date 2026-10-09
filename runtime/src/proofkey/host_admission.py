"""Fixed synthetic host admission. Declarations never authorize activation."""
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from functools import wraps
from contextlib import contextmanager
from hashlib import sha256
import base64
import json
import math
import os
from pathlib import Path
import stat
import sqlite3
import threading
from uuid import uuid4

from .clock import SyntheticReplayClock
from .contracts import AuthContext, CanonicalRequest, PhaseCheckpoint, RequestBinding
from .execution import ExecutionContext
from .identity import request_fingerprint
from .admission_routes import AdmissionRouteStoreV1
from .retained_state import RetainedStateSnapshotV1
from .registered_releases import ReleaseRegistryV1, RegisteredReleaseV1


class AdmissionCompositionFailure(ValueError):
    def __init__(self, code):
        self.code = code if code in {'invalid', 'scope', 'conflict', 'storage', 'timeout',
            'unregistered', 'pending_claim', 'unsupported_release', 'limit'} else 'invalid'
        super().__init__(self.code)


def _require(condition, code='invalid'):
    if not condition:
        raise AdmissionCompositionFailure(code)


def _checked(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except AdmissionCompositionFailure:
            raise
        except OSError:
            raise AdmissionCompositionFailure('storage') from None
        except (sqlite3.Error, RuntimeError):
            raise AdmissionCompositionFailure('storage') from None
        except (ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError, RecursionError):
            raise AdmissionCompositionFailure('invalid') from None
    return wrapped


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def _hash(value):
    return sha256(_canonical(value)).hexdigest()


def _id(value):
    _require(type(value) is str and 0 < len(value) <= 256 and bool(value.strip()))


def _digest(value):
    _require(type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value))


def _identity(path, *, directory=False):
    value = os.lstat(path)
    _require((stat.S_ISDIR(value.st_mode) if directory else stat.S_ISREG(value.st_mode))
        and (directory or (value.st_nlink == 1 and stat.S_IMODE(value.st_mode) == 0o600)), 'storage')
    return value.st_dev, value.st_ino


@_checked
def control_context(execution, clock):
    _require(type(execution) is ExecutionContext, 'scope')
    original = ExecutionContext(execution.deadline, execution.captured_at,
        execution.captured_monotonic, execution.monotonic_deadline)
    deadline = min(original.deadline, original.captured_at + timedelta(seconds=5))
    value = ExecutionContext(deadline, original.captured_at, original.captured_monotonic,
        original.captured_monotonic + max(0.0, (deadline - original.captured_at).total_seconds()))
    _require(clock.now() >= original.captured_at and value.remaining_seconds(clock) > 0, 'timeout')
    return value


@_checked
def _observation_context(execution, clock):
    """One final phase, clipped to both unchanged original parent bounds."""
    _require(type(execution) is ExecutionContext, 'scope')
    original = ExecutionContext(execution.deadline, execution.captured_at,
        execution.captured_monotonic, execution.monotonic_deadline)
    monotonic = clock.monotonic()
    now = clock.now()
    _require(type(monotonic) in (int, float) and math.isfinite(monotonic), 'timeout')
    _require(now >= original.captured_at and monotonic >= original.captured_monotonic, 'timeout')
    remaining = min(5.0, (original.deadline - now).total_seconds(),
        original.monotonic_deadline - monotonic)
    # Round down to datetime precision so conversion cannot extend the parent.
    duration = timedelta(microseconds=math.floor(remaining * 1000000))
    _require(duration.total_seconds() > 0, 'timeout')
    return ExecutionContext(now + duration, now, monotonic, monotonic + duration.total_seconds())

FIXED_IMPLEMENTATION_PATHS = ('adapters/world.py', 'admission.py', 'admission_routes.py',
    'contracts.py', 'engine.py', 'execution.py', 'gateway.py', 'host.py',
    'host_admission.py', 'host_writer.py', 'journal.py', 'policy.py', 'process.py',
    'registered_releases.py', 'retained_state.py', 'source_retained_state.py')


@dataclass(frozen=True, slots=True)
class HostExecutableBindingV1:
    host_release_id: str
    registered_release_id: str
    artifact_hash: str
    factory_id: str
    implementation_pins: tuple[tuple[str, str], ...]
    dependency_hash: str
    host_factory_key: str = 'fixed-synthetic-v1'

    @_checked
    def __post_init__(self):
        _require(type(self) is HostExecutableBindingV1)
        for value in (self.host_release_id, self.registered_release_id, self.factory_id):
            _id(value)
        _digest(self.artifact_hash); _digest(self.dependency_hash)
        _require(self.host_factory_key == self.factory_id == 'fixed-synthetic-v1', 'unsupported_release')
        _require(type(self.implementation_pins) is tuple and len(self.implementation_pins) == len(FIXED_IMPLEMENTATION_PATHS))
        for pair in self.implementation_pins:
            _require(type(pair) is tuple and len(pair) == 2)
            _id(pair[0]); _digest(pair[1])
        _require(tuple(pair[0] for pair in self.implementation_pins) == FIXED_IMPLEMENTATION_PATHS)


@dataclass(frozen=True, slots=True)
class SyntheticReviewGrantV1:
    review_id: str
    artifact_hash: str
    actor_id: str
    scope: str
    provenance: str
    issued_at: datetime
    expires_at: datetime

    @_checked
    def __post_init__(self):
        _require(type(self) is SyntheticReviewGrantV1)
        for value in (self.review_id, self.actor_id):
            _id(value)
        _digest(self.artifact_hash)
        _require(self.scope == 'admit_fixed_local_replay' and self.provenance == 'synthetic_rehearsal', 'scope')
        _require(all(type(value) is datetime and value.utcoffset() is not None for value in (self.issued_at, self.expires_at)))
        _require(self.issued_at < self.expires_at)


@dataclass(frozen=True, slots=True)
class ProvisionedReviewResolverV1:
    grants: tuple[SyntheticReviewGrantV1, ...]

    @_checked
    def __post_init__(self):
        _require(type(self) is ProvisionedReviewResolverV1 and type(self.grants) is tuple and 0 < len(self.grants) <= 256)
        for grant in self.grants:
            _require(type(grant) is SyntheticReviewGrantV1)
            SyntheticReviewGrantV1(**asdict(grant))
        _require(len({grant.review_id for grant in self.grants}) == len(self.grants))

    @_checked
    def resolve(self, review_id, *, artifact_hash, execution, clock):
        ProvisionedReviewResolverV1(self.grants)
        control_context(execution, clock)
        for grant in self.grants:
            if grant.review_id == review_id:
                _require(grant.artifact_hash == artifact_hash and grant.issued_at <= clock.now() < grant.expires_at, 'scope')
                return SyntheticReviewGrantV1(**asdict(grant))
        raise AdmissionCompositionFailure('unregistered')


@dataclass(frozen=True, slots=True)
class LocalAdmissionCompositionV1:
    registry: object
    binding: HostExecutableBindingV1
    approvals: ProvisionedReviewResolverV1
    review_id: str
    control_parent: Path

    @_checked
    def __post_init__(self):
        _require(type(self) is LocalAdmissionCompositionV1 and type(self.registry) is ReleaseRegistryV1)
        _require(type(self.binding) is HostExecutableBindingV1 and type(self.approvals) is ProvisionedReviewResolverV1)
        HostExecutableBindingV1(**asdict(self.binding)); ProvisionedReviewResolverV1(self.approvals.grants)
        _id(self.review_id)
        _require(type(self.control_parent) is type(Path()) and self.control_parent.is_absolute()
            and len(str(self.control_parent)) <= 1024 and '..' not in self.control_parent.parts, 'scope')
        for path in (self.control_parent, *self.control_parent.parents):
            _require(not stat.S_ISLNK(os.lstat(path).st_mode), 'scope')
        _identity(self.control_parent, directory=True)


@_checked
def validate_composition(release, clock, composition, execution):
    from .host import ApprovedProfileRelease
    _require(type(release) is ApprovedProfileRelease and type(clock) is SyntheticReplayClock, 'scope')
    _require(type(composition) is LocalAdmissionCompositionV1)
    LocalAdmissionCompositionV1(composition.registry, composition.binding, composition.approvals,
        composition.review_id, composition.control_parent)
    binding = HostExecutableBindingV1(**asdict(composition.binding))
    registered = composition.registry.resolve(binding.registered_release_id)
    # B3 exposes resolution, while its frozen inventory binds one composition.
    _require(type(composition.registry._releases) is tuple and len(composition.registry._releases) == 1)
    _require(type(composition.registry._releases[0]) is tuple and len(composition.registry._releases[0]) == 2
        and type(composition.registry._releases[0][1]) is bytes)
    registered = RegisteredReleaseV1(registered.wire_bytes)
    _require(registered.artifact_hash == binding.artifact_hash and release.release_id == binding.host_release_id, 'conflict')
    factory, resource = registered.factory, registered.resource
    _require(factory.factory_id == binding.factory_id and factory.implementation_pins == binding.implementation_pins
        and factory.dependency_hash == binding.dependency_hash, 'conflict')
    profile = release.validate()
    _require(release.mode == 'synthetic_replay' and profile.version == 'v1.3'
        and all(process.version == 'v1' for process in profile.processes.values()), 'unsupported_release')
    body = json.loads(registered.wire_bytes)
    _require(base64.b64decode(body['blobs']['profile']['base64'], validate=True)
        == _canonical(profile.model_dump(mode='json')), 'conflict')
    _require((profile.release_hash, profile.process_hash, profile.policy_hash) ==
        (release.profile_hash, release.process_hash, release.policy_hash), 'conflict')
    _require(resource.root_path == str(release.resource_root)
        and (resource.root_device, resource.root_inode) == _identity(release.resource_root, directory=True)
        and resource.journal_name == 'journal.sqlite' and resource.source_name == 'world.sqlite', 'conflict')
    accounts = tuple(sorted({item.shared_limits.account_id for item in profile.capabilities.values()
        if item.shared_limits.account_id is not None}))
    _require(resource.account_ids == accounts, 'conflict')
    source = Path(__file__).resolve().parent
    for name, expected in binding.implementation_pins:
        path = source / name
        _require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 1048576, 'unsupported_release')
        _require(sha256(path.read_bytes()).hexdigest() == expected, 'conflict')
    declared_source = json.loads(base64.b64decode(body['blobs']['source']['base64'], validate=True))
    _require(declared_source['source_id'] == 'fixed-world-fixture' and declared_source['documents'] ==
        [dict(source_id='fixed-world-fixture', text=release.fixture_path.read_text())], 'conflict')
    composition.approvals.resolve(composition.review_id, artifact_hash=binding.artifact_hash,
        execution=execution, clock=clock)
    return profile, registered


def _parse(raw, maximum=262144):
    _require(type(raw) is bytes and 0 < len(raw) <= maximum, 'limit')
    def pairs(items):
        result = {}
        for key, value in items:
            _require(key not in result)
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(AdmissionCompositionFailure('invalid')))
    _require(type(value) is dict and _canonical(value) == raw)
    return value


def _model(value, model):
    _require(type(value) is dict and set(value) == set(model.model_fields))
    result = model.model_validate(value)
    _require(_canonical(result.model_dump(mode='json')) == _canonical(value))
    return result


def _stamp(value):
    return value.astimezone(timezone.utc).isoformat()


def _window(execution):
    return dict(deadline=_stamp(execution.deadline), captured_at=_stamp(execution.captured_at),
        captured_monotonic=execution.captured_monotonic, monotonic_deadline=execution.monotonic_deadline)


def _grant(grant):
    return dict(review_id=grant.review_id, artifact_hash=grant.artifact_hash, actor_id=grant.actor_id,
        scope=grant.scope, provenance=grant.provenance, issued_at=_stamp(grant.issued_at), expires_at=_stamp(grant.expires_at))


_ORIGINAL = ('kind', 'version', 'claim_id', 'attempt_id', 'route_id', 'resource_id', 'resource_hash',
    'artifact_hash', 'release_id', 'review', 'request', 'auth_claim', 'execution',
    'initial_journal_hash', 'initial_source_hash')
_CHANGING = ('claim_hash', 'state', 'binding', 'route_reservation_hash', 'seal_hash',
    'final_journal_hash', 'final_source_hash', 'observation_hash', 'record_hash')


def _claim(raw):
    value = _parse(raw)
    _require(set(value) == set(_ORIGINAL + _CHANGING))
    _require(value['kind'] == 'registered-host-admission-v1' and type(value['version']) is int and value['version'] == 1)
    for key in ('claim_id', 'attempt_id', 'route_id', 'resource_id', 'release_id'):
        _id(value[key])
    for key in ('artifact_hash', 'resource_hash', 'claim_hash', 'initial_journal_hash', 'initial_source_hash', 'record_hash'):
        _digest(value[key])
    request = _model(value['request'], CanonicalRequest)
    auth = value['auth_claim']
    _require(type(auth) is dict and set(auth) == {'caller_id', 'proof_digest'})
    _id(auth['caller_id']); _digest(auth['proof_digest'])
    review = value['review']
    _require(type(review) is dict and set(review) == set(SyntheticReviewGrantV1.__dataclass_fields__))
    grant = SyntheticReviewGrantV1(**{**review, 'issued_at': datetime.fromisoformat(review['issued_at']),
        'expires_at': datetime.fromisoformat(review['expires_at'])})
    _require(_grant(grant) == review and grant.artifact_hash == value['artifact_hash'])
    window = value['execution']
    _require(type(window) is dict and set(window) == set(ExecutionContext.__dataclass_fields__))
    context = ExecutionContext(datetime.fromisoformat(window['deadline']), datetime.fromisoformat(window['captured_at']),
        window['captured_monotonic'], window['monotonic_deadline'])
    _require(_window(context) == window)
    _require(value['claim_hash'] == _hash({key: value[key] for key in _ORIGINAL}))
    _require(value['record_hash'] == _hash({key: item for key, item in value.items() if key != 'record_hash'}))
    _require(value['state'] in {'prepared', 'binding_sealed', 'admission_observed'})
    if value['state'] == 'prepared':
        _require(all(value[key] is None for key in ('binding', 'route_reservation_hash', 'seal_hash',
            'final_journal_hash', 'final_source_hash', 'observation_hash')))
    else:
        binding = _model(value['binding'], RequestBinding)
        _require(all(getattr(binding, key) == getattr(request, key) for key in
            ('case_id', 'object_id', 'principal_id', 'request_id', 'request_revision', 'consent_revision')))
        _require(binding.supersedes_generation is None)
        _require(binding.fingerprint == _hash({key: value['request'][key]
            for key in ('kind', 'consent_mode', 'arguments')}))
        _digest(value['route_reservation_hash']); _digest(value['seal_hash'])
        _require(value['seal_hash'] == _hash(dict(claim_hash=value['claim_hash'], binding=value['binding'],
            route_reservation_hash=value['route_reservation_hash'], artifact_hash=value['artifact_hash'])))
        for key in ('final_journal_hash', 'final_source_hash', 'observation_hash'):
            if value['state'] == 'admission_observed': _digest(value[key])
            else: _require(value[key] is None)
    return value


@dataclass(frozen=True, slots=True)
class AdmissionClaimV1:
    wire_bytes: bytes

    @_checked
    def __post_init__(self):
        _require(type(self) is AdmissionClaimV1)
        _claim(self.wire_bytes)

    @property
    @_checked
    def state(self): return _claim(self.wire_bytes)['state']
    @property
    @_checked
    def claim_id(self): return _claim(self.wire_bytes)['claim_id']
    @property
    @_checked
    def attempt_id(self): return _claim(self.wire_bytes)['attempt_id']
    @property
    @_checked
    def binding(self):
        value = _claim(self.wire_bytes)['binding']
        return None if value is None else RequestBinding.model_validate(value)
    @property
    @_checked
    def route_reservation_hash(self): return _claim(self.wire_bytes)['route_reservation_hash']


_DDL = (
    'CREATE TABLE meta(singleton INTEGER PRIMARY KEY CHECK(singleton=1),version INTEGER NOT NULL CHECK(version=1),composition_hash TEXT NOT NULL)',
    'CREATE TABLE claims(claim_id TEXT PRIMARY KEY NOT NULL,case_id TEXT NOT NULL UNIQUE,attempt_id TEXT NOT NULL UNIQUE,state TEXT NOT NULL,wire TEXT NOT NULL)',
)


class _ClaimStore:
    """A bounded separate store. Resource/B3 owners serialize every operation."""
    def __init__(self, owner):
        self.owner = owner
        self.path = owner.composition.control_parent / 'host-claims.sqlite'
        self.db = None
        self.fd = None
        self.identity = None
        self.closed = False
        self.failed = False

    def open(self, execution):
        fresh = not os.path.lexists(self.path)
        if not fresh: _identity(self.path)
        self.fd = os.open(self.path, os.O_RDWR | os.O_NOFOLLOW | (os.O_CREAT | os.O_EXCL if fresh else 0), 0o600)
        self.identity = _identity(self.path)
        _require((os.fstat(self.fd).st_dev, os.fstat(self.fd).st_ino) == self.identity, 'storage')
        self.db = sqlite3.connect(self.path.as_uri() + '?mode=rw', uri=True, timeout=0, isolation_level=None)
        if fresh:
            self.db.execute('PRAGMA synchronous=FULL')
        with self.operation(execution, write=fresh, initial=fresh):
            if fresh:
                for ddl in _DDL: self.db.execute(ddl)
                self.db.execute('INSERT INTO meta VALUES(1,1,?)', (self.owner.configuration_hash,))
            self.rows()

    def check(self):
        _require(not self.failed and not self.closed and self.db is not None, 'storage')
        self.owner.check()
        _require(_identity(self.path) == self.identity, 'storage')
        for suffix in ('-journal', '-wal', '-shm'):
            path = Path(str(self.path) + suffix)
            if os.path.lexists(path):
                _identity(path)

    @contextmanager
    def operation(self, execution, *, write=False, initial=False):
        context = control_context(execution, self.owner.clock)
        self.check()
        steps = 0
        def progress():
            nonlocal steps
            steps += 1
            try:
                _require(steps <= 1000000, 'limit')
                if steps % 32 == 0: control_context(context, self.owner.clock)
                return 0
            except Exception:
                return 1
        try:
            self.db.set_progress_handler(progress, 1)
            self.db.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
            if not initial: self.rows()
            yield
            control_context(context, self.owner.clock)
            self.check()
            self.db.execute('COMMIT')
            control_context(context, self.owner.clock)
        except sqlite3.Error:
            raise AdmissionCompositionFailure('storage') from None
        finally:
            try:
                self.db.set_progress_handler(None, 0)
                if self.db.in_transaction: self.db.execute('ROLLBACK')
            except BaseException:
                self.failed = True
                raise AdmissionCompositionFailure('storage') from None

    def rows(self):
        # Check counts and lengths before materializing schema or row payloads.
        _require(self.db.execute('SELECT count(*) FROM sqlite_master').fetchone()[0] == 5, 'storage')
        _require(self.db.execute('SELECT coalesce(max(length(sql)),0) FROM sqlite_master').fetchone()[0] <= 1024, 'storage')
        schema = tuple(self.db.execute('SELECT type,name,sql FROM sqlite_master ORDER BY name'))
        expected = [('table', name, ddl) for name, ddl in zip(('meta', 'claims'), _DDL)]
        expected += [('index', 'sqlite_autoindex_claims_' + str(number), None) for number in (1, 2, 3)]
        _require(schema == tuple(sorted(expected, key=lambda row: row[1])), 'storage')
        _require(self.db.execute('PRAGMA journal_mode').fetchone() == ('delete',)
            and self.db.execute('PRAGMA synchronous').fetchone() == (2,), 'storage')
        _require(self.db.execute('SELECT count(*) FROM meta').fetchone()[0] == 1
            and self.db.execute('SELECT coalesce(max(length(CAST(composition_hash AS BLOB))),0) FROM meta').fetchone()[0] == 64, 'storage')
        _require(tuple(self.db.execute('SELECT * FROM meta LIMIT 2')) == ((1, 1, self.owner.configuration_hash),), 'storage')
        size = 'length(CAST(wire AS BLOB))+length(CAST(claim_id AS BLOB))+length(CAST(case_id AS BLOB))+length(CAST(attempt_id AS BLOB))+length(CAST(state AS BLOB))'
        count, maximum, total = self.db.execute(f'SELECT count(*),coalesce(max({size}),0),coalesce(sum({size}),0) FROM claims').fetchone()
        _require(count <= 4096 and maximum <= 262144 and total <= 8388608, 'limit')
        rows = []
        cursor = self.db.execute('SELECT claim_id,case_id,attempt_id,state,wire FROM claims ORDER BY claim_id')
        while batch := cursor.fetchmany(32):
            self.check()
            for claim_id, case_id, attempt_id, state, raw in batch:
                _require(type(raw) is str)
                value = _claim(raw.encode())
                _require((claim_id, case_id, attempt_id, state) == (value['claim_id'], value['request']['case_id'], value['attempt_id'], value['state']), 'storage')
                _require(value['artifact_hash'] == self.owner.registered.artifact_hash
                    and value['resource_hash'] == self.owner.resource_hash
                    and value['resource_id'] == self.owner.registered.resource.resource_id
                    and value['release_id'] == self.owner.composition.binding.registered_release_id, 'storage')
                rows.append(value)
        return rows

    def find(self, case_id, execution):
        with self.operation(execution):
            return next((AdmissionClaimV1(_canonical(value)) for value in self.rows() if value['request']['case_id'] == case_id), None)

    def pending(self, execution):
        with self.operation(execution):
            return any(value['state'] != 'admission_observed' for value in self.rows())

    def write(self, value, execution, *, initial=False):
        value = dict(value)
        value['record_hash'] = _hash({key: item for key, item in value.items() if key != 'record_hash'})
        claim = AdmissionClaimV1(_canonical(value))
        with self.operation(execution, write=True):
            rows = self.rows()
            old = next((row for row in rows if row['claim_id'] == value['claim_id']), None)
            _require((old is None) == initial, 'conflict')
            _require(len(rows) + int(initial) <= 4096
                and sum(len(_canonical(row)) for row in rows if row is not old) + len(claim.wire_bytes) <= 8388608, 'limit')
            if initial:
                self.db.execute('INSERT INTO claims VALUES(?,?,?,?,?)', (value['claim_id'], value['request']['case_id'],
                    value['attempt_id'], value['state'], claim.wire_bytes.decode()))
            else:
                _require(old['claim_hash'] == value['claim_hash'] and (old['state'], value['state']) in
                    {('prepared', 'binding_sealed'), ('binding_sealed', 'admission_observed')}, 'conflict')
                if old['state'] == 'binding_sealed':
                    _require(all(old[key] == value[key] for key in
                        ('binding', 'route_reservation_hash', 'seal_hash')), 'conflict')
                self.db.execute('UPDATE claims SET state=?,wire=? WHERE claim_id=?',
                    (value['state'], claim.wire_bytes.decode(), value['claim_id']))
        result = self.find(value['request']['case_id'], execution)
        _require(result == claim, 'storage')
        return result

    def close(self):
        if self.closed: return
        if self.db is not None:
            self.db.close()
            self.db = None
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
        self.closed = True


class RegisteredAdmissionOwner:
    """Creator-only capability. A detached claim never grants entry."""
    def __init__(self, release, clock, composition, writer_lease, registered):
        self.release, self.clock, self.composition = release, clock, composition
        self.lease, self.registered = writer_lease, registered
        self.thread = threading.get_ident()
        self.routes = self.claims = self.resources = None
        self.active = None
        self.closed = self.uncertain = False
        self.control_identity = _identity(composition.control_parent, directory=True)
        self.root_identity = _identity(release.resource_root, directory=True)
        self.resource_hash = _hash(json.loads(registered.wire_bytes)['resource'])
        self.release_fields = asdict(release)
        self.registry_records = composition.registry._releases
        self.configuration = dict(kind='registered-host-resource-v1', version=1, host_release_id=release.release_id,
            artifact_hash=registered.artifact_hash, resource_hash=self.resource_hash,
            control_path=str(composition.control_parent), control_identity=list(self.control_identity),
            root_identity=list(self.root_identity), binding_hash=_hash(asdict(composition.binding)),
            review_id=composition.review_id, review_registry_hash=_hash([_grant(grant) for grant in composition.approvals.grants]))
        self.configuration_hash = _hash(self.configuration)

    def check(self):
        _require(type(self) is RegisteredAdmissionOwner and threading.get_ident() == self.thread, 'scope')
        _require(not self.closed and not self.uncertain, 'storage')
        _require(asdict(self.release) == self.release_fields
            and type(self.composition) is LocalAdmissionCompositionV1
            and type(self.composition.binding) is HostExecutableBindingV1
            and type(self.composition.approvals) is ProvisionedReviewResolverV1
            and type(self.composition.registry._releases) is tuple
            and self.composition.registry._releases == self.registry_records, 'scope')
        _require(_hash(asdict(self.composition.binding)) == self.configuration['binding_hash']
            and self.composition.review_id == self.configuration['review_id']
            and _hash([_grant(grant) for grant in self.composition.approvals.grants]) == self.configuration['review_registry_hash'], 'scope')
        self.lease.check()
        _require(_identity(self.composition.control_parent, directory=True) == self.control_identity
            and _identity(self.release.resource_root, directory=True) == self.root_identity, 'storage')
        if hasattr(self, 'marker_identity'):
            path = self.release.resource_root / '.proofkey-registration.json'
            _require(_identity(path) == self.marker_identity, 'storage')
            descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                _require(os.read(descriptor, 16385) == self.marker, 'storage')
            finally:
                os.close(descriptor)

    @_checked
    def open(self, execution):
        self.check()
        marker = self.release.resource_root / '.proofkey-registration.json'
        marked = os.path.lexists(marker)
        control = self.composition.control_parent
        if marked:
            for path in (control / 'routes.sqlite', control / 'host-claims.sqlite',
                    self.release.resource_root / 'journal.sqlite', self.release.resource_root / 'world.sqlite'):
                _identity(path)
        else:
            _require(not any(os.path.lexists(self.release.resource_root / name) for name in
                ('journal.sqlite', 'world.sqlite', 'journal.sqlite-wal', 'world.sqlite-wal',
                 'journal.sqlite-shm', 'world.sqlite-shm', 'journal.sqlite-journal', 'world.sqlite-journal')), 'conflict')
            _require(not any(os.path.lexists(control / (name + suffix))
                for name in ('routes.sqlite', 'host-claims.sqlite')
                for suffix in ('', '-journal', '-wal', '-shm')), 'conflict')
        try:
            self.routes = AdmissionRouteStoreV1(control, database_name='routes.sqlite', registry=self.composition.registry,
                clock=self.clock, execution=control_context(execution, self.clock))
        except BaseException:
            # Its public constructor cannot attest cleanup after a failure.
            self.uncertain = True
            raise
        self.claims = _ClaimStore(self)
        self.claims.open(execution)
        expected = {**self.configuration, 'route_identity': list(_identity(control / 'routes.sqlite')),
            'claim_identity': list(_identity(control / 'host-claims.sqlite'))}
        expected['marker_hash'] = _hash(expected)
        self.marker = _canonical(expected)
        if marked:
            _identity(marker)
            descriptor = os.open(marker, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                _require(os.read(descriptor, 16385) == self.marker, 'conflict')
            finally:
                os.close(descriptor)
        else:
            with self.claims.operation(execution):
                _require(not self.claims.rows(), 'conflict')
            # First adoption requires absent control DBs; B3 just created the
            # exact empty route store under its exclusive owner.
            descriptor = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            try:
                _require(os.write(descriptor, self.marker) == len(self.marker), 'storage')
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            directory = os.open(self.release.resource_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try: os.fsync(directory)
            finally: os.close(directory)
        self.marker_identity = _identity(marker)
        _require(not self.claims.pending(execution), 'pending_claim')

    def attach(self, resources):
        self.resources = resources
        self.store, self.world, self.engine = resources.store, resources.world, resources.engine
        self.gateway = self.engine.gateway
        self.bundle = self.engine.bundle
        self.profile_wire = _canonical(resources.profile.model_dump(mode='json'))

    def associations(self):
        self.check()
        from .gateway import ActionGateway
        from .engine import WorkflowEngine
        from .journal import CaseStore
        from .adapters.world import SimulatedWorld
        from .host import RuntimeResources
        r = self.resources
        _require(type(r) is RuntimeResources and r.admission is self and not r.closed
            and r.store is self.store and r.world is self.world and r.engine is self.engine
            and r._writer_lease is self.lease, 'scope')
        _require(type(self.store) is CaseStore and type(self.world) is SimulatedWorld
            and type(self.engine) is WorkflowEngine and type(self.gateway) is ActionGateway, 'scope')
        _require(self.engine.store is self.store and self.engine.clock is self.clock
            and self.engine.gateway is self.gateway and self.engine.bundle is self.bundle
            and self.gateway.store is self.store and self.gateway.clock is self.clock
            and self.gateway.bundle is self.bundle and self.gateway._admission_owner is self, 'scope')
        _require(_canonical(r.profile.model_dump(mode='json')) == self.profile_wire
            and _canonical(self.engine.profile.model_dump(mode='json')) == self.profile_wire
            and _canonical(self.gateway.profile.model_dump(mode='json')) == self.profile_wire, 'scope')

    def _images(self, execution):
        journal = self.store.capture_retained_state(execution=execution, clock=self.clock)
        source = self.world.capture_retained_state(execution=execution, clock=self.clock)
        return journal, source

    @staticmethod
    def _fresh(snapshot, case_id):
        RetainedStateSnapshotV1(**asdict(snapshot))
        image = json.loads(snapshot.payload)
        for table in image['tables']:
            columns = table['columns']
            for key in ('case_id', 'claimed_case_id'):
                if key in columns:
                    index = columns.index(key)
                    _require(all(row[index] != case_id for row in table['rows']), 'conflict')

    @_checked
    def prepare_entry(self, request, auth, *, execution):
        self.associations()
        _require(self.active is None, 'scope')
        _require(type(request) is CanonicalRequest and type(auth) is AuthContext, 'scope')
        request = _model(request.model_dump(mode='json'), CanonicalRequest)
        auth = _model(auth.model_dump(mode='json'), AuthContext)
        _require(request.kind == self.release.admitted_request_kind
            and request_fingerprint(request) == self.release.admitted_request_fingerprint, 'scope')
        control_context(execution, self.clock)
        _require(not self.claims.pending(execution), 'pending_claim')
        grant = self.composition.approvals.resolve(self.composition.review_id, artifact_hash=self.registered.artifact_hash,
            execution=execution, clock=self.clock)
        journal, source = self._images(control_context(execution, self.clock))
        self._fresh(journal, request.case_id)
        value = dict(kind='registered-host-admission-v1', version=1, claim_id='claim:' + uuid4().hex,
            attempt_id='attempt:' + uuid4().hex, route_id='route:' + uuid4().hex,
            resource_id=self.registered.resource.resource_id, resource_hash=self.resource_hash,
            artifact_hash=self.registered.artifact_hash, release_id=self.composition.binding.registered_release_id,
            review=_grant(grant), request=request.model_dump(mode='json'),
            auth_claim=dict(caller_id=auth.caller_id, proof_digest=_hash(dict(proof_reference=auth.proof_reference))),
            execution=_window(execution), initial_journal_hash=journal.content_hash, initial_source_hash=source.content_hash,
            state='prepared', binding=None, route_reservation_hash=None, seal_hash=None,
            final_journal_hash=None, final_source_hash=None, observation_hash=None)
        value['claim_hash'] = _hash({key: value[key] for key in _ORIGINAL})
        claim = self.claims.write(value, execution, initial=True)
        self.active = (execution, request, auth, claim)
        return claim

    def _guard_parent(self, execution, gateway):
        self.associations()
        _require(self.active is not None and gateway is self.gateway and execution is self.active[0], 'scope')
        _require(_window(execution) == _claim(self.active[3].wire_bytes)['execution'], 'scope')
        _require(self.clock.now() >= execution.captured_at
            and execution.remaining_seconds(self.clock) > 0, 'timeout')

    @_checked
    def guard_execution(self, execution, gateway):
        self._guard_parent(execution, gateway)
        control_context(execution, self.clock)

    @_checked
    def require_entry(self, request, auth):
        self.associations()
        _require(self.active is not None, 'scope')
        execution, original, authentication, claim = self.active
        self.guard_execution(execution, self.gateway)
        control_context(execution, self.clock)
        _require(type(request) is CanonicalRequest and type(auth) is AuthContext
            and request == original and auth == authentication, 'scope')
        _require(self.claims.find(original.case_id, execution) == claim, 'storage')
        return claim.attempt_id

    @_checked
    def seal_before_admit(self, attempt_id, binding, request, checkpoint):
        self.require_entry(request, self.gateway.auth)
        execution, original, auth, claim = self.active
        _require(claim.state == 'prepared' and attempt_id == claim.attempt_id, 'conflict')
        _require(type(binding) is RequestBinding and type(checkpoint) is PhaseCheckpoint
            and checkpoint.binding == binding and binding.supersedes_generation is None
            and checkpoint.profile_version == self.resources.profile.version
            and checkpoint.process_version == self.resources.profile.processes[request.kind].version
            and checkpoint.policy_version == 'v1' and not self.store.has_case(request.case_id), 'conflict')
        attempt = self.store.admission_attempt(attempt_id)
        _require(attempt.state == 'unbound' and attempt.request_hash == _hash(request.model_dump(mode='json'))
            and attempt.claimed_caller_id == auth.caller_id
            and attempt.proof_digest == _hash(dict(proof_reference=auth.proof_reference)), 'conflict')
        value = _claim(claim.wire_bytes)
        route = self.routes.reserve(value['route_id'], attempt_id=attempt_id, release_id=value['release_id'],
            binding=binding, request=request, auth_claim=auth, execution=control_context(execution, self.clock))
        retained = self.routes.get(value['route_id'], execution=control_context(execution, self.clock))
        _require(retained == route and route.binding == binding and route.request == request and route.state == 'reserved', 'storage')
        value.update(state='binding_sealed', binding=binding.model_dump(mode='json'),
            route_reservation_hash=json.loads(route.wire_bytes)['reservation_hash'])
        value['seal_hash'] = _hash(dict(claim_hash=value['claim_hash'], binding=value['binding'],
            route_reservation_hash=value['route_reservation_hash'], artifact_hash=value['artifact_hash']))
        sealed = self.claims.write(value, execution)
        self.active = (execution, original, auth, sealed)

    @_checked
    def run(self, request, auth, *, execution):
        self.prepare_entry(request, auth, execution=execution)
        try:
            result = self.engine.run(request, auth, execution=execution)
            self._guard_parent(execution, self.gateway)
            phase = _observation_context(execution, self.clock)
            claim = self.active[3]
            if claim.state == 'binding_sealed' and self.store.has_case(request.case_id):
                journal, source = self._images(phase)
                self._guard_parent(execution, self.gateway)
                value = _claim(claim.wire_bytes)
                route = self.routes.observe_admitted(value['route_id'], snapshot=journal,
                    execution=phase)
                _require(route.state == 'admission_observed' and route.binding == claim.binding, 'storage')
                value.update(state='admission_observed', final_journal_hash=journal.content_hash,
                    final_source_hash=source.content_hash, observation_hash=route.observation.observation_hash)
                self._guard_parent(execution, self.gateway)
                self.claims.write(value, phase)
                self._guard_parent(execution, self.gateway)
                control_context(phase, self.clock)
            return result
        finally:
            self.active = None

    @_checked
    def claim_for_case(self, case_id, *, execution):
        self.check()
        return self.claims.find(case_id, execution)

    @_checked
    def route_for_case(self, case_id, *, execution):
        claim = self.claim_for_case(case_id, execution=execution)
        return None if claim is None else self.routes.get(_claim(claim.wire_bytes)['route_id'],
            execution=control_context(execution, self.clock))

    def close(self):
        _require(threading.get_ident() == self.thread, 'scope')
        if self.closed: return
        failure = self.uncertain
        if self.claims is not None and not self.uncertain:
            try: self.claims.close()
            except BaseException: failure = True
        if self.routes is not None and not self.uncertain:
            try: self.routes.close()
            except BaseException: failure = True
        self.active = None
        if failure:
            self.uncertain = True
            raise AdmissionCompositionFailure('storage')
        self.closed = True
