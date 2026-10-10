"""Closed v2 provisioning contract; control behavior is tested separately."""
import base64
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from datetime import timedelta
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor

import proofkey
from proofkey import host_admission
from proofkey.host import RuntimeFactory
from proofkey.host_admission import FIXED_IMPLEMENTATION_PATHS
from proofkey.host_admission import AdmissionCompositionFailure, _ClaimStore
from proofkey.admission_routes import AdmissionRouteStoreV1
from proofkey.journal import CaseStore
from proofkey.contracts import ScopedReply
from proofkey.clock import SyntheticReplayClock
from proofkey.host import AuthResolver, HostDispatcher, ProfileRegistry
from proofkey.host_contracts import RunCommandV1, StopCommandV1, RecoverCommandV1, ReplyCommandV1, HostLimitsV1
from proofkey.host_writer import RuntimeWriterLease, RuntimeWriterFailure
from proofkey.synthetic_provisioning import (
    SyntheticCaseReleaseSpecV1, SyntheticPreparationFailureV1, prepare_synthetic_release)
from support_observed_stop_v2 import prepared_case, opened_case, snapshot_rows, assert_budget_continuity
from support_synthetic_provisioning import case_data, cj, context
from test_host_admission import paced_clock


class ObservedStopV2InventoryTests(unittest.TestCase):
    def test_new_factory_uses_exact_existing_schema(self):
        with prepared_case() as fx:
            value = json.loads(fx.prepared.registry.resolve('J07-L').wire_bytes)
            dependency = json.loads(base64.b64decode(value['blobs']['dependency']['base64']))
            self.assertEqual(value['version'], 1)
            self.assertEqual(value['factory']['factory_id'], 'fixed-synthetic-observed-stop-v2')
            self.assertEqual(fx.prepared.binding.host_factory_key, 'fixed-synthetic-observed-stop-v2')
            self.assertEqual(dependency['completeness'], 'unestablished')
            observed = tuple(item['name'] for item in dependency['entries'])
            self.assertEqual(observed, host_admission.OBSERVED_STOP_V2_IMPLEMENTATION_PATHS)
            self.assertIn('clock.py', observed)
            self.assertIn('waits.py', observed)
            self.assertIn('execution_trace.py', observed)
            self.assertEqual([(e['name'], e['sha256']) for e in dependency['entries']],
                [(e['name'], e['sha256']) for e in value['implementations']])
            self.assertEqual({e['name']: e['role'] for e in dependency['entries']},
                {name: 'data' if name == 'schema.sql' else 'code' for name in observed})
            for item in value['implementations']:
                self.assertEqual(sha256(base64.b64decode(item['base64'])).hexdigest(), item['sha256'])

    def test_factory_and_inventory_cannot_be_mixed(self):
        with prepared_case() as fx:
            binding = fx.prepared.binding
            pins = binding.implementation_pins
            old_pins = tuple(pair for pair in pins if pair[0] in FIXED_IMPLEMENTATION_PATHS)
            for update in (
                {'implementation_pins': old_pins},
                {'implementation_pins': tuple(reversed(pins))},
                {'implementation_pins': pins[:-1]},
                {'implementation_pins': pins + (pins[-1],)},
                {'factory_id': 'unknown', 'host_factory_key': 'unknown'},
                {'host_factory_key': 'fixed-synthetic-v1'},
            ):
                with self.subTest(update=update), self.assertRaises(ValueError):
                    replace(binding, **update)

    def test_default_preparation_preserves_v1_factory_and_inventory(self):
        with TemporaryDirectory() as folder, paced_clock() as (clock, _):
            parent = Path(folder).resolve()
            parent.chmod(0o700)
            request, source = case_data()
            prepared = prepare_synthetic_release(
                SyntheticCaseReleaseSpecV1('J07-H', 'J07-L', 'J07-R', request, cj(source)),
                parent=parent, clock=clock, execution=context(clock))
            self.assertEqual(prepared.binding.factory_id, 'fixed-synthetic-v1')
            self.assertEqual(prepared.binding.host_factory_key, 'fixed-synthetic-v1')
            self.assertEqual(tuple(name for name, _ in prepared.binding.implementation_pins),
                             FIXED_IMPLEMENTATION_PATHS)

    def test_binding_rejects_nonexact_factory_key_types(self):
        class EqualKey:
            def __eq__(self, other):
                return other == 'fixed-synthetic-observed-stop-v2'

        class StringKey(str):
            def __eq__(self, other):
                return str(self) == other

        with prepared_case() as fx:
            for key in (EqualKey(), StringKey('fixed-synthetic-observed-stop-v2')):
                with self.subTest(key_type=type(key).__name__):
                    with self.assertRaises(host_admission.AdmissionCompositionFailure) as caught:
                        replace(fx.prepared.binding, host_factory_key=key)
                    self.assertEqual(caught.exception.code, 'unsupported_release')

    def test_unknown_factory_rejected_before_child_allocation(self):
        with TemporaryDirectory() as folder, paced_clock() as (clock, _):
            parent = Path(folder).resolve()
            parent.chmod(0o700)
            request, source = case_data()
            spec = SyntheticCaseReleaseSpecV1('J07-H', 'J07-L', 'J07-R', request, cj(source))
            with self.assertRaises(SyntheticPreparationFailureV1) as caught:
                prepare_synthetic_release(spec, parent=parent, clock=clock,
                    execution=context(clock), factory_key='unknown')
            self.assertEqual(caught.exception.code, 'invalid_input')
            self.assertEqual(tuple(parent.iterdir()), ())

    def test_reviewed_v2_inventory_covers_all_first_party_source(self):
        package = Path(proofkey.__file__).parent
        installed = {path.relative_to(package).as_posix()
                     for path in package.rglob('*.py')}
        installed.add('schema.sql')
        names = host_admission.OBSERVED_STOP_V2_IMPLEMENTATION_PATHS
        self.assertEqual(set(names), installed)
        self.assertEqual(names, tuple(sorted(set(names))))

    def test_v2_preparation_opens_with_its_exact_pins(self):
        with prepared_case() as fx:
            resources = RuntimeFactory().create_registered(fx.prepared.host_release,
                fx.clock, composition=fx.composition, execution=context(fx.clock))
            try:
                self.assertFalse(resources.closed)
            finally:
                resources.close()
            self.assertTrue(resources.closed)


