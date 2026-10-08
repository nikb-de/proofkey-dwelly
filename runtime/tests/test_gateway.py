"""Real journal/provider boundaries, shared budgets, recovery and source races."""
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from proofkey.adapters.world import SimulatedWorld
from proofkey.contracts import ActionProposal, EnvironmentProfile, PhaseCheckpoint, RevisionVector
from proofkey.gateway import ActionGateway
from proofkey.identity import request_fingerprint
from proofkey.journal import CaseStore, JournalFailure
from proofkey.policy import GateDenied
from support import DEADLINE, NOW, FakeClock, load_test_profile, make_auth, make_binding, make_checkpoint, make_intent, make_request
from test_policy import ARGS, FIXTURE, PHASES, STAGES


class PacingClock(FakeClock):
    def wait(self, seconds):
        self.advance(seconds)


POST = {
    "reschedule": {"slot": "S1"},
    "register_goods_refusal": {"goods.refusal": "verified", "inventory": {"item-1": 1}, "quantity": 1},
    "register_service_refusal": {"service.refusal": "verified"},
    "create_return": {"returns.status": "initiated", "inventory": {"item-1": 1}, "quantity": 1, "destination": "D1"},
    "send_clarification": {"messaging.status": "sent", "recipient": "U1", "question_id": "Q1"},
    "send_status": {"messaging.status": "sent", "recipient": "U1"},
    "enqueue_handoff": {"operator.handoff_disposition": "pending", "packet_id": "P1", "packet_revision": "v1", "packet_hash": "packet-hash"},
    "transfer_owner": {"ownership.state": "pending", "ownership.owner": "U1", "epoch": 0,
                       "transfer_id": "T1", "packet_id": "P1", "packet_revision": "v1"},
}


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.clock = PacingClock()
        self.profile = load_test_profile("flat-v1.1")
        self.world = SimulatedWorld(Path(self.folder.name) / "world.sqlite", FIXTURE, profile=self.profile, clock=self.clock)
        self.path = Path(self.folder.name) / "journal.sqlite"
        self.store = CaseStore(self.path)
        self.addCleanup(lambda: self.store.close())
        self.gateway = ActionGateway(self.profile, self.world.bundle(), self.store, self.clock, auth=make_auth())

    def ready(self, operation="reschedule", request=None):
        kind = {"register_goods_refusal": "goods_refusal", "create_return": "goods_refusal",
                "register_service_refusal": "service_refusal"}.get(operation, "reschedule_window")
        request = request or make_request(kind=kind, consent_mode="unknown" if "refusal" in kind else "window",
            **({"arguments": {"inventory": {"item-1": 1}}} if kind == "goods_refusal" else
               {"arguments": {"scope": "service"}} if kind == "service_refusal" else {}))
        if request != make_request():
            self.world.mutate("customer.request_fingerprint", request_fingerprint(request))
            self.world.mutate("customer.consent_mode", request.consent_mode)
        binding = make_binding(request)
        checkpoint = make_checkpoint(binding=binding, profile_version="v1.1", phase=PHASES[operation], next_gate=PHASES[operation],
                                     ownership_state="accepted", ownership_state_revision="v1")
        self.store.admit(binding, request, checkpoint)
        return binding

    def intent(self, **changes):
        covered = self.profile.capabilities["reschedule"].conditional_coverage.covered_fields
        data = dict(profile_version="v1.1", expected_revisions=RevisionVector(revisions={key: "v1" for key in covered}),
                    ownership_state_revision="v1", ownership_epoch=0)
        return make_intent(**{**data, **changes})

    @staticmethod
    def builder(operation, arguments=None, postcondition=None):
        def build(request, observations):
            return ActionProposal(operation=operation, stage=STAGES[operation], arguments=arguments or ARGS[operation],
                                  evidence_refs=[]), POST[operation] if postcondition is None else postcondition
        return build

    def test_prepare_and_dispatch_commit_precede_effect_and_exact_lookup_survives_reopen(self):
        self.ready()
        world = self.world
        outer = self
        original = self.gateway.bundle.scheduling
        class CheckedScheduling:
            def __getattr__(self, name):
                return getattr(original, name)
            def reschedule(self, intent, *, deadline=None):
                with_store = CaseStore(outer.path)
                try:
                    outer.assertEqual(with_store.intent(intent.action_id).state, "dispatching")
                    outer.assertEqual(with_store.checkpoint("C1").budget.effects, 1)
                    outer.assertEqual(world.effect_count("reschedule"), 0)
                finally:
                    with_store.close()
                return original.reschedule(intent, deadline=deadline)
        from dataclasses import replace
        self.gateway.bundle = replace(self.gateway.bundle, scheduling=CheckedScheduling())
        result = self.gateway.execute(self.intent())
        self.assertEqual(result.status, "verified")
        self.assertEqual(self.world.effect_count("reschedule"), 1)
        self.assertEqual(self.store.intent(self.intent().action_id).state, "verified")

    def test_prepare_or_dispatch_commit_failure_never_enters_effect_transport(self):
        self.ready()
        for state in ("prepared", "dispatching"):
            with self.subTest(state=state):
                def fail_selected_commit():
                    row = self.store._db.execute("SELECT dispatch_state FROM intents").fetchone()
                    if row and row[0] == state:
                        raise JournalFailure("private:storage-canary")
                self.store._before_commit = fail_selected_commit
                result = self.gateway.execute(self.intent())
                self.assertEqual(result.status, "rejected")
                self.assertNotIn("canary", result.model_dump_json())
                self.assertEqual(self.world.effect_count("reschedule"), 0)
                self.assertFalse(any(c.operation == "reschedule" for c in self.world.calls))
                self.store._before_commit = None
                self.clock.advance(2)

    def test_acknowledgement_without_original_readback_is_unknown(self):
        self.ready()
        self.world.set_fault("read_schedule", "timeout_before")
        result = self.gateway.execute(self.intent())
        self.assertEqual(result.status, "outcome_unknown")
        self.assertEqual(self.world.effect_count("reschedule"), 1)
        self.assertEqual(self.store.intent(self.intent().action_id).state, "outcome_unknown")
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 10)

    def test_wrong_object_readback_is_conflict_and_keeps_original_journal_identity(self):
        self.ready()
        self.world.set_fault("read_schedule", "wrong_object")
        result = self.gateway.execute(self.intent())
        self.assertEqual(result.status, "conflict")
        self.assertEqual(result.object_id, "O1")
        self.assertNotIn("provider-other-object", result.model_dump_json())

    def test_unsupported_operation_and_absent_auth_fail_before_any_public_entry(self):
        self.ready()
        result = self.gateway.execute(make_intent(operation="invented"))
        self.assertEqual(result.status, "rejected")
        denied = ActionGateway(self.profile, self.world.bundle(), self.store, self.clock)
        self.assertEqual(denied.execute(self.intent()).status, "rejected")
        self.assertEqual(len(self.world.calls), 0)

    def test_unknown_conditional_coverage_denies_before_public_transport(self):
        self.ready()
        data = self.profile.model_dump()
        data["capabilities"]["reschedule"]["conditional_coverage"] = {"status": "unknown"}
        gateway = ActionGateway(EnvironmentProfile.model_validate(data), self.world.bundle(), self.store, self.clock, auth=make_auth())
        self.assertEqual(gateway.execute(self.intent()).status, "rejected")
        self.assertEqual(len(self.world.calls), 0)

    def test_authenticated_bootstrap_reads_are_durable_before_entry_and_imported(self):
        original = self.gateway.bundle.case
        outer = self
        class CheckedCase:
            def __getattr__(self, name):
                real = getattr(original, name)
                def read(request):
                    observer = CaseStore(outer.path)
                    try:
                        outer.assertGreaterEqual(observer.admission_account("C1").pending_tool_calls, 1)
                        with outer.assertRaises(JournalFailure):
                            observer.checkpoint("C1")
                        outer.assertLessEqual(request.deadline, outer.clock.now() + timedelta(seconds=10))
                    finally:
                        observer.close()
                    return real(request)
                return read
        from dataclasses import replace
        self.gateway.bundle = replace(self.gateway.bundle, case=CheckedCase())
        binding = self.gateway.bind_request(make_request(), DEADLINE)
        self.assertEqual(binding, make_binding())
        checkpoint = self.store.checkpoint("C1")
        self.assertEqual(checkpoint.phase, "intake")
        self.assertEqual(checkpoint.budget.tool_calls, 2)
        self.assertEqual(checkpoint.budget.active_seconds, 0)
        self.assertEqual(self.store.original_request("C1", "G1"), make_request())
        self.assertEqual([c.operation for c in self.world.calls], ["read_case", "read_principal"])
        self.assertTrue(self.store.admission_account("C1").imported)

    def test_forged_proof_prebind_denial_exposes_no_history_and_charges_failure(self):
        gateway = ActionGateway(self.profile, self.world.bundle(), self.store, self.clock, auth=make_auth(proof_reference="forged"))
        with self.assertRaises(GateDenied) as caught:
            gateway.bind_request(make_request(), DEADLINE)
        self.assertEqual(str(caught.exception), "scope_denied")
        self.assertIsNone(caught.exception.__cause__)
        with self.assertRaises(JournalFailure):
            self.store.checkpoint("C1")
        self.assertEqual(self.store.admission_account("C1").tool_calls, 1)

    def test_failed_read_is_precharged_and_unknown_lease_cannot_refund(self):
        self.ready()
        self.world.set_fault("read_case", "timeout_before")
        result = self.gateway.execute(self.intent())
        self.assertEqual(result.status, "rejected")
        checkpoint = self.store.checkpoint("C1")
        self.assertEqual(checkpoint.budget.tool_calls, 1)
        self.assertEqual(checkpoint.budget.active_seconds, 10)
        self.assertEqual(self.world.effect_count("reschedule"), 0)

    def test_current_stop_and_pending_owner_fence_new_effects_before_read_entry(self):
        self.ready()
        self.store.set_stop("C1", "G1")
        self.assertEqual(self.gateway.execute(self.intent()).status, "rejected")
        self.assertEqual(len(self.world.calls), 0)

    def test_original_reconciliation_under_stop_never_resends_even_with_terminal_proof(self):
        self.ready()
        intent = self.intent()
        self.store.prepare(intent)
        self.store.begin_dispatch(intent, self.clock.now())
        self.world.set_fault("reschedule", "final_rejection_unknown")
        self.world.bundle().scheduling.reschedule(intent)
        self.store.set_stop("C1", "G1")
        self.world.set_fault("read_schedule", "terminal_not_executed")
        result = self.gateway.reconcile(intent.action_id)
        self.assertEqual(result.status, "rejected")
        self.assertEqual(self.world.effect_count("reschedule"), 0)
        self.assertEqual(sum(c.operation == "reschedule" for c in self.world.calls), 1)
        self.assertTrue(self.store.checkpoint("C1").stop.requested)

    def test_idempotent_safe_resend_keeps_key_intent_versions_and_one_effect_debit(self):
        self.ready()
        intent = self.intent()
        self.world.set_fault("reschedule", "timeout_before")
        self.assertEqual(self.gateway.execute(intent).status, "outcome_unknown")
        self.world.set_fault("reschedule", "none")
        self.clock.advance(2)
        self.assertEqual(self.gateway.reconcile(intent.action_id).status, "verified")
        self.assertEqual(self.world.effect_count("reschedule"), 1)
        self.assertEqual(self.store.intent(intent.action_id).intent, intent)
        budget = self.store.checkpoint("C1").budget
        self.assertEqual(budget.effects, 1)
        self.assertEqual(budget.retries[intent.action_id], 1)

    def test_already_executed_terminal_driver_and_repeated_execute_do_not_resend(self):
        self.ready()
        intent = self.intent()
        self.assertEqual(self.gateway.execute(intent).status, "verified")
        self.world.set_fault("read_schedule", "terminal_not_executed")
        self.assertEqual(self.gateway.execute(intent).status, "verified")
        self.assertEqual(sum(c.operation == "reschedule" for c in self.world.calls), 1)
        self.assertEqual(self.store.checkpoint("C1").budget.effects, 1)

    def test_proposal_path_all_eight_operations_use_same_durable_sequence(self):
        for operation in STAGES:
            with self.subTest(operation=operation):
                # Independent cases use independent provider/journal fixture databases.
                test = GatewayTests("test_proposal_path_all_eight_operations_use_same_durable_sequence")
                test.setUp()
                try:
                    test.ready(operation)
                    if operation == "create_return":
                        test.world.mutate("goods.refusal", "verified")
                        # Source refusal alone must not satisfy the original journal precondition.
                        self.assertEqual(test.gateway.execute_proposal("C1", operation, self.builder(operation)).status, "rejected")
                        continue
                    result = test.gateway.execute_proposal("C1", operation, self.builder(operation))
                    self.assertEqual(result.status, "verified")
                    self.assertEqual(test.world.effect_count(operation), 1)
                    self.assertEqual(test.store.checkpoint("C1").budget.effects, 1)
                finally:
                    test.doCleanups()

    def test_shared_pacing_keeps_whole_refusal_and_return_inside_original_24_call_cap(self):
        request = make_request(kind="goods_refusal", consent_mode="unknown", arguments={"inventory": {"item-1": 1}})
        self.world.mutate("customer.request_fingerprint", request_fingerprint(request))
        self.world.mutate("customer.consent_mode", "unknown")
        self.gateway.bind_request(request, DEADLINE)
        cp = self.store.checkpoint("C1")
        self.store.save_checkpoint(PhaseCheckpoint.model_validate({**cp.model_dump(), "phase": "refusal_gate", "next_gate": "refusal_gate",
                                 "ownership_state": "accepted", "ownership_state_revision": "v1"}))
        self.assertEqual(self.gateway.execute_proposal("C1", "register_goods_refusal", self.builder("register_goods_refusal")).status, "verified")
        cp = self.store.checkpoint("C1")
        self.store.save_checkpoint(PhaseCheckpoint.model_validate({**cp.model_dump(), "phase": "return_gate", "next_gate": "return_gate"}))
        self.assertEqual(self.gateway.execute_proposal("C1", "create_return", self.builder("create_return")).status, "verified")
        self.assertEqual(self.world.effect_count("register_goods_refusal"), 1)
        self.assertEqual(self.world.effect_count("create_return"), 1)
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 19)
        self.assertEqual(len(self.world.calls), 19)
        self.assertGreaterEqual((self.clock.now() - NOW).total_seconds(), 1)

    def test_source_or_stop_change_after_fresh_reads_is_independently_fenced(self):
        for boundary in ("source", "stop", "owner"):
            test = GatewayTests("test_source_or_stop_change_after_fresh_reads_is_independently_fenced")
            test.setUp()
            try:
                test.ready()
                def mutate_after_reads(request, observations):
                    if boundary == "source":
                        test.world.mutate("customer.request_fingerprint", "0" * 64)
                    elif boundary == "stop":
                        test.store.set_stop("C1", "G1")
                    else:
                        cp = test.store.checkpoint("C1")
                        test.store.save_checkpoint(PhaseCheckpoint.model_validate({**cp.model_dump(), "ownership_state": "pending",
                                                                                 "ownership_state_revision": "v2"}))
                    return self.builder("reschedule")(request, observations)
                self.assertEqual(test.gateway.execute_proposal("C1", "reschedule", mutate_after_reads).status, "rejected")
                self.assertEqual(test.world.effect_count("reschedule"), 0)
            finally:
                test.doCleanups()

    def test_pacing_missing_wait_or_expired_after_wait_fails_closed(self):
        self.ready()
        self.gateway.clock = FakeClock()
        self.assertEqual(self.gateway.execute(self.intent()).status, "rejected")
        self.assertEqual(self.world.effect_count("reschedule"), 0)

    def test_foreign_auth_cannot_recover_original_or_dispatch_impersonating_customer(self):
        self.ready()
        gateway = ActionGateway(self.profile, self.world.bundle(), self.store, self.clock, auth=make_auth(caller_id="OP1", proof_reference="synthetic-operator-proof"))
        self.assertEqual(gateway.execute(self.intent()).status, "rejected")
        self.assertEqual(self.world.effect_count("reschedule"), 0)

    def test_invalid_current_read_acl_discloses_no_original_and_does_not_rewrite_history(self):
        self.ready()
        intent = self.intent()
        self.assertEqual(self.gateway.execute(intent).status, "verified")
        saved = self.store.intent(intent.action_id)
        gateway = ActionGateway(self.profile, self.world.bundle(), self.store, self.clock, auth=make_auth(proof_reference="forged"))
        result = gateway.reconcile(intent.action_id)
        self.assertEqual(result.status, "rejected")
        self.assertIsNone(result.object_id)
        self.assertIsNone(result.fingerprint)
        self.assertIsNone(result.postcondition)
        self.assertEqual(self.store.intent(intent.action_id), saved)

    def test_one_retry_and_three_original_reads_survive_gateway_restart(self):
        self.ready()
        intent = self.intent()
        self.world.set_fault("reschedule", "timeout_before")
        self.assertEqual(self.gateway.execute(intent).status, "outcome_unknown")
        self.assertEqual(self.gateway.reconcile(intent.action_id).status, "outcome_unknown")
        gateway = ActionGateway(self.profile, self.world.bundle(), self.store, self.clock, auth=make_auth())
        gateway.reconcile(intent.action_id)
        budget = self.store.checkpoint("C1").budget
        self.assertEqual(budget.retries[intent.action_id], 1)
        self.assertEqual(budget.reconciliation_reads[intent.action_id], 3)
        self.assertEqual(sum(c.operation == "reschedule" for c in self.world.calls), 2)
        self.assertEqual(self.world.effect_count("reschedule"), 0)

    def test_real_terminal_fence_does_not_enable_unknown_mandatory_idempotency_contract(self):
        self.ready()
        intent = self.intent()
        self.store.prepare(intent)
        self.store.begin_dispatch(intent, self.clock.now())
        self.world.set_fault("reschedule", "final_rejection_unknown")
        self.world.bundle().scheduling.reschedule(intent)
        self.world.set_fault("read_schedule", "terminal_not_executed")
        data = self.profile.model_dump()
        data["capabilities"]["reschedule"]["idempotency_scope"] = {"status": "unknown"}
        gateway = ActionGateway(EnvironmentProfile.model_validate(data), self.world.bundle(), self.store, self.clock, auth=make_auth())
        result = gateway.reconcile(intent.action_id)
        self.assertEqual(result.status, "rejected")
        self.assertEqual(result.reason, "terminal_nonexecution")
        self.assertTrue(result.evidence_refs)
        self.assertEqual(sum(c.operation == "reschedule" for c in self.world.calls), 1)

    def test_business_rejection_has_no_verified_acknowledgement_or_return_compensation(self):
        self.ready()
        self.world.set_fault("reschedule", "business_rejection")
        result = self.gateway.execute(self.intent())
        self.assertEqual(result.status, "rejected")
        self.assertEqual(self.world.effect_count("reschedule"), 0)
        self.assertEqual(self.store.intent(self.intent().action_id).state, "rejected")
        self.assertFalse(any(c.operation == "create_return" for c in self.world.calls))

    def test_window_proposal_selection_uses_only_just_read_slots_and_costs_ten_calls(self):
        self.gateway.bind_request(make_request(), DEADLINE)
        cp = self.store.checkpoint("C1")
        self.store.save_checkpoint(PhaseCheckpoint.model_validate({**cp.model_dump(), "phase": "window_gate", "next_gate": "window_gate",
                                 "ownership_state": "accepted", "ownership_state_revision": "v1"}))
        def select(request, observations):
            facts = {o.authority + "." + o.fact: o.value for o in observations}
            self.assertIsInstance(observations, tuple)
            slot = facts["scheduling.capacity"][0]
            return ActionProposal(operation="reschedule", stage="commit", arguments={"slot": slot}, evidence_refs=[]), {"slot": slot}
        self.assertEqual(self.gateway.execute_proposal("C1", "reschedule", select).status, "verified")
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 10)
        self.assertEqual(len(self.world.calls), 10)

    def test_mutated_or_unknown_proposal_operation_never_enters_transport(self):
        self.ready()
        def substitute(request, observations):
            return self.builder("send_status")(request, observations)
        self.assertEqual(self.gateway.execute_proposal("C1", "reschedule", substitute).status, "rejected")
        self.assertEqual(self.world.effect_count("send_status"), 0)
        count = len(self.world.calls)
        self.assertEqual(self.gateway.execute_proposal("C1", "invented", substitute).status, "rejected")
        self.assertEqual(len(self.world.calls), count)

    def test_pacing_rechecks_absolute_deadline_after_trusted_wait(self):
        self.ready()
        class LateClock(PacingClock):
            def wait(clock, seconds):
                clock.advance(7201)
        self.gateway.clock = LateClock()
        self.assertEqual(self.gateway.execute(self.intent()).status, "rejected")
        self.assertEqual(len(self.world.calls), 0)
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 0)

    def test_failed_bootstrap_commit_prevents_identity_read_transport(self):
        self.store._before_commit = lambda: (_ for _ in ()).throw(JournalFailure("secret:commit-canary"))
        with self.assertRaises(GateDenied) as caught:
            self.gateway.bind_request(make_request(), DEADLINE)
        self.assertEqual(str(caught.exception), "scope_denied")
        self.assertEqual(len(self.world.calls), 0)
        self.store._before_commit = None

    def test_raw_transport_exception_is_sanitized_and_keeps_read_debt(self):
        self.ready()
        original = self.gateway.bundle.case
        class BrokenCase:
            def read_case(self, request):
                raise RuntimeError("secret:exception-canary")
            def read_principal(self, request):
                return original.read_principal(request)
        from dataclasses import replace
        self.gateway.bundle = replace(self.gateway.bundle, case=BrokenCase())
        result = self.gateway.execute(self.intent())
        self.assertEqual(result.status, "rejected")
        self.assertNotIn("canary", result.model_dump_json())
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 1)
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 10)

    def test_shared_provider_backpressure_charges_read_and_cannot_grant_effect(self):
        self.ready()
        self.world.set_fault("read_case", "429")
        self.assertEqual(self.gateway.execute(self.intent()).status, "rejected")
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 1)
        self.assertEqual(self.world.effect_count("reschedule"), 0)

    def test_stale_vector_scope_or_immutable_postcondition_denies_effect(self):
        covered = self.profile.capabilities["reschedule"].conditional_coverage.covered_fields
        for changes in ({"expected_revisions": RevisionVector(revisions={key: "v2" for key in covered})},
                        {"postcondition": {"slot": "S2"}}, {"ownership_epoch": 1}, {"ownership_state_revision": "v2"},
                        {"profile_version": "v1"}, {"stage": "deliver"}):
            with self.subTest(changes=changes):
                test = GatewayTests("test_stale_vector_scope_or_immutable_postcondition_denies_effect")
                test.setUp()
                try:
                    test.ready()
                    self.assertEqual(test.gateway.execute(test.intent(**changes)).status, "rejected")
                    self.assertEqual(test.world.effect_count("reschedule"), 0)
                finally:
                    test.doCleanups()

    def test_effect_uses_committed_short_lease_without_rewriting_original_intent(self):
        self.ready()
        intent = self.intent()
        self.store.consume("C1", "active_seconds", 119, self.clock.now())
        original = self.gateway.bundle.scheduling
        outer = self
        class LateScheduling:
            def __getattr__(self, name):
                return getattr(original, name)
            def reschedule(self, supplied, *, deadline=None):
                outer.assertEqual(supplied, intent)
                outer.assertEqual(deadline, outer.clock.now() + timedelta(seconds=1))
                outer.clock.advance(2)
                return original.reschedule(supplied, deadline=deadline)
        from dataclasses import replace
        self.gateway.bundle = replace(self.gateway.bundle, scheduling=LateScheduling())
        result = self.gateway.execute(intent)
        self.assertEqual(result.status, "outcome_unknown")
        self.assertEqual(self.world.effect_count("reschedule"), 0)
        self.assertEqual(self.store.intent(intent.action_id).intent, intent)
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 120)

    def test_wrong_provider_ack_identity_conflicts_with_independent_original_read(self):
        self.ready()
        original = self.gateway.bundle.scheduling
        from proofkey.contracts import DispatchResult
        class WrongAckScheduling:
            def __getattr__(self, name):
                return getattr(original, name)
            def reschedule(self, intent, *, deadline=None):
                result = original.reschedule(intent, deadline=deadline)
                return DispatchResult.model_validate({**result.model_dump(), "provider_request_id": "provider:foreign-key"})
        from dataclasses import replace
        self.gateway.bundle = replace(self.gateway.bundle, scheduling=WrongAckScheduling())
        self.assertEqual(self.gateway.execute(self.intent()).status, "conflict")
        self.assertEqual(self.world.effect_count("reschedule"), 1)
        self.assertEqual(self.gateway.reconcile(self.intent().action_id).status, "conflict")
        self.assertEqual(self.store.intent(self.intent().action_id).state, "conflict")

    def test_key_and_argument_substitution_conflict_before_entry_preserving_exact_original(self):
        self.ready()
        intent = self.intent()
        self.store.prepare(intent)
        for changes in ({"provider_key": "foreign-key"}, {"postcondition": {"slot": "S2"}},
                        {"arguments": {"slot": "S2"}}):
            self.assertEqual(self.gateway.execute(self.intent(**changes)).status, "conflict")
            self.assertEqual(self.store.intent(intent.action_id).intent, intent)
            self.assertEqual(self.store.intent(intent.action_id).state, "prepared")
        self.assertEqual(len(self.world.calls), 0)

    def test_structured_only_first_admission_disables_both_planning_allowances(self):
        self.gateway.bind_request(make_request(), DEADLINE)
        budget = self.store.checkpoint("C1").budget
        self.assertEqual(budget.max_planner_calls, 0)
        self.assertEqual(budget.role_allowances["planning"].max_invocations, 0)

    def test_evidence_bearing_no_text_input_is_not_structured_only(self):
        self.gateway.bind_request(make_request(evidence_ids=["artifact:audio"]), DEADLINE)
        budget = self.store.checkpoint("C1").budget
        self.assertEqual(budget.max_planner_calls, 4)
        self.assertEqual(budget.role_allowances["planning"].max_invocations, 4)

    def test_new_generation_preserves_zero_planning_original_debt_and_sticky_stop(self):
        old = self.gateway.bind_request(make_request(), DEADLINE)
        self.store.set_stop("C1", "G1")
        self.world.mutate("case.generation", "G2")
        self.world.mutate("case.request_revision", "v2")
        self.world.mutate("customer.consent_revision", "v2")
        revised = make_request(request_revision="v2", consent_revision="v2", narrative="New authenticated text")
        new = self.gateway.bind_request(revised, DEADLINE)
        self.assertEqual(new.generation, "G2")
        self.assertEqual(new.supersedes_generation, "G1")
        self.assertEqual(self.store.original_request("C1", "G1"), make_request())
        self.assertEqual(self.store.original_request("C1", "G2"), revised)
        checkpoint = self.store.checkpoint("C1")
        self.assertEqual(checkpoint.budget.max_planner_calls, 0)
        self.assertEqual(checkpoint.budget.role_allowances["planning"].max_invocations, 0)
        self.assertEqual(checkpoint.budget.tool_calls, 4)
        self.assertTrue(checkpoint.stop.requested)

    def test_read_helper_rechecks_short_original_deadline_after_observed_completion(self):
        self.ready()
        original = self.gateway.bundle.scheduling
        outer = self
        class DelayedScheduling:
            def list_permitted_slots(self, request):
                reply = original.list_permitted_slots(request)
                outer.clock.advance(.2)
                return reply
        from dataclasses import replace
        self.gateway.bundle = replace(self.gateway.bundle, scheduling=DelayedScheduling())
        with self.assertRaises(GateDenied):
            self.gateway.read_material_authorities(self.intent(deadline=NOW + timedelta(seconds=.65)))
        self.assertEqual(self.world.effect_count("reschedule"), 0)
