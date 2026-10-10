"""Host-only source attachment CAS; storage typing is not source custody."""
from datetime import timedelta
from pathlib import Path
import tempfile
import threading
import unittest

from proofkey.contracts import AuthorityObservation, ReadTarget, ScopedReply
from proofkey.journal import CaseStore, JournalFailure
from support import NOW, CommitFault, make_binding, make_checkpoint, make_request
from test_wait_storage import make_record


class WaitReplyAttachmentTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "attachment.sqlite"
        self.fault = CommitFault()
        self.store = CaseStore(self.path, before_commit=self.fault)
        self.addCleanup(lambda: self.store.close())
        self.store.admit(make_binding(), make_request(), make_checkpoint(phase="completeness",
            next_gate="send_clarification", ownership_state="accepted",
            ownership_state_revision="owner-1", ownership_epoch=2))
        self.record = make_record(self.store.checkpoint("C1"))
        self.store.create_wait_atomic(self.record, NOW)
        self.store.save_checkpoint(self.store.checkpoint("C1").model_copy(update={
            "phase": self.record.wait_phase, "next_gate": self.record.accept_edge.operation,
            "question_id": "Q1", "awaited_fields": self.record.wait.awaited_fields}))
        # Real unresolved physical read reservation must not be refunded by local attachment.
        self.lease = self.store.begin_control_read(make_binding(), ReadTarget(
            kind="authority_facts", authority="ownership", facts=["epoch"]), "reply", NOW)
        current = self.store.checkpoint("C1")
        self.reply = ScopedReply(question_id="Q1", binding=current.binding, actor_id="U1",
            proof_reference="untrusted", request_revision="v1", consent_revision="v1",
            owner_state_revision="owner-1", fields={"case.missing_facts": "untrusted"},
            received_at=NOW + timedelta(seconds=1), simulated=True)
        self.consumed = self.store.consume_wait_reply_atomic("Q1", current, self.reply,
            current.model_copy(update={"phase": "completeness", "next_gate": "authenticate"}),
            NOW + timedelta(seconds=2))
        self.answered = self.store.load_wait_record("Q1")
        self.source = AuthorityObservation(authority="case", fact="completeness", object_id="O1",
            value={"source": "missing"}, revision="v1", observed_at=NOW, evidence_ref="fixture-source")

    def test_exact_consumed_attachment_changes_only_detached_sources_and_reopens(self):
        payload = [self.source]
        attached = self.store.attach_wait_reply_sources_atomic("Q1", self.consumed, payload)
        self.assertEqual(attached.model_copy(update={"observations": []}), self.consumed)
        self.assertEqual(attached.observations[0].value, {"source": "missing"})
        payload.clear()
        self.assertIsNot(attached.observations[0], self.source)
        with self.assertRaises(TypeError):
            self.source.value["source"] = "caller-mutated-after-write"
        self.assertEqual(attached.observations[0].value, {"source": "missing"})
        self.assertEqual(self.store.load_wait_record("Q1"), self.answered)
        self.assertEqual((attached.budget.tool_calls, attached.budget.active_seconds,
            attached.budget.clarifications), (1, 10.0, 1))
        self.assertEqual(self.store.entry(self.lease.entry_id).state, "active")
        self.store.close()
        self.store = CaseStore(self.path)
        self.assertEqual(self.store.checkpoint("C1"), attached)
        self.assertEqual(self.store.load_wait_record("Q1"), self.answered)
        with self.assertRaises(JournalFailure):
            self.store.attach_wait_reply_sources_atomic("Q1", self.consumed, (self.source,))
        with self.assertRaises(JournalFailure):
            self.store.consume_wait_reply_atomic("Q1", attached, self.reply, self.consumed,
                NOW + timedelta(seconds=3))

    def test_invalid_observation_payload_never_changes_answer_or_checkpoint(self):
        for label, observations in (
            ("untyped", [self.source.model_dump()]),
            ("foreign", [self.source.model_copy(update={"object_id": "other"})]),
            ("duplicate", [self.source, self.source]),
            ("missing-evidence", [AuthorityObservation.model_construct(**{
                **self.source.model_dump(), "evidence_ref": ""})]),
            ("naive-time", [AuthorityObservation.model_construct(**{
                **self.source.model_dump(), "observed_at": NOW.replace(tzinfo=None)})]),
            ("oversized", [self.source.model_copy(update={"fact": "f" + str(i)}) for i in range(65)]),
            ("generator", iter([self.source]))):
            with self.subTest(label=label), self.assertRaises(JournalFailure):
                self.store.attach_wait_reply_sources_atomic("Q1", self.consumed, observations)
            self.assertEqual(self.store.checkpoint("C1"), self.consumed)
            self.assertEqual(self.store.load_wait_record("Q1"), self.answered)

    def test_changed_actual_control_or_budget_denies_without_merging(self):
        newer = self.consumed.model_copy(update={"next_gate": "read_communication"})
        self.store.save_checkpoint(newer)
        with self.assertRaises(JournalFailure):
            self.store.attach_wait_reply_sources_atomic("Q1", self.consumed, [self.source])
        # Even a caller supplying the actual changed token cannot replace the
        # immutable answered-successor hash with a newly reconstructed control.
        with self.assertRaises(JournalFailure):
            self.store.attach_wait_reply_sources_atomic("Q1", newer, [self.source])
        self.assertEqual(self.store.checkpoint("C1"), newer)
        self.store.save_checkpoint(self.consumed)
        self.store.begin_control_read(make_binding(), ReadTarget(
            kind="authority_facts", authority="ownership", facts=["epoch"]), "reply", NOW)
        charged = self.store.checkpoint("C1")
        with self.assertRaises(JournalFailure):
            self.store.attach_wait_reply_sources_atomic("Q1", self.consumed, [self.source])
        self.assertEqual(self.store.checkpoint("C1"), charged)
        self.assertEqual(self.store.load_wait_record("Q1"), self.answered)

    def test_foreign_untyped_or_sourced_expected_token_is_rejected(self):
        for expected in (self.consumed.model_dump(),
            self.consumed.model_copy(update={"binding": make_binding(generation="other")}),
            self.consumed.model_copy(update={"observations": [self.source]})):
            with self.subTest(expected=type(expected).__name__), self.assertRaises(JournalFailure):
                self.store.attach_wait_reply_sources_atomic("Q1", expected, [self.source])
            self.assertEqual(self.store.checkpoint("C1"), self.consumed)
        with self.assertRaises(JournalFailure):
            self.store.attach_wait_reply_sources_atomic("foreign", self.consumed, [self.source])

    def test_commit_failure_keeps_consumed_receipt_and_full_reserved_debt(self):
        self.fault.arm()
        with self.assertRaises(JournalFailure):
            self.store.attach_wait_reply_sources_atomic("Q1", self.consumed, [self.source])
        self.assertEqual(self.store.checkpoint("C1"), self.consumed)
        self.assertEqual(self.store.load_wait_record("Q1"), self.answered)
        self.store.close()
        self.store = CaseStore(self.path)
        self.assertEqual(self.store.checkpoint("C1"), self.consumed)
        self.assertEqual(self.store.entry(self.lease.entry_id).state, "active")

    def test_current_generation_stop_rejects_even_original_consumed_hash(self):
        stopped = self.store.stop_waits_atomic(self.consumed.binding, self.consumed)
        with self.assertRaises(JournalFailure):
            self.store.attach_wait_reply_sources_atomic("Q1", self.consumed, (self.source,))
        self.assertEqual(self.store.checkpoint("C1"), stopped)
        self.assertEqual(self.store.load_wait_record("Q1"), self.answered)

    def test_attachment_requires_its_store_creator_thread_before_write(self):
        errors = []
        def attach():
            try:
                self.store.attach_wait_reply_sources_atomic("Q1", self.consumed, [self.source])
            except Exception as error:
                errors.append(error)
        worker = threading.Thread(target=attach)
        worker.start()
        worker.join(5)
        self.assertFalse(worker.is_alive())
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], JournalFailure)
        self.assertEqual(self.store.checkpoint("C1"), self.consumed)
        self.assertEqual(self.store.load_wait_record("Q1"), self.answered)
