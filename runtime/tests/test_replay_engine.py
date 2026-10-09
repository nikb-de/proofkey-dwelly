"""Engine replay ordering over real public provider and journal boundaries."""
from dataclasses import replace
import tempfile
import threading
import unittest

from proofkey.contracts import AuthContext, CanonicalRequest
from proofkey.engine import WorkflowEngine
from proofkey.identity import request_fingerprint
from support import build_test_runtime, make_auth, make_request


class CountingPlanner:
    def __init__(self):
        self.calls = 0

    def propose(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError("Historical replay entered planning")


class CountingEvidence:
    def __init__(self):
        self.calls = 0

    def read_original(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError("Historical replay entered evidence access")

    get = read_original
    assertions = read_original
    resolve_record = read_original


class ProcessCrash(BaseException):
    """Trusted host interruption; the production engine does not swallow it."""


class CrashOnPhase(WorkflowEngine):
    def __init__(self, fx, phase):
        super().__init__(fx.profile, fx.world.bundle(), fx.store, fx.clock)
        self.phase = phase

    def run_one_approved_phase(self, checkpoint, request, auth, **flags):
        if checkpoint.phase == self.phase:
            raise ProcessCrash()
        return super().run_one_approved_phase(checkpoint, request, auth, **flags)


class ForwardPort:
    """Observe the public boundary while preserving real provider behavior."""
    def __init__(self, real, **overrides):
        self.real, self.overrides = real, overrides

    def __getattr__(self, name):
        return self.overrides.get(name, getattr(self.real, name))


class EngineReplayTests(unittest.TestCase):
    def fixture(self, request=None):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        fx = build_test_runtime(folder.name, request=request)
        self.addCleanup(fx.store.close)
        return fx

    def replay_engine(self, fx, bundle=None):
        planner, evidence = CountingPlanner(), CountingEvidence()
        engine = WorkflowEngine(fx.profile, bundle or fx.world.bundle(), fx.store, fx.clock,
                                planner=planner, evidence=evidence)
        # A replay must not replace preexisting controller or business auth state.
        engine.gateway.auth = make_auth(caller_id="OTHER", proof_reference="other-proof")
        return engine, planner, evidence

    def assert_denied(self, result):
        self.assertEqual(result.model_dump(mode="json"),
                         {"status": "denied", "correlation_id": "C1", "reason": "denied"})

    def assert_disclosure_only(self, fx, call_count, effect_counts, engine, planner, evidence,
                               controller, gateway_auth):
        tail = fx.world.calls[call_count:]
        self.assertTrue(all(c.operation == "read_case" and c.purpose == "disclosure" for c in tail), tail)
        for operation, count in effect_counts.items():
            self.assertEqual(fx.world.effect_count(operation), count, operation)
        self.assertEqual(planner.calls, 0)
        self.assertEqual(evidence.calls, 0)
        self.assertIs(engine.process, controller)
        self.assertIs(engine.gateway.auth, gateway_auth)

    def effect_counts(self, fx):
        return {operation: fx.world.effect_count(operation) for operation in
                ("reschedule", "register_goods_refusal", "register_service_refusal", "create_return",
                 "send_clarification", "send_status", "enqueue_handoff", "transfer_owner")}

    def completed_schedule(self, fx):
        initial = fx.engine.run(fx.request, fx.auth)
        self.assertEqual(initial.effects["reschedule"].status, "verified")
        self.assertEqual(fx.store.saved_result("C1", "G1"), initial)
        return initial

    def test_saved_real_partial_unknown_return_stays_historical_after_external_change(self):
        request = make_request(kind="goods_refusal", consent_mode="unknown",
                               arguments={"inventory": {"item-1": 1}})
        fx = self.fixture(request)
        fx.world.set_fault("create_return", "timeout_after_execute")
        fx.world.set_fault("read_return", "timeout_before")
        initial = fx.engine.run(request, fx.auth)
        self.assertEqual(initial.effects["register_goods_refusal"].status, "verified")
        self.assertEqual(initial.effects["create_return"].status, "outcome_unknown")
        # Trusted setup saves the actual partial output without inventing effect truth.
        # The ordinary workflow pauses unknowns; explicit recover remains separate.
        fx.store.save_result(initial)
        checkpoint, intents = fx.store.checkpoint("C1"), fx.store.intents("C1")
        fx.world.mutate("returns.status", "received")
        fx.world.set_fault("read_return", "none")
        engine, planner, evidence = self.replay_engine(fx)
        controller, gateway_auth = engine.process, engine.gateway.auth
        calls, effects = len(fx.world.calls), self.effect_counts(fx)

        result = engine.run(request, fx.auth)

        self.assertTrue(result.historical)
        self.assertEqual(result.effects["create_return"].status, "outcome_unknown")
        self.assertEqual(result.effects["register_goods_refusal"], initial.effects["register_goods_refusal"])
        self.assertEqual(result.as_of, initial.as_of)
        self.assertEqual(result.result_version, initial.result_version)
        self.assertEqual({**result.model_dump(mode="json"), "historical": False}, initial.model_dump(mode="json"))
        self.assertEqual(fx.store.saved_result("C1", "G1"), initial)
        self.assertEqual(fx.store.original_request("C1", "G1"), request)
        after = fx.store.checkpoint("C1")
        self.assertEqual((after.binding, after.phase, after.next_gate, after.deadline, after.stop),
                         (checkpoint.binding, checkpoint.phase, checkpoint.next_gate, checkpoint.deadline, checkpoint.stop))
        self.assertEqual(after.budget.tool_calls, checkpoint.budget.tool_calls + 1)
        self.assertEqual(after.budget.max_tool_calls, checkpoint.budget.max_tool_calls)
        self.assertEqual(after.budget.reconciliation_reads, checkpoint.budget.reconciliation_reads)
        self.assertEqual(fx.store.intents("C1"), intents)
        self.assertEqual(len(fx.world.calls) - calls, 1)
        self.assert_disclosure_only(fx, calls, effects, engine, planner, evidence, controller, gateway_auth)

    def test_stopped_saved_schedule_discloses_original_stop_without_business_refresh(self):
        fx = self.fixture()
        with self.assertRaises(ProcessCrash):
            CrashOnPhase(fx, "verification").run(fx.request, fx.auth)
        fx.store.set_stop("C1", "G1")
        saved = fx.engine.build_case_result(fx.store.checkpoint("C1"))
        self.assertEqual(saved.effects["reschedule"].status, "verified")
        fx.store.save_result(saved)
        before = fx.store.checkpoint("C1")
        fx.world.mutate("delivery.status", "delivered")
        engine, planner, evidence = self.replay_engine(fx)
        controller, gateway_auth = engine.process, engine.gateway.auth
        calls, effects = len(fx.world.calls), self.effect_counts(fx)

        result = engine.run(fx.request, fx.auth)

        self.assertTrue(result.historical)
        self.assertTrue(result.stop.requested)
        self.assertEqual({**result.model_dump(mode="json"), "historical": False}, saved.model_dump(mode="json"))
        after = fx.store.checkpoint("C1")
        self.assertEqual((after.phase, after.next_gate, after.binding, after.stop, after.deadline),
                         (before.phase, before.next_gate, before.binding, before.stop, before.deadline))
        self.assertEqual(after.budget.tool_calls, before.budget.tool_calls + 1)
        self.assertEqual(len(fx.world.calls) - calls, 1)
        self.assert_disclosure_only(fx, calls, effects, engine, planner, evidence, controller, gateway_auth)

    def test_recognized_saved_access_denials_precede_bootstrap_and_withhold_details(self):
        for condition in ("revoked", "unverifiable", "tool_exhausted", "active_exhausted", "expired", "wrong_proof"):
            with self.subTest(condition=condition):
                fx = self.fixture()
                initial = self.completed_schedule(fx)
                auth = fx.auth
                if condition == "revoked":
                    fx.world.mutate("case.authorization", "revoked")
                elif condition == "unverifiable":
                    fx.world.set_fault("read_case", "timeout_before")
                elif condition == "tool_exhausted":
                    remaining = 24 - fx.store.checkpoint("C1").budget.tool_calls
                    fx.store.consume("C1", "tool_calls", remaining, fx.clock.now())
                elif condition == "active_exhausted":
                    remaining = 120 - fx.store.checkpoint("C1").budget.active_seconds
                    fx.store.consume("C1", "active_seconds", remaining, fx.clock.now())
                elif condition == "expired":
                    fx.clock.advance(7200)
                else:
                    auth = make_auth(proof_reference="foreign-proof")
                before = fx.store.checkpoint("C1")
                engine, planner, evidence = self.replay_engine(fx)
                controller, gateway_auth = engine.process, engine.gateway.auth
                calls, effects = len(fx.world.calls), self.effect_counts(fx)

                self.assert_denied(engine.run(fx.request, auth))

                self.assertEqual(fx.store.saved_result("C1", "G1"), initial)
                after = fx.store.checkpoint("C1")
                self.assertEqual((after.phase, after.next_gate, after.binding, after.deadline),
                                 (before.phase, before.next_gate, before.binding, before.deadline))
                self.assertEqual(after.budget.max_tool_calls, before.budget.max_tool_calls)
                self.assertEqual(after.budget.max_active_seconds, before.budget.max_active_seconds)
                self.assertEqual(after.budget.effects, before.budget.effects)
                self.assertEqual(after.budget.reconciliation_reads, before.budget.reconciliation_reads)
                extra = 1 if condition in {"revoked", "unverifiable", "wrong_proof"} else 0
                self.assertEqual(len(fx.world.calls) - calls, extra)
                self.assertEqual(after.budget.tool_calls, before.budget.tool_calls + extra)
                if condition == "unverifiable":
                    self.assertEqual(after.budget.active_seconds, before.budget.active_seconds + 10)
                self.assert_disclosure_only(fx, calls, effects, engine, planner, evidence, controller, gateway_auth)

    def test_revoked_business_consent_keeps_independent_historical_disclosure(self):
        fx = self.fixture()
        initial = self.completed_schedule(fx)
        fx.world.mutate("customer.consent", "revoked")
        fx.world.mutate("customer.consent_revision", "v2")
        engine, planner, evidence = self.replay_engine(fx)
        controller, gateway_auth = engine.process, engine.gateway.auth
        calls, effects = len(fx.world.calls), self.effect_counts(fx)

        result = engine.run(fx.request, fx.auth)

        self.assertTrue(result.historical)
        self.assertEqual({**result.model_dump(mode="json"), "historical": False}, initial.model_dump(mode="json"))
        self.assertEqual(result.binding.consent_revision, "v1")
        self.assertEqual(len(fx.world.calls) - calls, 1)
        self.assert_disclosure_only(fx, calls, effects, engine, planner, evidence, controller, gateway_auth)

    def test_ambiguous_historical_revision_or_scope_denies_before_any_source_read(self):
        for changes in ({"request_revision": "v2"}, {"consent_revision": "v2"},
                        {"object_id": "OTHER"}, {"principal_id": "OTHER"}):
            with self.subTest(changes=changes):
                fx = self.fixture()
                initial = self.completed_schedule(fx)
                candidate = fx.request.model_copy(update=changes)
                before = fx.store.checkpoint("C1")
                engine, planner, evidence = self.replay_engine(fx)
                controller, gateway_auth = engine.process, engine.gateway.auth
                calls, effects = len(fx.world.calls), self.effect_counts(fx)

                self.assert_denied(engine.run(candidate, fx.auth))

                self.assertEqual(fx.store.checkpoint("C1"), before)
                self.assertEqual(fx.store.saved_result("C1", "G1"), initial)
                self.assertEqual(len(fx.world.calls), calls)
                self.assert_disclosure_only(fx, calls, effects, engine, planner, evidence, controller, gateway_auth)

    def test_completed_input_noise_cannot_reenter_evidence_or_replace_saved_original(self):
        fx = self.fixture()
        initial = self.completed_schedule(fx)
        candidate = fx.request.model_copy(update={"evidence_ids": ["NEW-ARTIFACT"], "narrative": "Review saved result"})
        engine, planner, evidence = self.replay_engine(fx)
        controller, gateway_auth = engine.process, engine.gateway.auth
        calls, effects = len(fx.world.calls), self.effect_counts(fx)

        result = engine.run(candidate, fx.auth)

        self.assertTrue(result.historical)
        self.assertEqual({**result.model_dump(mode="json"), "historical": False}, initial.model_dump(mode="json"))
        self.assertEqual(fx.store.original_request("C1", "G1"), fx.request)
        self.assert_disclosure_only(fx, calls, effects, engine, planner, evidence, controller, gateway_auth)

    def test_new_business_identity_must_pass_independent_current_admission(self):
        fx = self.fixture()
        initial = self.completed_schedule(fx)
        candidate = make_request(request_id="REQ2", kind="reschedule_exact", consent_mode="exact_slot",
                                 arguments={"slot": "S2"})
        before = fx.store.checkpoint("C1")
        calls, effects = len(fx.world.calls), self.effect_counts(fx)

        stale = fx.engine.run(candidate, fx.auth)

        self.assert_denied(stale)
        self.assertEqual(fx.store.checkpoint("C1").binding, before.binding)
        self.assertEqual(fx.store.saved_result("C1", "G1"), initial)
        tail = fx.world.calls[calls:]
        self.assertTrue(tail)
        self.assertTrue(all(c.purpose != "disclosure" for c in tail))
        self.assertEqual(self.effect_counts(fx), effects)
        # Only independent trusted source changes can authenticate a new identity.
        fx.world.mutate("case.binding", {"case_id": "C1", "object_id": "O1", "principal_id": "U1", "request_id": "REQ2"})
        fx.world.mutate("case.generation", "G2")
        fx.world.mutate("customer.request_fingerprint", request_fingerprint(candidate))
        fx.world.mutate("customer.consent_mode", "exact_slot")
        calls = len(fx.world.calls)

        result = fx.engine.run(candidate, fx.auth)

        self.assertFalse(result.historical)
        self.assertEqual(result.binding.generation, "G2")
        self.assertEqual(result.binding.supersedes_generation, "G1")
        self.assertEqual(result.effects["reschedule"].postcondition, {"slot": "S2"})
        self.assertEqual(fx.world.effect_count("reschedule"), 2)
        self.assertTrue(all(c.purpose != "disclosure" for c in fx.world.calls[calls:]))
        after = fx.store.checkpoint("C1")
        self.assertEqual(after.deadline, before.deadline)
        self.assertEqual(after.budget.max_tool_calls, before.budget.max_tool_calls)
        self.assertGreater(after.budget.tool_calls, before.budget.tool_calls)
        self.assertEqual(fx.store.saved_result("C1", "G1"), initial)

    def test_exact_unfinished_input_continues_original_selected_gate_without_reset(self):
        fx = self.fixture()
        with self.assertRaises(ProcessCrash):
            CrashOnPhase(fx, "window_gate").run(fx.request, fx.auth)
        fx.store.save_checkpoint(fx.store.checkpoint("C1").model_copy(update={"next_gate": "reschedule"}))
        before = fx.store.checkpoint("C1")
        self.assertIsNone(fx.store.saved_result("C1", "G1"))
        self.assertEqual((before.phase, before.next_gate), ("window_gate", "reschedule"))
        observed = []
        bundle = fx.world.bundle()
        real = bundle.scheduling

        def reschedule(intent, *, deadline=None):
            observed.append(fx.store.checkpoint("C1"))
            return real.reschedule(intent, deadline=deadline)

        bundle = replace(bundle, scheduling=ForwardPort(real, reschedule=reschedule))
        engine, planner, evidence = self.replay_engine(fx, bundle)
        calls = len(fx.world.calls)

        result = engine.run(fx.request, fx.auth)

        self.assertFalse(result.historical)
        self.assertEqual(result.effects["reschedule"].status, "verified")
        self.assertEqual(len(observed), 1)
        dispatch = observed[0]
        self.assertEqual((dispatch.phase, dispatch.next_gate), ("window_gate", "reschedule"))
        self.assertEqual(dispatch.binding, before.binding)
        self.assertEqual(dispatch.deadline, before.deadline)
        self.assertGreater(dispatch.budget.tool_calls, before.budget.tool_calls)
        self.assertEqual(dispatch.budget.max_tool_calls, before.budget.max_tool_calls)
        self.assertEqual(fx.store.original_request("C1", "G1"), fx.request)
        self.assertEqual(fx.world.effect_count("reschedule"), 1)
        self.assertTrue(all(c.purpose != "disclosure" for c in fx.world.calls[calls:]))
        self.assertEqual(planner.calls, 0)
        self.assertEqual(evidence.calls, 0)

    def test_exact_unfinished_input_cannot_replace_unsupported_saved_gate(self):
        fx = self.fixture()
        with self.assertRaises(ProcessCrash):
            CrashOnPhase(fx, "window_gate").run(fx.request, fx.auth)
        fx.store.save_checkpoint(fx.store.checkpoint("C1").model_copy(update={"next_gate": "send_status"}))
        before = fx.store.checkpoint("C1")
        calls, effects = len(fx.world.calls), self.effect_counts(fx)

        self.assert_denied(fx.engine.run(fx.request, fx.auth))

        after = fx.store.checkpoint("C1")
        self.assertEqual((after.phase, after.next_gate), ("window_gate", "send_status"))
        self.assertEqual(after.binding, before.binding)
        self.assertEqual(after.deadline, before.deadline)
        self.assertGreater(after.budget.tool_calls, before.budget.tool_calls)
        self.assertEqual(after.budget.max_tool_calls, before.budget.max_tool_calls)
        self.assertTrue(all(c.purpose == "bind_request" for c in fx.world.calls[calls:]))
        self.assertEqual(self.effect_counts(fx), effects)
        self.assertIsNone(fx.store.saved_result("C1", "G1"))

    def test_changed_unfinished_lineage_denies_before_source_or_planner(self):
        fx = self.fixture()
        with self.assertRaises(ProcessCrash):
            CrashOnPhase(fx, "extraction").run(fx.request, fx.auth)
        before = fx.store.checkpoint("C1")
        engine, planner, evidence = self.replay_engine(fx)
        controller, gateway_auth = engine.process, engine.gateway.auth
        calls, effects = len(fx.world.calls), self.effect_counts(fx)
        candidate = fx.request.model_copy(update={"evidence_ids": ["NEW-ARTIFACT"]})

        self.assert_denied(engine.run(candidate, fx.auth))

        self.assertEqual(fx.store.checkpoint("C1"), before)
        self.assertEqual(fx.store.original_request("C1", "G1"), fx.request)
        self.assertEqual(len(fx.world.calls), calls)
        self.assert_disclosure_only(fx, calls, effects, engine, planner, evidence, controller, gateway_auth)

    def test_foreign_thread_is_denied_before_replay_journal_or_controller_mutation(self):
        fx = self.fixture()
        self.completed_schedule(fx)
        before = fx.store.checkpoint("C1")
        engine, planner, evidence = self.replay_engine(fx)
        controller, gateway_auth = engine.process, engine.gateway.auth
        calls, effects = len(fx.world.calls), self.effect_counts(fx)
        results = []
        thread = threading.Thread(target=lambda: results.append(engine.run(fx.request, fx.auth)))
        thread.start()
        thread.join()

        self.assertEqual(len(results), 1)
        self.assert_denied(results[0])
        self.assertEqual(fx.store.checkpoint("C1"), before)
        self.assertEqual(len(fx.world.calls), calls)
        self.assert_disclosure_only(fx, calls, effects, engine, planner, evidence, controller, gateway_auth)
        self.assertTrue(engine.run(fx.request, fx.auth).historical)

    def test_reentrant_public_disclosure_callback_denies_before_nested_mutation(self):
        fx = self.fixture()
        self.completed_schedule(fx)
        bundle = fx.world.bundle()
        real = bundle.case
        nested, observations = [], []
        engine = None

        def read_case(request):
            before = fx.store.checkpoint("C1")
            nested.append(engine.run(fx.request, make_auth(caller_id="OTHER")))
            observations.append((before, fx.store.checkpoint("C1")))
            return real.read_case(request)

        bundle = replace(bundle, case=ForwardPort(real, read_case=read_case))
        engine, planner, evidence = self.replay_engine(fx, bundle)
        controller, gateway_auth = engine.process, engine.gateway.auth
        calls, effects = len(fx.world.calls), self.effect_counts(fx)

        result = engine.run(fx.request, fx.auth)

        self.assertTrue(result.historical)
        self.assertEqual(len(nested), 1)
        self.assert_denied(nested[0])
        self.assertEqual(observations[0][0], observations[0][1])
        self.assertEqual(len(fx.world.calls) - calls, 1)
        self.assert_disclosure_only(fx, calls, effects, engine, planner, evidence, controller, gateway_auth)

    def test_unvalidated_typed_inputs_cannot_enter_replay_or_mutate_auth(self):
        fx = self.fixture()
        self.completed_schedule(fx)
        bad_auth = AuthContext.model_construct(caller_id="", proof_reference="synthetic-proof")
        bad_request = CanonicalRequest.model_construct(**{**fx.request.model_dump(), "evidence_ids": [""]})
        for request, auth in ((fx.request, None), (fx.request, bad_auth), (bad_request, fx.auth)):
            with self.subTest(request=request, auth=auth):
                before = fx.store.checkpoint("C1")
                engine, planner, evidence = self.replay_engine(fx)
                controller, gateway_auth = engine.process, engine.gateway.auth
                calls, effects = len(fx.world.calls), self.effect_counts(fx)

                self.assert_denied(engine.run(request, auth))

                self.assertEqual(fx.store.checkpoint("C1"), before)
                self.assertEqual(len(fx.world.calls), calls)
                self.assert_disclosure_only(fx, calls, effects, engine, planner, evidence, controller, gateway_auth)

    def test_recover_completed_result_does_not_automatically_disclose_saved_history(self):
        fx = self.fixture()
        self.completed_schedule(fx)
        calls, effects = len(fx.world.calls), self.effect_counts(fx)

        result = fx.engine.recover("C1", fx.auth)

        self.assertEqual(result.status, "denied")
        self.assertEqual(result.reason, "unavailable")
        self.assertFalse(result.historical)
        self.assertEqual(result.effects, {})
        self.assertTrue(all(c.purpose != "disclosure" for c in fx.world.calls[calls:]))
        self.assertEqual(self.effect_counts(fx), effects)
