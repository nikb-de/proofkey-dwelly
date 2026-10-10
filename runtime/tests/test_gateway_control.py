"""Current public source controls; local persistence never authenticates actors."""
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from proofkey.adapters.world import SimulatedWorld
from proofkey.contracts import AuthorityReadback, ActionProposal
from proofkey.gateway import ActionGateway
from proofkey.identity import request_fingerprint
from proofkey.journal import CaseStore
from proofkey.policy import GateDenied
from proofkey.profiles import load_profile
from support import DEADLINE, FakeClock, make_auth, make_binding, make_checkpoint, make_request

ROOT = Path(__file__).resolve().parents[1]


class GatewayControlTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.clock, self.profile = FakeClock(), load_profile("flat-v1.3")
        self.world = SimulatedWorld(Path(self.folder.name) / "world.sqlite",
            ROOT / "fixtures/development/packet-world-v1.json", profile=self.profile, clock=self.clock)
        self.path = Path(self.folder.name) / "journal.sqlite"
        self.store = CaseStore(self.path)
        self.addCleanup(lambda: self.store.close())
        self.binding = make_binding()
        self.store.admit(self.binding, make_request(), make_checkpoint(profile_version="v1.3",
            phase="intake", next_gate="extract_input", ownership_state="accepted", ownership_state_revision="v1"))
        self.gateway = ActionGateway(self.profile, self.world.bundle(), self.store, self.clock, make_auth())

    def control(self, auth=None, **kwargs):
        method = getattr(self.gateway, "authenticate_control", None)
        self.assertTrue(callable(method), "Gateway must authenticate stopped/no-intent control from current source")
        return method(self.binding, auth or make_auth(), **kwargs)

    def test_stopped_initiator_needs_one_case_read_and_no_owner_permission(self):
        self.store.set_stop("C1", "G1")
        self.world.mutate("ownership.state", "pending")
        checkpoint = self.control(purpose="stop")
        self.assertTrue(checkpoint.stop.requested)
        self.assertEqual(checkpoint.binding, self.binding)
        self.assertEqual(checkpoint.budget.tool_calls, 1)
        self.assertEqual(checkpoint.budget.active_seconds, 0)
        self.assertEqual([call.operation for call in self.world.calls], ["read_case"])
        self.assertEqual(self.store.intents("C1"), ())

    def test_control_rejects_wrong_proof_actor_generation_and_current_identity(self):
        method = getattr(self.gateway, "authenticate_control", None)
        self.assertTrue(callable(method), "Current source control authentication is required")
        for auth in (make_auth(proof_reference="old-proof"), make_auth(caller_id="OP1", proof_reference="synthetic-operator-proof")):
            with self.assertRaises(GateDenied):
                method(self.binding, auth, purpose="recorded_state")
        self.world.mutate("case.generation", "G2")
        with self.assertRaises(GateDenied):
            method(self.binding, make_auth(), purpose="stop")
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 2)

    def test_malformed_source_completion_keeps_full_reservation(self):
        # Settling before duplicate/foreign observation validation refunds unknown work.
        original, clock = self.gateway.bundle.case, self.clock
        class DuplicateCase:
            def __getattr__(self, name):
                return getattr(original, name)
            def read_case(self, request):
                read = original.read_case(request)
                clock.advance(2)
                return read.model_copy(update={"observations": [*read.observations, read.observations[0]], "as_of": clock.now()})
        self.gateway.bundle = replace(self.gateway.bundle, case=DuplicateCase())
        with self.assertRaises(GateDenied):
            self.gateway._facts(self.binding, {"case.binding"})
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 10)

    def test_scoped_rejection_settles_but_foreign_rejection_retains_debt(self):
        original, clock = self.gateway.bundle.case, self.clock
        class RejectedCase:
            def __getattr__(self, name):
                return getattr(original, name)
            def read_case(self, request):
                clock.advance(2)
                return AuthorityReadback(operation="read_case", object_id="foreign", observations=[],
                    stage="scope_rejected", as_of=clock.now(), evidence_refs=[])
        self.gateway.bundle = replace(self.gateway.bundle, case=RejectedCase())
        with self.assertRaises(GateDenied):
            self.gateway._facts(self.binding, {"case.binding"})
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 10)

    def test_fresh_refusal_has_clean_atomic_admission_and_shared_budget(self):
        self.store.set_stop("C1", "G1")
        request = make_request(request_id="REQ2", kind="service_refusal", consent_mode="unknown", arguments={"scope": "service"})
        self.world.mutate("case.binding", {"case_id": "C1", "object_id": "O1", "principal_id": "U1", "request_id": "REQ2"})
        self.world.mutate("case.generation", "G2")
        self.world.mutate("customer.request_fingerprint", request_fingerprint(request))
        self.world.mutate("customer.consent_mode", "unknown")
        old = self.store.checkpoint("C1")
        binding = self.gateway.bind_request(request, DEADLINE, initialize_process=True)
        checkpoint = self.store.checkpoint("C1")
        self.assertFalse(checkpoint.stop.requested, "Fresh explicit refusal must not inherit reschedule stop")
        self.assertEqual((checkpoint.phase, checkpoint.next_gate), ("intake", "extract_input"))
        self.assertEqual(binding.supersedes_generation, "G1")
        self.assertEqual(checkpoint.budget.tool_calls, old.budget.tool_calls + 3)
        self.assertEqual(checkpoint.deadline, old.deadline)
        self.assertTrue(self.store.generation_stop(self.binding).requested)
        self.assertEqual(self.store.original_request("C1", "G1"), make_request())
        self.assertEqual(self.store.original_request("C1", "G2"), request)

    def test_active_facts_actor_requires_fresh_proof_and_owned_reply_metadata(self):
        reader = getattr(self.gateway, "read_reply_sources", None)
        self.assertTrue(callable(reader), "Active facts replies need host-owned current metadata reads")
        observations = reader(self.binding, make_auth(caller_id="OP1", proof_reference="synthetic-operator-proof"), recipient_role="operator")
        facts = {item.authority + "." + item.fact: item.value for item in observations}
        self.assertEqual(facts["operator.recipient"], "OP1")
        self.assertEqual(facts["case.question_revision"], "v1")
        self.assertNotIn("customer.consent", facts)
        self.assertNotIn("customer.confirmation", facts)
        with self.assertRaises(GateDenied):
            reader(self.binding, make_auth(caller_id="OP1", proof_reference="saved-reply-locator"), recipient_role="operator")

    def test_active_facts_reply_can_authenticate_when_owner_is_pending(self):
        self.world.mutate("ownership.state", "pending")
        checkpoint = self.store.checkpoint("C1")
        self.store.save_checkpoint(checkpoint.model_copy(update={"ownership_state": "pending"}))
        try:
            observations = self.gateway.read_reply_sources(self.binding,
                make_auth(caller_id="OP1", proof_reference="synthetic-operator-proof"), recipient_role="operator")
        except GateDenied:
            observations = ()
        self.assertTrue(observations, "Current designated recipient may supply untrusted facts with pending ownership")
        self.assertEqual(next(item.value for item in observations if item.authority == "operator"), "OP1")
        self.assertEqual(self.world.effect_count("reschedule"), 0)

    def test_current_identity_semantic_mismatch_retains_control_read_debt(self):
        self.world.mutate("case.generation", "G-old")
        with self.assertRaises(GateDenied):
            self.gateway.authenticate_control(self.binding, make_auth(), purpose="stop")
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 10)

    def test_explicit_read_only_reconciliation_never_resends_active_unknown(self):
        from support import make_intent
        intent = make_intent(profile_version="v1.3")
        self.store.prepare(intent)
        self.store.begin_dispatch(intent, self.clock.now())
        method = getattr(self.gateway, "reconcile_read_only", None)
        self.assertTrue(callable(method), "A stopped engine needs an explicit no-resend original reader")
        result = method(intent.action_id)
        self.assertEqual(result.status, "outcome_unknown")
        self.assertEqual([call.operation for call in self.world.calls], ["read_schedule"])
        self.assertEqual(self.store.intent(intent.action_id).intent, intent)

    def test_unresolved_entered_predecessor_fences_new_refusal_business_effect(self):
        from support import make_intent
        old = make_intent(profile_version="v1.3")
        self.store.prepare(old)
        self.store.begin_dispatch(old, self.clock.now())
        self.store.set_stop("C1", "G1")
        request = make_request(request_id="REQ2", kind="service_refusal", consent_mode="unknown", arguments={"scope": "service"})
        for key, value in (("case.binding", {"case_id": "C1", "object_id": "O1", "principal_id": "U1", "request_id": "REQ2"}),
                           ("case.generation", "G2"), ("customer.request_fingerprint", request_fingerprint(request)),
                           ("customer.consent_mode", "unknown"), ("delivery.status", "completed")):
            self.world.mutate(key, value)
        self.gateway.bind_request(request, DEADLINE, initialize_process=True)
        checkpoint = self.store.checkpoint("C1")
        self.store.save_checkpoint(checkpoint.model_copy(update={"phase": "refusal_gate", "next_gate": "register_service_refusal"}))
        result = self.gateway.execute_proposal("C1", "register_service_refusal", lambda *args:
            (ActionProposal(operation="register_service_refusal", stage="commit", arguments={"scope": "service"}, evidence_refs=[]),
             {"service.refusal": "verified"}))
        self.assertEqual(result.status, "rejected", "New request identity cannot prove independence from unresolved prior reschedule")
        self.assertEqual(self.world.effect_count("register_service_refusal"), 0)

    def test_stopped_original_unknown_keeps_identity_and_never_resends(self):
        from support import make_intent
        intent = make_intent(profile_version="v1.3")
        self.store.prepare(intent)
        self.store.begin_dispatch(intent, self.clock.now())
        self.store.set_stop("C1", "G1")
        self.assertEqual(self.gateway.reconcile_read_only(intent.action_id).status, "outcome_unknown")
        self.assertEqual(self.gateway.reconcile(intent.action_id).status, "outcome_unknown")
        self.assertEqual([call.operation for call in self.world.calls], ["read_schedule", "read_schedule"])
        self.assertEqual(self.store.intent(intent.action_id).intent, intent)
        self.assertEqual(self.store.checkpoint("C1").budget.retries, {})

    def test_read_overrun_exhausts_budget_even_when_reply_is_malformed(self):
        original, clock = self.gateway.bundle.case, self.clock
        class SlowCase:
            def __getattr__(self, name):
                return getattr(original, name)
            def read_case(self, request):
                reply = original.read_case(request)
                clock.advance(11)
                return reply
        self.gateway.bundle = replace(self.gateway.bundle, case=SlowCase())
        with self.assertRaises(Exception):
            self.gateway.authenticate_control(self.binding, make_auth(), purpose="stop")
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 120)
        before = len(self.world.calls)
        with self.assertRaises(Exception):
            self.gateway.authenticate_control(self.binding, make_auth(), purpose="stop")
        self.assertEqual(len(self.world.calls), before)

    def test_active_reply_current_recipient_and_owner_revision_races_are_denied(self):
        for key, value in (("operator.recipient", "OP2"), ("ownership.state_revision", "v2"),
                           ("customer.consent_revision", "v2"), ("case.generation", "G2")):
            with self.subTest(key=key):
                fixture = GatewayControlTests()
                fixture.setUp()
                try:
                    fixture.world.mutate(key, value)
                    with self.assertRaises(GateDenied):
                        fixture.gateway.read_reply_sources(fixture.binding,
                            make_auth(caller_id="OP1", proof_reference="synthetic-operator-proof"), recipient_role="operator")
                    self.assertEqual(fixture.world.effect_count("reschedule"), 0)
                    self.assertEqual(fixture.store.checkpoint("C1").budget.active_seconds, 10)
                finally:
                    fixture.doCleanups()

    def test_refusal_cannot_reset_exhausted_shared_case_capacity(self):
        self.store.consume("C1", "tool_calls", 23, self.clock.now())
        self.store.set_stop("C1", "G1")
        request = make_request(request_id="REQ2", kind="service_refusal", consent_mode="unknown", arguments={"scope": "service"})
        for key, value in (("case.binding", {"case_id": "C1", "object_id": "O1", "principal_id": "U1", "request_id": "REQ2"}),
                           ("case.generation", "G2"), ("customer.request_fingerprint", request_fingerprint(request)),
                           ("customer.consent_mode", "unknown")):
            self.world.mutate(key, value)
        with self.assertRaises(GateDenied):
            self.gateway.bind_request(request, DEADLINE, initialize_process=True)
        self.assertEqual(self.store.checkpoint("C1").binding, self.binding)
        self.assertTrue(self.store.checkpoint("C1").stop.requested)
        self.assertEqual(self.store.request_bindings("C1"), (self.binding,))

    def test_customer_reply_uses_current_designation_and_stopped_reply_reads_are_unavailable(self):
        observations = self.gateway.read_reply_sources(self.binding, make_auth(), recipient_role="customer")
        self.assertEqual(next(item.value for item in observations if item.authority == "messaging"), "U1")
        self.store.set_stop("C1", "G1")
        before = len(self.world.calls)
        with self.assertRaises(GateDenied):
            self.gateway.read_reply_sources(self.binding, make_auth(), recipient_role="customer")
        self.assertEqual(len(self.world.calls), before)

    def test_foreign_original_envelope_preserves_conflict_and_full_read_reservation(self):
        checkpoint = self.store.checkpoint("C1")
        self.store.save_checkpoint(checkpoint.model_copy(update={"phase": "window_gate", "next_gate": "reschedule"}))
        original = self.gateway.bundle.scheduling
        class ForeignEnvelope:
            def __getattr__(self, name):
                return getattr(original, name)
            def read_schedule(self, request):
                read = original.read_schedule(request)
                return read.model_copy(update={"object_id": "foreign-envelope"})
        self.gateway.bundle = replace(self.gateway.bundle, scheduling=ForeignEnvelope())
        result = self.gateway.execute_proposal("C1", "reschedule", lambda *args:
            (ActionProposal(operation="reschedule", stage="commit", arguments={"slot": "S1"}, evidence_refs=[]), {"slot": "S1"}))
        self.assertEqual(result.status, "conflict")
        self.assertEqual(self.world.effect_count("reschedule"), 1)
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 10)

    def test_incomplete_original_observations_never_refund_the_read_reservation(self):
        checkpoint = self.store.checkpoint("C1")
        self.store.save_checkpoint(checkpoint.model_copy(update={"phase": "window_gate", "next_gate": "reschedule"}))
        original = self.gateway.bundle.scheduling
        class IncompleteOriginal:
            def __getattr__(self, name):
                return getattr(original, name)
            def read_schedule(self, request):
                return original.read_schedule(request).model_copy(update={"observations": []})
        self.gateway.bundle = replace(self.gateway.bundle, scheduling=IncompleteOriginal())
        result = self.gateway.execute_proposal("C1", "reschedule", lambda *args:
            (ActionProposal(operation="reschedule", stage="commit", arguments={"slot": "S1"}, evidence_refs=[]), {"slot": "S1"}))
        self.assertEqual(result.status, "outcome_unknown")
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 10)

    def test_reply_source_completeness_is_fresh_and_independent_of_untrusted_reply_body(self):
        from proofkey.contracts import ScopedReply
        reply = ScopedReply(question_id="Q1", binding=self.binding, actor_id="U1", proof_reference="saved-locator",
            request_revision="v1", consent_revision="v1", owner_state_revision="v1",
            fields={"case.completeness": "complete"}, received_at=self.clock.now(), simulated=True)
        self.world.mutate("case.completeness", "missing")
        observations = self.gateway.read_reply_sources(self.binding, make_auth(), recipient_role="customer")
        facts = {item.authority + "." + item.fact: item.value for item in observations}
        self.assertEqual(facts.get("case.completeness"), "missing",
            "Reply helper must return freshly read completeness in its existing case read")
        self.assertEqual(reply.fields["case.completeness"], "complete")
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 4)

    def test_malformed_source_completeness_retains_full_case_read_reservation(self):
        self.world.mutate("case.completeness", {"caller_claim": "complete"})
        with self.assertRaises(GateDenied):
            self.gateway.read_reply_sources(self.binding, make_auth(), recipient_role="customer")
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 1)
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 10)


if __name__ == "__main__":
    unittest.main()
