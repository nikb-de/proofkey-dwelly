"""Process bootstrap and committed service predecessors at real boundaries."""
import tempfile
import unittest
from pathlib import Path

from proofkey.adapters.world import SimulatedWorld
from proofkey.contracts import ActionProposal, AuthorityObservation, EnvironmentProfile, PhaseCheckpoint, RevisionVector, VerificationResult
from proofkey.gateway import ActionGateway
from proofkey.identity import request_fingerprint
from proofkey.journal import CaseStore, IntentRecord, JournalFailure
from proofkey.policy import GateDenied, PolicyGate
from support import DEADLINE, NOW, FakeClock, load_test_profile, make_auth, make_binding, make_intent, make_request
from test_gateway import POST
from test_policy import ARGS, FIXTURE, STAGES, context


def builder(operation):
    def build(request, observations):
        return ActionProposal(operation=operation, stage=STAGES[operation], arguments=ARGS[operation], evidence_refs=[]), POST[operation]
    return build


class BootstrapProcessTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.clock = FakeClock()
        self.profile = load_test_profile("flat-v1.2")
        self.world = SimulatedWorld(Path(folder.name) / "world.sqlite", FIXTURE, profile=self.profile, clock=self.clock)
        self.store = CaseStore(Path(folder.name) / "journal.sqlite")
        self.addCleanup(self.store.close)
        self.gateway = ActionGateway(self.profile, self.world.bundle(), self.store, self.clock, auth=make_auth())

    def admit(self, request=None):
        return self.gateway.bind_request(request or make_request(), DEADLINE, initialize_process=True)

    def test_first_admission_saves_three_designated_leased_reads_and_actual_owner(self):
        self.world.mutate("ownership.state_revision", "owner-revision")
        self.world.mutate("ownership.epoch", 7)
        binding = self.admit()
        self.assertIsNotNone(binding, "Declared process bootstrap must admit from authenticated source facts")
        cp = self.store.checkpoint("C1")
        self.assertEqual((cp.phase, cp.next_gate), ("intake", "intake"))
        self.assertEqual((cp.ownership_state, cp.ownership_state_revision, cp.ownership_epoch), ("accepted", "owner-revision", 7))
        self.assertEqual(cp.budget.tool_calls, 3)
        self.assertEqual(cp.budget.active_seconds, 0)
        self.assertEqual(cp.budget.max_planner_calls, 0)
        self.assertEqual(cp.budget.role_allowances["planning"].max_invocations, 0)
        keys = {o.authority + "." + o.fact for o in cp.observations}
        self.assertEqual(keys, {"case.binding", "case.request_revision", "case.authorization", "case.generation", "case.completeness",
            "customer.consent_revision", "customer.consent", "customer.consent_mode", "customer.request_fingerprint",
            "ownership.state", "ownership.state_revision", "ownership.epoch", "ownership.owner"})
        self.assertEqual([c.operation for c in self.world.calls], ["read_case", "read_principal", "read_owner"])

    def test_pending_source_ownership_is_saved_without_auto_acceptance(self):
        self.world.mutate("ownership.state", "pending")
        self.admit()
        self.assertEqual(self.store.checkpoint("C1").ownership_state, "pending")
        self.assertEqual(self.gateway.execute_proposal("C1", "reschedule", builder("reschedule")).status, "rejected")
        self.assertEqual(self.world.effect_count("reschedule"), 0)

    def test_unknown_consent_or_foreign_commitment_does_not_grant_business_permission(self):
        self.world.mutate("customer.consent", "unknown")
        self.world.mutate("customer.request_fingerprint", "0" * 64)
        self.admit()
        cp = self.store.checkpoint("C1")
        self.store.save_checkpoint(PhaseCheckpoint.model_validate({**cp.model_dump(), "phase": "window_gate", "next_gate": "window_gate"}))
        self.assertEqual(self.gateway.execute_proposal("C1", "reschedule", builder("reschedule")).status, "rejected")
        self.assertEqual(self.gateway.execute_proposal("C1", "enqueue_handoff", builder("enqueue_handoff")).status, "verified")
        self.assertEqual(self.world.effect_count("reschedule"), 0)

    def test_current_pending_checkpoint_phase_owner_and_original_survive_refresh(self):
        request = make_request()
        binding = self.admit(request)
        cp = self.store.checkpoint("C1")
        pending = PhaseCheckpoint.model_validate({**cp.model_dump(), "phase": "wait_operator", "next_gate": "completeness",
            "ownership_state": "pending", "ownership_state_revision": "saved-pending", "ownership_epoch": 4,
            "question_id": "Q1", "awaited_fields": ["case.completeness"]})
        self.store.save_checkpoint(pending)
        before = self.store.checkpoint("C1")
        self.world.mutate("case.completeness", "missing")
        self.world.mutate("ownership.state_revision", "new-owner")
        self.assertEqual(self.admit(request), binding)
        after = self.store.checkpoint("C1")
        for key in ("phase", "next_gate", "ownership_state", "ownership_state_revision", "ownership_epoch", "question_id", "awaited_fields", "stop", "deadline", "profile_version", "process_version", "policy_version"):
            self.assertEqual(getattr(after, key), getattr(before, key), key)
        self.assertEqual(after.budget.tool_calls, before.budget.tool_calls + 3)
        self.assertEqual(after.budget.max_planner_calls, 0)
        self.assertEqual(self.store.original_request("C1", "G1"), request)
        facts = {o.authority + "." + o.fact: o for o in after.observations}
        self.assertEqual(facts["case.completeness"].value, "missing")
        self.assertEqual(len(facts), len(after.observations))

    def test_stopped_current_bootstrap_denies_without_refresh_or_history_change(self):
        self.admit()
        self.store.set_stop("C1", "G1")
        before, calls = self.store.checkpoint("C1"), len(self.world.calls)
        with self.assertRaises(GateDenied):
            self.admit()
        self.assertEqual(self.store.checkpoint("C1"), before)
        self.assertEqual(len(self.world.calls), calls)

    def test_current_auth_revocation_debits_read_without_disclosing_saved_fields(self):
        self.admit()
        before = self.store.checkpoint("C1")
        self.gateway.auth = make_auth(proof_reference="revoked")
        with self.assertRaises(GateDenied) as caught:
            self.admit()
        self.assertEqual(str(caught.exception), "scope_denied")
        after = self.store.checkpoint("C1")
        self.assertEqual(after.budget.tool_calls, before.budget.tool_calls + 1)
        self.assertEqual(after.observations, before.observations)
        self.assertEqual(after.binding, before.binding)

    def test_duplicate_cannot_replace_original_text_or_evidence_lineage(self):
        self.admit()
        before = self.store.checkpoint("C1")
        for request in (make_request(narrative="new text"), make_request(evidence_ids=["foreign-artifact"])):
            with self.assertRaises(GateDenied):
                self.admit(request)
        self.assertEqual(self.store.checkpoint("C1"), before)
        self.assertEqual(self.store.original_request("C1", "G1"), make_request())

    def test_new_generation_retains_budget_stop_owner_and_original_history(self):
        self.admit()
        self.store.set_stop("C1", "G1")
        old = self.store.checkpoint("C1")
        for key, value in (("case.generation", "G2"), ("case.request_revision", "v2"), ("customer.consent_revision", "v2"),
                ("ownership.state", "pending"), ("ownership.epoch", 3)):
            self.world.mutate(key, value)
        request = make_request(request_revision="v2", consent_revision="v2", narrative="new authenticated generation")
        binding = self.admit(request)
        cp = self.store.checkpoint("C1")
        self.assertEqual(binding.supersedes_generation, "G1")
        self.assertEqual((cp.phase, cp.next_gate), ("intake", "intake"))
        self.assertEqual((cp.ownership_state, cp.ownership_state_revision, cp.ownership_epoch),
            (old.ownership_state, old.ownership_state_revision, old.ownership_epoch))
        self.assertTrue(cp.stop.requested)
        self.assertEqual(cp.deadline, old.deadline)
        self.assertEqual(cp.budget.max_planner_calls, 0)
        self.assertEqual(cp.budget.tool_calls, old.budget.tool_calls + 3)
        self.assertEqual(self.store.original_request("C1", "G1"), make_request())
        self.assertEqual(self.store.original_request("C1", "G2"), request)

    def test_new_generation_does_not_upgrade_saved_legacy_profile(self):
        legacy = ActionGateway(load_test_profile("flat-v1.1"), self.world.bundle(), self.store, self.clock, auth=make_auth())
        legacy.bind_request(make_request(), DEADLINE)
        for key, value in (("case.generation", "G2"), ("case.request_revision", "v2"), ("customer.consent_revision", "v2")):
            self.world.mutate(key, value)
        with self.assertRaises(GateDenied):
            self.admit(make_request(request_revision="v2", consent_revision="v2"))
        self.assertEqual(self.store.checkpoint("C1").profile_version, "v1.1")

    def test_missing_designation_and_saved_legacy_profile_fail_closed(self):
        legacy = ActionGateway(load_test_profile("flat-v1.1"), self.world.bundle(), self.store, self.clock, auth=make_auth())
        with self.assertRaises(GateDenied):
            legacy.bind_request(make_request(), DEADLINE, initialize_process=True)
        self.assertEqual(len(self.world.calls), 0)
        legacy.bind_request(make_request(), DEADLINE)
        before = self.store.checkpoint("C1")
        with self.assertRaises(GateDenied):
            self.admit()
        after = self.store.checkpoint("C1")
        self.assertEqual(after.profile_version, "v1.1")
        self.assertEqual(after.phase, before.phase)

    def test_authenticated_owner_mismatch_or_revision_mismatch_cannot_admit(self):
        self.world.mutate("ownership.owner", "OP1")
        with self.assertRaises(GateDenied):
            self.admit()
        self.assertEqual(self.store.admission_account("C1").tool_calls, 3)
        with self.assertRaises(JournalFailure):
            self.store.checkpoint("C1")
        self.world.mutate("ownership.owner", "U1")
        with self.assertRaises(GateDenied):
            self.admit(make_request(request_revision="wrong"))
        self.assertEqual(self.store.admission_account("C1").tool_calls, 5)

    def test_forged_auth_and_unknown_read_keep_finite_admission_debt(self):
        self.gateway.auth = make_auth(proof_reference="forged")
        with self.assertRaises(GateDenied):
            self.admit()
        self.gateway.auth = make_auth()
        self.world.set_fault("read_principal", "timeout_before")
        with self.assertRaises(GateDenied):
            self.admit()
        account = self.store.admission_account("C1")
        self.assertEqual(account.tool_calls, 3)
        self.assertEqual(account.active_seconds, 10)
        self.world.set_fault("read_principal", "none")
        self.admit()
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 6)
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 10)

    def verified_service(self):
        request = make_request(kind="service_refusal", consent_mode="unknown", arguments={"scope": "service"})
        self.world.mutate("customer.request_fingerprint", request_fingerprint(request))
        self.world.mutate("customer.consent_mode", "unknown")
        self.world.mutate("delivery.status", "completed")
        self.admit(request)
        cp = self.store.checkpoint("C1")
        self.store.save_checkpoint(PhaseCheckpoint.model_validate({**cp.model_dump(), "phase": "refusal_gate", "next_gate": "refusal_gate"}))
        self.assertEqual(self.gateway.execute_proposal("C1", "register_service_refusal", builder("register_service_refusal")).status, "verified")
        cp = self.store.checkpoint("C1")
        self.store.save_checkpoint(PhaseCheckpoint.model_validate({**cp.model_dump(), "phase": "refusal_complete", "next_gate": "refusal_complete"}))

    def test_service_refusal_then_committed_handoff_remains_within_budget(self):
        self.verified_service()
        self.assertEqual(self.gateway.execute_proposal("C1", "enqueue_handoff", builder("enqueue_handoff")).status, "verified")
        self.assertEqual(self.world.effect_count("register_service_refusal"), 1)
        self.assertEqual(self.world.effect_count("enqueue_handoff"), 1)
        self.assertLessEqual(self.store.checkpoint("C1").budget.tool_calls, 24)
        handoff = self.store.intents("C1")[-1].verification
        self.assertEqual(handoff.postcondition["operator.handoff_disposition"], "pending")

    def test_direct_execute_handoff_uses_same_committed_service_predecessor(self):
        self.verified_service()
        cp = self.store.checkpoint("C1")
        fields = self.profile.capabilities["enqueue_handoff"].conditional_coverage.covered_fields
        intent = make_intent(binding=cp.binding, operation="enqueue_handoff", stage="enqueue", arguments=ARGS["enqueue_handoff"],
            postcondition=POST["enqueue_handoff"], profile_version=cp.profile_version, process_version=cp.process_version,
            expected_revisions=RevisionVector(revisions={key: "v1" for key in fields}), ownership_state_revision="v1", ownership_epoch=0)
        self.assertEqual(self.gateway.execute(intent).status, "verified")
        self.assertEqual(self.world.effect_count("enqueue_handoff"), 1)
        self.assertLessEqual(self.store.checkpoint("C1").budget.tool_calls, 24)


