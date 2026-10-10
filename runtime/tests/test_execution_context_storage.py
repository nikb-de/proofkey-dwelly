"""Trusted host timing and creator-thread storage; no source/permission grant."""
from datetime import timedelta
from contextlib import closing
import importlib
import math
from pathlib import Path
import sqlite3
import tempfile
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import time
import unittest

from proofkey.budget import BudgetExceeded
from proofkey.contracts import BudgetLedger, ReadTarget, RoleAllowance, VerificationResult
from proofkey.journal import CaseStore, JournalFailure
from support import NOW, DEADLINE, make_auth, make_binding, make_checkpoint, make_intent, make_request, make_result


class DeterministicClock:
    def __init__(self):
        self.utc = NOW
        self.elapsed = 100.0

    def now(self):
        return self.utc

    def monotonic(self):
        return self.elapsed

    def advance(self, seconds, *, utc_seconds=None):
        self.elapsed += seconds
        self.utc += timedelta(seconds=seconds if utc_seconds is None else utc_seconds)


class ExecutionContextTests(unittest.TestCase):
    def context_type(self):
        try:
            return importlib.import_module("proofkey.execution").ExecutionContext
        except (ImportError, AttributeError) as error:
            self.fail("Trusted execution window unavailable: " + type(error).__name__)

    def test_capture_once_never_restarts_monotonic_window_after_wall_clock_reversal(self):
        clock = DeterministicClock()
        execution = self.context_type().capture(NOW + timedelta(seconds=2), clock)
        clock.advance(1, utc_seconds=-10)
        self.assertEqual(execution.remaining_seconds(clock), 1.0)
        self.assertEqual(execution.effective_deadline(clock), clock.now() + timedelta(seconds=1))
        clock.advance(1, utc_seconds=0)
        self.assertEqual(execution.remaining_seconds(clock), 0.0)
        with self.assertRaises((AttributeError, TypeError)):
            execution.deadline = NOW + timedelta(seconds=100)

    def test_expired_capture_is_data_but_invalid_clock_or_deadline_rejects(self):
        cls = self.context_type()
        clock = DeterministicClock()
        self.assertEqual(cls.capture(NOW, clock).remaining_seconds(clock), 0.0)
        with self.assertRaises(ValueError):
            cls.capture(NOW.replace(tzinfo=None), clock)
        for value in (math.nan, math.inf):
            clock.elapsed = value
            with self.assertRaises(ValueError):
                cls.capture(NOW + timedelta(seconds=2), clock)

    def test_current_window_accounts_for_time_consumed_observing_utc(self):
        class DelayedUtcClock(DeterministicClock):
            delay = False
            def now(self):
                if self.delay:
                    self.advance(1, utc_seconds=0)
                return super().now()
        clock = DelayedUtcClock()
        execution = self.context_type().capture(NOW + timedelta(seconds=1), clock)
        clock.delay = True
        self.assertEqual(execution.remaining_seconds(clock), 0,
            "Current monotonic sample must follow the UTC observation before new entry")


class ExecutionStorageTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "journal.sqlite"
        self.store = CaseStore(self.path)
        self.addCleanup(self.store.close)
        self.store.admit(make_binding(), make_request(), make_checkpoint())
        self.clock = DeterministicClock()
        from proofkey.execution import ExecutionContext
        self.execution = ExecutionContext.capture(NOW + timedelta(seconds=1), self.clock)

    def scope(self):
        if not callable(getattr(self.store, "execution_scope", None)):
            self.fail("Creator-thread execution scope missing")
        return self.store.execution_scope(self.execution, self.clock)

    def test_read_scope_caps_committed_lease_and_reservation_then_restores(self):
        with self.scope():
            lease = self.store.begin_read("C1", NOW)
        self.assertEqual(lease.deadline, NOW + timedelta(seconds=1))
        self.assertEqual(lease.reserved_seconds, 1.0)
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 1.0)
        self.assertEqual(self.store.entry(lease.entry_id), lease)
        self.store.finish_entry(lease.entry_id, 0.0)
        ordinary = self.store.begin_read("C1", NOW)
        self.assertEqual(ordinary.reserved_seconds, 10.0)

    def test_expired_window_denies_physical_entries_without_any_new_debt(self):
        intent = make_intent()
        self.store.prepare(intent)
        before = self.store.checkpoint("C1")
        self.clock.advance(1)
        with self.scope():
            for entry in (lambda: self.store.begin_read("C1", NOW),
                          lambda: self.store.begin_dispatch(intent, NOW)):
                with self.assertRaises(BudgetExceeded):
                    entry()
        self.assertEqual(self.store.checkpoint("C1"), before)
        self.assertEqual(self.store.intent(intent.action_id).state, "prepared")

    def test_scope_reentrant_and_foreign_thread_fail_before_mutation(self):
        before = self.store.checkpoint("C1")
        with self.scope():
            with self.assertRaises(JournalFailure):
                with self.scope():
                    self.store.begin_read("C1", NOW)
        def foreign():
            with self.scope():
                self.store.begin_read("C1", NOW)
        with ThreadPoolExecutor(max_workers=1) as pool:
            with self.assertRaises(JournalFailure):
                pool.submit(foreign).result()
        self.assertEqual(self.store.checkpoint("C1"), before)

    def test_short_original_caps_dispatch_and_reconciliation_without_rewriting_identity(self):
        intent = make_intent(deadline=NOW + timedelta(seconds=.25))
        self.store.prepare(intent)
        with self.scope():
            lease = self.store.begin_dispatch(intent, NOW)
            read = self.store.begin_read("C1", NOW, intent.action_id)
        for entry in (lease, read):
            self.assertEqual(entry.deadline, intent.deadline)
            self.assertEqual(entry.reserved_seconds, .25)
        self.assertEqual(self.store.intent(intent.action_id).intent, intent)
        self.assertEqual(self.store.original_request("C1", "G1"), make_request())
        self.assertEqual(self.store.checkpoint("C1").deadline, DEADLINE)
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, .5)

    def test_control_and_historical_disclosure_share_host_cap_without_rewriting_result(self):
        result = make_result()
        self.store.save_result(result)
        self.store.set_stop("C1", "G1")
        with self.scope():
            control = self.store.begin_control_read(make_binding(),
                ReadTarget(kind="authority_facts", authority="case", facts=["binding"]), "stop", NOW)
            disclosure = self.store.begin_disclosure_read(make_binding(), NOW)
        for lease in (control, disclosure):
            self.assertEqual(lease.deadline, self.execution.deadline)
            self.assertEqual(lease.reserved_seconds, 1)
        self.assertEqual(self.store.saved_result("C1", "G1"), result)
        self.assertTrue(self.store.checkpoint("C1").stop.requested)

    def test_provider_reservation_and_permit_scope_keep_identity_and_debt(self):
        from test_provider_invocation_recovery import permit, invocation
        binding = make_binding(case_id="provider")
        budget = BudgetLedger(case_id="provider", deadline=DEADLINE,
            role_allowances={"extraction": RoleAllowance(
                max_invocations=2, max_cost=6, usage_allowances={"tokens": 60})})
        self.store.admit(binding, make_request(case_id="provider"), make_checkpoint(binding=binding, budget=budget))
        grant = permit(expires_at=NOW + timedelta(seconds=.5))
        self.store.register_campaign(grant)
        request = invocation(grant, case="provider", deadline=grant.expires_at)
        with self.scope():
            reserved = self.store.reserve_invocation(request, NOW)
        lease = self.store.entry("invocation:" + request.invocation_id)
        self.assertEqual(lease.deadline, grant.expires_at)
        self.assertEqual(lease.reserved_seconds, .5)
        self.assertEqual(reserved.identity, request.identity)
        self.assertEqual(self.store.campaign_usage(grant.permit_hash)["invocations"], 1)
        before = self.store.checkpoint("provider")
        self.clock.advance(1)
        with self.scope(), self.assertRaises(BudgetExceeded):
            self.store.reserve_invocation(invocation(grant, case="provider", invocation_id="invoke-2", deadline=grant.expires_at), NOW)
        self.assertEqual(self.store.checkpoint("provider"), before)
        self.assertEqual(self.store.campaign_usage(grant.permit_hash)["invocations"], 1)

    def test_admission_caps_saved_account_and_reused_attempt_cannot_extend(self):
        with self.scope():
            attempt = self.store.start_admission("a1", make_auth(), make_request(), NOW, DEADLINE)
            lease = self.store.begin_admission_read(attempt.attempt_id, NOW)
        self.assertEqual(lease.deadline, self.execution.deadline)
        self.assertEqual(lease.reserved_seconds, 1)
        self.assertEqual(self.store.admission_account("C1").active_seconds, 1)
        self.assertEqual(self.store.admission_account("C1").deadline, self.execution.deadline)
        from proofkey.execution import ExecutionContext
        longer = ExecutionContext.capture(DEADLINE, self.clock)
        self.clock.advance(1)
        before = self.store.admission_account("C1")
        with self.store.execution_scope(longer, self.clock), self.assertRaises(BudgetExceeded):
            self.store.start_admission("a2", make_auth(), make_request(request_id="REQ2"), NOW, DEADLINE)
        self.assertEqual(self.store.admission_account("C1"), before)
        with self.store.execution_scope(longer, self.clock), self.assertRaises(BudgetExceeded):
            self.store.begin_admission_read(attempt.attempt_id, NOW)
        self.assertEqual(self.store.admission_account("C1"), before)
        with self.scope():
            self.store.finish_admission_read(lease.entry_id, .5)
        self.assertEqual(self.store.admission_entry(lease.entry_id).state, "settled")
        self.assertEqual(self.store.admission_account("C1").active_seconds, .5)

    def test_repeated_scope_and_wall_clock_reversal_do_not_restart_remaining_slice(self):
        with self.scope():
            first = self.store.begin_read("C1", NOW)
        self.clock.advance(.75, utc_seconds=-10)
        with self.scope():
            second = self.store.begin_read("C1", NOW)
        self.assertEqual(first.reserved_seconds, 1)
        self.assertEqual(second.started_at, self.clock.now())
        self.assertEqual(second.reserved_seconds, .25)
        self.assertEqual(second.deadline, self.clock.now() + timedelta(seconds=.25))
        self.assertEqual(self.store.entry(first.entry_id), first)
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 1.25)

    def test_expired_scope_allows_local_unknown_settlement_and_result_recording(self):
        intent = make_intent()
        self.store.prepare(intent)
        with self.scope():
            lease = self.store.begin_dispatch(intent, NOW)
            self.clock.advance(1)
            self.store.record_verification(intent.action_id, VerificationResult(status="outcome_unknown"))
            self.store.finish_entry(lease.entry_id, .5)
            self.store.save_result(make_result())
            with self.assertRaises(BudgetExceeded):
                self.store.begin_read("C1", NOW, intent.action_id)
        self.assertEqual(self.store.intent(intent.action_id).state, "outcome_unknown")
        self.assertEqual(self.store.entry(lease.entry_id).state, "settled")
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, .5)
        self.assertEqual(self.store.saved_result("C1", "G1"), make_result())

    def test_scope_timeout_restores_on_exception_and_invalid_clock_mutates_nothing(self):
        prior = self.store._db.execute("PRAGMA busy_timeout").fetchone()[0]
        before = self.store.checkpoint("C1")
        with self.assertRaisesRegex(RuntimeError, "caller failure"):
            with self.scope():
                self.assertLessEqual(self.store._db.execute("PRAGMA busy_timeout").fetchone()[0], 1000)
                raise RuntimeError("caller failure")
        self.assertEqual(self.store._db.execute("PRAGMA busy_timeout").fetchone()[0], prior)
        self.clock.elapsed = math.nan
        with self.assertRaises(ValueError):
            with self.scope():
                self.store.begin_read("C1", NOW)
        self.assertEqual(self.store.checkpoint("C1"), before)
        self.assertEqual(self.store._db.execute("PRAGMA busy_timeout").fetchone()[0], prior)

    def hold_database_lock(self, acquired, release, advance=None):
        # The competing connection is created/used/closed on its own thread.
        with closing(sqlite3.connect(self.path, timeout=1)) as db:
            db.execute("BEGIN IMMEDIATE")
            acquired.set()
            if not release.wait(5):
                raise AssertionError("Test lock release not signaled")
            if advance:
                advance()
            db.commit()

    def test_real_lock_wait_is_bounded_and_failed_entry_preserves_durable_state(self):
        from proofkey.execution import ExecutionContext
        anchor = time.monotonic()
        class RealClock:
            def monotonic(self):
                return time.monotonic()
            def now(self):
                return NOW + timedelta(seconds=time.monotonic() - anchor)
        clock = RealClock()
        before = self.store.checkpoint("C1")
        acquired, release = Event(), Event()
        prior = self.store._db.execute("PRAGMA busy_timeout").fetchone()[0]
        with ThreadPoolExecutor(max_workers=1) as pool:
            holder = pool.submit(self.hold_database_lock, acquired, release)
            self.assertTrue(acquired.wait(2))
            execution = ExecutionContext.capture(clock.now() + timedelta(seconds=.12), clock)
            started = time.monotonic()
            try:
                with self.store.execution_scope(execution, clock), self.assertRaises(JournalFailure):
                    self.store.begin_read("C1", NOW)
            finally:
                release.set()
            holder.result(timeout=2)
        elapsed = time.monotonic() - started
        self.assertLess(elapsed, 1, "SQLite timeout is bounded with scheduler tolerance, not hard kill")
        self.assertGreater(elapsed, .04, "Real competing lock exercised SQLite waiting")
        self.assertEqual(self.store.checkpoint("C1"), before)
        self.assertEqual(self.store._db.execute("PRAGMA busy_timeout").fetchone()[0], prior)

    def test_successful_lock_acquisition_refreshes_host_time_before_debit(self):
        acquired, release = Event(), Event()
        before = self.store.checkpoint("C1")
        with ThreadPoolExecutor(max_workers=1) as pool:
            holder = pool.submit(self.hold_database_lock, acquired, release,
                lambda: self.clock.advance(.75))
            self.assertTrue(acquired.wait(2))
            # SQLite traces the real BEGIN, then the competing owner advances
            # trusted test time and commits. No sleep supplies race correctness.
            self.store._db.set_trace_callback(lambda sql: release.set() if sql == "BEGIN IMMEDIATE" else None)
            try:
                with self.scope():
                    lease = self.store.begin_read("C1", NOW)
            finally:
                release.set()
                self.store._db.set_trace_callback(None)
            holder.result(timeout=2)
        self.assertEqual(lease.started_at, NOW + timedelta(seconds=.75))
        self.assertEqual(lease.reserved_seconds, .25)
        self.assertEqual(lease.deadline, self.execution.deadline)
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, before.budget.tool_calls + 1)

    def registered_transfer(self):
        from test_ownership_storage import synthetic_registry, synthetic_source, synthetic_transfer
        self.store.close()
        self.path = Path(self.folder.name) / "ownership.sqlite"
        registry = synthetic_registry()
        self.store = CaseStore(self.path, ownership_processes=registry)
        spec = registry.processes[make_request().kind]
        self.store.admit(make_binding(), make_request(), make_checkpoint(profile_version="v1.4",
            process_version=spec.version, phase="wait_operator", next_gate="wait_operator",
            ownership_state="accepted", ownership_state_revision="owner-r1", ownership_epoch=1))
        source = synthetic_source(self.store)
        transfer, effect = synthetic_transfer(source)
        self.store.register_transfer_atomic(transfer, effect, source, NOW)
        return transfer, effect

    def test_registered_transfer_host_cap_preserves_registered_original_and_pending_fence(self):
        transfer, effect = self.registered_transfer()
        with self.scope():
            lease = self.store.begin_registered_transfer(transfer.transfer_id, self.store.checkpoint("C1"), NOW)
            self.clock.advance(1)
            self.store.mark_transfer_unknown_atomic(transfer.transfer_id, self.store.checkpoint("C1"))
        self.assertEqual(lease.reserved_seconds, 1)
        self.assertEqual(lease.deadline, self.execution.deadline)
        self.assertEqual(self.store.intent(effect.action_id).intent, effect)
        self.assertEqual(self.store.transfer_record(transfer.transfer_id).lifecycle, "outcome_unknown")
        before = self.store.checkpoint("C1")
        with self.scope(), self.assertRaises((BudgetExceeded, JournalFailure)):
            self.store.begin_registered_transfer(transfer.transfer_id, before, NOW)
        self.assertEqual(self.store.checkpoint("C1"), before)

    def test_expired_host_denies_prepared_registered_transfer_without_entry_debt(self):
        transfer, effect = self.registered_transfer()
        before = self.store.checkpoint("C1")
        self.clock.advance(1)
        with self.scope(), self.assertRaises(BudgetExceeded):
            self.store.begin_registered_transfer(transfer.transfer_id, before, NOW)
        self.assertEqual(self.store.checkpoint("C1"), before)
        self.assertEqual(self.store.intent(effect.action_id).state, "prepared")
        self.assertEqual(self.store.transfer_record(transfer.transfer_id).lifecycle, "prepared")

    def test_host_expiry_after_real_lock_acquisition_rolls_back_all_entry_debt(self):
        intent = make_intent()
        self.store.prepare(intent)
        before = self.store.checkpoint("C1")
        acquired, release = Event(), Event()
        with ThreadPoolExecutor(max_workers=1) as pool:
            holder = pool.submit(self.hold_database_lock, acquired, release, lambda: self.clock.advance(1))
            self.assertTrue(acquired.wait(2))
            self.store._db.set_trace_callback(lambda sql: release.set() if sql == "BEGIN IMMEDIATE" else None)
            try:
                with self.scope(), self.assertRaises(BudgetExceeded):
                    self.store.begin_dispatch(intent, NOW)
            finally:
                release.set()
                self.store._db.set_trace_callback(None)
            holder.result(timeout=2)
        self.assertEqual(self.store.checkpoint("C1"), before)
        self.assertEqual(self.store.intent(intent.action_id).state, "prepared")
        with self.assertRaises(JournalFailure):
            self.store.entry("effect:" + intent.action_id + ":1")

    def test_host_shorter_resend_and_sequential_longer_scope_retain_original_lease(self):
        intent = make_intent()
        self.store.prepare(intent)
        first = self.store.begin_dispatch(intent, NOW)
        self.store.record_verification(intent.action_id, VerificationResult(status="outcome_unknown"))
        with self.scope():
            resend = self.store.begin_dispatch(intent, NOW, is_resend=True)
        self.assertEqual(resend.deadline, self.execution.deadline)
        self.assertEqual(resend.reserved_seconds, 1)
        from proofkey.execution import ExecutionContext
        longer = ExecutionContext.capture(DEADLINE, self.clock)
        with self.store.execution_scope(longer, self.clock):
            read = self.store.begin_read("C1", NOW, intent.action_id)
        self.assertEqual(self.store.entry(resend.entry_id), resend)
        self.assertEqual(self.store.entry(first.entry_id), first)
        self.assertEqual(read.reserved_seconds, 10)
        self.assertEqual(self.store.intent(intent.action_id).intent, intent)
        self.assertEqual(self.store.checkpoint("C1").budget.retries[intent.action_id], 1)
        self.assertEqual(self.store.checkpoint("C1").budget.effects, 1)

    def test_invalid_context_and_regressing_monotonic_time_deny_before_debit(self):
        before = self.store.checkpoint("C1")
        with self.assertRaises(JournalFailure):
            with self.store.execution_scope({"deadline": DEADLINE}, self.clock):
                self.store.begin_read("C1", NOW)
        with self.scope():
            self.clock.elapsed -= 1
            with self.assertRaises(ValueError):
                self.store.begin_read("C1", NOW)
        self.assertEqual(self.store.checkpoint("C1"), before)

    def test_saved_case_budget_shorter_than_host_cannot_be_extended_by_later_context(self):
        from proofkey.execution import ExecutionContext
        binding = make_binding(case_id="short")
        deadline = NOW + timedelta(seconds=.2)
        budget = BudgetLedger(case_id="short", deadline=deadline)
        self.store.admit(binding, make_request(case_id="short"),
            make_checkpoint(binding=binding, budget=budget, deadline=deadline))
        with self.scope():
            lease = self.store.begin_read("short", NOW)
        self.assertEqual(lease.deadline, deadline)
        self.assertEqual(lease.reserved_seconds, .2)
        self.clock.advance(.2)
        longer = ExecutionContext.capture(DEADLINE, self.clock)
        before = self.store.checkpoint("short")
        with self.store.execution_scope(longer, self.clock), self.assertRaises(BudgetExceeded):
            self.store.begin_read("short", NOW)
        self.assertEqual(self.store.checkpoint("short"), before)
        self.assertEqual(self.store.entry(lease.entry_id), lease)

    def test_expired_local_finalization_lock_failure_retains_entered_unknown_debt(self):
        intent = make_intent()
        self.store.prepare(intent)
        with self.scope():
            lease = self.store.begin_dispatch(intent, NOW)
            self.store.record_verification(intent.action_id, VerificationResult(status="outcome_unknown"))
        self.clock.advance(1)
        before = self.store.checkpoint("C1")
        acquired, release = Event(), Event()
        with ThreadPoolExecutor(max_workers=1) as pool:
            holder = pool.submit(self.hold_database_lock, acquired, release)
            self.assertTrue(acquired.wait(2))
            started = time.monotonic()
            try:
                with self.scope(), self.assertRaises(JournalFailure):
                    self.store.finish_entry(lease.entry_id, .5)
            finally:
                release.set()
            holder.result(timeout=2)
        self.assertLess(time.monotonic() - started, 1)
        self.assertEqual(self.store.checkpoint("C1"), before)
        self.assertEqual(self.store.intent(intent.action_id).state, "outcome_unknown")
        self.assertEqual(self.store.entry(lease.entry_id).state, "active")


if __name__ == "__main__":
    unittest.main()
