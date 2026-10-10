"""Packets request review only; operator facts are never customer consent."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from proofkey.adapters.world import SimulatedWorld
from proofkey.engine import WorkflowEngine
from proofkey.journal import CaseStore
from proofkey.identity import request_fingerprint, stable_action_id
from support import FakeClock, load_test_profile, make_auth, make_request


def operator_runtime(folder):
    """Public v1.3 composition; fixture source events are synthetic, not grants."""
    from types import SimpleNamespace
    root = Path(folder)
    profile, clock = load_test_profile("flat-v1.3"), FakeClock()
    world = SimulatedWorld(root / "world.sqlite", Path(__file__).resolve().parents[1] /
        "fixtures/development/packet-world-v1.json", profile=profile, clock=clock)
    store = CaseStore(root / "journal.sqlite")
    engine = WorkflowEngine(profile, world.bundle(), store, clock)
    return SimpleNamespace(profile=profile, clock=clock, world=world, store=store, engine=engine,
        request=make_request(), auth=make_auth())


def scoped_reply_for_record(fx, record):
    from proofkey.contracts import ScopedReply
    return ScopedReply(question_id=record.wait.question_id, binding=record.wait.binding,
        actor_id=record.wait.recipient, proof_reference="untrusted-reply-locator",
        request_revision=record.wait.binding.request_revision, consent_revision=record.wait.binding.consent_revision,
        owner_state_revision=record.owner_revision, fields={k: "untrusted fact" for k in record.wait.awaited_fields},
        received_at=fx.clock.now(), simulated=True)


class OperatorBoundaryTests(unittest.TestCase):
    def test_orphan_operator_pause_is_inspected_before_another_business_source_batch(self):
        class HostInterruption(BaseException):
            pass
        with tempfile.TemporaryDirectory() as folder:
            fx = operator_runtime(folder)
            self.addCleanup(fx.store.close)
            fx.world.mutate("scheduling.capacity", [])
            save = fx.store.create_wait_atomic
            def interrupt(record, now):
                save(record, now)
                raise HostInterruption("Labelled orphan pause envelope interruption")
            fx.store.create_wait_atomic = interrupt
            with self.assertRaises(HostInterruption):
                fx.engine.run(fx.request, fx.auth)
            cp = fx.store.checkpoint("C1")
            question_id = fx.engine.waits.question_id(cp.binding, operation="enqueue_handoff")
            saved = fx.store.load_wait_record(question_id)
            self.assertEqual(cp.phase, "window_gate")
            self.assertEqual(cp.next_gate, "reschedule")
            self.assertEqual(fx.store.intents("C1"), ())
            before = len(fx.world.calls)
            fx.store.create_wait_atomic = save
            fx.engine.recover("C1", fx.auth)
            later = fx.world.calls[before:]
            self.assertFalse(any(call.operation == "list_permitted_slots" for call in later),
                "Orphan operator original must be inspected before repeating failed business assembly")
            self.assertEqual(fx.store.load_wait_record(question_id), saved)
            self.assertEqual(fx.world.effect_count("reschedule"), 0)
            self.assertLessEqual(fx.store.checkpoint("C1").budget.tool_calls, 24)

    def test_unknown_operator_communication_uses_only_original_read_before_reply(self):
        from test_waits import scoped_reply
        with tempfile.TemporaryDirectory() as folder:
            fx = operator_runtime(folder)
            self.addCleanup(fx.store.close)
            enqueue = fx.engine.bundle.operator.enqueue_handoff
            def timeout_original_after_commit(intent, *, deadline=None):
                result = enqueue(intent, deadline=deadline)
                fx.world.set_fault("read_receipt", "timeout_before")
                return result
            fx.engine.bundle.operator.enqueue_handoff = timeout_original_after_commit
            with fx.engine._entry_scope():
                cp = fx.engine.authenticate_and_bind(fx.request, fx.auth)
            fx.store.save_checkpoint(cp.model_copy(update={"next_gate": "enqueue_handoff"}))
            first = fx.engine.recover("C1", fx.auth)
            self.assertEqual(first.handoff_status, "outcome_unknown")
            self.assertEqual(fx.world.effect_count("enqueue_handoff"), 1)
            reply = scoped_reply(fx)
            operator = make_auth(caller_id="OP1", proof_reference="synthetic-operator-proof")
            self.assertEqual(fx.engine.reply(reply, operator).status, "denied")
            self.assertEqual(fx.store.load_wait_record(reply.question_id).lifecycle, "pending")
            fx.world.set_fault("read_receipt", "none")
            before = len(fx.world.calls)
            # OP facts authentication is not an original-disclosure grant.
            # A separately authorized U1 host read establishes sent evidence.
            fx.engine.gateway.auth = fx.auth
            self.assertEqual(fx.engine.gateway.reconcile_read_only(
                fx.store.load_wait_record(reply.question_id).communication_action_id).status, "verified")
            self.assertEqual(fx.engine.reply(reply, operator).status, "authorized")
            self.assertEqual(len(fx.world.calls) - before, 5)  # 1 exact original + 4 reply reads.
            self.assertEqual(fx.world.effect_count("enqueue_handoff"), 1)
            self.assertEqual(fx.world.effect_count("reschedule"), 0)

    def test_operator_wait_expiry_and_stop_never_consume_or_resend(self):
        from test_waits import scoped_reply
        for fence in ("expiry", "stop", "reply_read_stop_race"):
            with self.subTest(fence=fence), tempfile.TemporaryDirectory() as folder:
                fx = self.start_operator(folder)
                reply = scoped_reply(fx)
                saved = fx.store.load_wait_record(reply.question_id)
                if fence == "expiry":
                    fx.clock.advance(120)
                    expired = fx.engine.waits.expire(reply.question_id)
                    self.assertEqual((expired.phase, expired.next_gate), ("expired", "enqueue_handoff"))
                elif fence == "stop":
                    stopped = fx.engine.stop("C1", reply.binding.generation, fx.auth)
                    self.assertTrue(stopped.stop.requested)
                else:
                    read = fx.engine.bundle.case.read_case
                    def stop_after_read(request):
                        result = read(request)
                        current = fx.store.checkpoint("C1")
                        fx.store.stop_waits_atomic(current.binding, current)
                        return result
                    fx.engine.bundle.case.read_case = stop_after_read
                self.assertEqual(fx.engine.reply(reply, make_auth(caller_id="OP1", proof_reference="synthetic-operator-proof")).status, "denied")
                self.assertNotEqual(fx.store.load_wait_record(reply.question_id).lifecycle, "answered")
                self.assertEqual(fx.store.load_wait_record(reply.question_id).communication_intent, saved.communication_intent)
                self.assertEqual(fx.world.effect_count("enqueue_handoff"), 1)
                self.assertEqual(fx.world.effect_count("reschedule"), 0)

    def test_finite_tool_budget_does_not_create_partial_operator_question(self):
        from proofkey.policy import GateDenied
        with tempfile.TemporaryDirectory() as folder:
            fx = operator_runtime(folder)
            self.addCleanup(fx.store.close)
            with fx.engine._entry_scope():
                cp = fx.engine.authenticate_and_bind(fx.request, fx.auth)
            # Five real ordinary four-source host reads after three bootstrap
            # reads consume23 tools, not a fabricated/reset accounting ledger.
            for _ in range(5):
                fx.engine.gateway.read_reply_sources(cp.binding, fx.auth, recipient_role="customer")
            current = fx.store.checkpoint("C1")
            self.assertEqual(current.budget.tool_calls, 23)
            with self.assertRaises(GateDenied):
                fx.engine.waits.create(current, ["case.operator_facts"])
            self.assertEqual(fx.store.checkpoint("C1").budget.tool_calls, 24)
            self.assertEqual(fx.store.intents("C1"), ())
            self.assertIsNone(fx.store.checkpoint("C1").question_id)
            self.assertEqual(fx.world.effect_count("enqueue_handoff"), 0)

    def test_operator_pause_at_real_physical_origin_queues_without_conceptual_jump(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = operator_runtime(folder)
            self.addCleanup(fx.store.close)
            fx.world.mutate("scheduling.capacity", [])
            result = fx.engine.run(fx.request, fx.auth)
            current = fx.store.checkpoint("C1")
            self.assertEqual(current.phase, "wait_operator")
            self.assertEqual(fx.world.effect_count("enqueue_handoff"), 1)
            self.assertEqual(fx.world.effect_count("reschedule"), 0)
            record = fx.store.load_wait_record(current.question_id)
            self.assertEqual(record.wait.origin, "window_gate")
            self.assertEqual(record.origin_checkpoint.phase, "window_gate")
            self.assertEqual(record.communication_intent, fx.store.intent(record.communication_action_id).intent)
            self.assertEqual(current.budget.clarifications, 0)
            self.assertEqual(result.handoff_status, "pending")

    def test_operator_reply_scope_and_current_metadata_changes_deny_without_consume(self):
        from test_waits import scoped_reply
        mutations = (("case.question_revision", "v2"), ("operator.recipient", "U1"),
            ("ownership.owner", "OP1"), ("ownership.state_revision", "v2"),
            ("ownership.epoch", 1), ("customer.consent_revision", "v2"))
        for key, value in mutations:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as folder:
                fx = self.start_operator(folder)
                reply = scoped_reply(fx)
                fx.world.mutate(key, value)
                operator = make_auth(caller_id="OP1", proof_reference="synthetic-operator-proof")
                self.assertEqual(fx.engine.reply(reply, operator).status, "denied")
                self.assertEqual(fx.store.load_wait_record(reply.question_id).lifecycle, "pending")
                self.assertEqual(fx.world.effect_count("enqueue_handoff"), 1)
                self.assertEqual(fx.world.effect_count("reschedule"), 0)
        for change in ({"actor_id": "U1"}, {"fields": {"customer.confirmation": True}}):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as folder:
                fx = self.start_operator(folder)
                reply = scoped_reply(fx, **change)
                before = len(fx.world.calls)
                self.assertEqual(fx.engine.reply(reply, make_auth(caller_id="OP1", proof_reference="synthetic-operator-proof")).status, "denied")
                self.assertEqual(len(fx.world.calls), before)
                self.assertEqual(fx.store.load_wait_record(reply.question_id).lifecycle, "pending")

    def test_operator_prepared_unsent_reply_denies_and_recovery_keeps_original(self):
        from test_waits import scoped_reply
        class HostInterruption(BaseException):
            pass
        with tempfile.TemporaryDirectory() as folder:
            fx = operator_runtime(folder)
            self.addCleanup(fx.store.close)
            with fx.engine._entry_scope():
                cp = fx.engine.authenticate_and_bind(fx.request, fx.auth)
            fx.store.save_checkpoint(cp.model_copy(update={"next_gate": "enqueue_handoff"}))
            prepare = fx.store.prepare
            def interrupt(intent):
                prepare(intent)
                raise HostInterruption("Labelled prepared-state host interruption")
            fx.store.prepare = interrupt
            try:
                fx.engine.recover("C1", fx.auth)
            except HostInterruption:
                pass
            question_id = fx.engine.waits.question_id(cp.binding, operation="enqueue_handoff")
            saved = fx.store.load_wait_record(question_id)
            intent = fx.store.intent(saved.communication_action_id)
            self.assertEqual(intent.state, "prepared")
            self.assertEqual(fx.store.checkpoint("C1").phase, "intake")
            self.assertIsNone(fx.store.checkpoint("C1").question_id)
            self.assertEqual(fx.world.effect_count("enqueue_handoff"), 0)
            # Explicit saved wait-phase projection to exercise unsent rejection,
            # not evidence of a legitimate wait-phase transition.
            origin = fx.store.checkpoint("C1")
            fx.store.save_checkpoint(origin.model_copy(update={"phase": saved.wait_phase,
                "question_id": question_id, "awaited_fields": saved.wait.awaited_fields,
                "next_gate": saved.accept_edge.operation}))
            self.assertEqual(fx.engine.reply(scoped_reply(fx), make_auth(caller_id="OP1", proof_reference="synthetic-operator-proof")).status, "denied")
            fx.store.save_checkpoint(origin)
            fx.store.prepare = prepare
            fx.clock.advance(2)
            fx.engine.recover("C1", fx.auth)
            self.assertEqual(fx.store.intent(saved.communication_action_id).intent, intent.intent)
            self.assertEqual(fx.store.load_wait_record(question_id), saved)
            self.assertEqual(fx.world.effect_count("enqueue_handoff"), 1)

    def test_real_operator_hard_exits_reopen_retained_original_and_consumed_reply(self):
        # Real process exits, distinct from prepared-state host simulation.
        for boundary, exit_code in (("envelope", 81), ("provider", 82), ("consume", 83)):
            with self.subTest(boundary=boundary), tempfile.TemporaryDirectory() as folder:
                script = """
