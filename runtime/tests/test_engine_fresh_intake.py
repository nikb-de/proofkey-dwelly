from dataclasses import asdict
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
import tempfile
import threading
import unittest
from unittest.mock import patch

from proofkey.adapters.world import SimulatedWorld
from proofkey.contracts import (CaseResult, InvocationRequest, ProcessingReceipt,
    ProcessorIdentity, ScopedReply)
from proofkey.engine import WorkflowEngine
from proofkey.evidence.catalog import EvidenceCatalog
from proofkey.evidence.processing_contracts import ProcessingCatalogBindings, SavedOriginalScope, canonical
from proofkey.execution import ExecutionContext
from proofkey.gateway import ActionGateway
from proofkey.identity import fingerprint, request_fingerprint
from proofkey.journal import CaseStore, JournalFailure
from proofkey.processing import RoleAdmissionLimits
from proofkey.processing_orchestration import ProcessingOrchestrator, ProcessingRecipe
from proofkey.processing_summary import ProcessingSummaryV1
from support import DEADLINE, FakeClock, load_test_profile, make_auth, make_fixture_campaign, make_request

class IntakeClock(FakeClock):
    def __init__(self):
        super().__init__()
        self.tick = 100.0

    def monotonic(self):
        return self.tick

    def advance(self, seconds):
        super().advance(seconds)
        self.tick += seconds

