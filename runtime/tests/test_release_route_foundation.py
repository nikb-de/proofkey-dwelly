"""Synthetic declarations and local bookkeeping, never runtime admission authority."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from proofkey.contracts import AuthContext
from proofkey.execution import ExecutionContext
from proofkey.identity import fingerprint
from proofkey.journal import CaseStore
from proofkey.profiles import load_profile
from proofkey.registered_releases import (ReleaseBlobV1, ResourceSetV1,
    KnownFactoryV1, ReleaseArtifactV1, ReleaseRegistryV1, RegisteredReleaseV1)
from proofkey.admission_routes import (AdmissionRouteStoreV1, RouteFoundationFailure,
    RouteRecordV1, RouteLimitsV1, ObservationV1)
from support import NOW, make_request, make_binding, make_checkpoint


def cj(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode()


class Clock:
    def now(self): return NOW
    def monotonic(self): return 10.0


class MutableClock:
    def __init__(self): self.utc, self.mono = NOW, 10.0
    def now(self): return self.utc
    def monotonic(self): return self.mono


def registration_inputs(root):
    profile = load_profile("flat-v1.3")
    policy = dict(policy_id="synthetic-test-policy-v1", version="v1",
        evidence_mode="synthetic", native_routes_enabled=False,
        live_roles=dict(extraction=False, transcription=False, planning=False),
        wait_expiry_seconds=300, internal_case_creation=False, automatic_reminders=False)
    impl = ReleaseBlobV1("fixture/never_executed.txt", b"synthetic declaration only")
    source = cj({"kind":"route-source-declaration-v1","mode":"synthetic",
                 "source_id":"fixture-source","documents":[{"source_id":"D1","text":"synthetic"}]})
    proposal = cj({"kind":"route-proposal-declaration-v1","mode":"synthetic",
                   "baseline_profile_hash":profile.release_hash,
                   "candidate_profile_hash":profile.release_hash,"diff":[]})
    tests = cj({"kind":"route-test-declaration-v1","mode":"synthetic","cases":[]})
    regression = cj({"kind":"route-regression-declaration-v1","mode":"synthetic",
                     "execution":"unestablished","tests_hash":sha256(tests).hexdigest(),"case_ids":[]})
    migration = cj({"kind":"route-migration-declaration-v1","mode":"synthetic",
                    "strategy":"preserve","affected_contracts":[]})
    agent = cj({"kind":"route-agent-declaration-v1","mode":"synthetic",
                "authorship":"unestablished","agent_label":"fixture-agent"})
    dependency = cj({"kind":"route-closure-declaration-v1","mode":"synthetic_declaration",
                     "completeness":"unestablished","entries":[{"name":impl.name,
                     "sha256":sha256(impl.data).hexdigest(),"role":"data"}]})
    stat = root.stat()
    resource = ResourceSetV1("R1", str(root), stat.st_dev, stat.st_ino,
        "journal.sqlite", "world.sqlite",
        tuple(sorted({c.shared_limits.account_id for c in profile.capabilities.values()
                      if c.shared_limits.account_id is not None})), "claimed_case_id")
    factory = KnownFactoryV1("fixture-never-invoked-v1",
        ((impl.name, sha256(impl.data).hexdigest()),), sha256(dependency).hexdigest(),
        "offline_synthetic")
    artifact = ReleaseArtifactV1("L1", factory.factory_id, resource.resource_id,
        cj(profile.model_dump(mode="json")), cj(policy),
        source, proposal, tests, regression, migration, agent, dependency, (impl,))
    return artifact, factory, resource


def registry_at(root):
    artifact, factory, resource = registration_inputs(root)
    return ReleaseRegistryV1(artifacts=(artifact,), factories=(factory,), resources=(resource,))


def literal_envelope(root):
    """Independent wire fixture; never calls a product serializer/hash builder."""
    import base64
    artifact, factory, resource = registration_inputs(root)
    def blob(data):
        return dict(base64=base64.b64encode(data).decode('ascii'), sha256=sha256(data).hexdigest())
    profile = json.loads(artifact.profile_json)
    value = dict(kind='registered-release-v1', version=1, release_id='L1', mode='offline_synthetic',
        factory=dict(factory_id=factory.factory_id, mode='offline_synthetic',
            implementation_pins=[dict(name=n, sha256=h) for n,h in factory.implementation_pins],
            dependency_hash=factory.dependency_hash),
        resource=dict(resource_id='R1', root_path=str(root), root_device=resource.root_device,
            root_inode=resource.root_inode, journal_name='journal.sqlite', source_name='world.sqlite',
            account_ids=['synthetic-local-world'], admission_account_scope='claimed_case_id'),
        blobs={name:blob(getattr(artifact, name+'_json')) for name in
            ('profile','policy','source','proposal','tests','regression','migration','agent','dependency')},
        implementations=[dict(name=b.name, **blob(b.data)) for b in artifact.implementations],
        semantic=dict(profile_hash=profile['release_hash'], process_hash=fingerprint(profile['processes']),
            capabilities_hash=fingerprint(profile['capabilities']), policy_hash=fingerprint(json.loads(artifact.policy_json))))
    value['artifact_hash'] = fingerprint(value)
    return value


def rehash(value):
    value['artifact_hash'] = fingerprint({k:v for k,v in value.items() if k != 'artifact_hash'})
    return cj(value)


def literal_route(root):
    request = make_request().model_dump(mode='json')
    binding = make_binding().model_dump(mode='json')
    claim = dict(caller_id='U1', proof_digest=fingerprint(dict(proof_reference='synthetic-proof')))
    business = fingerprint({k:request[k] for k in ('kind','consent_mode','arguments')})
    envelope = literal_envelope(root)
    value = dict(kind='original-admission-route-v1', version=1, reservation_id='RES1', attempt_id='A1',
        release_id='L1', artifact_hash=envelope['artifact_hash'],resource_id='R1',
        resource_hash=fingerprint(envelope['resource']),account_ids=['synthetic-local-world'],case_id='C1',generation='G1',
        binding=binding,request=request,binding_hash=fingerprint(binding),request_hash=fingerprint(request),
        business_fingerprint=business,auth_claim=claim,auth_claim_hash=fingerprint(claim),
        dedup_hash=fingerprint({**claim,'claim':{k:request[k] for k in
            ('case_id','object_id','principal_id','request_id','request_revision','consent_revision')},
            'business_fingerprint':business}),state='reserved',reserved_at='2026-10-08T10:00:00.000000Z',observation=None)
    value['reservation_hash'] = fingerprint({k:v for k,v in value.items() if k not in ('state','reserved_at','observation')})
    value['record_hash'] = fingerprint(value)
    return value


def public_snapshot(folder, *, request=None, binding=None, version='v1.3', attempt='A1', clock=None, execution=None):
    request=request or make_request(); binding=binding or make_binding(request)
    clock=clock or Clock(); execution=execution or ExecutionContext(NOW+timedelta(seconds=5),NOW,10.0,15.0)
    folder.mkdir(exist_ok=True)
    journal=CaseStore(folder/'journal.sqlite')
    try:
        journal.start_admission(attempt,AuthContext(caller_id='U1',proof_reference='synthetic-proof'),request,NOW,NOW+timedelta(seconds=5))
        journal.admit_from_attempt(attempt,binding,request,make_checkpoint(binding=binding,profile_version=version))
        return journal.capture_retained_state(execution=execution,clock=clock)
    finally: journal.close()


class ReleaseRouteTests(unittest.TestCase):
    def test_early_year_reservation_uses_exact_utc_microsecond_wire(self):
        for year in (1, 99, 999):
            with self.subTest(year=year), tempfile.TemporaryDirectory() as d:
                root=Path(d); control=root/'control'; control.mkdir(); clock=MutableClock()
                clock.utc=datetime(year,2,3,12,0,0,123456,tzinfo=timezone(timedelta(hours=5,minutes=45)))
                scope=ExecutionContext(clock.utc+timedelta(seconds=5),clock.utc,10.0,15.0)
                routes=AdmissionRouteStoreV1(control,database_name='routes.sqlite',registry=registry_at(root),clock=clock,execution=scope)
                try:
                    route=routes.reserve('RES1',attempt_id='A1',release_id='L1',binding=make_binding(),request=make_request(),
                        auth_claim=AuthContext(caller_id='U1',proof_reference='synthetic-proof'),execution=scope)
                    self.assertEqual(json.loads(route.wire_bytes)['reserved_at'],f'{year:04d}-02-03T06:15:00.123456Z')
                    self.assertEqual(RouteRecordV1(route.wire_bytes),route)
                finally: routes.close()

    def test_early_year_observation_constructor_preserves_full_wire_time(self):
        with tempfile.TemporaryDirectory() as d:
            image=public_snapshot(Path(d)/'journal')
            for year in (1, 99, 999):
                with self.subTest(year=year):
                    value=dict(kind='journal-admission-observation-v1',snapshot_kind=image.kind,
                        schema_version=image.schema_version,content_hash=image.content_hash,
                        schema_hash=image.schema_hash,table_counts=[list(item) for item in image.table_counts],total_rows=image.total_rows,
                        captured_at=f'{year:04d}-02-03T06:15:00.123456Z',
                        finished_at=f'{year:04d}-02-03T06:15:00.123457Z',elapsed_seconds=0.000001)
                    value['observation_hash']=fingerprint(value)
                    observation=ObservationV1(cj(value))
                    self.assertEqual(observation.captured_at,datetime(year,2,3,6,15,0,123456,tzinfo=timezone.utc))
                    self.assertEqual(observation.finished_at.microsecond,123457)
                    self.assertEqual(observation.wire_bytes,cj(value))

    def _assert_cleanup_fault_is_finite(self, phase, *, timeout=False):
        import sqlite3
        from unittest.mock import patch
        original=sqlite3.connect; armed=[False]; commit_failed=[False]; clock=MutableClock()
        class Connection:
            def __init__(self,*args,**kwargs): self.real=original(*args,**kwargs)
            def __getattr__(self,name): return getattr(self.real,name)
            def set_progress_handler(self,callback,count):
                if armed[0] and phase == 'progress' and callback is None:
                    armed[0]=False
                    raise sqlite3.OperationalError('cleanup-private-canary')
                return self.real.set_progress_handler(callback,count)
            def execute(self,sql,*args):
                if armed[0] and phase == 'ROLLBACK' and sql == 'COMMIT' and not commit_failed[0]:
                    commit_failed[0]=True
                    raise sqlite3.OperationalError('body-private-canary')
                if armed[0] and sql == phase:
                    armed[0]=False
                    raise OSError('cleanup-private-canary')
                result=self.real.execute(sql,*args)
                if armed[0] and timeout and sql.startswith('INSERT INTO routes'):
                    clock.utc=NOW+timedelta(seconds=6); clock.mono=16.0
                return result
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); control=root/'control'; control.mkdir(); registry=registry_at(root)
            scope=ExecutionContext(NOW+timedelta(seconds=5),NOW,10.0,15.0)
            with patch('proofkey.admission_routes.sqlite3.connect',Connection):
                routes=AdmissionRouteStoreV1(control,database_name='routes.sqlite',registry=registry,clock=clock,execution=scope)
            armed[0]=True
            try:
                with self.assertRaises(RouteFoundationFailure) as failure:
                    routes.reserve('RES1',attempt_id='A1',release_id='L1',binding=make_binding(),request=make_request(),
                        auth_claim=AuthContext(caller_id='U1',proof_reference='synthetic-proof'),execution=scope)
                self.assertEqual(failure.exception.code,'timeout' if timeout else 'storage')
                self.assertNotIn('canary',str(failure.exception))
            finally: routes.close()
            fresh=ExecutionContext(clock.utc+timedelta(seconds=5),clock.utc,clock.mono,clock.mono+5)
            reopened=AdmissionRouteStoreV1(control,database_name='routes.sqlite',registry=registry,clock=clock,execution=fresh)
            try:
                route=reopened.get('RES1',execution=fresh)
                self.assertEqual(route is None,phase == 'ROLLBACK' or timeout)
                reserved=reopened.reserve('RES1',attempt_id='A1',release_id='L1',binding=make_binding(),request=make_request(),
                    auth_claim=AuthContext(caller_id='U1',proof_reference='synthetic-proof'),execution=fresh)
                self.assertEqual(reopened.get('RES1',execution=fresh),reserved)
            finally: reopened.close()

    def test_cleanup_progress_fault_is_finite_and_reopenable(self):
        self._assert_cleanup_fault_is_finite('progress')

    def test_cleanup_rollback_fault_is_finite_and_reopenable(self):
        self._assert_cleanup_fault_is_finite('ROLLBACK')

    def test_cleanup_query_only_fault_is_finite_and_reopenable(self):
        self._assert_cleanup_fault_is_finite('PRAGMA query_only=ON')

    def test_cleanup_fault_preserves_original_timeout(self):
        self._assert_cleanup_fault_is_finite('ROLLBACK',timeout=True)

    def test_exact_wire_and_aggregate_registry_byte_limits(self):
        import base64
        from dataclasses import replace
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); value=literal_envelope(root)
            def inventory(tail):
                blobs=[(f'bulk/{i}.bin',b'x'*1048576) for i in range(5)]+[('bulk/5.bin',b'y'*tail)]
                value['implementations']=[dict(name=name,base64=base64.b64encode(raw).decode(),sha256=sha256(raw).hexdigest()) for name,raw in blobs]
                pins=[dict(name=item['name'],sha256=item['sha256']) for item in value['implementations']]
                dependency=cj(dict(kind='route-closure-declaration-v1',mode='synthetic_declaration',completeness='unestablished',
                    entries=[dict(**pin,role='data') for pin in pins]))
                value['factory']['implementation_pins']=pins
                value['factory']['dependency_hash']=sha256(dependency).hexdigest()
                value['blobs']['dependency']=dict(base64=base64.b64encode(dependency).decode(),sha256=sha256(dependency).hexdigest())
                return tuple(ReleaseBlobV1(name,raw) for name,raw in blobs)
            inventory(0)
            value['release_id']+='x'*((-len(rehash(value)))%4)
            remaining=8388608-len(rehash(value))
            self.assertEqual(remaining%4,0)
            tail=remaining//4*3
            self.assertLessEqual(tail,1048576)
            implementations=inventory(tail)
            wire=rehash(value)
            self.assertEqual(len(wire),8388608)
            self.assertEqual(RegisteredReleaseV1(wire).wire_bytes,wire)
            value['release_id']+='x'
            with self.assertRaises(RouteFoundationFailure) as failure: RegisteredReleaseV1(rehash(value))
            self.assertEqual(failure.exception.code,'limit')
            value['release_id']=value['release_id'][:-1]
            _,_,resource=registration_inputs(root)
            factory=KnownFactoryV1(value['factory']['factory_id'],tuple((p['name'],p['sha256']) for p in value['factory']['implementation_pins']),
                value['factory']['dependency_hash'],'offline_synthetic')
            blobs=[base64.b64decode(value['blobs'][name]['base64']) for name in
                ('profile','policy','source','proposal','tests','regression','migration','agent','dependency')]
            artifact=ReleaseArtifactV1(value['release_id'],factory.factory_id,'R1',*blobs,implementations)
            artifacts=tuple(replace(artifact,release_id='L'+str(i)+value['release_id'][2:]) for i in range(4))
            registry=ReleaseRegistryV1(artifacts=artifacts,factories=(factory,),resources=(resource,))
            self.assertEqual(sum(len(registry.resolve(a.release_id).wire_bytes) for a in artifacts),33554432)
            with self.assertRaises(RouteFoundationFailure) as failure:
                ReleaseRegistryV1(artifacts=artifacts+(replace(artifact,release_id='L4'+value['release_id'][2:]),),factories=(factory,),resources=(resource,))
            self.assertEqual(failure.exception.code,'limit')

    def test_registration_count_and_normalized_pin_collisions(self):
        from dataclasses import replace
        with tempfile.TemporaryDirectory() as d:
            artifact,factory,resource=registration_inputs(Path(d))
            many=tuple(replace(artifact,release_id=f'L{i}') for i in range(33))
            with self.assertRaises(RouteFoundationFailure):
                ReleaseRegistryV1(artifacts=many,factories=(factory,),resources=(resource,))
            with self.assertRaises(RouteFoundationFailure):
                replace(artifact,implementations=tuple(ReleaseBlobV1(f'f/{i:04}',b'') for i in range(513)))
            for names in [('a/e\u0301','a/\u00e9'),('a/X','a/x')]:
                with self.subTest(names=names):
                    with self.assertRaises(RouteFoundationFailure):
                        KnownFactoryV1('F',tuple((name,'0'*64) for name in sorted(names)),'0'*64,'offline_synthetic')

    def test_tampered_registry_cannot_relabel_release_identity(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); control=root/'control'; control.mkdir(); registry=registry_at(root)
            raw=registry.resolve('L1').wire_bytes
            object.__setattr__(registry,'_releases',(('L2',raw),))
            scope=ExecutionContext(NOW+timedelta(seconds=5),NOW,10.0,15.0)
            with self.assertRaises(RouteFoundationFailure):
                routes=AdmissionRouteStoreV1(control,database_name='routes.sqlite',registry=registry,clock=Clock(),execution=scope)
                routes.close()

    def test_clock_callback_failure_is_finite_and_cleanup_remains_available(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); control=root/'control'; control.mkdir(); clock=MutableClock()
            scope=ExecutionContext(NOW+timedelta(seconds=5),NOW,10.0,15.0)
            routes=AdmissionRouteStoreV1(control,database_name='routes.sqlite',registry=registry_at(root),clock=clock,execution=scope)
            def failed(): raise RuntimeError('clock-private-canary')
            clock.now=failed
            try:
                caught=None
                try: routes.get('missing',execution=scope)
                except Exception as error: caught=error
                self.assertIsInstance(caught,RouteFoundationFailure)
                self.assertEqual(caught.code,'scope')
                self.assertNotIn('canary',str(caught))
            finally: routes.close()

    def test_nullable_unrelated_rows_do_not_change_selected_original_join(self):
        from dataclasses import replace
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); control=root/'control'; control.mkdir()
            scope=ExecutionContext(NOW+timedelta(seconds=5),NOW,10.0,15.0)
            routes=AdmissionRouteStoreV1(control,database_name='routes.sqlite',registry=registry_at(root),clock=Clock(),execution=scope)
            try:
                routes.reserve('RES1',attempt_id='A1',release_id='L1',binding=make_binding(),request=make_request(),
                    auth_claim=AuthContext(caller_id='U1',proof_reference='synthetic-proof'),execution=scope)
                image=public_snapshot(root/'first'); data=json.loads(image.payload)
                attempts=next(table for table in data['tables'] if table['name']=='admission_attempts')
                unrelated=[None,'C2','0'*64,'{}','unbound']
                attempts['rows']=[unrelated,unrelated,*attempts['rows']]
                raw=cj(data)
                expanded=replace(image,payload=raw,content_hash=sha256(raw).hexdigest(),total_rows=image.total_rows+2,
                    table_counts=tuple((name,count+2 if name=='admission_attempts' else count) for name,count in image.table_counts))
                observed=routes.observe_admitted('RES1',snapshot=expanded,execution=scope)
                self.assertEqual(observed.state,'admission_observed')
                self.assertEqual(observed.observation.observation_hash,
                    fingerprint({k:v for k,v in json.loads(observed.observation.wire_bytes).items() if k!='observation_hash'}))
            finally: routes.close()

    def test_observation_constructor_rejects_rehashed_timestamp_and_count_aliases(self):
        with tempfile.TemporaryDirectory() as d:
            image=public_snapshot(Path(d)/'first')
            value=dict(kind='journal-admission-observation-v1',snapshot_kind=image.kind,schema_version=1,
                schema_hash=image.schema_hash,content_hash=image.content_hash,table_counts=[list(p) for p in image.table_counts],
                total_rows=image.total_rows,captured_at='2026-10-08T10:00:00.000000Z',
                finished_at='2026-10-08T10:00:00.000000Z',elapsed_seconds=0.0)
            value['observation_hash']=fingerprint(value)
            ObservationV1(cj(value))
            for key,bad in [('captured_at','2026-10-08T10:00:00Z'),('finished_at','2026-10-08T10:00:06.000000Z'),
                    ('elapsed_seconds',0),('schema_version',True),('total_rows',True),('schema_hash','0'*64)]:
                with self.subTest(key=key):
                    changed={**value,key:bad}
                    changed['observation_hash']=fingerprint({k:v for k,v in changed.items() if k!='observation_hash'})
                    with self.assertRaises(RouteFoundationFailure): ObservationV1(cj(changed))

    def test_interrupted_progress_is_restored_for_a_new_explicit_window(self):
        class InterruptClock(MutableClock):
            armed=False; count=0
            def now(self):
                if self.armed:
                    self.count+=1
                    if self.count==3:
                        self.utc=NOW+timedelta(seconds=6); self.mono=16.0; self.armed=False
                return self.utc
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); control=root/'control'; control.mkdir(); clock=InterruptClock()
            scope=ExecutionContext(NOW+timedelta(seconds=5),NOW,10.0,15.0)
            routes=AdmissionRouteStoreV1(control,database_name='routes.sqlite',registry=registry_at(root),clock=clock,execution=scope)
            try:
                clock.armed=True
                with self.assertRaises(RouteFoundationFailure) as failure: routes.get('missing',execution=scope)
                self.assertEqual(failure.exception.code,'timeout')
                fresh=ExecutionContext(clock.utc+timedelta(seconds=5),clock.utc,16.0,21.0)
                self.assertIsNone(routes.get('missing',execution=fresh))
            finally: routes.close()

    def test_read_uses_one_sqlite_snapshot_against_interleaved_writer(self):
        import sqlite3
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); control=root/'control'; control.mkdir(); original=sqlite3.connect
            scope=ExecutionContext(NOW+timedelta(seconds=5),NOW,10.0,15.0); armed=[False]; blocked=[]
            class Connection:
                def __init__(self,*args,**kwargs): self.real=original(*args,**kwargs)
                def __getattr__(self,name): return getattr(self.real,name)
                def execute(self,sql,*args):
                    cursor=self.real.execute(sql,*args)
                    if armed[0] and sql == 'SELECT * FROM meta':
                        rows=list(cursor)
                        try:
                            with original(control/'routes.sqlite',timeout=0) as writer:
                                writer.execute('UPDATE meta SET version=1')
                        except sqlite3.OperationalError: blocked.append(True)
                        else: blocked.append(False)
                        return iter(rows)
                    return cursor
            with patch('proofkey.admission_routes.sqlite3.connect',Connection):
                routes=AdmissionRouteStoreV1(control,database_name='routes.sqlite',registry=registry_at(root),clock=Clock(),execution=scope)
            armed[0]=True
            try:
                self.assertIsNone(routes.get('missing',execution=scope))
                self.assertTrue(blocked); self.assertTrue(all(blocked))
            finally: routes.close()

    def test_commit_without_response_retains_original_for_fresh_retry(self):
        import sqlite3
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); control=root/'control'; control.mkdir(); original=sqlite3.connect
            clock=MutableClock(); armed=[False]
            class Connection:
                def __init__(self,*args,**kwargs): self.real=original(*args,**kwargs)
                def __getattr__(self,name): return getattr(self.real,name)
                def execute(self,sql,*args):
                    cursor=self.real.execute(sql,*args)
                    if armed[0] and sql == 'COMMIT':
                        clock.utc=NOW+timedelta(seconds=6); clock.mono=16.0; armed[0]=False
                    return cursor
            scope=ExecutionContext(NOW+timedelta(seconds=5),NOW,10.0,15.0)
            with patch('proofkey.admission_routes.sqlite3.connect',Connection):
                routes=AdmissionRouteStoreV1(control,database_name='routes.sqlite',registry=registry_at(root),clock=clock,execution=scope)
            request=make_request(); binding=make_binding(); claim=AuthContext(caller_id='U1',proof_reference='synthetic-proof')
            armed[0]=True
            try:
                with self.assertRaises(RouteFoundationFailure) as failure:
                    routes.reserve('RES1',attempt_id='A1',release_id='L1',binding=binding,request=request,auth_claim=claim,execution=scope)
                self.assertEqual(failure.exception.code,'timeout')
                fresh=ExecutionContext(clock.utc+timedelta(seconds=5),clock.utc,16.0,21.0)
                retained=routes.get('RES1',execution=fresh)
                self.assertIsInstance(retained,RouteRecordV1)
                self.assertEqual(json.loads(retained.wire_bytes)['reserved_at'],'2026-10-08T10:00:00.000000Z')
                self.assertEqual(routes.reserve('RES1',attempt_id='A1',release_id='L1',binding=binding,request=request,
                    auth_claim=claim,execution=fresh),retained)
            finally: routes.close()

    def test_busy_vm_interruption_and_close_fault_are_finite(self):
        import sqlite3
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); control=root/'control'; control.mkdir(); registry=registry_at(root)
            scope=ExecutionContext(NOW+timedelta(seconds=5),NOW,10.0,15.0)
            with self.assertRaises(RouteFoundationFailure) as failure:
                AdmissionRouteStoreV1(control,database_name='interrupted.sqlite',registry=registry,clock=Clock(),execution=scope,
                    limits=RouteLimitsV1(max_sqlite_steps=1))
            self.assertEqual(failure.exception.code,'limit')
            with self.assertRaises(RouteFoundationFailure):
                AdmissionRouteStoreV1(control,database_name='interrupted.sqlite',registry=registry,clock=Clock(),execution=scope)
            routes=AdmissionRouteStoreV1(control,database_name='routes.sqlite',registry=registry,clock=Clock(),execution=scope)
            with sqlite3.connect(control/'routes.sqlite',timeout=0) as writer:
                writer.execute('BEGIN IMMEDIATE')
                with self.assertRaises(RouteFoundationFailure) as failure:
                    routes.reserve('RES1',attempt_id='A1',release_id='L1',binding=make_binding(),request=make_request(),
                        auth_claim=AuthContext(caller_id='U1',proof_reference='synthetic-proof'),execution=scope)
                self.assertEqual(failure.exception.code,'storage')
                writer.rollback()
            self.assertIsNone(routes.get('RES1',execution=scope)); routes.close()
            original=sqlite3.connect
            class Connection:
                def __init__(self,*args,**kwargs): self.real=original(*args,**kwargs)
                def __getattr__(self,name): return getattr(self.real,name)
                def close(self): self.real.close(); raise sqlite3.OperationalError('private canary')
            with patch('proofkey.admission_routes.sqlite3.connect',Connection):
                routes=AdmissionRouteStoreV1(control,database_name='routes.sqlite',registry=registry,clock=Clock(),execution=scope)
            with self.assertRaises(RouteFoundationFailure) as failure: routes.close()
            self.assertEqual(str(failure.exception),'storage')
            recovered=AdmissionRouteStoreV1(control,database_name='routes.sqlite',registry=registry,clock=Clock(),execution=scope)
            recovered.close()

    def test_constructor_detaches_limits_from_caller(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); control=root/'control'; control.mkdir()
            scope=ExecutionContext(NOW+timedelta(seconds=5),NOW,10.0,15.0)
            limits=RouteLimitsV1()
            routes=AdmissionRouteStoreV1(control,database_name='routes.sqlite',registry=registry_at(root),clock=Clock(),execution=scope,limits=limits)
            object.__setattr__(limits,'max_sqlite_steps',1)
            try:
                try: found=routes.get('missing',execution=scope)
                except RouteFoundationFailure as error: self.fail(f'caller mutated retained limits: {error.code}')
                self.assertIsNone(found)
            finally: routes.close()

    def test_control_schema_and_data_corruption_are_never_repaired(self):
        import sqlite3
        changes=["CREATE TABLE extra(x)","CREATE INDEX extra ON routes(case_id)",
            "CREATE TRIGGER extra AFTER INSERT ON routes BEGIN SELECT 1; END",
            "UPDATE meta SET registry_hash='wrong'","DELETE FROM releases",
            "UPDATE releases SET artifact_json=zeroblob(8388609)",
            "UPDATE releases SET artifact_hash='wrong'"]
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); registry=registry_at(root); scope=ExecutionContext(NOW+timedelta(seconds=5),NOW,10.0,15.0)
            for index,statement in enumerate(changes):
                with self.subTest(index=index):
                    control=root/f'control{index}'; control.mkdir()
                    routes=AdmissionRouteStoreV1(control,database_name='routes.sqlite',registry=registry,clock=Clock(),execution=scope)
                    routes.close()
                    with sqlite3.connect(control/'routes.sqlite') as db: db.execute(statement)
                    before=(control/'routes.sqlite').read_bytes()
                    with self.assertRaises(RouteFoundationFailure):
                        AdmissionRouteStoreV1(control,database_name='routes.sqlite',registry=registry,clock=Clock(),execution=scope)
                    self.assertEqual((control/'routes.sqlite').read_bytes(),before)
            for index in range(2):
                control=root/f'empty{index}'; control.mkdir(); database=control/'routes.sqlite'
                if index:
                    with sqlite3.connect(database) as db: db.execute('CREATE TABLE meta(singleton INTEGER)')
                else: database.touch()
                before=database.read_bytes()
                with self.assertRaises(RouteFoundationFailure):
                    AdmissionRouteStoreV1(control,database_name='routes.sqlite',registry=registry,clock=Clock(),execution=scope)
                self.assertEqual(database.read_bytes(),before)

    def test_count_and_aggregate_limits_preserve_previous_routes(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); control=root/'control'; control.mkdir()
            scope=ExecutionContext(NOW+timedelta(seconds=5),NOW,10.0,15.0)
            row=literal_route(root)
            full=len(cj({**{k:row[k] for k in ('reservation_id','attempt_id','resource_id','case_id','generation','release_id','state')},'record':row}))
            for label,limits in [('count',RouteLimitsV1(max_routes=1)),('bytes',RouteLimitsV1(max_routes_bytes=full))]:
                routes=AdmissionRouteStoreV1(control,database_name=label+'.sqlite',registry=registry_at(root),clock=Clock(),execution=scope,limits=limits)
                try:
                    first=routes.reserve('RES1',attempt_id='A1',release_id='L1',binding=make_binding(),request=make_request(),
                        auth_claim=AuthContext(caller_id='U1',proof_reference='synthetic-proof'),execution=scope)
                    with self.assertRaises(RouteFoundationFailure) as failure:
                        routes.reserve('RES2',attempt_id='A2',release_id='L1',binding=make_binding(generation='G2'),request=make_request(),
                            auth_claim=AuthContext(caller_id='U1',proof_reference='synthetic-proof'),execution=scope)
                    self.assertEqual(failure.exception.code,'limit')
                    self.assertEqual(routes.get('RES1',execution=scope),first)
                finally: routes.close()

    def test_full_release_aggregate_threshold_and_lowered_reopen_limit(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); control=root/'control'; control.mkdir(); registry=registry_at(root)
            scope=ExecutionContext(NOW+timedelta(seconds=5),NOW,10.0,15.0)
            value=literal_envelope(root)
            exact=len(cj(dict(release_id='L1',artifact_hash=value['artifact_hash'],artifact=value)))
            with self.assertRaises(RouteFoundationFailure) as failure:
                AdmissionRouteStoreV1(control,database_name='small.sqlite',registry=registry,clock=Clock(),execution=scope,
                    limits=RouteLimitsV1(max_release_bytes=exact-1))
            self.assertEqual(failure.exception.code,'limit')
            routes=AdmissionRouteStoreV1(control,database_name='exact.sqlite',registry=registry,clock=Clock(),execution=scope,
                limits=RouteLimitsV1(max_release_bytes=exact)); routes.close()
            before=(control/'exact.sqlite').read_bytes()
            with self.assertRaises(RouteFoundationFailure):
                AdmissionRouteStoreV1(control,database_name='exact.sqlite',registry=registry,clock=Clock(),execution=scope,
                    limits=RouteLimitsV1(max_release_bytes=exact-1))
            self.assertEqual((control/'exact.sqlite').read_bytes(),before)

    def test_creator_reentrancy_closed_and_cleanup_after_expiry(self):
        import threading
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); control=root/'control'; control.mkdir(); clock=MutableClock()
            scope=ExecutionContext(NOW+timedelta(seconds=5),NOW,10.0,15.0)
            routes=AdmissionRouteStoreV1(control,database_name='routes.sqlite',registry=registry_at(root),clock=clock,execution=scope)
            denied=[]
            def foreign():
                for call in (lambda: routes.get('missing',execution=scope),routes.close):
                    try: call()
                    except RouteFoundationFailure as error: denied.append(error.code)
            thread=threading.Thread(target=foreign); thread.start(); thread.join(timeout=2)
            self.assertFalse(thread.is_alive()); self.assertEqual(denied,['scope','scope'])
            original=clock.now
            def nested():
                clock.now=original
                try: routes.get('missing',execution=scope)
                except RouteFoundationFailure as error: denied.append(error.code)
                return original()
            clock.now=nested
            self.assertIsNone(routes.get('missing',execution=scope)); self.assertEqual(denied[-1],'scope')
            clock.utc=NOW+timedelta(seconds=10); clock.mono=20.0
            routes.close(); routes.close()
            self.assertTrue((control/'routes.sqlite.owner-lock').exists())
            with self.assertRaises(RouteFoundationFailure): routes.get('missing',execution=scope)

    def test_symlink_hardlink_and_live_replacement_are_rejected(self):
        import os
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); registry=registry_at(root); scope=ExecutionContext(NOW+timedelta(seconds=5),NOW,10.0,15.0)
            outside=root/'outside.sqlite'; outside.touch()
            for label,link in [('symlink',os.symlink),('hardlink',os.link)]:
                control=root/label; control.mkdir(); link(outside,control/'routes.sqlite')
                with self.assertRaises(RouteFoundationFailure):
                    AdmissionRouteStoreV1(control,database_name='routes.sqlite',registry=registry,clock=Clock(),execution=scope)
            control=root/'live'; control.mkdir()
            routes=AdmissionRouteStoreV1(control,database_name='routes.sqlite',registry=registry,clock=Clock(),execution=scope)
            (control/'routes.sqlite').rename(control/'retained.sqlite')
            (control/'routes.sqlite').touch()
            try:
                with self.assertRaises(RouteFoundationFailure): routes.get('missing',execution=scope)
            finally: routes.close()

    def test_untrusted_snapshot_objects_and_tagged_scalars_are_revalidated(self):
        import copy
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); control=root/'control'; control.mkdir()
            scope=ExecutionContext(NOW+timedelta(seconds=5),NOW,10.0,15.0)
            routes=AdmissionRouteStoreV1(control,database_name='routes.sqlite',registry=registry_at(root),clock=Clock(),execution=scope)
            try:
                first=routes.reserve('RES1',attempt_id='A1',release_id='L1',binding=make_binding(),request=make_request(),
                    auth_claim=AuthContext(caller_id='U1',proof_reference='synthetic-proof'),execution=scope)
                image=public_snapshot(root/'first')
                tagged=json.loads(image.payload)
                next(table for table in tagged['tables'] if table['name']=='requests')['rows'][0][0]=['text','C1']
                bad=copy.copy(image); object.__setattr__(bad,'payload',cj(tagged)); object.__setattr__(bad,'content_hash',sha256(bad.payload).hexdigest())
                oversized=copy.copy(image); object.__setattr__(oversized,'payload',b'x'*4194305)
                for value in (image.__dict__ if hasattr(image,'__dict__') else {},bad,oversized):
                    with self.subTest(kind=type(value).__name__):
                        with self.assertRaises(RouteFoundationFailure): routes.observe_admitted('RES1',snapshot=value,execution=scope)
                        self.assertEqual(routes.get('RES1',execution=scope),first)
            finally: routes.close()

    def test_registry_duplicate_unknown_unused_and_blob_name_bounds(self):
        from dataclasses import replace
        with tempfile.TemporaryDirectory() as d:
            artifact,factory,resource=registration_inputs(Path(d))
            for artifacts,factories,resources in [((artifact,artifact),(factory,),(resource,)),
                    ((artifact,),(factory,factory),(resource,)),
                    ((artifact,),(factory,),(resource,resource)),
                    ((artifact,),(replace(factory,factory_id='other'),),(resource,)),
                    ((artifact,),(factory,),(replace(resource,resource_id='other'),)),
                    ((artifact,),(factory,replace(factory,factory_id='unused')),(resource,))]:
                with self.subTest(counts=(len(artifacts),len(factories),len(resources))):
                    with self.assertRaises(RouteFoundationFailure):
                        ReleaseRegistryV1(artifacts=artifacts,factories=factories,resources=resources)
            for name in ('../bad','/bad','a//b','a/./b','a\\b','a:b','a\0b'):
                with self.subTest(name=repr(name)):
                    with self.assertRaises(RouteFoundationFailure): ReleaseBlobV1(name,b'')
            ReleaseBlobV1('exact.bin',b'x'*1048576)
            with self.assertRaises(RouteFoundationFailure): ReleaseBlobV1('large.bin',b'x'*1048577)
            with self.assertRaises(RouteFoundationFailure):
                KnownFactoryV1('F',(('A.bin','0'*64),('a.bin','0'*64)),'0'*64,'offline_synthetic')
            registry=registry_at(Path(d))
            with self.assertRaises(RouteFoundationFailure) as failure: registry.resolve('unknown')
            self.assertEqual(failure.exception.code,'unregistered')
            with self.assertRaises(RouteFoundationFailure): registry.resource('unknown')
            with self.assertRaises((AttributeError,TypeError)): registry._releases=()

    def test_stopped_old_generation_and_debt_image_are_observational_only(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); control=root/'control'; control.mkdir(); clock=Clock()
            scope=ExecutionContext(NOW+timedelta(seconds=5),NOW,10.0,15.0)
            registry=registry_at(root)
            routes=AdmissionRouteStoreV1(control,database_name='routes.sqlite',registry=registry,clock=clock,execution=scope)
            journal=CaseStore(root/'journal.sqlite')
            request=make_request(); binding=make_binding(request); claim=AuthContext(caller_id='U1',proof_reference='synthetic-proof')
            try:
                routes.reserve('RES1',attempt_id='A1',release_id='L1',binding=binding,request=request,auth_claim=claim,execution=scope)
                journal.start_admission('A1',claim,request,NOW,NOW+timedelta(seconds=5))
                journal.admit_from_attempt('A1',binding,request,make_checkpoint(binding=binding,profile_version='v1.3'))
                journal.set_stop('C1','G1')
                successor_request=make_request(request_id='REQ2')
                successor=make_binding(successor_request,generation='G2',supersedes_generation='G1')
                old=journal.checkpoint('C1')
                journal.admit(successor,successor_request,make_checkpoint(binding=successor,profile_version='v1.3',deadline=old.deadline,budget=old.budget))
                before=journal.capture_retained_state(execution=scope,clock=clock)
                observed=routes.observe_admitted('RES1',snapshot=before,execution=scope)
                self.assertEqual(observed.binding,binding)
                self.assertTrue(journal.generation_stop(binding).requested)
                self.assertEqual(journal.checkpoint('C1').binding,successor)
                self.assertEqual(journal.capture_retained_state(execution=scope,clock=clock).payload,before.payload)
            finally: journal.close(); routes.close()

    def test_registry_rejects_alias_before_reading_properties(self):
        touched=[]
        class Alias:
            @property
            def release_id(self): touched.append(True); return 'L1'
        with tempfile.TemporaryDirectory() as d:
            _,factory,resource=registration_inputs(Path(d))
            with self.assertRaises(RouteFoundationFailure):
                ReleaseRegistryV1(artifacts=(Alias(),),factories=(factory,),resources=(resource,))
            self.assertEqual(touched,[])

    def test_case_sensitive_ids_are_not_path_aliases(self):
        import base64
        with tempfile.TemporaryDirectory() as d:
            value=literal_envelope(Path(d))
            tests=cj(dict(kind='route-test-declaration-v1',mode='synthetic',cases=[
                dict(case_id='A',purpose='upper identity'),dict(case_id='a',purpose='lower identity')]))
            regression=cj(dict(kind='route-regression-declaration-v1',mode='synthetic',execution='unestablished',
                tests_hash=sha256(tests).hexdigest(),case_ids=['A','a']))
            for name,raw in [('tests',tests),('regression',regression)]:
                value['blobs'][name]=dict(base64=base64.b64encode(raw).decode(),sha256=sha256(raw).hexdigest())
            try: result=RegisteredReleaseV1(rehash(value))
            except RouteFoundationFailure as error: self.fail(f'distinct public IDs denied: {error.code}')
            self.assertEqual(result.profile.profile_id,'flat-v1.3')

    def test_aggregate_implementation_bytes_are_bounded_before_envelope_encoding(self):
        from dataclasses import replace
        with tempfile.TemporaryDirectory() as d:
            artifact,_,_=registration_inputs(Path(d))
            blobs=tuple(ReleaseBlobV1(f'big/{i}.dat',b'x'*1048576) for i in range(9))
            with self.assertRaises(RouteFoundationFailure) as failure:
                replace(artifact,implementations=blobs)
            self.assertEqual(failure.exception.code,'limit')

    def test_first_observation_rejects_wrong_complete_public_joins(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); control=root/'control'; control.mkdir()
            scope=ExecutionContext(NOW+timedelta(seconds=5),NOW,10.0,15.0)
            routes=AdmissionRouteStoreV1(control,database_name='routes.sqlite',registry=registry_at(root),clock=Clock(),execution=scope)
            try:
                first=routes.reserve('RES1',attempt_id='A1',release_id='L1',binding=make_binding(),request=make_request(),
                    auth_claim=AuthContext(caller_id='U1',proof_reference='synthetic-proof'),execution=scope)
                for label,options in [('narrative',dict(request=make_request(narrative='changed'))),
                        ('evidence',dict(request=make_request(evidence_ids=['different']))),
                        ('supersedes',dict(binding=make_binding(supersedes_generation='G0'))),
                        ('version',dict(version='wrong')),('attempt',dict(attempt='A2'))]:
                    with self.subTest(label=label):
                        image=public_snapshot(root/label,**options)
                        with self.assertRaises(RouteFoundationFailure):
                            routes.observe_admitted('RES1',snapshot=image,execution=scope)
                        self.assertEqual(routes.get('RES1',execution=scope),first)
            finally: routes.close()

    def test_later_consistent_image_preserves_first_observation_and_wrong_image_denies(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); control=root/'control'; control.mkdir(); clock=MutableClock()
            scope=ExecutionContext(NOW+timedelta(seconds=5),NOW,10.0,15.0)
            routes=AdmissionRouteStoreV1(control,database_name='routes.sqlite',registry=registry_at(root),clock=clock,execution=scope)
            try:
                routes.reserve('RES1',attempt_id='A1',release_id='L1',binding=make_binding(),request=make_request(),
                    auth_claim=AuthContext(caller_id='U1',proof_reference='synthetic-proof'),execution=scope)
                first_image=public_snapshot(root/'first')
                first=routes.observe_admitted('RES1',snapshot=first_image,execution=scope)
                self.assertIsInstance(first,RouteRecordV1)
                clock.utc,clock.mono=NOW+timedelta(seconds=1),11.0
                fresh=ExecutionContext(clock.utc+timedelta(seconds=5),clock.utc,11.0,16.0)
                journal=CaseStore(root/'first'/'journal.sqlite')
                try: later=journal.capture_retained_state(execution=fresh,clock=clock)
                finally: journal.close()
                self.assertEqual(later.payload,first_image.payload)
                self.assertNotEqual(later.captured_at,first_image.captured_at)
                self.assertEqual(routes.observe_admitted('RES1',snapshot=later,execution=fresh),first)
                self.assertEqual(first.observation.captured_at,NOW)
                for label,options in [('narrative',dict(request=make_request(narrative='changed'))),
                        ('evidence',dict(request=make_request(evidence_ids=['different']))),
                        ('supersedes',dict(binding=make_binding(supersedes_generation='G0'))),
                        ('version',dict(version='wrong')),('attempt',dict(attempt='A2'))]:
                    with self.subTest(label=label):
                        image=public_snapshot(root/label,**options)
                        with self.assertRaises(RouteFoundationFailure) as failure:
                            routes.observe_admitted('RES1',snapshot=image,execution=fresh)
                        self.assertEqual(failure.exception.code,'observation_mismatch')
                        self.assertEqual(routes.get('RES1',execution=fresh),first)
            finally: routes.close()

    def test_observation_expansion_over_full_row_limit_keeps_reservation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); control=root/'control'; control.mkdir()
            scope=ExecutionContext(NOW+timedelta(seconds=5),NOW,10.0,15.0)
            value=literal_route(root)
            size=len(cj({**{k:value[k] for k in ('reservation_id','attempt_id','resource_id','case_id','generation','release_id','state')},'record':value}))
            routes=AdmissionRouteStoreV1(control,database_name='routes.sqlite',registry=registry_at(root),clock=Clock(),
                execution=scope,limits=RouteLimitsV1(max_row_bytes=size))
            try:
                first=routes.reserve('RES1',attempt_id='A1',release_id='L1',binding=make_binding(),request=make_request(),
                    auth_claim=AuthContext(caller_id='U1',proof_reference='synthetic-proof'),execution=scope)
                image=public_snapshot(root/'first')
                with self.assertRaises(RouteFoundationFailure) as failure:
                    routes.observe_admitted('RES1',snapshot=image,execution=scope)
                self.assertEqual(failure.exception.code,'limit')
                self.assertEqual(routes.get('RES1',execution=scope),first)
            finally: routes.close()

    def test_route_wire_constructor_independently_rejects_false_identity(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for key, bad in [('request_hash','0'*64), ('business_fingerprint','0'*64),
                    ('dedup_hash','0'*64), ('auth_claim_hash','0'*64), ('reservation_hash','0'*64),
                    ('state','admitted'), ('reserved_at','2026-10-08T10:00:00Z'), ('generation','G2')]:
                with self.subTest(key=key):
                    value = literal_route(root); value[key] = bad
                    value['record_hash'] = fingerprint({k:v for k,v in value.items() if k != 'record_hash'})
                    with self.assertRaises(RouteFoundationFailure): RouteRecordV1(cj(value))

    def test_original_fields_and_claim_aliases_cannot_rebind(self):
        class ClaimAlias(AuthContext): pass
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); control=root/'control'; control.mkdir()
            scope=ExecutionContext(NOW+timedelta(seconds=5),NOW,10.0,15.0)
            routes=AdmissionRouteStoreV1(control,database_name='routes.sqlite',registry=registry_at(root),clock=Clock(),execution=scope)
            request=make_request(evidence_ids=['E1','E2'],narrative=' original '); binding=make_binding(request)
            claim=AuthContext(caller_id='U1',proof_reference='synthetic-proof')
            try:
                first=routes.reserve('RES1',attempt_id='A1',release_id='L1',binding=binding,request=request,auth_claim=claim,execution=scope)
                for changed in (make_request(evidence_ids=['E2','E1'],narrative=' original '),
                        make_request(evidence_ids=['E1','E2'],narrative='original'),
                        make_request(evidence_ids=['E1','E2'],narrative=' original ',consent_revision='v2')):
                    with self.subTest(request=changed):
                        with self.assertRaises(RouteFoundationFailure):
                            routes.reserve('RES1',attempt_id='A1',release_id='L1',binding=make_binding(changed),request=changed,auth_claim=claim,execution=scope)
                for alias in (claim.model_dump(),ClaimAlias(**claim.model_dump())):
                    with self.subTest(alias=type(alias).__name__):
                        with self.assertRaises(RouteFoundationFailure):
                            routes.reserve('RES1',attempt_id='A1',release_id='L1',binding=binding,request=request,auth_claim=alias,execution=scope)
                self.assertEqual(routes.get('RES1',execution=scope),first)
            finally: routes.close()

    def test_each_unique_key_collision_preserves_original_and_generation_route(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); control=root/'control'; control.mkdir()
            scope=ExecutionContext(NOW+timedelta(seconds=5),NOW,10.0,15.0)
            routes=AdmissionRouteStoreV1(control,database_name='routes.sqlite',registry=registry_at(root),clock=Clock(),execution=scope)
            request=make_request(); binding=make_binding(request); claim=AuthContext(caller_id='U1',proof_reference='synthetic-proof')
            try:
                first=routes.reserve('RES1',attempt_id='A1',release_id='L1',binding=binding,request=request,auth_claim=claim,execution=scope)
                for reservation,attempt in [('RES1','A2'),('RES2','A1'),('RES2','A2')]:
                    with self.subTest(reservation=reservation,attempt=attempt):
                        with self.assertRaises(RouteFoundationFailure):
                            routes.reserve(reservation,attempt_id=attempt,release_id='L1',binding=binding,request=request,auth_claim=claim,execution=scope)
                self.assertEqual(routes.for_generation('R1','C1','G1',execution=scope),first)
                self.assertIsNone(routes.get('missing',execution=scope))
                second=routes.reserve('RES2',attempt_id='A2',release_id='L1',binding=make_binding(generation='G2',supersedes_generation='G1'),request=request,auth_claim=claim,execution=scope)
                self.assertIsInstance(second,RouteRecordV1)
                self.assertEqual(second.binding.supersedes_generation,'G1')
            finally: routes.close()

    def test_limits_deny_aliases_and_widening(self):
        for values in ({'max_routes':True},{'max_routes':4097},{'max_row_bytes':0},
                {'max_release_bytes':33554433},{'max_routes_bytes':8388609},
                {'max_operation_seconds':5},{'max_operation_seconds':float('nan')},
                {'max_sqlite_steps':1000001}):
            with self.subTest(values=values):
                with self.assertRaises(RouteFoundationFailure): RouteLimitsV1(**values)

    def test_expiry_reversal_and_fresh_explicit_context(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); control=root/'control'; control.mkdir(); clock=MutableClock()
            scope=ExecutionContext(NOW+timedelta(seconds=5),NOW,10.0,15.0)
            routes=AdmissionRouteStoreV1(control,database_name='routes.sqlite',registry=registry_at(root),clock=clock,execution=scope)
            try:
                for utc,mono in [(NOW-timedelta(seconds=1),10.0),(NOW,9.0),(NOW+timedelta(seconds=5),15.0)]:
                    clock.utc,clock.mono=utc,mono
                    with self.subTest(utc=utc,mono=mono):
                        with self.assertRaises(RouteFoundationFailure): routes.get('RES1',execution=scope)
                clock.utc,clock.mono=NOW+timedelta(seconds=6),16.0
                fresh=ExecutionContext(clock.utc+timedelta(seconds=5),clock.utc,16.0,21.0)
                self.assertIsNone(routes.get('RES1',execution=fresh))
            finally: routes.close()
            routes.close()

    def test_control_root_alias_and_second_owner_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); control=root/'control'; control.mkdir()
            registry=registry_at(root); scope=ExecutionContext(NOW+timedelta(seconds=5),NOW,10.0,15.0)
            with self.assertRaises(RouteFoundationFailure):
                AdmissionRouteStoreV1(root,database_name='routes.sqlite',registry=registry,clock=Clock(),execution=scope)
            routes=AdmissionRouteStoreV1(control,database_name='routes.sqlite',registry=registry,clock=Clock(),execution=scope)
            try:
                with self.assertRaises(RouteFoundationFailure):
                    AdmissionRouteStoreV1(control,database_name='routes.sqlite',registry=registry,clock=Clock(),execution=scope)
            finally: routes.close()

    def test_full_stored_row_threshold_counts_index_projections(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); control=root/'control'; control.mkdir(); clock=Clock()
            scope=ExecutionContext(NOW+timedelta(seconds=5),NOW,10.0,15.0)
            row=literal_route(root)
            full={k:row[k] for k in ('reservation_id','attempt_id','resource_id','case_id','generation','release_id','state')}
            exact=len(cj(dict(full,record=row)))
            self.assertGreater(exact,len(cj(row)))
            for size in (exact-1,exact):
                routes=AdmissionRouteStoreV1(control,database_name=f'routes{size}.sqlite',registry=registry_at(root),clock=clock,
                    execution=scope,limits=RouteLimitsV1(max_row_bytes=size))
                try:
                    if size < exact:
                        with self.assertRaises(RouteFoundationFailure) as failure:
                            routes.reserve('RES1',attempt_id='A1',release_id='L1',binding=make_binding(),request=make_request(),
                                auth_claim=AuthContext(caller_id='U1',proof_reference='synthetic-proof'),execution=scope)
                        self.assertEqual(failure.exception.code,'limit')
                    else:
                        self.assertEqual(routes.reserve('RES1',attempt_id='A1',release_id='L1',binding=make_binding(),request=make_request(),
                            auth_claim=AuthContext(caller_id='U1',proof_reference='synthetic-proof'),execution=scope).wire_bytes,cj(row))
                finally: routes.close()
    def test_registry_wire_validation_rejects_rehashed_semantic_drift(self):
        import base64
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for blob_name, key, bad in [('source','mode','actual'), ('proposal','candidate_profile_hash','0'*64),
                    ('regression','execution','passed'), ('migration','strategy','migrate'),
                    ('agent','authorship','verified'), ('dependency','completeness','actual'),
                    ('policy','automatic_reminders', True), ('profile','version','tampered')]:
                with self.subTest(blob=blob_name):
                    value = literal_envelope(root)
                    content = json.loads(base64.b64decode(value['blobs'][blob_name]['base64']))
                    content[key] = bad
                    raw = cj(content)
                    value['blobs'][blob_name] = dict(base64=base64.b64encode(raw).decode(), sha256=sha256(raw).hexdigest())
                    with self.assertRaises(RouteFoundationFailure): RegisteredReleaseV1(rehash(value))
            for change in ('extra', 'bool_version', 'bad_pin', 'account', 'unsafe_name', 'bad_base64'):
                with self.subTest(change=change):
                    value = literal_envelope(root)
                    if change == 'extra': value['authority'] = 'approved'
                    if change == 'bool_version': value['version'] = True
                    if change == 'bad_pin': value['factory']['implementation_pins'][0]['sha256'] = '0'*64
                    if change == 'account': value['resource']['account_ids'] = []
                    if change == 'unsafe_name': value['implementations'][0]['name'] = '../escape'
                    if change == 'bad_base64': value['implementations'][0]['base64'] = '===='
                    with self.assertRaises(RouteFoundationFailure): RegisteredReleaseV1(rehash(value))
            for raw in (b'{}', b'{"version":1,"version":1}', b' NaN ', b'[]', cj(literal_envelope(root))+b' '):
                with self.subTest(raw=raw[:30]):
                    with self.assertRaises(RouteFoundationFailure): RegisteredReleaseV1(raw)

    def test_registry_returns_closed_synthetic_release(self):
        with tempfile.TemporaryDirectory() as d:
            registered = registry_at(Path(d)).resolve("L1")
            self.assertIsInstance(registered, RegisteredReleaseV1)
            body = json.loads(registered.wire_bytes)
            self.assertEqual(body["mode"], "offline_synthetic")
            self.assertEqual(body["artifact_hash"], fingerprint({k:v for k,v in body.items() if k != "artifact_hash"}))

    def test_reserved_route_survives_restart_and_cannot_rebind(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); registry = registry_at(root); clock = Clock()
            control = root / 'route-control'; control.mkdir()
            scope = ExecutionContext(NOW+timedelta(seconds=5), NOW, 10.0, 15.0)
            request = make_request(); binding = make_binding(request)
            claim = AuthContext(caller_id="U1", proof_reference="synthetic-proof")
            routes = AdmissionRouteStoreV1(control, database_name="routes.sqlite",
                registry=registry, clock=clock, execution=scope)
            first = routes.reserve("RES1", attempt_id="A1", release_id="L1",
                binding=binding, request=request, auth_claim=claim, execution=scope)
            self.assertIsInstance(first, RouteRecordV1)
            routes.close()
            routes = AdmissionRouteStoreV1(control, database_name="routes.sqlite",
                registry=registry, clock=clock, execution=scope)
            try:
                self.assertEqual(routes.get("RES1", execution=scope), first)
                self.assertEqual(routes.reserve("RES1", attempt_id="A1", release_id="L1",
                    binding=binding, request=request, auth_claim=claim, execution=scope), first)
                with self.assertRaises(RouteFoundationFailure) as failure:
                    routes.reserve("RES2", attempt_id="A1", release_id="L1",
                        binding=binding, request=request, auth_claim=claim, execution=scope)
                self.assertEqual(failure.exception.code, "conflict")
                self.assertEqual(first.state, "reserved")
                self.assertFalse((root/"journal.sqlite").exists())
                self.assertFalse((root/"world.sqlite").exists())
            finally: routes.close()

    def test_admitted_observation_joins_original_and_preserves_journal(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); registry = registry_at(root); clock = Clock()
            control = root / 'route-control'; control.mkdir()
            scope = ExecutionContext(NOW+timedelta(seconds=5), NOW, 10.0, 15.0)
            request = make_request(); binding = make_binding(request)
            claim = AuthContext(caller_id="U1", proof_reference="synthetic-proof")
            routes = AdmissionRouteStoreV1(control, database_name="routes.sqlite",
                registry=registry, clock=clock, execution=scope)
            journal = CaseStore(root/"journal.sqlite")
            try:
                reserved = routes.reserve("RES1", attempt_id="A1", release_id="L1",
                    binding=binding, request=request, auth_claim=claim, execution=scope)
                journal.start_admission("A1", claim, request, NOW, NOW+timedelta(seconds=5))
                checkpoint = make_checkpoint(binding=binding, profile_version="v1.3",
                    process_version="v1", policy_version="v1")
                journal.admit_from_attempt("A1", binding, request, checkpoint)
                before = journal.capture_retained_state(execution=scope, clock=clock)
                admitted = routes.observe_admitted("RES1", snapshot=before, execution=scope)
                self.assertIsInstance(admitted, RouteRecordV1)
                self.assertEqual(admitted.state, "admission_observed")
                self.assertEqual(admitted.binding, binding)
                self.assertEqual(admitted.artifact_hash, reserved.artifact_hash)
                self.assertEqual(journal.capture_retained_state(execution=scope,
                    clock=clock).payload, before.payload)
                self.assertEqual(routes.observe_admitted("RES1", snapshot=before,
                    execution=scope), admitted)
            finally:
                journal.close(); routes.close()

    def test_rehashed_implementation_drift_cannot_match_registered_inventory(self):
        import base64
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); registered = registry_at(root).resolve("L1")
            body = json.loads(registered.wire_bytes)
            blob = body["implementations"][0]
            blob["base64"] = base64.b64encode(b"different synthetic bytes").decode("ascii")
            blob["sha256"] = sha256(b"different synthetic bytes").hexdigest()
            body["artifact_hash"] = fingerprint({k:v for k,v in body.items() if k != "artifact_hash"})
            with self.assertRaises(RouteFoundationFailure) as failure:
                RegisteredReleaseV1(cj(body))
            self.assertEqual(failure.exception.code, "invalid")
            profile = registered.profile
            object.__setattr__(profile, "profile_id", "caller-mutated")
            self.assertEqual(registered.profile.profile_id, "flat-v1.3")

    def test_same_business_fingerprint_does_not_hide_changed_narrative(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); control = root / "route-control"; control.mkdir()
            clock = Clock(); scope = ExecutionContext(NOW+timedelta(seconds=5), NOW, 10.0, 15.0)
            request = make_request(narrative="first")
            binding = make_binding(request)
            claim = AuthContext(caller_id="U1", proof_reference="synthetic-proof")
            routes = AdmissionRouteStoreV1(control, database_name="routes.sqlite",
                registry=registry_at(root), clock=clock, execution=scope)
            try:
                first = routes.reserve("RES1", attempt_id="A1", release_id="L1",
                    binding=binding, request=request, auth_claim=claim, execution=scope)
                changed = make_request(narrative="second")
                self.assertEqual(make_binding(changed).fingerprint, binding.fingerprint)
                with self.assertRaises(RouteFoundationFailure) as failure:
                    routes.reserve("RES1", attempt_id="A1", release_id="L1",
                        binding=binding, request=changed, auth_claim=claim, execution=scope)
                self.assertEqual(failure.exception.code, "conflict")
                self.assertEqual(routes.get("RES1", execution=scope), first)
            finally: routes.close()

    def test_foreign_empty_database_is_not_repaired_or_overwritten(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); control = root / "route-control"; control.mkdir()
            database = control / "routes.sqlite"
            with sqlite3.connect(database) as db:
                db.execute("CREATE TABLE foreign_data(value TEXT)")
                db.execute("INSERT INTO foreign_data VALUES('retain me')")
            before = database.read_bytes()
            clock = Clock(); scope = ExecutionContext(NOW+timedelta(seconds=5), NOW, 10.0, 15.0)
            with self.assertRaises(RouteFoundationFailure) as failure:
                AdmissionRouteStoreV1(control, database_name="routes.sqlite",
                    registry=registry_at(root), clock=clock, execution=scope)
            self.assertEqual(failure.exception.code, "storage")
            self.assertEqual(database.read_bytes(), before)
            with sqlite3.connect(database) as db:
                self.assertEqual(db.execute("SELECT value FROM foreign_data").fetchall(), [("retain me",)])