class ServicePredecessorPolicyTests(unittest.TestCase):
    def setUp(self):
        self.profile = load_test_profile("flat-v1.1")
        self.gate = PolicyGate(self.profile)
        request = make_request(kind="service_refusal", consent_mode="unknown", arguments={"scope": "service"})
        self.request, self.proposal, self.obs, checkpoint = context("enqueue_handoff", request=request)
        self.cp = PhaseCheckpoint.model_validate({**checkpoint.model_dump(), "phase": "refusal_complete", "next_gate": "refusal_complete"})
        intent = make_intent(binding=make_binding(request), operation="register_service_refusal", stage="commit",
            arguments={"scope": "service"}, postcondition={"service.refusal": "verified"}, profile_version="v1.1")
        result = VerificationResult(status="verified", object_id="O1", action_id=intent.action_id,
            fingerprint=intent.argument_fingerprint, postcondition=intent.postcondition, evidence_refs=["committed-source-evidence"], as_of=NOW)
        self.predecessor = IntentRecord(intent=intent, state="verified", verification=result)

    def decision(self, predecessor):
        return self.gate.evaluate(self.request, self.proposal, self.obs, self.cp, journal_predecessor=predecessor).allowed

    def test_matching_typed_verified_original_allows_graph_only_service_predicate(self):
        self.assertTrue(self.decision(self.predecessor))

    def test_raw_source_refusal_claim_cannot_replace_committed_predecessor(self):
        obs = [*[o for o in self.obs if (o.authority, o.fact) != ("service", "refusal")], AuthorityObservation(authority="service", fact="refusal", object_id="O1", value="verified",
            revision="v1", observed_at=NOW, evidence_ref="source-claim")]
        self.assertFalse(self.gate.evaluate(self.request, self.proposal, obs, self.cp).allowed)

    def test_wrong_binding_weak_result_and_raw_bool_are_not_journal_predecessors(self):
        self.assertFalse(self.decision(True))
        for changes in ({"state": "pending"}, {"verification": VerificationResult(status="pending")},
                {"intent": make_intent(operation="register_service_refusal", arguments={"scope": "service"}, postcondition={"service.refusal": "verified"})}):
            self.assertFalse(self.decision(IntentRecord.model_validate({**self.predecessor.model_dump(), **changes})))
        data = self.predecessor.model_dump()
        for key, value in (("object_id", "foreign"), ("action_id", "foreign"), ("fingerprint", "0" * 64), ("postcondition", {"service.refusal": "pending"})):
            result = VerificationResult.model_validate({**data["verification"], key: value})
            self.assertFalse(self.decision(IntentRecord.model_validate({**data, "verification": result})))

    def test_covered_service_lifecycle_must_be_completed_but_legacy_is_frozen(self):
        args = context("register_service_refusal", **{"delivery.status": "scheduled"})
        self.assertTrue(self.gate.evaluate(*args).allowed)
        data = self.profile.model_dump()
        data["capabilities"]["register_service_refusal"]["conditional_coverage"]["covered_fields"].append("delivery.status")
        guarded = PolicyGate(EnvironmentProfile.model_validate(data))
        self.assertFalse(guarded.evaluate(*args).allowed)
        self.assertTrue(guarded.evaluate(*context("register_service_refusal", **{"delivery.status": "completed"})).allowed)

    def test_future_profile_cannot_drop_service_lifecycle_coverage(self):
        data = self.profile.model_dump()
        data["version"] = "v2"
        guarded = PolicyGate(EnvironmentProfile.model_validate(data))
        request, proposal, obs, cp = context("register_service_refusal", **{"delivery.status": "completed"})
        cp = PhaseCheckpoint.model_validate({**cp.model_dump(), "profile_version": "v2"})
        self.assertFalse(guarded.evaluate(request, proposal, obs, cp).allowed)
