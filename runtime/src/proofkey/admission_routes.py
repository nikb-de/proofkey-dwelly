"""Original-route bookkeeping only; never admission or disclosure authority."""
from contextlib import contextmanager
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timedelta, timezone
import fcntl
import math
import os
from pathlib import Path
import re
import sqlite3
import stat
import threading

from .admission import AdmissionAttempt
from .contracts import AuthContext, CanonicalRequest, RequestBinding
from .execution import ExecutionContext
from .retained_state import RetainedStateClock, RetainedStateSnapshotV1
from .registered_releases import (RouteFoundationFailure, ReleaseRegistryV1, RegisteredReleaseV1,
    _require, _checked, _canon, _parse, _keys, _id, _digest, _jhash, _ordered, _norm, _basename)

_IDENTITY = ('case_id','object_id','principal_id','request_id','request_revision','consent_revision')
_INDEX = ('reservation_id','attempt_id','resource_id','case_id','generation','release_id','state')
_RESERVATION_EXCLUDE = ('reservation_hash','state','reserved_at','observation','record_hash')
# Public journal wire columns, not imported private encoder/schema internals.
_JOURNAL_COLUMNS = {
    'admission_accounts': ('claimed_case_id','account_json','revision'),
    'admission_attempts': ('attempt_id','claimed_case_id','dedup_hash','attempt_json','state'),
    'admission_audit': ('sequence','claimed_case_id','event_json'),
    'admission_entries': ('entry_id','attempt_id','claimed_case_id','charge_generation','lease_json','state'),
    'audit': ('sequence','case_id','event_json'),
    'campaigns': ('permit_hash','campaign_id','permit_json','consumed_json','revision'),
    'cases': ('case_id','checkpoint_json','revision'),
    'entries': ('entry_id','case_id','generation','kind','subject_id','lease_json','state'),
    'intents': ('action_id','case_id','generation','fingerprint','intent_json','dispatch_state','verification_json'),
    'invocations': ('invocation_id','case_id','generation','role','permit_hash','reservation_json','state','receipt_json'),
    'original_requests': ('case_id','generation','request_json'),
    'requests': ('case_id','generation','binding_json','versions_json','stop_requested','request_id','request_revision','consent_revision','fingerprint'),
    'results': ('case_id','generation','result_json'),
    'schema_meta': ('version',),
    'transfers': ('transfer_id','case_id','generation','transfer_json','state'),
    'waits': ('question_id','case_id','generation','wait_json'),
}
_SCHEMA_HASH = 'b351849ccaa305758b1a2c15e75de09a6a4bf2bdd4dbe8e891046ceaa35aee56'
_DDL = (
    'CREATE TABLE meta(singleton INTEGER PRIMARY KEY CHECK(singleton=1),version INTEGER NOT NULL CHECK(version=1),registry_hash TEXT NOT NULL)',
    'CREATE TABLE releases(release_id TEXT PRIMARY KEY NOT NULL,artifact_hash TEXT NOT NULL,artifact_json TEXT NOT NULL)',
    "CREATE TABLE routes(reservation_id TEXT PRIMARY KEY NOT NULL,attempt_id TEXT NOT NULL UNIQUE,resource_id TEXT NOT NULL,case_id TEXT NOT NULL,generation TEXT NOT NULL,release_id TEXT NOT NULL REFERENCES releases(release_id),state TEXT NOT NULL CHECK(state IN ('reserved','admission_observed')),record_json TEXT NOT NULL,UNIQUE(resource_id,case_id,generation))",
)


def _stamp(value):
    _require(type(value) is datetime and value.utcoffset() is not None)
    return value.astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00','Z')


