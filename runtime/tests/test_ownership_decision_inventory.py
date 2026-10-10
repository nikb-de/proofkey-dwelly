"""Historical storage inspection with synthetic public producers, not grants."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json
import sqlite3
import tempfile
import unittest

from proofkey.contracts import RequestBinding
from proofkey.identity import stable_action_id
from proofkey.journal import CaseStore, JournalFailure
from proofkey.ownership_contracts import OperatorDecisionSubmissionV1, OwnershipSourceReadV1
from support import NOW, DEADLINE, make_binding, make_checkpoint, make_request
from test_ownership_storage import synthetic_decision, synthetic_registry, synthetic_source


class DecisionInventoryTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "journal.sqlite"
        self.store = CaseStore(self.path, ownership_processes=synthetic_registry())
        self.addCleanup(lambda: self.store.close())
        process = synthetic_registry().processes[make_request().kind]
        self.binding = make_binding()
        self.store.admit(self.binding, make_request(), make_checkpoint(profile_version="v1.4",
            process_version=process.version, phase="wait_operator", next_gate="wait_operator",
            ownership_state="accepted", ownership_state_revision="owner-r1", ownership_epoch=1))
        source = synthetic_source(self.store, purpose="decision")
        self.source = source
        self.submission, self.effect = synthetic_decision(source)
        self.store.record_decision_atomic(self.submission, source, NOW)

    def test_exact_original_is_detached_immutable_and_survives_reopen_without_debit(self):
        before = self.store.checkpoint("C1")
        value = self.store.decision_record(self.binding, "decision-1")
        self.assertEqual(value, self.submission)
        self.assertIsNot(value, self.submission)
        self.assertEqual(value.decision.owner, "OP1")
        self.assertEqual(value.effect_scope.operation, "reschedule")
        with self.assertRaises((TypeError, ValueError)):
            value.decision.scope.append("transfer_owner")
        self.assertEqual(self.store.checkpoint("C1"), before)
        self.assertEqual(self.store.intents("C1"), ())
        self.store.close()
        self.store = CaseStore(self.path)
        self.assertEqual(self.store.decision_record(self.binding, "decision-1"), self.submission)
        self.assertEqual(self.store.checkpoint("C1"), before)

    def durable_bytes(self):
        return {suffix: Path(str(self.path) + suffix).read_bytes()
                for suffix in ("", "-wal") if Path(str(self.path) + suffix).exists()}

    def test_consumed_stopped_expired_original_remains_read_only_and_cannot_reenter(self):
        self.store.prepare(self.effect)
        self.store.begin_dispatch(self.effect, NOW)
        self.store.set_stop("C1", "G1")
        before = self.store.checkpoint("C1")
        intents = self.store.intents("C1")
        durable = self.durable_bytes()
        self.assertEqual(self.store.decision_record(self.binding, "decision-1"), self.submission)
        self.assertEqual(self.store.checkpoint("C1"), before)
        self.assertEqual(self.store.intents("C1"), intents)
        self.assertEqual(self.durable_bytes(), durable)
        # Expiry is not consulted by historical lookup; physical entry still is.
        with self.assertRaises(JournalFailure):
            self.store.begin_dispatch(self.effect, DEADLINE)
        self.assertEqual(self.store.decision_record(self.binding, "decision-1"), self.submission)
        self.assertEqual(self.durable_bytes(), durable)

    def test_current_generation_does_not_select_historical_decision_by_id(self):
        request = make_request(request_revision="v2")
        newer = make_binding(request, generation="G2", supersedes_generation="G1")
        self.store.admit(newer, request, make_checkpoint(binding=newer, profile_version="v1.4",
            process_version=self.source.checkpoint.process_version))
        with self.assertRaises(JournalFailure):
            self.store.decision_record(newer, "decision-1")
        self.assertEqual(self.store.decision_record(self.binding, "decision-1"), self.submission)

    def test_same_decision_id_in_foreign_case_never_aliases(self):
        request = make_request(case_id="C2")
        binding = make_binding(request, generation="G2")
        cp = make_checkpoint(binding=binding, profile_version="v1.4", process_version=self.source.checkpoint.process_version,
            phase="wait_operator", next_gate="wait_operator", ownership_state="accepted",
            ownership_state_revision="owner-r1", ownership_epoch=1)
        self.store.admit(binding, request, cp)
        # This is another synthetic public producer, not a foreign storage write.
        data = self.source.model_dump(mode="json")
        data["binding"] = binding.model_dump(mode="json")
        data["packet"]["binding"] = data["binding"]
        data["grant"]["binding"] = data["binding"]
        ids = []
        for _ in self.source.read_entry_ids:
            lease = self.store.begin_read("C2", NOW)
            self.store.finish_entry(lease.entry_id, 0.0)
            ids.append(lease.entry_id)
        data["read_entry_ids"] = ids
        data["checkpoint"] = self.store.checkpoint("C2").model_dump(mode="json")
        for item in data["observations"]:
            field = item["authority"] + "." + item["fact"]
            if field == "case.binding":
                item["value"] = {key: getattr(binding, key) for key in ("case_id", "object_id", "principal_id", "request_id")}
            elif field == "case.generation":
                item["value"] = "G2"
            elif field == "operator.ownership_packet":
                item["value"] = data["packet"]
            elif field == "operator.ownership_grant":
                item["value"] = data["grant"]
        source = OwnershipSourceReadV1.model_validate(data)
        wire = self.submission.model_dump(mode="json")
        wire["decision"]["binding"] = binding.model_dump(mode="json")
        wire["effect_scope"]["action_id"] = stable_action_id(binding, "reschedule", "commit")
        other = OperatorDecisionSubmissionV1.model_validate(wire)
        self.store.record_decision_atomic(other, source, NOW)
        self.assertEqual(self.store.decision_record(binding, "decision-1"), other)
        self.assertEqual(self.store.decision_record(self.binding, "decision-1"), self.submission)
        self.assertNotEqual(other.effect_scope.action_id, self.submission.effect_scope.action_id)

    def test_missing_strict_and_complete_binding_and_identifier_deny_without_writes(self):
        durable = self.durable_bytes()
        for binding in (self.binding.model_dump(), None, RequestBinding.model_construct(case_id="C1"),
                        make_binding(object_id="foreign"), make_binding(generation="unknown"),
                        make_binding(consent_revision="foreign"), make_binding(fingerprint="0" * 64)):
            with self.subTest(binding=binding), self.assertRaises(JournalFailure):
                self.store.decision_record(binding, "decision-1")
        for identifier in ("missing", "", " ", 7, b"decision-1", None):
            with self.subTest(identifier=identifier), self.assertRaises(JournalFailure):
                self.store.decision_record(self.binding, identifier)
        self.assertEqual(self.durable_bytes(), durable)

    def test_creator_thread_guard_is_journal_failure_not_sqlite_cross_thread_error(self):
        before = self.store.checkpoint("C1")
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self.store.decision_record, self.binding, "decision-1")
            with self.assertRaises(JournalFailure):
                future.result()
        self.assertEqual(self.store.checkpoint("C1"), before)

    def test_duplicate_and_corrupt_selected_audit_fail_closed(self):
        # Deliberate corruption of a task-owned temporary database only.
        with sqlite3.connect(self.path) as db:
            sequence, original = db.execute("SELECT sequence,event_json FROM audit ORDER BY sequence DESC LIMIT 1").fetchone()
        patches = ({"payload_hash": "0" * 64}, {"recorded_at": DEADLINE.isoformat()},
                   {"source": {**json.loads(original)["ownership_event"]["source"], "read_entry_ids": []}})
        for patch in patches:
            raw = json.loads(original)
            raw["ownership_event"].update(patch)
            with sqlite3.connect(self.path) as db:
                db.execute("UPDATE audit SET event_json=? WHERE sequence=?", (json.dumps(raw), sequence))
            with self.assertRaises(JournalFailure):
                self.store.decision_record(self.binding, "decision-1")
            with sqlite3.connect(self.path) as db:
                db.execute("UPDATE audit SET event_json=? WHERE sequence=?", (original, sequence))
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO audit(case_id,event_json) VALUES('C1',?)", (original,))
        with self.assertRaises(JournalFailure):
            self.store.decision_record(self.binding, "decision-1")

    def test_selected_original_input_corruption_denies(self):
        # Labeled durable fault injection, not a public caller input exploit.
        raw = make_request().model_dump(mode="json")
        raw["arguments"]["inventory"] = {"foreign-item": 99}
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE original_requests SET request_json=? WHERE case_id='C1'", (json.dumps(raw),))
        with self.assertRaises(JournalFailure):
            self.store.decision_record(self.binding, "decision-1")
