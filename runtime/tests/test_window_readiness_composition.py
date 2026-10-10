"""Current-source registered v3 integration, never historical qualification."""
from contextlib import ExitStack, contextmanager, redirect_stdout
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import io
import json
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from proofkey import synthetic_provisioning as provisioning
from proofkey.cli import main
from proofkey.bootstrap import CliReceiptV1
from proofkey.contracts import AuthContext
from proofkey.host import AuthResolver, ProfileRegistry, RuntimeFactory
from proofkey.host_admission import AdmissionCompositionFailure, HostExecutableBindingV1, LocalAdmissionCompositionV1
from proofkey.host_contracts import HostLimitsV1, InterfaceLimitsV1
from proofkey.profiles import load_profile
from proofkey.registered_releases import RegisteredReleaseV1
from support_window_readiness import candidate_case_data, opened_candidate_case
from support_synthetic_provisioning import case_data, cj, context
from test_host_admission import paced_clock

KEY = 'fixed-synthetic-window-readiness-v3'
EXPECTED = [
    ('read_case', 'bind_request'), ('read_principal', 'bind_request'), ('read_owner', 'bind_request'),
    ('read_case', 'window_readiness_identity'), ('read_principal', 'window_readiness_identity'),
    ('read_owner', 'window_readiness_identity'), ('list_permitted_slots', 'window_readiness'),
    ('read_case', 'material_authority'), ('read_principal', 'material_authority'),
    ('read_delivery', 'material_authority'), ('read_case', 'material_authority'),
    ('read_owner', 'material_authority'), ('list_permitted_slots', 'material_authority'),
    ('reschedule', 'dispatch'), ('read_schedule', 'reconcile_original')]


@contextmanager
def measured_transports(state, clock):
    """Delegate each physical adapter call once; record its real journal lease."""
    from proofkey.journal import CaseStore
    from proofkey.adapters.case import CaseAdapter
    from proofkey.adapters.operator import OperatorAdapter
    from proofkey.adapters.delivery import DeliveryAdapter
    from proofkey.adapters.scheduling import SchedulingAdapter
    leases, calls = [], []
    def begin(original):
        def invoke(store, *args, **kwargs):
            lease = original(store, *args, **kwargs)
            leases.append(lease)
            return lease
        return invoke
    def transport(original, operation):
        def invoke(adapter, request, **kwargs):
            lease = leases[-1]
            target = getattr(request, 'target', None)
            calls.append(dict(operation=operation,
                purpose=getattr(request, 'purpose', 'dispatch'),
                authority=(target.authority or 'scheduling') if target else 'scheduling',
                target=target.model_dump(mode='json') if target else None,
                lease_id=lease.entry_id, reserved_seconds=lease.reserved_seconds,
                started_at=lease.started_at.isoformat(),
                lease_deadline=lease.deadline.isoformat(),
                transport_deadline=(kwargs.get('deadline') or request.deadline).isoformat()))
            # Real transport and validation run normally; deterministic nonzero latency.
            state['tick'] += 0.025
            return original(adapter, request, **kwargs)
        return invoke
    with ExitStack() as stack:
        for method in ('begin_admission_read', 'begin_read', 'begin_dispatch'):
            stack.enter_context(patch.object(CaseStore, method, begin(getattr(CaseStore, method))))
        for cls, methods in ((CaseAdapter, ('read_case', 'read_principal')),
                             (OperatorAdapter, ('read_owner',)),
                             (DeliveryAdapter, ('read_delivery',)),
                             (SchedulingAdapter, ('list_permitted_slots', 'reschedule', 'read_schedule'))):
            for method in methods:
                stack.enter_context(patch.object(cls, method, transport(getattr(cls, method), method)))
        yield calls


def lease_rows(path):
    with sqlite3.connect(path) as db:
        rows = {}
        for table in ('admission_entries', 'entries'):
            for (raw,) in db.execute('SELECT lease_json FROM ' + table):
                lease = json.loads(raw)
                rows[lease['entry_id']] = dict(table=table, **lease)
        return rows


