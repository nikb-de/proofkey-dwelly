"""Breaks caught: fabricated decoding/ASR, forged records and lost failure states."""
import unittest

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
