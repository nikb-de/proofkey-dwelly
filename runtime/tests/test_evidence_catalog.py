"""Trusted synthetic scope; no identity here grants production authority.

Breaks caught: caller-name bypass, forged-record reads, filesystem escapes,
mutable scopes, persistence loss and derivatives widening private scope.
"""
import hashlib
import tempfile
import unittest
import os
import subprocess
import sys
from pathlib import Path

from proofkey.evidence.catalog import EvidenceCatalog, EvidenceAccessDenied, EvidencePathError
from proofkey.evidence.redaction import redact_derivative
from support import FakeClock, make_auth, NOW
from proofkey.contracts import TextSpan, PageRegion, Region, AudioTime, ProcessingReceipt

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures/development/media"
AUTH = make_auth(caller_id="OP1", proof_reference="recording-proof-1")


def synthetic_proof_resolver(auth, record, scope, purpose):
    return (auth.caller_id == "OP1" and auth.proof_reference == "recording-proof-1"
            and record.case_id == "C1" and auth.caller_id in scope["allowed_actors"])


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / "evidence"
        self.catalog = EvidenceCatalog(self.root, FakeClock(), allowed_input_roots=[FIXTURES],
            access_resolver=synthetic_proof_resolver,
            derivative_policies={"mask-synthetic": {"rights_reference": "synthetic-rights-v1",
                "replacements": {"SYNTHETIC NAME": "[REDACTED]"}, "allowed_actors": ["OP1"]}})

    def register(self, name="synthetic.txt", scope=None):
        return self.catalog.register(FIXTURES / name, "C1", "synthetic_fixture",
                                     scope or {"allowed_actors": ["OP1"]})

    def test_new_owner_and_wrong_proof_denied(self):
        record = self.register()
        for auth in (None, make_auth(caller_id="OP2"),
                     make_auth(caller_id="OP1", proof_reference="wrong-proof")):
            with self.subTest(auth=auth), self.assertRaises(EvidenceAccessDenied):
                self.catalog.get(record.artifact_id, auth)

    def test_original_hash_mime_time_and_restart_scope(self):
        scope = {"allowed_actors": ["OP1"]}
        record = self.register(scope=scope)
        scope["allowed_actors"].append("OP2")
        self.assertEqual(record.original_hash, hashlib.sha256(b"SYNTHETIC NAME reports damaged box.\n").hexdigest())
        self.assertEqual((record.mime_type, record.case_id, record.source, record.access),
                         ("text/plain", "C1", "synthetic_fixture", "restricted"))
        self.assertEqual(record.created_at, NOW)
        reopened = EvidenceCatalog(self.root, FakeClock(), allowed_input_roots=[FIXTURES],
                                   access_resolver=synthetic_proof_resolver)
        self.assertEqual(reopened.read_original(record.artifact_id, AUTH),
                         b"SYNTHETIC NAME reports damaged box.\n")
        self.assertEqual(reopened.get(record.artifact_id, AUTH), record)

    def test_sources_reject_escape_remote_and_symlink(self):
        for source in (Path(self.temp.name), "https://example.com/audio.wav"):
            with self.subTest(source=source), self.assertRaises(EvidencePathError):
                self.catalog.register(source, "C1", "synthetic_fixture", {"allowed_actors": ["OP1"]})
        link = Path(self.temp.name) / "link.txt"
        link.symlink_to(FIXTURES / "synthetic.txt")
        with self.assertRaises(EvidencePathError):
            self.catalog.register(link, "C1", "synthetic_fixture", {"allowed_actors": ["OP1"]})

    def test_oversize_rejected_before_read(self):
        catalog = EvidenceCatalog(self.root, allowed_input_roots=[FIXTURES],
                                  access_resolver=synthetic_proof_resolver, max_bytes=4)
        with self.assertRaises(EvidencePathError):
            catalog.register(FIXTURES / "synthetic.txt", "C1", "synthetic_fixture", {"allowed_actors": ["OP1"]})

    def test_catalog_rejects_oversized_assertion_storage(self):
        record = self.register()
        with self.assertRaises(EvidencePathError):
            self.catalog.assertion(record.artifact_id, "X" * (8 * 1024 * 1024 + 1), None, auth=AUTH)
        self.assertEqual(self.catalog.assertions(record.artifact_id, AUTH), [])

    def test_catalog_files_and_directories_remain_private(self):
        record = self.register()
        self.assertEqual(self.root.stat().st_mode & 0o077, 0)
        blob = self.root / "objects" / record.original_hash
        blob.chmod(0o644)
        with self.assertRaises(EvidencePathError):
            self.catalog.read_original(record.artifact_id, AUTH)

    def test_fifo_input_is_rejected_without_waiting_for_writer(self):
        fifo = self.root.parent / "fifo"
        os.mkfifo(fifo)
        code = "from proofkey.evidence.catalog import _bounded_read, EvidencePathError\nimport sys\ntry: _bounded_read(sys.argv[1], 100)\nexcept EvidencePathError: print('rejected')"
        result = subprocess.run([sys.executable, "-c", code, str(fifo)], timeout=2, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "rejected")

    def test_tampered_storage_and_symlink_root_fail_closed(self):
        record = self.register()
        blob = self.root / "objects" / record.original_hash
        blob.write_bytes(b"tampered")
        with self.assertRaises(EvidencePathError):
            self.catalog.read_original(record.artifact_id, AUTH)
        link = Path(self.temp.name) / "alias"
        link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(EvidencePathError):
            EvidenceCatalog(link, allowed_input_roots=[FIXTURES], access_resolver=synthetic_proof_resolver)

    def test_symlink_inside_permitted_root_is_rejected(self):
        permitted = self.root.parent / "inputs"
        permitted.mkdir()
        link = permitted / "recording.wav"
        link.symlink_to(FIXTURES / "synthetic.wav")
        catalog = EvidenceCatalog(self.root, allowed_input_roots=[permitted], access_resolver=synthetic_proof_resolver)
        with self.assertRaises(EvidencePathError):
            catalog.register(link, "C1", "synthetic_fixture", {"allowed_actors": ["OP1"]})

    def test_assertion_locator_is_bounded_and_references_real_receipt(self):
        text = self.register()
        claim = self.catalog.assertion(text.artifact_id, "box damaged", TextSpan(kind="text_span", start=23, end=30), auth=AUTH)
        receipt_path = self.root / "receipts" / (claim.processing_receipt_id + ".json")
        self.assertTrue(receipt_path.exists())
        receipt = ProcessingReceipt.model_validate_json(receipt_path.read_bytes())
        self.assertEqual(receipt.input_hashes, [text.original_hash])
        self.assertEqual(receipt.output.assertions, [])
        with self.assertRaises(ValueError):
            self.catalog.assertion(text.artifact_id, "beyond text", TextSpan(kind="text_span", start=0, end=999), auth=AUTH)
        for name, locator in (("synthetic.png", PageRegion(kind="page_region", page=1,
                                region=Region(x=3, y=0, width=2, height=1, units="pixels"))),
                              ("synthetic.pdf", PageRegion(kind="page_region", page=2)),
                              ("synthetic.wav", AudioTime(kind="audio_time", start_seconds=0, end_seconds=10))):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.catalog.assertion(self.register(name).artifact_id, "outside source", locator, auth=AUTH)

    def test_derivative_cannot_use_forged_record_or_widen_scope(self):
        record = self.register()
        forged = record.model_copy(update={"case_id": "C2"})
        with self.assertRaises(EvidenceAccessDenied):
            redact_derivative(forged, "mask-synthetic", "synthetic-rights-v1", catalog=self.catalog, auth=AUTH)
        with self.assertRaises(TypeError):
            self.catalog.derivative_policies["mask-synthetic"]["allowed_actors"] += ("OP2",)

    def test_assertions_keep_conflicts_and_unknown_coordinates(self):
        record = self.register()
        first = self.catalog.assertion(record.artifact_id, "box damaged", None, auth=AUTH)
        second = self.catalog.assertion(record.artifact_id, "box intact", None, auth=AUTH)
        self.assertEqual((first.locator.kind, second.locator.kind), ("unknown", "unknown"))
        self.assertEqual(first.uncertainty, "unverified")
        self.assertNotEqual(first.content_hash, second.content_hash)
        self.assertEqual(len(self.catalog.assertions(record.artifact_id, AUTH)), 2)
        with self.assertRaises(EvidenceAccessDenied):
            self.catalog.assertion(record.artifact_id, "forged", None)

    def test_redaction_preserves_original_and_requires_trusted_rights(self):
        record = self.register()
        for rights in ("self-attested", {"approved": True}):
            with self.subTest(rights=rights), self.assertRaises(EvidenceAccessDenied):
                redact_derivative(record, "mask-synthetic", rights, catalog=self.catalog, auth=AUTH)
        derivative = redact_derivative(record, "mask-synthetic", "synthetic-rights-v1", catalog=self.catalog, auth=AUTH)
        self.assertEqual(self.catalog.read_original(derivative.artifact_id, AUTH), b"[REDACTED] reports damaged box.\n")
        self.assertEqual(derivative.parent_hashes, [record.original_hash])
        self.assertNotEqual(derivative.original_hash, record.original_hash)
        self.assertEqual(self.catalog.read_original(record.artifact_id, AUTH), b"SYNTHETIC NAME reports damaged box.\n")
        with self.assertRaises(EvidenceAccessDenied):
            self.catalog.get(derivative.artifact_id, make_auth(caller_id="OP2"))