class WindowReadinessCompositionTests(unittest.TestCase):
    def assert_accounting(self, calls, path, execution, clock, budget, lane):
        self.assertEqual([(c['operation'], c['purpose']) for c in calls], EXPECTED)
        self.assertEqual(len(set(c['lease_id'] for c in calls)), 15)
        self.assertEqual(calls[7]['authority'], 'case')
        self.assertEqual(calls[10]['authority'], 'policy')
        rows = lease_rows(path)
        self.assertEqual(len(rows), 15)
        for i, call in enumerate(calls):
            row = rows[call['lease_id']]
            call['elapsed_seconds'] = row['elapsed_seconds']
            call['state'] = row['state']
            call['table'] = row['table']
            self.assertEqual(row['state'], 'settled')
            self.assertGreater(row['elapsed_seconds'], 0)
            self.assertLessEqual(row['elapsed_seconds'], row['reserved_seconds'])
            self.assertLessEqual(row['reserved_seconds'], 10)
            self.assertEqual(row['table'], 'admission_entries' if i < 3 else 'entries')
            if i < 3:
                self.assertEqual((row['charge'], row['charge_generation']), ('unbound', None))
        with sqlite3.connect(path) as db:
            account = json.loads(db.execute('SELECT account_json FROM admission_accounts').fetchone()[0])
            self.assertEqual((account['imported'], account['pending_tool_calls'], account['pending_active_seconds']),
                             (True, 0, 0))
            self.assertEqual(account['tool_calls'], 3)
        self.assertAlmostEqual(budget.active_seconds, sum(c['elapsed_seconds'] for c in calls))
        self.assertEqual(budget.tool_calls, 15)
        self.assertEqual((budget.max_tool_calls, budget.max_active_seconds, budget.max_tool_seconds),
                         (24, 120, 10))
        self.assertLessEqual(budget.active_seconds, 120)
        self.assertEqual(budget.retries, {})
        self.assertEqual(sum(budget.reconciliation_reads.values()), 1)
        elapsed = clock.monotonic() - execution.captured_monotonic
        self.assertGreater(elapsed, 0)
        self.assertGreater(execution.remaining_seconds(clock), 0)
        print('J05_TIMING ' + json.dumps(dict(lane=lane, calls=calls,
            admission_account=account,
            active_seconds=budget.active_seconds, host_elapsed_seconds=elapsed,
            host_remaining_seconds=execution.remaining_seconds(clock)), sort_keys=True))

    def test_v3_preparation_and_finalized_registered_run(self):
        with opened_candidate_case() as fx:
            self.assertEqual(fx.prepared.binding.host_factory_key, KEY)
            self.assertEqual(fx.runtime.profile.profile_id, 'flat-window-readiness-v1')
            self.assertFalse(fx.runtime.store.has_case(fx.request.case_id))
            self.assertEqual(fx.runtime.world.calls, ())
            execution = context(fx.clock, seconds=120)
            with measured_transports(fx.state, fx.clock) as calls:
                result = fx.runtime.run_registered(fx.request, fx.auth, execution=execution)
            self.assertEqual(result.effects['reschedule'].status, 'verified')
            self.assertEqual(fx.runtime.world.effect_count('reschedule'), 1)
            self.assertEqual([(c.operation, c.purpose) for c in fx.runtime.world.calls], EXPECTED)
            checkpoint = fx.runtime.store.checkpoint(fx.request.case_id)
            self.assertEqual(checkpoint.budget.tool_calls, 15)
            self.assertLessEqual(checkpoint.budget.active_seconds, 120)
            self.assertEqual(fx.runtime.world.effect_count('enqueue_handoff'), 0)
            claim = fx.runtime.admission.claim_for_case(fx.request.case_id, execution=context(fx.clock))
            route = fx.runtime.admission.route_for_case(fx.request.case_id, execution=context(fx.clock))
            body = json.loads(claim.wire_bytes)
            self.assertEqual((claim.state, route.state), ('admission_observed', 'admission_observed'))
            self.assertEqual(claim.binding, result.binding)
            self.assertEqual(route.binding, result.binding)
            self.assertEqual(route.request, fx.request)
            self.assertEqual(body['route_id'], json.loads(route.wire_bytes)['reservation_id'])
            source = fx.runtime.world.capture_retained_state(execution=context(fx.clock), clock=fx.clock)
            journal = fx.runtime.store.capture_retained_state(execution=context(fx.clock), clock=fx.clock)
            self.assertEqual(body['final_source_hash'], source.content_hash)
            self.assertEqual(body['final_journal_hash'], journal.content_hash)
            self.assertIn('provider:window-envelope-v1:', source.payload.decode())
            print('J05_FINALIZATION ' + json.dumps(dict(lane='library', state=claim.state,
                claim_id=body['claim_id'], route_id=body['route_id'], artifact_hash=body['artifact_hash'],
                final_source_hash=source.content_hash, final_journal_hash=journal.content_hash,
                binding=body['binding']), sort_keys=True))
            self.assert_accounting(calls, fx.prepared.host_release.resource_root / 'journal.sqlite',
                                   execution, fx.clock, checkpoint.budget, 'library')

    def test_closed_selection_for_all_keys(self):
        from proofkey.profiles import _validate_selected_profile
        for key, name in [('fixed-synthetic-v1', 'flat-v1.3'),
                          ('fixed-synthetic-observed-stop-v2', 'flat-v1.3'),
                          (KEY, 'flat-window-readiness-v1')]:
            _validate_selected_profile(key, load_profile(name), 'reschedule_window')
            for wrong in ['flat-v1.2', 'flat-v1.4',
                          'flat-v1.3' if name != 'flat-v1.3' else 'flat-window-readiness-v1']:
                with self.subTest(key=key, wrong=wrong), self.assertRaises(ValueError):
                    _validate_selected_profile(key, load_profile(wrong), 'reschedule_window')
        for kind in ['goods_refusal', 'reschedule_exact']:
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                _validate_selected_profile(KEY, load_profile('flat-window-readiness-v1'), kind)
        with self.assertRaises(ValueError):
            _validate_selected_profile('unregistered', load_profile('flat-v1.3'))

    def test_v3_ordinary_parent_guard_survives_only_admission_phase_expiry(self):
        from proofkey.host_admission import control_context
        with opened_candidate_case() as fx:
            execution = context(fx.clock, seconds=120)
            fx.runtime.admission.prepare_entry(fx.request, fx.auth, execution=execution)
            fx.state['tick'] += 6
            fx.runtime.admission.guard_execution(execution, fx.runtime.engine.gateway)
            # Admission/sealing retains its own original five-second bound.
            with self.assertRaises(AdmissionCompositionFailure):
                control_context(execution, fx.clock)
            with self.assertRaises(AdmissionCompositionFailure):
                fx.runtime.admission.require_entry(fx.request, fx.auth)
            with self.assertRaises(AdmissionCompositionFailure) as caught:
                fx.runtime.admission.seal_before_admit('not-reached', None, fx.request, None)
            self.assertEqual(caught.exception.code, 'timeout')
            with self.assertRaises(AdmissionCompositionFailure):
                fx.runtime.admission.guard_execution(execution, fx.runtime.engine.gateway, entry_kind='stop')

    def test_parent_guards_reject_expiry_identity_and_legacy_phase_overrun(self):
        from support_observed_stop_v2 import opened_case
        for key in ('fixed-synthetic-v1', 'fixed-synthetic-observed-stop-v2'):
            with self.subTest(key=key), opened_case(key) as fx:
                execution = context(fx.clock, seconds=120)
                fx.runtime.admission.prepare_entry(fx.request, fx.auth, execution=execution)
                fx.state['tick'] += 6
                with self.assertRaises(AdmissionCompositionFailure):
                    fx.runtime.admission.guard_execution(execution, fx.runtime.engine.gateway)
        with opened_candidate_case() as fx:
            execution = context(fx.clock, seconds=120)
            fx.runtime.admission.prepare_entry(fx.request, fx.auth, execution=execution)
            for utc_delta, monotonic_delta in ((120, 0), (121, 0), (0, 120), (0, 121),
                                                (-1, 0), (0, -1)):
                tick, offset = fx.state['tick'], fx.state['utc_offset']
                fx.state['tick'] += monotonic_delta
                fx.state['utc_offset'] += utc_delta - monotonic_delta
                with self.subTest(utc=utc_delta, monotonic=monotonic_delta), self.assertRaises(AdmissionCompositionFailure):
                    fx.runtime.admission.guard_execution(execution, fx.runtime.engine.gateway)
                fx.state['tick'], fx.state['utc_offset'] = tick, offset
            for other, gateway in [(context(fx.clock, seconds=120), fx.runtime.engine.gateway),
                                   (execution, object())]:
                with self.assertRaises(AdmissionCompositionFailure):
                    fx.runtime.admission.guard_execution(other, gateway)
            gateway = fx.runtime.engine.gateway
            fx.runtime.engine._gateway = object()
            try:
                with self.assertRaises(AdmissionCompositionFailure):
                    fx.runtime.admission.guard_execution(execution, gateway)
            finally:
                fx.runtime.engine._gateway = gateway

    def test_final_observation_clips_both_original_bounds_and_its_own_phase(self):
        from proofkey.host_admission import _observation_context
        for utc_elapsed, monotonic_elapsed, remaining in [(6, 6, 5), (118, 6, 2), (6, 119, 1)]:
            with self.subTest(utc=utc_elapsed, monotonic=monotonic_elapsed), paced_clock() as (clock, state):
                execution = context(clock, seconds=120)
                state['tick'] += monotonic_elapsed
                state['utc_offset'] += utc_elapsed - monotonic_elapsed
                phase = _observation_context(execution, clock)
                self.assertEqual(phase.remaining_seconds(clock), remaining)
                self.assertLessEqual(phase.deadline, execution.deadline)
                self.assertLessEqual(phase.monotonic_deadline, execution.monotonic_deadline)
                self.assertEqual((phase.deadline - phase.captured_at).total_seconds(), remaining)
                state['tick'] += remaining
                self.assertEqual(phase.remaining_seconds(clock), 0)

    def test_initial_invalid_selection_allocates_no_child(self):
        with tempfile.TemporaryDirectory() as folder, paced_clock() as (clock, _):
            parent = Path(folder).resolve()
            parent.chmod(0o700)
            for key, kind in [(KEY, 'goods_refusal'), ('unknown', 'reschedule_window')]:
                request, source = case_data(kind)
                with self.subTest(key=key, kind=kind), self.assertRaises(provisioning.SyntheticPreparationFailureV1):
                    provisioning.prepare_synthetic_release(
                        provisioning.SyntheticCaseReleaseSpecV1('H', 'L', 'R', request, cj(source)),
                        parent=parent, clock=clock, execution=context(clock), factory_key=key)
                self.assertEqual(list(parent.iterdir()), [])
            request, source = candidate_case_data()
            exact = request.model_copy(update={'kind': 'reschedule_exact', 'consent_mode': 'exact_slot',
                                               'arguments': {'slot_id': 'J06-S3'}})
            with self.assertRaises(provisioning.SyntheticPreparationFailureV1):
                provisioning.prepare_synthetic_release(
                    provisioning.SyntheticCaseReleaseSpecV1('H', 'L', 'R', exact, cj(source)),
                    parent=parent, clock=clock, execution=context(clock), factory_key=KEY)
            self.assertEqual(list(parent.iterdir()), [])

    def test_prepared_mutations_retain_root_and_deny(self):
        for mutation in ['key', 'kind', 'version', 'resource_hash', 'source_pin', 'request']:
            with self.subTest(mutation=mutation), opened_candidate_case() as fx:
                prepared = fx.prepared
                if mutation == 'key':
                    object.__setattr__(prepared.binding, 'host_factory_key', 'fixed-synthetic-v1')
                elif mutation == 'kind':
                    object.__setattr__(prepared.host_release, 'admitted_request_kind', 'goods_refusal')
                elif mutation == 'version':
                    object.__setattr__(prepared.host_release, 'profile_version', 'v1.4')
                elif mutation == 'resource_hash':
                    object.__setattr__(prepared.host_release, 'profile_file_hash', '0' * 64)
                elif mutation == 'request':
                    request, _ = case_data('goods_refusal')
                    object.__setattr__(prepared, '_request_bytes', cj(request.model_dump(mode='json')))
                else:
                    pins = prepared.binding.implementation_pins
                    object.__setattr__(prepared.binding, 'implementation_pins', ((pins[0][0], '0' * 64), *pins[1:]))
                with self.assertRaises(provisioning.SyntheticPreparationFailureV1) as caught:
                    provisioning._revalidate_prepared(prepared, fx.clock, context(fx.clock))
                self.assertEqual(caught.exception.code, 'identity_changed')
                self.assertEqual(caught.exception.retained_root, prepared.root)
                self.assertTrue(prepared.root.is_dir())

    def test_closed_inventory_rejects_alias_missing_duplicate_extra_and_unsorted(self):
        with opened_candidate_case() as fx:
            binding = fx.prepared.binding
            pins = binding.implementation_pins
            for wrong in (pins[1:], (*pins, pins[-1]), tuple(reversed(pins)),
                          (('./' + pins[0][0], pins[0][1]), *pins[1:]),
                          (*pins, ('unregistered.py', '0' * 64))):
                with self.subTest(paths=tuple(p[0] for p in wrong[:2])), self.assertRaises(AdmissionCompositionFailure):
                    replace(binding, implementation_pins=wrong)

    def test_revalidation_rejects_malformed_original_as_identity_changed(self):
        with opened_candidate_case() as fx:
            changed = fx.request.model_dump(mode='json')
            changed['narrative'] = 'not a structured original'
            object.__setattr__(fx.prepared, '_request_bytes', cj(changed))
            with self.assertRaises(provisioning.SyntheticPreparationFailureV1) as caught:
                provisioning._revalidate_prepared(fx.prepared, fx.clock, context(fx.clock))
            self.assertEqual(caught.exception.code, 'identity_changed')
            self.assertEqual(caught.exception.retained_root, fx.prepared.root)

    def test_revalidation_rejects_changed_original_request_id_as_identity_changed(self):
        with opened_candidate_case() as fx:
            changed = fx.request.model_dump(mode='json')
            changed['request_id'] = 'J05-ALTERED-ORIGINAL'
            object.__setattr__(fx.prepared, '_request_bytes', cj(changed))
            with self.assertRaises(provisioning.SyntheticPreparationFailureV1) as caught:
                provisioning._revalidate_prepared(fx.prepared, fx.clock, context(fx.clock))
            self.assertEqual(caught.exception.code, 'identity_changed')
            self.assertEqual(caught.exception.retained_root, fx.prepared.root)
            self.assertTrue(fx.prepared.root.is_dir())

    def test_current_source_bytes_are_rechecked_at_both_boundaries(self):
        with opened_candidate_case() as fx:
            installed = provisioning._installed_bytes
            target = Path(provisioning.__file__).parent / 'gateway.py'
            def stale(path):
                return b'changed current source' if path == target else installed(path)
            with patch.object(provisioning, '_installed_bytes', stale), \
                    self.assertRaises(provisioning.SyntheticPreparationFailureV1) as caught:
                provisioning._revalidate_prepared(fx.prepared, fx.clock, context(fx.clock))
            self.assertEqual(caught.exception.code, 'identity_changed')
            self.assertTrue(fx.prepared.root.is_dir())
            fx.runtime.close()
            read = Path.read_bytes
            def stale_host(path):
                return b'changed current source' if path == target else read(path)
            with patch.object(Path, 'read_bytes', stale_host), self.assertRaises(AdmissionCompositionFailure) as caught:
                RuntimeFactory().create_registered(fx.prepared.host_release, fx.clock,
                    composition=fx.composition, execution=context(fx.clock))
            self.assertEqual(caught.exception.code, 'conflict')

    def test_composition_rejects_multiple_releases_and_profile_key_swaps(self):
        from test_release_route_foundation import rehash
        with opened_candidate_case() as fx:
            fx.runtime.close()
            composition = fx.composition
            first = composition.registry.resolve('J05-L').wire_bytes
            second = json.loads(first)
            second['release_id'] = 'J05-OTHER'
            second_raw = rehash(second)
            RegisteredReleaseV1(second_raw)
            original = composition.registry._releases
            object.__setattr__(composition.registry, '_releases', (('J05-L', first), ('J05-OTHER', second_raw)))
            with self.assertRaises(AdmissionCompositionFailure):
                RuntimeFactory().create_registered(fx.prepared.host_release, fx.clock,
                    composition=composition, execution=context(fx.clock))
            object.__setattr__(composition.registry, '_releases', original)
            for name, value in [('admitted_request_kind', 'goods_refusal'),
                                ('profile_hash', '0' * 64), ('profile_version', 'v1.4')]:
                wrong = replace(fx.prepared.host_release, **{name: value})
                with self.subTest(field=name), self.assertRaises(ValueError):
                    RuntimeFactory().create_registered(wrong, fx.clock,
                        composition=composition, execution=context(fx.clock))

    def test_initial_profile_substitution_is_rejected_before_allocation(self):
        original = provisioning._installed_bytes
        for raw in [b'{}', (Path(provisioning.__file__).parent / 'resources/profiles/flat-v1.3.json').read_bytes()]:
            with tempfile.TemporaryDirectory() as folder, paced_clock() as (clock, _):
                parent = Path(folder).resolve()
                parent.chmod(0o700)
                request, source = candidate_case_data()
                def substituted(path):
                    return raw if path.name == 'flat-window-readiness-v1.json' else original(path)
                with patch.object(provisioning, '_installed_bytes', substituted), \
                        self.assertRaises(provisioning.SyntheticPreparationFailureV1):
                    provisioning.prepare_synthetic_release(
                        provisioning.SyntheticCaseReleaseSpecV1('H', 'L', 'R', request, cj(source)),
                        parent=parent, clock=clock, execution=context(clock), factory_key=KEY)
                self.assertEqual(list(parent.iterdir()), [])

    def test_composition_rejects_equivalent_profile_with_uncommitted_resource_bytes(self):
        with opened_candidate_case() as fx:
            fx.runtime.close()
            profile_path = fx.prepared.host_release.profile_path
            raw = cj(load_profile('flat-window-readiness-v1').model_dump(mode='json'))
            profile_path.write_bytes(raw)
            release = replace(fx.prepared.host_release, profile_file_hash=sha256(raw).hexdigest())
            with self.assertRaises(AdmissionCompositionFailure):
                RuntimeFactory().create_registered(release, fx.clock,
                    composition=fx.composition, execution=context(fx.clock))

    def test_configured_cli_finalizes_and_keeps_all_controls_denied(self):
        with opened_candidate_case() as fx:
            fx.runtime.close()
            configuration = provisioning.configure_registered_cli(fx.prepared,
                approvals=fx.composition.approvals, review_id=fx.composition.review_id,
                auth_resolver=AuthResolver({'j05-user': fx.auth}), clock=fx.clock, execution=context(fx.clock),
                host_limits=HostLimitsV1(), interface_limits=InterfaceLimitsV1(),
                total_seconds=120.0, publication_reserve_seconds=10.0, shutdown_seconds=2.0)
            path = fx.parent / 'request.json'
            path.write_bytes(cj(fx.request.model_dump(mode='json')))
            def invoke(args):
                output = io.StringIO()
                with redirect_stdout(output):
                    code = main([*args, '--credential-ref', 'j05-user', '--release', 'J05-H'],
                                configuration=configuration)
                return code, CliReceiptV1.model_validate_json(output.getvalue())
            with measured_transports(fx.state, fx.clock) as calls:
                code, receipt = invoke(['run', '--input', str(path)])
            self.assertEqual(code, 0)
            self.assertTrue(receipt.shutdown.owner_closed)
            self.assertEqual(receipt.run.command.result.effects['reschedule'].status, 'verified')
            from proofkey.execution import ExecutionContext
            window = receipt.run.command.execution
            execution = ExecutionContext(window.deadline, window.captured_at,
                                         window.captured_monotonic, window.monotonic_deadline)
            resources = fx.prepared.host_release.resource_root
            with sqlite3.connect(resources / 'journal.sqlite') as db:
                checkpoint = json.loads(db.execute('SELECT checkpoint_json FROM cases').fetchone()[0])
            from proofkey.contracts import BudgetLedger
            self.assert_accounting(calls, resources / 'journal.sqlite', execution, fx.clock,
                                   BudgetLedger.model_validate(checkpoint['budget']), 'configured_cli')
            with sqlite3.connect(fx.prepared.control_parent / 'host-claims.sqlite') as db:
                claim_raw = db.execute('SELECT wire FROM claims').fetchone()[0]
                claim = json.loads(claim_raw)
            self.assertEqual(claim['state'], 'admission_observed')
            self.assertEqual(claim['request'], fx.request.model_dump(mode='json'))
            reopened = RuntimeFactory().create_registered(fx.prepared.host_release, fx.clock,
                composition=fx.composition, execution=context(fx.clock))
            try:
                source = reopened.world.capture_retained_state(execution=context(fx.clock), clock=fx.clock)
                journal = reopened.store.capture_retained_state(execution=context(fx.clock), clock=fx.clock)
                route = reopened.admission.route_for_case(fx.request.case_id, execution=context(fx.clock))
                self.assertEqual((claim['final_source_hash'], claim['final_journal_hash']),
                                 (source.content_hash, journal.content_hash))
                self.assertIn('provider:window-envelope-v1:', source.payload.decode())
                self.assertEqual(route.state, 'admission_observed')
                print('J05_FINALIZATION ' + json.dumps(dict(lane='configured_cli', state=claim['state'],
                    claim_id=claim['claim_id'], route_id=claim['route_id'], artifact_hash=claim['artifact_hash'],
                    final_source_hash=source.content_hash, final_journal_hash=journal.content_hash,
                    binding=claim['binding']), sort_keys=True))
                with self.assertRaises(AdmissionCompositionFailure):
                    reopened.stop_registered(fx.request.case_id, 'G1', fx.auth, execution=context(fx.clock))
            finally:
                reopened.close()
            reply = fx.parent / 'reply.json'
            reply.write_bytes(cj(dict(question_id='absent', binding=claim['binding'],
                actor_id=fx.auth.caller_id, proof_reference=fx.auth.proof_reference,
                request_revision='v1', consent_revision='v1', owner_state_revision='v1',
                fields={}, received_at=fx.clock.now().isoformat(), simulated=True)))
            for command in [['recover', '--case-id', fx.request.case_id],
                            ['stop', '--case-id', fx.request.case_id, '--generation', 'G1'],
                            ['reply', '--input', str(reply)], ['transfer']]:
                with self.subTest(command=command[0]):
                    code, denied = invoke(command)
                    self.assertEqual(code, 2)
                    self.assertIn(denied.run.command.outcome, ('denied', 'unavailable'))
            with sqlite3.connect(resources / 'world.sqlite') as db:
                self.assertEqual(db.execute('SELECT operation FROM effects').fetchall(), [('reschedule',)])
            with sqlite3.connect(fx.prepared.control_parent / 'host-claims.sqlite') as db:
                self.assertEqual(db.execute('SELECT wire FROM claims').fetchone()[0], claim_raw)

    def test_configured_cli_rejects_key_profile_kind_and_resource_swaps(self):
        with opened_candidate_case() as fx:
            fx.runtime.close()
            configuration = provisioning.configure_registered_cli(fx.prepared,
                approvals=fx.composition.approvals, review_id=fx.composition.review_id,
                auth_resolver=AuthResolver({'j05-user': fx.auth}), clock=fx.clock, execution=context(fx.clock),
                host_limits=HostLimitsV1(), interface_limits=InterfaceLimitsV1(),
                total_seconds=120.0, publication_reserve_seconds=10.0, shutdown_seconds=2.0)
            for field, value in [('profile_id', 'flat-v1.3'), ('admitted_request_kind', 'goods_refusal'),
                                 ('profile_file_hash', '0' * 64), ('resource_root', fx.prepared.control_parent)]:
                wrong = replace(fx.prepared.host_release, **{field: value})
                with self.subTest(field=field), self.assertRaises(ValueError):
                    replace(configuration, profile_registry=ProfileRegistry((wrong,)))
            object.__setattr__(fx.prepared.binding, 'host_factory_key', 'fixed-synthetic-observed-stop-v2')
            with self.assertRaises(ValueError):
                replace(configuration)

    def test_wrong_auth_creates_no_business_effects_but_retains_audit(self):
        for auth in [AuthContext(caller_id='wrong', proof_reference='j06-synthetic-proof'),
                     AuthContext(caller_id='J06-USER-WINDOW', proof_reference='wrong')]:
            with self.subTest(auth=auth.caller_id), opened_candidate_case() as fx:
                result = fx.runtime.run_registered(fx.request, auth, execution=context(fx.clock, seconds=120))
                self.assertNotEqual(result.status, 'authorized')
                self.assertEqual(fx.runtime.world.effect_count('reschedule'), 0)
                self.assertIsNotNone(fx.runtime.admission.claim_for_case(fx.request.case_id, execution=context(fx.clock)))
                self.assertGreater(fx.runtime.store._db.execute('SELECT COUNT(*) FROM admission_attempts').fetchone()[0], 0)

    def test_revoked_source_acl_creates_no_business_effects(self):
        request, source = candidate_case_data()
        source['scopes'][0]['readers'] = {'other-actor': 'other-proof'}
        with patch('support_window_readiness.candidate_case_data', return_value=(request, source)), \
                opened_candidate_case() as fx:
            result = fx.runtime.run_registered(fx.request, fx.auth, execution=context(fx.clock, seconds=120))
            self.assertNotEqual(result.status, 'authorized')
            self.assertEqual(fx.runtime.world.effect_count('reschedule'), 0)
            self.assertIsNotNone(fx.runtime.admission.claim_for_case(fx.request.case_id, execution=context(fx.clock)))
            self.assertGreater(fx.runtime.store._db.execute('SELECT COUNT(*) FROM admission_attempts').fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
