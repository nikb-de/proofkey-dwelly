"""Public customer waits; source events below are explicitly simulated."""
from datetime import timedelta
from dataclasses import replace
import threading
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest

from proofkey.contracts import ScopedReply
from support import build_test_runtime, make_auth, make_request


def scoped_reply(fx, **changes):
    checkpoint = fx.store.checkpoint("C1")
    wait = fx.store.load_wait_record(checkpoint.question_id)
    data = dict(question_id=wait.wait.question_id, binding=wait.wait.binding,
        actor_id=wait.wait.recipient, proof_reference="untrusted-reply-locator",
        request_revision=wait.wait.binding.request_revision,
        consent_revision=wait.wait.binding.consent_revision,
        owner_state_revision=wait.owner_revision,
        fields={key: "untrusted supplied fact" for key in wait.wait.awaited_fields},
        received_at=fx.clock.now(), simulated=True)
    return ScopedReply.model_validate({**data, **changes})


class WaitTests(unittest.TestCase):
    def test_uncontended_customer_and_true_operator_attach_only_four_read_source_batch(self):
        from test_operator_boundary import operator_runtime
        for role in ("customer", "operator"):
            with self.subTest(role=role), tempfile.TemporaryDirectory() as folder:
                if role == "customer":
                    fx = self.fixture(folder)
                    fx.world.mutate("case.completeness", "missing")
                    fx.engine.run(fx.request, fx.auth)
                    auth = fx.auth
                else:
                    fx = operator_runtime(folder)
                    self.addCleanup(fx.store.close)
                    # Explicit trusted-host selection at the physical origin;
                    # no saved fake wait, provider receipt or free source batch.
                    with fx.engine._entry_scope():
                        cp = fx.engine.authenticate_and_bind(fx.request, fx.auth)
                    fx.store.save_checkpoint(cp.model_copy(update={"next_gate": "enqueue_handoff"}))
                    fx.engine.recover("C1", fx.auth)
                    auth = make_auth(caller_id="OP1", proof_reference="synthetic-operator-proof")
                reply = scoped_reply(fx)
                captured = {}
                real = fx.store.attach_wait_reply_sources_atomic
                def attach(question, expected, observations):
                    captured["expected"] = expected
                    captured["sources"] = list(observations)
                    captured["receipt"] = fx.store.load_wait_record(question)
                    captured["attached"] = real(question, expected, observations)
                    return captured["attached"]
                fx.store.attach_wait_reply_sources_atomic = attach
                calls = len(fx.world.calls)
                self.assertEqual(fx.engine.reply(reply, auth).status, "authorized")
                self.assertEqual(captured["attached"].model_copy(update={"observations": []}),
                    captured["expected"])
                self.assertEqual(captured["attached"].observations, captured["sources"])
                self.assertEqual(len(captured["sources"]), 12)
                self.assertEqual(captured["expected"].observations, [])
                self.assertEqual(fx.store.load_wait_record(reply.question_id), captured["receipt"])
                self.assertEqual(captured["receipt"].accepted_reply, reply)
                self.assertEqual(len(fx.world.calls) - calls, 4)
                self.assertEqual(fx.world.effect_count("reschedule"), 0)
                self.assertFalse(any(o.authority == "customer" and o.fact in {"consent", "confirmation"}
                    for o in captured["sources"]))

    def test_public_stop_after_consume_preserves_exact_newer_control_at_source_attachment(self):
        # Removing the atomic expected-current attachment resurrects the stale
        # completeness phase after a lawful second host has finished stop.
        from proofkey.engine import WorkflowEngine
        from proofkey.journal import CaseStore
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder)
            fx.world.mutate("case.completeness", "missing")
            fx.engine.run(fx.request, fx.auth)
            reply = scoped_reply(fx)
            stopped = {}

            def concurrent_stop():
                try:
                    with_store = CaseStore(Path(folder) / "journal.sqlite")
                    try:
                        engine = WorkflowEngine(fx.profile, fx.world.bundle(), with_store, fx.clock)
                        stopped["result"] = engine.stop("C1", "G1", fx.auth)
                        stopped["checkpoint"] = with_store.checkpoint("C1")
                    finally:
                        with_store.close()
                except Exception as error:
                    stopped["error"] = error

            def pause_then_forward(real, *args):
                consumed = fx.store.checkpoint("C1")
                self.assertEqual((consumed.phase, consumed.next_gate, consumed.budget.tool_calls),
                    ("completeness", "authenticate", 15))
                self.assertEqual(consumed.observations, [])
                self.assertEqual(fx.store.load_wait_record(reply.question_id).lifecycle, "answered")
                worker = threading.Thread(target=concurrent_stop)
                worker.start()
                worker.join(5)
                self.assertFalse(worker.is_alive(), "Second creator-owned host must finish its public stop")
                if "error" in stopped:
                    raise stopped["error"]
                self.assertEqual(stopped["result"].status, "authorized")
                self.assertEqual((stopped["checkpoint"].phase, stopped["checkpoint"].next_gate),
                    ("stopped", "stopped"))
                return real(*args)

            # RED forwards the genuine old source-only save, not a fake result.
            # GREEN pauses at the public atomic attachment's transaction entry.
            if hasattr(fx.store, "attach_wait_reply_sources_atomic"):
                real = fx.store.attach_wait_reply_sources_atomic
                fx.store.attach_wait_reply_sources_atomic = lambda *args: pause_then_forward(real, *args)
            else:
                real = fx.store.save_checkpoint
                def save(value):
                    if (value.phase == "completeness" and value.observations
                            and fx.store.load_wait_record(reply.question_id).lifecycle == "answered"):
                        return pause_then_forward(real, value)
                    return real(value)
                fx.store.save_checkpoint = save

            before_calls = len(fx.world.calls)
            result = fx.engine.reply(reply, fx.auth)
            self.assertEqual(fx.store.checkpoint("C1"), stopped["checkpoint"],
                "Source attachment must not overwrite the completed public stop's exact checkpoint")
            self.assertEqual(result.status, "denied")
            self.assertEqual([call.operation for call in fx.world.calls[before_calls:]],
                ["read_case", "read_principal", "read_owner", "read_message", "read_case"])
            answered = fx.store.load_wait_record(reply.question_id)
            self.assertEqual((answered.lifecycle, answered.accepted_reply), ("answered", reply))
            self.assertEqual(stopped["checkpoint"].budget.tool_calls, 16)
            self.assertEqual(fx.world.effect_count("send_clarification"), 1)
            self.assertEqual(fx.world.effect_count("reschedule"), 0)
            self.assertIsNone(fx.store.saved_result("C1", "G1"))
            reopened = CaseStore(Path(folder) / "journal.sqlite")
            try:
                self.assertEqual(reopened.checkpoint("C1"), stopped["checkpoint"])
                self.assertEqual(reopened.load_wait_record(reply.question_id), answered)
            finally:
                reopened.close()
            before_duplicate = len(fx.world.calls)
            self.assertEqual(fx.engine.reply(reply, fx.auth).status, "denied")
            self.assertEqual(len(fx.world.calls), before_duplicate)

    def fixture(self, folder):
        fx = build_test_runtime(folder)
        self.addCleanup(fx.store.close)
        return fx

    def test_customer_wait_then_fresh_source_event_and_reply_completes_with_23_tools(self):
        # Missing durable pre-send question or bootstrap on reply breaks this route.
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder)
            fx.world.mutate("case.completeness", "missing")
            first = fx.engine.run(fx.request, fx.auth)
            checkpoint = fx.store.checkpoint("C1")
            self.assertEqual(checkpoint.phase, "wait_customer")
            self.assertEqual(first.wait_status, "pending")
            self.assertEqual(fx.world.effect_count("send_clarification"), 1)
            self.assertEqual(checkpoint.budget.clarifications, 1)
            reply = scoped_reply(fx)
            # Independent synthetic source completion; reply cannot mutate this.
            fx.world.mutate("case.completeness", "complete")
            result = fx.engine.reply(reply, fx.auth)
            self.assertEqual(result.effects["reschedule"].status, "verified")
            self.assertEqual(fx.world.effect_count("reschedule"), 1)
            self.assertEqual(fx.store.checkpoint("C1").budget.tool_calls, 23)
            self.assertEqual(len(fx.world.calls), 23)
            self.assertEqual(fx.store.load_wait_record(reply.question_id).lifecycle, "answered")
            self.assertEqual(fx.store.original_request("C1", result.binding.generation), fx.request)

    def test_reply_body_cannot_make_source_complete_or_create_permission(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder)
            fx.world.mutate("case.completeness", "missing")
            fx.engine.run(fx.request, fx.auth)
            self.assertIsNotNone(fx.store.checkpoint("C1").question_id,
                "A customer wait requires an immutable question before reply")
            reply = scoped_reply(fx, fields={"case.missing_facts": {"case.completeness": "complete",
                "customer.consent": "granted", "customer.confirmation": "verified"}})
            result = fx.engine.reply(reply, fx.auth)
            self.assertEqual(result.status, "authorized")
            self.assertEqual(fx.world.effect_count("reschedule"), 0)
            self.assertEqual(fx.store.load_wait_record(reply.question_id).accepted_reply, reply)
            self.assertFalse(any(o.authority == "customer" and o.fact == "confirmation"
                for o in fx.store.checkpoint("C1").observations))

    def test_invalid_scoped_replies_cannot_consume_or_rewrite_pending_wait(self):
        changes = ({"question_id": "foreign"}, {"actor_id": "OP1"},
            {"fields": {"customer.consent": "granted"}}, {"request_revision": "v2"},
            {"consent_revision": "v2"}, {"owner_state_revision": "v2"},
            {"received_at": "2027-01-01T00:00:00Z"}, {"received_at": "2025-01-01T00:00:00Z"})
        for change in changes:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as folder:
                fx = self.fixture(folder)
                fx.world.mutate("case.completeness", "missing")
                fx.engine.run(fx.request, fx.auth)
                record = fx.store.load_wait_record(fx.store.checkpoint("C1").question_id)
                before = len(fx.world.calls)
                result = fx.engine.reply(scoped_reply(fx, **change), fx.auth)
                self.assertEqual(result.status, "denied")
                self.assertEqual(fx.store.load_wait_record(record.wait.question_id).lifecycle, "pending")
                self.assertEqual(len(fx.world.calls), before)
                self.assertEqual(fx.world.effect_count("reschedule"), 0)

    def test_current_metadata_changes_deny_without_consuming(self):
        changes = (("case.question_revision", "v2"), ("customer.consent_revision", "v2"),
            ("ownership.owner", "OP1"), ("ownership.state_revision", "v2"),
            ("ownership.epoch", 1), ("messaging.recipient", "OP1"))
        for key, value in changes:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as folder:
                fx = self.fixture(folder)
                fx.world.mutate("case.completeness", "missing")
                fx.engine.run(fx.request, fx.auth)
                reply = scoped_reply(fx)
                fx.world.mutate(key, value)
                result = fx.engine.reply(reply, fx.auth)
                self.assertEqual(result.status, "denied")
                self.assertEqual(fx.store.load_wait_record(reply.question_id).lifecycle, "pending")
                self.assertEqual(fx.world.effect_count("reschedule"), 0)
                self.assertGreater(fx.store.checkpoint("C1").budget.tool_calls, 11)

    def test_bad_auth_locator_is_not_reply_authentication(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder)
            fx.world.mutate("case.completeness", "missing")
            fx.engine.run(fx.request, fx.auth)
            reply = scoped_reply(fx)
            result = fx.engine.reply(reply, make_auth(proof_reference=reply.proof_reference))
            self.assertEqual(result.status, "denied")
            self.assertEqual(fx.store.load_wait_record(reply.question_id).lifecycle, "pending")
            self.assertEqual(fx.store.checkpoint("C1").budget.tool_calls, 12)

    def test_expiry_only_advances_declared_successor_without_side_effect(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder)
            fx.world.mutate("case.completeness", "missing")
            fx.engine.run(fx.request, fx.auth)
            reply = scoped_reply(fx)
            record = fx.store.load_wait_record(reply.question_id)
            self.assertEqual(record.wait.expires_at, fx.store.checkpoint("C1").deadline)
            fx.clock.advance(120)
            calls = len(fx.world.calls)
            expired = fx.engine.waits.expire(reply.question_id)
            self.assertEqual((expired.phase, expired.next_gate), ("expired", "enqueue_handoff"))
            self.assertEqual(len(fx.world.calls), calls)
            self.assertEqual(fx.engine.reply(reply, fx.auth).status, "denied")
            self.assertEqual(fx.store.load_wait_record(reply.question_id).lifecycle, "expired")

    def test_duplicate_reply_does_not_repeat_effect_or_consume_new_reads(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder)
            fx.world.mutate("case.completeness", "missing")
            fx.engine.run(fx.request, fx.auth)
            reply = scoped_reply(fx)
            fx.world.mutate("case.completeness", "complete")
            fx.engine.reply(reply, fx.auth)
            calls = len(fx.world.calls)
            self.assertEqual(fx.engine.reply(reply, fx.auth).status, "denied")
            self.assertEqual(len(fx.world.calls), calls)
            self.assertEqual(fx.world.effect_count("reschedule"), 1)

    def test_reply_entry_guard_precedes_gateway_auth_mutation(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder)
            fx.world.mutate("case.completeness", "missing")
            fx.engine.run(fx.request, fx.auth)
            reply = scoped_reply(fx)
            old_auth = fx.engine.gateway.auth
            foreign = make_auth(proof_reference="foreign")
            returned = []
            thread = threading.Thread(target=lambda: returned.append(fx.engine.reply(reply, foreign)))
            thread.start(); thread.join()
            self.assertEqual(returned[0].status, "denied")
            with fx.engine._entry_scope():
                self.assertEqual(fx.engine.reply(reply, foreign).status, "denied")
            self.assertEqual(fx.engine.gateway.auth, old_auth)

    def test_real_process_exit_after_wait_persistence_resumes_original_question(self):
        # Actual os._exit, followed by SQLite reopen; no simulated phase label.
        with tempfile.TemporaryDirectory() as folder:
            script = """
import os, sys
from support import build_test_runtime
fx=build_test_runtime(sys.argv[1])
fx.world.mutate('case.completeness', 'missing')
old=fx.store.create_wait_atomic
def die(record, now):
    old(record, now)
    os._exit(71)
fx.store.create_wait_atomic=die
fx.engine.run(fx.request, fx.auth)
"""
            process = subprocess.run([sys.executable, "-c", script, folder], capture_output=True, text=True)
            self.assertEqual(process.returncode, 71, process.stderr)
            fx = self.fixture(folder)
            fx.clock.advance(2)
            question_id = fx.engine.waits.question_id(fx.store.checkpoint("C1").binding)
            original = fx.store.load_wait_record(question_id)
            self.assertEqual(fx.store.intents("C1"), ())
            result = fx.engine.recover("C1", fx.auth)
            self.assertEqual(fx.world.effect_count("send_clarification"), 1,
                "Reopen must find pre-transport question and prepare only its original payload")
            self.assertEqual(fx.store.checkpoint("C1").question_id, question_id)
            self.assertEqual(fx.store.load_wait_record(question_id).wait, original.wait)
            self.assertEqual(fx.store.checkpoint("C1").budget.clarifications, 1)

    def test_real_process_exit_after_message_commit_recovers_only_original_read(self):
        with tempfile.TemporaryDirectory() as folder:
            script = """
import os, sys
from dataclasses import replace
from support import build_test_runtime
fx=build_test_runtime(sys.argv[1])
fx.world.mutate('case.completeness', 'missing')
real=fx.engine.gateway.bundle.messaging
class ExitMessaging:
    def __getattr__(self, name): return getattr(real, name)
    def send_clarification(self, intent, *, deadline):
        real.send_clarification(intent, deadline=deadline)
        os._exit(72)
fx.engine.gateway.bundle=replace(fx.engine.gateway.bundle, messaging=ExitMessaging())
fx.engine.run(fx.request, fx.auth)
"""
            process = subprocess.run([sys.executable, "-c", script, folder], capture_output=True, text=True)
            self.assertEqual(process.returncode, 72, process.stderr)
            fx = self.fixture(folder)
            fx.clock.advance(2)
            intent = fx.store.intents("C1")[0].intent
            result = fx.engine.recover("C1", fx.auth)
            self.assertEqual(result.effects["send_clarification"].status, "verified")
            self.assertEqual(fx.world.effect_count("send_clarification"), 1)
            self.assertEqual(fx.store.intents("C1")[0].intent, intent)
            self.assertNotIn("send_clarification", [call.operation for call in fx.world.calls])

    def test_real_process_exit_after_atomic_consume_does_not_reaccept_reply(self):
        with tempfile.TemporaryDirectory() as folder:
            script = """
import os, sys
from support import build_test_runtime
from test_waits import scoped_reply
fx=build_test_runtime(sys.argv[1])
fx.world.mutate('case.completeness', 'missing')
fx.engine.run(fx.request, fx.auth)
reply=scoped_reply(fx)
fx.world.mutate('case.completeness', 'complete')
old=fx.store.consume_wait_reply_atomic
def die(*args):
    old(*args)
    os._exit(73)
fx.store.consume_wait_reply_atomic=die
fx.engine.reply(reply, fx.auth)
"""
            process = subprocess.run([sys.executable, "-c", script, folder], capture_output=True, text=True)
            self.assertEqual(process.returncode, 73, process.stderr)
            fx = self.fixture(folder)
            fx.clock.advance(2)
            question_id = fx.engine.waits.question_id(fx.store.checkpoint("C1").binding)
            record = fx.store.load_wait_record(question_id)
            self.assertEqual(record.lifecycle, "answered")
            self.assertEqual(fx.engine.reply(record.accepted_reply, fx.auth).status, "denied")
            self.assertEqual(fx.world.effect_count("reschedule"), 0)
            result = fx.engine.recover("C1", fx.auth)
            self.assertLessEqual(fx.store.checkpoint("C1").budget.tool_calls, 24)
            self.assertLessEqual(fx.world.effect_count("reschedule"), 1)

    def test_prepared_wait_recovery_rereads_original_scope_and_preserves_payload(self):
        class HostInterruption(BaseException):
            pass
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder)
            fx.world.mutate("case.completeness", "missing")
            old = fx.store.prepare
            def interrupted(intent):
                old(intent)
                raise HostInterruption()
            fx.store.prepare = interrupted
            with self.assertRaises(HostInterruption):
                fx.engine.run(fx.request, fx.auth)
            fx.store.prepare = old
            original = fx.store.intents("C1")[0].intent
            result = fx.engine.recover("C1", fx.auth)
            self.assertEqual(fx.world.effect_count("send_clarification"), 1)
            self.assertEqual(fx.store.intents("C1")[0].intent, original)
            self.assertEqual(fx.store.checkpoint("C1").budget.clarifications, 1)

    def test_current_checkpoint_race_during_reply_read_cannot_consume(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder)
            fx.world.mutate("case.completeness", "missing")
            fx.engine.run(fx.request, fx.auth)
            reply = scoped_reply(fx)
            real = fx.engine.gateway.bundle.case
            class RaceCase:
                def __getattr__(self, name): return getattr(real, name)
                def read_case(self, request):
                    result = real.read_case(request)
                    cp = fx.store.checkpoint("C1")
                    fx.store.save_checkpoint(cp.model_copy(update={"next_gate": "read_communication"}))
                    return result
            fx.engine.gateway.bundle = replace(fx.engine.gateway.bundle, case=RaceCase())
            self.assertEqual(fx.engine.reply(reply, fx.auth).status, "denied")
            self.assertEqual(fx.store.load_wait_record(reply.question_id).lifecycle, "pending")

    def test_exact_confirmation_text_cannot_supply_new_source_commitment_or_change_request(self):
        with tempfile.TemporaryDirectory() as folder:
            request = make_request(kind="reschedule_exact", consent_mode="exact_slot", arguments={"slot": "S2"})
            fx = build_test_runtime(folder, request=request)
            self.addCleanup(fx.store.close)
            fx.world.mutate("customer.consent", "missing")
            fx.engine.run(request, fx.auth)
            self.assertEqual(fx.store.checkpoint("C1").phase, "wait_confirmation")
            reply = scoped_reply(fx, fields={"customer.confirmation": "verified", "scheduling.slot": "S1"})
            result = fx.engine.reply(reply, fx.auth)
            self.assertEqual(result.status, "authorized")
            self.assertEqual(fx.world.effect_count("reschedule"), 0)
            self.assertEqual(fx.store.original_request("C1", "G1"), request)
            self.assertFalse(any(o.authority == "customer" and o.fact == "confirmation"
                for o in fx.store.checkpoint("C1").observations))

    def test_stored_legacy_wait_projection_is_never_reply_scope(self):
        from proofkey.contracts import WaitState
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder)
            fx.engine.run(fx.request, fx.auth)
            checkpoint = fx.store.checkpoint("C1")
            legacy = WaitState(question_id="legacy", binding=checkpoint.binding, origin="completeness",
                next_gate="completeness", recipient="U1", owner_state_revision="v1",
                awaited_fields=["case.missing_facts"], expires_at=checkpoint.deadline, budget=checkpoint.budget)
            fx.store.save_wait(legacy)
            reply = ScopedReply(question_id="legacy", binding=checkpoint.binding, actor_id="U1",
                proof_reference="locator", request_revision="v1", consent_revision="v1",
                owner_state_revision="v1", fields={"case.missing_facts": "complete"}, received_at=fx.clock.now(), simulated=True)
            before = len(fx.world.calls)
            self.assertEqual(fx.engine.reply(reply, fx.auth).status, "denied")
            self.assertEqual(len(fx.world.calls), before)

    def test_missing_wait_policy_disables_wait_but_not_original_read(self):
        from proofkey.engine import WorkflowEngine
        from proofkey.contracts import EnvironmentProfile
        from proofkey.identity import fingerprint
        from proofkey.policy import GateDenied
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder)
            raw = fx.profile.model_dump(mode="json")
            spec = raw["processes"]["reschedule_window"]
            spec["waits"] = []
            spec["release_hash"] = fingerprint({key: value for key, value in spec.items() if key != "release_hash"})
            raw["process_hash"] = fingerprint(raw["processes"])
            raw["release_hash"] = fingerprint({key: value for key, value in raw.items() if key != "release_hash"})
            profile = EnvironmentProfile.model_validate(raw)
            engine = WorkflowEngine(profile, fx.world.bundle(), fx.store, fx.clock)
            result = engine.run(fx.request, fx.auth)
            self.assertEqual(result.effects["reschedule"].status, "verified")
            calls = len(fx.world.calls)
            with self.assertRaises(GateDenied):
                engine.waits.create(fx.store.checkpoint("C1"), ["case.missing_facts"])
            self.assertEqual(len(fx.world.calls), calls)
            self.assertEqual(engine.gateway.reconcile_read_only(fx.store.intents("C1")[0].intent.action_id).status, "verified")

    def test_host_gateway_injection_keeps_same_instance_for_waits(self):
        from proofkey.engine import WorkflowEngine
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder)
            engine = WorkflowEngine(fx.profile, fx.engine.bundle, fx.store, fx.clock, gateway=fx.engine.gateway)
            self.assertIs(engine.gateway, fx.engine.gateway)
            self.assertIs(engine.waits.gateway, engine.gateway)

    def test_malformed_fresh_reply_source_retains_full_read_reservation(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder)
            fx.world.mutate("case.completeness", "missing")
            fx.engine.run(fx.request, fx.auth)
            reply = scoped_reply(fx)
            real = fx.engine.gateway.bundle.case
            class InvalidCase:
                def __getattr__(self, name): return getattr(real, name)
                def read_case(self, request):
                    read = real.read_case(request)
                    return read.model_copy(update={"observations": [item.model_copy(update={"value": True})
                        if item.fact == "completeness" else item for item in read.observations]})
            fx.engine.gateway.bundle = replace(fx.engine.gateway.bundle, case=InvalidCase())
            self.assertEqual(fx.engine.reply(reply, fx.auth).status, "denied")
            cp = fx.store.checkpoint("C1")
            self.assertEqual((cp.budget.tool_calls, cp.budget.active_seconds), (12, 10.0))
            self.assertEqual(fx.store.load_wait_record(reply.question_id).lifecycle, "pending")

    def test_goods_return_after_wait_preserves_partial_effect_when_shared_cap_reached(self):
        with tempfile.TemporaryDirectory() as folder:
            request = make_request(kind="goods_refusal", consent_mode="unknown", arguments={"inventory": {"item-1": 1}})
            fx = build_test_runtime(folder, request=request)
            self.addCleanup(fx.store.close)
            fx.world.mutate("case.completeness", "missing")
            fx.engine.run(request, fx.auth)
            reply = scoped_reply(fx)
            fx.world.mutate("case.completeness", "complete")
            result = fx.engine.reply(reply, fx.auth)
            self.assertEqual(result.effects["register_goods_refusal"].status, "verified")
            self.assertEqual(fx.world.effect_count("register_goods_refusal"), 1)
            self.assertEqual(fx.world.effect_count("create_return"), 0)
            self.assertEqual(fx.store.checkpoint("C1").budget.tool_calls, 24)
            self.assertEqual(fx.store.checkpoint("C1").budget.max_tool_calls, 24)
            self.assertEqual(fx.store.checkpoint("C1").budget.clarifications, 1)

    def test_shorter_trusted_wait_expiry_fences_orphan_and_prepared_original(self):
        from proofkey.contracts import EnvironmentProfile
        from proofkey.engine import WorkflowEngine
        from proofkey.identity import fingerprint
        from proofkey.policy import GateDenied
        class HostInterruption(BaseException): pass
        for boundary in ("create_wait_atomic", "prepare"):
            with self.subTest(boundary=boundary), tempfile.TemporaryDirectory() as folder:
                fx = self.fixture(folder)
                raw = fx.profile.model_dump(mode="json")
                spec = raw["processes"]["reschedule_window"]
                next(wait for wait in spec["waits"] if wait["phase"] == "wait_customer")["expiry_seconds"] = 30.0
                spec["release_hash"] = fingerprint({key: value for key, value in spec.items() if key != "release_hash"})
                raw["process_hash"] = fingerprint(raw["processes"])
                raw["release_hash"] = fingerprint({key: value for key, value in raw.items() if key != "release_hash"})
                profile = EnvironmentProfile.model_validate(raw)
                engine = WorkflowEngine(profile, fx.world.bundle(), fx.store, fx.clock)
                fx.world.mutate("case.completeness", "missing")
                original = getattr(fx.store, boundary)
                def interrupt(*args):
                    original(*args)
                    raise HostInterruption()
                setattr(fx.store, boundary, interrupt)
                with self.assertRaises(HostInterruption): engine.run(fx.request, fx.auth)
                setattr(fx.store, boundary, original)
                checkpoint = fx.store.checkpoint("C1")
                wait = fx.store.load_wait_record(engine.waits.question_id(checkpoint.binding))
                fx.clock.advance(31)
                self.assertLess(fx.clock.now(), checkpoint.deadline)
                before = len(fx.world.calls)
                with self.assertRaises(GateDenied, msg="Expired original wait must not dispatch or rebuild before case deadline"):
                    engine.waits.create(checkpoint, ["case.missing_facts"])
                self.assertEqual(len(fx.world.calls), before)
                self.assertEqual(fx.world.effect_count("send_clarification"), 0)
                self.assertEqual(fx.store.load_wait_record(wait.wait.question_id), wait)

    def test_prepared_original_rechecks_source_question_value_without_revision_change(self):
        class HostInterruption(BaseException): pass
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder)
            fx.world.mutate("case.completeness", "missing")
            original = fx.store.prepare
            def interrupt(intent):
                original(intent)
                raise HostInterruption()
            fx.store.prepare = interrupt
            with self.assertRaises(HostInterruption): fx.engine.run(fx.request, fx.auth)
            fx.store.prepare = original
            checkpoint = fx.store.checkpoint("C1")
            real = fx.engine.gateway.bundle.case
            class DifferentQuestion:
                def __getattr__(self, name): return getattr(real, name)
                def read_case(self, request):
                    read = real.read_case(request)
                    return read.model_copy(update={"observations": [item.model_copy(update={"value": "v2"})
                        if item.fact == "question_revision" else item for item in read.observations]})
            fx.engine.gateway.bundle = replace(fx.engine.gateway.bundle, case=DifferentQuestion())
            fx.engine.waits.create(checkpoint, ["case.missing_facts"])
            self.assertEqual(fx.world.effect_count("send_clarification"), 0,
                "Exact sourced question context must be rechecked before prepared dispatch")
            self.assertEqual(fx.store.intents("C1")[0].state, "prepared")
