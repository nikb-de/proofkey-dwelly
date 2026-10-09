"""Complete local bookkeeping inventory; stored identities confer no authority."""
from pathlib import Path
import json
import sqlite3
import tempfile
import unittest

from proofkey.contracts import ReadTarget, RequestBinding
from proofkey.journal import CaseStore, JournalFailure
from support import NOW, make_binding, make_checkpoint, make_intent, make_request, make_result


class PacketHistoryTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "history.sqlite"
        self.store = CaseStore(self.path)
        self.addCleanup(lambda: self.store.close())

    def populate(self):
        # Both detached generations predate the first current checkpoint.
        bound_only = make_binding(request=make_request(request_id="REQ10"), generation="G10")
        stopped_request = make_request(request_id="REQ2")
        stopped = make_binding(request=stopped_request, generation="G2")
        self.store.bind(bound_only)
        self.store.bind(stopped)
        self.store.save_request(stopped, stopped_request)
        self.store.admit(make_binding(), make_request(), make_checkpoint())
        self.store.prepare(make_intent())
        self.store.set_stop("C1", "G2")

    def test_inventory_keeps_detached_bound_only_and_stopped_no_intent_generations(self):
        # A checkpoint/intent-only inventory loses G10 and the stopped G2.
        self.populate()
        inventory = self.store.request_bindings("C1")
        self.assertEqual(tuple(binding.generation for binding in inventory), ("G1", "G10", "G2"))
        self.assertIsNone(self.store.original_request("C1", "G10"))
        self.assertEqual(self.store.original_request("C1", "G2").request_id, "REQ2")
        self.assertTrue(self.store.generation_stop(inventory[2]).requested)
        self.assertEqual(tuple(record.intent.binding.generation for record in self.store.intents("C1")), ("G1",))

    def test_exact_case_filter_includes_a_case_without_checkpoint_or_original(self):
        # Case-prefix filtering or a join against checkpoints would lose or leak rows.
        self.populate()
        other = make_binding(request=make_request(case_id="C10"), generation="G0")
        self.store.bind(other)
        self.assertEqual(self.store.request_bindings("C10"), (other,))
        self.assertEqual(len(self.store.request_bindings("C1")), 3)
        self.assertEqual(self.store.request_bindings("C"), ())
        self.assertEqual(self.store.request_bindings("absent"), ())
        with self.assertRaises(JournalFailure):
            self.store.checkpoint("C10")
        self.assertIsNone(self.store.original_request("C10", "G0"))

    def test_inventory_is_an_immutable_defensive_typed_snapshot_after_reopen(self):
        # Returning cached/mutable bindings would allow consumers to rewrite identity.
        self.populate()
        first = self.store.request_bindings("C1")
        self.assertIsInstance(first, tuple)
        self.assertTrue(all(isinstance(binding, RequestBinding) for binding in first))
        with self.assertRaises((AttributeError, TypeError, ValueError)):
            first[1].principal_id = "attacker"
        changed = first[1].model_copy(update={"principal_id": "attacker"})
        self.assertNotEqual(changed, first[1])
        self.assertEqual(self.store.request_bindings("C1"), first)
        self.assertIsNot(self.store.request_bindings("C1")[1], first[1])
        self.store.close()
        self.store = CaseStore(self.path)
        self.assertEqual(self.store.request_bindings("C1"), first)

    def test_inventory_leaves_accounting_controls_requests_results_and_audit_untouched(self):
        # An inventory that reserves/refunds a read or alters history fails this check.
        self.populate()
        self.store.save_result(make_result())
        lease = self.store.begin_control_read(make_binding(),
            ReadTarget(kind="authority_facts", authority="case", facts=["binding"]), "recorded_state", NOW)
        checkpoint = self.store.checkpoint("C1")
        intents = self.store.intents("C1")
        result = self.store.saved_result("C1", "G1")
        paths = (self.path, Path(str(self.path) + "-wal"))
        before = tuple(path.read_bytes() for path in paths)
        self.assertEqual(len(self.store.request_bindings("C1")), 3)
        self.assertEqual(tuple(path.read_bytes() for path in paths), before)
        self.assertEqual(self.store.checkpoint("C1"), checkpoint)
        self.assertEqual(self.store.entry(lease.entry_id), lease)
        self.assertEqual(self.store.intents("C1"), intents)
        self.assertEqual(self.store.saved_result("C1", "G1"), result)
        self.assertEqual(self.store.original_request("C1", "G1"), make_request())
        self.assertTrue(self.store.generation_stop(self.store.request_bindings("C1")[2]).requested)

    def test_inventory_does_not_grant_stopped_or_bound_only_read_entry(self):
        # Local visibility must not bypass the existing disclosure entry fences.
        self.populate()
        inventory = self.store.request_bindings("C1")
        for binding in inventory[1:]:
            with self.subTest(generation=binding.generation), self.assertRaises(JournalFailure):
                self.store.begin_disclosure_read(binding, NOW)
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 0)

    def test_malformed_or_foreign_binding_fails_the_whole_inventory(self):
        # Skipping bad rows or returning a partially decoded prefix loses history.
        self.populate()
        bound_only = make_binding(request=make_request(request_id="REQ10"), generation="G10")
        original = bound_only.model_dump(mode="json")
        corruptions = (
            "{",
            '{"case_id":"C1","case_id":"C1"}',
            json.dumps({**original, "extra": "unexpected"}),
            json.dumps({**original, "case_id": "foreign"}),
            json.dumps({**original, "generation": "foreign"}),
            json.dumps({**original, "request_id": "foreign"}),
            json.dumps({**original, "request_revision": "foreign"}),
            json.dumps({**original, "consent_revision": "foreign"}),
            json.dumps({**original, "fingerprint": "0" * 64}),
        )
        for raw in corruptions:
            with self.subTest(raw=raw):
                with sqlite3.connect(self.path) as db:
                    db.execute("UPDATE requests SET binding_json=? WHERE case_id='C1' AND generation='G10'", (raw,))
                with self.assertRaises(JournalFailure):
                    self.store.request_bindings("C1")
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE requests SET binding_json=?,versions_json=? WHERE case_id='C1' AND generation='G10'",
                       (bound_only.model_dump_json(), '{"profile_version":1}'))
        with self.assertRaises(JournalFailure):
            self.store.request_bindings("C1")

    def test_index_corruption_is_revalidated_on_live_read_and_reopen(self):
        # Trusting only JSON would hide divergence between selection and identity.
        self.populate()
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE requests SET generation='G20' WHERE case_id='C1' AND generation='G10'")
        with self.assertRaises(JournalFailure):
            self.store.request_bindings("C1")
        self.store.close()
        with self.assertRaises(JournalFailure):
            CaseStore(self.path)
