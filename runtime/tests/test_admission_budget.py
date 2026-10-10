"""Untrusted admission selectors cannot reset or poison authoritative history."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from proofkey.budget import BudgetExceeded
from proofkey.contracts import BudgetLedger
from proofkey.journal import CaseStore, JournalFailure
from support import NOW, DEADLINE, CommitFault, make_auth, make_binding, make_checkpoint, make_intent, make_request


class AdmissionBudgetTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "journal.sqlite"
        self.store = CaseStore(self.path)
        self.addCleanup(lambda: self.store.close())

    def start(self, attempt="attempt-1", request=None, auth=None, now=NOW, deadline=DEADLINE):
        return self.store.start_admission(attempt, auth or make_auth(), request or make_request(), now, deadline)

    def assert_no_authoritative_history(self):
        self.assertIsNone(self.store.find_request("C1", "REQ1", "v1", "v1", make_binding().fingerprint))
        db = sqlite3.connect(self.path)
        try:
            for table in ("cases", "requests", "original_requests", "results", "intents"):
                self.assertEqual(db.execute("SELECT COUNT(*) FROM " + table).fetchone()[0], 0, table)
        finally:
            db.close()

    def test_unverified_and_denied_reads_create_only_untrusted_accounting(self):
        attempt = self.start()
        lease = self.store.begin_admission_read(attempt.attempt_id, NOW)
        self.assertEqual(lease.claimed_case_id, "C1")
        self.assertEqual(lease.reserved_seconds, 10.0)
        self.assertEqual(self.store.admission_account("C1").tool_calls, 1)
        self.assertEqual(self.store.admission_account("C1").active_seconds, 10.0)
        self.assert_no_authoritative_history()
        self.store.close()
        self.store = CaseStore(self.path)
        self.assertEqual(self.store.admission_entry(lease.entry_id).state, "active")
        self.assert_no_authoritative_history()

    def test_new_request_proof_and_attempt_id_share_claimed_case_caps(self):
        for index in range(24):
            attempt = self.start("attempt-" + str(index), request=make_request(request_id="REQ" + str(index)),
                auth=make_auth(proof_reference="different-proof-" + str(index)))
            lease = self.store.begin_admission_read(attempt.attempt_id, NOW)
            self.store.finish_admission_read(lease.entry_id, 0.0)
        newer = self.start("new-id", request=make_request(request_id="REQ-new", request_revision="v2"),
            auth=make_auth(caller_id="different-caller", proof_reference="new-proof"))
        with self.assertRaises(BudgetExceeded):
            self.store.begin_admission_read(newer.attempt_id, NOW)
        self.assertEqual(self.store.admission_account("C1").tool_calls, 24)
        self.assertEqual(self.store.admission_account("C1").active_seconds, 0.0)
        self.assert_no_authoritative_history()

    def test_identical_business_dedup_and_changed_lineage_conflict(self):
        first = self.start()
        lease = self.store.begin_admission_read(first.attempt_id, NOW)
        replay = self.start("other-host-attempt-id")
        self.assertEqual(replay.attempt_id, first.attempt_id)
        for changed in (make_request(narrative="new transport words"), make_request(evidence_ids=["new-input"]),
                        make_request(arguments={"slot": "other"})):
            with self.assertRaises(JournalFailure):
                self.start("attempt-1", request=changed)
        with self.assertRaises(JournalFailure):
            self.start("another-id", request=make_request(narrative="changed lineage"))
        self.assertEqual(self.store.admission_account("C1").tool_calls, 1)
        self.assertEqual(self.store.admission_entry(lease.entry_id).state, "active")

    def test_new_attempt_cannot_extend_unbound_absolute_deadline(self):
        self.start(deadline=NOW + timedelta(seconds=1))
        with self.assertRaises(BudgetExceeded):
            self.start("later", request=make_request(request_id="REQ2"), auth=make_auth(proof_reference="new"),
                now=NOW + timedelta(seconds=2), deadline=DEADLINE)
        self.assert_no_authoritative_history()

    def test_known_completion_settles_once_before_transfer(self):
        self.start()
        lease = self.store.begin_admission_read("attempt-1", NOW)
        self.store.finish_admission_read(lease.entry_id, 1.25)
        self.assertEqual(self.store.admission_account("C1").active_seconds, 1.25)
        self.store.close()
        self.store = CaseStore(self.path)
        with self.assertRaises(JournalFailure):
            self.store.finish_admission_read(lease.entry_id, 0.0)
        for elapsed in (-1.0, True, float("nan"), float("inf"), "1"):
            with self.assertRaises(JournalFailure):
                self.store.finish_admission_read(lease.entry_id, elapsed)
        self.assertEqual(self.store.admission_account("C1").active_seconds, 1.25)

    def test_first_authentic_admission_imports_all_account_debts_once(self):
        self.start()
        first = self.store.begin_admission_read("attempt-1", NOW)
        second_attempt = self.start("attempt-2", request=make_request(request_id="REQ2"),
            auth=make_auth(proof_reference="other-proof"))
        second = self.store.begin_admission_read(second_attempt.attempt_id, NOW)
        self.store.admit_from_attempt("attempt-1", make_binding(), make_request(), make_checkpoint())
        checkpoint = self.store.checkpoint("C1")
        self.assertEqual(checkpoint.budget.tool_calls, 2)
        self.assertEqual(checkpoint.budget.active_seconds, 20.0)
        self.assertEqual(self.store.original_request("C1", "G1"), make_request())
        self.assertEqual(self.store.admission_attempt("attempt-1").state, "transferred")
        with self.assertRaises(JournalFailure):
            self.store.admit_from_attempt("attempt-1", make_binding(), make_request(), make_checkpoint())
        for lease in (first, second):
            with self.assertRaises(JournalFailure):
                self.store.finish_admission_read(lease.entry_id, 0.0)
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 20.0)

    def test_direct_host_admit_imports_all_debt_once_across_reopen(self):
        self.start()
        lease = self.store.begin_admission_read("attempt-1", NOW)
        self.store.admit(make_binding(), make_request(), make_checkpoint())
        self.store.close()
        self.store = CaseStore(self.path)
        current = self.store.checkpoint("C1")
        self.store.admit(make_binding(), make_request(), current)
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 1)
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 10.0)
        with self.assertRaises(JournalFailure):
            self.store.finish_admission_read(lease.entry_id, 0.0)

    def test_manual_history_cannot_bypass_pending_admission_debt(self):
        self.start()
        self.store.begin_admission_read("attempt-1", NOW)
        self.store.bind(make_binding())
        self.store.save_request(make_binding(), make_request())
        self.store.save_checkpoint(make_checkpoint())
        intent = make_intent()
        self.store.prepare(intent)
        for enter in (lambda: self.store.begin_read("C1", NOW),
                      lambda: self.store.begin_dispatch(intent, NOW)):
            with self.assertRaises(JournalFailure):
                enter()
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 0)
        self.store.admit(make_binding(), make_request(), make_checkpoint())
        self.store.begin_read("C1", NOW)
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 2)

    def test_case_and_admission_overrun_fence_each_others_old_settlements(self):
        self.store.admit(make_binding(), make_request(), make_checkpoint())
        self.start()
        core = self.store.begin_read("C1", NOW)
        bootstrap = self.store.begin_admission_read("attempt-1", NOW)
        with self.assertRaises(BudgetExceeded):
            self.store.finish_admission_read(bootstrap.entry_id, 11.0)
        with self.assertRaises(BudgetExceeded):
            self.store.finish_entry(core.entry_id, 0.0)
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 120.0)
        self.store.close()
        other_path = Path(self.folder.name) / "other.sqlite"
        self.store = CaseStore(other_path)
        self.store.admit(make_binding(), make_request(), make_checkpoint())
        self.start()
        core = self.store.begin_read("C1", NOW)
        bootstrap = self.store.begin_admission_read("attempt-1", NOW)
        with self.assertRaises(BudgetExceeded):
            self.store.finish_entry(core.entry_id, 11.0)
        with self.assertRaises(BudgetExceeded):
            self.store.finish_admission_read(bootstrap.entry_id, 0.0)
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 120.0)

    def test_corrupted_unbound_record_fails_closed_on_get_and_reopen(self):
        self.start()
        db = sqlite3.connect(self.path)
        db.execute("UPDATE admission_accounts SET account_json=json_set(account_json,'$.tool_calls',0.0)")
        db.commit()
        db.close()
        with self.assertRaises(JournalFailure):
            self.store.admission_account("C1")
        self.store.close()
        with self.assertRaises(JournalFailure):
            CaseStore(self.path)

    def test_changed_valid_proof_digest_cannot_rebind_stored_dedup_identity(self):
        self.start()
        db = sqlite3.connect(self.path)
        db.execute("UPDATE admission_attempts SET attempt_json=json_set(attempt_json,'$.proof_digest',?)", ("0" * 64,))
        db.commit()
        db.close()
        with self.assertRaises(JournalFailure):
            self.store.admission_attempt("attempt-1")
        with self.assertRaises(JournalFailure):
            self.store.begin_admission_read("attempt-1", NOW)
        self.assertEqual(self.store.admission_account("C1").tool_calls, 0)
        self.store.close()
        with self.assertRaises(JournalFailure):
            CaseStore(self.path)

    def test_bootstrap_slice_clamps_both_original_and_current_deadlines(self):
        self.start(deadline=NOW + timedelta(seconds=2))
        lease = self.store.begin_admission_read("attempt-1", NOW)
        self.assertEqual(lease.reserved_seconds, 2.0)
        self.assertEqual(lease.deadline, NOW + timedelta(seconds=2))
        self.store.admit(make_binding(), make_request(), make_checkpoint())
        self.assertEqual(self.store.checkpoint("C1").budget.deadline, lease.deadline)
        with self.assertRaises(BudgetExceeded):
            self.store.begin_read("C1", lease.deadline)

    def test_raw_proof_is_not_persisted_as_authentication_material(self):
        secret = "raw-proof-private-test-only"
        self.start(auth=make_auth(proof_reference=secret))
        for table, column in (("admission_accounts", "account_json"),
                              ("admission_attempts", "attempt_json"),
                              ("admission_audit", "event_json")):
            rows = self.store._db.execute("SELECT " + column + " FROM " + table).fetchall()
            self.assertNotIn(secret, " ".join(row[0] for row in rows))

    def test_lineage_mismatch_or_insufficient_import_rolls_back_authentic_history(self):
        self.start()
        lease = self.store.begin_admission_read("attempt-1", NOW)
        with self.assertRaises(JournalFailure):
            self.store.admit_from_attempt("attempt-1", make_binding(), make_request(narrative="substituted"), make_checkpoint())
        self.assert_no_authoritative_history()
        self.store.finish_admission_read(lease.entry_id, 0.0)
        lease = self.store.begin_admission_read("attempt-1", NOW)
        self.store.finish_admission_read(lease.entry_id, 0.0)
        tight = make_checkpoint(budget=BudgetLedger(case_id="C1", deadline=DEADLINE, max_tool_calls=1))
        with self.assertRaises(BudgetExceeded):
            self.store.admit_from_attempt("attempt-1", make_binding(), make_request(), tight)
        self.assert_no_authoritative_history()
        self.assertEqual(self.store.admission_account("C1").tool_calls, 2)
        self.assertEqual(self.store.admission_attempt("attempt-1").state, "unbound")

    def test_existing_case_read_and_new_generation_keep_shared_debts_and_stop(self):
        self.store.admit(make_binding(), make_request(), make_checkpoint(phase="stopped", next_gate="saved_result"))
        self.store.set_stop("C1", "G1")
        self.store.consume("C1", "tool_calls", 2, NOW)
        self.store.consume("C1", "active_seconds", 3.0, NOW)
        request = make_request(request_revision="v2")
        attempt = self.start(request=request)
        lease = self.store.begin_admission_read(attempt.attempt_id, NOW)
        before = self.store.checkpoint("C1")
        self.assertEqual(before.binding.generation, "G1")
        self.assertTrue(before.stop.requested)
        self.assertEqual(before.phase, "stopped")
        self.assertEqual(before.next_gate, "saved_result")
        self.assertEqual(before.budget.tool_calls, 3)
        self.assertEqual(before.budget.active_seconds, 13.0)
        self.assertEqual(self.store.original_request("C1", "G1"), make_request())
        self.assertIsNone(self.store.find_request("C1", "REQ1", "v2", "v1", make_binding().fingerprint))
        self.store.finish_admission_read(lease.entry_id, 1.0)
        newer = make_binding(request=request, generation="G2", supersedes_generation="G1")
        self.store.admit_from_attempt(attempt.attempt_id, newer, request, make_checkpoint(binding=newer))
        after = self.store.checkpoint("C1")
        self.assertEqual(after.binding, newer)
        self.assertTrue(after.stop.requested)
        self.assertEqual(after.budget.tool_calls, 3)
        self.assertEqual(after.budget.active_seconds, 4.0)

    def test_existing_case_and_unbound_exhaustion_have_identical_generic_error(self):
        self.store.admit(make_binding(), make_request(), make_checkpoint())
        self.store.consume("C1", "tool_calls", 24, NOW)
        self.start()
        with self.assertRaises(BudgetExceeded) as existing:
            self.store.begin_admission_read("attempt-1", NOW)
        unbound_request = make_request(case_id="unbound")
        attempt = self.start("unbound-attempt", request=unbound_request)
        for _ in range(12):
            self.store.begin_admission_read(attempt.attempt_id, NOW)
        with self.assertRaises(BudgetExceeded) as unbound:
            self.store.begin_admission_read(attempt.attempt_id, NOW)
        self.assertEqual(str(existing.exception), str(unbound.exception))

    def test_last_correlation_allowance_is_atomic_across_connections(self):
        attempt = self.start()
        for _ in range(23):
            lease = self.store.begin_admission_read(attempt.attempt_id, NOW)
            self.store.finish_admission_read(lease.entry_id, 0.0)
        def compete(_):
            store = CaseStore(self.path)
            try:
                store.begin_admission_read(attempt.attempt_id, NOW)
                return "reserved"
            except BudgetExceeded:
                return "denied"
            finally:
                store.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(compete, range(2)))
        self.assertEqual(sorted(outcomes), ["denied", "reserved"])
        self.assertEqual(self.store.admission_account("C1").tool_calls, 24)

    def test_commit_fault_preserves_debt_and_blocks_uncommitted_entry_or_import(self):
        self.start()
        self.store.close()
        fault = CommitFault()
        self.store = CaseStore(self.path, before_commit=fault)
        fault.arm()
        with self.assertRaises(JournalFailure):
            self.store.begin_admission_read("attempt-1", NOW)
        self.assertEqual(self.store.admission_account("C1").tool_calls, 0)
        self.store.begin_admission_read("attempt-1", NOW)
        fault.arm()
        with self.assertRaises(JournalFailure):
            self.store.admit_from_attempt("attempt-1", make_binding(), make_request(), make_checkpoint())
        self.assert_no_authoritative_history()
        self.assertEqual(self.store.admission_account("C1").tool_calls, 1)

    def test_sigkill_before_identity_verification_retains_unbound_debt_only(self):
        with tempfile.TemporaryDirectory() as folder:
            child = subprocess.Popen([sys.executable, str(Path(__file__).with_name("crash_worker.py")), folder, "admission"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            entry_id = child.stdout.readline().strip().removeprefix("ENTRY ")
            self.assertEqual(child.stdout.readline().strip(), "BOUNDARY admission")
            child.send_signal(signal.SIGKILL)
            out, err = child.communicate(timeout=10)
            self.assertEqual(child.returncode, -signal.SIGKILL, (out, err))
            store = CaseStore(Path(folder) / "journal.sqlite")
            try:
                self.assertEqual(store.admission_entry(entry_id).state, "active")
                self.assertEqual(store.admission_account("C1").tool_calls, 1)
                self.assertEqual(store.admission_account("C1").active_seconds, 10.0)
                self.assertIsNone(store.find_request("C1", "REQ1", "v1", "v1", make_binding().fingerprint))
            finally:
                store.close()

    def test_admission_overrun_cannot_reopen_account_capacity(self):
        self.start()
        first = self.store.begin_admission_read("attempt-1", NOW)
        second = self.store.begin_admission_read("attempt-1", NOW)
        with self.assertRaises(BudgetExceeded):
            self.store.finish_admission_read(second.entry_id, 11.0)
        with self.assertRaises(BudgetExceeded):
            self.store.finish_admission_read(first.entry_id, 0.0)
        self.assertEqual(self.store.admission_account("C1").active_seconds, 120.0)
        with self.assertRaises(BudgetExceeded):
            self.store.begin_admission_read("attempt-1", NOW)
