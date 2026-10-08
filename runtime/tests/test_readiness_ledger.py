"""Breaks caught: synthetic parsing/replay and incomplete identity posing as actual readiness."""
import unittest

from proofkey.assessment.readiness import ReadinessLedger
from support import make_processing_receipt


class ReadinessTests(unittest.TestCase):
    def test_replay_cannot_satisfy_actual_audio_or_model_role(self):
        ledger = ReadinessLedger(required={"audio_asr", "runtime_ai_plan"})
        ledger.record("audio_asr", make_processing_receipt(role="transcription", mode="recorded_replay"))
        ledger.record("runtime_ai_plan", make_processing_receipt(role="planning", mode="recorded_replay"))
        self.assertFalse(ledger.complete())
        self.assertEqual(set(ledger.missing()), {"audio_asr", "runtime_ai_plan"})

    def test_all_synthetic_and_deterministic_rows_remain_incomplete(self):
        ledger = ReadinessLedger()
        for dimension in ledger.required:
            ledger.record(dimension, make_processing_receipt(mode="deterministic"))
        self.assertFalse(ledger.complete())
        self.assertEqual(len(ledger.missing()), 10)

    def test_unknown_observed_model_or_usage_never_upgrades_actual(self):
        for changes in ({"observed_model": None}, {"usage": {}}, {"status": "outcome_unknown", "output": None}):
            with self.subTest(changes=changes):
                ledger = ReadinessLedger(required={"audio_asr"})
                ledger.record("audio_asr", make_processing_receipt(role="transcription", mode="actual", **changes))
                self.assertFalse(ledger.complete())

    def test_actual_role_receipt_must_match_dimension(self):
        ledger = ReadinessLedger(required={"runtime_ai_plan"})
        ledger.record("runtime_ai_plan", make_processing_receipt(mode="actual", role="transcription"))
        self.assertFalse(ledger.complete())
        ledger.record("runtime_ai_plan", make_processing_receipt(mode="actual", role="planning"))
        self.assertTrue(ledger.complete())

    def test_receipt_alone_cannot_attest_development_adaptation_or_input_class(self):
        for dimension in ("development_adaptation", "images_photos", "raw_audio"):
            ledger = ReadinessLedger(required={dimension})
            ledger.record(dimension, make_processing_receipt(mode="actual", role="planning"))
            self.assertFalse(ledger.complete())

    def test_unknown_dimension_and_mutable_receipt_rejected(self):
        ledger = ReadinessLedger(required={"audio_asr"})
        with self.assertRaises(ValueError):
            ledger.record("typo", make_processing_receipt())
        with self.assertRaises(TypeError):
            ledger.record("audio_asr", {"mode": "actual"})