def captured_view(fx, snapshot=None):
    r, clock = fx.runtime, fx.clock
    if snapshot is None:
        snapshot = r.store.capture_retained_state(execution=context(clock), clock=clock)
    claim = r.admission.claim_for_case(fx.request.case_id, execution=context(clock))
    route = r.admission.route_for_case(fx.request.case_id, execution=context(clock))
    return snapshot, host_admission._stop_view(snapshot, fx.request.case_id,
        claim.binding.generation, context(clock), clock, claim=claim, route=route)


def changed_inner(snapshot, table_name, column, update):
    image = json.loads(snapshot.payload)
    table = next(item for item in image['tables'] if item['name'] == table_name)
    index = table['columns'].index(column)
    assert len(table['rows']) == 1
    value = json.loads(table['rows'][0][index])
    update(value)
    table['rows'][0][index] = json.dumps(value)
    payload = cj(image)
    return replace(snapshot, payload=payload, content_hash=sha256(payload).hexdigest())


class ObservedStopV2ControlTests(unittest.TestCase):
    def run_case(self, fx):
        return fx.runtime.run_registered(fx.request, fx.auth, execution=context(fx.clock, 120))

    def stop(self, fx):
        return fx.runtime.stop_registered(fx.request.case_id, 'G1', fx.auth,
            execution=context(fx.clock))

    def test_same_owner_stop_preserves_original_and_charges_existing_case(self):
        with opened_case() as fx:
            r = fx.runtime
            first = self.run_case(fx)
            key = (fx.request.case_id, first.binding.generation)
            before = r.store.checkpoint(key[0])
            original, saved = r.store.original_request(*key), r.store.saved_result(*key)
            claim = r.admission.claim_for_case(key[0], execution=context(fx.clock))
            route = r.admission.route_for_case(key[0], execution=context(fx.clock))
            attempts = snapshot_rows(r, fx.clock)['admission_attempts']
            effect_count, calls = r.world.effect_count('reschedule'), len(r.world.calls)
            result = self.stop(fx)
            after = r.store.checkpoint(key[0])
            self.assertTrue(result.stop.requested)
            self.assertEqual(after.binding, before.binding)
            self.assertEqual(r.store.original_request(*key), original)
            self.assertEqual(r.store.saved_result(*key), saved)
            self.assertEqual(r.admission.claim_for_case(key[0], execution=context(fx.clock)), claim)
            self.assertEqual(r.admission.route_for_case(key[0], execution=context(fx.clock)), route)
            self.assertEqual(snapshot_rows(r, fx.clock)['admission_attempts'], attempts)
            self.assertEqual(r.world.effect_count('reschedule'), effect_count)
            self.assertEqual([c.operation for c in r.world.calls[calls:]], ['read_case'])
            self.assertLessEqual(after.deadline, before.deadline)
            self.assertGreater(after.budget.tool_calls, before.budget.tool_calls)
            assert_budget_continuity(self, before.budget, after.budget)

    def test_v1_and_direct_engine_controls_stay_denied(self):
        for factory in ('fixed-synthetic-v1', 'fixed-synthetic-observed-stop-v2'):
            with self.subTest(factory=factory), opened_case(factory) as fx:
                r = fx.runtime
                self.run_case(fx)
                calls = len(r.world.calls)
                self.assertEqual(r.engine.stop(fx.request.case_id, 'G1', fx.auth,
                    execution=context(fx.clock)).status, 'denied')
                self.assertEqual(r.engine.recover(fx.request.case_id, fx.auth,
                    execution=context(fx.clock)).status, 'denied')
                if factory == 'fixed-synthetic-v1':
                    with self.assertRaises(AdmissionCompositionFailure): self.stop(fx)
                self.assertEqual(len(r.world.calls), calls)

    def test_wrong_target_and_auth_deny_before_read(self):
        for kind in ('case', 'generation', 'caller', 'proof'):
            with self.subTest(kind=kind), opened_case() as fx:
                self.run_case(fx)
                r = fx.runtime
                before, calls = snapshot_rows(r, fx.clock), len(r.world.calls)
                case, generation, auth = fx.request.case_id, 'G1', fx.auth
                if kind == 'case': case = 'foreign'
                if kind == 'generation': generation = 'foreign'
                if kind == 'caller': auth = auth.model_copy(update={'caller_id': 'foreign'})
                if kind == 'proof': auth = auth.model_copy(update={'proof_reference': 'wrong'})
                with self.assertRaises(AdmissionCompositionFailure):
                    r.stop_registered(case, generation, auth, execution=context(fx.clock))
                self.assertEqual(len(r.world.calls), calls)
                self.assertEqual(snapshot_rows(r, fx.clock), before)

    def test_revoked_current_source_is_denied_but_read_is_charged(self):
        with opened_case() as fx:
            self.run_case(fx)
            r = fx.runtime
            before = r.store.checkpoint(fx.request.case_id)
            calls = len(r.world.calls)
            r.world.mutate('case.authorization', 'revoked')
            self.assertEqual(self.stop(fx).status, 'denied')
            after = r.store.checkpoint(fx.request.case_id)
            self.assertFalse(after.stop.requested)
            self.assertGreater(after.budget.tool_calls, before.budget.tool_calls)
            self.assertEqual([c.operation for c in r.world.calls[calls:]], ['read_case'])
            assert_budget_continuity(self, before.budget, after.budget)

    def test_final_claim_write_failure_never_mints_receipt(self):
        with opened_case() as fx:
            actual = _ClaimStore.write
            def fail(store, value, execution, **kwargs):
                if value['state'] == 'admission_observed':
                    raise AdmissionCompositionFailure('storage')
                return actual(store, value, execution, **kwargs)
            with patch.object(_ClaimStore, 'write', fail):
                with self.assertRaises(AdmissionCompositionFailure): self.run_case(fx)
            r = fx.runtime
            self.assertEqual(r.admission.claim_for_case(fx.request.case_id,
                execution=context(fx.clock)).state, 'binding_sealed')
            self.assertEqual(r.admission.route_for_case(fx.request.case_id,
                execution=context(fx.clock)).state, 'admission_observed')
            calls = len(r.world.calls)
            with self.assertRaises(AdmissionCompositionFailure): self.stop(fx)
            self.assertEqual(len(r.world.calls), calls)

    def test_reopened_owner_has_no_live_receipt(self):
        with opened_case() as fx:
            self.run_case(fx)
            fx.runtime.close()
            fx.runtime = RuntimeFactory().create_registered(fx.prepared.host_release,
                fx.clock, composition=fx.composition, execution=context(fx.clock))
            calls = len(fx.runtime.world.calls)
            with self.assertRaises(AdmissionCompositionFailure): self.stop(fx)
            self.assertEqual(len(fx.runtime.world.calls), calls)

    def test_post_commit_interruption_keeps_stop_and_wait_fence(self):
        class Interrupted(BaseException): pass
        with opened_case(missing=True) as fx:
            self.run_case(fx)
            r = fx.runtime
            question = r.store.checkpoint(fx.request.case_id).question_id
            self.assertIsNotNone(question)
            before = r.store.load_wait_record(question)
            actual = CaseStore.stop_waits_atomic
            def interrupt(store, binding, expected):
                actual(store, binding, expected)
                raise Interrupted()
            with patch.object(CaseStore, 'stop_waits_atomic', interrupt):
                with self.assertRaises(Interrupted): self.stop(fx)
            after = r.store.load_wait_record(question)
            self.assertTrue(r.store.checkpoint(fx.request.case_id).stop.requested)
            self.assertEqual(after.lifecycle, 'stopped')
            self.assertEqual(after.model_dump(exclude={'lifecycle', 'successor_hash'}),
                before.model_dump(exclude={'lifecycle', 'successor_hash'}))
            self.assertEqual(after.wait.expires_at, before.wait.expires_at)
            self.assertEqual(after.wait.budget.deadline, before.wait.budget.deadline)
            self.assertEqual(after.origin_checkpoint, before.origin_checkpoint)
            self.assertIsNone(r.admission.active)
            self.assertEqual(r.world.effect_count('reschedule'), 0)
            self.assertTrue(self.stop(fx).stop.requested)
            self.assertEqual(r.store.load_wait_record(question), after)

    def test_real_noncanonical_inner_strings_parse_and_exact_attempt_joins(self):
        with opened_case(missing=True) as fx:
            self.run_case(fx)
            snapshot, view = captured_view(fx)
            image = json.loads(snapshot.payload)
            strings = [row[i] for table in image['tables']
                for i, column in enumerate(table['columns']) if column.endswith('_json')
                for row in table['rows'] if isinstance(row[i], str)]
            self.assertTrue(any(raw.encode() != cj(json.loads(raw)) for raw in strings))
            claim = fx.runtime.admission.claim_for_case(fx.request.case_id, execution=context(fx.clock))
            self.assertNotEqual(claim.claim_id, claim.attempt_id)
            self.assertEqual(view.binding, claim.binding)
            for field, bad in (('claimed_principal_id', 'foreign'), ('proof_digest', '0' * 64),
                              ('request_hash', '0' * 64), ('attempt_id', claim.claim_id)):
                altered = changed_inner(snapshot, 'admission_attempts', 'attempt_json',
                    lambda value, field=field, bad=bad: value.__setitem__(field, bad))
                with self.subTest(field=field), self.assertRaises(AdmissionCompositionFailure):
                    captured_view(fx, altered)

    def test_inner_json_rejects_duplicates_nonfinite_and_oversized_strings(self):
        for raw in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":1e999}', '{"a":"' + 'x' * 262144 + '"}'):
            with self.subTest(prefix=raw[:30]), self.assertRaises(ValueError):
                host_admission._inner_json(raw)

    def test_wait_expiry_context_and_observed_stop_fences_cannot_regress(self):
        with opened_case(missing=True) as fx:
            self.run_case(fx)
            snapshot, before = captured_view(fx)
            question = fx.runtime.store.checkpoint(fx.request.case_id).question_id
            record = fx.runtime.store.load_wait_record(question)
            def shorten(value):
                reduced = record.wait.model_copy(update={'expires_at': record.wait.expires_at - timedelta(seconds=1)})
                value['wait']['expires_at'] = reduced.model_dump(mode='json')['expires_at']
            _, changed = captured_view(fx, changed_inner(snapshot, 'waits', 'wait_json', shorten))
            with self.assertRaises(AdmissionCompositionFailure):
                host_admission._check_stop_continuity(before, changed)
            self.stop(fx)
            _, stopped = captured_view(fx)
            host_admission._check_stop_continuity(before, stopped)
            for regressed in (replace(stopped, request_stopped=False),
                replace(stopped, checkpoint=stopped.checkpoint.model_copy(update={
                    'stop': stopped.checkpoint.stop.model_copy(update={'requested': False})})),
                replace(stopped, wait_states=((question, 'pending', None),))):
                with self.assertRaises(AdmissionCompositionFailure):
                    host_admission._check_stop_continuity(stopped, regressed)

    def test_one_five_second_window_covers_claim_and_route_preflight(self):
        with opened_case() as fx:
            self.run_case(fx)
            find, get = _ClaimStore.find, AdmissionRouteStoreV1.get
            def slow_find(*args, **kwargs):
                result = find(*args, **kwargs)
                fx.state['tick'] += 3.0
                return result
            def slow_get(*args, **kwargs):
                result = get(*args, **kwargs)
                fx.state['tick'] += 3.0
                return result
            calls = len(fx.runtime.world.calls)
            with patch.object(_ClaimStore, 'find', slow_find), patch.object(AdmissionRouteStoreV1, 'get', slow_get):
                with self.assertRaises(AdmissionCompositionFailure): self.stop(fx)
            self.assertEqual(len(fx.runtime.world.calls), calls)

    def test_aliases_cross_thread_marker_and_closed_owner_deny(self):
        with opened_case() as fx:
            self.run_case(fx)
            r = fx.runtime
            calls = len(r.world.calls)
            for field in ('engine', 'store', 'world'):
                original = getattr(r, field)
                try:
                    setattr(r, field, object())
                    with self.subTest(field=field), self.assertRaises(AdmissionCompositionFailure): self.stop(fx)
                finally: setattr(r, field, original)
            with ThreadPoolExecutor(max_workers=1) as executor:
                with self.assertRaises(AdmissionCompositionFailure):
                    executor.submit(r.stop_registered, fx.request.case_id, 'G1', fx.auth,
                        execution=context(fx.clock)).result()
            marker = fx.prepared.host_release.resource_root / '.proofkey-registration.json'
            original = marker.read_bytes()
            try:
                marker.write_bytes(b'{}')
                with self.assertRaises(AdmissionCompositionFailure): self.stop(fx)
            finally: marker.write_bytes(original)
            self.assertEqual(len(r.world.calls), calls)
            r.close()
            with self.assertRaises(AdmissionCompositionFailure): self.stop(fx)

    def test_clock_alias_backward_nonfinite_and_expired_context_deny(self):
        with opened_case() as fx:
            self.run_case(fx)
            r, owner = fx.runtime, fx.runtime.admission
            calls = len(r.world.calls)
            replacement = SyntheticReplayClock()
            for target in (owner, r.engine, r.engine.gateway):
                target.clock = replacement
            try:
                with self.assertRaises(AdmissionCompositionFailure): self.stop(fx)
            finally:
                for target in (owner, r.engine, r.engine.gateway):
                    target.clock = fx.clock
            for tick, offset in ((fx.state['tick'] - 1, 0), (fx.state['tick'], -1), (float('nan'), 0)):
                execution = context(fx.clock)
                old = dict(fx.state)
                try:
                    fx.state.update(tick=tick, utc_offset=offset)
                    with self.assertRaises(AdmissionCompositionFailure):
                        r.stop_registered(fx.request.case_id, 'G1', fx.auth, execution=execution)
                finally: fx.state.update(old)
            for seconds in (0, -1):
                with self.assertRaises(AdmissionCompositionFailure):
                    r.stop_registered(fx.request.case_id, 'G1', fx.auth, execution=context(fx.clock, seconds))
            execution = context(fx.clock)
            object.__setattr__(execution, 'monotonic_deadline', execution.monotonic_deadline + 1)
            with self.assertRaises(AdmissionCompositionFailure):
                r.stop_registered(fx.request.case_id, 'G1', fx.auth, execution=execution)
            self.assertEqual(len(r.world.calls), calls)
            with self.assertRaises(RuntimeWriterFailure):
                RuntimeWriterLease(fx.prepared.host_release.resource_root)

    def test_two_fresh_windows_preserve_business_deadline_then_expiry_denies(self):
        with opened_case() as fx:
            self.run_case(fx)
            r = fx.runtime
            original = r.store.checkpoint(fx.request.case_id)
            claim = r.admission.claim_for_case(fx.request.case_id, execution=context(fx.clock))
            self.assertTrue(self.stop(fx).stop.requested)
            fx.state['tick'] += 6
            self.assertTrue(self.stop(fx).stop.requested)
            self.assertEqual(r.admission.claim_for_case(fx.request.case_id, execution=context(fx.clock)), claim)
            self.assertEqual(r.store.checkpoint(fx.request.case_id).deadline, original.deadline)
            fx.state['tick'] += (original.deadline - fx.clock.now()).total_seconds() + 1
            calls = len(r.world.calls)
            result = self.stop(fx)
            self.assertEqual(result.status, 'denied')
            self.assertEqual(len(r.world.calls), calls)
            self.assertEqual(r.store.checkpoint(fx.request.case_id).deadline, original.deadline)

    def test_active_stop_token_denies_other_operations_reentry_and_mutation(self):
        import pickle
        with opened_case(missing=True) as fx:
            self.run_case(fx)
            r = fx.runtime
            wait = r.store.load_wait_record(r.store.checkpoint(fx.request.case_id).question_id).wait
            reply = ScopedReply(question_id=wait.question_id, binding=wait.binding,
                actor_id=wait.recipient, proof_reference=fx.auth.proof_reference,
                request_revision=wait.binding.request_revision, consent_revision=wait.binding.consent_revision,
                owner_state_revision=wait.owner_state_revision, fields={'complete': True},
                received_at=fx.clock.now(), simulated=True)
            actual = type(r.engine).stop
            observed = []
            def inspect(engine, case, generation, auth, *, execution):
                calls = len(r.world.calls)
                token = r.admission.active
                self.assertIsNotNone(token, 'registered stop must install its private live capability')
                observed.append(type(token).__name__)
                for obj in (token, token.receipt):
                    with self.assertRaises(TypeError): pickle.dumps(obj)
                for tag in (None, 'run', 'recover', 'reply'):
                    with self.assertRaises(AdmissionCompositionFailure):
                        r.admission.guard_execution(execution, r.engine.gateway, entry_kind=tag)
                self.assertEqual(engine.run(fx.request, auth, execution=execution).status, 'denied')
                self.assertEqual(engine.recover(case, auth, execution=execution).status, 'denied')
                self.assertEqual(engine.reply(reply, auth, execution=execution).status, 'denied')
                with self.assertRaises(AdmissionCompositionFailure):
                    r.admission.require_entry(fx.request, auth)
                with self.assertRaises(AdmissionCompositionFailure): self.stop(fx)
                deadline = execution.deadline
                object.__setattr__(execution, 'deadline', deadline + timedelta(seconds=1))
                try:
                    self.assertEqual(actual(engine, case, generation, auth, execution=execution).status, 'denied')
                finally: object.__setattr__(execution, 'deadline', deadline)
                self.assertEqual(len(r.world.calls), calls)
                return actual(engine, case, generation, auth, execution=execution)
            with patch.object(type(r.engine), 'stop', inspect):
                self.assertTrue(self.stop(fx).stop.requested)
            self.assertEqual(observed, ['_ObservedStopV2'])
            self.assertIsNone(r.admission.active)

    def test_registered_host_stop_and_closed_other_controls(self):
        with prepared_case(missing=True) as fx:
            release = fx.prepared.host_release
            resolver = AuthResolver({'user': fx.auth})
            host = HostDispatcher(RuntimeFactory(), resolver, ProfileRegistry((release,)), fx.clock,
                fx.prepared.inventory_parent / 'host', HostLimitsV1(), release_id='J07-H',
                admission_composition=fx.composition)
            waits = []
            actual = CaseStore.create_wait_atomic
            def capture(store, record, now):
                result = actual(store, record, now)
                waits.append(record.wait)
                return result
            try:
                with patch.object(CaseStore, 'create_wait_atomic', capture):
                    first = host.submit(RunCommandV1(release_id='J07-H', request=fx.request),
                        resolver.handle('user'), context(fx.clock, 120))
                self.assertEqual(first.outcome, 'result')
                self.assertEqual(len(waits), 1)
                wait = waits[0]
                reply = ScopedReply(question_id=wait.question_id, binding=wait.binding,
                    actor_id=wait.recipient, proof_reference=fx.auth.proof_reference,
                    request_revision=wait.binding.request_revision, consent_revision=wait.binding.consent_revision,
                    owner_state_revision=wait.owner_state_revision, fields={'complete': True},
                    received_at=fx.clock.now(), simulated=True)
                for command in (RecoverCommandV1(release_id='J07-H', case_id=fx.request.case_id),
                                ReplyCommandV1(release_id='J07-H', reply=reply)):
                    self.assertEqual(host.submit(command, resolver.handle('user'), context(fx.clock)).outcome, 'denied')
                stopped = host.submit(StopCommandV1(release_id='J07-H', case_id=fx.request.case_id, generation='G1'),
                    resolver.handle('user'), context(fx.clock))
                self.assertEqual(stopped.outcome, 'result')
                self.assertTrue(stopped.result.stop.requested)
            finally:
                self.assertTrue(host.close(fx.clock.now() + timedelta(seconds=3)).owner_closed)

    def test_stop_first_never_constructs_runtime(self):
        with prepared_case() as fx:
            resolver = AuthResolver({'user': fx.auth})
            host = HostDispatcher(RuntimeFactory(), resolver, ProfileRegistry((fx.prepared.host_release,)), fx.clock,
                fx.prepared.inventory_parent / 'host', HostLimitsV1(), release_id='J07-H',
                admission_composition=fx.composition)
            try:
                with patch.object(RuntimeFactory, 'create_registered', side_effect=AssertionError('stop opened runtime')):
                    stopped = host.submit(StopCommandV1(release_id='J07-H', case_id=fx.request.case_id, generation='G1'),
                        resolver.handle('user'), context(fx.clock))
                self.assertEqual(stopped.outcome, 'denied')
                self.assertFalse((fx.prepared.host_release.resource_root / 'journal.sqlite').exists())
            finally:
                self.assertTrue(host.close(fx.clock.now() + timedelta(seconds=3)).owner_closed)

    def test_interrupted_preparation_reservation_and_seal_do_not_qualify(self):
        for stage in ('prepared', 'reserved', 'binding_sealed'):
            with self.subTest(stage=stage), opened_case() as fx:
                write, reserve = _ClaimStore.write, AdmissionRouteStoreV1.reserve
                def interrupted_write(store, value, execution, **kwargs):
                    result = write(store, value, execution, **kwargs)
                    if value['state'] == stage:
                        raise AdmissionCompositionFailure('storage')
                    return result
                def interrupted_reserve(*args, **kwargs):
                    result = reserve(*args, **kwargs)
                    if stage == 'reserved':
                        raise AdmissionCompositionFailure('storage')
                    return result
                with patch.object(_ClaimStore, 'write', interrupted_write), \
                        patch.object(AdmissionRouteStoreV1, 'reserve', interrupted_reserve):
                    try:
                        result = self.run_case(fx)
                    except AdmissionCompositionFailure:
                        pass
                    else:
                        self.assertEqual(result.status, 'denied')
                self.assertFalse(fx.runtime.admission._stop_receipts)
                calls = len(fx.runtime.world.calls)
                with self.assertRaises(AdmissionCompositionFailure): self.stop(fx)
                self.assertEqual(len(fx.runtime.world.calls), calls)

    def test_final_observation_time_failure_does_not_mint_receipt(self):
        with opened_case() as fx:
            write = _ClaimStore.write
            def late_write(store, value, execution, **kwargs):
                result = write(store, value, execution, **kwargs)
                if value['state'] == 'admission_observed':
                    fx.state['tick'] += 121
                return result
            with patch.object(_ClaimStore, 'write', late_write):
                with self.assertRaises(AdmissionCompositionFailure): self.run_case(fx)
            self.assertFalse(fx.runtime.admission._stop_receipts)
            self.assertEqual(fx.runtime.admission.claim_for_case(fx.request.case_id,
                execution=context(fx.clock)).state, 'admission_observed')
            calls = len(fx.runtime.world.calls)
            with self.assertRaises(AdmissionCompositionFailure): self.stop(fx)
            self.assertEqual(len(fx.runtime.world.calls), calls)

    def test_post_commit_timeout_preserves_fence_without_renewed_capture(self):
        with opened_case(missing=True) as fx:
            self.run_case(fx)
            r = fx.runtime
            question = r.store.checkpoint(fx.request.case_id).question_id
            original_wait = r.store.load_wait_record(question)
            stop, capture = CaseStore.stop_waits_atomic, CaseStore.capture_retained_state
            windows = []
            def counted_capture(store, **kwargs):
                windows.append(kwargs['execution'])
                return capture(store, **kwargs)
            def late_stop(store, *args):
                result = stop(store, *args)
                fx.state['tick'] += 6
                return result
            with patch.object(CaseStore, 'stop_waits_atomic', late_stop), \
                    patch.object(CaseStore, 'capture_retained_state', counted_capture):
                with self.assertRaises(AdmissionCompositionFailure): self.stop(fx)
            self.assertEqual(len(windows), 1)
            self.assertIsNone(r.admission.active)
            self.assertTrue(r.store.checkpoint(fx.request.case_id).stop.requested)
            stopped = r.store.load_wait_record(question)
            self.assertEqual(stopped.lifecycle, 'stopped')
            self.assertEqual(stopped.wait, original_wait.wait)
            self.assertEqual(stopped.origin_checkpoint, original_wait.origin_checkpoint)
            self.assertTrue(self.stop(fx).stop.requested)
            self.assertEqual(r.world.effect_count('reschedule'), 0)

    def test_journal_preflight_time_is_part_of_the_same_window(self):
        with opened_case() as fx:
            self.run_case(fx)
            capture = CaseStore.capture_retained_state
            def late_capture(*args, **kwargs):
                result = capture(*args, **kwargs)
                fx.state['tick'] += 5
                return result
            calls = len(fx.runtime.world.calls)
            with patch.object(CaseStore, 'capture_retained_state', late_capture):
                with self.assertRaises(AdmissionCompositionFailure): self.stop(fx)
            self.assertEqual(len(fx.runtime.world.calls), calls)
            self.assertFalse(fx.runtime.store.checkpoint(fx.request.case_id).stop.requested)

    def test_budget_floor_rejects_debt_drop_and_changed_allowances(self):
        with opened_case() as fx:
            self.run_case(fx)
            _, before = captured_view(fx)
            budget = before.checkpoint.budget
            self.assertGreater(budget.tool_calls, 0)
            for changes in ({'tool_calls': budget.tool_calls - 1},
                            {'max_tool_calls': budget.max_tool_calls + 1},
                            {'deadline': budget.deadline + timedelta(seconds=1)}):
                after = replace(before, checkpoint=before.checkpoint.model_copy(update={
                    'budget': budget.model_copy(update=changes)}))
                with self.subTest(changes=changes), self.assertRaises(AdmissionCompositionFailure):
                    host_admission._check_stop_continuity(before, after)


if __name__ == '__main__':
    unittest.main()
