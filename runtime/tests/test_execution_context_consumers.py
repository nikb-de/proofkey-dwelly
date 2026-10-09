"""Trusted host timing propagation; clocks/sources below are synthetic."""
from datetime import timedelta
from dataclasses import replace
import tempfile
import threading
from pathlib import Path
import subprocess
import sys
import unittest

from proofkey.budget import BudgetExceeded
from proofkey.execution import ExecutionContext
from proofkey.engine import WorkflowEngine
from proofkey.policy import GateDenied
from proofkey.journal import CaseStore, JournalFailure
from proofkey.providers.invocations import InvocationService
from support import build_test_runtime, FakeClock, DEADLINE, make_binding, make_checkpoint, make_request


def processing_fixture(folder, id_factory=None):
    from pathlib import Path
    from proofkey.contracts import BudgetLedger, RoleAllowance
    from test_provider_invocation_recovery import permit, invocation
    store = CaseStore(Path(folder) / "processing.sqlite")
    budget = BudgetLedger(case_id="C1", deadline=DEADLINE, role_allowances={"extraction": RoleAllowance(
        max_invocations=3, max_cost=6.0, usage_allowances={"tokens": 60.0})})
    store.admit(make_binding(), make_request(), make_checkpoint(budget=budget))
    grant = permit()
    store.register_campaign(grant)
    clock = ConsumerClock(FakeClock())
    service = InvocationService("C1", store, clock, grant, invocation(grant).identity,
        worst_case_cost=2.0, invocation_id_factory=id_factory or (lambda: "invoke-1"))
    return store, clock, service


def processing_receipt(service, clock, *, status="completed"):
    from proofkey.contracts import AssertionsOutput, ProcessingReceipt
    from proofkey.providers.invocations import output_digest
    request = service.current_request
    identity = request.identity
    output = AssertionsOutput(kind="assertions", assertions=[]) if status == "completed" else None
    return ProcessingReceipt(invocation_id=request.invocation_id, role=identity.role, provider=identity.provider,
        requested_model=identity.model, prompt_hash=identity.prompt_hash, version=identity.version,
        input_hashes=identity.input_hashes, mode="synthetic", status=status, latency_seconds=0.0, usage={},
        output=output, output_hashes=[output_digest(output)] if output else [], processed_at=clock.now())


def observe_deadlines(bundle, deadlines):
    def wrap(port):
        class Port:
            def __getattr__(self, name):
                target = getattr(port, name)
                if not callable(target):
                    return target
                def forward(*args, **kwargs):
                    deadline = kwargs.get("deadline", getattr(args[0], "deadline", None) if args else None)
                    if deadline is not None:
                        deadlines.append(deadline)
                    return target(*args, **kwargs)
                return forward
        return Port()
    return replace(bundle, **{name: wrap(getattr(bundle, name)) for name in
        ("case", "delivery", "scheduling", "returns", "messaging", "operator")})


class ConsumerClock:
    def __init__(self, utc_clock):
        self.utc_clock = utc_clock
        self.seconds = 0.0
        self.waits = []
        self.on_now = None

    def now(self):
        value = self.utc_clock.now()
        if self.on_now is not None:
            self.on_now()
        return value

    def monotonic(self):
        return self.seconds

    def wait(self, delay):
        self.waits.append(delay)
        self.advance(delay)

    def advance(self, seconds, *, utc=True):
        self.seconds += seconds
        if utc:
            self.utc_clock.advance(seconds)


