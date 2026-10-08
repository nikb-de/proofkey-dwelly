from datetime import timedelta
from pathlib import Path
import tempfile
import unittest

from proofkey.budget import BudgetExceeded, tool_timeout
from proofkey.contracts import BudgetLedger
from proofkey.journal import CaseStore, JournalFailure
from support import NOW, make_binding, make_checkpoint, make_intent, make_request


class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "journal.sqlite"
        self.store = CaseStore(self.path)
        self.addCleanup(lambda: self.store.close())
        self.store.bind(make_binding())
        self.store.save_request(make_binding(), make_request())
        self.store.save_checkpoint(make_checkpoint())

    def test_shared_calls_include_failed_and_read_attempts(self):
        for _ in range(24):
            self.store.consume("C1", "tool_calls", 1, NOW)
        with self.assertRaises(BudgetExceeded):
            self.store.consume("C1", "tool_calls", 1, NOW)
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 24)

    def test_planner_clarification_and_active_caps(self):
        for kind, amount in (("planner_calls", 4), ("clarifications", 2), ("active_seconds", 120.0)):
            self.store.consume("C1", kind, amount, NOW)
            with self.assertRaises(BudgetExceeded):
                self.store.consume("C1", kind, 1, NOW)

    def test_per_intent_read_and_retry_caps_are_shared(self):
        self.store.prepare(make_intent())
        action = make_intent().action_id
        self.store.consume("C1", "reconciliation_reads:" + action, 3, NOW)
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 3)
        with self.assertRaises(BudgetExceeded):
            self.store.consume("C1", "reconciliation_reads:" + action, 1, NOW)
        self.store.consume("C1", "retries:" + action, 1, NOW)
        with self.assertRaises(BudgetExceeded):
            self.store.consume("C1", "retries:" + action, 1, NOW)

    def test_sixth_effect_is_reserved_for_handoff(self):
        for stage in range(5):
            intent = make_intent(stage=str(stage))
            self.store.prepare(intent)
            self.store.begin_dispatch(intent, NOW)
        sixth = make_intent(stage="sixth")
        self.store.prepare(sixth)
        with self.assertRaises(BudgetExceeded):
            self.store.begin_dispatch(sixth, NOW)
        handoff = make_intent(operation="enqueue_handoff", stage="handoff")
        self.store.prepare(handoff)
        self.store.begin_dispatch(handoff, NOW)
        self.assertEqual(self.store.checkpoint("C1").budget.effects, 6)

    def test_generation_cannot_reset_counters_or_extend_deadline(self):
        self.store.consume("C1", "tool_calls", 7, NOW)
        self.store.consume("C1", "active_seconds", 33.0, NOW)
        newer = make_binding(generation="G2", request_revision="v2", supersedes_generation="G1")
        self.store.bind(newer)
        self.store.save_checkpoint(make_checkpoint(binding=newer))
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 7)
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 33.0)
        later = make_checkpoint(binding=newer, deadline=NOW + timedelta(days=1),
            budget=BudgetLedger(case_id="C1", deadline=NOW + timedelta(days=1)))
        with self.assertRaises(JournalFailure):
            self.store.save_checkpoint(later)

    def test_untrusted_counter_or_cap_rewrite_denied(self):
        self.store.consume("C1", "tool_calls", 3, NOW)
        raised = BudgetLedger(case_id="C1", deadline=make_checkpoint().deadline, max_tool_calls=99)
        with self.assertRaises(JournalFailure):
            self.store.save_checkpoint(make_checkpoint(budget=raised))
        self.store.save_checkpoint(make_checkpoint())
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 3)

    def test_structured_case_configured_zero_planners(self):
        folder = Path(self.folder.name) / "structured.sqlite"
        store = CaseStore(folder)
        try:
            store.bind(make_binding())
            store.save_checkpoint(make_checkpoint(budget=BudgetLedger(case_id="C1", deadline=make_checkpoint().deadline, max_planner_calls=0)))
            with self.assertRaises(BudgetExceeded):
                store.consume("C1", "planner_calls", 1, NOW)
        finally:
            store.close()

    def test_timeout_is_ten_or_remaining_active_or_deadline(self):
        ledger = BudgetLedger(case_id="C1", deadline=NOW + timedelta(seconds=7), active_seconds=117.0)
        self.assertEqual(tool_timeout(ledger, NOW), 3.0)
        with self.assertRaises(BudgetExceeded):
            tool_timeout(ledger, NOW + timedelta(seconds=8))

    def test_invalid_debits_and_expired_deadline_fail_before_update(self):
        for kind, amount in (("tool_calls", True), ("tool_calls", 0), ("tool_calls", 1.5), ("active_seconds", float("nan")), ("other", 1)):
            with self.assertRaises((JournalFailure, BudgetExceeded, ValueError)):
                self.store.consume("C1", kind, amount, NOW)
        with self.assertRaises(BudgetExceeded):
            self.store.consume("C1", "tool_calls", 1, make_checkpoint().deadline)
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 0)

    def test_stored_over_ceiling_budget_fails_closed(self):
        import json
        import sqlite3
        raw = make_checkpoint().model_dump(mode="json")
        raw["budget"]["max_tool_calls"] = 99
        db = sqlite3.connect(self.path)
        db.execute("UPDATE cases SET checkpoint_json=?", (json.dumps(raw),))
        db.commit()
        db.close()
        with self.assertRaises(JournalFailure):
            self.store.checkpoint("C1")

    def test_clarification_dispatch_debits_two_request_limit_atomically(self):
        for stage in ("one", "two"):
            intent = make_intent(operation="send_clarification", stage=stage)
            self.store.prepare(intent)
            self.store.begin_dispatch(intent, NOW)
        third = make_intent(operation="send_clarification", stage="three")
        self.store.prepare(third)
        with self.assertRaises(BudgetExceeded):
            self.store.begin_dispatch(third, NOW)
        self.assertEqual(self.store.checkpoint("C1").budget.clarifications, 2)
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 2)

    def test_one_rejected_original_resend_no_distinct_effect_reset(self):
        from proofkey.contracts import VerificationResult
        intent = make_intent()
        self.store.prepare(intent)
        self.store.begin_dispatch(intent, NOW)
        with self.assertRaises(JournalFailure):
            self.store.begin_dispatch(intent, NOW, is_resend=True)
        self.store.record_verification(intent.action_id, VerificationResult(status="rejected"))
        self.store.begin_dispatch(intent, NOW, is_resend=True)
        self.store.record_verification(intent.action_id, VerificationResult(status="rejected"))
        with self.assertRaises(BudgetExceeded):
            self.store.begin_dispatch(intent, NOW, is_resend=True)
        self.assertEqual(self.store.checkpoint("C1").budget.effects, 1)
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 2)

    def test_shorter_checkpoint_deadline_bounds_all_reads(self):
        deadline = NOW + timedelta(seconds=4)
        self.store.save_checkpoint(make_checkpoint(deadline=deadline))
        with self.assertRaises(BudgetExceeded):
            self.store.consume("C1", "tool_calls", 1, deadline)
        self.assertEqual(tool_timeout(self.store.checkpoint("C1").budget, NOW), 4.0)

    def test_entry_reserves_active_time_and_one_use_settlement(self):
        intent = make_intent()
        self.store.prepare(intent)
        lease = self.store.begin_dispatch(intent, NOW)
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 10.0)
        self.store.finish_entry(lease.entry_id, 2.5)
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 2.5)
        self.store.close()
        self.store = CaseStore(self.path)
        with self.assertRaises(JournalFailure):
            self.store.finish_entry(lease.entry_id, 0.0)
        self.store.save_checkpoint(make_checkpoint())
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 2.5)

    def test_interrupted_reads_cannot_exceed_persisted_active_limit(self):
        leases = [self.store.begin_read("C1", NOW) for _ in range(12)]
        self.store.close()
        self.store = CaseStore(self.path)
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 120.0)
        self.assertEqual(self.store.entry(leases[-1].entry_id).state, "active")
        with self.assertRaises(BudgetExceeded):
            self.store.begin_read("C1", NOW)
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 12)

    def test_read_entry_reserves_remaining_deadline_and_scoped_cap(self):
        intent = make_intent()
        self.store.prepare(intent)
        self.store.consume("C1", "active_seconds", 118.0, NOW)
        self.store.save_checkpoint(make_checkpoint(deadline=NOW + timedelta(seconds=1)))
        lease = self.store.begin_read("C1", NOW, action_id=intent.action_id)
        self.assertEqual(lease.reserved_seconds, 1.0)
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 1)
        self.assertEqual(self.store.checkpoint("C1").budget.reconciliation_reads[intent.action_id], 1)
        self.store.finish_entry(lease.entry_id, 0.25)
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 118.25)
        with self.assertRaises(BudgetExceeded):
            self.store.begin_read("C1", NOW + timedelta(seconds=1), action_id=intent.action_id)

    def test_settlement_fault_rolls_back_counter_and_lease(self):
        from support import CommitFault
        self.store.close()
        fault = CommitFault()
        self.store = CaseStore(self.path, before_commit=fault)
        lease = self.store.begin_read("C1", NOW)
        fault.arm()
        with self.assertRaises(JournalFailure):
            self.store.finish_entry(lease.entry_id, 1.0)
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 10.0)
        self.assertEqual(self.store.entry(lease.entry_id).state, "active")

    def test_overrun_exhausts_budget_durably_instead_of_refunding(self):
        older = self.store.begin_read("C1", NOW)
        lease = self.store.begin_read("C1", NOW)
        with self.assertRaises(BudgetExceeded):
            self.store.finish_entry(lease.entry_id, 11.0)
        self.store.close()
        self.store = CaseStore(self.path)
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 120.0)
        self.assertEqual(self.store.entry(lease.entry_id).state, "overrun")
        self.assertEqual(self.store.entry(lease.entry_id).elapsed_seconds, 11.0)
        with self.assertRaises(BudgetExceeded):
            self.store.begin_read("C1", NOW)
        with self.assertRaises(BudgetExceeded):
            self.store.finish_entry(older.entry_id, 0.0)
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 120.0)

    def test_sigkill_after_scoped_read_lease_keeps_full_active_debit(self):
        import signal
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as folder:
            child = subprocess.Popen([sys.executable, str(Path(__file__).with_name("crash_worker.py")), folder, "read"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            entry_id = child.stdout.readline().strip().removeprefix("ENTRY ")
            self.assertEqual(child.stdout.readline().strip(), "BOUNDARY read")
            child.send_signal(signal.SIGKILL)
            out, err = child.communicate(timeout=10)
            self.assertEqual(child.returncode, -signal.SIGKILL, (out, err))
            store = CaseStore(Path(folder) / "journal.sqlite")
            try:
                self.assertEqual(store.entry(entry_id).state, "active")
                self.assertEqual(store.checkpoint("C1").budget.active_seconds, 10.0)
                self.assertEqual(store.checkpoint("C1").budget.tool_calls, 1)
                self.assertEqual(store.checkpoint("C1").budget.reconciliation_reads[make_intent().action_id], 1)
            finally:
                store.close()

    def test_invalid_settlement_cannot_refund_capacity(self):
        lease = self.store.begin_read("C1", NOW)
        for elapsed in (-1.0, float("nan"), float("inf"), True, "1"):
            with self.assertRaises(JournalFailure):
                self.store.finish_entry(lease.entry_id, elapsed)
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 10.0)
