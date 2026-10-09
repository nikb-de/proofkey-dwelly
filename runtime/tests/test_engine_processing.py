from dataclasses import asdict
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
import threading
from unittest.mock import patch
from proofkey.journal import JournalFailure
from proofkey.budget import BudgetExceeded

from proofkey.adapters.world import SimulatedWorld
from proofkey.contracts import (AssertionsOutput, CaseResult, EvidenceAssertion,
    InvocationRequest, ProcessingReceipt, ProcessorIdentity, UnknownLocator)
from proofkey.engine import WorkflowEngine
from proofkey.evidence.catalog import EvidenceAccessDenied, EvidenceCatalog
from proofkey.evidence.processing_contracts import (
    ProcessingCatalogBindings, SavedOriginalScope, canonical)
from proofkey.execution import ExecutionContext
from proofkey.gateway import ActionGateway
from proofkey.identity import fingerprint, request_fingerprint
from proofkey.journal import CaseStore
from proofkey.processing import RoleAdmissionLimits
from proofkey.processing_orchestration import ProcessingOrchestrator, ProcessingRecipe
from proofkey.processing_summary import ProcessingSummaryV1
from proofkey.providers.invocations import output_digest
from support import (NOW, DEADLINE, FakeClock, load_test_profile, make_auth,
                     make_fixture_campaign, make_request)

class Clock(FakeClock):
    def __init__(self):
        super().__init__()
        self.tick = 100.0
    def monotonic(self):
        return self.tick
    def advance(self, seconds):
        super().advance(seconds)
        self.tick += seconds

def compose(fx, allowances):
    # Explicit trusted host composition, never an engine callback/grant.
    def original(binding):
        found = fx.store.find_request(binding.case_id, binding.request_id,
            binding.request_revision, binding.consent_revision, binding.fingerprint)
        if found != binding:
            raise ValueError('Not the exact saved binding')
        return fx.store.original_request(binding.case_id, binding.generation)
    def scope(binding, saved, auth, purpose):
        if (saved != fx.request or auth != fx.auth or 'saved-scope' in fx.revoked
                or fx.clock.now() >= DEADLINE):
            return None
        raw = dict(allowed_actors=['U1'], case_id=binding.case_id, object_id=binding.object_id,
            binding_hash=fingerprint(binding.model_dump(mode='json')),
            original_request_hash=fingerprint(saved.model_dump(mode='json')),
            scope_id='saved-scope', policy_id='local-policy', authorization_reference='synthetic-proof',
            provenance='synthetic_host_registration', expires_at=DEADLINE.isoformat())
        return SavedOriginalScope(canonical(binding.model_dump(mode='json')),
            raw['original_request_hash'], 'saved-scope', canonical(raw), 'local-policy',
            'synthetic_host_registration', 'synthetic-proof', DEADLINE)
    def access(auth, record, saved_scope, purpose):
        return (auth == fx.auth and record.case_id == 'C1'
            and saved_scope['allowed_actors'] == ('U1',)
            and saved_scope.get('scope_id') not in fx.revoked)
    fx.catalog = EvidenceCatalog(fx.root / 'catalog', fx.clock,
        allowed_input_roots=[fx.root], access_resolver=access,
        processing_bindings=ProcessingCatalogBindings(original,
            lambda b: fx.store.checkpoint(b.case_id), fx.store.invocation, scope,
            profile_lookup=lambda b, o: fx.profile))
    fx.bundle = fx.world.bundle()
    fx.gateway = ActionGateway(fx.profile, fx.bundle, fx.store, fx.clock, auth=fx.auth,
                                processing_allowances=allowances)
    recipe = ProcessingRecipe(allowances=allowances, planning_registrations=())
    def no_id():
        raise AssertionError('Structured/unavailable engine entered processing')
    fx.processing = ProcessingOrchestrator(fx.store, fx.clock, fx.catalog,
        parent_gateway=fx.gateway, recipe=recipe, invocation_id_factory=no_id)
    fx.engine = WorkflowEngine(fx.profile, fx.bundle, fx.store, fx.clock,
        evidence=fx.catalog, gateway=fx.gateway, processing=fx.processing)