class ExecutionConsumerTests(unittest.TestCase):
    def test_legacy_auth_is_retained_but_explicit_context_restores_after_normal_or_crash(self):
        from test_workflows import CrashOnPhase, ProcessCrash
        from support import make_auth
        for scoped in (False, True):
            for crash in (False, True):
                with self.subTest(scoped=scoped, crash=crash), tempfile.TemporaryDirectory() as folder:
                    fx = build_test_runtime(folder)
                    self.addCleanup(fx.store.close)
                    clock = ConsumerClock(fx.clock)
                    engine = (CrashOnPhase(fx, "window_gate") if crash else
                        WorkflowEngine(fx.profile, fx.world.bundle(), fx.store, clock))
                    engine.clock = engine.gateway.clock = clock
                    prior = make_auth(caller_id="prior-host", proof_reference="prior-proof")
                    engine.gateway.auth = prior
                    context = ExecutionContext.capture(clock.now() + timedelta(seconds=20), clock)
                    if crash:
                        with self.assertRaises(ProcessCrash):
                            engine.run(fx.request, fx.auth, execution=context if scoped else None)
                    else:
                        result = engine.run(fx.request, fx.auth, execution=context if scoped else None)
                        self.assertEqual(result.effects["reschedule"].status, "verified")
                    self.assertEqual(engine.gateway.auth, prior if scoped else fx.auth)
                    self.assertFalse(engine._entry_active)
                    with engine.gateway.execution_scope(context) as timing:
                        self.assertIs(timing.execution, context)
                    self.assertEqual(engine.gateway.auth, prior if scoped else fx.auth)
                    if not scoped and not crash:
                        original = fx.store.intents("C1")[0].intent
                        self.assertEqual(engine.gateway.reconcile_read_only(original.action_id).status, "verified")
                        self.assertEqual(fx.world.effect_count("reschedule"), 1)

    def test_processing_timeout_resamples_elapsed_after_delayed_utc_observation(self):
        with tempfile.TemporaryDirectory() as folder:
            store, clock, service = processing_fixture(folder)
            self.addCleanup(store.close)
            context = ExecutionContext.capture(clock.now() + timedelta(seconds=20), clock)
            observed = []
            def invoke():
                clock.on_now = lambda: clock.advance(0.25, utc=False)
                observed.append(service.processing_context(None, None).timeout_seconds)
                clock.on_now = None
                return processing_receipt(service, clock)
            service.call("extraction", service.campaign.input_hashes, {"tokens": 10}, invoke,
                execution=context)
            self.assertEqual(observed, [9.75])
            self.assertAlmostEqual(store.checkpoint("C1").budget.active_seconds, 0.25)

    def test_invalid_wrong_thread_and_recursive_entries_restore_auth_and_host_scope(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = build_test_runtime(folder)
            self.addCleanup(fx.store.close)
            clock = ConsumerClock(fx.clock)
            engine = WorkflowEngine(fx.profile, fx.world.bundle(), fx.store, clock)
            sentinel = fx.auth
            engine.gateway.auth = sentinel
            process = engine.process
            for invalid in ({}, True, "caller-selected"):
                self.assertEqual(engine.run(fx.request, fx.auth, execution=invalid).status, "denied")
                self.assertIs(engine.gateway.auth, sentinel)
                self.assertIs(engine.process, process)
                self.assertFalse(fx.store.has_case("C1"))
            context = ExecutionContext.capture(clock.now() + timedelta(seconds=20), clock)
            results = []
            worker = threading.Thread(target=lambda: results.append(engine.run(fx.request, fx.auth, execution=context)))
            worker.start()
            worker.join(5)
            self.assertFalse(worker.is_alive())
            self.assertEqual(results[0].status, "denied")
            self.assertEqual(fx.world.calls, ())
            real = engine.gateway.bundle.case
            recursive = []
            class CasePort:
                def __getattr__(self, name): return getattr(real, name)
                def read_case(self, request):
                    recursive.append(engine.run(fx.request, fx.auth, execution=context))
                    return real.read_case(request)
            engine.gateway.bundle = replace(engine.gateway.bundle, case=CasePort())
            self.assertEqual(engine.run(fx.request, fx.auth, execution=context).effects["reschedule"].status, "verified")
            self.assertTrue(recursive)
            self.assertTrue(all(result.status == "denied" for result in recursive))
            self.assertIs(engine.gateway.auth, sentinel)
            self.assertFalse(engine._entry_active)
            with fx.store.execution_scope(context, clock):
                # Scope restoration permits the next distinct host entry.
                self.assertTrue(fx.store.has_case("C1"))

    def test_gateway_read_monotonic_settlement_and_backwards_utc_never_refund_unknown(self):
        for reverse in (False, True):
            with self.subTest(reverse=reverse), tempfile.TemporaryDirectory() as folder:
                fx = build_test_runtime(folder)
                self.addCleanup(fx.store.close)
                with fx.engine._entry_scope():
                    cp = fx.engine.authenticate_and_bind(fx.request, fx.auth)
                clock = ConsumerClock(fx.clock)
                fx.engine.gateway.clock = clock
                context = ExecutionContext.capture(clock.now() + timedelta(seconds=2), clock)
                real = fx.world.bundle().case
                class CasePort:
                    def __getattr__(self, name): return getattr(real, name)
                    def read_case(self, request):
                        reply = real.read_case(request)
                        clock.advance(0.25, utc=False)
                        if reverse:
                            fx.clock.advance(-0.1)
                        return reply
                fx.engine.gateway.bundle = replace(fx.engine.gateway.bundle, case=CasePort())
                before = fx.store.checkpoint("C1")
                with fx.engine.gateway.execution_scope(context):
                    if reverse:
                        with self.assertRaises(GateDenied):
                            fx.engine.gateway.authenticate_control(cp.binding, fx.auth, purpose="stop")
                    else:
                        fx.engine.gateway.authenticate_control(cp.binding, fx.auth, purpose="stop")
                after = fx.store.checkpoint("C1")
                self.assertEqual(after.budget.tool_calls, before.budget.tool_calls + 1)
                self.assertAlmostEqual(after.budget.active_seconds,
                    1.899999 if reverse else 0.25, places=5)
                self.assertLess(context.remaining_seconds(clock), 2.0)

    def test_time_consumed_observing_utc_blocks_entry_before_source_or_auth(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = build_test_runtime(folder)
            self.addCleanup(fx.store.close)
            clock = ConsumerClock(fx.clock)
            context = ExecutionContext.capture(clock.now() + timedelta(seconds=1), clock)
            clock.on_now = lambda: clock.advance(1, utc=False)
            engine = WorkflowEngine(fx.profile, fx.world.bundle(), fx.store, clock)
            self.assertEqual(engine.run(fx.request, fx.auth, execution=context).status, "denied")
            self.assertEqual(fx.world.calls, ())
            self.assertFalse(fx.store.has_case("C1"))

    def test_customer_and_operator_reply_and_stop_recovery_share_ephemeral_context(self):
        from test_waits import scoped_reply
        from test_operator_boundary import operator_runtime
        from support import make_auth
        for role in ("customer", "operator"):
            with self.subTest(role=role), tempfile.TemporaryDirectory() as folder:
                fx = operator_runtime(folder) if role == "operator" else build_test_runtime(folder)
                self.addCleanup(fx.store.close)
                if role == "operator":
                    with fx.engine._entry_scope():
                        cp = fx.engine.authenticate_and_bind(fx.request, fx.auth)
                    fx.store.save_checkpoint(cp.model_copy(update={"next_gate": "enqueue_handoff"}))
                    fx.engine.recover("C1", fx.auth)
                else:
                    fx.world.mutate("case.completeness", "missing")
                    fx.engine.run(fx.request, fx.auth)
                reply = scoped_reply(fx)
                original_deadline = fx.store.checkpoint("C1").deadline
                clock = ConsumerClock(fx.clock)
                engine = WorkflowEngine(fx.profile, fx.world.bundle(), fx.store, clock)
                context = ExecutionContext.capture(clock.now() + timedelta(seconds=2), clock)
                auth = make_auth(caller_id="OP1", proof_reference="synthetic-operator-proof") if role == "operator" else fx.auth
                calls = len(fx.world.calls)
                self.assertEqual(engine.reply(reply, auth, execution=context).status, "authorized")
                self.assertEqual(len(fx.world.calls) - calls, 4)
                self.assertEqual(fx.store.load_wait_record(reply.question_id).lifecycle, "answered")
                self.assertEqual(engine.stop("C1", "G1", fx.auth, execution=context).status, "authorized")
                stop = fx.store.checkpoint("C1")
                self.assertTrue(stop.stop.requested)
                engine.recover("C1", fx.auth, execution=context)
                self.assertTrue(fx.store.checkpoint("C1").stop.requested)
                self.assertEqual(fx.world.effect_count("reschedule"), 0)
                self.assertGreater(clock.seconds, 0.0)
                self.assertEqual(stop.deadline, original_deadline)
                self.assertEqual(stop.budget.deadline, original_deadline)
                self.assertGreater(original_deadline, context.deadline)

    def test_replay_settlement_includes_time_spent_observing_final_utc(self):
        from proofkey.replay import ReplayService
        with tempfile.TemporaryDirectory() as folder:
            fx = build_test_runtime(folder)
            self.addCleanup(fx.store.close)
            fx.engine.run(fx.request, fx.auth)
            before = fx.store.checkpoint("C1").budget
            clock = ConsumerClock(fx.clock)
            context = ExecutionContext.capture(clock.now() + timedelta(seconds=1), clock)
            real = fx.world.bundle().case
            observations = []
            class CasePort:
                def __getattr__(self, name): return getattr(real, name)
                def read_case(self, request):
                    reply = real.read_case(request)
                    def observe():
                        observations.append(True)
                        if len(observations) == 2:
                            clock.advance(0.25, utc=False)
                    clock.on_now = observe
                    return reply
            bundle = replace(fx.world.bundle(), case=CasePort())
            result = ReplayService(fx.profile, bundle, fx.store, clock).lookup(
                fx.request, fx.auth, execution=context)
            self.assertTrue(result.historical)
            self.assertGreaterEqual(len(observations), 2)
            after = fx.store.checkpoint("C1").budget
            self.assertEqual(after.tool_calls, before.tool_calls + 1)
            self.assertAlmostEqual(after.active_seconds - before.active_seconds, 0.25)

    def test_both_autonomous_positive_families_use_capped_common_physical_path(self):
        requests = (make_request(), make_request(kind="goods_refusal", consent_mode="unknown",
            arguments={"inventory": {"item-1": 1}}))
        for request in requests:
            with self.subTest(kind=request.kind), tempfile.TemporaryDirectory() as folder:
                fx = build_test_runtime(folder, request=request)
                self.addCleanup(fx.store.close)
                clock = ConsumerClock(fx.clock)
                deadlines = []
                engine = WorkflowEngine(fx.profile, observe_deadlines(fx.world.bundle(), deadlines), fx.store, clock)
                context = ExecutionContext.capture(clock.now() + timedelta(seconds=20), clock)
                sentinel = fx.auth
                engine.gateway.auth = sentinel
                result = engine.run(request, fx.auth, execution=context)
                self.assertEqual(result.status, "authorized")
                required = ("reschedule",) if request.kind == "reschedule_window" else (
                    "register_goods_refusal", "create_return")
                for operation in required:
                    self.assertEqual(result.effects[operation].status, "verified")
                    self.assertEqual(fx.world.effect_count(operation), 1)
                self.assertEqual(fx.store.checkpoint("C1").deadline, context.deadline)
                self.assertEqual(fx.store.checkpoint("C1").budget.tool_calls, len(fx.world.calls))
                self.assertEqual(fx.store.checkpoint("C1").budget.planner_calls, 0)
                self.assertIs(engine.gateway.auth, sentinel)
                self.assertEqual(len(deadlines), len(fx.world.calls))
                self.assertTrue(all(deadline <= context.deadline for deadline in deadlines))

    def test_short_saved_replay_keeps_original_horizon_receipt_and_current_acl(self):
        from proofkey.replay import ReplayService
        with tempfile.TemporaryDirectory() as folder:
            fx = build_test_runtime(folder)
            self.addCleanup(fx.store.close)
            original = fx.engine.run(fx.request, fx.auth)
            checkpoint = fx.store.checkpoint("C1")
            saved = fx.store.saved_result("C1", "G1")
            intents = fx.store.intents("C1")
            clock = ConsumerClock(fx.clock)
            context = ExecutionContext.capture(clock.now() + timedelta(seconds=0.5), clock)
            engine = WorkflowEngine(fx.profile, fx.world.bundle(), fx.store, clock)
            result = engine.run(fx.request, fx.auth, execution=context)
            self.assertTrue(result.historical)
            self.assertEqual(result.model_copy(update={"historical": False}).model_dump(), original.model_dump())
            self.assertEqual(fx.store.checkpoint("C1").deadline, checkpoint.deadline)
            self.assertEqual(fx.store.saved_result("C1", "G1"), saved)
            self.assertEqual(fx.store.intents("C1"), intents)
            fx.world.mutate("case.authorization", "revoked")
            denied = ReplayService(fx.profile, fx.world.bundle(), fx.store, clock).lookup(
                fx.request, fx.auth, execution=context)
            self.assertEqual(denied.status, "denied")
            self.assertIsNone(denied.binding)
            self.assertEqual(fx.store.saved_result("C1", "G1"), saved)
            self.assertEqual(fx.world.effect_count("reschedule"), 1)

    def test_same_captured_context_denies_later_case_without_recapture_or_auth(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            fx = build_test_runtime(first)
            self.addCleanup(fx.store.close)
            clock = ConsumerClock(fx.clock)
            context = ExecutionContext.capture(clock.now() + timedelta(seconds=20), clock)
            engine = WorkflowEngine(fx.profile, fx.world.bundle(), fx.store, clock)
            self.assertEqual(engine.run(fx.request, fx.auth, execution=context).effects["reschedule"].status, "verified")
            original = fx.store.checkpoint("C1")
            clock.advance(context.remaining_seconds(clock), utc=False)
            later = build_test_runtime(second, request=make_request(case_id="C2"))
            self.addCleanup(later.store.close)
            later_engine = WorkflowEngine(later.profile, later.world.bundle(), later.store, clock)
            self.assertEqual(later_engine.run(later.request, later.auth, execution=context).status, "denied")
            self.assertFalse(later.store.has_case("C2"))
            self.assertEqual(later.world.calls, ())
            self.assertEqual(fx.store.checkpoint("C1"), original)

    def test_real_simulated_processing_timeout_and_monotonic_settlement_include_reservation_setup(self):
        with tempfile.TemporaryDirectory() as folder:
            store, clock, service = processing_fixture(folder)
            self.addCleanup(store.close)
            context = ExecutionContext.capture(clock.now() + timedelta(seconds=1), clock)
            reserve = store.reserve_invocation
            def delayed(*args):
                result = reserve(*args)
                clock.advance(0.25, utc=False)
                return result
            store.reserve_invocation = delayed
            observed = []
            def invoke():
                observed.append(service.processing_context(None, None).timeout_seconds)
                return processing_receipt(service, clock)
            receipt = service.call("extraction", ["1" * 64], {"tokens": 20.0}, invoke, execution=context)
            self.assertEqual(receipt.status, "completed")
            self.assertEqual(observed, [0.75])
            self.assertEqual(store.checkpoint("C1").budget.active_seconds, 0.25)
            self.assertEqual(store.entry("invocation:invoke-1").state, "settled")
            self.assertEqual(store.campaign_usage(service.campaign.permit_hash)["cost"], 2.0)
            self.assertIsNone(service._timing)

    def test_failed_late_throwing_or_invalid_processing_keeps_full_reserved_debt(self):
        for outcome in ("failed", "late", "throw", "invalid"):
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as folder:
                store, clock, service = processing_fixture(folder)
                self.addCleanup(store.close)
                context = ExecutionContext.capture(clock.now() + timedelta(seconds=1), clock)
                def invoke():
                    if outcome == "throw":
                        raise RuntimeError("test injected transport failure")
                    if outcome == "invalid":
                        return {"status": "completed"}
                    if outcome == "late":
                        clock.advance(1, utc=False)
                    return processing_receipt(service, clock, status="failed" if outcome == "failed" else "completed")
                if outcome == "failed":
                    self.assertEqual(service.call("extraction", ["1" * 64], {"tokens": 20.0}, invoke,
                        execution=context).status, "failed")
                else:
                    with self.assertRaises((JournalFailure, BudgetExceeded, RuntimeError, TypeError)):
                        service.call("extraction", ["1" * 64], {"tokens": 20.0}, invoke, execution=context)
                    self.assertEqual(store.invocation("invoke-1")[1].status, "outcome_unknown")
                self.assertGreaterEqual(store.checkpoint("C1").budget.active_seconds, 1.0)
                self.assertEqual(store.checkpoint("C1").budget.tool_calls, 1)
                self.assertEqual(store.checkpoint("C1").budget.role_allowances["extraction"].cost, 2.0)

    def test_genuine_exit_after_context_capped_dispatch_commit_retains_original_and_debt_on_reopen(self):
        with tempfile.TemporaryDirectory() as folder:
            script = """
import os, sys
from datetime import timedelta
from support import build_test_runtime
from proofkey.engine import WorkflowEngine
from proofkey.execution import ExecutionContext
from test_execution_context_consumers import ConsumerClock
fx=build_test_runtime(sys.argv[1])
clock=ConsumerClock(fx.clock)
engine=WorkflowEngine(fx.profile, fx.world.bundle(), fx.store, clock)
context=ExecutionContext.capture(clock.now()+timedelta(seconds=20),clock)
old=fx.store.begin_dispatch
def die(*args,**kwargs):
    old(*args,**kwargs)
    os._exit(91)
fx.store.begin_dispatch=die
engine.run(fx.request,fx.auth,execution=context)
"""
            child = subprocess.run([sys.executable, "-c", script, folder], capture_output=True, text=True)
            self.assertEqual(child.returncode, 91, child.stderr)
            reopened = CaseStore(Path(folder) / "journal.sqlite")
            try:
                records = reopened.intents("C1")
                self.assertEqual(len(records), 1)
                self.assertEqual(records[0].state, "dispatching")
                self.assertEqual(records[0].intent.operation, "reschedule")
                checkpoint = reopened.checkpoint("C1")
                self.assertEqual((checkpoint.budget.tool_calls, checkpoint.budget.effects,
                    checkpoint.budget.active_seconds, checkpoint.budget.planner_calls), (10, 1, 10.0, 0))
                self.assertEqual(reopened.original_request("C1", "G1"), make_request())
                self.assertEqual(reopened.intents("C1"), records)
            finally:
                reopened.close()

    def test_invocation_wrong_creator_thread_never_reaches_id_factory_or_callback(self):
        with tempfile.TemporaryDirectory() as folder:
            identities, entries, errors = [], [], []
            store, clock, service = processing_fixture(folder,
                lambda: identities.append("allocated") or "invoke-1")
            self.addCleanup(store.close)
            def invoke():
                try:
                    service.call("extraction", ["1" * 64], {"tokens": 20.0}, lambda: entries.append("called"))
                except Exception as error:
                    errors.append(error)
            worker = threading.Thread(target=invoke)
            worker.start()
            worker.join(5)
            self.assertFalse(worker.is_alive())
            self.assertEqual(identities, [], "Creator rejection precedes invocation IDs and mutable service state")
            self.assertEqual(entries, [])
            self.assertIsInstance(errors[0], JournalFailure)
            self.assertEqual(store.checkpoint("C1").budget.tool_calls, 0)

    def test_invocation_after_real_reservation_expiry_keeps_unknown_without_callback(self):
        from proofkey.contracts import ProcessingReceipt
        with tempfile.TemporaryDirectory() as folder:
            store, clock, service = processing_fixture(folder)
            self.addCleanup(store.close)
            context = ExecutionContext.capture(clock.now() + timedelta(seconds=1), clock)
            original = store.reserve_invocation
            def reserve(*args):
                attempt = original(*args)
                clock.advance(context.remaining_seconds(clock))
                return attempt
            store.reserve_invocation = reserve
            entries = []
            def invoke():
                entries.append("called")
                request = service.current_request
                identity = request.identity
                return ProcessingReceipt(invocation_id=request.invocation_id, role=identity.role,
                    provider=identity.provider, requested_model=identity.model, prompt_hash=identity.prompt_hash,
                    version=identity.version, input_hashes=identity.input_hashes, mode="synthetic", status="failed",
                    latency_seconds=0.0, usage={}, processed_at=clock.now())
            with self.assertRaises((JournalFailure, BudgetExceeded)):
                if hasattr(service, "_creator_thread"):
                    service.call("extraction", ["1" * 64], {"tokens": 20.0}, invoke, execution=context)
                else:
                    with store.execution_scope(context, clock):
                        service.call("extraction", ["1" * 64], {"tokens": 20.0}, invoke)
            self.assertEqual(entries, [], "Reservation expiry precedes the actual injected provider boundary")
            attempt, receipt = store.invocation("invoke-1")
            self.assertEqual(receipt.status, "outcome_unknown")
            self.assertEqual(attempt.status, "outcome_unknown")
            budget = store.checkpoint("C1").budget
            self.assertEqual((budget.tool_calls, budget.active_seconds, budget.planner_calls), (1, 1.0, 0))
            self.assertEqual(budget.role_allowances["extraction"].cost, 2.0)
            self.assertEqual(store.campaign_usage(service.campaign.permit_hash)["invocations"], 1)

    def test_monotonic_cutoff_at_return_cannot_refund_or_authorize_with_unchanged_utc(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = build_test_runtime(folder)
            self.addCleanup(fx.store.close)
            with fx.engine._entry_scope():
                cp = fx.engine.authenticate_and_bind(fx.request, fx.auth)
            clock = ConsumerClock(fx.clock)
            fx.engine.gateway.clock = clock
            context = ExecutionContext.capture(clock.now() + timedelta(seconds=1), clock)
            real = fx.world.bundle().case
            leases = []
            reserve = fx.store.begin_control_read
            def capture(*args, **kwargs):
                lease = reserve(*args, **kwargs)
                leases.append(lease)
                return lease
            fx.store.begin_control_read = capture
            class CasePort:
                def __getattr__(self, name): return getattr(real, name)
                def read_case(self, request):
                    reply = real.read_case(request)
                    clock.advance(context.remaining_seconds(clock), utc=False)
                    return reply
            fx.engine.gateway.bundle = replace(fx.engine.gateway.bundle, case=CasePort())
            with fx.engine.gateway.execution_scope(context):
                with self.assertRaises(GateDenied):
                    fx.engine.gateway.authenticate_control(cp.binding, fx.auth, purpose="stop")
            self.assertEqual(fx.store.entry(leases[0].entry_id).state, "active")
            self.assertEqual(fx.store.checkpoint("C1").budget.active_seconds, leases[0].reserved_seconds)

    def test_after_real_dispatch_reservation_expiry_blocks_business_customer_and_operator_ports(self):
        from test_operator_boundary import operator_runtime
        for route in ("business", "customer", "operator"):
            with self.subTest(route=route), tempfile.TemporaryDirectory() as folder:
                fx = operator_runtime(folder) if route == "operator" else build_test_runtime(folder)
                self.addCleanup(fx.store.close)
                if route == "customer":
                    fx.world.mutate("case.completeness", "missing")
                clock = ConsumerClock(fx.clock)
                engine = WorkflowEngine(fx.profile, fx.world.bundle(), fx.store, clock)
                context = ExecutionContext.capture(clock.now() + timedelta(seconds=20), clock)
                if route == "operator":
                    with engine._entry_scope():
                        cp = engine.authenticate_and_bind(fx.request, fx.auth)
                    fx.store.save_checkpoint(cp.model_copy(update={"next_gate": "enqueue_handoff"}))
                original = fx.store.begin_dispatch
                reservations = []
                def reserve(*args, **kwargs):
                    lease = original(*args, **kwargs)
                    reservations.append(lease)
                    clock.advance(context.remaining_seconds(clock))
                    return lease
                fx.store.begin_dispatch = reserve
                port_name, method = {"business": ("scheduling", "reschedule"),
                    "customer": ("messaging", "send_clarification"),
                    "operator": ("operator", "enqueue_handoff")}[route]
                real = getattr(engine.gateway.bundle, port_name)
                entries = []
                class Port:
                    def __getattr__(self, name):
                        if name == method:
                            def forward(*args, **kwargs):
                                entries.append(args[0])
                                return getattr(real, name)(*args, **kwargs)
                            return forward
                        return getattr(real, name)
                engine.gateway.bundle = replace(engine.gateway.bundle, **{port_name: Port()})
                if route == "operator":
                    engine.recover("C1", fx.auth, execution=context)
                else:
                    engine.run(fx.request, fx.auth, execution=context)
                self.assertEqual(len(reservations), 1)
                self.assertEqual(entries, [], "Post-reservation expiry must not call any effect port")
                self.assertEqual(fx.world.effect_count(method), 0)
                lease = fx.store.entry(reservations[0].entry_id)
                self.assertEqual(lease.state, "active")
                self.assertGreaterEqual(fx.store.checkpoint("C1").budget.active_seconds, lease.reserved_seconds)
                self.assertIn(fx.store.intents("C1")[0].state, {"dispatching", "outcome_unknown"})

    def test_replay_expiry_after_real_disclosure_reservation_blocks_source_and_history(self):
        from proofkey.replay import ReplayService
        with tempfile.TemporaryDirectory() as folder:
            fx = build_test_runtime(folder)
            self.addCleanup(fx.store.close)
            self.assertEqual(fx.engine.run(fx.request, fx.auth).effects["reschedule"].status, "verified")
            saved = fx.store.saved_result("C1", "G1")
            clock = ConsumerClock(fx.clock)
            context = ExecutionContext.capture(clock.now() + timedelta(seconds=1), clock)
            original = fx.store.begin_disclosure_read
            reservations = []
            def reserve(*args):
                lease = original(*args)
                reservations.append(lease)
                clock.advance(context.remaining_seconds(clock))
                return lease
            fx.store.begin_disclosure_read = reserve
            real = fx.world.bundle().case
            entries = []
            class CasePort:
                def __getattr__(self, name): return getattr(real, name)
                def read_case(self, request):
                    entries.append(request)
                    return real.read_case(request)
            replay = ReplayService(fx.profile, replace(fx.world.bundle(), case=CasePort()), fx.store, clock)
            result = replay.lookup(fx.request, fx.auth, execution=context)
            self.assertEqual(entries, [], "Expired disclosure lease must not enter the source port")
            self.assertEqual(result.status, "denied")
            self.assertIsNone(result.binding)
            self.assertEqual(fx.store.saved_result("C1", "G1"), saved)
            self.assertEqual(fx.store.entry(reservations[0].entry_id).state, "active")

    def test_real_committed_control_reservation_expiry_never_enters_port_and_retains_debt(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = build_test_runtime(folder)
            self.addCleanup(fx.store.close)
            with fx.engine._entry_scope():
                cp = fx.engine.authenticate_and_bind(fx.request, fx.auth)
            clock = ConsumerClock(fx.clock)
            fx.engine.gateway.clock = clock
            context = ExecutionContext.capture(clock.now() + timedelta(seconds=1), clock)
            reservation = {}
            original = fx.store.begin_control_read
            def reserve(*args, **kwargs):
                reservation["lease"] = original(*args, **kwargs)
                clock.advance(context.remaining_seconds(clock))
                return reservation["lease"]
            fx.store.begin_control_read = reserve
            real_port = fx.engine.gateway.bundle.case
            entries = []
            class CasePort:
                def __getattr__(self, name): return getattr(real_port, name)
                def read_case(self, request):
                    entries.append(request)
                    return real_port.read_case(request)
            fx.engine.gateway.bundle = replace(fx.engine.gateway.bundle, case=CasePort())
            before = fx.store.checkpoint("C1")
            with fx.engine.gateway.execution_scope(context):
                with self.assertRaises(GateDenied):
                    fx.engine.gateway.authenticate_control(cp.binding, fx.auth, purpose="stop")
            self.assertEqual(entries, [], "A committed lease is not permission after the host cutoff")
            current = fx.store.checkpoint("C1")
            self.assertEqual(current.budget.tool_calls, before.budget.tool_calls + 1)
            self.assertEqual(current.budget.active_seconds,
                before.budget.active_seconds + reservation["lease"].reserved_seconds)
            self.assertEqual(fx.store.entry(reservation["lease"].entry_id).state, "active")

    def test_expired_context_blocks_all_four_engine_entries_before_auth_or_state(self):
        from test_waits import scoped_reply
        with tempfile.TemporaryDirectory() as folder:
            fx = build_test_runtime(folder)
            self.addCleanup(fx.store.close)
            fx.world.mutate("case.completeness", "missing")
            fx.engine.run(fx.request, fx.auth)
            reply = scoped_reply(fx)
            clock = ConsumerClock(fx.clock)
            engine = WorkflowEngine(fx.profile, fx.world.bundle(), fx.store, clock)
            context = ExecutionContext.capture(clock.now(), clock)
            before = fx.store.checkpoint("C1")
            calls = len(fx.world.calls)
            sentinel = fx.auth
            engine.gateway.auth = sentinel
            process = engine.process
            for action in (lambda: engine.run(fx.request, fx.auth, execution=context),
                lambda: engine.recover("C1", fx.auth, execution=context),
                lambda: engine.reply(reply, fx.auth, execution=context),
                lambda: engine.stop("C1", "G1", fx.auth, execution=context)):
                self.assertEqual(action().status, "denied")
                self.assertIs(engine.gateway.auth, sentinel)
                self.assertIs(engine.process, process)
                self.assertEqual(fx.store.checkpoint("C1"), before)
                self.assertEqual(len(fx.world.calls), calls)

    def test_full_gateway_pacing_must_fit_real_scoped_host_window_before_wait_or_debit(self):
        # Using the old case deadline for pacing wastes the host's last slice
        # even though the already-approved store refuses the later reservation.
        with tempfile.TemporaryDirectory() as folder:
            fx = build_test_runtime(folder)
            self.addCleanup(fx.store.close)
            with fx.engine._entry_scope():
                cp = fx.engine.authenticate_and_bind(fx.request, fx.auth)
            clock = ConsumerClock(fx.clock)
            fx.engine.gateway.clock = clock
            context = ExecutionContext.capture(clock.now() + timedelta(seconds=0.1), clock)
            before = fx.store.checkpoint("C1")
            calls = len(fx.world.calls)
            scope = (fx.engine.gateway.execution_scope(context) if hasattr(fx.engine.gateway, "execution_scope")
                     else fx.store.execution_scope(context, clock))
            with scope:
                with self.assertRaises((GateDenied, BudgetExceeded)):
                    fx.engine.gateway.authenticate_control(cp.binding, fx.auth, purpose="stop")
            self.assertEqual(clock.waits, [], "A required full delay exceeding the host cap must never begin")
            self.assertEqual(len(fx.world.calls), calls)
            self.assertEqual(fx.store.checkpoint("C1"), before)
