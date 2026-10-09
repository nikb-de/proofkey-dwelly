from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from proofkey.contracts import BudgetLedger, RoleAllowance
from proofkey.execution import ExecutionContext
from proofkey.gateway import ActionGateway
from proofkey.journal import CaseStore, JournalFailure
from proofkey.budget import BudgetExceeded
from proofkey.policy import GateDenied
from proofkey.providers.invocations import InvocationService
from support import (DEADLINE, FakeClock, build_test_runtime, make_binding,
                     make_checkpoint, make_fixture_campaign,
                     make_processing_receipt, make_processor_identity,
                     make_request)


class ParentClock:
    """Task-local trusted synthetic clock; no wall-clock sleep."""
    def __init__(self, utc_clock):
        self.utc_clock = utc_clock
        self.seconds = 0.0

    def now(self):
        return self.utc_clock.now()

    def monotonic(self):
        return self.seconds

    def advance(self, seconds, *, utc=True):
        self.seconds += seconds
        if utc:
            self.utc_clock.advance(seconds)

    def wait(self, seconds):
        self.advance(seconds)


class ProcessingParentScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        # Existing support creates isolated synthetic world/store resources.
        # It does not admit/run the engine or invoke a processing provider.
        self.fx = build_test_runtime(self.root,
            request=make_request(narrative="Synthetic parent accounting fixture"))
        self.store = self.fx.store
        self.addCleanup(self.store.close)
        self.clock = ParentClock(self.fx.clock)
        self.binding = make_binding(self.fx.request)
        self.gateway = ActionGateway(self.fx.profile, self.fx.world.bundle(),
            self.store, self.clock, auth=self.fx.auth)
        # Public direct admission is intentional for a parent-service boundary
        # test; it is not evidence of engine recipe/content integration.
        budget = BudgetLedger(case_id="C1", deadline=DEADLINE,
            max_planner_calls=3,
            role_allowances={"planning": RoleAllowance(max_invocations=3,
                max_cost=3.0, usage_allowances={"tokens": 30.0})})
        self.store.admit(self.binding, self.fx.request,
            make_checkpoint(binding=self.binding, phase="intake", next_gate="intake",
                profile_version=self.fx.profile.version,
                process_version=self.fx.profile.processes[self.fx.request.kind].version,
                budget=budget))
        self.grant = make_fixture_campaign(role="planning")
        self.store.register_campaign(self.grant)  # explicit synthetic registration
        cp = self.store.checkpoint("C1")
        self.identity = make_processor_identity(role="planning",
            generation=cp.binding.generation, campaign_id=self.grant.campaign_id,
            permit_hash=self.grant.permit_hash, input_hashes=self.grant.input_hashes,
            provider=self.grant.provider, model=self.grant.model,
            endpoint=self.grant.endpoint, profile_version=cp.profile_version,
            process_version=cp.process_version, deadline=cp.deadline)
        self.ids, self.callbacks = [], []
        for target in ("socket.socket.connect", "socket.socket.connect_ex",
                       "socket.create_connection"):
            blocker = patch(target, side_effect=AssertionError("No network in 12B4a"))
            blocker.start()
            self.addCleanup(blocker.stop)

    def next_id(self):
        value = "parent-plan-" + str(len(self.ids) + 1)
        self.ids.append(value)
        return value

    def service(self, parent):
        return InvocationService("C1", self.store, self.clock, self.grant,
            self.identity, worst_case_cost=1.0,
            invocation_id_factory=self.next_id, parent_gateway=parent)

    def durable_state(self):
        return (self.store.checkpoint("C1"),
                self.store.campaign_usage(self.grant.permit_hash),
                self.store.processing_attempts(self.binding))

    def receipt(self, service):
        request = service.current_request
        identity = request.identity
        return make_processing_receipt(role="planning",
            invocation_id=request.invocation_id, provider=identity.provider,
            requested_model=identity.model, prompt_hash=identity.prompt_hash,
            version=identity.version, input_hashes=identity.input_hashes,
            processed_at=self.clock.now(), usage={"tokens": 1.0})

    def test_parent_planning_receipt_uses_one_original_scope_and_real_debit(self):
        service = self.service(self.gateway)
        self.assertIs(service.parent_gateway, self.gateway)
        with self.assertRaises(AttributeError):
            service.parent_gateway = self.gateway
        execution = ExecutionContext.capture(
            self.clock.now() + timedelta(seconds=20), self.clock)
        captured = (execution.deadline, execution.captured_at,
                    execution.captured_monotonic, execution.monotonic_deadline)
        before = self.store.checkpoint("C1").budget
        real_scope = self.store.execution_scope
        scope_entries = []

        @contextmanager
        def counted_scope(context, clock):
            scope_entries.append((context, clock))
            with real_scope(context, clock):
                yield

        real_reserve = self.store.reserve_invocation

        def reserve_with_setup_time(request, now):
            attempt = real_reserve(request, now)
            self.clock.advance(0.25, utc=False)
            return attempt

        def invoke():
            request = service.current_request
            self.callbacks.append(request.invocation_id)
            attempt, saved = self.store.invocation(request.invocation_id)
            self.assertEqual(attempt.status, "consumed")
            self.assertIsNone(saved)
            budget = self.store.checkpoint("C1").budget
            self.assertEqual(budget.tool_calls, before.tool_calls + 1)
            self.assertEqual(budget.planner_calls, before.planner_calls + 1)
            self.assertEqual(budget.role_allowances["planning"].invocations, 1)
            self.assertEqual(budget.role_allowances["planning"].usage, {"tokens": 10.0})
            self.assertEqual(budget.role_allowances["planning"].cost, 1.0)
            # Public context construction belongs only to the owned reservation.
            # No client/catalog is used by this accounting callback.
            context = service.processing_context(None, None)
            lease = self.store.entry("invocation:" + request.invocation_id)
            self.assertEqual(lease.reserved_seconds, 10.0)
            self.assertLessEqual(lease.deadline, execution.deadline)
            self.assertAlmostEqual(context.timeout_seconds, 9.75)
            self.assertEqual(context.identity, self.identity)
            self.assertEqual(dict(context.reserved_usage), {"tokens": 10.0})
            self.clock.advance(0.5, utc=False)
            return self.receipt(service)

        with patch.object(self.store, "execution_scope", counted_scope), \
             patch.object(self.store, "reserve_invocation", reserve_with_setup_time):
            with self.gateway.execution_scope(execution) as timing:
                self.assertIs(self.gateway.processing_parent_timing(
                    store=self.store, clock=self.clock), timing)
                receipt = service.call_in_parent("planning", self.identity.input_hashes,
                    {"tokens": 10.0}, invoke)
                # The service did not exit/replace the surrounding gateway scope.
                self.assertIs(self.gateway.processing_parent_timing(
                    store=self.store, clock=self.clock), timing)
                self.assertIs(timing.execution, execution)
                with self.assertRaises(JournalFailure):
                    service.processing_context(None, None)
                attempt, saved = self.store.invocation(receipt.invocation_id)
                self.assertEqual(saved, receipt)
                self.assertEqual(attempt.status, "completed")
                self.assertEqual(receipt.output.proposal.operation, "reschedule")
                self.assertEqual(receipt.mode, "synthetic")
                lease = self.store.entry("invocation:" + receipt.invocation_id)
                self.assertEqual(lease.state, "settled")
                budget = self.store.checkpoint("C1").budget
                self.assertAlmostEqual(budget.active_seconds, before.active_seconds + 0.75)
                self.assertEqual(self.store.campaign_usage(self.grant.permit_hash),
                    {"invocations": 1, "cost": 1.0, "usage": {"tokens": 10.0}})
        self.assertEqual(scope_entries, [(execution, self.clock)])
        self.assertEqual(self.ids, ["parent-plan-1"])
        self.assertEqual(self.callbacks, ["parent-plan-1"])
        self.assertEqual(captured, (execution.deadline, execution.captured_at,
            execution.captured_monotonic, execution.monotonic_deadline))
        with self.assertRaises(JournalFailure):
            self.gateway.processing_parent_timing(store=self.store, clock=self.clock)

    def test_inactive_parent_denies_before_id_callback_or_any_debit(self):
        service = self.service(self.gateway)  # inactive is valid construction
        before, calls = self.durable_state(), self.fx.world.calls

        def invoke():
            self.callbacks.append("unsafe")
            return self.receipt(service)

        with self.assertRaises(JournalFailure):
            service.call_in_parent("planning", self.identity.input_hashes,
                {"tokens": 10.0}, invoke)
        self.assertEqual(self.ids, [])
        self.assertEqual(self.callbacks, [])
        self.assertEqual(self.durable_state(), before)
        self.assertEqual(self.fx.world.calls, calls)
        # Configured ordinary public call must not choose a wall-time fallback.
        with self.assertRaises(JournalFailure):
            service.call("planning", self.identity.input_hashes,
                {"tokens": 10.0}, invoke)
        self.assertEqual(self.ids, [])
        self.assertEqual(self.callbacks, [])
        self.assertEqual(self.durable_state(), before)

    def test_foreign_store_or_clock_parent_denies_at_construction_without_debit(self):
        foreign_store = CaseStore(self.root / "foreign.sqlite")
        self.addCleanup(foreign_store.close)
        foreign_clock = ParentClock(FakeClock())
        parents = (
            ActionGateway(self.fx.profile, self.fx.world.bundle(),
                          foreign_store, self.clock, auth=self.fx.auth),
            ActionGateway(self.fx.profile, self.fx.world.bundle(),
                          self.store, foreign_clock, auth=self.fx.auth),
        )
        before, calls = self.durable_state(), self.fx.world.calls
        for parent in parents:
            with self.subTest(parent_store_matches=parent.store is self.store), \
                 self.assertRaises(JournalFailure):
                self.service(parent)
            self.assertEqual(self.ids, [])
            self.assertEqual(self.callbacks, [])
            self.assertEqual(self.durable_state(), before)
            self.assertEqual(self.fx.world.calls, calls)

    def execution(self, seconds=20):
        return ExecutionContext.capture(self.clock.now() + timedelta(seconds=seconds), self.clock)

    def call_parent(self, service, invoke=None):
        return service.call_in_parent("planning", self.identity.input_hashes,
            {"tokens": 10.0}, invoke or (lambda: self.receipt(service)))

    def assert_unknown(self, invocation_id, *, callbacks=0):
        attempt, receipt = self.store.invocation(invocation_id)
        self.assertIsNotNone(receipt)
        self.assertEqual((attempt.status, receipt.status), ("outcome_unknown", "outcome_unknown"))
        self.assertIsNone(receipt.output)
        self.assertEqual(receipt.usage, {})
        self.assertEqual(self.store.entry("invocation:" + invocation_id).state, "active")
        budget = self.store.checkpoint("C1").budget
        self.assertEqual(budget.role_allowances["planning"].invocations, 1)
        self.assertEqual(budget.role_allowances["planning"].cost, 1.0)
        self.assertEqual(budget.role_allowances["planning"].usage, {"tokens": 10.0})
        self.assertGreaterEqual(budget.active_seconds, 10.0)
        self.assertEqual(self.store.campaign_usage(self.grant.permit_hash),
            {"invocations": 1, "cost": 1.0, "usage": {"tokens": 10.0}})
        self.assertEqual(len(self.callbacks), callbacks)

    def assert_context_closed(self, service):
        with self.assertRaises(JournalFailure):
            service.current_request
        with self.assertRaises(JournalFailure):
            service.processing_context(None, None)

    def test_mutating_both_public_clocks_cannot_replace_fixed_constructor_association(self):
        service = self.service(self.gateway)
        before = self.durable_state()
        original_clock = self.clock
        changed_clock = ParentClock(self.fx.clock)
        self.gateway.clock = service.clock = changed_clock
        with self.gateway.execution_scope(self.execution()):
            with self.assertRaises(JournalFailure):
                self.call_parent(service)
        self.gateway.clock = service.clock = original_clock
        self.assertEqual(self.ids, [])
        self.assertEqual(self.durable_state(), before)

    def test_parent_exit_during_callback_denies_context_and_retains_unknown(self):
        service = self.service(self.gateway)
        scope = self.gateway.execution_scope(self.execution())
        scope.__enter__()
        def invoke():
            self.callbacks.append(service.current_request.invocation_id)
            receipt = self.receipt(service)
            scope.__exit__(None, None, None)
            with self.assertRaises(JournalFailure):
                service.processing_context(None, None)
            return receipt
        try:
            with self.assertRaises(JournalFailure):
                self.call_parent(service, invoke)
        finally:
            scope.__exit__(None, None, None)
        self.assert_unknown(self.ids[0], callbacks=1)
        self.assert_context_closed(service)
        with self.gateway.execution_scope(self.execution()):
            receipt = self.call_parent(service)
        self.assertEqual(self.store.invocation(receipt.invocation_id)[0].status, "completed")

    def test_parent_exit_reentry_cannot_publish_from_original_timing(self):
        service = self.service(self.gateway)
        execution = self.execution()
        scope = self.gateway.execution_scope(execution)
        timing = scope.__enter__()
        replacement = []
        def invoke():
            self.callbacks.append(service.current_request.invocation_id)
            receipt = self.receipt(service)
            scope.__exit__(None, None, None)
            new_scope = self.gateway.execution_scope(execution)
            replacement.append(new_scope)
            self.assertIsNot(new_scope.__enter__(), timing)
            return receipt
        try:
            with self.assertRaises(JournalFailure):
                self.call_parent(service, invoke)
        finally:
            for cm in replacement:
                cm.__exit__(None, None, None)
            scope.__exit__(None, None, None)
        self.assert_unknown(self.ids[0], callbacks=1)
        self.assert_context_closed(service)
        with self.gateway.execution_scope(self.execution()):
            self.assertEqual(self.call_parent(service).status, "completed")

    def test_parent_exit_in_request_setup_denies_before_reservation(self):
        service = self.service(self.gateway)
        before = self.durable_state()
        scope = self.gateway.execution_scope(self.execution())
        scope.__enter__()
        def identifier():
            value = self.next_id()
            scope.__exit__(None, None, None)
            return value
        service._id = identifier
        try:
            with self.assertRaises(JournalFailure):
                self.call_parent(service)
        finally:
            scope.__exit__(None, None, None)
        self.assertEqual(self.ids, ["parent-plan-1"])
        self.assertEqual(self.durable_state(), before)
        self.assert_context_closed(service)

    def test_parent_exit_after_real_reservation_denies_before_callback(self):
        service = self.service(self.gateway)
        scope = self.gateway.execution_scope(self.execution())
        scope.__enter__()
        real = self.store.reserve_invocation
        def reserve(request, now):
            attempt = real(request, now)
            scope.__exit__(None, None, None)
            return attempt
        def invoke():
            self.callbacks.append("unsafe")
            return self.receipt(service)
        try:
            with patch.object(self.store, "reserve_invocation", reserve):
                with self.assertRaises(JournalFailure):
                    self.call_parent(service, invoke)
        finally:
            scope.__exit__(None, None, None)
        self.assert_unknown(self.ids[0])
        self.assert_context_closed(service)

    def test_parent_exit_at_saved_readback_prevents_successful_return(self):
        service = self.service(self.gateway)
        scope = self.gateway.execution_scope(self.execution())
        scope.__enter__()
        real = self.store.invocation
        def readback(invocation_id):
            result = real(invocation_id)
            if result[1] is not None and result[1].status == "completed":
                scope.__exit__(None, None, None)
            return result
        try:
            with patch.object(self.store, "invocation", readback):
                with self.assertRaises(JournalFailure):
                    self.call_parent(service)
        finally:
            scope.__exit__(None, None, None)
        self.assertEqual(self.store.invocation(self.ids[0])[0].status, "completed")
        self.assertEqual(self.store.campaign_usage(self.grant.permit_hash)["invocations"], 1)
        self.assert_context_closed(service)
        with self.gateway.execution_scope(self.execution()):
            self.assertEqual(self.call_parent(service).status, "completed")

    def test_parent_exit_during_lease_setup_prevents_callback(self):
        service = self.service(self.gateway)
        scope = self.gateway.execution_scope(self.execution())
        scope.__enter__()
        real = self.store.entry
        def entry(entry_id):
            lease = real(entry_id)
            scope.__exit__(None, None, None)
            return lease
        def invoke():
            self.callbacks.append(service.current_request.invocation_id)
            return self.receipt(service)
        try:
            with patch.object(self.store, "entry", entry):
                with self.assertRaises(JournalFailure):
                    self.call_parent(service, invoke)
        finally:
            scope.__exit__(None, None, None)
        self.assert_unknown(self.ids[0])
        self.assert_context_closed(service)

    def test_final_parent_verification_time_cannot_outlive_committed_lease(self):
        service = self.service(self.gateway)
        real_entry, real_now = self.store.entry, self.clock.now
        observations = [None]
        def entry(entry_id):
            lease = real_entry(entry_id)
            observations[0] = 0
            return lease
        def now():
            value = real_now()
            if observations[0] is not None:
                observations[0] += 1
                if observations[0] == 2:
                    self.clock.advance(10, utc=False)
            return value
        def invoke():
            self.callbacks.append(service.current_request.invocation_id)
            return self.receipt(service)
        with self.gateway.execution_scope(self.execution(40)), \
                patch.object(self.store, "entry", entry), patch.object(self.clock, "now", now):
            with self.assertRaises(JournalFailure):
                self.call_parent(service, invoke)
        self.assert_unknown(self.ids[0])
        self.assert_context_closed(service)

    def test_exact_parent_type_rejects_custom_and_subclass_before_source_access(self):
        class Custom:
            @property
            def store(self):
                raise AssertionError("custom parent must not be inspected")
        class Subclass(ActionGateway):
            pass
        before = self.durable_state()
        for parent in (Custom(), Subclass(self.fx.profile, self.fx.world.bundle(),
                         self.store, self.clock, auth=self.fx.auth)):
            with self.assertRaises(JournalFailure):
                self.service(parent)
        self.assertEqual(self.ids, [])
        self.assertEqual(self.durable_state(), before)

    def test_changed_parent_or_service_association_denies_before_id(self):
        service = self.service(self.gateway)
        foreign = CaseStore(self.root / "mutation.sqlite")
        self.addCleanup(foreign.close)
        clock = ParentClock(self.fx.clock)
        before = self.durable_state()
        for obj, attr, value in ((self.gateway, "store", foreign),
                (service, "store", foreign), (self.gateway, "clock", clock),
                (service, "clock", clock)):
            with self.gateway.execution_scope(self.execution()):
                with patch.object(obj, attr, value):
                    with self.assertRaises(JournalFailure):
                        self.call_parent(service)
            self.assertEqual(self.ids, [])
            self.assertEqual(self.durable_state(), before)

    def test_wrong_thread_cannot_use_service_or_retained_parent_timing(self):
        service = self.service(self.gateway)
        before = self.durable_state()
        failures = []
        def worker():
            for operation in (lambda: self.call_parent(service),
                    lambda: self.gateway.processing_parent_timing(store=self.store, clock=self.clock)):
                try:
                    operation()
                except JournalFailure as exc:
                    failures.append(str(exc))
        with self.gateway.execution_scope(self.execution()):
            thread = threading.Thread(target=worker)
            thread.start()
            thread.join(5)
            self.assertFalse(thread.is_alive())
        self.assertEqual(len(failures), 2)
        self.assertEqual(self.ids, [])
        self.assertEqual(self.durable_state(), before)

    def test_configured_ordinary_and_forged_parent_keywords_deny_before_id(self):
        service = self.service(self.gateway)
        before = self.durable_state()
        execution = self.execution()
        with self.gateway.execution_scope(execution) as timing:
            with self.assertRaises(JournalFailure):
                service.call("planning", self.identity.input_hashes, {"tokens": 10.0},
                    lambda: self.receipt(service), execution=execution)
            for extra in ({"execution": execution}, {"timing": timing},
                    {"already_scoped": True}, {"token": timing}):
                with self.assertRaises(TypeError):
                    service.call_in_parent("planning", self.identity.input_hashes, {"tokens": 10.0},
                        lambda: self.receipt(service), **extra)
        self.assertEqual(self.ids, [])
        self.assertEqual(self.durable_state(), before)

    def test_unconfigured_standalone_legacy_and_explicit_calls_remain_lawful(self):
        service = self.service(None)
        self.assertIsNone(service.parent_gateway)
        for execution in (None, self.execution()):
            receipt = service.call("planning", self.identity.input_hashes, {"tokens": 10.0},
                lambda: self.receipt(service), execution=execution)
            self.assertEqual(self.store.invocation(receipt.invocation_id)[1], receipt)
            self.assert_context_closed(service)
        before = self.durable_state()
        with self.assertRaises(JournalFailure):
            self.call_parent(service)
        self.assertEqual(len(self.ids), 2)
        self.assertEqual(self.durable_state(), before)

    def test_parent_legacy_scope_keeps_existing_legacy_timing(self):
        service = self.service(self.gateway)
        with self.gateway.execution_scope() as timing:
            receipt = self.call_parent(service)
            self.assertIsNone(timing.execution)
            self.assertIs(self.gateway.processing_parent_timing(store=self.store, clock=self.clock), timing)
            self.assertEqual(self.store.invocation(receipt.invocation_id)[1], receipt)

    def test_setup_expiry_cannot_reserve_or_renew_original_context(self):
        service = self.service(self.gateway)
        execution = self.execution(1)
        before = self.durable_state()
        def identifier():
            value = self.next_id()
            self.clock.advance(1, utc=False)
            return value
        service._id = identifier
        with self.gateway.execution_scope(execution):
            with self.assertRaises(JournalFailure):
                self.call_parent(service)
        self.assertEqual(self.ids, ["parent-plan-1"])
        self.assertEqual(self.durable_state(), before)
        self.assertEqual(execution.monotonic_deadline, 1.0)
        self.assert_context_closed(service)

    def test_utc_observation_expiry_denies_before_id_or_debit(self):
        service = self.service(self.gateway)
        execution = self.execution(1)
        before = self.durable_state()
        real = self.clock.now
        def slow_observation():
            value = real()
            self.clock.advance(1, utc=False)
            return value
        with self.gateway.execution_scope(execution):
            with patch.object(self.clock, "now", slow_observation):
                with self.assertRaises(JournalFailure):
                    self.call_parent(service)
        self.assertEqual(self.ids, [])
        self.assertEqual(self.durable_state(), before)

    def test_post_reservation_lease_expiry_keeps_unknown_with_zero_callback(self):
        service = self.service(self.gateway)
        real = self.store.reserve_invocation
        def reserve(request, now):
            attempt = real(request, now)
            self.clock.advance(10, utc=False)
            return attempt
        with self.gateway.execution_scope(self.execution(20)), \
                patch.object(self.store, "reserve_invocation", reserve):
            with self.assertRaises(JournalFailure):
                self.call_parent(service, lambda: self.callbacks.append("unsafe"))
        self.assert_unknown(self.ids[0])
        self.assert_context_closed(service)

    def test_public_context_construction_consumes_utc_observation_time(self):
        service = self.service(self.gateway)
        real = self.clock.now
        def slow_observation():
            value = real()
            self.clock.advance(10, utc=False)
            return value
        def invoke():
            self.callbacks.append(service.current_request.invocation_id)
            with patch.object(self.clock, "now", slow_observation):
                service.processing_context(None, None)
            self.fail("expired context returned")
        with self.gateway.execution_scope(self.execution(40)):
            with self.assertRaises(JournalFailure):
                self.call_parent(service, invoke)
        self.assert_unknown(self.ids[0], callbacks=1)
        self.assert_context_closed(service)

    def test_public_context_timeout_includes_parent_verification_observations(self):
        service = self.service(self.gateway)
        real = self.clock.now
        def slow_observation():
            value = real()
            self.clock.advance(0.25, utc=False)
            return value
        def invoke():
            started = self.clock.seconds
            with patch.object(self.clock, "now", slow_observation):
                context = service.processing_context(None, None)
            self.assertAlmostEqual(context.timeout_seconds, 10.0 - (self.clock.seconds - started))
            return self.receipt(service)
        with self.gateway.execution_scope(self.execution(40)):
            receipt = self.call_parent(service, invoke)
        self.assertEqual(self.store.invocation(receipt.invocation_id)[1], receipt)
        self.assertAlmostEqual(self.store.checkpoint("C1").budget.active_seconds, self.clock.seconds)

    def test_callback_exception_keeps_unknown_and_next_lawful_scope_usable(self):
        service = self.service(self.gateway)
        def invoke():
            self.callbacks.append(service.current_request.invocation_id)
            raise TimeoutError("synthetic callback fault")
        with self.gateway.execution_scope(self.execution()):
            with self.assertRaises(TimeoutError):
                self.call_parent(service, invoke)
        self.assert_unknown(self.ids[0], callbacks=1)
        self.assert_context_closed(service)
        with self.gateway.execution_scope(self.execution()):
            self.assertEqual(self.call_parent(service).status, "completed")

    def test_invalid_receipt_keeps_unknown_without_usable_output(self):
        service = self.service(self.gateway)
        def invoke():
            self.callbacks.append(service.current_request.invocation_id)
            return self.receipt(service).model_copy(update={"invocation_id": "foreign-receipt"})
        with self.gateway.execution_scope(self.execution()):
            with self.assertRaises(JournalFailure):
                self.call_parent(service, invoke)
        self.assert_unknown(self.ids[0], callbacks=1)
        self.assert_context_closed(service)

    def test_nonfinite_and_reversed_parent_clock_never_returns_complete_output(self):
        service = self.service(self.gateway)
        for value in (float("nan"), -1.0):
            before = self.store.checkpoint("C1").budget
            def invoke():
                self.callbacks.append(service.current_request.invocation_id)
                receipt = self.receipt(service)
                self.clock.seconds = value
                return receipt
            with self.gateway.execution_scope(self.execution()):
                with self.assertRaises(JournalFailure):
                    self.call_parent(service, invoke)
            self.clock.seconds = 0.0
            attempt, saved = self.store.invocation(self.ids[-1])
            self.assertEqual(attempt.status, "consumed")
            self.assertIsNone(saved)
            self.assertEqual(self.store.checkpoint("C1").budget.active_seconds,
                before.active_seconds + 10.0)
            reopened = CaseStore(self.root / "journal.sqlite")
            self.addCleanup(reopened.close)
            reopened_attempt, reopened_receipt = reopened.invocation(self.ids[-1])
            self.assertEqual(reopened_attempt.status, "consumed")
            self.assertIsNone(reopened_receipt)
            self.assertEqual(reopened.campaign_usage(self.grant.permit_hash)["invocations"], len(self.ids))
            reopened.close()
            self.assert_context_closed(service)
        with self.gateway.execution_scope(self.execution()):
            self.assertEqual(self.call_parent(service).status, "completed")

    def test_recovered_invalid_clock_still_records_actual_unknown_receipt(self):
        service = self.service(self.gateway)
        real = self.clock.monotonic
        invalid = [False]
        def observation():
            if invalid[0]:
                invalid[0] = False
                return float("nan")
            return real()
        def invoke():
            self.callbacks.append(service.current_request.invocation_id)
            receipt = self.receipt(service)
            invalid[0] = True
            return receipt
        with self.gateway.execution_scope(self.execution()), \
                patch.object(self.clock, "monotonic", observation):
            with self.assertRaises(JournalFailure):
                self.call_parent(service, invoke)
        self.assert_unknown(self.ids[0], callbacks=1)
        self.assert_context_closed(service)

    def test_late_callback_keeps_debit_and_no_completed_output(self):
        service = self.service(self.gateway)
        def invoke():
            self.callbacks.append(service.current_request.invocation_id)
            self.clock.advance(11, utc=False)
            return self.receipt(service)
        with self.gateway.execution_scope(self.execution(20)):
            with self.assertRaises(BudgetExceeded):
                self.call_parent(service, invoke)
        attempt, saved = self.store.invocation(self.ids[0])
        self.assertEqual(attempt.status, "outcome_unknown")
        self.assertIsNone(saved.output)
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 120.0)
        self.assertEqual(self.store.campaign_usage(self.grant.permit_hash)["invocations"], 1)
        self.assert_context_closed(service)

    def test_recursion_denies_without_second_debit_and_outer_scope_remains_usable(self):
        service = self.service(self.gateway)
        def invoke():
            with self.assertRaises(JournalFailure):
                self.call_parent(service)
            with self.assertRaises(GateDenied):
                with self.gateway.execution_scope(self.execution()):
                    self.fail("recursive gateway entered")
            return self.receipt(service)
        with self.gateway.execution_scope(self.execution()) as timing:
            self.call_parent(service, invoke)
            self.assertIs(self.gateway.processing_parent_timing(store=self.store, clock=self.clock), timing)
        self.assertEqual(self.ids, ["parent-plan-1"])
        self.assertEqual(self.store.campaign_usage(self.grant.permit_hash)["invocations"], 1)
        self.assert_context_closed(service)
        with self.gateway.execution_scope(self.execution()):
            self.assertEqual(self.call_parent(service).status, "completed")

    def test_stopped_and_ownership_fenced_reservations_never_enter_or_consume(self):
        service = self.service(self.gateway)
        original = self.store.checkpoint("C1")
        for state in ("pending", "transfer_pending", "stopped"):
            self.store.save_checkpoint(original.model_copy(update={"ownership_state": state}))
            before = self.durable_state()
            with self.gateway.execution_scope(self.execution()):
                with self.assertRaises(JournalFailure):
                    self.call_parent(service, lambda: self.callbacks.append("unsafe"))
            self.assertEqual(self.durable_state(), before)
        self.store.save_checkpoint(original)
        self.store.set_stop("C1", self.binding.generation)
        before = self.durable_state()
        with self.gateway.execution_scope(self.execution()):
            with self.assertRaises(JournalFailure):
                self.call_parent(service, lambda: self.callbacks.append("unsafe"))
        self.assertEqual(self.durable_state(), before)
        self.assertEqual(self.callbacks, [])
        self.assert_context_closed(service)

    def test_service_store_mutation_after_reserve_preserves_original_unknown_debt(self):
        service = self.service(self.gateway)
        foreign = CaseStore(self.root / "after-reserve.sqlite")
        self.addCleanup(foreign.close)
        real = self.store.reserve_invocation
        def reserve(request, now):
            attempt = real(request, now)
            service.store = foreign
            return attempt
        with self.gateway.execution_scope(self.execution()), \
                patch.object(self.store, "reserve_invocation", reserve):
            with self.assertRaises(JournalFailure):
                self.call_parent(service, lambda: self.callbacks.append("unsafe"))
        service.store = self.store
        self.assert_unknown(self.ids[0])
        self.assert_context_closed(service)
        with self.gateway.execution_scope(self.execution()):
            self.assertEqual(self.call_parent(service).status, "completed")

    def test_service_association_mutation_during_callback_preserves_original_debt(self):
        service = self.service(self.gateway)
        foreign = CaseStore(self.root / "after-callback.sqlite")
        self.addCleanup(foreign.close)
        foreign_clock = ParentClock(FakeClock())
        def invoke():
            self.callbacks.append(service.current_request.invocation_id)
            receipt = self.receipt(service)
            service.store, service.clock = foreign, foreign_clock
            return receipt
        with self.gateway.execution_scope(self.execution()):
            with self.assertRaises(JournalFailure):
                self.call_parent(service, invoke)
        service.store, service.clock = self.store, self.clock
        self.assert_unknown(self.ids[0], callbacks=1)
        self.assert_context_closed(service)
        with self.gateway.execution_scope(self.execution()):
            self.assertEqual(self.call_parent(service).status, "completed")
