"""Durable wait scope/accounting; fixtures are not source authorization evidence."""
from datetime import timedelta
from pathlib import Path
import json
import sqlite3
import threading
import tempfile
import unittest

from proofkey.contracts import AuthorityObservation, ReadTarget, ScopedReply, WaitState
from proofkey.identity import fingerprint, stable_action_id
from proofkey.journal import CaseStore, JournalFailure
from proofkey.wait_contracts import WaitRecordV1
from support import NOW, CommitFault, make_binding, make_checkpoint, make_request, make_intent, load_test_profile


def make_record(origin, operation="send_clarification", **overrides):
    profile = load_test_profile()
    process = profile.processes["reschedule_window"]
    edge = next(e for e in process.edges if e.origin == origin.phase and e.operation == operation)
    contract = next(w for w in process.waits if w.phase == edge.target)
    wait = WaitState(question_id="Q1", binding=origin.binding, origin=origin.phase,
        next_gate=contract.next_gate, recipient="U1", owner_state_revision=origin.ownership_state_revision,
        awaited_fields=contract.awaited_fields, expires_at=NOW + timedelta(seconds=60), budget=origin.budget)
    data = dict(wait=wait, origin_checkpoint=origin, origin_hash=fingerprint(origin.model_dump(mode="json")),
        process=process, profile_hash=profile.release_hash, policy_hash=profile.policy_hash, owner_id="agent",
        owner_state=origin.ownership_state, owner_revision=origin.ownership_state_revision, owner_epoch=origin.ownership_epoch,
        recipient_role=contract.recipient_role, wait_phase=edge.target, communication_edge=edge,
        communication_stage="send" if operation == "send_clarification" else "enqueue",
        communication_action_id=stable_action_id(origin.binding, operation, "send" if operation == "send_clarification" else "enqueue"),
        accept_edge=next(e for e in process.edges if e.origin == edge.target and e.target == contract.next_gate),
        expiry_edge=next(e for e in process.edges if e.origin == edge.target and e.operation == "expire_wait"), created_at=NOW)
    return WaitRecordV1.model_validate({**data, **overrides})


class WaitStorageTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "wait.sqlite"
        self.store = CaseStore(self.path)
        self.addCleanup(lambda: self.store.close())
        self.store.admit(make_binding(), make_request(), make_checkpoint(phase="completeness", next_gate="send_clarification",
            ownership_state="accepted", ownership_state_revision="owner-1", ownership_epoch=2))

    def activate(self):
        record = make_record(self.store.checkpoint("C1"))
        self.store.create_wait_atomic(record, NOW)
        self.store.save_checkpoint(self.store.checkpoint("C1").model_copy(update={"phase": record.wait_phase,
            "next_gate": record.accept_edge.operation, "question_id": "Q1", "awaited_fields": record.wait.awaited_fields}))
        return record, self.store.checkpoint("C1")

    def reply(self, **overrides):
        data = dict(question_id="Q1", binding=make_binding(), actor_id="U1",
            proof_reference="fixture-only", request_revision="v1", consent_revision="v1", owner_state_revision="owner-1",
            fields={"case.missing_facts": "untrusted fixture"}, received_at=NOW + timedelta(seconds=1), simulated=True)
        return ScopedReply.model_validate({**data, **overrides})

    def test_question_persistence_debits_clarification_once_before_send(self):
        # Plain immutable WaitState persistence loses the pre-send clarification debit.
        origin = self.store.checkpoint("C1")
        record = make_record(origin)
        self.store.create_wait_atomic(record, NOW)
        self.store.create_wait_atomic(record, NOW)
        self.store.close()
        self.store = CaseStore(self.path)
        self.assertEqual(self.store.checkpoint("C1").budget.clarifications, 1,
            "Scoped wait creation must durably charge the question before physical send")
        self.assertEqual(self.store.checkpoint("C1").phase, "completeness")

    def test_reply_is_one_use_and_preserves_current_charges(self):
        record, _ = self.activate()
        self.store.begin_control_read(make_binding(), ReadTarget(
            kind="authority_facts", authority="ownership", facts=["epoch"]), "reply", NOW)
        current = self.store.checkpoint("C1")
        successor = current.model_copy(update={"phase": "completeness", "next_gate": "authenticate",
            "observations": [AuthorityObservation(authority="customer", fact="consent", object_id="O1",
                value=True, revision="stale", observed_at=NOW, evidence_ref="fixture-stale")], "ownership_epoch": 999})
        result = self.store.consume_wait_reply_atomic("Q1", current, self.reply(), successor, NOW + timedelta(seconds=2))
        self.assertIsNotNone(result, "Pending question must atomically commit an answered successor")
        self.assertEqual((result.budget.tool_calls, result.budget.active_seconds, result.budget.clarifications), (1, 10.0, 1))
        self.assertEqual(result.phase, "completeness")
        self.assertIsNone(result.question_id)
        self.assertEqual(result.observations, [])
        self.assertEqual(result.ownership_epoch, 2)
        self.store.close()
        self.store = CaseStore(self.path)
        self.assertEqual(self.store.load_wait_record("Q1").lifecycle, "answered")
        with self.assertRaises(JournalFailure):
            self.store.consume_wait_reply_atomic("Q1", current, self.reply(), successor, NOW + timedelta(seconds=2))

    def test_stop_marks_pending_question_without_creating_consent(self):
        _, current = self.activate()
        stopped = self.store.stop_waits_atomic(make_binding(), current)
        self.assertTrue(stopped.stop.requested)
        self.assertEqual(self.store.load_wait_record("Q1").lifecycle, "stopped")
        self.assertIsNone(self.store.load_wait_record("Q1").accepted_reply_hash)
        with self.assertRaises(JournalFailure):
            self.store.consume_wait_reply_atomic("Q1", stopped, self.reply(),
                stopped.model_copy(update={"phase": "completeness", "next_gate": "authenticate"}), NOW + timedelta(seconds=2))

    def test_clarification_dispatch_does_not_charge_pre_send_scope_twice(self):
        record = make_record(self.store.checkpoint("C1"))
        self.store.create_wait_atomic(record, NOW)
        intent = make_intent(operation="send_clarification", stage="send",
            arguments={"recipient": "U1", "question_id": "Q1", "text": "Fixture question"},
            ownership_state_revision="owner-1", ownership_epoch=2)
        self.store.prepare(intent)
        self.store.begin_dispatch(intent, NOW)
        self.assertEqual(self.store.checkpoint("C1").budget.clarifications, 1)
        self.assertEqual(self.store.checkpoint("C1").budget.effects, 1)
        with self.assertRaises(JournalFailure):
            self.store.begin_dispatch(intent, NOW)

    def test_invalid_reply_leaves_question_pending_and_charges_reads(self):
        self.activate()
        for changed in ({"actor_id": "other"}, {"question_id": "other"}, {"request_revision": "v2"},
                        {"consent_revision": "v2"}, {"owner_state_revision": "owner-2"},
                        {"fields": {"customer.consent": True}}, {"binding": make_binding(generation="other")}):
            self.store.begin_control_read(make_binding(), ReadTarget(kind="authority_facts", authority="case", facts=["binding"]), "reply", NOW)
            current = self.store.checkpoint("C1")
            with self.assertRaises(JournalFailure):
                self.store.consume_wait_reply_atomic("Q1", current, self.reply(**changed),
                    current.model_copy(update={"phase": "completeness", "next_gate": "authenticate"}), NOW + timedelta(seconds=2))
            self.assertEqual(self.store.load_wait_record("Q1").lifecycle, "pending")
        self.assertEqual((self.store.checkpoint("C1").budget.tool_calls, self.store.checkpoint("C1").budget.active_seconds), (7, 70.0))

    def test_legacy_wait_projects_but_cannot_resume(self):
        record = make_record(self.store.checkpoint("C1"))
        self.store.save_wait(record.wait)
        self.assertEqual(self.store.wait("Q1"), record.wait)
        with self.assertRaises(JournalFailure):
            self.store.load_wait_record("Q1")
        self.assertEqual(self.store.checkpoint("C1").budget.clarifications, 0)

    def test_changed_scope_fails_on_reopen(self):
        record, _ = self.activate()
        baseline = record.model_dump(mode="json")
        for mutation in ("epoch", "version", "origin", "case", "format", "process"):
            with self.subTest(mutation=mutation):
                raw = json.loads(json.dumps(baseline))
                if mutation == "epoch":
                    raw["owner_epoch"] = 99
                elif mutation == "version":
                    raw["origin_checkpoint"]["profile_version"] = "other"
                    raw["origin_hash"] = fingerprint(raw["origin_checkpoint"])
                elif mutation == "origin":
                    raw["origin_checkpoint"]["next_gate"] = "unexpected"
                    raw["origin_hash"] = fingerprint(raw["origin_checkpoint"])
                elif mutation == "case":
                    raw["wait"]["binding"]["case_id"] = "other"
                elif mutation == "format":
                    raw["kind"] = "wait_record_v2"
                else:
                    raw["process"]["release_hash"] = "0" * 64
                db = sqlite3.connect(self.path)
                db.execute("UPDATE waits SET wait_json=? WHERE question_id='Q1'", (json.dumps(raw),))
                db.commit()
                db.close()
                with self.assertRaises(JournalFailure):
                    CaseStore(self.path)
                db = sqlite3.connect(self.path)
                db.execute("UPDATE waits SET wait_json=? WHERE question_id='Q1'", (record.model_dump_json(),))
                db.commit()
                db.close()

    def test_expiry_is_one_use_and_does_not_dispatch(self):
        record, current = self.activate()
        successor = current.model_copy(update={"phase": "expired", "next_gate": "enqueue_handoff"})
        with self.assertRaises(JournalFailure):
            self.store.expire_wait_atomic("Q1", current, successor, NOW)
        expired = self.store.expire_wait_atomic("Q1", current, successor, record.wait.expires_at)
        self.assertEqual(expired.phase, "expired")
        self.assertEqual(expired.budget.clarifications, 1)
        self.assertEqual(self.store.load_wait_record("Q1").lifecycle, "expired")
        self.assertEqual(self.store.intents("C1"), ())
        with self.assertRaises(JournalFailure):
            self.store.consume_wait_reply_atomic("Q1", expired, self.reply(),
                expired.model_copy(update={"phase": "completeness", "next_gate": "authenticate"}), record.wait.expires_at)

    def test_changed_current_checkpoint_or_wrong_continuation_denies_reply(self):
        _, stale = self.activate()
        self.store.consume("C1", "tool_calls", 1, NOW)
        current = self.store.checkpoint("C1")
        for expected, successor in ((stale, current.model_copy(update={"phase": "completeness", "next_gate": "authenticate"})),
                                    (current, current.model_copy(update={"phase": "exact_gate", "next_gate": "reschedule"}))):
            with self.assertRaises(JournalFailure):
                self.store.consume_wait_reply_atomic("Q1", expected, self.reply(), successor, NOW + timedelta(seconds=2))
        self.assertEqual(self.store.load_wait_record("Q1").lifecycle, "pending")

    def test_creation_and_reply_commit_failures_roll_back_atomically(self):
        fault = CommitFault()
        self.store.close()
        self.store = CaseStore(self.path, before_commit=fault)
        record = make_record(self.store.checkpoint("C1"))
        fault.arm()
        with self.assertRaises(JournalFailure):
            self.store.create_wait_atomic(record, NOW)
        self.assertIsNone(self.store.wait("Q1"))
        self.assertEqual(self.store.checkpoint("C1").budget.clarifications, 0)
        _, current = self.activate()
        fault.arm()
        with self.assertRaises(JournalFailure):
            self.store.consume_wait_reply_atomic("Q1", current, self.reply(),
                current.model_copy(update={"phase": "completeness", "next_gate": "authenticate"}), NOW + timedelta(seconds=2))
        self.assertEqual(self.store.load_wait_record("Q1").lifecycle, "pending")
        self.assertEqual(self.store.checkpoint("C1"), current)

    def test_accept_expiry_and_stop_race_permits_one_transition(self):
        record, current = self.activate()
        barrier = threading.Barrier(3)
        results = []
        def transition(kind):
            store = CaseStore(self.path)
            try:
                barrier.wait()
                if kind == "reply":
                    store.consume_wait_reply_atomic("Q1", current, self.reply(),
                        current.model_copy(update={"phase": "completeness", "next_gate": "authenticate"}), NOW + timedelta(seconds=2))
                elif kind == "expiry":
                    store.expire_wait_atomic("Q1", current,
                        current.model_copy(update={"phase": "expired", "next_gate": "enqueue_handoff"}), record.wait.expires_at)
                else:
                    store.stop_waits_atomic(make_binding(), current)
                results.append("committed")
            except JournalFailure:
                results.append("denied")
            finally:
                store.close()
        threads = [threading.Thread(target=transition, args=(kind,)) for kind in ("reply", "expiry", "stop")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(10)
            self.assertFalse(thread.is_alive())
        self.assertEqual(results.count("committed"), 1)
        self.assertEqual(results.count("denied"), 2)
        self.assertIn(self.store.load_wait_record("Q1").lifecycle, {"answered", "expired", "stopped"})

    def test_entered_effect_wait_returns_to_original_verification(self):
        intent = make_intent()
        self.store.prepare(intent)
        self.store.begin_dispatch(intent, NOW)
        self.store.save_checkpoint(self.store.checkpoint("C1").model_copy(update={"phase": "verification", "next_gate": "enqueue_handoff"}))
        record = make_record(self.store.checkpoint("C1"), operation="enqueue_handoff")
        self.store.create_wait_atomic(record, NOW)
        self.store.save_checkpoint(self.store.checkpoint("C1").model_copy(update={"phase": record.wait_phase,
            "next_gate": record.accept_edge.operation, "question_id": "Q1", "awaited_fields": record.wait.awaited_fields}))
        current = self.store.checkpoint("C1")
        reply = self.reply(fields={"journal.original_effect": "original only", "case.reconciliation_facts": "untrusted"})
        restored = self.store.consume_wait_reply_atomic("Q1", current, reply,
            current.model_copy(update={"phase": "verification", "next_gate": "read_effect"}), NOW + timedelta(seconds=2))
        self.assertEqual((restored.phase, restored.next_gate), ("verification", "read_effect"))
        self.assertEqual(self.store.intents("C1")[0].intent, intent)
        self.assertEqual(self.store.intents("C1")[0].state, "dispatching")
        self.assertEqual(restored.budget.clarifications, 0)

    def test_legacy_question_never_suppresses_send_debit(self):
        record = make_record(self.store.checkpoint("C1"))
        self.store.save_wait(record.wait)
        intent = make_intent(operation="send_clarification", stage="send",
            arguments={"recipient": "U1", "question_id": "Q1", "text": "Legacy fixture"})
        self.store.prepare(intent)
        self.store.begin_dispatch(intent, NOW)
        self.assertEqual(self.store.checkpoint("C1").budget.clarifications, 1)

    def test_clarification_duplicate_new_question_id_cannot_rotate_action_identity(self):
        record = make_record(self.store.checkpoint("C1"))
        self.store.create_wait_atomic(record, NOW)
        changed_wait = record.wait.model_copy(update={"question_id": "Q2"})
        changed = record.model_copy(update={"wait": changed_wait})
        with self.assertRaises(JournalFailure):
            self.store.create_wait_atomic(changed, NOW)
        self.assertEqual(self.store.checkpoint("C1").budget.clarifications, 1)

    def test_expired_reply_stale_owner_epoch_and_future_time_leave_pending(self):
        record, current = self.activate()
        successor = current.model_copy(update={"phase": "completeness", "next_gate": "authenticate"})
        with self.assertRaises(JournalFailure):
            self.store.consume_wait_reply_atomic("Q1", current, self.reply(), successor, record.wait.expires_at)
        self.store.save_checkpoint(current.model_copy(update={"ownership_epoch": 3}))
        stale_owner = self.store.checkpoint("C1")
        with self.assertRaises(JournalFailure):
            self.store.consume_wait_reply_atomic("Q1", stale_owner, self.reply(), successor, NOW + timedelta(seconds=2))
        self.assertEqual(self.store.load_wait_record("Q1").lifecycle, "pending")

    def test_pending_wait_creation_after_entered_communication_is_denied(self):
        intent = make_intent(operation="send_clarification", stage="send",
            arguments={"recipient": "U1", "question_id": "Q1", "text": "already sent fixture"})
        self.store.prepare(intent)
        self.store.begin_dispatch(intent, NOW)
        record = make_record(self.store.checkpoint("C1"))
        with self.assertRaises(JournalFailure):
            self.store.create_wait_atomic(record, NOW)
        self.assertEqual(self.store.checkpoint("C1").budget.clarifications, 1)

    def test_answered_reply_facts_survive_reopen_as_untrusted_private_payload(self):
        _, current = self.activate()
        reply = self.reply(fields={"case.missing_facts": {"customer_words": "fixture facts", "authority": False}})
        self.store.consume_wait_reply_atomic("Q1", current, reply,
            current.model_copy(update={"phase": "completeness", "next_gate": "authenticate"}), NOW + timedelta(seconds=2))
        self.store.close()
        self.store = CaseStore(self.path)
        stored = self.store.load_wait_record("Q1")
        self.assertEqual(getattr(stored, "accepted_reply", None), reply,
            "Answered wait must retain exact untrusted reply facts/provenance across crash/reopen")
        self.assertTrue(stored.accepted_reply.simulated)
        self.assertEqual(self.store.checkpoint("C1").observations, [])
        self.assertNotIn("proof_reference", self.store.wait("Q1").model_dump())

    def test_answered_reply_payload_hash_and_actor_tampering_fail_reopen(self):
        _, current = self.activate()
        reply = self.reply()
        self.store.consume_wait_reply_atomic("Q1", current, reply,
            current.model_copy(update={"phase": "completeness", "next_gate": "authenticate"}), NOW + timedelta(seconds=2))
        original = self.store.load_wait_record("Q1")
        self.assertIsNotNone(getattr(original, "accepted_reply", None), "Answered reply body must be durable")
        for mutation in ("fields", "proof", "hash", "actor", "missing", "simulated"):
            with self.subTest(mutation=mutation):
                raw = original.model_dump(mode="json")
                if mutation == "fields":
                    raw["accepted_reply"]["fields"]["case.missing_facts"] = "changed facts"
                elif mutation == "proof":
                    raw["accepted_reply"]["proof_reference"] = "changed locator"
                elif mutation == "hash":
                    raw["accepted_reply_hash"] = "0" * 64
                elif mutation == "actor":
                    raw["accepted_actor"] = "other"
                elif mutation == "missing":
                    raw["accepted_reply"] = None
                else:
                    raw["accepted_reply"]["simulated"] = False
                db = sqlite3.connect(self.path)
                db.execute("UPDATE waits SET wait_json=? WHERE question_id='Q1'", (json.dumps(raw),))
                db.commit()
                db.close()
                with self.assertRaises(JournalFailure):
                    CaseStore(self.path)
                db = sqlite3.connect(self.path)
                db.execute("UPDATE waits SET wait_json=? WHERE question_id='Q1'", (original.model_dump_json(),))
                db.commit()
                db.close()

    def test_reply_commit_fault_retains_pending_without_partial_private_payload(self):
        fault = CommitFault()
        _, current = self.activate()
        self.store.close()
        self.store = CaseStore(self.path, before_commit=fault)
        fault.arm()
        with self.assertRaises(JournalFailure):
            self.store.consume_wait_reply_atomic("Q1", current, self.reply(),
                current.model_copy(update={"phase": "completeness", "next_gate": "authenticate"}), NOW + timedelta(seconds=2))
        self.store.close()
        self.store = CaseStore(self.path)
        record = self.store.load_wait_record("Q1")
        self.assertEqual(record.lifecycle, "pending")
        self.assertIsNone(getattr(record, "accepted_reply", None))
        self.assertIsNone(record.accepted_reply_hash)
        self.assertEqual(self.store.checkpoint("C1"), current)
