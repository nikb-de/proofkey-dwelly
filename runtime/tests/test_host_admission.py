"""Real fixed-runtime admission tests; synthetic registration is not human review."""
from pathlib import Path
from dataclasses import replace
from datetime import timedelta
from hashlib import sha256
import json
import os
import tempfile
import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import sys

from proofkey.contracts import AuthContext
from proofkey.journal import CaseStore, JournalFailure
from proofkey.clock import SyntheticReplayClock
from proofkey.host import ProfileRegistry, RuntimeFactory, HostDispatcher, AuthResolver
from proofkey.host_contracts import HostLimitsV1
from proofkey.execution import ExecutionContext
from proofkey.registered_releases import ReleaseBlobV1, KnownFactoryV1, ReleaseRegistryV1, RegisteredReleaseV1
from proofkey.host_admission import (FIXED_IMPLEMENTATION_PATHS, HostExecutableBindingV1,
    SyntheticReviewGrantV1, ProvisionedReviewResolverV1, LocalAdmissionCompositionV1,
    AdmissionCompositionFailure, AdmissionClaimV1, RegisteredAdmissionOwner, _ClaimStore)
from proofkey.admission_routes import AdmissionRouteStoreV1
from proofkey.engine import WorkflowEngine
from proofkey.host_writer import RuntimeWriterLease
from test_release_route_foundation import registration_inputs, cj, rehash
from test_host_contracts import request

AUTH = AuthContext(caller_id='U1', proof_reference='synthetic-proof')


@contextmanager
def paced_clock(after_engine=None):
    """Advance real engine pacing without wall sleeps or substituting results."""
    state = {'tick': 100.0, 'utc_offset': 0.0, 'finished': False}
    def now(clock):
        return clock._EPOCH + timedelta(seconds=state['tick'] - 100 + state['utc_offset'])
    def wait(clock, seconds):
        state['tick'] += seconds + 1.0
    def profile(frame, event, result):
        if frame.f_code is WorkflowEngine.run.__code__ and event == 'return' and result is not None:
            state['finished'] = True
            if after_engine is not None:
                after_engine(state)
    previous = sys.getprofile()
    with patch.object(SyntheticReplayClock, 'monotonic', lambda clock: state['tick']), \
            patch.object(SyntheticReplayClock, 'now', now), patch.object(SyntheticReplayClock, 'wait', wait):
        sys.setprofile(profile)
        try:
            yield SyntheticReplayClock(), state
        finally:
            sys.setprofile(previous)


def context(clock, seconds=5):
    return ExecutionContext.capture(clock.now() + timedelta(seconds=seconds), clock)


def fixture(base, clock, *, goods=False, corrupt_pin=False, corrupt_resource=False):
    release = ProfileRegistry.builtin(base / 'resources').resolve(
        'host-goods-replay-v1' if goods else 'host-window-replay-v1')
    release.resource_root.mkdir(parents=True)
    control = base / 'control'
    control.mkdir()
    artifact, _, resource = registration_inputs(release.resource_root)
    source = Path(__file__).resolve().parents[1] / 'src/proofkey'
    implementations = tuple(ReleaseBlobV1(name, (source / name).read_bytes()) for name in FIXED_IMPLEMENTATION_PATHS)
    if corrupt_pin:
        implementations = (ReleaseBlobV1(implementations[0].name, b'# coherent declaration, wrong executable'), *implementations[1:])
    if corrupt_resource:
        resource = replace(resource, root_inode=resource.root_inode + 1)
    dependency = cj(dict(kind='route-closure-declaration-v1', mode='synthetic_declaration',
        completeness='unestablished', entries=[dict(name=item.name, sha256=item.sha256, role='code') for item in implementations]))
    factory = KnownFactoryV1('fixed-synthetic-v1', tuple((item.name, item.sha256) for item in implementations),
        sha256(dependency).hexdigest(), 'offline_synthetic')
    source_declaration = cj(dict(kind='route-source-declaration-v1', mode='synthetic', source_id='fixed-world-fixture',
        documents=[dict(source_id='fixed-world-fixture', text=release.fixture_path.read_text())]))
    artifact = replace(artifact, factory_id=factory.factory_id, implementations=implementations,
        dependency_json=dependency, source_json=source_declaration)
    registry = ReleaseRegistryV1(artifacts=(artifact,), factories=(factory,), resources=(resource,))
    binding = HostExecutableBindingV1(release.release_id, artifact.release_id, registry.resolve('L1').artifact_hash,
        factory.factory_id, factory.implementation_pins, factory.dependency_hash)
    grant = SyntheticReviewGrantV1('review-1', binding.artifact_hash, 'fixture-reviewer', 'admit_fixed_local_replay',
        'synthetic_rehearsal', clock.now(), clock.now() + timedelta(minutes=10))
    return release, LocalAdmissionCompositionV1(registry, binding, ProvisionedReviewResolverV1((grant,)), 'review-1', control)


