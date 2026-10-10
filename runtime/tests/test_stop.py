"""Durable stop is recorded revocation, never undo or permission to resend."""
import tempfile
import unittest
import subprocess
import sys
import threading

from support import build_test_runtime, make_auth


class StopTests(unittest.TestCase):
    def fixture(self, folder):
        fx = build_test_runtime(folder)
        self.addCleanup(fx.store.close)
        return fx

    def test_stop_after_effect_preserves_historical_result_and_live_recorded_state(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder)
            first = fx.engine.run(fx.request, fx.auth)
            historical = fx.store.saved_result("C1", first.binding.generation)
            self.assertTrue(callable(getattr(fx.engine, "stop", None)), "Engine needs guarded durable stop")
            stopped = fx.engine.stop("C1", first.binding.generation, fx.auth)
            self.assertTrue(stopped.stop.requested)
            self.assertEqual(stopped.effects["reschedule"].status, "verified")
            self.assertEqual(fx.world.effect_count("reschedule"), 1)
            self.assertEqual(fx.store.saved_result("C1", first.binding.generation), historical)
            calls = len(fx.world.calls)
            recovered = fx.engine.recover("C1", fx.auth)
            self.assertTrue(recovered.stop.requested)
            self.assertEqual([c.operation for c in fx.world.calls[calls:]], ["read_case", "read_schedule"])
            self.assertEqual(fx.store.saved_result("C1", first.binding.generation), historical)

    def test_stopped_unknown_terminal_nonexecution_never_resends(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder)
            fx.world.set_fault("reschedule", "timeout_before")
            fx.world.set_fault("read_schedule", "timeout_before")
            first = fx.engine.run(fx.request, fx.auth)
            self.assertTrue(callable(getattr(fx.engine, "stop", None)), "Engine stop must fence unknown originals")
            stopped = fx.engine.stop("C1", first.binding.generation, fx.auth)
            self.assertTrue(stopped.stop.requested)
            calls = len(fx.world.calls)
            fx.world.set_fault("read_schedule", "terminal_not_executed")
            recovered = fx.engine.recover("C1", fx.auth)
            self.assertTrue(recovered.stop.requested)
            self.assertEqual(fx.world.effect_count("reschedule"), 0)
            self.assertFalse(any(c.operation == "reschedule" for c in fx.world.calls[calls:]))

    def test_wrong_generation_and_actor_cannot_stop_or_disclose(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder)
            first = fx.engine.run(fx.request, fx.auth)
            self.assertTrue(callable(getattr(fx.engine, "stop", None)), "Engine stop is missing")
            self.assertEqual(fx.engine.stop("C1", "foreign", fx.auth).status, "denied")
            self.assertEqual(fx.engine.stop("C1", first.binding.generation,
                make_auth(proof_reference="old-proof")).status, "denied")
            self.assertFalse(fx.store.checkpoint("C1").stop.requested)

    def test_stop_prepared_original_returns_unentered_and_recovery_does_not_send(self):
        class HostInterruption(BaseException): pass
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder)
            real = fx.store.prepare
            def interrupt(intent):
                real(intent)
                raise HostInterruption()
            fx.store.prepare = interrupt
            with self.assertRaises(HostInterruption):
                fx.engine.run(fx.request, fx.auth)
            fx.store.prepare = real
            checkpoint = fx.store.checkpoint("C1")
            intent = fx.store.intents("C1")[0].intent
            result = fx.engine.stop("C1", checkpoint.binding.generation, fx.auth)
            self.assertIn("reschedule", result.effects, "Recorded stop must expose prepared original as locally unentered")
            self.assertEqual(result.effects["reschedule"].reason, "stopped_before_entry")
            calls = len(fx.world.calls)
            recovered = fx.engine.recover("C1", fx.auth)
            self.assertTrue(recovered.stop.requested)
            self.assertEqual(fx.store.intents("C1")[0].intent, intent)
            self.assertEqual(fx.store.intents("C1")[0].state, "prepared")
            self.assertEqual([c.operation for c in fx.world.calls[calls:]], ["read_case"])
            self.assertEqual(fx.world.effect_count("reschedule"), 0)

    def test_real_process_exit_after_stop_fence_cannot_revive_prepared_original(self):
        with tempfile.TemporaryDirectory() as folder:
            script = """
import os, sys
from support import build_test_runtime
fx=build_test_runtime(sys.argv[1])
class HostInterruption(BaseException): pass
old=fx.store.prepare
def prepare(intent):
    old(intent)
    raise HostInterruption()
fx.store.prepare=prepare
try:fx.engine.run(fx.request, fx.auth)
except HostInterruption:pass
fx.store.prepare=old
stop=fx.store.stop_waits_atomic
def die(*args):
    stop(*args)
    os._exit(74)
fx.store.stop_waits_atomic=die
fx.engine.stop('C1','G1',fx.auth)
"""
            result = subprocess.run([sys.executable, "-c", script, folder], capture_output=True, text=True)
            self.assertEqual(result.returncode, 74, result.stderr)
            fx = self.fixture(folder)
            fx.clock.advance(2)
            before = fx.store.checkpoint("C1")
            self.assertTrue(before.stop.requested)
            self.assertEqual(before.phase, "window_gate", "Fence was committed before cosmetic stop phase")
            recovered = fx.engine.recover("C1", fx.auth)
            self.assertTrue(recovered.stop.requested)
            self.assertEqual(fx.store.intents("C1")[0].state, "prepared")
            self.assertEqual(fx.world.effect_count("reschedule"), 0)
            self.assertEqual([c.operation for c in fx.world.calls], ["read_case"])

    def test_repeated_stop_requires_current_source_and_keeps_budget_and_fence(self):
        from test_workflows import CrashOnPhase, ProcessCrash
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder)
            with self.assertRaises(ProcessCrash):
                CrashOnPhase(fx, "intake").run(fx.request, fx.auth)
            first = fx.engine.stop("C1", "G1", fx.auth)
            self.assertTrue(first.stop.requested)
            before = fx.store.checkpoint("C1")
            second = fx.engine.stop("C1", "G1", fx.auth)
            self.assertTrue(second.stop.requested)
            self.assertEqual(fx.store.checkpoint("C1").budget.tool_calls, before.budget.tool_calls + 1)
            self.assertEqual(fx.store.checkpoint("C1").deadline, before.deadline)
            fx.world.mutate("case.generation", "G2")
            self.assertEqual(fx.engine.stop("C1", "G1", fx.auth).status, "denied")
            self.assertEqual(fx.engine.recover("C1", fx.auth).status, "denied")
            self.assertTrue(fx.store.generation_stop(before.binding).requested)

    def test_stop_entry_guard_precedes_auth_mutation(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder)
            fx.engine.run(fx.request, fx.auth)
            before = fx.engine.gateway.auth
            responses = []
            foreign = make_auth(proof_reference="foreign")
            thread = threading.Thread(target=lambda: responses.append(fx.engine.stop("C1", "G1", foreign)))
            thread.start();thread.join()
            self.assertEqual(responses[0].status, "denied")
            with fx.engine._entry_scope():
                self.assertEqual(fx.engine.stop("C1", "G1", foreign).status, "denied")
            self.assertEqual(fx.engine.gateway.auth, before)
            self.assertFalse(fx.store.checkpoint("C1").stop.requested)

    def test_fresh_refusal_after_stop_preserves_unknown_predecessor_and_case_budget(self):
        from proofkey.identity import request_fingerprint
        from support import make_request
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder)
            fx.world.set_fault("reschedule", "timeout_before")
            fx.world.set_fault("read_schedule", "timeout_before")
            first = fx.engine.run(fx.request, fx.auth)
            fx.engine.stop("C1", "G1", fx.auth)
            before = fx.store.checkpoint("C1")
            request = make_request(request_id="REQ2", kind="service_refusal", consent_mode="unknown", arguments={"scope": "service"})
            for key, value in (("case.binding", {"case_id": "C1", "object_id": "O1", "principal_id": "U1", "request_id": "REQ2"}),
                ("case.generation", "G2"), ("customer.request_fingerprint", request_fingerprint(request)),
                ("customer.consent_mode", "unknown"), ("delivery.status", "completed")):
                fx.world.mutate(key, value)
            result = fx.engine.run(request, fx.auth)
            current = fx.store.checkpoint("C1")
            self.assertEqual(current.binding.generation, "G2")
            self.assertEqual(current.binding.supersedes_generation, "G1")
            self.assertTrue(fx.store.generation_stop(before.binding).requested)
            self.assertFalse(current.stop.requested)
            self.assertEqual(current.deadline, before.deadline)
            self.assertGreater(current.budget.tool_calls, before.budget.tool_calls)
            self.assertLessEqual(current.budget.tool_calls, 24)
            self.assertEqual(fx.world.effect_count("register_service_refusal"), 0)
            self.assertEqual(fx.store.intents("C1")[0].verification.status, "outcome_unknown")

    def test_exhausted_repeated_stop_denies_but_never_clears_fence(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder)
            fx.engine.run(fx.request, fx.auth)
            fx.engine.stop("C1", "G1", fx.auth)
            cp = fx.store.checkpoint("C1")
            fx.store.consume("C1", "tool_calls", 24 - cp.budget.tool_calls, fx.clock.now())
            before = len(fx.world.calls)
            self.assertEqual(fx.engine.stop("C1", "G1", fx.auth).status, "denied")
            self.assertEqual(len(fx.world.calls), before)
            self.assertTrue(fx.store.checkpoint("C1").stop.requested)
            self.assertEqual(fx.store.checkpoint("C1").budget.tool_calls, 24)

    def test_stopped_original_read_scope_rejection_cannot_disclose_saved_effect(self):
        from dataclasses import replace
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder)
            fx.engine.run(fx.request, fx.auth)
            fx.engine.stop("C1", "G1", fx.auth)
            real = fx.engine.gateway.bundle.scheduling
            class RejectedOriginal:
                def __getattr__(self, name): return getattr(real, name)
                def read_schedule(self, request):
                    read = real.read_schedule(request)
                    return read.model_copy(update={"operation": "read_schedule", "stage": "scope_rejected",
                        "observations": [], "action_id": None, "fingerprint": None, "evidence_refs": []})
            fx.engine.gateway.bundle = replace(fx.engine.gateway.bundle, scheduling=RejectedOriginal())
            result = fx.engine.recover("C1", fx.auth)
            self.assertEqual(result.status, "denied", "Original-read ACL refusal must not fall through to saved receipt disclosure")
            self.assertEqual(result.effects, {})
            self.assertTrue(fx.store.checkpoint("C1").stop.requested)