def _time(value):
    _require(type(value) is str and re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{6}Z',value) is not None)
    result = datetime.strptime(value,'%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)
    _require(_stamp(result) == value)
    return result


def _model(value, cls):
    _keys(value,cls.model_fields)
    result = cls.model_validate(value)
    _require(_canon(value) == _canon(result.model_dump(mode='json')))
    return result


def _input(value, cls):
    _require(type(value) is cls)
    # The caller's public model may have been object.__setattr__-modified.
    raw = _canon(value.model_dump(mode='json'))
    _require(len(raw) <= 262144, 'limit')
    return _model(_parse(raw,262144),cls)


def _observation(value):
    _keys(value,('kind','snapshot_kind','schema_version','schema_hash','content_hash','table_counts',
        'total_rows','captured_at','finished_at','elapsed_seconds','observation_hash'))
    _require(value['kind'] == 'journal-admission-observation-v1' and
        value['snapshot_kind'] == 'case-store-retained-state-v1' and
        type(value['schema_version']) is int and value['schema_version'] == 1 and value['schema_hash'] == _SCHEMA_HASH)
    for key in ('schema_hash','content_hash','observation_hash'): _digest(value[key])
    counts=value['table_counts']
    _require(type(counts) is list and len(counts) == len(_JOURNAL_COLUMNS))
    for item,name in zip(counts,_JOURNAL_COLUMNS):
        _require(type(item) is list and len(item) == 2 and item[0] == name and
            type(item[1]) is int and 0 <= item[1] <= 4096)
    _require(dict(counts)['schema_meta'] == 1 and type(value['total_rows']) is int and
        1 <= value['total_rows'] <= 4096 and sum(item[1] for item in counts) == value['total_rows'])
    start,finish = _time(value['captured_at']),_time(value['finished_at'])
    _require(timedelta(0) <= finish-start <= timedelta(seconds=5))
    elapsed=value['elapsed_seconds']
    _require(type(elapsed) is float and math.isfinite(elapsed) and 0 <= elapsed <= 5.0)
    _require(value['observation_hash'] == _jhash({k:v for k,v in value.items() if k != 'observation_hash'}))


def _route(raw):
    value=_parse(raw,262144)
    _keys(value,('kind','version','reservation_id','attempt_id','release_id','artifact_hash','resource_id','resource_hash',
        'account_ids','case_id','generation','binding','request','binding_hash','request_hash','business_fingerprint',
        'auth_claim','auth_claim_hash','dedup_hash','reservation_hash','state','reserved_at','observation','record_hash'))
    _require(value['kind'] == 'original-admission-route-v1' and type(value['version']) is int and value['version'] == 1)
    for key in ('reservation_id','attempt_id','release_id','resource_id','case_id','generation'): _id(value[key])
    for key in ('artifact_hash','resource_hash','binding_hash','request_hash','business_fingerprint',
            'auth_claim_hash','dedup_hash','reservation_hash','record_hash'): _digest(value[key])
    _require(type(value['account_ids']) is list and len(value['account_ids']) <= 512)
    _ordered(value['account_ids'])
    binding=_model(value['binding'],RequestBinding); request=_model(value['request'],CanonicalRequest)
    _require(all(getattr(binding,k) == getattr(request,k) for k in _IDENTITY))
    _require(binding.case_id == value['case_id'] and binding.generation == value['generation'])
    business=_jhash({k:value['request'][k] for k in ('kind','consent_mode','arguments')})
    _require(business == binding.fingerprint == value['business_fingerprint'])
    _require(value['binding_hash'] == _jhash(value['binding']) and value['request_hash'] == _jhash(value['request']))
    claim=value['auth_claim']; _keys(claim,('caller_id','proof_digest')); _id(claim['caller_id']); _digest(claim['proof_digest'])
    _require(value['auth_claim_hash'] == _jhash(claim))
    _require(value['dedup_hash'] == _jhash({**claim,'claim':{k:value['request'][k] for k in _IDENTITY},'business_fingerprint':business}))
    _time(value['reserved_at'])
    _require(value['state'] in ('reserved','admission_observed'))
    if value['state'] == 'reserved': _require(value['observation'] is None)
    else: _observation(value['observation'])
    _require(value['reservation_hash'] == _jhash({k:v for k,v in value.items() if k not in _RESERVATION_EXCLUDE}))
    _require(value['record_hash'] == _jhash({k:v for k,v in value.items() if k != 'record_hash'}))
    return value


@dataclass(frozen=True, slots=True)
class RouteRecordV1:
    wire_bytes: bytes

    @_checked
    def __post_init__(self):
        _require(type(self) is RouteRecordV1)
        _route(self.wire_bytes)

    @property
    def binding(self): return RequestBinding.model_validate(_parse(self.wire_bytes,262144)['binding'])
    @property
    def request(self): return CanonicalRequest.model_validate(_parse(self.wire_bytes,262144)['request'])
    @property
    def state(self): return _parse(self.wire_bytes,262144)['state']
    @property
    def artifact_hash(self): return _parse(self.wire_bytes,262144)['artifact_hash']
    @property
    def observation(self):
        value=_parse(self.wire_bytes,262144)['observation']
        return None if value is None else ObservationV1(_canon(value))


@dataclass(frozen=True, slots=True)
class ObservationV1:
    wire_bytes: bytes

    @_checked
    def __post_init__(self):
        _require(type(self) is ObservationV1)
        _observation(_parse(self.wire_bytes,262144))

    @property
    def observation_hash(self): return _parse(self.wire_bytes,262144)['observation_hash']
    @property
    def captured_at(self): return _time(_parse(self.wire_bytes,262144)['captured_at'])
    @property
    def finished_at(self): return _time(_parse(self.wire_bytes,262144)['finished_at'])
    @property
    def elapsed_seconds(self): return _parse(self.wire_bytes,262144)['elapsed_seconds']


@dataclass(frozen=True, slots=True)
class RouteLimitsV1:
    max_routes: int = 4096
    max_row_bytes: int = 262144
    max_release_bytes: int = 33554432
    max_routes_bytes: int = 8388608
    max_operation_seconds: float = 5.0
    max_sqlite_steps: int = 1000000

    @_checked
    def __post_init__(self):
        _require(type(self) is RouteLimitsV1)
        for key,ceiling in (('max_routes',4096),('max_row_bytes',262144),('max_release_bytes',33554432),
                ('max_routes_bytes',8388608),('max_sqlite_steps',1000000)):
            value=getattr(self,key); _require(type(value) is int and 0 < value <= ceiling)
        _require(type(self.max_operation_seconds) is float and math.isfinite(self.max_operation_seconds)
            and 0 < self.max_operation_seconds <= 5.0)


def _full_route(value):
    return _canon({**{key:value[key] for key in _INDEX},'record':value})


def _file_identity(path, *, directory=False):
    item=os.lstat(path)
    _require((stat.S_ISDIR(item.st_mode) if directory else stat.S_ISREG(item.st_mode)) and
        not stat.S_ISLNK(item.st_mode) and (directory or item.st_nlink == 1),'storage')
    return item.st_dev,item.st_ino


class AdmissionRouteStoreV1:
    """Exclusive local control store. Never opens declared resource contents."""
    @_checked
    def __init__(self, parent: Path, *, database_name: str, registry: ReleaseRegistryV1,
                 clock: RetainedStateClock, execution: ExecutionContext,
                 limits: RouteLimitsV1 = RouteLimitsV1()):
        self._owner=threading.get_ident(); self._busy=False; self._closed=False
        self._db=None; self._lock_fd=None; self._db_fd=None
        self._clock=clock; self._limits=limits; self._context=execution
        self._steps=0; self._progress_failure=None
        try:
            _require(type(registry) is ReleaseRegistryV1 and type(limits) is RouteLimitsV1)
            self._limits=RouteLimitsV1(**asdict(limits))
            _require(type(registry._releases) is tuple and 0 < len(registry._releases) <= 32)
            total=0
            for pair in registry._releases:
                _require(type(pair) is tuple and len(pair) == 2 and type(pair[1]) is bytes)
                _id(pair[0]); total+=len(pair[1])
                _require(len(pair[1]) <= 8388608 and total <= 33554432,'limit')
            self._registered=tuple((name,RegisteredReleaseV1(raw)) for name,raw in registry._releases)
            _require(tuple(name for name,_ in self._registered) == tuple(sorted(set(name for name,_ in self._registered))))
            resources={}; factories={}
            for name,item in self._registered:
                body=_parse(item.wire_bytes)
                _require(name == body['release_id'])
                for key,collection in (('resource',resources),('factory',factories)):
                    identity=body[key][key+'_id']
                    _require(identity not in collection or collection[identity] == body[key])
                    collection[identity]=body[key]
            self._registry_hash=_jhash(dict(kind='route-registry-v1',version=1,
                releases=[dict(release_id=name,artifact_hash=item.artifact_hash) for name,item in self._registered]))
            self._resources=tuple({item.resource.resource_id:item.resource for _,item in self._registered}.values())
            self._check_time()
            _require(type(parent) is type(Path()) and parent.is_absolute(),'scope')
            # Reject symlink components before resolving ordinary dot segments.
            for ancestor in (parent,*parent.parents):
                self._check_time()
                _require(not stat.S_ISLNK(os.lstat(ancestor).st_mode),'scope')
            parent=parent.resolve(strict=True)
            self._parent=parent
            prohibited=tuple(path.resolve(strict=True) for path in (Path('/'),Path.home(),Path.cwd()))
            self._parent_id=_file_identity(parent,directory=True)
            _require(parent not in prohibited and not (parent/'.git').exists(),'scope')
            _require(self._parent_id not in tuple(_file_identity(path,directory=True) for path in prohibited),'scope')
            _basename(database_name)
            self._path=parent/database_name; self._lock_path=parent/(database_name+'.owner-lock')
            self._paths(resource_only=True)
            self._lock_fd=os.open(self._lock_path,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
            lock_stat=os.fstat(self._lock_fd)
            _require(stat.S_ISREG(lock_stat.st_mode) and lock_stat.st_nlink == 1 and stat.S_IMODE(lock_stat.st_mode) == 0o600,'storage')
            self._lock_id=(lock_stat.st_dev,lock_stat.st_ino)
            _require(_file_identity(self._lock_path) == self._lock_id,'storage')
            fcntl.flock(self._lock_fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            fresh=not os.path.lexists(self._path)
            if not fresh: _file_identity(self._path)
            self._db_fd=os.open(self._path,os.O_RDWR|os.O_NOFOLLOW|(os.O_CREAT|os.O_EXCL if fresh else 0),0o600)
            file_stat=os.fstat(self._db_fd); self._db_id=(file_stat.st_dev,file_stat.st_ino)
            self._paths()
            self._db=sqlite3.connect(self._path.as_uri()+'?mode=rw',uri=True,timeout=0,isolation_level=None)
            self._db.execute('PRAGMA foreign_keys=ON')
            _require(self._db.execute('PRAGMA journal_mode').fetchone() == ('delete',),'storage')
            if fresh: self._db.execute('PRAGMA synchronous=FULL')
            self._db.execute('PRAGMA query_only=ON')
            with self._operation(execution,write=fresh,initial=True):
                if fresh:
                    for ddl in _DDL: self._db.execute(ddl)
                    self._db.execute('INSERT INTO meta VALUES(1,1,?)',(self._registry_hash,))
                    for name,item in self._registered:
                        self._db.execute('INSERT INTO releases VALUES(?,?,?)',(name,item.artifact_hash,item.wire_bytes.decode('utf-8')))
                self._validate_store()
        except BaseException as error:
            self._release_handles(); self._closed=True
            if isinstance(error,RouteFoundationFailure): raise
            if isinstance(error,Exception): raise RouteFoundationFailure('storage') from None
            raise

    def _check_time(self):
        value=self._context
        _require(type(value) is ExecutionContext,'scope')
        ExecutionContext(value.deadline,value.captured_at,value.captured_monotonic,value.monotonic_deadline)
        _require(0 < (value.deadline-value.captured_at).total_seconds() <= self._limits.max_operation_seconds,'scope')
        try:
            now=self._clock.now(); mono=self._clock.monotonic()
        except Exception:
            raise RouteFoundationFailure('scope') from None
        _require(type(now) is datetime and now.utcoffset() is not None and type(mono) in (int,float) and math.isfinite(mono),'scope')
        _require(now >= value.captured_at and mono >= value.captured_monotonic,'scope')
        _require(now < value.deadline and mono < value.monotonic_deadline,'timeout')
        if hasattr(self,'_last_clock'):
            _require(now >= self._last_clock[0] and mono >= self._last_clock[1],'scope')
        self._last_clock=(now,float(mono))
        return now

    def _paths(self, *, resource_only=False):
        _require(_file_identity(self._parent,directory=True) == self._parent_id,'storage')
        own_paths=(self._parent,self._path,self._lock_path)
        normalized=[_norm(os.path.abspath(p)) for p in own_paths]
        _require(len(set(normalized)) == 3,'scope')
        own_ids=[]
        for path in own_paths[1:]:
            if os.path.lexists(path): own_ids.append(_file_identity(path))
        _require(len(set(own_ids)) == len(own_ids),'storage')
        for resource in self._resources:
            root=Path(resource.root_path)
            for index,path in enumerate((root,root/resource.journal_name,root/resource.source_name)):
                _require(_norm(os.path.abspath(path)) not in normalized,'scope')
                if os.path.lexists(path):
                    identity=_file_identity(path,directory=index == 0)
                    _require(identity not in own_ids and identity != self._parent_id,'storage')
                    if index == 0: _require(identity == (resource.root_device,resource.root_inode),'storage')
        if not resource_only:
            _require(_file_identity(self._lock_path) == self._lock_id and _file_identity(self._path) == self._db_id,'storage')

    def _progress(self):
        self._steps+=1
        try:
            _require(self._steps <= self._limits.max_sqlite_steps,'limit')
            if self._steps % 32 == 0: self._check_time()
            return 0
        except Exception as error:
            self._progress_failure=error if isinstance(error,RouteFoundationFailure) else RouteFoundationFailure('scope')
            return 1

    @contextmanager
    def _operation(self, execution, *, write=False, initial=False):
        _require(threading.get_ident() == self._owner and not self._busy and not self._closed,'scope')
        self._busy=True; self._context=execution; self._steps=0; self._progress_failure=None
        failure=None; cleanup_failed=False
        try:
            self._check_time(); self._paths()
            self._db.set_progress_handler(self._progress,1)
            if write:
                self._db.execute('PRAGMA query_only=OFF')
                self._db.execute('BEGIN IMMEDIATE')
            else:
                self._db.execute('BEGIN')
            if not initial: self._validate_store()
            yield
            self._check_time(); self._paths()
            self._db.execute('COMMIT')
            self._check_time(); self._paths()
        except RouteFoundationFailure as error:
            failure=error
        except (sqlite3.Error,OSError):
            failure=self._progress_failure or RouteFoundationFailure('storage')
        except (TypeError,ValueError,KeyError,IndexError,AttributeError,RecursionError,OverflowError):
            failure=RouteFoundationFailure('invalid')
        except BaseException as error:
            failure=error
        finally:
            try:
                # Each restoration is attempted even if a preceding phase fails.
                for phase in ('progress','rollback','query_only'):
                    try:
                        if phase == 'progress': self._db.set_progress_handler(None,0)
                        elif phase == 'rollback':
                            if self._db.in_transaction: self._db.execute('ROLLBACK')
                        else: self._db.execute('PRAGMA query_only=ON')
                    except BaseException as error:
                        cleanup_failed=True
                        if not isinstance(error,Exception) and failure is None: failure=error
            finally:
                try:
                    if cleanup_failed:
                        # An uncertain connection cannot serve another operation.
                        self._closed=True
                        self._release_handles()
                finally:
                    self._busy=False; self._context=None
        if failure is not None: raise failure from None
        if cleanup_failed: raise RouteFoundationFailure('storage') from None

    def _release_handles(self):
        failed=False
        if self._db is not None:
            try: self._db.close()
            except Exception: failed=True
            self._db=None
        for name in ('_db_fd','_lock_fd'):
            descriptor=getattr(self,name,None)
            if descriptor is not None:
                try: os.close(descriptor)
                except OSError: failed=True
                setattr(self,name,None)
        return failed

    def _schema(self):
        db=self._db
        _require(db.execute('SELECT count(*) FROM sqlite_master').fetchone()[0] == 7,'storage')
        _require(db.execute('SELECT coalesce(max(length(CAST(sql AS BLOB))),0) FROM sqlite_master').fetchone()[0] <= 1024,'storage')
        actual=tuple(db.execute('SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name'))
        expected=[('table',name,name,ddl) for name,ddl in zip(('meta','releases','routes'),_DDL)]
        expected.extend(('index',f'sqlite_autoindex_{table}_{number}',table,None) for table,number in
            (('releases',1),('routes',1),('routes',2),('routes',3)))
        _require(actual == tuple(sorted(expected)),'storage')
        definitions={
            'meta': [('singleton','INTEGER',0,1),('version','INTEGER',1,0),('registry_hash','TEXT',1,0)],
            'releases': [('release_id','TEXT',1,1),('artifact_hash','TEXT',1,0),('artifact_json','TEXT',1,0)],
            'routes': [(key,'TEXT',1,1 if key == 'reservation_id' else 0) for key in (*_INDEX,'record_json')],
        }
        expected_indices={'meta':{},'releases':{'sqlite_autoindex_releases_1':('pk',('release_id',))},
            'routes':{'sqlite_autoindex_routes_1':('pk',('reservation_id',)),
                      'sqlite_autoindex_routes_2':('u',('attempt_id',)),
                      'sqlite_autoindex_routes_3':('u',('resource_id','case_id','generation'))}}
        for table,definition in definitions.items():
            self._check_time()
            _require(tuple(db.execute(f'PRAGMA table_info({table})')) == tuple(
                (i,name,kind,nonnull,None,pk) for i,(name,kind,nonnull,pk) in enumerate(definition)),'storage')
            foreign=tuple(db.execute(f'PRAGMA foreign_key_list({table})'))
            wanted=((0,0,'releases','release_id','release_id','NO ACTION','NO ACTION','NONE'),) if table == 'routes' else ()
            _require(foreign == wanted,'storage')
            indices=tuple(db.execute(f'PRAGMA index_list({table})'))
            _require(len(indices) == len(expected_indices[table]),'storage')
            for sequence,name,unique,origin,partial in indices:
                _require(name in expected_indices[table] and unique == 1 and partial == 0,'storage')
                expected_origin,columns=expected_indices[table][name]
                _require(origin == expected_origin,'storage')
                info=tuple(db.execute(f'PRAGMA index_info({name})'))
                column_ids={column:i for i,(column,*_) in enumerate(definition)}
                _require(info == tuple((i,column_ids[column],column) for i,column in enumerate(columns)),'storage')
        _require(tuple(db.execute('PRAGMA foreign_keys')) == ((1,),),'storage')
        _require(tuple(db.execute('PRAGMA journal_mode')) == (('delete',),),'storage')

    def _preflight(self, table, columns, count_limit, lengths, total_limit=None):
        count=self._db.execute(f'SELECT count(*) FROM {table}').fetchone()[0]
        _require(count <= count_limit,'limit')
        for column,kind in columns:
            _require(self._db.execute(f'SELECT count(*) FROM {table} WHERE typeof({column}) != ?',
                (kind,)).fetchone()[0] == 0,'storage')
        for column,limit in lengths:
            maximum=self._db.execute(f'SELECT coalesce(max(length(CAST({column} AS BLOB))),0) FROM {table}').fetchone()[0]
            _require(maximum <= limit,'limit')
        if total_limit is not None:
            expression='+'.join(f'length(CAST({column} AS BLOB))' for column,_ in columns)
            total=self._db.execute(f'SELECT coalesce(sum({expression}),0) FROM {table}').fetchone()[0]
            _require(total <= total_limit,'limit')
        return count

    def _validate_store(self):
        self._schema()
        _require(self._preflight('meta',(('singleton','integer'),('version','integer'),('registry_hash','text')),1,(('registry_hash',64),)) == 1,'storage')
        _require(tuple(self._db.execute('SELECT * FROM meta')) == ((1,1,self._registry_hash),),'storage')
        count=self._preflight('releases',tuple((x,'text') for x in ('release_id','artifact_hash','artifact_json')),32,
            (('release_id',8*1048576),('artifact_hash',64),('artifact_json',8*1048576)),self._limits.max_release_bytes)
        _require(count == len(self._registered),'storage')
        cursor=self._db.execute('SELECT release_id,artifact_hash,artifact_json FROM releases ORDER BY release_id')
        total=0; seen=0
        while batch:=cursor.fetchmany(32):
            for name,digest,raw in batch:
                self._check_time()
                _require(seen < len(self._registered),'storage')
                registered_name,item=self._registered[seen]; seen+=1
                _require(name == registered_name and digest == item.artifact_hash and raw.encode('utf-8') == item.wire_bytes,'storage')
                encoded=_canon(dict(release_id=name,artifact_hash=digest,artifact=_parse(raw.encode('utf-8'))))
                _require(len(encoded) <= 8*1048576,'limit'); total+=len(encoded)
                _require(total <= self._limits.max_release_bytes,'limit')
        self._preflight('routes',tuple((x,'text') for x in (*_INDEX,'record_json')),self._limits.max_routes,
            tuple((x,self._limits.max_row_bytes) for x in (*_INDEX,'record_json')),self._limits.max_routes_bytes)
        _require(tuple(self._db.execute('PRAGMA foreign_key_check')) == (),'storage')
        cursor=self._db.execute('SELECT '+','.join((*_INDEX,'record_json'))+' FROM routes ORDER BY reservation_id')
        total=0; records=[]
        while batch:=cursor.fetchmany(32):
            for row in batch:
                self._check_time()
                value=_route(row[-1].encode('utf-8'))
                _require(tuple(value[key] for key in _INDEX) == row[:-1],'storage')
                self._membership(value)
                size=len(_full_route(value)); total+=size
                _require(size <= self._limits.max_row_bytes and total <= self._limits.max_routes_bytes,'limit')
                records.append(value)
        return records,total

    def _release(self, release_id):
        _id(release_id)
        for name,item in self._registered:
            if name == release_id: return item
        raise RouteFoundationFailure('unregistered')

    def _membership(self, value):
        item=self._release(value['release_id']); resource=item.resource
        _require(value['artifact_hash'] == item.artifact_hash and value['resource_id'] == resource.resource_id and
            value['resource_hash'] == _jhash(_parse(item.wire_bytes)['resource']) and value['account_ids'] == list(resource.account_ids),'storage')

    @_checked
    def reserve(self, reservation_id: str, *, attempt_id: str, release_id: str,
                binding: RequestBinding, request: CanonicalRequest, auth_claim: AuthContext,
                execution: ExecutionContext) -> RouteRecordV1:
        with self._operation(execution,write=True):
            _id(reservation_id); _id(attempt_id)
            item=self._release(release_id); binding=_input(binding,RequestBinding); request=_input(request,CanonicalRequest)
            auth_claim=_input(auth_claim,AuthContext)
            resource=item.resource; body=_parse(item.wire_bytes)
            claim=dict(caller_id=auth_claim.caller_id,proof_digest=_jhash(dict(proof_reference=auth_claim.proof_reference)))
            request_data=request.model_dump(mode='json'); binding_data=binding.model_dump(mode='json')
            value=dict(kind='original-admission-route-v1',version=1,reservation_id=reservation_id,attempt_id=attempt_id,
                release_id=release_id,artifact_hash=item.artifact_hash,resource_id=resource.resource_id,
                resource_hash=_jhash(body['resource']),account_ids=list(resource.account_ids),case_id=binding.case_id,generation=binding.generation,
                binding=binding_data,request=request_data,binding_hash=_jhash(binding_data),request_hash=_jhash(request_data),
                business_fingerprint=binding.fingerprint,auth_claim=claim,auth_claim_hash=_jhash(claim),
                dedup_hash=_jhash({**claim,'claim':{k:request_data[k] for k in _IDENTITY},'business_fingerprint':binding.fingerprint}),
                state='reserved',reserved_at=_stamp(self._check_time()),observation=None)
            value['reservation_hash']=_jhash({k:v for k,v in value.items() if k not in _RESERVATION_EXCLUDE})
            value['record_hash']=_jhash(value); candidate=RouteRecordV1(_canon(value))
            records,total=self._validate_store()
            for old in records:
                if old['reservation_id'] == reservation_id:
                    _require(old['reservation_hash'] == value['reservation_hash'],'conflict')
                    return RouteRecordV1(_canon(old))
                _require(old['attempt_id'] != attempt_id and (old['resource_id'],old['case_id'],old['generation']) !=
                    (resource.resource_id,binding.case_id,binding.generation),'conflict')
            size=len(_full_route(value))
            _require(len(records) < self._limits.max_routes and size <= self._limits.max_row_bytes and
                total+size <= self._limits.max_routes_bytes,'limit')
            self._db.execute('INSERT INTO routes VALUES(?,?,?,?,?,?,?,?)',tuple(value[k] for k in _INDEX)+(candidate.wire_bytes.decode('utf-8'),))
            return candidate

    @_checked
    def get(self, reservation_id: str, *, execution: ExecutionContext) -> RouteRecordV1 | None:
        with self._operation(execution):
            _id(reservation_id)
            rows,_=self._validate_store()
            return next((RouteRecordV1(_canon(row)) for row in rows if row['reservation_id'] == reservation_id),None)

    @_checked
    def for_generation(self, resource_id: str, case_id: str, generation: str, *,
                       execution: ExecutionContext) -> RouteRecordV1 | None:
        with self._operation(execution):
            for value in (resource_id,case_id,generation): _id(value)
            _require(any(resource.resource_id == resource_id for resource in self._resources),'unregistered')
            rows,_=self._validate_store()
            return next((RouteRecordV1(_canon(row)) for row in rows if
                (row['resource_id'],row['case_id'],row['generation']) == (resource_id,case_id,generation)),None)

    def _join_snapshot(self, snapshot, route):
        _require(type(snapshot) is RetainedStateSnapshotV1)
        _require(type(snapshot.payload) is bytes and 0 < len(snapshot.payload) <= 4194304,'limit')
        # Reconstruct only through the public immutable envelope API.
        snapshot=RetainedStateSnapshotV1(**{f.name:getattr(snapshot,f.name) for f in fields(RetainedStateSnapshotV1)})
        image=_parse(snapshot.payload,4194304)
        tables=image['tables']
        _require(tuple(table['name'] for table in tables) == tuple(_JOURNAL_COLUMNS))
        for table in tables:
            self._check_time()
            _require(table['columns'] == list(_JOURNAL_COLUMNS[table['name']]))
        data={table['name']:table['rows'] for table in tables}
        def one(table, predicate):
            selected=[]
            for row in data[table]:
                self._check_time()
                if predicate(row): selected.append(row)
            _require(len(selected) == 1,'observation_mismatch')
            return selected[0]
        try:
            request_row=one('requests',lambda row: row[:2] == [route['case_id'],route['generation']])
            original=one('original_requests',lambda row: row[:2] == [route['case_id'],route['generation']])
            attempt_row=one('admission_attempts',lambda row: row[0] == route['attempt_id'])
            binding=_model(_parse(request_row[2].encode('utf-8'),262144,canonical=False),RequestBinding)
            request=_model(_parse(original[2].encode('utf-8'),262144,canonical=False),CanonicalRequest)
            _require(_canon(binding.model_dump(mode='json')) == _canon(route['binding']) and
                _canon(request.model_dump(mode='json')) == _canon(route['request']))
            _require(request_row[5:] == [binding.request_id,binding.request_revision,binding.consent_revision,binding.fingerprint])
            _require(type(request_row[4]) is int and request_row[4] in (0,1))
            versions=_parse(request_row[3].encode('utf-8'),262144,canonical=False)
            profile=self._release(route['release_id']).profile
            _require(versions == dict(profile_version=profile.version,
                process_version=profile.processes[request.kind].version,policy_version='v1'))
            attempt_data=_parse(attempt_row[3].encode('utf-8'),262144,canonical=False)
            _keys(attempt_data,AdmissionAttempt.model_fields)
            attempt=AdmissionAttempt.model_validate(attempt_data)
            _require(attempt.deadline > attempt.created_at and attempt.state == 'transferred')
            _require(attempt_row[:3] == [route['attempt_id'],route['case_id'],route['dedup_hash']] and attempt_row[4] == 'transferred')
            expected=dict(attempt_id=route['attempt_id'],claimed_case_id=route['case_id'],
                claimed_object_id=binding.object_id,claimed_principal_id=binding.principal_id,
                request_id=binding.request_id,request_revision=binding.request_revision,consent_revision=binding.consent_revision,
                claimed_caller_id=route['auth_claim']['caller_id'],proof_digest=route['auth_claim']['proof_digest'],
                business_fingerprint=route['business_fingerprint'],request_hash=route['request_hash'],dedup_hash=route['dedup_hash'])
            _require(all(getattr(attempt,key) == value for key,value in expected.items()))
        except (ValueError,TypeError,KeyError,IndexError,AttributeError,OverflowError,RecursionError):
            raise RouteFoundationFailure('observation_mismatch') from None
        value=dict(kind='journal-admission-observation-v1',snapshot_kind=snapshot.kind,
            schema_version=snapshot.schema_version,schema_hash=snapshot.schema_hash,content_hash=snapshot.content_hash,
            table_counts=[list(pair) for pair in snapshot.table_counts],total_rows=snapshot.total_rows,
            captured_at=_stamp(snapshot.captured_at),finished_at=_stamp(snapshot.finished_at),elapsed_seconds=snapshot.elapsed_seconds)
        value['observation_hash']=_jhash(value)
        ObservationV1(_canon(value))
        return value

    @_checked
    def observe_admitted(self, reservation_id: str, *, snapshot: RetainedStateSnapshotV1,
                         execution: ExecutionContext) -> RouteRecordV1:
        with self._operation(execution,write=True):
            _id(reservation_id)
            rows,total=self._validate_store()
            route=next((row for row in rows if row['reservation_id'] == reservation_id),None)
            _require(route is not None,'observation_mismatch')
            observation=self._join_snapshot(snapshot,route)
            if route['state'] == 'admission_observed': return RouteRecordV1(_canon(route))
            updated={**route,'state':'admission_observed','observation':observation}
            updated['record_hash']=_jhash({k:v for k,v in updated.items() if k != 'record_hash'})
            result=RouteRecordV1(_canon(updated))
            old_size=len(_full_route(route)); size=len(_full_route(updated))
            _require(size <= self._limits.max_row_bytes and total-old_size+size <= self._limits.max_routes_bytes,'limit')
            self._db.execute("UPDATE routes SET state='admission_observed',record_json=? WHERE reservation_id=?",
                (result.wire_bytes.decode('utf-8'),reservation_id))
            return result

    def close(self) -> None:
        _require(threading.get_ident() == self._owner and not self._busy,'scope')
        if not self._closed:
            self._closed=True
            if self._release_handles(): raise RouteFoundationFailure('storage') from None
