"""Closed synthetic release declarations; not runtime selection or review authority."""
import base64
from dataclasses import asdict, dataclass
from functools import wraps
from hashlib import sha256
import json
import posixpath
import re
import unicodedata

from .contracts import EnvironmentProfile
from .profiles import validate_profile

_MIB = 1048576
_BLOBS = ('profile', 'policy', 'source', 'proposal', 'tests', 'regression', 'migration', 'agent', 'dependency')
_POLICY = dict(policy_id='synthetic-test-policy-v1', version='v1', evidence_mode='synthetic',
    native_routes_enabled=False, live_roles=dict(extraction=False, transcription=False, planning=False),
    wait_expiry_seconds=300, internal_case_creation=False, automatic_reminders=False)


class RouteFoundationFailure(ValueError):
    def __init__(self, code):
        if code not in {'invalid','conflict','unregistered','scope','limit','timeout','storage','observation_mismatch'}:
            code = 'invalid'
        self.code = code
        super().__init__(code)


def _checked(function):
    @wraps(function)
    def check(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except RouteFoundationFailure:
            raise
        except (ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError, RecursionError):
            raise RouteFoundationFailure('invalid') from None
    return check


def _require(condition, code='invalid'):
    if not condition:
        raise RouteFoundationFailure(code)


def _canon(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')


def _hash(value):
    return sha256(value).hexdigest()


def _jhash(value):
    return _hash(_canon(value))


def _pairs(items):
    result = {}
    for key, value in items:
        _require(key not in result)
        result[key] = value
    return result


def _parse(raw, limit=8*_MIB, *, canonical=True):
    _require(type(raw) is bytes)
    _require(0 < len(raw) <= limit, 'limit')
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(RouteFoundationFailure('invalid')))
    _require(type(value) is dict)
    if canonical:
        _require(_canon(value) == raw)
    return value


def _keys(value, names):
    _require(type(value) is dict and set(value) == set(names))


def _id(value):
    _require(type(value) is str and bool(value) and any(not c.isspace() for c in value))
    _canon(value)  # reject unencodable surrogate input
    return value


def _digest(value):
    _require(type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None)


def _norm(value):
    return unicodedata.normalize('NFC', value).casefold()


def _name(value):
    _id(value)
    _require(not any(c in value for c in ('\\', ':', '\0')) and
        all(p not in ('', '.', '..') for p in value.split('/')))


def _basename(value):
    _require(type(value) is str and re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}\.sqlite', value) is not None)


def _sequence(values, maximum, *, minimum=0, tuple_only=False):
    _require(type(values) is (tuple if tuple_only else list))
    _require(minimum <= len(values) <= maximum, 'limit')


def _ordered(values, *, names=False):
    for value in values:
        (_name if names else _id)(value)
    _require(list(values) == sorted(values) and
        len(set(map(_norm, values) if names else values)) == len(values))


def _exact(value, cls):
    _require(type(value) is cls)
    return cls(**asdict(value))


def _blob(data):
    return dict(base64=base64.b64encode(data).decode('ascii'), sha256=_hash(data))


def _unblob(value, *, named=False):
    _keys(value, ('name','base64','sha256') if named else ('base64','sha256'))
    if named:
        _name(value['name'])
    raw = value['base64']
    _require(type(raw) is str)
    _require(len(raw) <= 4*((_MIB+2)//3), 'limit')
    data = base64.b64decode(raw, validate=True)
    _require(len(data) <= _MIB, 'limit')
    _require(base64.b64encode(data).decode('ascii') == raw)
    _digest(value['sha256'])
    _require(_hash(data) == value['sha256'])
    return data


@dataclass(frozen=True, slots=True)
class ReleaseBlobV1:
    name: str
    data: bytes

    @_checked
    def __post_init__(self):
        _require(type(self) is ReleaseBlobV1)
        _name(self.name)
        _require(type(self.data) is bytes)
        _require(len(self.data) <= _MIB, 'limit')

    @property
    def sha256(self):
        return _hash(self.data)


@dataclass(frozen=True, slots=True)
class ResourceSetV1:
    resource_id: str
    root_path: str
    root_device: int
    root_inode: int
    journal_name: str
    source_name: str
    account_ids: tuple[str, ...]
    admission_account_scope: str

    @_checked
    def __post_init__(self):
        _require(type(self) is ResourceSetV1)
        _id(self.resource_id)
        _require(type(self.root_path) is str and self.root_path.startswith('/') and
            '\0' not in self.root_path and '\\' not in self.root_path and
            posixpath.normpath(self.root_path) == self.root_path)
        for value in (self.root_device, self.root_inode):
            _require(type(value) is int and 0 <= value < 2**63)
        _basename(self.journal_name); _basename(self.source_name)
        _require(_norm(self.journal_name) != _norm(self.source_name))
        _sequence(self.account_ids, 512, tuple_only=True)
        _ordered(self.account_ids)
        _require(type(self.admission_account_scope) is str and self.admission_account_scope == 'claimed_case_id')


@dataclass(frozen=True, slots=True)
class KnownFactoryV1:
    factory_id: str
    implementation_pins: tuple[tuple[str, str], ...]
    dependency_hash: str
    mode: str

    @_checked
    def __post_init__(self):
        _require(type(self) is KnownFactoryV1)
        _id(self.factory_id); _digest(self.dependency_hash)
        _require(type(self.mode) is str and self.mode == 'offline_synthetic')
        _sequence(self.implementation_pins, 512, minimum=1, tuple_only=True)
        for pair in self.implementation_pins:
            _require(type(pair) is tuple and len(pair) == 2)
            _name(pair[0]); _digest(pair[1])
        _ordered([pair[0] for pair in self.implementation_pins], names=True)


@dataclass(frozen=True, slots=True)
class ReleaseArtifactV1:
    release_id: str
    factory_id: str
    resource_id: str
    profile_json: bytes
    policy_json: bytes
    source_json: bytes
    proposal_json: bytes
    tests_json: bytes
    regression_json: bytes
    migration_json: bytes
    agent_json: bytes
    dependency_json: bytes
    implementations: tuple[ReleaseBlobV1, ...]

    @_checked
    def __post_init__(self):
        _require(type(self) is ReleaseArtifactV1)
        for value in (self.release_id, self.factory_id, self.resource_id): _id(value)
        for name in _BLOBS: _parse(getattr(self, name+'_json'), _MIB)
        _sequence(self.implementations, 512, minimum=1, tuple_only=True)
        for item in self.implementations: _exact(item, ReleaseBlobV1)
        _ordered([item.name for item in self.implementations], names=True)
        # This cheap lower bound rejects impossible envelopes before base64/JSON
        # expansion. The exact encoded bound is independently checked later.
        total=sum(len(getattr(self,name+'_json')) for name in _BLOBS)
        total+=sum(len(item.data) for item in self.implementations)
        _require(total <= 8*_MIB,'limit')


def _declarations(blobs, profile, factory, implementations):
    data = {name:_parse(_unblob(blobs[name]), _MIB) for name in _BLOBS}
    _require(_canon(data['policy']) == _canon(_POLICY))
    _require(_jhash(data['policy']) == profile.policy_hash)
    source = data['source']
    _keys(source, ('kind','mode','source_id','documents'))
    _require(source['kind'] == 'route-source-declaration-v1' and source['mode'] == 'synthetic')
    _id(source['source_id']); _sequence(source['documents'],64,minimum=1)
    ids = []
    for item in source['documents']:
        _keys(item, ('source_id','text')); _id(item['source_id'])
        _require(type(item['text']) is str); ids.append(item['source_id'])
    _require(len(set(ids)) == len(ids))
    proposal = data['proposal']
    _keys(proposal, ('kind','mode','baseline_profile_hash','candidate_profile_hash','diff'))
    _require(proposal['kind'] == 'route-proposal-declaration-v1' and proposal['mode'] == 'synthetic')
    _digest(proposal['baseline_profile_hash'])
    _require(proposal['candidate_profile_hash'] == profile.release_hash)
    _sequence(proposal['diff'],64)
    for item in proposal['diff']: _keys(item, ('path','before','after')); _name(item['path'])
    _ordered([item['path'] for item in proposal['diff']], names=True)
    tests = data['tests']
    _keys(tests, ('kind','mode','cases'))
    _require(tests['kind'] == 'route-test-declaration-v1' and tests['mode'] == 'synthetic')
    _sequence(tests['cases'],128)
    for item in tests['cases']:
        _keys(item, ('case_id','purpose')); _id(item['case_id']); _require(type(item['purpose']) is str)
    case_ids = [item['case_id'] for item in tests['cases']]; _ordered(case_ids)
    regression = data['regression']
    _keys(regression, ('kind','mode','execution','tests_hash','case_ids'))
    _require(regression == dict(kind='route-regression-declaration-v1', mode='synthetic',
        execution='unestablished', tests_hash=blobs['tests']['sha256'], case_ids=case_ids))
    migration = data['migration']
    _keys(migration, ('kind','mode','strategy','affected_contracts'))
    _require(migration['kind'] == 'route-migration-declaration-v1' and migration['mode'] == 'synthetic'
        and migration['strategy'] == 'preserve')
    _sequence(migration['affected_contracts'],128); _ordered(migration['affected_contracts'])
    agent = data['agent']
    _keys(agent, ('kind','mode','authorship','agent_label'))
    _require(agent['kind'] == 'route-agent-declaration-v1' and agent['mode'] == 'synthetic'
        and agent['authorship'] == 'unestablished'); _id(agent['agent_label'])
    dependency = data['dependency']
    _keys(dependency, ('kind','mode','completeness','entries'))
    _require(dependency['kind'] == 'route-closure-declaration-v1' and
        dependency['mode'] == 'synthetic_declaration' and dependency['completeness'] == 'unestablished')
    _sequence(dependency['entries'],512,minimum=1)
    for item in dependency['entries']:
        _keys(item, ('name','sha256','role')); _name(item['name']); _digest(item['sha256'])
        _require(item['role'] in ('code','data','dependency','interpreter','platform','notice'))
    _ordered([item['name'] for item in dependency['entries']], names=True)
    pins = tuple((item['name'], item['sha256']) for item in dependency['entries'])
    _require(pins == factory.implementation_pins == tuple((item['name'],item['sha256']) for item in implementations))
    _require(factory.dependency_hash == blobs['dependency']['sha256'])


def _envelope(raw):
    value = _parse(raw)
    _keys(value, ('kind','version','release_id','mode','factory','resource','blobs','implementations','semantic','artifact_hash'))
    _require(value['kind'] == 'registered-release-v1' and type(value['version']) is int and value['version'] == 1
        and value['mode'] == 'offline_synthetic')
    _id(value['release_id']); _digest(value['artifact_hash'])
    _require(value['artifact_hash'] == _jhash({k:v for k,v in value.items() if k != 'artifact_hash'}))
    resource = value['resource']
    _keys(resource, ('resource_id','root_path','root_device','root_inode','journal_name','source_name','account_ids','admission_account_scope'))
    _sequence(resource['account_ids'],512)
    ResourceSetV1(**{**resource,'account_ids':tuple(resource['account_ids'])})
    factory = value['factory']; _keys(factory, ('factory_id','mode','implementation_pins','dependency_hash'))
    _sequence(factory['implementation_pins'],512,minimum=1)
    for pin in factory['implementation_pins']: _keys(pin, ('name','sha256'))
    registered = KnownFactoryV1(factory['factory_id'],tuple((p['name'],p['sha256']) for p in factory['implementation_pins']),
        factory['dependency_hash'],factory['mode'])
    _keys(value['blobs'], _BLOBS)
    _sequence(value['implementations'],512,minimum=1)
    for item in value['implementations']: _unblob(item,named=True)
    _ordered([item['name'] for item in value['implementations']], names=True)
    profile_data = _parse(_unblob(value['blobs']['profile']),_MIB)
    profile = validate_profile(EnvironmentProfile.model_validate(profile_data))
    _require(_canon(profile.model_dump(mode='json')) == _canon(profile_data))
    accounts = sorted({c.shared_limits.account_id for c in profile.capabilities.values() if c.shared_limits.account_id is not None})
    _require(resource['account_ids'] == accounts)
    _declarations(value['blobs'],profile,registered,value['implementations'])
    _require(value['semantic'] == dict(profile_hash=profile.release_hash,
        process_hash=_jhash(profile_data['processes']), capabilities_hash=_jhash(profile_data['capabilities']), policy_hash=profile.policy_hash))
    return value


@dataclass(frozen=True, slots=True)
class RegisteredReleaseV1:
    wire_bytes: bytes

    @_checked
    def __post_init__(self):
        _require(type(self) is RegisteredReleaseV1)
        _envelope(self.wire_bytes)

    @property
    def artifact_hash(self): return _parse(self.wire_bytes)['artifact_hash']

    @property
    def profile(self):
        return EnvironmentProfile.model_validate(_parse(_unblob(_parse(self.wire_bytes)['blobs']['profile']),_MIB))

    @property
    def resource(self):
        value = _parse(self.wire_bytes)['resource']
        return ResourceSetV1(**{**value,'account_ids':tuple(value['account_ids'])})

    @property
    def factory(self):
        value = _parse(self.wire_bytes)['factory']
        return KnownFactoryV1(value['factory_id'],tuple((p['name'],p['sha256']) for p in value['implementation_pins']),
            value['dependency_hash'],value['mode'])


@dataclass(frozen=True, slots=True, init=False)
class ReleaseRegistryV1:
    _releases: tuple[tuple[str, bytes], ...]

    @_checked
    def __init__(self, *, artifacts: tuple[ReleaseArtifactV1, ...],
                 factories: tuple[KnownFactoryV1, ...], resources: tuple[ResourceSetV1, ...]):
        _require(type(self) is ReleaseRegistryV1)
        for values in (artifacts,factories,resources): _sequence(values,32,minimum=1,tuple_only=True)
        for item in artifacts: _require(type(item) is ReleaseArtifactV1)
        for item in factories: _exact(item,KnownFactoryV1)
        for item in resources: _exact(item,ResourceSetV1)
        _require(len({f.factory_id for f in factories}) == len(factories))
        _require(len({r.resource_id for r in resources}) == len(resources))
        _require(len({a.release_id for a in artifacts}) == len(artifacts))
        _require({a.factory_id for a in artifacts} == {f.factory_id for f in factories})
        _require({a.resource_id for a in artifacts} == {r.resource_id for r in resources})
        built, total = [], 0
        for artifact in artifacts:
            _require(type(artifact) is ReleaseArtifactV1)
            # Reconstruct without asdict: nested frozen blob types must remain exact.
            ReleaseArtifactV1(**{k:getattr(artifact,k) for k in artifact.__dataclass_fields__})
            factory = next(f for f in factories if f.factory_id == artifact.factory_id)
            resource = next(r for r in resources if r.resource_id == artifact.resource_id)
            factory_data = asdict(factory)
            factory_data['implementation_pins'] = [dict(name=n,sha256=h) for n,h in factory.implementation_pins]
            resource_data = asdict(resource); resource_data['account_ids'] = list(resource.account_ids)
            profile = _parse(artifact.profile_json,_MIB)
            value = dict(kind='registered-release-v1',version=1,release_id=artifact.release_id,mode='offline_synthetic',
                factory=factory_data,resource=resource_data,
                blobs={name:_blob(getattr(artifact,name+'_json')) for name in _BLOBS},
                implementations=[dict(name=b.name,**_blob(b.data)) for b in artifact.implementations],
                semantic=dict(profile_hash=profile['release_hash'],process_hash=_jhash(profile['processes']),
                    capabilities_hash=_jhash(profile['capabilities']),policy_hash=_jhash(_parse(artifact.policy_json,_MIB))))
            value['artifact_hash'] = _jhash(value)
            wire = _canon(value); total += len(wire)
            _require(total <= 32*_MIB,'limit')
            RegisteredReleaseV1(wire)
            built.append((artifact.release_id,wire))
        object.__setattr__(self,'_releases',tuple(sorted(built)))

    @_checked
    def resolve(self, release_id: str) -> RegisteredReleaseV1:
        _require(type(self) is ReleaseRegistryV1); _id(release_id)
        for name, raw in self._releases:
            if name == release_id: return RegisteredReleaseV1(raw)
        raise RouteFoundationFailure('unregistered')

    @_checked
    def resource(self, resource_id: str) -> ResourceSetV1:
        _require(type(self) is ReleaseRegistryV1)
        _id(resource_id)
        for _,raw in self._releases:
            item = RegisteredReleaseV1(raw).resource
            if item.resource_id == resource_id: return item
        raise RouteFoundationFailure('unregistered')
