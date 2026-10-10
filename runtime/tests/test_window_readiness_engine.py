"""Real J05 readiness, journal fences and bounded-domain workflow evidence."""
from dataclasses import replace
from contextlib import contextmanager
from datetime import timedelta
import json
import os
import tempfile
import threading
import unittest
from unittest.mock import patch

from proofkey.contracts import ActionProposal, AuthorityObservation, PhaseCheckpoint
from proofkey.journal import JournalFailure
from proofkey.policy import GateDenied
from proofkey.process import ProcessController
from support import build_test_runtime, make_binding, make_checkpoint, make_request, make_intent, CommitFault, NOW
from test_workflows import ForwardPort


class WindowReadinessEngineTests(unittest.TestCase):
    def fixture(self, **options):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        fx = build_test_runtime(temporary.name, **options)
        self.addCleanup(fx.store.close)
        return fx

    def ready_fixture(self, *, checkpoint_changes=None, **options):
        fx = self.fixture(profile_name='flat-window-readiness-v1', **options)
        binding = make_binding(fx.request)
        values = dict(binding=binding, phase='window_readiness',
            next_gate='read_authority', profile_version='v1.3', process_version='v2-window-readiness',
            ownership_state='accepted', ownership_state_revision='v1', ownership_epoch=0)
        values.update(checkpoint_changes or {})
        checkpoint = make_checkpoint(**values)
        fx.store.admit(binding, fx.request, checkpoint)
        return fx

    def read_ready(self, fx):
        with fx.engine.gateway.execution_scope(), fx.engine.gateway._auth_scope(fx.auth):
            return fx.engine.gateway.read_window_readiness('C1')

    def test_exact_four_reads_and_original_state(self):
        fx = self.ready_fixture()
        before = fx.store.checkpoint('C1')
        self.assertTrue(callable(getattr(fx.engine.gateway, 'read_window_readiness', None)),
                        'readiness must have its own authenticated source-read entry')
        observations = self.read_ready(fx)
        after = fx.store.checkpoint('C1')
        self.assertEqual([(c.operation, c.purpose) for c in fx.world.calls], [
            ('read_case', 'window_readiness_identity'),
            ('read_principal', 'window_readiness_identity'),
            ('read_owner', 'window_readiness_identity'),
            ('list_permitted_slots', 'window_readiness')])
        self.assertEqual(len(observations), 10)
        self.assertEqual({o.authority + '.' + o.fact for o in observations}, {
            'case.authorization', 'case.binding', 'case.generation', 'case.request_revision',
            'customer.consent_revision', 'ownership.epoch', 'ownership.owner', 'ownership.state',
            'ownership.state_revision', 'scheduling.slot'})
        self.assertEqual(after.budget.tool_calls - before.budget.tool_calls, 4)
        self.assertEqual((after.binding, after.deadline), (before.binding, before.deadline))
        self.assertEqual(fx.world.effect_count('reschedule'), 0)

    def test_owner_validation_precedes_settlement(self):
        for owner in ('', True, 1, None, 'OTHER', 'U1'):
            with self.subTest(owner=owner):
                fx = self.ready_fixture()
                fx.world.mutate('ownership.owner', owner)
                settlements = []
                real = fx.engine.gateway._settle
                def settle(lease, completed, **kwargs):
                    settlements.append(completed)
                    return real(lease, completed, **kwargs)
                fx.engine.gateway._settle = settle
                if owner == 'U1':
                    self.assertEqual(len(self.read_ready(fx)), 10)
                    self.assertEqual(settlements, [True] * 4)
                else:
                    with self.assertRaises(GateDenied):
                        self.read_ready(fx)
                    self.assertEqual(settlements, [True, True, False])
                    self.assertEqual(len(fx.world.calls), 3)
                    self.assertEqual(fx.store.checkpoint('C1').budget.tool_calls, 3)
                self.assertEqual(fx.world.effect_count('reschedule'), 0)

    def test_boolean_epoch_cannot_equal_integer_epoch(self):
        fx = self.ready_fixture(checkpoint_changes={'ownership_epoch': 1})
        fx.world.mutate('ownership.epoch', True)
        with self.assertRaises(GateDenied):
            self.read_ready(fx)
        self.assertEqual(len(fx.world.calls), 3)
        self.assertEqual(fx.store.checkpoint('C1').budget.tool_calls, 3)

    def test_source_identity_and_owner_changes_deny_at_the_source(self):
        cases = [('case.authorization', 'denied', 1), ('case.binding', {}, 1),
            ('case.generation', 'G2', 1), ('case.request_revision', 'v2', 1),
            ('customer.consent_revision', 'v2', 2), ('ownership.state', 'pending', 3),
            ('ownership.state_revision', 'v2', 3), ('ownership.epoch', 1, 3),
            ('ownership.epoch', True, 3)]
        for field, value, count in cases:
            with self.subTest(field=field, value=value):
                fx = self.ready_fixture()
                fx.world.mutate(field, value)
                with self.assertRaises(GateDenied):
                    self.read_ready(fx)
                self.assertEqual(len(fx.world.calls), count)
                self.assertEqual(fx.store.checkpoint('C1').budget.tool_calls, count)

    def phase(self, fx):
        with fx.engine.gateway.execution_scope(), fx.engine.gateway._auth_scope(fx.auth):
            return fx.engine.run_one_approved_phase(fx.store.checkpoint('C1'), fx.request, fx.auth)

    def test_entry_guards_do_not_read(self):
        for mode in ('no_scope', 'no_auth', 'no_timing', 'wrong_thread'):
            with self.subTest(mode=mode):
                fx = self.ready_fixture()
                gateway = fx.engine.gateway
                if mode == 'no_scope':
                    with gateway._auth_scope(fx.auth), self.assertRaises(GateDenied):
                        gateway.read_window_readiness('C1')
                elif mode == 'no_auth':
                    with gateway.execution_scope(), self.assertRaises(GateDenied):
                        gateway.read_window_readiness('C1')
                else:
                    with gateway.execution_scope(), gateway._auth_scope(fx.auth):
                        if mode == 'no_timing':
                            gateway._timing = None
                            with self.assertRaises(GateDenied):
                                gateway.read_window_readiness('C1')
                        else:
                            failures = []
                            def foreign():
                                try:
                                    gateway.read_window_readiness('C1')
                                except GateDenied:
                                    failures.append('denied')
                            thread = threading.Thread(target=foreign)
                            thread.start()
                            thread.join()
                            self.assertEqual(failures, ['denied'])
                self.assertEqual(len(fx.world.calls), 0)

    def test_stop_token_cannot_supply_readiness_authority(self):
        # Isolate the real entry-kind guard without provisioning a registered host.
        # Associations have independent host tests; this proves the helper does
        # not forward 'stop' and thereby turn control authority into reads.
        from proofkey.host_admission import RegisteredAdmissionOwner, _ObservedStopV2, AdmissionCompositionFailure
        fx = self.ready_fixture()
        owner = object.__new__(RegisteredAdmissionOwner)
        owner.active = object.__new__(_ObservedStopV2)
        owner.associations = lambda: None
        with fx.engine.gateway.execution_scope(), fx.engine.gateway._auth_scope(fx.auth):
            fx.engine.gateway._admission_owner = owner
            with self.assertRaises(AdmissionCompositionFailure):
                fx.engine.gateway.read_window_readiness('C1')
        self.assertEqual(len(fx.world.calls), 0)

    def test_wrong_original_or_checkpoint_does_not_read(self):
        changes = [{'phase': 'window_gate'}, {'next_gate': 'reschedule'},
            {'profile_version': 'v1.2'}, {'process_version': 'v1'}, {'policy_version': 'v2'},
            {'ownership_state': 'pending'}, {'deadline': NOW}]
        for change in changes:
            with self.subTest(change=change):
                fx = self.ready_fixture(checkpoint_changes=change)
                with self.assertRaises(GateDenied):
                    self.read_ready(fx)
                self.assertEqual(len(fx.world.calls), 0)
        fx = self.ready_fixture(request=make_request(kind='reschedule_exact', consent_mode='exact_slot',
                                                   arguments={'slot': 'S1'}))
        with self.assertRaises(GateDenied):
            self.read_ready(fx)
        self.assertEqual(len(fx.world.calls), 0)
        fx = self.ready_fixture()
        fx.store.set_stop('C1', 'G1')
        with self.assertRaises(GateDenied):
            self.read_ready(fx)
        self.assertEqual(len(fx.world.calls), 0)

    def test_finite_branch_selects_then_advances_and_retains_latest_observations(self):
        fx = self.ready_fixture(checkpoint_changes={'next_gate': 'window_readiness'})
        before = fx.store.checkpoint('C1')
        kept = AuthorityObservation(authority='delivery', fact='risk', object_id='O1', value='safe',
            revision='v1', observed_at=fx.clock.now(), evidence_ref='keep-delivery')
        stale = AuthorityObservation(authority='scheduling', fact='slot', object_id='O1', value='OLD',
            revision='v0', observed_at=fx.clock.now(), evidence_ref='old-slot')
        fx.store.save_checkpoint(before.model_copy(update={'observations': [kept, stale]}))
        selections = []
        save = fx.store.save_checkpoint
        def traced(checkpoint):
            selections.append((checkpoint.phase, checkpoint.next_gate, checkpoint.budget.tool_calls))
            return save(checkpoint)
        fx.store.save_checkpoint = traced
        result = self.phase(fx)
        self.assertEqual(result.phase, 'window_gate')
        self.assertEqual(selections[0], ('window_readiness', 'read_authority', 0))
        self.assertEqual(selections[-1], ('window_gate', 'window_gate', 4))
        values = {o.authority + '.' + o.fact: o for o in result.observations}
        self.assertEqual(len(values), 11)
        self.assertEqual(values['delivery.risk'], kept)
        self.assertEqual(values['scheduling.slot'].value, 'S0')
        self.assertEqual(result.budget.tool_calls, 4)
        self.assertEqual((result.binding, result.deadline), (before.binding, before.deadline))
        self.assertEqual(fx.store.intents('C1'), ())

    def test_readiness_failure_is_unavailable_without_handoff(self):
        for slot in ('S1', '', True, None):
            with self.subTest(slot=slot):
                fx = self.ready_fixture()
                fx.world.mutate('scheduling.slot', slot)
                result = self.phase(fx)
                self.assertEqual((result.phase, result.processing_status), ('window_readiness', 'unavailable'))
                self.assertEqual(result.budget.tool_calls, 4)
                self.assertEqual(fx.store.intents('C1'), ())
                self.assertEqual(fx.world.effect_count('enqueue_handoff'), 0)

    def test_unavailable_readiness_source_retains_debit_without_dispatch(self):
        for fault in ('429', 'timeout_before'):
            with self.subTest(fault=fault):
                fx = self.ready_fixture()
                fx.world.set_fault('list_permitted_slots', fault)
                result = self.phase(fx)
                self.assertEqual((result.phase, result.processing_status), ('window_readiness', 'unavailable'))
                self.assertEqual(result.budget.tool_calls, 4)
                self.assertEqual(fx.store.intents('C1'), ())
                self.assertEqual(fx.world.effect_count('reschedule'), 0)
                self.assertEqual(fx.world.effect_count('enqueue_handoff'), 0)

    def test_current_fences_are_rechecked_before_and_after_fourth_read(self):
        for boundary in ('before_slot', 'after_slot'):
            for field, value in (('next_gate', 'ask_operator'), ('ownership_state', 'pending'),
                    ('ownership_state_revision', 'v2'), ('ownership_epoch', 1), ('stop', True),
                    ('deadline', 'expired')):
                with self.subTest(boundary=boundary, field=field):
                    fx = self.ready_fixture()
                    before = fx.store.checkpoint('C1')
                    def change():
                        current = fx.store.checkpoint('C1')
                        if field == 'stop':
                            fx.store.set_stop('C1', 'G1')
                        elif field == 'deadline':
                            fx.clock.advance(7201)
                        else:
                            fx.store.save_checkpoint(current.model_copy(update={field: value}))
                    port = fx.engine.gateway.bundle.operator if boundary == 'before_slot' else fx.engine.gateway.bundle.scheduling
                    method = 'read_owner' if boundary == 'before_slot' else 'list_permitted_slots'
                    real = getattr(port, method)
                    def changing(request):
                        reply = real(request)
                        change()
                        return reply
                    name = 'operator' if boundary == 'before_slot' else 'scheduling'
                    fx.engine.gateway.bundle = replace(fx.engine.gateway.bundle,
                        **{name: ForwardPort(port, **{method: changing})})
                    result = self.phase(fx)
                    self.assertEqual(result.phase, 'window_readiness')
                    self.assertEqual(result.budget.tool_calls, 3 if boundary == 'before_slot' else 4)
                    self.assertEqual((result.binding, result.deadline), (before.binding, before.deadline))
                    if field == 'stop':
                        self.assertTrue(result.stop.requested)
                    self.assertEqual(fx.store.intents('C1'), ())
                    self.assertEqual(fx.world.effect_count('enqueue_handoff'), 0)

    def test_version_binding_and_phase_fences_reject_changed_read_snapshots(self):
        # Frozen versions/generation cannot be changed by save_checkpoint; inject
        # changed current snapshots at that boundary, without corrupting storage.
        for boundary in ('before_slot', 'after_slot'):
            for field, value in (('profile_version', 'v9'), ('process_version', 'v9'),
                    ('policy_version', 'v9'), ('binding', 'G2'), ('phase', 'window_gate'),
                    ('deadline', 'shorter')):
                with self.subTest(boundary=boundary, field=field):
                    fx = self.ready_fixture()
                    checkpoint = fx.store.checkpoint
                    changed = False
                    def current(case_id):
                        value_now = checkpoint(case_id)
                        if not changed:
                            return value_now
                        replacement = (value_now.binding.model_copy(update={'generation': 'G2'}) if field == 'binding'
                            else value_now.deadline - timedelta(seconds=1) if field == 'deadline' else value)
                        return value_now.model_copy(update={field: replacement})
                    fx.store.checkpoint = current
                    real = fx.engine.gateway._facts
                    def flip(scope, fields, **options):
                        nonlocal changed
                        reply = real(scope, fields, **options)
                        if (boundary == 'before_slot' and options.get('purpose') == 'window_readiness_identity'
                                or boundary == 'after_slot' and options.get('purpose') == 'window_readiness'):
                            changed = True
                        return reply
                    fx.engine.gateway._facts = flip
                    with self.assertRaises((GateDenied, JournalFailure) if field == 'binding' else GateDenied):
                        self.read_ready(fx)
                    changed = False
                    self.assertEqual(checkpoint('C1').phase, 'window_readiness')
                    self.assertEqual(len(fx.world.calls), 3 if boundary == 'before_slot' else 4)
                    self.assertEqual(fx.store.intents('C1'), ())

    def test_advancing_save_failure_propagates_without_advancement(self):
        fx = self.ready_fixture()
        real = fx.store.save_checkpoint
        def fail(checkpoint):
            if checkpoint.phase == 'window_gate':
                raise JournalFailure('advancing save failed')
            return real(checkpoint)
        fx.store.save_checkpoint = fail
        with self.assertRaises(JournalFailure):
            self.phase(fx)
        current = fx.store.checkpoint('C1')
        self.assertEqual(current.phase, 'window_readiness')
        self.assertEqual(current.budget.tool_calls, 4)
        self.assertEqual(fx.store.intents('C1'), ())

    def test_actual_commit_failure_rolls_back_advancement(self):
        fault = CommitFault()
        fx = self.ready_fixture(before_commit=fault)
        read = fx.engine.gateway.read_window_readiness
        def arm_after_settlement(case_id):
            reply = read(case_id)
            fault.arm()
            return reply
        fx.engine.gateway.read_window_readiness = arm_after_settlement
        with self.assertRaises(JournalFailure):
            self.phase(fx)
        self.assertEqual(fx.store.checkpoint('C1').phase, 'window_readiness')
        self.assertEqual(fx.store.checkpoint('C1').budget.tool_calls, 4)
        self.assertEqual(fx.store.intents('C1'), ())

    def test_source_read_commit_fault_retains_debit_and_never_advances(self):
        fault = CommitFault()
        fx = self.ready_fixture(before_commit=fault)
        port = fx.engine.gateway.bundle.scheduling
        def arm_after_physical(request):
            result = port.list_permitted_slots(request)
            fault.arm()
            return result
        fx.engine.gateway.bundle = replace(fx.engine.gateway.bundle,
            scheduling=ForwardPort(port, list_permitted_slots=arm_after_physical))
        with self.assertRaises(JournalFailure):
            self.phase(fx)
        result = fx.store.checkpoint('C1')
        self.assertEqual(result.phase, 'window_readiness')
        self.assertEqual(result.budget.tool_calls, 4)
        self.assertEqual(fx.store.intents('C1'), ())

    def test_new_observation_at_save_boundary_is_not_overwritten(self):
        fx = self.ready_fixture()
        save = fx.engine._save_window_readiness
        kept = AuthorityObservation(authority='delivery', fact='risk', object_id='O1', value='safe',
            revision='v9', observed_at=fx.clock.now(), evidence_ref='latest-delivery')
        def add_latest(expected, **changes):
            if changes.get('phase') == 'window_gate':
                current = fx.store.checkpoint('C1')
                fx.store.save_checkpoint(current.model_copy(update={'observations': [*current.observations, kept]}))
            return save(expected, **changes)
        fx.engine._save_window_readiness = add_latest
        result = self.phase(fx)
        self.assertEqual(result.phase, 'window_gate')
        self.assertIn(kept, result.observations)

    def test_save_compares_under_transaction_and_preserves_new_stop(self):
        fx = self.ready_fixture()
        self.assertTrue(callable(getattr(fx.engine, '_save_window_readiness', None)))
        expected = fx.store.checkpoint('C1')
        transaction = fx.store._transaction
        armed = True
        @contextmanager
        def changing_transaction():
            nonlocal armed
            if armed:
                armed = False
                fx.store.set_stop('C1', 'G1')
            with transaction():
                yield
        fx.store._transaction = changing_transaction
        with fx.engine.gateway.execution_scope(), fx.engine.gateway._auth_scope(fx.auth):
            with self.assertRaises(GateDenied):
                fx.engine._save_window_readiness(expected, phase='window_gate', next_gate='window_gate')
        self.assertTrue(fx.store.checkpoint('C1').stop.requested)
        self.assertEqual(fx.store.checkpoint('C1').phase, 'window_readiness')

    def test_save_compares_new_nonstop_fences_inside_outer_transaction(self):
        for field, value in (('next_gate', 'ask_operator'), ('ownership_state', 'pending'),
                ('ownership_state_revision', 'v2'), ('ownership_epoch', 1), ('phase', 'wait_operator')):
            with self.subTest(field=field):
                fx = self.ready_fixture()
                expected = fx.store.checkpoint('C1')
                transaction = fx.store._transaction
                armed = True
                @contextmanager
                def changing_transaction():
                    nonlocal armed
                    if armed:
                        armed = False
                        current = fx.store.checkpoint('C1')
                        fx.store.save_checkpoint(current.model_copy(update={field: value}))
                    with transaction():
                        yield
                fx.store._transaction = changing_transaction
                with fx.engine.gateway.execution_scope(), fx.engine.gateway._auth_scope(fx.auth):
                    with self.assertRaises(GateDenied):
                        fx.engine._save_window_readiness(expected, phase='window_gate', next_gate='window_gate')
                current = fx.store.checkpoint('C1')
                self.assertEqual(getattr(current, field), value)
                self.assertNotEqual(current.phase, 'window_gate')
                self.assertEqual(current.budget, expected.budget)

    def test_fresh_real_engine_fits_original_budget_and_verifies_original(self):
        fx = self.fixture(profile_name='flat-window-readiness-v1')
        self.assertFalse(fx.store.has_case('C1'))
        deadlines = []
        bundle = fx.engine.gateway.bundle
        for port_name, methods in (('case', ('read_case', 'read_principal')),
                ('operator', ('read_owner',)), ('delivery', ('read_delivery',)),
                ('scheduling', ('list_permitted_slots', 'reschedule', 'read_schedule'))):
            port = getattr(bundle, port_name)
            overrides = {}
            for method in methods:
                real = getattr(port, method)
                def capture(value, *, deadline=None, real=real, method=method):
                    cutoff = deadline if deadline is not None else value.deadline
                    deadlines.append({'operation': method, 'started_at': fx.clock.now().isoformat(),
                        'deadline': cutoff.isoformat(), 'allowance_seconds': (cutoff - fx.clock.now()).total_seconds()})
                    return real(value, deadline=deadline) if method == 'reschedule' else real(value)
                overrides[method] = capture
            bundle = replace(bundle, **{port_name: ForwardPort(port, **overrides)})
        fx.engine.gateway.bundle = bundle
        start = fx.clock.now()
        result = fx.engine.run(fx.request, fx.auth)
        self.assertEqual(result.effects['reschedule'].status, 'verified')
        self.assertEqual(result.effects['reschedule'].postcondition, {'slot': 'S1'})
        self.assertEqual(result.handoff_status, 'none')
        self.assertEqual(fx.world.effect_count('reschedule'), 1)
        self.assertEqual(fx.world.effect_count('enqueue_handoff'), 0)
        checkpoint = fx.store.checkpoint('C1')
        self.assertEqual(checkpoint.phase, 'complete')
        self.assertEqual(checkpoint.deadline, start + timedelta(seconds=120))
        self.assertEqual(checkpoint.budget.tool_calls, len(fx.world.calls))
        self.assertEqual(checkpoint.budget.tool_calls, 15)
        self.assertLessEqual(checkpoint.budget.tool_calls, 24)
        self.assertLessEqual(checkpoint.budget.active_seconds, 120)
        self.assertEqual(len(deadlines), 15)
        self.assertTrue(all(0 < item['allowance_seconds'] <= 10 for item in deadlines), deadlines)
        leases = [fx.store.entry(row[0]) for row in fx.store._db.execute('SELECT entry_id FROM entries')]
        admission = [fx.store.admission_entry(row[0]) for row in
                     fx.store._db.execute('SELECT entry_id FROM admission_entries')]
        self.assertEqual((len(admission), len(leases)), (3, 12))
        self.assertTrue(all(lease.reserved_seconds <= 10 for lease in leases + admission))
        self.assertEqual([(c.operation, c.purpose) for c in fx.world.calls], [
            ('read_case', 'bind_request'), ('read_principal', 'bind_request'), ('read_owner', 'bind_request'),
            ('read_case', 'window_readiness_identity'), ('read_principal', 'window_readiness_identity'),
            ('read_owner', 'window_readiness_identity'), ('list_permitted_slots', 'window_readiness'),
            ('read_case', 'material_authority'), ('read_principal', 'material_authority'),
            ('read_delivery', 'material_authority'), ('read_case', 'material_authority'),
            ('read_owner', 'material_authority'), ('list_permitted_slots', 'material_authority'),
            ('reschedule', 'dispatch'), ('read_schedule', 'reconcile_original')])
        if os.environ.get('PROOFKEY_TASK3_WITNESS') == '1':
            print(json.dumps({'core_only': True, 'physical_calls': [
                {'operation': call.operation, 'purpose': call.purpose, **timing}
                for call, timing in zip(fx.world.calls, deadlines)],
                'budget': checkpoint.budget.model_dump(mode='json'),
                'case_leases': [lease.model_dump(mode='json') for lease in leases],
                'admission_leases': [lease.model_dump(mode='json') for lease in admission]}, sort_keys=True))

    def test_slot_changes_after_readiness_or_material_read_prevent_effect(self):
        for boundary in ('after_readiness', 'after_material'):
            with self.subTest(boundary=boundary):
                fx = self.fixture(profile_name='flat-window-readiness-v1')
                if boundary == 'after_readiness':
                    real = fx.engine.gateway.read_window_readiness
                    def move(case_id):
                        reply = real(case_id)
                        fx.world.mutate('scheduling.slot', 'OTHER')
                        return reply
                    fx.engine.gateway.read_window_readiness = move
                else:
                    real = fx.world._read_scheduling_raw
                    def move(operation, request):
                        reply = real(operation, request)
                        if request.purpose == 'material_authority':
                            fx.world.mutate('scheduling.slot', 'OTHER')
                        return reply
                    fx.world._read_scheduling_raw = move
                fx.engine.run(fx.request, fx.auth)
                self.assertEqual(fx.world.effect_count('reschedule'), 0)

    def test_otherwise_current_direct_candidate_intent_cannot_bypass_s0(self):
        fx = self.ready_fixture(checkpoint_changes={'phase': 'window_gate', 'next_gate': 'reschedule'})
        fx.world.mutate('scheduling.slot', 'OTHER')
        checkpoint = fx.store.checkpoint('C1')
        intent = make_intent(binding=checkpoint.binding, profile_version='v1.3',
            process_version='v2-window-readiness', ownership_state_revision='v1', ownership_epoch=0,
            expected_revisions=fx.world.material_revisions())
        with fx.engine.gateway.execution_scope(), fx.engine.gateway._auth_scope(fx.auth):
            result = fx.engine.gateway.execute(intent)
        self.assertEqual(result.status, 'rejected')
        self.assertEqual(fx.world.effect_count('reschedule'), 0)
        self.assertFalse(any(c.operation == 'reschedule' for c in fx.world.calls))

    def test_policy_independently_fences_s0_before_graph_admission(self):
        # Removing this policy check must fail even if the downstream graph permits
        # the edge: graph prerequisites and fresh policy are separate boundaries.
        fx = self.ready_fixture(checkpoint_changes={'phase': 'window_gate', 'next_gate': 'reschedule'})
        fx.world.mutate('scheduling.slot', 'OTHER')
        current = fx.store.checkpoint('C1')
        intent = make_intent(binding=current.binding, profile_version='v1.3',
            process_version='v2-window-readiness', ownership_state_revision='v1', ownership_epoch=0,
            expected_revisions=fx.world.material_revisions())
        with fx.engine.gateway.execution_scope(), fx.engine.gateway._auth_scope(fx.auth):
            observations = fx.engine.gateway.read_material_authorities(intent)
        proposal = ActionProposal(operation='reschedule', stage='commit', arguments={'slot': 'S1'}, evidence_refs=[])
        with patch.object(ProcessController, 'permits', return_value=True):
            decision = fx.engine.gateway.gate.evaluate(fx.request, proposal, observations, current)
        self.assertFalse(decision.allowed)

    def test_committed_effect_survives_unreadable_original(self):
        for mode in ('malformed', 'over_bound', 'exception'):
            with self.subTest(mode=mode):
                fx = self.fixture(profile_name='flat-window-readiness-v1')
                read = fx.world._read_scheduling_raw
                def unreadable(operation, request):
                    raw = read(operation, request)
                    if request.target.kind != 'original_effect':
                        return raw
                    self.assertEqual(fx.world.effect_count('reschedule'), 1)
                    if mode == 'exception':
                        raise ValueError('original source unavailable')
                    if mode == 'malformed':
                        return b'{'
                    body = json.loads(raw)
                    body['body']['evidence_refs'] = ['x' * 1025]
                    return json.dumps(body).encode()
                fx.world._read_scheduling_raw = unreadable
                result = fx.engine.run(fx.request, fx.auth)
                self.assertEqual(result.effects['reschedule'].status, 'outcome_unknown')
                self.assertEqual(result.effects['reschedule'].reason, 'original_read_unavailable')
                before = fx.store.checkpoint('C1')
                records = fx.store.intents('C1')
                self.assertEqual(len(records), 1)
                record = records[0]
                self.assertEqual(record.state, 'outcome_unknown')
                self.assertEqual(before.budget.effects, 1)
                self.assertEqual(before.budget.reconciliation_reads, {record.intent.action_id: 1})
                self.assertEqual(before.budget.retries, {})
                with fx.world._connect() as connection:
                    rows = [dict(row) for row in connection.execute('SELECT * FROM effects')]
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]['provider_key'], record.intent.provider_key)
                self.assertEqual(rows[0]['action_id'], record.intent.action_id)
                self.assertEqual(rows[0]['fingerprint'], record.intent.argument_fingerprint)
                self.assertTrue(rows[0]['request_id'].startswith('provider:window-envelope-v1:'))
                # Recovery may consume another original-read allowance, never a second write.
                fx.engine.recover('C1', fx.auth)
                after = fx.store.checkpoint('C1')
                self.assertEqual(fx.store.intents('C1')[0].intent, record.intent)
                self.assertEqual((after.binding, after.deadline), (before.binding, before.deadline))
                self.assertEqual(after.budget.effects, 1)
                self.assertEqual(after.budget.retries, {})
                with fx.world._connect() as connection:
                    self.assertEqual([dict(row) for row in connection.execute('SELECT * FROM effects')], rows)
                self.assertEqual(sum(c.operation == 'reschedule' for c in fx.world.calls), 1)
                self.assertEqual(fx.world.effect_count('enqueue_handoff'), 0)
                if os.environ.get('PROOFKEY_TASK3_WITNESS') == '1':
                    print(json.dumps({'unreadable_original': mode,
                        'journal_intent': record.intent.model_dump(mode='json'), 'source_rows': rows,
                        'before_recovery_budget': before.budget.model_dump(mode='json'),
                        'after_recovery_budget': after.budget.model_dump(mode='json'),
                        'original_result': result.effects['reschedule'].model_dump(mode='json'),
                        'physical_calls': [{'operation': c.operation, 'purpose': c.purpose} for c in fx.world.calls]},
                        sort_keys=True))

    def test_legacy_reference_domain_contrast(self):
        for profile in ('flat-v1.3', 'flat-window-readiness-v1'):
            for kind in ('reschedule_window', 'reschedule_exact'):
                for length in (1024, 1025):
                    with self.subTest(profile=profile, kind=kind, length=length):
                        request = make_request() if kind == 'reschedule_window' else make_request(
                            kind=kind, consent_mode='exact_slot', arguments={'slot': 'S1'})
                        fx = self.fixture(profile_name=profile, request=request)
                        with fx.world._connect() as connection:
                            connection.execute('UPDATE facts SET evidence_ref=? WHERE identity=?',
                                               ('e' * length, 'scheduling.slot'))
                        result = fx.engine.run(request, fx.auth)
                        if profile == 'flat-window-readiness-v1' and length == 1025:
                            self.assertEqual(fx.world.effect_count('reschedule'), 0)
                            self.assertFalse(any(c.operation == 'reschedule' for c in fx.world.calls))
                            self.assertEqual(fx.store.intents('C1'), ())
                            self.assertEqual(fx.store.checkpoint('C1').processing_status, 'unavailable')
                        else:
                            self.assertEqual(result.effects['reschedule'].status, 'verified')
                            self.assertEqual(fx.world.effect_count('reschedule'), 1)


if __name__ == '__main__':
    unittest.main()