class HostAdmissionTests(unittest.TestCase):
    def _assert_short_parent_observation(self, *, expire_before_write):
        cases = (
            ('utc', 216.0, 2.0, '2026-10-08T10:01:58+00:00', '2026-10-08T10:02:00+00:00', 218.0),
            ('monotonic', 218.0, -2.0, '2026-10-08T10:01:56+00:00', '2026-10-08T10:01:58+00:00', 220.0),
        )
        for bound, tick, offset, captured_at, deadline, monotonic_deadline in cases:
            with self.subTest(bound=bound), tempfile.TemporaryDirectory() as folder:
                def after_engine(state):
                    state.update(tick=tick, utc_offset=offset)
                with paced_clock(after_engine) as (clock, state):
                    release, composition = fixture(Path(folder).resolve(), clock)
                    runtime = RuntimeFactory().create_registered(
                        release, clock, composition=composition, execution=context(clock))
                    parent = context(clock, 120)
                    original = dict(deadline='2026-10-08T10:02:00+00:00',
                        captured_at='2026-10-08T10:00:00+00:00',
                        captured_monotonic=100.0, monotonic_deadline=220.0)
                    parent_fields = (parent.deadline, parent.captured_at,
                        parent.captured_monotonic, parent.monotonic_deadline)
                    phases = []
                    images = RegisteredAdmissionOwner._images
                    observe = AdmissionRouteStoreV1.observe_admitted
                    write = _ClaimStore.write

                    def capture_images(owner, execution):
                        if state['finished']:
                            phases.append(('images', execution))
                        return images(owner, execution)

                    def observe_route(store, *args, **kwargs):
                        if state['finished']:
                            phases.append(('route', kwargs['execution']))
                        return observe(store, *args, **kwargs)

                    def write_claim(store, value, execution, **kwargs):
                        if state['finished']:
                            phases.append(('claim', execution))
                            if expire_before_write:
                                state['tick'] += 2.0
                        return write(store, value, execution, **kwargs)

                    try:
                        with patch.object(RegisteredAdmissionOwner, '_images', capture_images), \
                                patch.object(AdmissionRouteStoreV1, 'observe_admitted', observe_route), \
                                patch.object(_ClaimStore, 'write', write_claim):
                            if expire_before_write:
                                with self.assertRaises(AdmissionCompositionFailure) as caught:
                                    runtime.run_registered(request(), AUTH, execution=parent)
                                self.assertEqual(caught.exception.code, 'timeout')
                            else:
                                result = runtime.run_registered(request(), AUTH, execution=parent)
                                self.assertEqual(result.status, 'authorized')
                                self.assertEqual(result.effects['reschedule'].status, 'verified')
                        self.assertTrue(state['finished'])
                        self.assertEqual([stage for stage, _ in phases], ['images', 'route', 'claim'])
                        phase = phases[0][1]
                        for _, observed in phases:
                            self.assertIs(observed, phase)
                        self.assertEqual((phase.deadline - phase.captured_at).total_seconds(), 2.0)
                        self.assertEqual(phase.captured_at.isoformat(), captured_at)
                        self.assertEqual(phase.deadline.isoformat(), deadline)
                        self.assertEqual(phase.captured_monotonic, tick)
                        self.assertEqual(phase.monotonic_deadline, monotonic_deadline)
                        self.assertEqual((parent.deadline, parent.captured_at,
                            parent.captured_monotonic, parent.monotonic_deadline), parent_fields)
                        claim = runtime.admission.claim_for_case('C1', execution=context(clock))
                        route = runtime.admission.route_for_case('C1', execution=context(clock))
                        self.assertEqual(claim.state,
                            'binding_sealed' if expire_before_write else 'admission_observed')
                        self.assertEqual(json.loads(claim.wire_bytes)['execution'], original)
                        self.assertEqual(route.state, 'admission_observed')
                        self.assertTrue(runtime.store.admission_account('C1').imported)
                        self.assertEqual(runtime.world.effect_count('reschedule'), 1)
                    finally:
                        runtime.close()

    def test_short_parent_final_phase_uses_smaller_clock_bound(self):
        # Granting five seconds, or renewing any stage, breaks the literal phase bounds.
        self._assert_short_parent_observation(expire_before_write=False)

    def test_short_parent_expiry_at_final_claim_write_retains_sealed_debt(self):
        # Ignoring the shared phase expiry would persist an observed claim instead.
        self._assert_short_parent_observation(expire_before_write=True)

    def test_two_release_registry_denies_host_composition_before_resources_or_effect(self):
        # Public multi-release inventory must not widen exactly-one-release host authority.
        with tempfile.TemporaryDirectory() as folder, paced_clock() as (clock, state):
            release, composition = fixture(Path(folder).resolve(), clock)
            first = composition.registry.resolve('L1').wire_bytes
            second = json.loads(first); second['release_id'] = 'L2'
            second_raw = rehash(second)
            RegisteredReleaseV1(second_raw)
            object.__setattr__(composition.registry, '_releases', (('L1', first), ('L2', second_raw)))
            with self.assertRaises(AdmissionCompositionFailure) as caught:
                RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
            self.assertEqual(caught.exception.code, 'invalid')
            for name in ('journal.sqlite', 'world.sqlite', '.proofkey-registration.json'):
                self.assertFalse((release.resource_root / name).exists())
            for name in ('routes.sqlite', 'host-claims.sqlite'):
                self.assertFalse((composition.control_parent / name).exists())
            self.assertFalse(state['finished'])

    def test_registry_replacement_denies_entry_before_claim_debt_or_effect(self):
        # A cached projection, missing registry type guard, or ignored invalid records breaks this.
        for mutation in ('valid_envelope', 'invalid_envelope', 'registry_type'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as folder, paced_clock() as (clock, state):
                release, composition = fixture(Path(folder).resolve(), clock)
                runtime = RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
                registry = composition.registry
                original = registry.resolve('L1').wire_bytes
                before = runtime.store.capture_retained_state(execution=context(clock), clock=clock).payload
                try:
                    if mutation == 'valid_envelope':
                        changed = json.loads(original); changed['resource']['root_inode'] += 1
                        replacement = rehash(changed)
                        self.assertNotEqual(RegisteredReleaseV1(replacement).artifact_hash,
                            RegisteredReleaseV1(original).artifact_hash)
                        object.__setattr__(registry, '_releases', (('L1', replacement),))
                    elif mutation == 'invalid_envelope':
                        object.__setattr__(registry, '_releases', (('L1', b'{}'),))
                    else:
                        class RegistryFacade:
                            def commitments(self): return (('L1', RegisteredReleaseV1(original).artifact_hash),)
                        object.__setattr__(composition, 'registry', RegistryFacade())
                    with self.assertRaises(AdmissionCompositionFailure) as caught:
                        runtime.run_registered(request(), AUTH, execution=context(clock, 120))
                    self.assertIn(caught.exception.code, ('scope', 'invalid'))
                    object.__setattr__(composition, 'registry', registry)
                    object.__setattr__(registry, '_releases', (('L1', original),))
                    self.assertIsNone(runtime.admission.claim_for_case('C1', execution=context(clock)))
                    self.assertIsNone(runtime.admission.route_for_case('C1', execution=context(clock)))
                    with self.assertRaises(JournalFailure):
                        runtime.store.admission_account('C1')
                    self.assertEqual(runtime.store._db.execute('SELECT count(*) FROM admission_accounts').fetchone()[0], 0)
                    self.assertFalse(runtime.store.has_case('C1'))
                    self.assertEqual(runtime.store.capture_retained_state(execution=context(clock), clock=clock).payload, before)
                    self.assertEqual(runtime.world.effect_count('reschedule'), 0)
                    self.assertFalse(state['finished'])
                finally:
                    object.__setattr__(composition, 'registry', registry)
                    object.__setattr__(registry, '_releases', (('L1', original),))
                    runtime.close()

    def test_final_observation_after_long_real_engine_preserves_parent_and_reopens(self):
        # Reusing the ingress cutoff after real engine completion breaks this.
        with tempfile.TemporaryDirectory() as folder, paced_clock() as (clock, state):
            release, composition = fixture(Path(folder).resolve(), clock)
            runtime = RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
            parent = context(clock, 120)
            original = dict(deadline=parent.deadline.isoformat(), captured_at=parent.captured_at.isoformat(),
                captured_monotonic=100.0, monotonic_deadline=220.0)
            try:
                result = runtime.run_registered(request(), AUTH, execution=parent)
                self.assertEqual(result.status, 'authorized')
                self.assertEqual(result.effects['reschedule'].status, 'verified')
                self.assertGreater(state['tick'] - 100, 5)
                self.assertLess(state['tick'] - 100, 120)
                claim = runtime.admission.claim_for_case('C1', execution=context(clock))
                route = runtime.admission.route_for_case('C1', execution=context(clock))
                self.assertEqual(claim.state, 'admission_observed')
                self.assertEqual(route.state, 'admission_observed')
                self.assertEqual(json.loads(claim.wire_bytes)['execution'], original)
                self.assertEqual(runtime.world.effect_count('reschedule'), 1)
            finally:
                runtime.close()
            reopened = RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
            try:
                self.assertEqual(reopened.admission.claim_for_case('C1', execution=context(clock)).state, 'admission_observed')
                self.assertEqual(reopened.world.effect_count('reschedule'), 1)
            finally:
                reopened.close()

    def test_final_observation_rejects_invalid_original_parent_and_retains_effect(self):
        # A fresh independent parent or a missing original-identity check admits these.
        for fault in ('utc_expired', 'monotonic_expired', 'utc_backwards', 'monotonic_backwards', 'changed_parent'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as folder:
                parent = None
                def corrupt(state):
                    if fault == 'utc_expired': state['utc_offset'] = 120
                    elif fault == 'monotonic_expired': state['tick'] = 220
                    elif fault == 'utc_backwards': state['utc_offset'] = -100
                    elif fault == 'monotonic_backwards': state['tick'] = 99
                    else: object.__setattr__(parent, 'deadline', parent.deadline + timedelta(seconds=1))
                with paced_clock(corrupt) as (clock, state):
                    release, composition = fixture(Path(folder).resolve(), clock)
                    runtime = RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
                    parent = context(clock, 120)
                    try:
                        with self.assertRaises(AdmissionCompositionFailure):
                            runtime.run_registered(request(), AUTH, execution=parent)
                        self.assertTrue(state['finished'])
                        state.update(tick=113.0, utc_offset=0.0)
                        self.assertEqual(runtime.world.effect_count('reschedule'), 1)
                        self.assertTrue(runtime.store.admission_account('C1').imported)
                        self.assertEqual(runtime.admission.claim_for_case('C1', execution=context(clock)).state, 'binding_sealed')
                    finally:
                        runtime.close()
                    with self.assertRaises(AdmissionCompositionFailure) as caught:
                        RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
                    self.assertEqual(caught.exception.code, 'pending_claim')

    def test_final_phase_cumulative_capture_join_and_write_budget_retains_debt(self):
        # Renewing the five-second budget per stage admits six seconds of final work.
        with tempfile.TemporaryDirectory() as folder, paced_clock() as (clock, state):
            release, composition = fixture(Path(folder).resolve(), clock)
            runtime = RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
            capture = CaseStore.capture_retained_state
            observe = AdmissionRouteStoreV1.observe_admitted
            write = _ClaimStore.write
            def delayed_capture(store, *args, **kwargs):
                result = capture(store, *args, **kwargs)
                if state['finished']: state['tick'] += 2
                return result
            def delayed_observe(store, *args, **kwargs):
                result = observe(store, *args, **kwargs)
                if state['finished']: state['tick'] += 2
                return result
            def delayed_write(store, *args, **kwargs):
                if state['finished']: state['tick'] += 2
                return write(store, *args, **kwargs)
            try:
                with patch.object(CaseStore, 'capture_retained_state', delayed_capture), \
                        patch.object(AdmissionRouteStoreV1, 'observe_admitted', delayed_observe), \
                        patch.object(_ClaimStore, 'write', delayed_write):
                    with self.assertRaises(AdmissionCompositionFailure):
                        runtime.run_registered(request(), AUTH, execution=context(clock, 120))
                self.assertTrue(state['finished'])
                self.assertEqual(runtime.world.effect_count('reschedule'), 1)
                self.assertTrue(runtime.store.admission_account('C1').imported)
                self.assertEqual(runtime.admission.claim_for_case('C1', execution=context(clock)).state, 'binding_sealed')
                self.assertEqual(runtime.admission.route_for_case('C1', execution=context(clock)).state, 'admission_observed')
            finally:
                runtime.close()

    def test_uncertain_claim_close_never_retries_a_reused_descriptor(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder).resolve()
            clock = SyntheticReplayClock()
            release, composition = fixture(base, clock)
            runtime = RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
            claim_fd = runtime.admission.claims.fd
            real_close = os.close
            outsider = None

            def close_then_raise(fd):
                real_close(fd)
                if fd == claim_fd:
                    raise OSError('close completed before local reporting fault')

            try:
                with patch('proofkey.host_admission.os.close', side_effect=close_then_raise):
                    with self.assertRaises(ValueError): runtime.close()
                self.assertIsNone(runtime.store._db)
                with self.assertRaises(ValueError): RuntimeWriterLease(release.resource_root)
                outsider = os.open(base / 'unrelated', os.O_CREAT | os.O_RDWR, 0o600)
                if outsider != claim_fd:
                    os.dup2(outsider, claim_fd)
                    real_close(outsider)
                    outsider = claim_fd
                with self.assertRaises(ValueError): runtime.close()
                try:
                    os.fstat(outsider)
                    remains_open = True
                except OSError:
                    remains_open = False
                self.assertTrue(remains_open, 'uncertain close retried a descriptor now owned elsewhere')
                with self.assertRaises(ValueError): RuntimeWriterLease(release.resource_root)
            finally:
                if outsider is not None:
                    try: real_close(outsider)
                    except OSError: pass
                runtime._writer_lease.close()

    def test_registered_cleanup_uses_original_handles_despite_public_alias_changes(self):
        for changed in ('store', 'admission'):
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as folder:
                base = Path(folder).resolve()
                clock = SyntheticReplayClock()
                release, composition = fixture(base, clock)
                runtime = RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
                original_store, original_owner = runtime.store, runtime.admission
                replacement = CaseStore(base / 'replacement.sqlite')
                try:
                    if changed == 'store': runtime.store = replacement
                    else: runtime.admission = None
                    runtime.close()
                    self.assertIsNone(original_store._db, 'creator-owned journal must close before writer release')
                    self.assertTrue(original_owner.closed, 'creator-owned admission handles must close before writer release')
                    self.assertIsNotNone(replacement._db, 'public alias is not the creator-owned journal')
                    lease = RuntimeWriterLease(release.resource_root)
                    lease.close()
                finally:
                    original_owner.close()
                    original_store.close()
                    replacement.close()
                    runtime._writer_lease.close()

    def test_construction_failure_closes_inner_owners_before_releasing_writer(self):
        with tempfile.TemporaryDirectory() as folder:
            clock = SyntheticReplayClock()
            release, composition = fixture(Path(folder).resolve(), clock)
            with patch.object(RegisteredAdmissionOwner, 'attach', side_effect=ValueError('local attachment fault')):
                with self.assertRaises(ValueError):
                    RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
            lease = RuntimeWriterLease(release.resource_root)
            lease.close()
            reopened = RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
            reopened.close()

    def test_construction_cleanup_failure_retains_owner_and_outer_lease(self):
        with tempfile.TemporaryDirectory() as folder:
            clock = SyntheticReplayClock()
            release, composition = fixture(Path(folder).resolve(), clock)
            original = AdmissionRouteStoreV1.close
            failure = None
            try:
                with patch.object(RegisteredAdmissionOwner, 'attach', side_effect=ValueError('local attachment fault')):
                    with patch.object(AdmissionRouteStoreV1, 'close', side_effect=ValueError('local cleanup fault')):
                        with self.assertRaises(ValueError) as caught:
                            RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
                failure = caught.exception
                self.assertEqual(failure.code, 'writer_storage')
                self.assertIsNotNone(failure._admission_owner)
                self.assertIsNone(failure._store)
                with self.assertRaises(ValueError): RuntimeWriterLease(release.resource_root)
                with self.assertRaises(ValueError): failure.close()
            finally:
                if failure is not None:
                    original(failure._admission_owner.routes)
                    failure._writer_lease.close()

    def test_corrupt_claim_store_denies_reopen_without_touching_runtime_state(self):
        with tempfile.TemporaryDirectory() as folder:
            clock = SyntheticReplayClock()
            release, composition = fixture(Path(folder).resolve(), clock)
            runtime = RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
            runtime.close()
            journal = release.resource_root / 'journal.sqlite'
            before = journal.read_bytes()
            claims = composition.control_parent / 'host-claims.sqlite'
            raw = claims.read_bytes()
            claims.write_bytes(b'corrupt fixture!!' + raw[16:])
            with self.assertRaises(ValueError):
                RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
            self.assertEqual(journal.read_bytes(), before)

    def test_dispatcher_selects_registered_run_and_denies_recovery(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder).resolve()
            clock = SyntheticReplayClock()
            release, composition = fixture(base, clock)
            resolver = AuthResolver({'fixture': AUTH})
            host = HostDispatcher(RuntimeFactory(), resolver, ProfileRegistry((release,)), clock,
                base / 'inventory', HostLimitsV1(), release_id=release.release_id, admission_composition=composition)
            try:
                receipt = host.submit(dict(tag='run', release_id=release.release_id,
                    request=request().model_dump(mode='json')), resolver.handle('fixture'), context(clock, 120))
                self.assertEqual(receipt.outcome, 'result')
                self.assertEqual(receipt.result.effects['reschedule'].status, 'verified')
                denied = host.submit(dict(tag='recover', release_id=release.release_id, case_id='C1'),
                    resolver.handle('fixture'), context(clock, 120))
                self.assertEqual(denied.outcome, 'denied')
                self.assertEqual(denied.failure, 'scope_denied')
            finally:
                self.assertTrue(host.close(clock.now() + timedelta(seconds=3)).owner_closed)

    def test_observed_claim_reopens_without_replaying_original(self):
        with tempfile.TemporaryDirectory() as folder:
            clock = SyntheticReplayClock()
            release, composition = fixture(Path(folder).resolve(), clock)
            runtime = RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
            runtime.run_registered(request(), AUTH, execution=context(clock, 120))
            before = runtime.store.capture_retained_state(execution=context(clock), clock=clock).payload
            runtime.close()
            reopened = RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
            try:
                self.assertEqual(reopened.admission.claim_for_case('C1', execution=context(clock)).state, 'admission_observed')
                with self.assertRaises(ValueError): reopened.run_registered(request(), AUTH, execution=context(clock, 120))
                reopened.engine.run(request(), AUTH, execution=context(clock, 120))
                self.assertEqual(reopened.store.capture_retained_state(execution=context(clock), clock=clock).payload, before)
                self.assertEqual(reopened.world.effect_count('reschedule'), 1)
            finally:
                reopened.close()

    def test_review_scope_expiry_and_profile_pin_fail_before_runtime_creation(self):
        with tempfile.TemporaryDirectory() as folder:
            clock = SyntheticReplayClock()
            release, composition = fixture(Path(folder).resolve(), clock)
            grant = composition.approvals.grants[0]
            with self.assertRaises(ValueError): replace(grant, scope='activation')
            with self.assertRaises(ValueError): replace(grant, provenance='actual_human')
            expired = replace(grant, issued_at=clock.now() - timedelta(days=1), expires_at=clock.now() - timedelta(seconds=1))
            with self.assertRaises(ValueError):
                RuntimeFactory().create_registered(release, clock,
                    composition=replace(composition, approvals=ProvisionedReviewResolverV1((expired,))), execution=context(clock))
            with self.assertRaises(ValueError):
                RuntimeFactory().create_registered(replace(release, profile_hash='0' * 64), clock,
                    composition=composition, execution=context(clock))
            self.assertFalse((release.resource_root / 'journal.sqlite').exists())

    def test_prepared_claim_retains_full_narrative_whitespace_and_evidence_order(self):
        with tempfile.TemporaryDirectory() as folder:
            clock = SyntheticReplayClock()
            release, composition = fixture(Path(folder).resolve(), clock)
            runtime = RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
            original = request().model_copy(update={'narrative': '  exact original\n', 'evidence_ids': ['E2', 'E1']})
            try:
                claim = runtime.admission.prepare_entry(original, AUTH, execution=context(clock, 120))
                payload = json.loads(claim.wire_bytes)
                self.assertEqual(payload['request']['narrative'], '  exact original\n')
                self.assertEqual(payload['request']['evidence_ids'], ['E2', 'E1'])
                self.assertNotIn('synthetic-proof', claim.wire_bytes.decode())
                self.assertIsNone(claim.binding)
            finally:
                runtime.close()

    def test_coherent_wrong_executable_and_resource_declarations_are_denied(self):
        for mutation in ('corrupt_pin', 'corrupt_resource'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as folder:
                clock = SyntheticReplayClock()
                release, composition = fixture(Path(folder).resolve(), clock, **{mutation: True})
                with self.assertRaises(ValueError):
                    RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
                self.assertFalse((release.resource_root / 'journal.sqlite').exists())
                self.assertFalse((release.resource_root / 'world.sqlite').exists())

    def test_mutating_provisioned_review_alias_cannot_authorize_new_entry(self):
        with tempfile.TemporaryDirectory() as folder:
            clock = SyntheticReplayClock()
            release, composition = fixture(Path(folder).resolve(), clock)
            runtime = RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
            try:
                forged = replace(composition.approvals.grants[0], actor_id='replacement-reviewer')
                object.__setattr__(composition.approvals, 'grants', (forged,))
                with self.assertRaises(ValueError):
                    runtime.run_registered(request(), AUTH, execution=context(clock, 120))
                self.assertFalse(runtime.store.has_case('C1'))
            finally:
                runtime.close()

    def test_direct_registered_entry_rejects_other_business_request_before_claim(self):
        with tempfile.TemporaryDirectory() as folder:
            clock = SyntheticReplayClock()
            release, composition = fixture(Path(folder).resolve(), clock)
            runtime = RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
            try:
                wrong = request().model_copy(update={'arguments': {'inventory': {'item-1': 2}}})
                with self.assertRaises(ValueError): runtime.run_registered(wrong, AUTH, execution=context(clock, 120))
                self.assertIsNone(runtime.admission.claim_for_case('C1', execution=context(clock)))
                self.assertFalse(runtime.store.has_case('C1'))
            finally:
                runtime.close()

    def test_prepared_execution_cannot_be_reanchored_by_mutation(self):
        with tempfile.TemporaryDirectory() as folder:
            clock = SyntheticReplayClock()
            release, composition = fixture(Path(folder).resolve(), clock)
            runtime = RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
            try:
                scope = context(clock, 120)
                runtime.admission.prepare_entry(request(), AUTH, execution=scope)
                object.__setattr__(scope, 'deadline', scope.deadline + timedelta(seconds=10))
                object.__setattr__(scope, 'monotonic_deadline', scope.monotonic_deadline + 10)
                with self.assertRaises(ValueError): runtime.admission.guard_execution(scope, runtime.engine.gateway)
                self.assertFalse(runtime.store.has_case('C1'))
            finally:
                runtime.close()

    def test_mutated_marker_denies_entry_before_new_debt(self):
        with tempfile.TemporaryDirectory() as folder:
            clock = SyntheticReplayClock()
            release, composition = fixture(Path(folder).resolve(), clock)
            runtime = RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
            try:
                (release.resource_root / '.proofkey-registration.json').write_bytes(b'changed marker')
                before = runtime.store.capture_retained_state(execution=context(clock), clock=clock).payload
                with self.assertRaises(ValueError):
                    runtime.run_registered(request(), AUTH, execution=context(clock, 120))
                self.assertEqual(runtime.store.capture_retained_state(execution=context(clock), clock=clock).payload, before)
            finally:
                runtime.close()

    def test_claim_rejects_rehashed_binding_with_wrong_business_fingerprint(self):
        with tempfile.TemporaryDirectory() as folder:
            clock = SyntheticReplayClock()
            release, composition = fixture(Path(folder).resolve(), clock)
            runtime = RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
            try:
                runtime.run_registered(request(), AUTH, execution=context(clock, 120))
                value = json.loads(runtime.admission.claim_for_case('C1', execution=context(clock)).wire_bytes)
                value['binding']['fingerprint'] = '0' * 64
                value['seal_hash'] = sha256(cj(dict(claim_hash=value['claim_hash'], binding=value['binding'],
                    route_reservation_hash=value['route_reservation_hash'], artifact_hash=value['artifact_hash']))).hexdigest()
                value['record_hash'] = sha256(cj({key: item for key, item in value.items() if key != 'record_hash'})).hexdigest()
                with self.assertRaises(ValueError):
                    AdmissionClaimV1(cj(value))
            finally:
                runtime.close()

    def test_route_close_failure_retains_outer_lease_and_closes_journal(self):
        with tempfile.TemporaryDirectory() as folder:
            clock = SyntheticReplayClock()
            release, composition = fixture(Path(folder).resolve(), clock)
            runtime = RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
            original = AdmissionRouteStoreV1.close
            try:
                with patch.object(AdmissionRouteStoreV1, 'close', side_effect=ValueError('local close fault')):
                    with self.assertRaises(ValueError): runtime.close()
                self.assertIsNone(runtime.store._db)
                with self.assertRaises(ValueError): RuntimeWriterLease(release.resource_root)
                with self.assertRaises(ValueError): runtime.close()
            finally:
                # Test fixture cleanup only. Production deliberately offers no
                # release after an uncertain B3 close outcome.
                original(runtime.admission.routes)
                runtime._writer_lease.close()

    def test_expired_context_and_replaced_engine_deny_before_preparation(self):
        with tempfile.TemporaryDirectory() as folder:
            clock = SyntheticReplayClock()
            release, composition = fixture(Path(folder).resolve(), clock)
            runtime = RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
            try:
                before = runtime.store.capture_retained_state(execution=context(clock), clock=clock).payload
                expired = ExecutionContext.capture(clock.now() - timedelta(seconds=1), clock)
                with self.assertRaises(ValueError): runtime.run_registered(request(), AUTH, execution=expired)
                engine = runtime.engine
                runtime.engine = object()
                with self.assertRaises(ValueError): runtime.run_registered(request(), AUTH, execution=context(clock))
                runtime.engine = engine
                self.assertIsNone(runtime.admission.claim_for_case('C1', execution=context(clock)))
                self.assertEqual(runtime.store.capture_retained_state(execution=context(clock), clock=clock).payload, before)
            finally:
                runtime.close()

    def test_goods_case_uses_same_seal_protocol(self):
        with tempfile.TemporaryDirectory() as folder:
            clock = SyntheticReplayClock()
            release, composition = fixture(Path(folder).resolve(), clock, goods=True)
            runtime = RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
            original = request().model_copy(update={'kind': 'goods_refusal', 'consent_mode': 'unknown',
                'arguments': {'inventory': {'item-1': 1}}})
            try:
                runtime.run_registered(original, AUTH, execution=context(clock, 120))
                self.assertEqual(runtime.admission.claim_for_case('C1', execution=context(clock)).state, 'admission_observed')
                self.assertEqual(runtime.world.effect_count('register_goods_refusal'), 1)
                self.assertEqual(runtime.world.effect_count('create_return'), 1)
            finally:
                runtime.close()

    def test_existing_case_and_orphan_admission_account_are_denied_before_new_debt(self):
        for orphan in (False, True):
            with self.subTest(orphan=orphan), tempfile.TemporaryDirectory() as folder:
                clock = SyntheticReplayClock()
                release, composition = fixture(Path(folder).resolve(), clock)
                runtime = RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
                try:
                    if orphan:
                        runtime.store.start_admission('historical-attempt', AUTH, request(), clock.now(), clock.now() + timedelta(seconds=120))
                    else:
                        runtime.run_registered(request(), AUTH, execution=context(clock, 120))
                    before = runtime.store.capture_retained_state(execution=context(clock), clock=clock).payload
                    with self.assertRaises(ValueError):
                        runtime.run_registered(request(), AUTH, execution=context(clock, 120))
                    self.assertEqual(runtime.store.capture_retained_state(execution=context(clock), clock=clock).payload, before)
                finally:
                    runtime.close()

    def test_prepared_restart_blocks_without_new_journal_debt(self):
        with tempfile.TemporaryDirectory() as folder:
            clock = SyntheticReplayClock()
            release, composition = fixture(Path(folder).resolve(), clock)
            runtime = RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
            runtime.admission.prepare_entry(request(), AUTH, execution=context(clock, 120))
            before = runtime.store.capture_retained_state(execution=context(clock), clock=clock).payload
            runtime.close()
            with self.assertRaises(AdmissionCompositionFailure) as error:
                RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
            self.assertEqual(error.exception.code, 'pending_claim')
            store = CaseStore(release.resource_root / 'journal.sqlite')
            try:
                self.assertEqual(store.capture_retained_state(execution=context(clock), clock=clock).payload, before)
            finally:
                store.close()

    def test_failed_seal_preserves_unbound_debt_and_reserved_route(self):
        with tempfile.TemporaryDirectory() as folder:
            clock = SyntheticReplayClock()
            release, composition = fixture(Path(folder).resolve(), clock)
            runtime = RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
            write = _ClaimStore.write
            def fail_seal(store, value, execution, *, initial=False):
                if value['state'] == 'binding_sealed':
                    raise AdmissionCompositionFailure('storage')
                return write(store, value, execution, initial=initial)
            try:
                with patch.object(_ClaimStore, 'write', fail_seal):
                    runtime.run_registered(request(), AUTH, execution=context(clock, 120))
                self.assertFalse(runtime.store.has_case('C1'))
                account = runtime.store.admission_account('C1')
                self.assertFalse(account.imported)
                self.assertGreater(account.pending_tool_calls, 0)
                self.assertEqual(runtime.world.effect_count('reschedule'), 0)
                self.assertEqual(runtime.admission.route_for_case('C1', execution=context(clock)).state, 'reserved')
                self.assertEqual(runtime.admission.claim_for_case('C1', execution=context(clock)).state, 'prepared')
            finally:
                runtime.close()
            with self.assertRaises(AdmissionCompositionFailure) as error:
                RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
            self.assertEqual(error.exception.code, 'pending_claim')

    def test_observation_failure_retains_admitted_debt_and_effect(self):
        with tempfile.TemporaryDirectory() as folder:
            clock = SyntheticReplayClock()
            release, composition = fixture(Path(folder).resolve(), clock)
            runtime = RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
            try:
                with patch.object(AdmissionRouteStoreV1, 'observe_admitted', side_effect=ValueError('local boundary fault')):
                    with self.assertRaises(ValueError):
                        runtime.run_registered(request(), AUTH, execution=context(clock, 120))
                self.assertTrue(runtime.store.admission_account('C1').imported)
                self.assertEqual(runtime.world.effect_count('reschedule'), 1)
                self.assertEqual(runtime.admission.claim_for_case('C1', execution=context(clock)).state, 'binding_sealed')
            finally:
                runtime.close()
            with self.assertRaises(AdmissionCompositionFailure) as error:
                RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
            self.assertEqual(error.exception.code, 'pending_claim')

    def test_changed_original_foreign_thread_and_expired_context_deny_before_reads(self):
        with tempfile.TemporaryDirectory() as folder:
            clock = SyntheticReplayClock()
            release, composition = fixture(Path(folder).resolve(), clock)
            runtime = RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
            try:
                scope = context(clock, 120)
                runtime.admission.prepare_entry(request(), AUTH, execution=scope)
                before = runtime.store.capture_retained_state(execution=context(clock), clock=clock).payload
                changed = request().model_copy(update={'narrative': ' changed original '})
                runtime.engine.run(changed, AUTH, execution=scope)
                with ThreadPoolExecutor(max_workers=1) as pool:
                    pool.submit(runtime.engine.run, request(), AUTH, execution=scope).result()
                self.assertEqual(runtime.store.capture_retained_state(execution=context(clock), clock=clock).payload, before)
            finally:
                runtime.close()

    def test_marker_reopen_denies_missing_control_or_runtime_database(self):
        for name, control in (('routes.sqlite', True), ('host-claims.sqlite', True), ('journal.sqlite', False), ('world.sqlite', False)):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as folder:
                clock = SyntheticReplayClock()
                release, composition = fixture(Path(folder).resolve(), clock)
                runtime = RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
                runtime.close()
                path = (composition.control_parent if control else release.resource_root) / name
                path.rename(path.with_suffix('.retained'))
                with self.assertRaises(ValueError):
                    RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
                self.assertFalse(path.exists())

    def test_first_adoption_rejects_preexisting_controls(self):
        for name in ('routes.sqlite', 'host-claims.sqlite', 'routes.sqlite-journal', 'host-claims.sqlite-wal'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as folder:
                clock = SyntheticReplayClock()
                release, composition = fixture(Path(folder).resolve(), clock)
                path = composition.control_parent / name
                path.write_bytes(b'unknown')
                with self.assertRaises(ValueError):
                    RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
                self.assertEqual(path.read_bytes(), b'unknown')
                self.assertFalse((release.resource_root / 'world.sqlite').exists())

    def test_fresh_case_seals_full_actual_route_before_atomic_debt_import(self):
        with tempfile.TemporaryDirectory() as folder:
            clock = SyntheticReplayClock()
            release, composition = fixture(Path(folder).resolve(), clock)
            runtime = RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
            failures = []
            observed = []
            base_admit = CaseStore.admit_from_attempt
            def checked_admit(store, attempt_id, binding, original, checkpoint):
                claim = runtime.admission.claim_for_case('C1', execution=context(clock))
                route = runtime.admission.route_for_case('C1', execution=context(clock))
                if claim.state != 'binding_sealed': failures.append('unsealed claim')
                if route is None or route.state != 'reserved': failures.append('unreserved route')
                if route is not None and (route.binding != binding or route.request != original): failures.append('wrong actual route')
                if store.admission_account('C1').imported: failures.append('premature import')
                if store.has_case('C1'): failures.append('premature case')
                observed.append(attempt_id)
                return base_admit(store, attempt_id, binding, original, checkpoint)
            try:
                with patch.object(CaseStore, 'admit_from_attempt', checked_admit):
                    runtime.run_registered(request(), AUTH, execution=context(clock, 120))
                self.assertEqual(failures, [])
                self.assertEqual(len(observed), 1)
                self.assertEqual(runtime.world.effect_count('reschedule'), 1)
                self.assertEqual(runtime.admission.claim_for_case('C1', execution=context(clock)).state, 'admission_observed')
                self.assertTrue(runtime.store.admission_account('C1').imported)
            finally:
                runtime.close()

    def test_registered_construction_installs_durable_marker_and_denies_legacy_reopen(self):
        with tempfile.TemporaryDirectory() as folder:
            clock = SyntheticReplayClock()
            release, composition = fixture(Path(folder).resolve(), clock)
            runtime = RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
            try:
                self.assertTrue((release.resource_root / '.proofkey-registration.json').is_file())
            finally:
                runtime.close()
            with self.assertRaises(ValueError):
                RuntimeFactory().create(release, clock)

    def test_direct_engine_entry_cannot_create_case_or_admission_debt(self):
        with tempfile.TemporaryDirectory() as folder:
            clock = SyntheticReplayClock()
            release, composition = fixture(Path(folder).resolve(), clock)
            runtime = RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
            try:
                before = runtime.store.capture_retained_state(execution=context(clock), clock=clock)
                runtime.engine.run(request(), AUTH, execution=context(clock, 120))
                after = runtime.store.capture_retained_state(execution=context(clock), clock=clock)
                self.assertEqual(after.payload, before.payload)
                self.assertEqual(runtime.world.effect_count('reschedule'), 0)
            finally:
                runtime.close()

    def test_wrong_artifact_is_denied_before_runtime_databases(self):
        # Omitting the independently provisioned artifact join must fail this.
        with tempfile.TemporaryDirectory() as folder:
            clock = SyntheticReplayClock()
            release, composition = fixture(Path(folder).resolve(), clock)
            composition = replace(composition, binding=replace(composition.binding, artifact_hash='0' * 64))
            runtime = None
            try:
                with self.assertRaises(ValueError):
                    runtime = RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
                self.assertFalse((release.resource_root / 'journal.sqlite').exists())
                self.assertFalse((release.resource_root / 'world.sqlite').exists())
            finally:
                if runtime is not None:
                    runtime.close()

    def test_unknown_review_is_denied_before_runtime_databases(self):
        with tempfile.TemporaryDirectory() as folder:
            clock = SyntheticReplayClock()
            release, composition = fixture(Path(folder).resolve(), clock)
            composition = replace(composition, review_id='not-provisioned')
            runtime = None
            try:
                with self.assertRaises(ValueError):
                    runtime = RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))
                self.assertFalse((release.resource_root / 'journal.sqlite').exists())
            finally:
                if runtime is not None:
                    runtime.close()

    def test_legacy_factory_denies_any_registration_marker_before_database_creation(self):
        # Removing the legacy marker guard must allow this real factory and fail.
        with tempfile.TemporaryDirectory() as folder:
            release = ProfileRegistry.builtin(Path(folder).resolve() / 'resources').resolve('host-window-replay-v1')
            release.resource_root.mkdir(parents=True)
            (release.resource_root / '.proofkey-registration.json').write_bytes(b'partial registration')
            runtime = None
            try:
                with self.assertRaises(ValueError):
                    runtime = RuntimeFactory().create(release, SyntheticReplayClock())
                self.assertFalse((release.resource_root / 'world.sqlite').exists())
                self.assertFalse((release.resource_root / 'journal.sqlite').exists())
            finally:
                if runtime is not None:
                    runtime.close()