import os, sys
from test_operator_boundary import operator_runtime
from test_waits import scoped_reply
from support import make_auth
fx=operator_runtime(sys.argv[1]); boundary=sys.argv[2]; code=int(sys.argv[3])
if boundary=='envelope':
    original=fx.store.create_wait_atomic
    def die(record, now):
        original(record, now); os._exit(code)
    fx.store.create_wait_atomic=die
elif boundary=='provider':
    original=fx.engine.bundle.operator.enqueue_handoff
    def die(request, *, deadline=None):
        original(request, deadline=deadline); os._exit(code)
    fx.engine.bundle.operator.enqueue_handoff=die
with fx.engine._entry_scope():
    cp=fx.engine.authenticate_and_bind(fx.request,fx.auth)
fx.store.save_checkpoint(cp.model_copy(update={'next_gate':'enqueue_handoff'}))
fx.engine.recover('C1',fx.auth)
if boundary=='consume':
    original=fx.store.consume_wait_reply_atomic
    def die(*args):
        original(*args); os._exit(code)
    fx.store.consume_wait_reply_atomic=die
    fx.engine.reply(scoped_reply(fx),make_auth(caller_id='OP1',proof_reference='synthetic-operator-proof'))
"""
                child = subprocess.run([sys.executable, "-c", script, folder, boundary, str(exit_code)], capture_output=True, text=True)
                self.assertEqual(child.returncode, exit_code, child.stderr)
                fx = operator_runtime(folder)
                self.addCleanup(fx.store.close)
                fx.clock.advance(2)
                cp = fx.store.checkpoint("C1")
                question_id = fx.engine.waits.question_id(cp.binding, operation="enqueue_handoff")
                saved = fx.store.load_wait_record(question_id)
                original_intent = saved.communication_intent
                if boundary == "envelope":
                    self.assertEqual(fx.store.intents("C1"), ())
                    self.assertEqual(fx.world.effect_count("enqueue_handoff"), 0)
                else:
                    self.assertEqual(fx.world.effect_count("enqueue_handoff"), 1)
                if boundary == "consume":
                    self.assertEqual(saved.lifecycle, "answered")
                    self.assertEqual(cp.observations, [])
                    self.assertEqual(cp.phase, "operator_facts")
                    calls = len(fx.world.calls)
                    reply = scoped_reply_for_record(fx, saved)
                    self.assertEqual(fx.engine.reply(reply, make_auth(caller_id="OP1", proof_reference="synthetic-operator-proof")).status, "denied")
                    self.assertEqual(len(fx.world.calls), calls)
                    fx.engine.recover("C1", fx.auth)
                    self.assertLessEqual(fx.store.checkpoint("C1").budget.tool_calls, 24)
                else:
                    def forbid(*args):
                        self.fail("Saved original must not gain a reconstructed wait")
                    fx.store.create_wait_atomic = forbid
                    fx.engine.recover("C1", fx.auth)
                    self.assertEqual(fx.store.checkpoint("C1").question_id, question_id)
                    self.assertEqual(fx.store.load_wait_record(question_id), saved)
                self.assertEqual(fx.world.effect_count("enqueue_handoff"), 1)
                self.assertEqual(fx.world.effect_count("reschedule"), 0)
                self.assertEqual(fx.store.intent(saved.communication_action_id).intent, original_intent)

    def start_operator(self, folder):
        fx = operator_runtime(folder)
        self.addCleanup(fx.store.close)
        with fx.engine._entry_scope():
            cp = fx.engine.authenticate_and_bind(fx.request, fx.auth)
        fx.store.save_checkpoint(cp.model_copy(update={"next_gate": "enqueue_handoff"}))
        fx.engine.recover("C1", fx.auth)
        return fx

    def test_true_operator_recipient_reply_is_one_use_untrusted_facts_not_customer_consent(self):
        from test_waits import scoped_reply
        for consent in ("granted", "denied", "unknown"):
            with self.subTest(consent=consent), tempfile.TemporaryDirectory() as folder:
                fx = self.start_operator(folder)
                record = fx.store.load_wait_record(fx.store.checkpoint("C1").question_id)
                fx.world.mutate("customer.consent", consent)
                reply = scoped_reply(fx, fields={"case.operator_facts": {"consent": "granted", "confirmed": True}})
                operator = make_auth(caller_id="OP1", proof_reference="synthetic-operator-proof")
                before = len(fx.world.calls)
                result = fx.engine.reply(reply, operator)
                self.assertEqual(result.status, "authorized", "Recorded matching OP facts should be consumed, not mistaken for customer payload")
                consumed = fx.store.load_wait_record(reply.question_id)
                self.assertEqual(consumed.lifecycle, "answered")
                self.assertEqual(consumed.accepted_actor, "OP1")
                self.assertEqual(fx.world.effect_count("reschedule"), 0)
                self.assertEqual(fx.world.effect_count("enqueue_handoff"), 1)
                self.assertEqual(fx.store.original_request("C1", reply.binding.generation), fx.request)
                self.assertFalse(any(o.authority == "customer" and o.fact in {"consent", "confirmation"}
                    for o in fx.store.checkpoint("C1").observations))
                self.assertEqual(len(fx.world.calls) - before, 4)
                self.assertEqual(fx.store.checkpoint("C1").phase, "completeness")
                calls = len(fx.world.calls)
                self.assertEqual(fx.engine.reply(reply, operator).status, "denied")
                self.assertEqual(len(fx.world.calls), calls)
                self.assertEqual(consumed.communication_intent, record.communication_intent)

    def test_selected_operator_communication_creates_exact_durable_question_before_dispatch(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = operator_runtime(folder)
            self.addCleanup(fx.store.close)
            with fx.engine._entry_scope():
                cp = fx.engine.authenticate_and_bind(fx.request, fx.auth)
            fx.store.save_checkpoint(cp.model_copy(update={"next_gate": "enqueue_handoff"}))
            result = fx.engine.recover("C1", fx.auth)
            current = fx.store.checkpoint("C1")
            self.assertEqual(fx.world.effect_count("enqueue_handoff"), 1,
                "Selected physical wait edge must queue a real packet, not a conceptual wait")
            self.assertEqual(current.phase, "wait_operator")
            self.assertEqual(current.awaited_fields, ["case.operator_facts"])
            self.assertEqual(current.question_id, "question:" + stable_action_id(current.binding, "enqueue_handoff", "enqueue"))
            saved = fx.store.load_wait_record(current.question_id)
            communication = fx.store.intent(saved.communication_action_id)
            self.assertEqual(saved.communication_intent, communication.intent)
            self.assertEqual(saved.recipient_role, "operator")
            self.assertEqual(saved.wait.recipient, "OP1")
            self.assertEqual(saved.communication_stage, "enqueue")
            self.assertEqual(saved.wait.origin, "intake")
            self.assertEqual(saved.origin_checkpoint.phase, "intake")
            self.assertEqual(saved.origin_checkpoint.budget.clarifications, 0)
            self.assertEqual(current.budget.tool_calls, 14)  # 3 initial + 3 recover + 8 packet.
            self.assertEqual(current.budget.tool_calls, len(fx.world.calls))
            self.assertEqual(result.handoff_status, "pending")
            self.assertEqual(fx.world.effect_count("reschedule"), 0)

    def test_nonwait_service_handoff_uses_dynamic_packet_and_keeps_owner_pending(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            profile, clock = load_test_profile("flat-v1.3"), FakeClock()
            world = SimulatedWorld(root / "world.sqlite", Path(__file__).resolve().parents[1] /
                "fixtures/development/packet-world-v1.json", profile=profile, clock=clock)
            request = make_request(kind="service_refusal", consent_mode="unknown", arguments={"scope": "service"})
            world.mutate("delivery.status", "completed")
            world.mutate("customer.consent_mode", "unknown")
            world.mutate("customer.request_fingerprint", request_fingerprint(request))
            store = CaseStore(root / "journal.sqlite")
            self.addCleanup(store.close)
            engine = WorkflowEngine(profile, world.bundle(), store, clock)
            result = engine.run(request, make_auth())
            self.assertEqual(world.effect_count("enqueue_handoff"), 1,
                "Service handoff must call the owned dynamic entry with a registered disposition")
            self.assertEqual(result.effects["register_service_refusal"].status, "verified")
            self.assertEqual(result.handoff_status, "pending")
            self.assertIsNone(store.checkpoint("C1").question_id)
            intent = next(record.intent for record in store.intents("C1") if record.intent.operation == "enqueue_handoff")
            self.assertEqual(intent.arguments["content"]["disposition"], "review_facts")
            # Three bootstrap + seven service business + eight dynamic packet tools.
            self.assertEqual(store.checkpoint("C1").budget.tool_calls, 18)
            self.assertNotIn("content", result.effects["enqueue_handoff"].model_dump())

    def test_true_dynamic_operator_wait_denies_before_free_batch_or_synthetic_question(self):
        from support import build_test_runtime
        from proofkey.policy import GateDenied
        with tempfile.TemporaryDirectory() as folder:
            fx = build_test_runtime(folder)
            self.addCleanup(fx.store.close)
            fx.engine.gateway.auth = fx.auth
            fx.engine.gateway.bind_request(fx.request, fx.clock.now().replace(hour=11), initialize_process=True)
            checkpoint = fx.store.checkpoint("C1")
            self.assertTrue(hasattr(fx.engine, "waits"), "Engine needs the same gateway-owned wait service")
            before = len(fx.world.calls)
            with self.assertRaises(GateDenied):
                fx.engine.waits.create(checkpoint, ["case.operator_facts"])
            self.assertEqual(len(fx.world.calls), before)
            self.assertEqual(fx.store.intents("C1"), ())
            self.assertIsNone(fx.store.checkpoint("C1").question_id)

    def test_saved_phase_simulation_operator_facts_reenters_source_gate_without_consent(self):
        # Saved-phase simulation only: no claim of supported true operator creation.
        from support import build_test_runtime
        with tempfile.TemporaryDirectory() as folder:
            fx = build_test_runtime(folder)
            self.addCleanup(fx.store.close)
            with fx.engine._entry_scope():
                checkpoint = fx.engine.authenticate_and_bind(fx.request, fx.auth)
                operator = make_auth(caller_id="OP1", proof_reference="synthetic-operator-proof")
                observations = fx.engine.gateway.read_reply_sources(checkpoint.binding, operator, recipient_role="operator")
                current = fx.store.checkpoint("C1")
                fx.store.save_checkpoint(current.model_copy(update={"phase": "operator_facts",
                    "next_gate": "reenter_facts", "observations": list(observations)}))
                fx.engine.gateway.auth = operator
                result = fx.engine._drive(fx.store.checkpoint("C1"), fx.request, operator)
            self.assertEqual(result.status, "authorized")
            self.assertEqual(fx.world.effect_count("reschedule"), 0)
            self.assertFalse(any(o.authority == "customer" and o.fact in {"consent", "confirmation"}
                for o in fx.store.checkpoint("C1").observations))
            self.assertEqual(fx.store.checkpoint("C1").phase, "wait_operator")