class FreshIntakeTests(unittest.TestCase):
    def assert_denied(self, value):
        self.assertEqual(value.model_dump(mode='json'),
            CaseResult(status='denied', correlation_id='C1', reason='denied').model_dump(mode='json'))

    def test_invalid_mutated_catalog_ceiling_denies_before_original_io(self):
        class IntAlias(int):
            pass
        for limit in (9 * 1024 * 1024, float(8 * 1024 * 1024), True, 0, IntAlias(8 * 1024 * 1024)):
            with self.subTest(limit=limit, limit_type=type(limit).__name__):
                fx = self.fixture(evidence=True)
                fx.catalog.max_bytes = limit
                entered = []
                actual = fx.catalog.get
                def get(*args, **kwargs):
                    entered.append(True)
                    return actual(*args, **kwargs)
                with patch.object(fx.catalog, 'get', get):
                    result = fx.engine.run(fx.request, fx.auth, execution=self.execution(fx))
                self.assert_denied(result)
                self.assertEqual(entered, [])
                self.assert_no_processing(fx)

    def test_catalog_ceiling_change_after_real_original_read_denies(self):
        for delta in (1024, -1024):
            with self.subTest(delta=delta):
                fx = self.fixture(evidence=True)
                limit = fx.catalog.max_bytes
                actual = fx.catalog.read_original
                read_values = []
                def read(identifier, auth=None, *, purpose='read', max_bytes=None):
                    value = actual(identifier, auth, purpose=purpose, max_bytes=max_bytes)
                    read_values.append((value, max_bytes))
                    fx.catalog.max_bytes = limit + delta
                    return value
                with patch.object(fx.catalog, 'read_original', read):
                    result = fx.engine.run(fx.request, fx.auth, execution=self.execution(fx))
                self.assertEqual(read_values,
                    [(b'PRIVATE original evidence; not semantic proof.\n', 8 * 1024 * 1024)])
                self.assert_denied(result)
                self.assert_no_processing(fx)

    def test_last_journal_read_cannot_hide_saved_ownership_change(self):
        fx = self.fixture(evidence=True)
        actual_stop = fx.store.generation_stop
        fired = []
        def generation_stop(binding):
            result = actual_stop(binding)
            if fired:
                cp = fx.store.checkpoint('C1')
                fx.store.save_checkpoint(cp.model_copy(update={'ownership_epoch': cp.ownership_epoch + 1}))
            return result
        actual_read = fx.catalog.read_original
        def read(*args, **kwargs):
            value = actual_read(*args, **kwargs)
            fired.append(True)
            return value
        with patch.object(fx.catalog, 'read_original', read), \
                patch.object(fx.store, 'generation_stop', generation_stop):
            self.assert_denied(fx.engine.run(fx.request, fx.auth, execution=self.execution(fx)))
        self.assertTrue(fired)
        self.assert_no_processing(fx)

    def test_missing_scope_id_and_catalog_failures_are_generic(self):
        for mode in ('scope', 'missing', 'permission', 'storage', 'value'):
            with self.subTest(mode=mode):
                fx = self.fixture(narrative='PRIVATE' if mode == 'scope' else None,
                    evidence=mode != 'scope')
                if mode == 'scope':
                    fx.revoked = True
                    self.assert_denied(fx.engine.run(fx.request, fx.auth, execution=self.execution(fx)))
                elif mode == 'missing':
                    fx.request = make_request(evidence_ids=['missing-original'])
                    fx.world.mutate('customer.request_fingerprint', request_fingerprint(fx.request))
                    self.assert_denied(fx.engine.run(fx.request, fx.auth, execution=self.execution(fx)))
                else:
                    error = {'permission': PermissionError, 'storage': OSError, 'value': ValueError}[mode]
                    with patch.object(fx.catalog, 'get', side_effect=error('PRIVATE path')):
                        self.assert_denied(fx.engine.run(fx.request, fx.auth, execution=self.execution(fx)))
                self.assert_no_processing(fx)

    def test_process_exit_is_not_swallowed_and_partial_narrative_is_retained(self):
        fx = self.fixture(narrative='PRIVATE surviving partial bytes')
        actual = fx.catalog.register_saved_narrative
        records = []
        def register(binding, auth):
            records.append(actual(binding, auth))
            raise KeyboardInterrupt('controlled process exit')
        with patch.object(fx.catalog, 'register_saved_narrative', register), self.assertRaises(KeyboardInterrupt):
            fx.engine.run(fx.request, fx.auth, execution=self.execution(fx))
        self.assertEqual(fx.catalog.read_original(records[0].artifact_id, fx.auth), fx.request.narrative.encode())
        self.assert_no_processing(fx)

    def test_record_identity_and_integrity_changes_are_denied(self):
        for mode in ('id', 'hash', 'post_read_record'):
            with self.subTest(mode=mode):
                fx = self.fixture(evidence=True)
                actual_get, actual_read = fx.catalog.get, fx.catalog.read_original
                read_done = []
                def read(*args, **kwargs):
                    data = actual_read(*args, **kwargs)
                    read_done.append(True)
                    return data
                def get(*args, **kwargs):
                    result = actual_get(*args, **kwargs)
                    change = ({'artifact_id': 'different-original'} if mode == 'id' else
                        {'original_hash': '1' * 64} if mode == 'hash' else
                        {'source': 'changed-original'} if read_done else {})
                    return result.model_copy(update=change)
                with patch.object(fx.catalog, 'get', get), patch.object(fx.catalog, 'read_original', read):
                    self.assert_denied(fx.engine.run(fx.request, fx.auth, execution=self.execution(fx)))
                self.assert_no_processing(fx)

    def test_saved_versions_ownership_and_original_are_fenced(self):
        changes = ({'profile_version': 'other'}, {'process_version': 'other'}, {'policy_version': 'other'},
            {'ownership_state': 'pending'}, {'ownership_state': 'transfer_pending'},
            {'ownership_state': 'stopped'}, {'ownership_state_revision': 'v2'}, {'ownership_epoch': 1})
        for change in changes:
            with self.subTest(change=change):
                fx = self.fixture(evidence=True)
                actual = fx.catalog.read_original
                def read(*args, **kwargs):
                    data = actual(*args, **kwargs)
                    cp = fx.store.checkpoint('C1')
                    fx.store.save_checkpoint(cp.model_copy(update=change))
                    return data
                with patch.object(fx.catalog, 'read_original', read):
                    self.assert_denied(fx.engine.run(fx.request, fx.auth, execution=self.execution(fx)))
                self.assert_no_processing(fx)

    def test_final_acl_read_time_and_fixed_association_are_fenced(self):
        for mode in ('expiry', 'utc', 'monotonic', 'association'):
            with self.subTest(mode=mode):
                fx = self.fixture(evidence=True)
                execution = self.execution(fx)
                fx.clock.advance(2)
                actual_get, actual_read = fx.catalog.get, fx.catalog.read_original
                read_done = []
                def read(*args, **kwargs):
                    value = actual_read(*args, **kwargs)
                    read_done.append(True)
                    return value
                def get(*args, **kwargs):
                    value = actual_get(*args, **kwargs)
                    if read_done:
                        if mode == 'expiry': fx.clock.advance(31)
                        elif mode == 'utc': fx.clock._now -= timedelta(seconds=1)
                        elif mode == 'monotonic': fx.clock.tick -= 1
                        else: fx.engine.evidence = object()
                    return value
                with patch.object(fx.catalog, 'get', get), patch.object(fx.catalog, 'read_original', read):
                    self.assert_denied(fx.engine.run(fx.request, fx.auth, execution=execution))
                self.assert_no_processing(fx)

    def test_reentry_foreign_thread_and_initial_association_deny_before_intake(self):
        fx = self.fixture(evidence=True)
        nested = []
        actual = fx.catalog.read_original
        def read(*args, **kwargs):
            nested.append(fx.engine.run(fx.request, fx.auth))
            return actual(*args, **kwargs)
        with patch.object(fx.catalog, 'read_original', read):
            result = fx.engine.run(fx.request, fx.auth, execution=self.execution(fx))
        self.assertEqual(result.media_status, 'unavailable')
        self.assert_denied(nested[0])
        foreign = []
        thread = threading.Thread(target=lambda: foreign.append(fx.engine.run(fx.request, fx.auth)))
        thread.start()
        thread.join()
        self.assert_denied(foreign[0])
        with patch.object(fx.engine, 'evidence', object()), \
                patch.object(fx.catalog, 'get', side_effect=AssertionError('foreign intake')):
            self.assert_denied(fx.engine.run(fx.request, fx.auth))
        self.assert_no_processing(fx)

    def test_structured_whitespace_legacy_and_replay_never_enter_catalog(self):
        for mode in ('structured', 'whitespace', 'legacy'):
            with self.subTest(mode=mode):
                fx = self.fixture(narrative=' \n\t' if mode == 'whitespace' else 'PRIVATE' if mode == 'legacy' else None)
                if mode == 'legacy':
                    fx.engine = WorkflowEngine(fx.profile, fx.bundle, fx.store, fx.clock)
                with patch.object(fx.catalog, 'get', side_effect=AssertionError('unexpected read')), \
                        patch.object(fx.catalog, 'register_saved_narrative', side_effect=AssertionError('unexpected publish')):
                    result = fx.engine.run(fx.request, fx.auth, execution=self.execution(fx))
                    if mode == 'structured':
                        self.assertEqual(result.effects['reschedule'].status, 'verified')
                        replay = fx.engine.run(fx.request, fx.auth, execution=self.execution(fx))
                        self.assertTrue(replay.historical)
                    else:
                        self.assertEqual(result.media_status, 'none' if mode == 'whitespace' else 'unavailable')
                self.assertEqual(fx.store.processing_attempts(fx.store.checkpoint('C1').binding), ())
                self.assertEqual(fx.store.checkpoint('C1').budget.max_planner_calls, 4 if mode == 'legacy' else 0)

    def test_retry_recover_and_summary_keep_identity_caps_and_local_history(self):
        fx = self.fixture(narrative='PRIVATE exact retry')
        records = []
        actual = fx.catalog.register_saved_narrative
        def register(*args, **kwargs):
            value = actual(*args, **kwargs)
            records.append(value)
            return value
        with patch.object(fx.catalog, 'register_saved_narrative', register):
            self.assertEqual(fx.engine.run(fx.request, fx.auth).media_status, 'unavailable')
            before = fx.store.checkpoint('C1')
            self.assertEqual(fx.engine.run(fx.request, fx.auth).media_status, 'unavailable')
            self.assertEqual(len(records), 1)  # Later phase never rewinds implicitly.
            fx.store.save_checkpoint(before.model_copy(update={'phase': 'intake', 'next_gate': 'extract_input'}))
            self.assertEqual(fx.engine.run(fx.request, fx.auth).media_status, 'unavailable')
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0], records[1])
        with patch.object(fx.catalog, 'get', side_effect=AssertionError('implicit intake')):
            self.assertEqual(fx.engine.recover('C1', fx.auth).media_status, 'unavailable')
            copied = WorkflowEngine(fx.profile, fx.bundle, fx.store, fx.clock,
                evidence=fx.catalog, processing=fx.processing)
            summary = copied.processing_summary('C1', fx.auth)
        self.assertEqual(summary.entry_local, ())
        self.assertEqual(set(asdict(summary)), {'binding_bytes', 'as_of', 'attempts', 'entry_local'})
        self.assertEqual(fx.store.checkpoint('C1').budget.role_allowances, before.budget.role_allowances)
        self.assertEqual(fx.store.checkpoint('C1').deadline, before.deadline)
        self.assert_no_processing(fx)

    def test_narrative_byte_preflight_precedes_publication(self):
        fx = self.fixture(narrative='é' * 5)
        fx.catalog.max_bytes = 9
        entered = []
        real = fx.catalog.register_saved_narrative
        def register(binding, auth):
            entered.append(binding)
            return real(binding, auth)
        with patch.object(fx.catalog, 'register_saved_narrative', register):
            self.assert_denied(fx.engine.run(fx.request, fx.auth, execution=self.execution(fx)))
        self.assertEqual(entered, [])
        self.assert_no_processing(fx)

    def test_pending_saved_ownership_blocks_content_before_io(self):
        fx = self.fixture(evidence=True)
        self.assertEqual(fx.engine.run(fx.request, fx.auth).media_status, 'unavailable')
        cp = fx.store.checkpoint('C1')
        fx.store.save_checkpoint(cp.model_copy(update={'phase': 'intake', 'next_gate': 'extract_input',
            'ownership_state': 'pending'}))
        with patch.object(fx.catalog, 'get', side_effect=AssertionError('pending owner read')):
            self.assert_denied(fx.engine.run(fx.request, fx.auth))
        self.assert_no_processing(fx)

    def test_narrative_then_original_evidence_order_and_current_original_fence(self):
        for change_original in (False, True):
            with self.subTest(change_original=change_original):
                fx = self.fixture(narrative=' exact narrative\n', evidence=True)
                source = fx.root / 'second.txt'
                source.write_bytes(b'second original')
                second = fx.catalog.register(source, 'C1', 'ordinary-independent-original',
                    {'allowed_actors': ['U1'], 'scope_id': 'fixture-input'})
                fx.request = make_request(narrative=fx.request.narrative,
                    evidence_ids=[fx.evidence.artifact_id, second.artifact_id])
                fx.world.mutate('customer.request_fingerprint', request_fingerprint(fx.request))
                actual_read, actual_original = fx.catalog.read_original, fx.store.original_request
                reads = []
                def read(identifier, *args, **kwargs):
                    data = actual_read(identifier, *args, **kwargs)
                    reads.append((identifier, data))
                    return data
                def original(*args, **kwargs):
                    value = actual_original(*args, **kwargs)
                    if change_original and len(reads) == 3:
                        return value.model_copy(update={'narrative': 'different'})
                    return value
                with patch.object(fx.catalog, 'read_original', read), \
                        patch.object(fx.store, 'original_request', original):
                    result = fx.engine.run(fx.request, fx.auth, execution=self.execution(fx))
                self.assertEqual([data for _, data in reads],
                    [fx.request.narrative.encode(), b'PRIVATE original evidence; not semantic proof.\n', b'second original'])
                self.assertEqual([identifier for identifier, _ in reads][1:], fx.request.evidence_ids)
                if change_original:
                    self.assert_denied(result)
                else:
                    self.assertEqual(result.media_status, 'unavailable')
                self.assert_no_processing(fx)

    def test_exact_same_case_original_record_boundary(self):
        from proofkey.contracts import ArtifactRecord
        class RecordAlias(ArtifactRecord):
            pass
        cases = ('foreign', 'parent', 'saved-planning-snapshot-v1',
            'saved-planning-evidence-v2', 'saved-synthetic-transcription', 'alias')
        for case in cases:
            with self.subTest(case=case):
                fx = self.fixture(evidence=True)
                real = fx.catalog.get
                def get(identifier, auth=None, *, purpose='read'):
                    record = real(identifier, auth, purpose=purpose)
                    if case == 'alias':
                        return RecordAlias(**record.model_dump())
                    changes = ({'case_id': 'FOREIGN'} if case == 'foreign' else
                        {'parent_hashes': ['1' * 64]} if case == 'parent' else {'source': case})
                    return record.model_copy(update=changes)
                with patch.object(fx.catalog, 'get', get):
                    self.assert_denied(fx.engine.run(fx.request, fx.auth, execution=self.execution(fx)))
                self.assert_no_processing(fx)

    def test_payload_is_exact_bytes_and_aggregate_is_bounded(self):
        fx = self.fixture(evidence=True)
        real = fx.catalog.read_original
        def read(identifier, auth=None, **kwargs):
            return bytearray(real(identifier, auth, **kwargs))
        with patch.object(fx.catalog, 'read_original', read):
            self.assert_denied(fx.engine.run(fx.request, fx.auth, execution=self.execution(fx)))
        self.assert_no_processing(fx)
        fx = self.fixture(evidence=True)
        source = fx.root / 'aggregate.txt'
        source.write_bytes(b'x' * 4000)
        first = fx.catalog.register(source, 'C1', 'first-original',
            {'allowed_actors': ['U1'], 'scope_id': 'fixture-input'})
        source.write_bytes(b'y' * 4000)
        second = fx.catalog.register(source, 'C1', 'second-original',
            {'allowed_actors': ['U1'], 'scope_id': 'fixture-input'})
        fx.request = make_request(evidence_ids=[first.artifact_id, second.artifact_id])
        fx.world.mutate('customer.request_fingerprint', request_fingerprint(fx.request))
        fx.catalog.max_bytes = 7000
        self.assert_denied(fx.engine.run(fx.request, fx.auth, execution=self.execution(fx)))
        self.assert_no_processing(fx)

    def test_local_utc_and_scoped_monotonic_reversal_above_capture_denies(self):
        for field in ('utc', 'monotonic'):
            with self.subTest(field=field):
                fx = self.fixture(evidence=True)
                execution = self.execution(fx)
                fx.clock.advance(2)
                real = fx.catalog.read_original
                def read(identifier, auth=None, **kwargs):
                    data = real(identifier, auth, **kwargs)
                    if field == 'utc':
                        fx.clock._now -= timedelta(seconds=1)
                    else:
                        fx.clock.tick -= 1
                    return data
                with patch.object(fx.catalog, 'read_original', read):
                    self.assert_denied(fx.engine.run(fx.request, fx.auth, execution=execution))
                self.assert_no_processing(fx)

    def test_saved_phase_gate_stop_and_deadline_drift_after_read_denies(self):
        for field in ('phase', 'next_gate', 'stop', 'deadline'):
            with self.subTest(field=field):
                fx = self.fixture(evidence=True)
                real = fx.catalog.read_original
                def read(identifier, auth=None, **kwargs):
                    data = real(identifier, auth, **kwargs)
                    cp = fx.store.checkpoint('C1')
                    if field == 'stop':
                        fx.store.set_stop('C1', cp.binding.generation)
                    else:
                        change = ({'phase': 'completeness'} if field == 'phase' else
                            {'next_gate': 'check_completeness'} if field == 'next_gate' else
                            {'deadline': cp.deadline - timedelta(seconds=1)})
                        fx.store.save_checkpoint(cp.model_copy(update=change))
                    return data
                with patch.object(fx.catalog, 'read_original', read):
                    self.assert_denied(fx.engine.run(fx.request, fx.auth, execution=self.execution(fx)))
                self.assert_no_processing(fx)

    def fixture(self, *, narrative=None, evidence=False, extraction_calls=2):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        root = Path(folder.name).resolve()
        fx = SimpleNamespace(root=root, clock=IntakeClock(),
            profile=load_test_profile('flat-v1.2'), store=CaseStore(root / 'journal.sqlite'),
            auth=make_auth(), request=make_request(narrative=narrative),
            revoked=False, ids=[], evidence=None)
        self.addCleanup(fx.store.close)

        def original(binding):
            actual = fx.store.find_request(binding.case_id, binding.request_id,
                binding.request_revision, binding.consent_revision, binding.fingerprint)
            if actual != binding:
                raise ValueError('Exact original binding required')
            return fx.store.original_request(binding.case_id, binding.generation)

        def scope(binding, saved, auth, purpose):
            if saved != fx.request or auth != fx.auth or fx.revoked or fx.clock.now() >= DEADLINE:
                return None
            raw = dict(allowed_actors=['U1'], case_id=binding.case_id,
                object_id=binding.object_id, binding_hash=fingerprint(binding.model_dump(mode='json')),
                original_request_hash=fingerprint(saved.model_dump(mode='json')),
                scope_id='saved-scope', policy_id='local-policy',
                authorization_reference='synthetic-proof',
                provenance='synthetic_host_registration', expires_at=DEADLINE.isoformat())
            return SavedOriginalScope(canonical(binding.model_dump(mode='json')),
                raw['original_request_hash'], 'saved-scope', canonical(raw),
                'local-policy', 'synthetic_host_registration', 'synthetic-proof', DEADLINE)

        def access(auth, record, source_scope, purpose):
            return (auth == fx.auth and not fx.revoked and record.case_id == 'C1'
                and source_scope.get('allowed_actors') == ('U1',)
                and source_scope.get('scope_id') in {'saved-scope', 'fixture-input'})

        fx.catalog = EvidenceCatalog(root / 'catalog', fx.clock,
            allowed_input_roots=[root], access_resolver=access,
            processing_bindings=ProcessingCatalogBindings(original,
                lambda binding: fx.store.checkpoint(binding.case_id),
                fx.store.invocation, scope, profile_lookup=lambda binding, saved: fx.profile))
        if evidence:
            source = root / 'source.txt'
            source.write_bytes(b'PRIVATE original evidence; not semantic proof.\n')
            fx.evidence = fx.catalog.register(source, 'C1', 'synthetic-intake-evidence',
                {'allowed_actors': ['U1'], 'scope_id': 'fixture-input'})
            fx.request = make_request(narrative=narrative,
                evidence_ids=[fx.evidence.artifact_id])
        fx.world = SimulatedWorld(root / 'world.sqlite',
            Path(__file__).resolve().parents[1] / 'fixtures/development/world.json',
            profile=fx.profile, clock=fx.clock)
        fx.world.mutate('customer.request_fingerprint', request_fingerprint(fx.request))
        fx.world.mutate('customer.consent_mode', fx.request.consent_mode)
        fx.bundle = fx.world.bundle()
        allowances = (
            RoleAdmissionLimits('extraction', extraction_calls, (('tokens', float(extraction_calls * 2)),), float(extraction_calls)),
            RoleAdmissionLimits('planning', 1, (('tokens', 2.0),), 1.0))
        recipe = ProcessingRecipe(allowances=allowances, planning_registrations=())
        fx.gateway = ActionGateway(fx.profile, fx.bundle, fx.store, fx.clock,
            auth=fx.auth, processing_allowances=recipe.allowances)

        def no_invocation():
            fx.ids.append('unexpected')
            raise AssertionError('Intake cannot allocate an invocation')

        fx.processing = ProcessingOrchestrator(fx.store, fx.clock, fx.catalog,
            parent_gateway=fx.gateway, recipe=recipe, invocation_id_factory=no_invocation)
        fx.engine = WorkflowEngine(fx.profile, fx.bundle, fx.store, fx.clock,
            evidence=fx.catalog, processing=fx.processing)
        return fx

    def execution(self, fx):
        return ExecutionContext.capture(fx.clock.now() + timedelta(seconds=30), fx.clock)

    def test_all_five_prior_statuses_and_case_role_campaign_debt_survive_intake(self):
        fx = self.fixture(evidence=True, extraction_calls=5)
        self.assertEqual(fx.engine.run(fx.request, fx.auth).media_status, 'unavailable')
        cp = fx.store.checkpoint('C1')
        grant = make_fixture_campaign(input_hashes=[fx.evidence.original_hash],
            max_invocations=5, max_usage={'tokens': 10.0}, max_cost=5.0)
        fx.store.register_campaign(grant)  # Explicit test-host synthetic producer, not engine permission.
        ordered = (('z-complete', 'completed'), ('m-none', None), ('b-failed', 'failed'),
            ('a-unknown', 'outcome_unknown'), ('q-unavailable', 'unavailable'))
        for identifier, status in ordered:
            identity = ProcessorIdentity(case_id='C1', generation=cp.binding.generation,
                role='extraction', campaign_id=grant.campaign_id, permit_hash=grant.permit_hash,
                input_hashes=grant.input_hashes, provider=grant.provider, model=grant.model,
                endpoint=grant.endpoint, prompt_hash='2' * 64, version='v1',
                profile_version=cp.profile_version, process_version=cp.process_version,
                deadline=fx.clock.now() + timedelta(seconds=1))
            fx.store.reserve_invocation(InvocationRequest(identity=identity, invocation_id=identifier,
                requested_usage={'tokens': 2.0}, worst_case_cost=1.0), fx.clock.now())
            if status is not None:
                fx.store.record_processing(identifier, ProcessingReceipt(invocation_id=identifier,
                    role='extraction', provider=identity.provider, requested_model=identity.model,
                    prompt_hash=identity.prompt_hash, version='v1', input_hashes=identity.input_hashes,
                    mode='synthetic', status=status, latency_seconds=0.0, usage={},
                    processed_at=fx.clock.now(), reason='PRIVATE historical synthetic status'))
        # Each original producer reserves one second; no settlement/refund or budget repair.
        before = fx.store.checkpoint('C1')
        attempts = fx.store.processing_attempts(cp.binding)
        campaign = fx.store.campaign_usage(grant.permit_hash)
        fx.store.save_checkpoint(before.model_copy(update={'phase': 'intake', 'next_gate': 'extract_input'}))
        self.assertEqual(fx.engine.run(fx.request, fx.auth, execution=self.execution(fx)).media_status, 'unavailable')
        after = fx.store.checkpoint('C1')
        self.assertEqual(fx.store.processing_attempts(cp.binding), attempts)
        self.assertEqual(fx.store.campaign_usage(grant.permit_hash), campaign)
        self.assertEqual(after.budget.role_allowances, before.budget.role_allowances)
        self.assertEqual(after.deadline, before.deadline)
        self.assertEqual(after.budget.max_tool_calls, before.budget.max_tool_calls)
        self.assertEqual(after.budget.max_active_seconds, before.budget.max_active_seconds)
        self.assertGreater(after.budget.tool_calls, before.budget.tool_calls)
        self.assertGreaterEqual(after.budget.active_seconds, before.budget.active_seconds)
        summary = fx.engine.processing_summary('C1', fx.auth, execution=self.execution(fx))
        self.assertEqual([a.invocation_id for a in summary.attempts], [i for i, _ in ordered])
        self.assertEqual([a.receipt_status for a in summary.attempts], [s for _, s in ordered])
        self.assertEqual([a.reservation_status for a in summary.attempts],
            ['completed', 'consumed', 'failed', 'outcome_unknown', 'failed'])
        self.assertEqual(fx.ids, [])
        self.assertEqual(fx.world.effect_count('reschedule'), 0)
        self.assertNotIn('PRIVATE historical', repr(asdict(summary)))

    def test_source_generation_and_revision_drift_after_read_deny(self):
        for key, value in (('case.generation', 'G2'), ('case.request_revision', 'v2')):
            with self.subTest(key=key):
                fx = self.fixture(evidence=True)
                actual = fx.catalog.read_original
                def read(*args, **kwargs):
                    data = actual(*args, **kwargs)
                    fx.world.mutate(key, value)
                    return data
                with patch.object(fx.catalog, 'read_original', read):
                    self.assert_denied(fx.engine.run(fx.request, fx.auth, execution=self.execution(fx)))
                self.assert_no_processing(fx)

    def test_reply_and_stopped_fresh_retry_cannot_intake(self):
        fx = self.fixture(evidence=True)
        self.assertEqual(fx.engine.run(fx.request, fx.auth).media_status, 'unavailable')
        cp = fx.store.checkpoint('C1')
        reply = ScopedReply(question_id='not-a-wait', binding=cp.binding, actor_id='U1',
            proof_reference=fx.auth.proof_reference, request_revision=cp.binding.request_revision,
            consent_revision=cp.binding.consent_revision, owner_state_revision='v1',
            fields={}, received_at=fx.clock.now(), simulated=True)
        with patch.object(fx.catalog, 'get', side_effect=AssertionError('implicit reply intake')), \
                patch.object(fx.catalog, 'read_original', side_effect=AssertionError('implicit reply read')):
            self.assert_denied(fx.engine.reply(reply, fx.auth))
            fx.store.set_stop('C1', cp.binding.generation)
            result = fx.engine.run(fx.request, fx.auth)
            self.assertEqual(result.status, 'denied')
        self.assert_no_processing(fx)

    def test_public_generation_migration_preserves_original_role_caps(self):
        fx = self.fixture(narrative='PRIVATE original generation')
        self.assertEqual(fx.engine.run(fx.request, fx.auth).media_status, 'unavailable')
        first = fx.store.checkpoint('C1')
        fx.engine.stop('C1', first.binding.generation, fx.auth)
        replacement = make_request(request_id='REQ2', request_revision='v2', kind='goods_refusal',
            narrative=None, arguments={'inventory': {'item-1': 1}})
        fx.world.mutate('case.binding', dict(case_id='C1', object_id='O1', principal_id='U1', request_id='REQ2'))
        fx.world.mutate('case.generation', 'G2')
        fx.world.mutate('case.request_revision', 'v2')
        fx.world.mutate('customer.request_fingerprint', request_fingerprint(replacement))
        fx.world.mutate('delivery.status', 'delivered')
        fx.request = replacement
        with patch.object(fx.catalog, 'get', side_effect=AssertionError('structured migration intake')):
            result = fx.engine.run(replacement, fx.auth)
        current = fx.store.checkpoint('C1')
        self.assertEqual(current.binding.generation, 'G2')
        self.assertEqual(current.binding.supersedes_generation, first.binding.generation)
        self.assertEqual(current.budget.role_allowances, first.budget.role_allowances)
        self.assertEqual(current.budget.max_planner_calls, first.budget.max_planner_calls)
        self.assertIn(result.status, {'authorized', 'denied'})
        self.assertEqual(fx.store.processing_attempts(current.binding), ())
        self.assertEqual(fx.ids, [])

    def assert_no_processing(self, fx):
        cp = fx.store.checkpoint('C1')
        self.assertEqual(fx.ids, [])
        self.assertEqual(fx.store.processing_attempts(cp.binding), ())
        self.assertEqual(cp.budget.planner_calls, 0)
        self.assertEqual(cp.budget.role_allowances['extraction'].invocations, 0)
        self.assertEqual(cp.budget.role_allowances['planning'].invocations, 0)
        self.assertEqual(cp.budget.role_allowances['extraction'].max_invocations, 2)
        self.assertEqual(cp.budget.role_allowances['planning'].max_invocations, 1)
        self.assertEqual(fx.world.effect_count('reschedule'), 0)
        return cp

    def test_fresh_narrative_is_saved_exactly_without_model_or_semantic_claim(self):
        secret = 'PRIVATE original narrative.  Preserve whitespace.\n'
        fx = self.fixture(narrative=secret)
        registered, observed_contexts = [], []
        real_register = fx.catalog.register_saved_narrative
        execution = self.execution(fx)

        def register(binding, auth):
            # Real operation and fresh public saved-original readback, not a mock result.
            timing = fx.gateway.processing_parent_timing(store=fx.store, clock=fx.clock)
            observed_contexts.append(timing.execution)
            record = real_register(binding, auth)
            registered.append(record)
            return record

        with patch.object(fx.catalog, 'register_saved_narrative', register):
            result = fx.engine.run(fx.request, fx.auth, execution=execution)
        self.assertEqual(result.status, 'authorized')
        self.assertEqual(result.media_status, 'unavailable')
        self.assertEqual(len(registered), 1)
        record = registered[0]
        self.assertEqual(record.source, 'saved-request-narrative')
        self.assertEqual(fx.catalog.get(record.artifact_id, fx.auth), record)
        self.assertEqual(fx.catalog.read_original(record.artifact_id, fx.auth), secret.encode())
        self.assertEqual(observed_contexts, [execution])
        self.assertIs(fx.engine.gateway, fx.processing.parent_gateway)
        cp = self.assert_no_processing(fx)
        self.assertEqual(fx.store.original_request('C1', cp.binding.generation), fx.request)
        summary = fx.engine.processing_summary('C1', fx.auth, execution=self.execution(fx))
        self.assertIsInstance(summary, ProcessingSummaryV1)
        self.assertEqual(summary.attempts, ())
        self.assertEqual([(n.kind, n.reason) for n in summary.entry_local],
            [('unavailable', 'input_unavailable')])
        self.assertNotIn(secret, repr(asdict(summary)))
        self.assertNotIn(record.artifact_id, repr(asdict(summary)))

    def test_fresh_evidence_waits_for_source_auth_and_rechecks_acl_after_real_read(self):
        for revoke_after_read in (False, True):
            with self.subTest(revoke_after_read=revoke_after_read):
                fx = self.fixture(evidence=True)
                observed = []
                real_read = fx.catalog.read_original
                def read(identifier, auth=None, *, purpose='read', max_bytes=None):
                    timing = fx.gateway.processing_parent_timing(store=fx.store, clock=fx.clock)
                    data = real_read(identifier, auth, purpose=purpose, max_bytes=max_bytes)
                    observed.append((identifier, data, timing.execution))
                    if revoke_after_read:
                        fx.revoked = True
                    return data

                with patch.object(fx.catalog, 'read_original', read):
                    # Wrong proof can consume real admission pressure, but cannot read content.
                    wrong = fx.engine.run(fx.request, make_auth(proof_reference='wrong'),
                        execution=self.execution(fx))
                    self.assertEqual(wrong.model_dump(mode='json'),
                        CaseResult(status='denied', correlation_id='C1',
                            reason='denied').model_dump(mode='json'))
                    self.assertEqual(observed, [])
                    with self.assertRaises(JournalFailure):
                        fx.store.checkpoint('C1')
                    execution = self.execution(fx)
                    result = fx.engine.run(fx.request, fx.auth, execution=execution)
                self.assertTrue(observed)
                self.assertEqual(observed[0],
                    (fx.evidence.artifact_id,
                     b'PRIVATE original evidence; not semantic proof.\n', execution))
                if revoke_after_read:
                    self.assertEqual(result.model_dump(mode='json'),
                        CaseResult(status='denied', correlation_id='C1',
                            reason='denied').model_dump(mode='json'))
                else:
                    self.assertEqual(result.status, 'authorized')
                    self.assertEqual(result.media_status, 'unavailable')
                cp = self.assert_no_processing(fx)
                self.assertEqual(fx.store.original_request('C1', cp.binding.generation), fx.request)
                self.assertNotIn('PRIVATE original evidence', repr(result.model_dump()))

    def test_count_and_duplicates_deny_before_narrative_publication(self):
        for selected in ('duplicate', 'excess'):
            with self.subTest(selected=selected):
                fx = self.fixture(narrative='PRIVATE selected original', evidence=True)
                ids = ([fx.evidence.artifact_id] * 2 if selected == 'duplicate'
                       else ['artifact-' + format(n, '032x') for n in range(16)])
                fx.request = make_request(narrative=fx.request.narrative, evidence_ids=ids)
                fx.world.mutate('customer.request_fingerprint', request_fingerprint(fx.request))
                published = []
                real_register = fx.catalog.register_saved_narrative
                def register(binding, auth):
                    record = real_register(binding, auth)
                    published.append(record)
                    return record
                with patch.object(fx.catalog, 'register_saved_narrative', register):
                    result = fx.engine.run(fx.request, fx.auth, execution=self.execution(fx))
                self.assertEqual(result.model_dump(mode='json'),
                    CaseResult(status='denied', correlation_id='C1', reason='denied').model_dump(mode='json'))
                self.assertEqual(published, [])
                self.assert_no_processing(fx)

    def test_current_case_drift_after_actual_content_read_denies(self):
        fx = self.fixture(evidence=True)
        real_read = fx.catalog.read_original
        observed = []
        def read(identifier, auth=None, *, purpose='read', max_bytes=None):
            data = real_read(identifier, auth, purpose=purpose, max_bytes=max_bytes)
            observed.append(identifier)
            fx.world.mutate('case.authorization', 'unverified')
            return data
        with patch.object(fx.catalog, 'read_original', read):
            result = fx.engine.run(fx.request, fx.auth, execution=self.execution(fx))
        self.assertTrue(observed)
        self.assertEqual(result.model_dump(mode='json'),
            CaseResult(status='denied', correlation_id='C1', reason='denied').model_dump(mode='json'))
        self.assert_no_processing(fx)

    def test_final_real_read_expiry_retains_original_window_and_denies(self):
        fx = self.fixture(evidence=True)
        real_read = fx.catalog.read_original
        observed = []
        execution = self.execution(fx)
        def read(identifier, auth=None, *, purpose='read', max_bytes=None):
            data = real_read(identifier, auth, purpose=purpose, max_bytes=max_bytes)
            observed.append(fx.gateway.processing_parent_timing(store=fx.store, clock=fx.clock).execution)
            fx.clock.advance(31)
            return data
        with patch.object(fx.catalog, 'read_original', read):
            result = fx.engine.run(fx.request, fx.auth, execution=execution)
        self.assertEqual(observed, [execution])
        self.assertEqual(result.model_dump(mode='json'),
            CaseResult(status='denied', correlation_id='C1', reason='denied').model_dump(mode='json'))
        self.assert_no_processing(fx)
