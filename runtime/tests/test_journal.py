"""Real SQLite persistence, immutable identity, transaction and kill boundaries."""
import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from proofkey.contracts import VerificationResult
from proofkey.identity import fingerprint
from proofkey.journal import CaseStore, JournalFailure
from support import NOW, CommitFault, make_binding, make_checkpoint, make_intent, make_result, make_request


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "journal.sqlite"
        self.store = CaseStore(self.path)
        self.addCleanup(lambda: self.store.close())
        self.store.bind(make_binding())
        self.store.save_request(make_binding(), make_request())
        self.store.save_checkpoint(make_checkpoint())

    def reopen(self):
        self.store.close()
        self.store = CaseStore(self.path)

    def test_restart_preserves_stop_identity_and_debit(self):
        intent = make_intent()
        self.store.prepare(intent)
        self.store.consume("C1", "tool_calls", 1, NOW)
        self.store.set_stop("C1", "G1")
        self.reopen()
        self.assertTrue(self.store.checkpoint("C1").stop.requested)
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 1)
        self.assertEqual(self.store.intents("C1")[0].intent, intent)
        self.assertEqual(self.store.settings, {"journal_mode": "wal", "synchronous": 2, "foreign_keys": 1})

    def test_all_phase_and_gate_state_survive_without_result(self):
        for phase in ("start", "wait_customer", "handoff_pending", "outcome_unknown", "stopped", "complete"):
            self.store.save_checkpoint(make_checkpoint(phase=phase, next_gate="original-key-read"))
            self.reopen()
            self.assertEqual(self.store.checkpoint("C1").phase, phase)
            self.assertEqual(self.store.checkpoint("C1").next_gate, "original-key-read")
            self.assertIsNone(self.store.saved_result("C1", "G1"))

    def test_request_fingerprint_conflict_and_exact_find(self):
        self.assertEqual(self.store.find_request("C1", "REQ1", "v1", "v1", make_binding().fingerprint), make_binding())
        self.assertIsNone(self.store.find_request("C1", "REQ1", "v1", "v1", "0" * 64))
        with self.assertRaises(JournalFailure):
            self.store.bind(make_binding(fingerprint="0" * 64))

    def test_prepare_replay_preserves_full_immutable_intent(self):
        intent = make_intent()
        self.store.prepare(intent)
        self.store.prepare(intent)
        for changed in (make_intent(postcondition={"slot": "S2"}), make_intent(provider_key="other-key"),
                        make_intent(arguments={"slot": "S2"}, argument_fingerprint=fingerprint({"slot": "S2"}))):
            with self.assertRaises(JournalFailure):
                self.store.prepare(changed)
        record = self.store.intents("C1")[0]
        with self.assertRaises((AttributeError, TypeError, ValueError)):
            record.state = "verified"

    def test_commit_fault_rolls_back_prepare_and_dispatch_debit(self):
        self.store.close()
        fault = CommitFault()
        self.store = CaseStore(self.path, before_commit=fault)
        fault.arm()
        with self.assertRaises(JournalFailure):
            self.store.prepare(make_intent())
        self.assertEqual(self.store.intents("C1"), ())
        self.store.prepare(make_intent())
        fault.arm()
        with self.assertRaises(JournalFailure):
            self.store.begin_dispatch(make_intent(), NOW)
        self.reopen()
        self.assertEqual(self.store.intents("C1")[0].state, "prepared")
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 0)
        self.assertEqual(self.store.checkpoint("C1").budget.effects, 0)
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 0.0)
        with self.assertRaises(JournalFailure):
            self.store.entry("effect:" + make_intent().action_id + ":1")

    def test_stop_and_ownership_fence_prepared_dispatch(self):
        self.store.prepare(make_intent())
        self.store.set_stop("C1", "G1")
        with self.assertRaises(JournalFailure):
            self.store.begin_dispatch(make_intent(), NOW)
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 0)

    def test_changed_ownership_revision_fences_without_epoch_change(self):
        intent = make_intent(ownership_state_revision="state-1", ownership_epoch=0)
        self.store.save_checkpoint(make_checkpoint(ownership_state="accepted", ownership_state_revision="state-1"))
        self.store.prepare(intent)
        self.store.save_checkpoint(make_checkpoint(ownership_state="transfer_pending", ownership_state_revision="state-2"))
        with self.assertRaises(JournalFailure):
            self.store.begin_dispatch(intent, NOW)

    def test_verification_requires_matching_original_identity(self):
        self.store.prepare(make_intent())
        self.store.begin_dispatch(make_intent(), NOW)
        good = VerificationResult(status="verified", object_id="O1", action_id=make_intent().action_id,
            fingerprint=make_intent().argument_fingerprint, postcondition={"slot": "S1"}, evidence_refs=["readback-1"], as_of=NOW)
        bad = VerificationResult.model_validate({**good.model_dump(), "object_id": "O2"})
        with self.assertRaises(JournalFailure):
            self.store.record_verification(make_intent().action_id, bad)
        self.store.record_verification(make_intent().action_id, good)
        self.reopen()
        self.assertEqual(self.store.intents("C1")[0].verification, good)

    def test_saved_result_historical_identity_survives(self):
        self.store.save_result(make_result())
        self.reopen()
        self.assertEqual(self.store.saved_result("C1", "G1"), make_result())
        with self.assertRaises(JournalFailure):
            self.store.save_result(make_result(binding=make_binding(fingerprint="0" * 64)))

    def test_corrupt_checkpoint_fails_closed_on_read_and_open(self):
        raw = json.loads(self.store.checkpoint("C1").model_dump_json())
        raw["budget"]["tool_calls"] = "1"
        db = sqlite3.connect(self.path)
        db.execute("UPDATE cases SET checkpoint_json=?", (json.dumps(raw),))
        db.commit()
        db.close()
        with self.assertRaises(JournalFailure):
            self.store.checkpoint("C1")
        self.store.close()
        with self.assertRaises(JournalFailure):
            CaseStore(self.path)

    def test_incompatible_schema_never_migrates(self):
        self.store.close()
        db = sqlite3.connect(self.path)
        db.execute("UPDATE schema_meta SET version=999")
        db.commit()
        db.close()
        with self.assertRaises(JournalFailure):
            CaseStore(self.path)

    def test_frozen_checkpoint_versions_cannot_change(self):
        with self.assertRaises(JournalFailure):
            self.store.save_checkpoint(make_checkpoint(profile_version="future"))

    def test_historical_intent_version_corruption_fails_closed(self):
        self.store.prepare(make_intent())
        raw = make_intent().model_dump(mode="json")
        raw["profile_version"] = "future"
        db = sqlite3.connect(self.path)
        db.execute("UPDATE intents SET intent_json=?", (json.dumps(raw),))
        db.commit()
        db.close()
        with self.assertRaises(JournalFailure):
            self.store.intents("C1")

    def test_incompatible_table_shape_fails_on_open(self):
        self.store.close()
        db = sqlite3.connect(self.path)
        db.execute("ALTER TABLE cases ADD COLUMN unexpected TEXT")
        db.commit()
        db.close()
        with self.assertRaises(JournalFailure):
            CaseStore(self.path)

    def test_wait_and_transfer_roundtrip_have_historical_scope(self):
        from proofkey.contracts import WaitState, TransferIntent
        wait = WaitState(question_id="question-1", binding=make_binding(), origin="start", next_gate="resume",
            recipient="U1", owner_state_revision="state-1", awaited_fields=["slot"], expires_at=make_checkpoint().deadline,
            budget=make_checkpoint().budget)
        transfer = TransferIntent(transfer_id="transfer-1", binding=make_binding(), case_id="C1", packet_id="packet-1",
            packet_hash="3" * 64, packet_revision="v1", expected_owner="agent", expected_state_revision="state-1",
            expected_epoch=0, target_owner="operator", expires_at=make_checkpoint().deadline)
        self.store.save_wait(wait)
        self.store.save_transfer(transfer, "pending")
        self.reopen()
        self.assertEqual(self.store.wait("question-1"), wait)
        self.assertEqual(self.store.transfer("transfer-1").intent, transfer)
        self.assertEqual(self.store.transfer("transfer-1").state, "pending")

    def test_old_generation_dispatch_fenced_after_supersession(self):
        self.store.prepare(make_intent())
        newer = make_binding(generation="G2", request_revision="v2", supersedes_generation="G1")
        self.store.bind(newer)
        self.store.save_checkpoint(make_checkpoint(binding=newer))
        with self.assertRaises(JournalFailure):
            self.store.begin_dispatch(make_intent(), NOW)

    def test_original_request_roundtrip_and_immutable_input_lineage(self):
        request = make_request(case_id="C2", narrative="Untrusted customer words", evidence_ids=["input-a"])
        binding = make_binding(request=request)
        self.store.bind(binding)
        self.store.save_request(binding, request)
        self.reopen()
        self.assertEqual(self.store.original_request("C2", "G1"), request)
        for changed in (make_request(case_id="C2", kind="service_refusal", consent_mode="unknown"),
                        make_request(case_id="C2", evidence_ids=["input-b"]), make_request(case_id="C2", narrative="different words")):
            with self.assertRaises(JournalFailure):
                self.store.save_request(binding, changed)

    def test_atomic_admission_fault_leaves_no_partial_request(self):
        fault = CommitFault()
        store = CaseStore(Path(self.folder.name) / "atomic.sqlite", before_commit=fault)
        try:
            fault.arm()
            with self.assertRaises(JournalFailure):
                store.admit(make_binding(), make_request(), make_checkpoint())
            self.assertIsNone(store.find_request("C1", "REQ1", "v1", "v1", make_binding().fingerprint))
            store.admit(make_binding(), make_request(), make_checkpoint())
            self.assertEqual(store.original_request("C1", "G1").kind, "reschedule_window")
        finally:
            store.close()

    def test_entry_requires_durable_original_request(self):
        store = CaseStore(Path(self.folder.name) / "missing-original.sqlite")
        try:
            store.bind(make_binding())
            store.save_checkpoint(make_checkpoint())
            store.prepare(make_intent())
            with self.assertRaises(JournalFailure):
                store.begin_dispatch(make_intent(), NOW)
            self.assertEqual(store.checkpoint("C1").budget.tool_calls, 0)
        finally:
            store.close()

    def test_stop_stays_requested_across_phase_and_generation_changes(self):
        self.store.set_stop("C1", "G1")
        self.store.save_checkpoint(make_checkpoint(phase="complete", next_gate="saved"))
        newer = make_binding(generation="G2", request_revision="v2", supersedes_generation="G1")
        self.store.bind(newer)
        self.store.save_checkpoint(make_checkpoint(binding=newer))
        self.reopen()
        self.assertTrue(self.store.checkpoint("C1").stop.requested)

    def test_find_request_rejects_malformed_frozen_version_record(self):
        db = sqlite3.connect(self.path)
        db.execute("UPDATE requests SET versions_json=?", ('{"profile_version":true}',))
        db.commit()
        db.close()
        with self.assertRaises(JournalFailure):
            self.store.find_request("C1", "REQ1", "v1", "v1", make_binding().fingerprint)

    def test_prepared_state_cannot_carry_verification_without_dispatch_debit(self):
        self.store.prepare(make_intent())
        db = sqlite3.connect(self.path)
        db.execute("UPDATE intents SET verification_json=?", (VerificationResult(status="rejected").model_dump_json(),))
        db.commit()
        db.close()
        with self.assertRaises(JournalFailure):
            self.store.intents("C1")

    def test_disclosure_of_stopped_saved_generation_needs_no_effect(self):
        self.store.set_stop("C1", "G1")
        self.store.save_checkpoint(make_checkpoint(phase="stopped", next_gate="saved_result"))
        result = make_result(stop=self.store.checkpoint("C1").stop)
        self.store.save_result(result)
        lease = self.store.begin_disclosure_read(make_binding(), NOW)
        self.assertEqual(lease.kind, "disclosure_read")
        self.assertEqual(lease.generation, "G1")
        self.assertEqual(self.store.intents("C1"), ())
        self.assertEqual(self.store.saved_result("C1", "G1"), result)
        checkpoint = self.store.checkpoint("C1")
        self.assertEqual(checkpoint.phase, "stopped")
        self.assertEqual(checkpoint.next_gate, "saved_result")
        self.assertTrue(checkpoint.stop.requested)
        self.assertEqual(checkpoint.budget.tool_calls, 1)
        self.assertEqual(checkpoint.budget.active_seconds, 10.0)
        self.assertEqual(checkpoint.budget.effects, 0)
        self.assertEqual(checkpoint.budget.reconciliation_reads, {})
        with self.assertRaises(JournalFailure):
            self.store.begin_read("C1", NOW)
        self.reopen()
        self.assertEqual(self.store.entry(lease.entry_id), lease)

    def test_historical_disclosure_charges_current_case_without_reactivating_generation(self):
        self.store.set_stop("C1", "G1")
        result = make_result(stop=self.store.checkpoint("C1").stop)
        self.store.save_result(result)
        newer = make_binding(generation="G2", request_revision="v2", supersedes_generation="G1")
        self.store.admit(newer, make_request(request_revision="v2"), make_checkpoint(binding=newer))
        self.store.consume("C1", "tool_calls", 2, NOW)
        self.store.consume("C1", "active_seconds", 3.0, NOW)
        lease = self.store.begin_disclosure_read(make_binding(), NOW)
        checkpoint = self.store.checkpoint("C1")
        self.assertEqual(lease.generation, "G1")
        self.assertEqual(checkpoint.binding, newer)
        self.assertTrue(checkpoint.stop.requested)
        self.assertEqual(checkpoint.budget.tool_calls, 3)
        self.assertEqual(checkpoint.budget.active_seconds, 13.0)
        self.assertEqual(checkpoint.budget.effects, 0)
        self.assertEqual(checkpoint.budget.reconciliation_reads, {})
        self.assertEqual(self.store.saved_result("C1", "G1"), result)
        self.assertEqual(self.store.original_request("C1", "G1"), make_request())

    def test_disclosure_requires_exact_historical_input_and_saved_result(self):
        with self.assertRaises(JournalFailure):
            self.store.begin_disclosure_read(make_binding(), NOW)
        self.store.save_result(make_result())
        with self.assertRaises(JournalFailure):
            self.store.begin_disclosure_read(make_binding(fingerprint="0" * 64), NOW)
        absent = make_binding(case_id="C2")
        self.store.bind(absent)
        self.store.save_checkpoint(make_checkpoint(binding=absent))
        self.store.save_result(make_result(binding=absent))
        with self.assertRaises(JournalFailure):
            self.store.begin_disclosure_read(absent, NOW)
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 0)
        self.assertEqual(self.store.checkpoint("C2").budget.tool_calls, 0)

    def test_disclosure_uses_existing_shared_deadline_and_call_allowance(self):
        from proofkey.budget import BudgetExceeded
        self.store.save_result(make_result())
        with self.assertRaises(BudgetExceeded):
            self.store.begin_disclosure_read(make_binding(), make_checkpoint().deadline)
        self.store.consume("C1", "tool_calls", 24, NOW)
        with self.assertRaises(BudgetExceeded):
            self.store.begin_disclosure_read(make_binding(), NOW)
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 24)
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 0.0)

    def test_abrupt_kill_at_real_committed_boundaries(self):
        self.store.close()
        for stage, want_state, want_external, want_verification in (
            ("prepare", "prepared", False, False), ("mark", "dispatching", False, False),
            ("external", "dispatching", True, False), ("preverify", "dispatching", True, False),
            ("postverify", "verified", True, True)):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as folder:
                process = subprocess.Popen([sys.executable, str(Path(__file__).with_name("crash_worker.py")), folder, stage],
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                ready = process.stdout.readline().strip()
                self.assertEqual(ready, "BOUNDARY " + stage)
                process.send_signal(signal.SIGKILL)
                out, err = process.communicate(timeout=10)
                self.assertEqual(process.returncode, -signal.SIGKILL, (out, err))
                recovered = CaseStore(Path(folder) / "journal.sqlite")
                try:
                    record = recovered.intents("C1")[0]
                    self.assertEqual(record.state, want_state)
                    self.assertEqual(record.verification is not None, want_verification)
                    self.assertEqual(recovered.checkpoint("C1").budget.tool_calls, 0 if stage == "prepare" else 1)
                    self.assertEqual(recovered.checkpoint("C1").budget.active_seconds, 0.0 if stage == "prepare" else 10.0)
                    external = sqlite3.connect(Path(folder) / "external.sqlite")
                    count = external.execute("SELECT COUNT(*) FROM writes").fetchone()[0]
                    external.close()
                    self.assertEqual(count, int(want_external))
                finally:
                    recovered.close()
