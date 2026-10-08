"""Breaks caught: fabricated decoding/ASR, forged records and lost failure states."""
import unittest
from unittest.mock import patch
from pypdf import PdfReader
from pypdf.generic import EncodedStreamObject

from proofkey.evidence.intake import inspect_content, IntakeLimits
from proofkey.evidence.catalog import EvidenceAccessDenied
import test_evidence_catalog as catalog_tests
AUTH = catalog_tests.AUTH


class MediaTests(unittest.TestCase):
    setUp = catalog_tests.EvidenceTests.setUp
    register = catalog_tests.EvidenceTests.register

    def inspect(self, name, limits=None):
        record = self.register(name)
        return inspect_content(record, limits or IntakeLimits(), catalog=self.catalog, auth=AUTH)

    def test_real_supported_bytes_decode_with_coordinates(self):
        for name, coordinate in (("synthetic.txt", "text_span"), ("synthetic.json", "text_span"),
                                 ("synthetic.png", "page_region"), ("synthetic.jpg", "page_region"),
                                 ("synthetic.pdf", "page_region"), ("synthetic.wav", "audio_time")):
            with self.subTest(name=name):
                receipt = self.inspect(name)
                self.assertEqual(receipt.status, "completed")
                self.assertEqual(receipt.role, "extraction")
                self.assertEqual(receipt.available_coordinates[0].kind, coordinate)
                self.assertIn("semantic", receipt.reason)
                self.assertEqual(receipt.output.kind, "assertions")
                self.assertEqual(receipt.output.assertions, [])

    def test_supplied_transcript_is_text_not_asr(self):
        receipt = self.inspect("supplied.transcript")
        self.assertEqual(receipt.status, "completed")
        self.assertEqual(receipt.role, "extraction")
        self.assertEqual(receipt.output.text, "Synthetic supplied transcript: box is damaged.\n")
        self.assertEqual(receipt.output.segments[0].locator.kind, "text_span")
        self.assertIn("not ASR", receipt.reason)

    def test_byte_parsing_cannot_report_actual_provider_mode(self):
        for name, status, mode in (("synthetic.txt", "completed", "deterministic"),
                                  ("supplied.transcript", "completed", "deterministic"),
                                  ("malformed.json", "failed", "deterministic"),
                                  ("synthetic.mp3", "unavailable", "unavailable")):
            with self.subTest(name=name):
                receipt = self.inspect(name)
                self.assertEqual((receipt.status, receipt.mode), (status, mode))
                self.assertIsNone(receipt.observed_model)

    def test_malformed_encrypted_unsupported_and_unavailable_visible(self):
        for name, status in (("malformed.json", "failed"), ("malformed.png", "failed"),
                             ("malformed.wav", "failed"), ("malformed.pdf", "failed"),
                             ("encrypted.pdf", "unavailable"), ("unsupported.bin", "unavailable"),
                             ("synthetic.mp3", "unavailable")):
            with self.subTest(name=name):
                receipt = self.inspect(name)
                self.assertEqual(receipt.status, status)
                self.assertIsNone(receipt.output)
                self.assertTrue(receipt.reason)

    def test_limit_failure_has_no_decoded_output(self):
        receipt = self.inspect("synthetic.png", IntakeLimits(max_pixels=1))
        self.assertEqual(receipt.status, "failed")
        self.assertIsNone(receipt.output)
        receipt = self.inspect("synthetic.txt", IntakeLimits(max_bytes=1))
        self.assertEqual(receipt.status, "failed")
        self.assertIsNone(receipt.output)

    def test_invalid_text_nonfinite_json_and_truncated_wav_fail(self):
        for name in ("malformed.txt", "nonfinite.json", "truncated.wav", "compressed-bomb.pdf", "compressed-aggregate.pdf"):
            with self.subTest(name=name):
                receipt = self.inspect(name)
                self.assertEqual(receipt.status, "failed")
                self.assertIsNone(receipt.output)
        for limits in ({"max_bytes": -1}, {"max_audio_seconds": float("inf")}, {"max_pixels": True}):
            with self.subTest(limits=limits), self.assertRaises(ValueError):
                IntakeLimits(**limits)

    def test_forged_record_or_absent_authority_never_reads(self):
        record = self.register()
        forged = record.model_copy(update={"source_reference": "/etc/passwd"})
        for candidate, auth, catalog in ((forged, AUTH, self.catalog), (record, None, self.catalog),
                                        (record, AUTH, None)):
            with self.subTest(candidate=candidate), self.assertRaises(EvidenceAccessDenied):
                inspect_content(candidate, IntakeLimits(), catalog=catalog, auth=auth)

    def test_actual_repeated_deep_cyclic_and_count_trees_fail(self):
        for name in ("repeated-page.pdf", "repeated-subtree.pdf", "cyclic-pages.pdf",
                     "deep-pages.pdf", "oversized-count.pdf", "too-many-pages.pdf"):
            with self.subTest(name=name):
                receipt = self.inspect(name)
                self.assertEqual((receipt.status, receipt.mode), ("failed", "deterministic"))
                self.assertIsNone(receipt.output)
                self.assertEqual(receipt.available_coordinates, [])

    def test_real_pdf_parser_never_uses_unbounded_flatten(self):
        # Narrow unsafe-allocation trap: all actual PDF bytes/parser objects are real.
        # Calling this dependency operation is the bug, even if rejection follows.
        with patch.object(PdfReader, "_flatten", side_effect=AssertionError("unbounded_flatten_called")):
            for name in ("repeated-subtree.pdf", "cyclic-pages.pdf", "deep-pages.pdf",
                         "oversized-count.pdf", "too-many-pages.pdf"):
                with self.subTest(name=name):
                    receipt = self.inspect(name)
                    self.assertEqual(receipt.status, "failed")
                    self.assertEqual(receipt.reason, "Format decoding failed: ValueError")
            receipt = self.inspect("two-pages.pdf")
            self.assertEqual(receipt.status, "completed")
            self.assertEqual([item.page for item in receipt.available_coordinates], [1, 2])

    def test_page_tree_node_reference_and_depth_budgets_enforced(self):
        for limits in (IntakeLimits(max_pdf_nodes=2), IntakeLimits(max_pdf_references=1),
                       IntakeLimits(max_pdf_depth=1)):
            with self.subTest(limits=limits):
                receipt = self.inspect("two-pages.pdf", limits)
                self.assertEqual(receipt.status, "failed")
                self.assertIsNone(receipt.output)

    def test_compressed_xref_and_object_stream_routes_unavailable_before_decode(self):
        names = ("xref-stream-bomb.pdf", "escaped-xref-stream-bomb.pdf", "hybrid-xref-stream-bomb.pdf",
                 "escaped-hybrid-xref-stream-bomb.pdf",
                 "previous-xref-stream-bomb.pdf", "object-stream-bomb.pdf")
        # Trap the exact unsafe dependency operation; input, xref dispatch and
        # parser are real. A pre-limit get_data produces failed, not unavailable.
        with patch.object(EncodedStreamObject, "get_data", side_effect=AssertionError("unbounded_stream_decode_called")):
            for name in names:
                with self.subTest(name=name):
                    receipt = self.inspect(name)
                    self.assertEqual((receipt.status, receipt.mode), ("unavailable", "unavailable"))
                    self.assertIsNone(receipt.output)
                    self.assertIn("compressed", receipt.reason)
            self.assertEqual(self.inspect("synthetic.pdf").status, "completed")
            self.assertEqual(self.inspect("classic-v15.pdf").status, "completed")

    def test_untested_pdf_library_version_fails_closed(self):
        with patch("importlib.metadata.version", return_value="6.11.0"):
            receipt = self.inspect("synthetic.pdf")
            self.assertEqual((receipt.status, receipt.mode), ("unavailable", "unavailable"))
            self.assertIsNone(receipt.output)