class EngineFixture(unittest.TestCase):
    def fixture(self, request):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        root = Path(folder.name).resolve()
        clock, profile = Clock(), load_test_profile('flat-v1.2')
        world = SimulatedWorld(root / 'world.sqlite',
            Path(__file__).resolve().parents[1] / 'fixtures/development/world.json',
            profile=profile, clock=clock)
        world.mutate('customer.request_fingerprint', request_fingerprint(request))
        world.mutate('customer.consent_mode', request.consent_mode)
        fx = SimpleNamespace(root=root, clock=clock, profile=profile, world=world,
            store=CaseStore(root / 'journal.sqlite'), request=request,
            auth=make_auth(), revoked=set())
        self.addCleanup(lambda: fx.store.close())
        compose(fx, (RoleAdmissionLimits('extraction', 5, (('tokens', 10.0),), 5.0),
                     RoleAdmissionLimits('planning', 1, (('tokens', 2.0),), 1.0)))
        return fx

    def execution(self, fx):
        return ExecutionContext.capture(fx.clock.now() + timedelta(seconds=30), fx.clock)


class EngineProcessingInjectionTests(EngineFixture):
    def test_constructor_rejects_foreign_components_before_source_or_admission(self):
        fx = self.fixture(make_request())
        foreign = self.fixture(make_request())
        alias = SimpleNamespace(store=fx.store, clock=fx.clock, catalog=fx.catalog,
            parent_gateway=fx.gateway)
        cases = [('store', dict(store=foreign.store)), ('clock', dict(clock=foreign.clock)),
            ('catalog', dict(evidence=foreign.catalog)), ('bundle', dict(bundle=foreign.bundle)),
            ('profile', dict(profile=fx.profile.model_copy(update={'version': 'other'}))),
            ('gateway', dict(gateway=foreign.gateway)), ('alias', dict(processing=alias)),
            ('object', dict(processing=object()))]
        for label, changes in cases:
            args = dict(profile=fx.profile, bundle=fx.bundle, store=fx.store, clock=fx.clock,
                evidence=fx.catalog, gateway=fx.gateway, processing=fx.processing)
            with self.subTest(label=label), self.assertRaises((ValueError, TypeError)):
                WorkflowEngine(**{**args, **changes})
        self.assertEqual(fx.world.calls, ())
        self.assertEqual(foreign.world.calls, ())
        with self.assertRaises(JournalFailure):
            fx.store.checkpoint('C1')

    def test_joint_profile_or_bundle_replacement_does_not_reconfigure_fixed_parent(self):
        for field in ('profile', 'bundle'):
            fx = self.fixture(make_request())
            other = self.fixture(make_request())
            replacement = other.bundle if field == 'bundle' else fx.profile.model_copy(update={'version': 'other'})
            entered = []
            actual_checkpoint = fx.store.checkpoint
            def checkpoint(case_id):
                entered.append(case_id)
                return actual_checkpoint(case_id)
            with self.subTest(field=field), patch.object(fx.engine, field, replacement), \
                    patch.object(fx.gateway, field, replacement), \
                    patch.object(fx.store, 'checkpoint', checkpoint):
                result = fx.engine.run(fx.request, fx.auth, execution=self.execution(fx))
                self.assertEqual(result.status, 'denied')
                self.assertEqual(entered, [])
                self.assertEqual(fx.world.calls, ())
                self.assertEqual(other.world.calls, ())

    def test_structured_source_slot_window_status_and_consent_gate_actual_effect(self):
        scenarios = [('capacity', {}, 'scheduling.capacity', []),
            ('status', {}, 'delivery.status', 'completed'),
            ('consent', {}, 'customer.consent', 'revoked'),
            ('window', {'arguments': {'window_start': (DEADLINE + timedelta(hours=1)).isoformat(),
                'window_end': (DEADLINE + timedelta(hours=2)).isoformat()}}, None, None)]
        for label, changes, fact, value in scenarios:
            fx = self.fixture(make_request(**changes))
            if fact is not None:
                fx.world.mutate(fact, value)
            with self.subTest(label=label):
                result = fx.engine.run(fx.request, fx.auth, execution=self.execution(fx))
                self.assertNotEqual(result.effects.get('reschedule', SimpleNamespace(status=None)).status, 'verified')
                self.assertEqual(fx.world.effect_count('reschedule'), 0)
                try:
                    cp = fx.store.checkpoint('C1')
                except JournalFailure:
                    continue
                self.assertEqual(cp.budget.planner_calls, 0)
                self.assertEqual(fx.store.processing_attempts(cp.binding), ())

    def test_text_evidence_and_recovery_do_not_call_prepared_consumer(self):
        for changes in ({'narrative': 'synthetic text'}, {'evidence_ids': ['unavailable-artifact']}):
            fx = self.fixture(make_request(**changes))
            with patch.object(fx.processing, 'plan_prepared', side_effect=AssertionError('prepared consumer entered')):
                result = fx.engine.run(fx.request, fx.auth, execution=self.execution(fx))
                self.assertEqual(result.status, 'authorized')
                cp = fx.store.checkpoint('C1')
                self.assertEqual(cp.processing_status, 'unavailable')
                recovered = fx.engine.recover('C1', fx.auth, execution=self.execution(fx))
                self.assertEqual(recovered.status, 'authorized')
            self.assertEqual(fx.store.processing_attempts(cp.binding), ())
            self.assertEqual(fx.world.effect_count('reschedule'), 0)
            self.assertEqual(fx.store.checkpoint('C1').budget.planner_calls, 0)

    def test_missing_host_allowances_deny_real_reservation_without_repair(self):
        fx = self.fixture(make_request(narrative='synthetic text'))
        recipe = fx.processing.recipe
        fx.gateway = ActionGateway(fx.profile, fx.bundle, fx.store, fx.clock, auth=fx.auth,
            processing_allowances=())
        fx.processing = ProcessingOrchestrator(fx.store, fx.clock, fx.catalog,
            parent_gateway=fx.gateway, recipe=recipe,
            invocation_id_factory=lambda: self.fail('ID created'))
        fx.engine = WorkflowEngine(fx.profile, fx.bundle, fx.store, fx.clock,
            evidence=fx.catalog, processing=fx.processing)
        fx.engine.run(fx.request, fx.auth, execution=self.execution(fx))
        cp = fx.store.checkpoint('C1')
        self.assertEqual(cp.budget.role_allowances, {})
        grant = make_fixture_campaign()
        fx.store.register_campaign(grant)
        identity = ProcessorIdentity(case_id='C1', generation=cp.binding.generation, role='extraction',
            campaign_id=grant.campaign_id, permit_hash=grant.permit_hash, input_hashes=grant.input_hashes,
            provider=grant.provider, model=grant.model, endpoint=grant.endpoint, prompt_hash='2' * 64,
            version='v1', profile_version=cp.profile_version, process_version=cp.process_version, deadline=cp.deadline)
        before = fx.store.checkpoint('C1').budget
        with self.assertRaises(BudgetExceeded):
            fx.store.reserve_invocation(InvocationRequest(identity=identity, invocation_id='blocked',
                requested_usage={'tokens': 1.0}, worst_case_cost=1.0), fx.clock.now())
        self.assertEqual(fx.store.checkpoint('C1').budget, before)
        self.assertEqual(fx.store.processing_attempts(cp.binding), ())
        self.assertEqual(fx.store.campaign_usage(grant.permit_hash)['invocations'], 0)

    def test_semantically_equal_profile_and_legacy_defaults_keep_existing_meaning(self):
        fx = self.fixture(make_request())
        copy = WorkflowEngine(fx.profile.model_copy(), fx.bundle, fx.store, fx.clock,
            evidence=fx.catalog, processing=fx.processing)
        self.assertIs(copy.gateway, fx.gateway)
        legacy = WorkflowEngine(fx.profile, fx.bundle, fx.store, fx.clock)
        self.assertIsNone(legacy.processing)
        result = legacy.run(fx.request, fx.auth, execution=self.execution(fx))
        self.assertEqual(result.effects['reschedule'].status, 'verified')
        self.assertEqual(fx.store.checkpoint('C1').budget.max_planner_calls, 0)

    def test_larger_recipe_preserves_caps_through_recovery_stop_and_public_migration(self):
        fx = self.fixture(make_request(narrative='synthetic unavailable input'))
        fx.engine.run(fx.request, fx.auth, execution=self.execution(fx))
        original = fx.store.checkpoint('C1')
        compose(fx, (RoleAdmissionLimits('extraction', 20, (('tokens', 40.0),), 20.0),
                     RoleAdmissionLimits('planning', 4, (('tokens', 8.0),), 4.0)))
        fx.engine.recover('C1', fx.auth, execution=self.execution(fx))
        self.assertEqual(fx.store.checkpoint('C1').budget.role_allowances, original.budget.role_allowances)
        fx.engine.stop('C1', original.binding.generation, fx.auth, execution=self.execution(fx))
        self.assertTrue(fx.store.checkpoint('C1').stop.requested)
        next_request = make_request(request_id='REQ2', request_revision='v2', kind='goods_refusal',
            narrative=None, arguments={'inventory': {'item-1': 1}})
        fx.world.mutate('case.binding', dict(case_id='C1', object_id='O1', principal_id='U1', request_id='REQ2'))
        fx.world.mutate('case.generation', 'G2')
        fx.world.mutate('case.request_revision', 'v2')
        fx.world.mutate('customer.request_fingerprint', request_fingerprint(next_request))
        fx.world.mutate('delivery.status', 'delivered')
        fx.request = next_request
        result = fx.engine.run(next_request, fx.auth, execution=self.execution(fx))
        self.assertEqual(result.status, 'authorized')
        current = fx.store.checkpoint('C1')
        self.assertEqual(current.binding.generation, 'G2')
        self.assertEqual(current.binding.supersedes_generation, original.binding.generation)
        self.assertEqual(current.budget.role_allowances, original.budget.role_allowances)
        self.assertEqual(current.budget.max_planner_calls, original.budget.max_planner_calls)
        self.assertEqual(fx.store.processing_attempts(current.binding), ())
        summary = fx.engine.processing_summary('C1', fx.auth, execution=self.execution(fx))
        # The real continuation spent the original global tool allowance.
        self.assertEqual(current.budget.tool_calls, current.budget.max_tool_calls)
        self.assertEqual(summary.model_dump(mode='json'),
            CaseResult(status='denied', correlation_id='C1', reason='denied').model_dump(mode='json'))

    def test_changed_fixed_associations_deny_before_any_store_or_source_entry(self):
        for owner, field in (('engine', 'clock'), ('engine', 'store'), ('engine', 'evidence'),
                ('engine', 'bundle'), ('engine', 'profile'), ('gateway', 'clock'),
                ('gateway', 'store'), ('gateway', 'bundle'), ('gateway', 'profile'),
                ('catalog', 'clock')):
            fx = self.fixture(make_request())
            target = getattr(fx, owner)
            value = fx.profile.model_copy(update={'version': 'other'}) if field == 'profile' else object()
            with self.subTest(owner=owner, field=field), patch.object(target, field, value), \
                    patch.object(fx.store, 'checkpoint', side_effect=AssertionError('store entered')):
                denied = fx.engine.run(fx.request, fx.auth, execution=self.execution(fx))
                self.assertEqual(denied.model_dump(mode='json'),
                    CaseResult(status='denied', correlation_id='C1', reason='denied').model_dump(mode='json'))
            self.assertEqual(fx.world.calls, ())

    def test_readonly_processing_wrong_thread_and_recursive_entry(self):
        fx = self.fixture(make_request())
        with self.assertRaises(AttributeError):
            fx.engine.processing = None
        replies = []
        thread = threading.Thread(target=lambda: replies.append(fx.engine.run(fx.request, fx.auth,
            execution=self.execution(fx))))
        thread.start()
        thread.join()
        self.assertEqual(replies[0].status, 'denied')
        with fx.engine._execution_scope(self.execution(fx)):
            recursive = fx.engine.run(fx.request, fx.auth, execution=self.execution(fx))
        self.assertEqual(recursive.status, 'denied')
        self.assertEqual(fx.world.calls, ())

    def test_structured_recipe_positive_and_later_recipe_never_upgrades_caps(self):
        fx = self.fixture(make_request())  # no text/evidence
        implicit_same_parent = WorkflowEngine(fx.profile, fx.bundle, fx.store, fx.clock,
            evidence=fx.catalog, processing=fx.processing)
        self.assertIs(implicit_same_parent.gateway, fx.gateway)
        result = fx.engine.run(fx.request, fx.auth, execution=self.execution(fx))
        self.assertEqual(result.status, 'authorized')
        self.assertEqual(result.effects['reschedule'].status, 'verified')
        self.assertIs(fx.engine.processing, fx.processing)
        cp = fx.store.checkpoint('C1')
        self.assertEqual(cp.budget.max_planner_calls, 0)
        self.assertEqual(cp.budget.planner_calls, 0)
        self.assertEqual(fx.store.processing_attempts(cp.binding), ())
        summary = fx.engine.processing_summary('C1', fx.auth, execution=self.execution(fx))
        self.assertIsInstance(summary, ProcessingSummaryV1)
        self.assertEqual((summary.attempts, summary.entry_local), ((), ()))
        original_caps = fx.store.checkpoint('C1').budget.role_allowances
        compose(fx, (RoleAdmissionLimits('extraction', 20, (('tokens', 40.0),), 20.0),
                     RoleAdmissionLimits('planning', 4, (('tokens', 8.0),), 4.0)))
        replay = fx.engine.run(fx.request, fx.auth, execution=self.execution(fx))
        self.assertEqual(replay.status, 'authorized')
        current = fx.store.checkpoint('C1')
        self.assertEqual(current.budget.role_allowances, original_caps)
        self.assertEqual(current.budget.max_planner_calls, 0)
        self.assertEqual(fx.store.processing_attempts(current.binding), ())
        self.assertEqual(fx.world.effect_count('reschedule'), 1)
        replay_summary = fx.engine.processing_summary('C1', fx.auth, execution=self.execution(fx))
        self.assertEqual([(n.kind, n.reason) for n in replay_summary.entry_local],
                         [('recorded_replay', None)])
