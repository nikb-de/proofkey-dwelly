"""SQLite control integrity only; none of these stored claims authenticate a caller."""
from pathlib import Path
import json
import sqlite3
import tempfile
import unittest

from proofkey.contracts import ReadTarget, StopState
from proofkey.journal import CaseStore, JournalFailure
from support import NOW, DEADLINE, CommitFault, make_auth, make_binding, make_checkpoint, make_request, make_intent


class ControlStorageTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "control.sqlite"
        self.store = CaseStore(self.path)
        self.addCleanup(lambda: self.store.close())
        self.store.admit(make_binding(), make_request(), make_checkpoint())

    def reopen(self):
        self.store.close()
        self.store = CaseStore(self.path)

    def test_stopped_no_intent_no_result_control_read_keeps_unknown_debt(self):
        # A generic stopped-read branch wrongly used for control would deny this.
        self.store.set_stop("C1", "G1")
        target = ReadTarget(kind="authority_facts", authority="case", facts=["binding"])
        lease = self.store.begin_control_read(make_binding(), target, "stop", NOW)
        self.assertIsNotNone(lease, "Stopped original must reserve its narrow physical control read")
        self.reopen()
        self.assertEqual(self.store.entry(lease.entry_id).state, "active")
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 1)
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 10.0)
        self.assertTrue(self.store.checkpoint("C1").stop.requested)
        self.assertEqual(self.store.intents("C1"), ())
        self.assertIsNone(self.store.saved_result("C1", "G1"))

    def test_explicit_refusal_after_stopped_reschedule_preserves_stop_and_debt(self):
        # Using generic admission would inherit stop and strand the explicit refusal.
        self.store.set_stop("C1", "G1")
        request = make_request(request_id="REQ2", kind="service_refusal", consent_mode="unknown")
        binding = make_binding(request=request, generation="G2", supersedes_generation="G1")
        self.store.start_admission("a2", make_auth(), request, NOW, DEADLINE)
        self.store.begin_admission_read("a2", NOW)  # unknown outcome: full charge remains
        checkpoint = make_checkpoint(binding=binding, phase="intake", next_gate="extract_input")
        self.store.admit_refusal_after_stopped_reschedule("a2", binding, request, checkpoint, make_binding())
        self.reopen()
        current = self.store.checkpoint("C1")
        self.assertFalse(current.stop.requested, "Dedicated explicit refusal must have independent generation stop")
        self.assertEqual(current.binding, binding)
        self.assertEqual((current.budget.tool_calls, current.budget.active_seconds), (1, 10.0))
        self.assertEqual(current.deadline, DEADLINE)
        self.assertEqual(self.store.original_request("C1", "G1"), make_request())
        self.assertEqual(self.store.original_request("C1", "G2"), request)
        self.assertTrue(self.store.generation_stop(make_binding()).requested)
        self.assertFalse(self.store.generation_stop(binding).requested)

    def refusal(self):
        request = make_request(request_id="REQ2", kind="service_refusal", consent_mode="unknown")
        binding = make_binding(request=request, generation="G2", supersedes_generation="G1")
        self.store.start_admission("a2", make_auth(), request, NOW, DEADLINE)
        return request, binding, make_checkpoint(binding=binding, phase="intake", next_gate="extract_input")

    def test_control_target_purpose_and_binding_are_narrow(self):
        self.store.set_stop("C1", "G1")
        for binding, target, purpose in (
            (make_binding(), ReadTarget(kind="authority_facts", authority="delivery", facts=["status"]), "stop"),
            (make_binding(), ReadTarget(kind="authority_facts", authority="customer", facts=["consent"]), "reply"),
            (make_binding(), ReadTarget(kind="authority_facts", authority="case", facts=["binding"]), "refusal_admission"),
            (make_binding(generation="other"), ReadTarget(kind="authority_facts", authority="case", facts=["binding"]), "stop"),
            (make_binding(case_id="other"), ReadTarget(kind="authority_facts", authority="case", facts=["binding"]), "stop")):
            with self.assertRaises(JournalFailure):
                self.store.begin_control_read(binding, target, purpose, NOW)
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 0)
        with self.assertRaises(JournalFailure):
            self.store.begin_read("C1", NOW)
        with self.assertRaises(JournalFailure):
            self.store.begin_disclosure_read(make_binding(), NOW)

    def test_control_lease_valid_payload_substitution_denies_settlement(self):
        lease = self.store.begin_control_read(make_binding(), ReadTarget(kind="authority_facts", authority="case", facts=["binding"]), "stop", NOW)
        raw = lease.model_dump(mode="json")
        raw["control_scope"]["target"]["facts"] = ["generation"]
        db = sqlite3.connect(self.path)
        db.execute("UPDATE entries SET lease_json=? WHERE entry_id=?", (json.dumps(raw), lease.entry_id))
        db.commit()
        db.close()
        with self.assertRaises(JournalFailure):
            self.store.finish_entry(lease.entry_id, 1.0)
        db = sqlite3.connect(self.path)
        try:
            self.assertEqual(json.loads(db.execute("SELECT checkpoint_json FROM cases WHERE case_id='C1'").fetchone()[0])[
                "budget"]["active_seconds"], 10.0)
        finally:
            db.close()

    def test_control_settlement_reopens_exact_scope_and_refunds_only_observed_time(self):
        lease = self.store.begin_control_read(make_binding(), ReadTarget(kind="authority_facts", authority="ownership", facts=["epoch"]), "recorded_state", NOW)
        self.store.finish_entry(lease.entry_id, 2.0)
        self.reopen()
        self.assertEqual(self.store.entry(lease.entry_id).control_scope.binding, make_binding())
        self.assertEqual((self.store.checkpoint("C1").budget.tool_calls, self.store.checkpoint("C1").budget.active_seconds), (1, 2.0))
        with self.assertRaises(JournalFailure):
            self.store.finish_entry(lease.entry_id, 0.0)

    def test_stripping_control_tag_cannot_decode_as_legacy_read(self):
        lease = self.store.begin_control_read(make_binding(), ReadTarget(kind="authority_facts", authority="case", facts=["binding"]), "stop", NOW)
        raw = lease.model_dump(mode="json")
        raw.pop("control_scope")
        db = sqlite3.connect(self.path)
        db.execute("UPDATE entries SET lease_json=? WHERE entry_id=?", (json.dumps(raw), lease.entry_id))
        db.commit()
        db.close()
        with self.assertRaises(JournalFailure):
            self.store.entry(lease.entry_id)

    def test_restricted_refusal_rejects_unstopped_or_stale_predecessor_and_stale_question(self):
        request, binding, checkpoint = self.refusal()
        with self.assertRaises(JournalFailure):
            self.store.admit_refusal_after_stopped_reschedule("a2", binding, request, checkpoint, make_binding())
        self.store.set_stop("C1", "G1")
        for expected, incoming in ((make_binding(generation="other"), checkpoint),
                                   (make_binding(), checkpoint.model_copy(update={"question_id": "old"})),
                                   (make_binding(), checkpoint.model_copy(update={"phase": "completeness"})),
                                   (make_binding(), checkpoint.model_copy(update={"next_gate": "reschedule"})),
                                   (make_binding(), checkpoint.model_copy(update={"stop": StopState(requested=True)}))):
            with self.assertRaises(JournalFailure):
                self.store.admit_refusal_after_stopped_reschedule("a2", binding, request, incoming, expected)
        self.assertEqual(self.store.checkpoint("C1").binding, make_binding())
        self.assertEqual(self.store.admission_attempt("a2").state, "unbound")

    def test_refusal_commit_fault_keeps_original_stop_intents_and_admission_debt(self):
        self.store.prepare(make_intent())
        self.store.set_stop("C1", "G1")
        request, binding, checkpoint = self.refusal()
        self.store.begin_admission_read("a2", NOW)
        current = self.store.checkpoint("C1")
        fault = CommitFault()
        self.store.close()
        self.store = CaseStore(self.path, before_commit=fault)
        fault.arm()
        with self.assertRaises(JournalFailure):
            self.store.admit_refusal_after_stopped_reschedule("a2", binding, request, checkpoint, make_binding())
        self.reopen()
        self.assertEqual(self.store.checkpoint("C1"), current)
        self.assertTrue(self.store.generation_stop(make_binding()).requested)
        self.assertEqual(self.store.intents("C1")[0].intent, make_intent())
        self.assertEqual(self.store.admission_attempt("a2").state, "unbound")
        self.store.admit_refusal_after_stopped_reschedule("a2", binding, request, checkpoint, make_binding())
        self.assertEqual(self.store.intents("C1")[0].intent, make_intent())
        with self.assertRaises(JournalFailure):
            self.store.begin_dispatch(make_intent(), NOW)
        with self.assertRaises(JournalFailure):
            self.store.admit_refusal_after_stopped_reschedule("a2", binding, request, checkpoint, make_binding())

    def test_refusal_history_keeps_original_stop_detail_and_rejects_corruption(self):
        self.store.save_checkpoint(self.store.checkpoint("C1").model_copy(update={
            "stop": StopState(requested=True, requested_at=NOW, reason="fixture original stop")}))
        request, binding, checkpoint = self.refusal()
        self.store.admit_refusal_after_stopped_reschedule("a2", binding, request, checkpoint, make_binding())
        self.reopen()
        self.assertEqual(self.store.generation_stop(make_binding()).reason, "fixture original stop")
        db = sqlite3.connect(self.path)
        rows = db.execute("SELECT sequence,event_json FROM audit").fetchall()
        seq, raw = next((seq, json.loads(raw)) for seq, raw in rows if json.loads(raw).get("refusal_history"))
        raw["refusal_history"]["predecessor_input_hash"] = "0" * 64
        db.execute("UPDATE audit SET event_json=? WHERE sequence=?", (json.dumps(raw), seq))
        db.commit()
        db.close()
        with self.assertRaises(JournalFailure):
            CaseStore(self.path)
