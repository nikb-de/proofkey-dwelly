"""Historical disclosure uses independent provider state and durable accounting."""
from dataclasses import replace
from datetime import timedelta
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from proofkey.adapters.world import SimulatedWorld
from proofkey.contracts import AuthorityReadback, CaseResult, EnvironmentProfile
from proofkey.identity import request_fingerprint
from proofkey.journal import CaseStore
from proofkey.replay import ReplayService
from support import (NOW, CommitFault, FakeClock, load_test_profile, make_auth,
                     make_binding, make_checkpoint, make_request, make_result)


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.profile = load_test_profile("flat-v1.2")
        self.clock = FakeClock()
        self.world = SimulatedWorld(self.root / "world.sqlite", Path(__file__).resolve().parents[1] /
            "fixtures/development/world.json", profile=self.profile, clock=self.clock)
        self.fault = CommitFault()
        self.store = CaseStore(self.root / "journal.sqlite", before_commit=self.fault)
        self.addCleanup(self.store.close)
        self.bundle = self.world.bundle()
        self.auth = make_auth()
        self.request = make_request(kind="goods_refusal", consent_mode="unknown",
                                    arguments={"inventory": {"item-1": 1}})
        # Trusted setup precedes execution, never derives provider authority at lookup.
        self.world.mutate("customer.request_fingerprint", request_fingerprint(self.request))
        self.world.mutate("customer.consent_mode", self.request.consent_mode)
        self.world.mutate("delivery.status", "delivered")
        self.binding = make_binding(request=self.request)
        self.saved = None

    def save(self, *, request=None, stopped=False, budget=None):
        request = request or self.request
        self.request, self.binding = request, make_binding(request=request)
        checkpoint = make_checkpoint(binding=self.binding, phase="complete", next_gate="saved_result",
            processing_status="completed", **({"budget": budget} if budget is not None else {}))
        self.store.admit(self.binding, request, checkpoint)
        if stopped:
            self.store.set_stop("C1", "G1")
            self.store.save_checkpoint(make_checkpoint(binding=self.binding, phase="stopped",
                next_gate="saved_result", processing_status="completed"))
        effects = ({"reschedule": {"status": "outcome_unknown"}} if request.kind.startswith("reschedule")
                   else {"create_return": {"status": "outcome_unknown"}})
        self.saved = make_result(binding=self.binding, effects=effects,
            stop=self.store.checkpoint("C1").stop, result_version="result-17", as_of=NOW - timedelta(minutes=2),
            handoff_status="pending", media_status="outcome_unknown")
        self.store.save_result(self.saved)

    def lookup(self, request=None, auth=None, bundle=None, profile=None):
        return ReplayService(profile or self.profile, bundle or self.bundle, self.store, self.clock).lookup(
            request or self.request, auth if auth is not None else self.auth)

    def denied(self, result):
        self.assertIsInstance(result, CaseResult)
        self.assertEqual(result.model_dump(mode="json"),
                         {"status": "denied", "correlation_id": "C1", "reason": "denied"})
        self.assertIsNone(result.binding)
        self.assertEqual(result.effects, {})
        self.assertEqual(result.evidence_refs, [])

    def no_business(self):
        self.assertTrue(all(call.operation == "read_case" and call.purpose == "disclosure"
                            for call in self.world.calls))
        for operation in ("reschedule", "register_goods_refusal", "register_service_refusal", "create_return",
                          "send_clarification", "send_status", "enqueue_handoff", "transfer_owner"):
            self.assertEqual(self.world.effect_count(operation), 0)
        checkpoint = self.store.checkpoint("C1")
        self.assertEqual(checkpoint.budget.planner_calls, 0)
        self.assertEqual(checkpoint.budget.effects, 0)
        self.assertEqual(checkpoint.budget.reconciliation_reads, {})
        self.assertEqual(self.store.intents("C1"), ())
        with sqlite3.connect(self.root / "journal.sqlite") as db:
            self.assertEqual(db.execute("SELECT count(*) FROM invocations").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT count(*) FROM requests").fetchone()[0], 1)

    def test_historical_unknown_replay_has_no_business_calls(self):
        self.save()
        before = self.store.saved_result("C1", "G1").model_dump_json()
        self.world.mutate("returns.status", "received")
        result = self.lookup()
        self.assertIsInstance(result, CaseResult)
        self.assertTrue(result.historical)
        self.assertEqual(result.effects["create_return"].status, "outcome_unknown")
        expected = json.loads(before)
        expected["historical"] = True
        self.assertEqual(result.model_dump(mode="json"), expected)
        self.assertEqual(self.store.saved_result("C1", "G1").model_dump_json(), before)
        self.assertEqual(self.store.original_request("C1", "G1"), self.request)
        self.no_business()

    def test_stopped_schedule_replay_retains_stop(self):
        self.save(request=make_request(), stopped=True)
        before = self.store.checkpoint("C1")
        result = self.lookup()
        self.assertIsInstance(result, CaseResult)
        self.assertTrue(result.historical)
        self.assertTrue(result.stop.requested)
        self.assertEqual(result.effects["reschedule"].status, "outcome_unknown")
        after = self.store.checkpoint("C1")
        self.assertEqual((after.phase, after.next_gate, after.stop), (before.phase, before.next_gate, before.stop))
        self.assertEqual(after.budget.tool_calls, 1)
        self.no_business()

    def test_business_consent_revocation_does_not_revoke_disclosure(self):
        self.save()
        self.world.mutate("customer.consent", "revoked")
        self.world.mutate("customer.consent_revision", "revoked-v2")
        result = self.lookup()
        self.assertIsInstance(result, CaseResult)
        self.assertTrue(result.historical)
        self.assertEqual(result.binding.consent_revision, "v1")
        self.no_business()

    def test_revoked_current_acl_withholds_all_saved_details(self):
        self.save()
        self.world.mutate("case.authorization", "revoked")
        self.denied(self.lookup())
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 1)
        self.no_business()

    def test_wrong_or_revoked_proof_cannot_use_storage_as_authority(self):
        self.save()
        self.denied(self.lookup(auth=make_auth(proof_reference="revoked-proof")))
        self.denied(self.lookup(auth=make_auth(caller_id="OTHER")))
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 2)
        self.no_business()

    def test_unverifiable_access_retains_reserved_active_slice(self):
        self.save()
        self.world.set_fault("read_case", "timeout_before")
        self.denied(self.lookup())
        budget = self.store.checkpoint("C1").budget
        self.assertEqual((budget.tool_calls, budget.active_seconds), (1, 10.0))
        self.no_business()

    def test_wrong_provider_object_is_generic_denial(self):
        self.save()
        self.world.set_fault("read_case", "wrong_object")
        self.denied(self.lookup())
        self.no_business()

    def test_current_case_identity_cannot_be_replaced_by_saved_binding(self):
        self.save()
        self.world.mutate("case.binding", {"case_id": "C1", "object_id": "O1",
            "principal_id": "OTHER", "request_id": "REQ1"})
        self.denied(self.lookup())
        self.no_business()

    def test_exhausted_tool_allowance_blocks_disclosure_without_new_read(self):
        self.save()
        self.store.consume("C1", "tool_calls", 24, self.clock.now())
        self.denied(self.lookup())
        self.assertEqual(self.world.calls, ())
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 24)

    def test_exhausted_deadline_blocks_disclosure_without_new_read(self):
        self.save()
        self.clock.advance(7200)
        self.denied(self.lookup())
        self.assertEqual(self.world.calls, ())
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 0)

    def test_exhausted_active_allowance_blocks_disclosure_without_new_read(self):
        self.save()
        self.store.consume("C1", "active_seconds", 120.0, self.clock.now())
        self.denied(self.lookup())
        self.assertEqual(self.world.calls, ())

    def test_commit_failure_prevents_provider_entry(self):
        self.save()
        self.fault.arm()
        self.denied(self.lookup())
        self.assertEqual(self.world.calls, ())
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 0)

    def test_same_intent_with_mismatched_identity_or_revision_is_denied(self):
        self.save()
        for changes in ({"object_id": "OTHER"}, {"principal_id": "OTHER"},
                        {"request_revision": "v2"}, {"consent_revision": "v2"}):
            with self.subTest(changes=changes):
                candidate = make_request(**{**self.request.model_dump(), **changes})
                self.denied(self.lookup(candidate))
        self.assertEqual(self.world.calls, ())
        self.no_business()

    def test_distinct_request_id_with_same_business_arguments_is_not_replay(self):
        self.save()
        candidate = make_request(**{**self.request.model_dump(), "request_id": "REQ2"})
        self.assertIsNone(self.lookup(candidate))
        self.assertEqual(self.world.calls, ())
        self.no_business()

    def test_changed_business_arguments_are_not_permission_from_old_request_id(self):
        self.save()
        candidate = make_request(**{**self.request.model_dump(), "arguments": {"inventory": {"item-1": 2}}})
        self.assertIsNone(self.lookup(candidate))
        self.assertEqual(self.world.calls, ())
        self.no_business()

    def test_new_business_intent_is_not_replay_or_permission(self):
        self.save()
        candidate = make_request(request_id="REQ2", kind="service_refusal", consent_mode="unknown",
                                 arguments={"scope": "service"})
        self.assertIsNone(self.lookup(candidate))
        self.assertEqual(self.world.calls, ())
        self.no_business()

    def test_missing_case_is_not_an_authorized_result(self):
        self.assertIsNone(self.lookup())
        self.assertEqual(self.world.calls, ())

    def test_exact_incomplete_request_returns_no_replay_and_preserves_phase(self):
        self.store.admit(self.binding, self.request, make_checkpoint(binding=self.binding))
        before = self.store.checkpoint("C1")
        self.assertIsNone(self.lookup())
        self.assertEqual(self.store.checkpoint("C1"), before)
        self.assertEqual(self.world.calls, ())
        self.no_business()

    def test_incomplete_request_changed_input_lineage_cannot_restart(self):
        self.store.admit(self.binding, self.request, make_checkpoint(binding=self.binding))
        candidate = make_request(**{**self.request.model_dump(), "evidence_ids": ["NEW-ARTIFACT"]})
        self.denied(self.lookup(candidate))
        self.assertEqual(self.world.calls, ())
        self.no_business()

    def test_saved_result_without_durable_original_is_not_authority(self):
        self.store.bind(self.binding)
        self.store.save_checkpoint(make_checkpoint(binding=self.binding))
        self.store.save_result(make_result(binding=self.binding))
        self.denied(self.lookup())
        self.assertEqual(self.world.calls, ())

    def test_completed_duplicate_keeps_original_evidence_despite_input_noise(self):
        self.save()
        candidate = make_request(**{**self.request.model_dump(), "evidence_ids": ["NEW-ARTIFACT"],
                                   "narrative": "Please send the saved result"})
        result = self.lookup(candidate)
        self.assertIsInstance(result, CaseResult)
        self.assertTrue(result.historical)
        self.assertEqual(self.store.original_request("C1", "G1"), self.request)
        self.no_business()

    def test_lease_is_committed_before_public_read_and_uses_exact_scope(self):
        self.save()
        original = self.bundle.case
        outer = self
        class Observer:
            def read_case(self, request):
                with sqlite3.connect(outer.root / "journal.sqlite") as db:
                    raw = db.execute("SELECT lease_json FROM entries").fetchone()[0]
                    lease = json.loads(raw)
                outer.assertEqual(lease["kind"], "disclosure_read")
                outer.assertEqual(lease["generation"], "G1")
                outer.assertEqual(request.case_id, "C1")
                outer.assertEqual(request.object_id, "O1")
                outer.assertEqual(request.caller_id, "U1")
                outer.assertEqual(request.proof_reference, "synthetic-proof")
                outer.assertEqual(request.purpose, "disclosure")
                outer.assertEqual(request.target.model_dump(), {"kind": "authority_facts", "authority": "case",
                    "facts": ["authorization", "binding"], "operation": None, "generation": None,
                    "action_id": None, "provider_key": None, "fingerprint": None, "transfer_id": None,
                    "packet_id": None, "packet_revision": None, "question_id": None})
                outer.assertLessEqual(request.deadline, outer.clock.now() + timedelta(seconds=10))
                return original.read_case(request)
            def read_principal(self, request):
                raise AssertionError("Business consent is not disclosure ACL")
        result = self.lookup(bundle=replace(self.bundle, case=Observer()))
        self.assertIsInstance(result, CaseResult)
        self.assertTrue(result.historical)
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 0.0)

    def test_repeated_replays_charge_remaining_current_ledger_without_reset(self):
        self.save()
        self.store.consume("C1", "tool_calls", 2, self.clock.now())
        self.store.consume("C1", "active_seconds", 3.0, self.clock.now())
        before = self.store.checkpoint("C1")
        for _ in range(2):
            result = self.lookup()
            self.assertIsInstance(result, CaseResult)
            self.assertTrue(result.historical)
        after = self.store.checkpoint("C1")
        self.assertEqual(after.budget.tool_calls, 4)
        self.assertEqual(after.budget.active_seconds, 3.0)
        self.assertEqual(after.budget.deadline, before.budget.deadline)
        self.assertEqual(after.budget.max_tool_calls, before.budget.max_tool_calls)
        self.assertEqual((after.phase, after.processing_status), (before.phase, before.processing_status))
        self.no_business()

    def test_historical_old_generation_charges_newer_case_ledger(self):
        self.save(request=make_request(), stopped=True)
        old_request, old_saved = self.request, self.saved
        newer_request = make_request(request_id="REQ2", request_revision="v2", kind="goods_refusal",
                                     consent_mode="unknown", arguments={"inventory": {"item-1": 1}})
        newer = make_binding(request=newer_request, generation="G2", supersedes_generation="G1")
        self.store.admit(newer, newer_request, make_checkpoint(binding=newer))
        self.store.consume("C1", "tool_calls", 3, self.clock.now())
        self.world.mutate("case.binding", {"case_id": "C1", "object_id": "O1", "principal_id": "U1",
                                           "request_id": "REQ2"})
        result = self.lookup(old_request)
        self.assertIsInstance(result, CaseResult)
        self.assertEqual(result.binding.generation, "G1")
        self.assertEqual(result.stop, old_saved.stop)
        after = self.store.checkpoint("C1")
        self.assertEqual(after.binding, newer)
        self.assertEqual(after.budget.tool_calls, 4)
        self.assertTrue(after.stop.requested)
        candidate = make_request(**{**old_request.model_dump(), "consent_revision": "wrong-old-revision"})
        self.denied(self.lookup(candidate))
        with sqlite3.connect(self.root / "journal.sqlite") as db:
            self.assertEqual(db.execute("SELECT count(*) FROM requests").fetchone()[0], 2)

    def test_returned_projection_cannot_mutate_saved_unknown(self):
        self.save()
        result = self.lookup()
        self.assertIsInstance(result, CaseResult)
        with self.assertRaises(TypeError):
            result.effects.clear()
        with self.assertRaises(TypeError):
            result.evidence_refs.clear()
        saved = self.store.saved_result("C1", "G1")
        self.assertEqual(saved.effects["create_return"].status, "outcome_unknown")
        self.assertEqual(saved.evidence_refs, ["synthetic-evidence"])

    def test_supported_read_contract_without_evidence_cannot_disclose(self):
        self.save()
        data = self.profile.model_dump()
        data["capabilities"]["read_authority"]["permission_basis"]["evidence_ref"] = None
        profile = EnvironmentProfile.model_validate(data)
        self.denied(self.lookup(profile=profile))
        self.assertEqual(self.world.calls, ())

    def test_missing_auth_is_generic_denial_without_provider_entry(self):
        self.save()
        result = ReplayService(self.profile, self.bundle, self.store, self.clock).lookup(self.request, None)
        self.denied(result)
        self.assertEqual(self.world.calls, ())

    def test_provider_exception_leaves_committed_unknown_entry_consumed(self):
        self.save()
        class FailingPort:
            def read_case(self, request):
                raise RuntimeError("private-provider-error-canary")
        self.denied(self.lookup(bundle=replace(self.bundle, case=FailingPort())))
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 10.0)
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 1)

    def test_stale_acl_observation_and_deadline_overrun_do_not_disclose(self):
        self.save()
        original, outer = self.bundle.case, self
        class StalePort:
            def read_case(self, request):
                raw = original.read_case(request).model_dump()
                raw["as_of"] = NOW - timedelta(seconds=1)
                return AuthorityReadback.model_validate(raw)
        self.denied(self.lookup(bundle=replace(self.bundle, case=StalePort())))
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 10.0)
        class LatePort:
            def read_case(self, request):
                reply = original.read_case(request)
                outer.clock.advance(11)
                return reply
        self.denied(self.lookup(bundle=replace(self.bundle, case=LatePort())))
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 120.0)
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 2)

    def test_reopened_journal_preserves_historical_unknown_and_budget(self):
        self.save()
        self.store.consume("C1", "tool_calls", 2, self.clock.now())
        self.store.close()
        self.store = CaseStore(self.root / "journal.sqlite")
        self.addCleanup(self.store.close)
        result = self.lookup()
        self.assertIsInstance(result, CaseResult)
        self.assertTrue(result.historical)
        self.assertEqual(result.effects["create_return"].status, "outcome_unknown")
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 3)
        self.no_business()

    def test_replay_has_zero_network_entries_and_processing_invocations(self):
        self.save()
        # Guard the external boundary; journal/world behavior stays real.
        with patch("socket.create_connection", side_effect=AssertionError("Unexpected network entry")) as network:
            result = self.lookup()
            self.assertIsInstance(result, CaseResult)
            self.assertTrue(result.historical)
            self.assertEqual(network.call_count, 0)
        self.no_business()


if __name__ == "__main__":
    unittest.main()
