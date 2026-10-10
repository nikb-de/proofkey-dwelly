"""Read-only processing inventory over actual synthetic durable reservations."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json
import sqlite3
import tempfile
import unittest

from proofkey.contracts import BudgetLedger, ProcessingReceipt, RequestBinding, RoleAllowance
from proofkey.journal import CaseStore, JournalFailure
from support import NOW, DEADLINE, make_binding, make_checkpoint, make_request
from test_provider_invocation_recovery import invocation, permit


class ProcessingAttemptsTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "journal.sqlite"
        self.store = CaseStore(self.path)
        self.addCleanup(lambda: self.store.close())
        self.binding = make_binding()
        budget = BudgetLedger(case_id="C1", deadline=DEADLINE, role_allowances={"extraction": RoleAllowance(
            max_invocations=3, max_cost=6.0, usage_allowances={"tokens": 60.0})})
        self.store.admit(self.binding, make_request(), make_checkpoint(budget=budget))
        self.grant = permit()
        self.store.register_campaign(self.grant)

    def test_insertion_order_and_interrupted_originals_survive_reopen_without_new_debt(self):
        first = self.store.reserve_invocation(invocation(self.grant, invocation_id="z-first"), NOW)
        second = self.store.reserve_invocation(invocation(self.grant, invocation_id="a-second"), NOW)
        before = self.store.checkpoint("C1")
        debt = self.store.campaign_usage(self.grant.permit_hash)
        self.store.close()
        self.store = CaseStore(self.path)
        values = self.store.processing_attempts(self.binding)
        self.assertIsInstance(values, tuple)
        self.assertEqual(values, ((first, None), (second, None)))
        self.assertEqual([item[0].invocation_id for item in values], ["z-first", "a-second"])
        self.assertIsNot(values[0][0], first)
        with self.assertRaises((TypeError, ValueError)):
            values[0][0].identity.input_hashes.append("3" * 64)
        self.assertEqual(self.store.checkpoint("C1"), before)
        self.assertEqual(self.store.campaign_usage(self.grant.permit_hash), debt)

    def durable_bytes(self):
        return {suffix: Path(str(self.path) + suffix).read_bytes()
                for suffix in ("", "-wal") if Path(str(self.path) + suffix).exists()}

    def receipt(self, identifier, status):
        return ProcessingReceipt(invocation_id=identifier, role="extraction", provider=self.grant.provider,
            requested_model=self.grant.model, prompt_hash="2" * 64, version="v1", input_hashes=["1" * 64],
            mode="synthetic", status=status, latency_seconds=0.0, usage={"tokens": 1.0}, processed_at=NOW)

    def test_complete_failed_and_consumed_history_never_refunds_or_writes(self):
        for identifier in ("z-complete", "m-failed", "a-interrupted"):
            self.store.reserve_invocation(invocation(self.grant, invocation_id=identifier), NOW)
        complete = self.receipt("z-complete", "completed")
        failed = self.receipt("m-failed", "failed")
        self.store.record_processing("z-complete", complete)
        self.store.record_processing("m-failed", failed)
        self.store.set_stop("C1", "G1")
        before = self.store.checkpoint("C1")
        debt = self.store.campaign_usage(self.grant.permit_hash)
        durable = self.durable_bytes()
        values = self.store.processing_attempts(self.binding)
        self.assertEqual([item[0].status for item in values], ["completed", "failed", "consumed"])
        self.assertEqual([item[1] for item in values], [complete, failed, None])
        self.assertIsNot(values[0][1], complete)
        self.assertEqual(self.store.checkpoint("C1"), before)
        self.assertEqual(self.store.campaign_usage(self.grant.permit_hash), debt)
        self.assertEqual(self.durable_bytes(), durable)
        self.store.close()
        self.store = CaseStore(self.path)
        self.assertEqual(self.store.processing_attempts(self.binding), values)

    def test_empty_is_explicit_and_never_authorizes_provider(self):
        before = self.store.checkpoint("C1")
        durable = self.durable_bytes()
        self.assertEqual(self.store.processing_attempts(self.binding), ())
        self.assertEqual(self.store.checkpoint("C1"), before)
        self.assertEqual(self.durable_bytes(), durable)

    def test_exact_generation_and_case_separation_preserve_shared_debt(self):
        first = self.store.reserve_invocation(invocation(self.grant, invocation_id="z-G1"), NOW)
        newer_request = make_request(request_revision="v2")
        newer = make_binding(newer_request, generation="G2", supersedes_generation="G1")
        budget = BudgetLedger(case_id="C1", deadline=DEADLINE, role_allowances={"extraction": RoleAllowance(
            max_invocations=3, max_cost=6.0, usage_allowances={"tokens": 60.0})})
        self.store.admit(newer, newer_request, make_checkpoint(binding=newer, budget=budget))
        second = self.store.reserve_invocation(invocation(self.grant, invocation_id="a-G2", generation="G2"), NOW)
        foreign_request = make_request(case_id="C2")
        foreign = make_binding(foreign_request)
        foreign_budget = BudgetLedger(case_id="C2", deadline=DEADLINE, role_allowances={"extraction": RoleAllowance(
            max_invocations=1, max_cost=2.0, usage_allowances={"tokens": 20.0})})
        self.store.admit(foreign, foreign_request, make_checkpoint(binding=foreign, budget=foreign_budget))
        third = self.store.reserve_invocation(invocation(self.grant, case="C2", invocation_id="m-C2"), NOW)
        before = self.store.checkpoint("C1")
        debt = self.store.campaign_usage(self.grant.permit_hash)
        self.assertEqual(self.store.processing_attempts(self.binding), ((first, None),))
        self.assertEqual(self.store.processing_attempts(newer), ((second, None),))
        self.assertEqual(self.store.processing_attempts(foreign), ((third, None),))
        self.assertEqual(self.store.checkpoint("C1"), before)
        self.assertEqual(self.store.campaign_usage(self.grant.permit_hash), debt)

    def test_strict_complete_binding_and_creator_thread_fail_without_mutation(self):
        durable = self.durable_bytes()
        for binding in (None, self.binding.model_dump(), RequestBinding.model_construct(case_id="C1"),
                        make_binding(object_id="foreign"), make_binding(request_id="foreign"),
                        make_binding(generation="unknown"), make_binding(fingerprint="0" * 64)):
            with self.subTest(binding=binding), self.assertRaises(JournalFailure):
                self.store.processing_attempts(binding)
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self.store.processing_attempts, self.binding)
            with self.assertRaises(JournalFailure):
                future.result()
        self.assertEqual(self.durable_bytes(), durable)

    def test_selected_index_state_and_reservation_corruption_deny_not_partial(self):
        self.store.reserve_invocation(invocation(self.grant, invocation_id="first"), NOW)
        self.store.reserve_invocation(invocation(self.grant, invocation_id="second"), NOW)
        # Deliberate temporary durable-row corruption, never ordinary input.
        with sqlite3.connect(self.path) as db:
            original = db.execute("SELECT reservation_json FROM invocations WHERE invocation_id='second'").fetchone()[0]
        for patch in ({"case_debit": 0}, {"status": "failed"}, {"identity": {
                **json.loads(original)["identity"], "process_version": "foreign"}}, {"invocation_id": "first"}):
            raw = {**json.loads(original), **patch}
            with sqlite3.connect(self.path) as db:
                db.execute("UPDATE invocations SET reservation_json=? WHERE invocation_id='second'", (json.dumps(raw),))
            with self.assertRaises(JournalFailure):
                self.store.processing_attempts(self.binding)
            with sqlite3.connect(self.path) as db:
                db.execute("UPDATE invocations SET reservation_json=? WHERE invocation_id='second'", (original,))
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE invocations SET role='planning' WHERE invocation_id='second'")
        with self.assertRaises(JournalFailure):
            self.store.processing_attempts(self.binding)

    def test_selected_receipt_and_permit_corruption_fail_closed(self):
        self.store.reserve_invocation(invocation(self.grant), NOW)
        receipt = self.receipt("invoke-1", "completed")
        self.store.record_processing("invoke-1", receipt)
        # Labeled task-temp SQL fault injection; public producers stay strict.
        for patch in ({"invocation_id": "foreign"}, {"requested_model": "foreign"}, {"status": "running"}):
            raw = {**receipt.model_dump(mode="json"), **patch}
            with sqlite3.connect(self.path) as db:
                db.execute("UPDATE invocations SET receipt_json=?", (json.dumps(raw),))
            with self.assertRaises(JournalFailure):
                self.store.processing_attempts(self.binding)
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE invocations SET receipt_json=?", (receipt.model_dump_json(),))
            db.execute("UPDATE campaigns SET permit_json=?", (self.grant.model_dump_json().replace("model-1", "foreign"),))
        with self.assertRaises(JournalFailure):
            self.store.processing_attempts(self.binding)

    def test_missing_original_request_denies_even_empty_inventory(self):
        binding = make_binding(case_id="no-original")
        self.store.bind(binding)
        with self.assertRaises(JournalFailure):
            self.store.processing_attempts(binding)

    def test_invocation_ids_remain_global_immutable_originals_not_scope_aliases(self):
        first = self.store.reserve_invocation(invocation(self.grant), NOW)
        request = make_request(case_id="C2")
        binding = make_binding(request)
        budget = BudgetLedger(case_id="C2", deadline=DEADLINE, role_allowances={"extraction": RoleAllowance(
            max_invocations=1, max_cost=2.0, usage_allowances={"tokens": 20.0})})
        self.store.admit(binding, request, make_checkpoint(binding=binding, budget=budget))
        before = self.store.checkpoint("C2")
        with self.assertRaises(JournalFailure):
            self.store.reserve_invocation(invocation(self.grant, case="C2"), NOW)
        self.assertEqual(self.store.processing_attempts(binding), ())
        self.assertEqual(self.store.processing_attempts(self.binding), ((first, None),))
        self.assertEqual(self.store.checkpoint("C2"), before)
