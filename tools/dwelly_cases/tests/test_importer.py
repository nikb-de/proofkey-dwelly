import hashlib
import importlib
import json
from pathlib import Path
import tempfile
import unittest

from tools.dwelly_cases.tests.fixtures import make_source

try:
    importer = importlib.import_module("tools.dwelly_cases.importer")
except ImportError:
    importer = None


class ImporterTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importer, "missing offline importer")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "source"
        self.case = make_source(self.source)

    def test_snapshot_contains_only_available_events_and_attachments(self):
        snapshot, reference, inventory = importer.parse_case(self.case)
        self.assertEqual([e["event_id"] for e in snapshot["events"]], ["event-001", "event-002"])
        self.assertEqual(snapshot["case_id"], "delivery-logistics-001")
        self.assertEqual(snapshot["cutoff_event"], "event-002")
        self.assertEqual(snapshot["events"][0]["occurred_at"], "2026-02-02T09:01:00+00:00")
        self.assertEqual([a["path"] for a in snapshot["attachments"]], ["attachments/visible.txt"])
        self.assertEqual(reference["action"]["event_id"], "event-003")
        self.assertEqual(len(inventory["files"]), 4)
        self.assertNotIn("SECRET_FUTURE", json.dumps(snapshot))
        self.assertNotIn("future.txt", json.dumps(snapshot))

    def test_future_mutation_leaves_input_hash_and_snapshot_identical(self):
        before, _, _ = importer.parse_case(self.case)
        path = self.case / "history.md"
        path.write_text(path.read_text().replace("SECRET_FUTURE_ACTION", "DIFFERENT_ANSWER"))
        (self.case / "index.md").write_text("Entirely changed future summary")
        (self.case / "attachments/future.txt").write_bytes(b"different future receipt")
        after, _, _ = importer.parse_case(self.case)
        self.assertEqual(before, after)

    def test_source_bytes_and_hashes_are_preserved(self):
        source_bytes = (self.case / "history.md").read_bytes()
        output = self.root / "bundle"
        manifest = importer.import_cases(self.source, output, expected_cases=1)
        copied = output / "raw/Delivery & Logistics/001/history.md"
        self.assertEqual(copied.read_bytes(), source_bytes)
        self.assertEqual(manifest["case_count"], 1)
        entry = next(f for f in manifest["files"] if f["path"].endswith("history.md"))
        self.assertEqual(entry["sha256"], hashlib.sha256(source_bytes).hexdigest())
        saved = json.loads((output / "agent/delivery-logistics-001.json").read_text())
        self.assertNotIn("SECRET_FUTURE", json.dumps(saved))

    def test_rejects_history_gap_without_publishing(self):
        path = self.case / "history.md"
        path.write_text(path.read_text().replace("event-002", "event-009").replace("event 002", "event 009"))
        output = self.root / "bundle"
        with self.assertRaises(ValueError):
            importer.import_cases(self.source, output, expected_cases=1)
        self.assertFalse(output.exists())

    def test_rejects_nonchronological_events(self):
        path = self.case / "history.md"
        path.write_text(path.read_text().replace("09:02:00", "08:02:00"))
        with self.assertRaises(ValueError):
            importer.parse_case(self.case)

    def test_rejects_unknown_stage_and_duplicate_action(self):
        path = self.case / "history.md"
        original = path.read_text()
        for changed in (original.replace("**Stage:** Context", "**Stage:** Surprise"),
                        original.replace("**Stage:** Follow-through / confirmation", "**Stage:** Agent action")):
            path.write_text(changed)
            with self.assertRaises(ValueError):
                importer.parse_case(self.case)

    def test_rejects_anchor_header_disagreement(self):
        path = self.case / "history.md"
        path.write_text(path.read_text().replace('id="event-001"', 'id="event-999"'))
        with self.assertRaises(ValueError):
            importer.parse_case(self.case)

    def test_rejects_traversal_even_in_future_links(self):
        path = self.case / "history.md"
        path.write_text(path.read_text().replace("attachments/future.txt", "../private.txt"))
        with self.assertRaises(ValueError):
            importer.parse_case(self.case)

    def test_rejects_missing_attachment(self):
        (self.case / "attachments/visible.txt").unlink()
        with self.assertRaises(ValueError):
            importer.parse_case(self.case)

    def test_rejects_symlink_source(self):
        target = self.root / "outside.txt"
        target.write_text("not case data")
        attachment = self.case / "attachments/visible.txt"
        attachment.unlink()
        attachment.symlink_to(target)
        with self.assertRaises(ValueError):
            importer.parse_case(self.case)

    def test_refuses_existing_output_without_touching_it(self):
        output = self.root / "bundle"
        output.mkdir()
        keep = output / "keep"
        keep.write_text("owned by user")
        with self.assertRaises((ValueError, FileExistsError)):
            importer.import_cases(self.source, output, expected_cases=1)
        self.assertEqual(keep.read_text(), "owned by user")

    def test_refuses_output_inside_source(self):
        with self.assertRaises(ValueError):
            importer.import_cases(self.source, self.source / "bundle", expected_cases=1)

    def test_count_mismatch_does_not_publish(self):
        output = self.root / "bundle"
        with self.assertRaises(ValueError):
            importer.import_cases(self.source, output, expected_cases=50)
        self.assertFalse(output.exists())

    def test_identical_events_timestamps_keep_source_ordinal(self):
        path = self.case / "history.md"
        path.write_text(path.read_text().replace("09:02:00", "09:01:00"))
        snapshot, _, _ = importer.parse_case(self.case)
        self.assertEqual([e["event_id"] for e in snapshot["events"]], ["event-001", "event-002"])


if __name__ == "__main__":
    unittest.main()
