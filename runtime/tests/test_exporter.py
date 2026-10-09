"""Exporter disk semantics; all paths and adversarial files are task-owned."""
import hashlib
import fcntl
import json
import os
import signal
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from proofkey.contracts import CaseResult, VerificationResult
from proofkey.exporter import ExportFailure, export_case
from support import NOW, make_result


class ExportTests(unittest.TestCase):
    def setUp(self):
        # macOS /var is a symlink; use the real task-owned temporary ancestry.
        self.folder = tempfile.TemporaryDirectory(dir=Path(tempfile.gettempdir()).resolve())
        self.addCleanup(self.folder.cleanup)
        self.base = Path(self.folder.name)
        self.root = self.base / "ANSWERS"

    def test_export_path_and_collision_controls(self):
        with self.assertRaises(ExportFailure):
            export_case(make_result(case_id="../escape"), self.root)
        export_case(make_result(case_id="CaseA"), self.root)
        with self.assertRaises(ExportFailure):
            export_case(make_result(case_id="casea"), self.root)
        self.assertTrue((self.root / "CaseA" / "ANSWER.md").exists())

    def test_absolute_separator_and_control_ids_cannot_create_files(self):
        for value in (str(self.base / "escape"), "/absolute", "a/b", "a\\b", "..", ".", "C:\\x", "nul\x00x", "bidi\u202ex"):
            with self.subTest(value=value), self.assertRaises(ExportFailure):
                export_case(make_result(case_id=value), self.root)
        self.assertFalse(self.root.exists())
        self.assertFalse((self.base / "escape").exists())

    def test_unicode_and_preexisting_entries_reserve_collision_namespace(self):
        export_case(make_result(case_id="Caf\u00e9"), self.root)
        for value in ("Cafe\u0301", "CAF\u00c9"):
            with self.assertRaises(ExportFailure):
                export_case(make_result(case_id=value), self.root)
        existing = self.root / "UserCase"
        existing.write_text("user-owned")
        with self.assertRaises(ExportFailure):
            export_case(make_result(case_id="usercase"), self.root)
        self.assertEqual(existing.read_text(), "user-owned")

    def test_denied_error_and_partial_outputs_are_auditable_not_success_claims(self):
        cases = [CaseResult(status="denied", correlation_id="Denied", reason="denied"),
                 CaseResult(status="error", correlation_id="Error", reason="runtime_error"),
                 make_result(case_id="Partial", effects={"create_return": VerificationResult(status="outcome_unknown")},
                             wait_status="pending", handoff_status="outcome_unknown", historical=True)]
        for result in cases:
            before = datetime.now(timezone.utc)
            receipt = export_case(result, self.root)
            after = datetime.now(timezone.utc)
            self.assertIsNotNone(receipt)
            self.assertEqual(receipt.supplied_case_id, result.case_id)
            self.assertEqual(receipt.status, "written")
            answer = (self.root / result.case_id / "ANSWER.md").read_text()
            reasoning = (self.root / result.case_id / "REASONING.md").read_text()
            self.assertIn("Source mode: offline", answer)
            self.assertIn(result.status, answer)
            if result.status != "authorized":
                self.assertLessEqual(before, receipt.as_of)
                self.assertLessEqual(receipt.as_of, after)
                self.assertNotIn("synthetic-evidence", answer + reasoning)
                self.assertNotIn("fingerprint", answer + reasoning)
            else:
                self.assertEqual(receipt.as_of, NOW)
                for fact in ("outcome_unknown", "pending", "historical"):
                    self.assertIn(fact, answer)
                self.assertIn("Synthetic offline fixture", reasoning)

    def test_hash_is_independently_reproducible_and_bytes_are_deterministic(self):
        result = make_result(case_id="Stable")
        receipts = [export_case(result, self.base / name) for name in ("one", "two")]
        payloads = []
        for name, receipt in zip(("one", "two"), receipts):
            self.assertTrue((self.base / name / "Stable" / "ANSWER.md").is_file())
            files = {filename: (self.base / name / "Stable" / filename).read_bytes()
                     for filename in ("ANSWER.md", "REASONING.md")}
            payloads.append(files)
            hashes = {filename: hashlib.sha256(payload).hexdigest() for filename, payload in files.items()}
            expected = hashlib.sha256(json.dumps(hashes, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
            self.assertIsNotNone(receipt)
            self.assertEqual(receipt.output_hash, expected)
            self.assertEqual(receipt.output_name, "Stable")
        self.assertEqual(payloads[0], payloads[1])

    def test_symlink_root_ancestor_and_case_conflicts_cannot_touch_target(self):
        target = self.base / "target"
        target.mkdir()
        (target / "canary").write_text("untouched")
        self.root.symlink_to(target, target_is_directory=True)
        with self.assertRaises(ExportFailure):
            export_case(make_result(), self.root)
        ancestor = self.base / "alias"
        ancestor.symlink_to(target, target_is_directory=True)
        with self.assertRaises(ExportFailure):
            export_case(make_result(), ancestor / "new")
        real = self.base / "real"
        real.mkdir()
        (real / "C1").symlink_to(target, target_is_directory=True)
        with self.assertRaises(ExportFailure):
            export_case(make_result(), real)
        self.assertEqual(sorted(p.name for p in target.iterdir()), ["canary"])
        self.assertEqual((target / "canary").read_text(), "untouched")

    def test_link_race_never_overwrites_a_user_file(self):
        real_link = os.link
        def conflict(source, destination, **kwargs):
            (self.root / "C1" / destination).write_text("user-owned-canary")
            return real_link(source, destination, **kwargs)
        with patch("proofkey.exporter.os.link", side_effect=conflict), self.assertRaises(ExportFailure) as caught:
            export_case(make_result(), self.root)
        self.assertEqual((self.root / "C1" / "ANSWER.md").read_text(), "user-owned-canary")
        self.assertEqual(caught.exception.supplied_case_id, "C1")

    def test_receipt_requires_actual_published_bytes_not_just_intended_bytes(self):
        real_link = os.link
        def corrupt(source, destination, **kwargs):
            real_link(source, destination, **kwargs)
            (self.root / "C1" / destination).write_text("interrupted/corrupted storage")
        with patch("proofkey.exporter.os.link", side_effect=corrupt), self.assertRaises(ExportFailure):
            export_case(make_result(), self.root)

    def test_interrupted_second_file_keeps_partial_case_visible_and_blocks_reuse(self):
        real_link = os.link
        def interrupt(source, destination, **kwargs):
            if destination == "REASONING.md":
                raise OSError("PRIVATE_EXCEPTION_CANARY")
            return real_link(source, destination, **kwargs)
        with patch("proofkey.exporter.os.link", side_effect=interrupt), self.assertRaises(ExportFailure) as caught:
            export_case(make_result(), self.root)
        self.assertNotIn("PRIVATE_EXCEPTION_CANARY", str(caught.exception))
        self.assertIsNone(caught.exception.__cause__)
        self.assertIsNone(caught.exception.__context__)
        case = self.root / "C1"
        original = {p.name: p.read_bytes() for p in case.iterdir()}
        self.assertIn("ANSWER.md", original)
        self.assertNotIn("REASONING.md", original)
        self.assertTrue(any(name.startswith("REASONING.md.pending-") for name in original))
        with self.assertRaises(ExportFailure):
            export_case(make_result(), self.root)
        self.assertEqual(original, {p.name: p.read_bytes() for p in case.iterdir()})

    def test_actual_process_kill_keeps_completed_and_pending_files_visible(self):
        script = """
import os, signal, sys
from unittest.mock import patch
from proofkey.exporter import export_case
from support import make_result
real = os.link
def die(source, destination, **kwargs):
    if destination == 'REASONING.md':
        os.kill(os.getpid(), signal.SIGKILL)
    return real(source, destination, **kwargs)
with patch('proofkey.exporter.os.link', side_effect=die):
    export_case(make_result(), sys.argv[1])
"""
        run = subprocess.run([sys.executable, "-c", script, str(self.root)], capture_output=True, timeout=10)
        self.assertEqual(run.returncode, -signal.SIGKILL)
        self.assertTrue((self.root / "C1" / "ANSWER.md").is_file())
        self.assertFalse((self.root / "C1" / "REASONING.md").exists())
        self.assertTrue(list((self.root / "C1").glob("REASONING.md.pending-*")))
        with self.assertRaises(ExportFailure):
            export_case(make_result(), self.root)

    def test_symlink_swap_during_publication_fails_without_touching_target(self):
        target = self.base / "target"
        target.mkdir()
        (target / "canary").write_text("user-owned")
        parked = self.base / "parked-case"
        real_link = os.link
        def swap(source, destination, **kwargs):
            (self.root / "C1").rename(parked)
            (self.root / "C1").symlink_to(target, target_is_directory=True)
            return real_link(source, destination, **kwargs)
        with patch("proofkey.exporter.os.link", side_effect=swap), self.assertRaises(ExportFailure):
            export_case(make_result(), self.root)
        self.assertEqual([p.name for p in target.iterdir()], ["canary"])
        self.assertEqual((target / "canary").read_text(), "user-owned")

    def test_ancestor_swap_during_traversal_fails_before_target_write(self):
        parent = self.base / "parent"
        parent.mkdir()
        target = self.base / "target"
        target.mkdir()
        parked = self.base / "parked-parent"
        real_open = os.open
        def swap(path, *args, **kwargs):
            if path == "ANSWERS":
                parent.rename(parked)
                parent.symlink_to(target, target_is_directory=True)
            return real_open(path, *args, **kwargs)
        with patch("proofkey.exporter.os.open", side_effect=swap), self.assertRaises(ExportFailure):
            export_case(make_result(), parent / "ANSWERS")
        self.assertEqual(list(target.iterdir()), [])

    def test_concurrent_normalized_collisions_allow_only_one_writer(self):
        self.root.mkdir()
        def write(value):
            try:
                return export_case(make_result(case_id=value), self.root).status
            except ExportFailure:
                return "failed"
        with ThreadPoolExecutor(max_workers=4) as executor:
            statuses = list(executor.map(write, ["CaseA", "casea", "CASEA", "CaSeA"] * 3))
        self.assertEqual(statuses.count("written"), 1)
        self.assertEqual(statuses.count("failed"), 11)
        self.assertEqual(len(list(self.root.iterdir())), 1)

    def test_unvalidated_models_cannot_smuggle_private_denial_or_authority(self):
        invalid = CaseResult.model_construct(status="denied", correlation_id="Denied", reason="denied",
                                             rationale="PRIVATE_EXCEPTION_CANARY")
        with self.assertRaises(ExportFailure) as caught:
            export_case(invalid, self.root)
        self.assertNotIn("PRIVATE_EXCEPTION_CANARY", str(caught.exception))
        self.assertFalse(self.root.exists())
        with self.assertRaises(ExportFailure):
            export_case({"status": "authorized", "case_id": "CallerGrant"}, self.root)

    def test_busy_root_fails_without_an_unbounded_lock_wait(self):
        self.root.mkdir()
        fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
        self.addCleanup(os.close, fd)
        fcntl.flock(fd, fcntl.LOCK_EX)
        # Child timeout prevents an unsafe implementation from hanging the suite.
        script = """
import sys
from proofkey.exporter import ExportFailure, export_case
from support import make_result
try:
    export_case(make_result(), sys.argv[1])
except ExportFailure:
    sys.exit(0)
sys.exit(3)
"""
        try:
            run = subprocess.run([sys.executable, "-c", script, str(self.root)], capture_output=True, timeout=2)
        except subprocess.TimeoutExpired:
            self.fail("Exporter waited indefinitely for a busy root")
        self.assertEqual(run.returncode, 0)
        self.assertEqual(list(self.root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
