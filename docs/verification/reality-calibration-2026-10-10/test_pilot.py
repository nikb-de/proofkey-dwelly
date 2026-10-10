"""Offline accounting checks; fabricated test grades are not calibration evidence."""
import importlib.util
import json
import pathlib
import tempfile
import unittest


SCRIPT = pathlib.Path(__file__).with_name("pilot.py")


class PilotTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.exists(), "offline calibration reporter is not implemented")
        spec = importlib.util.spec_from_file_location("calibration_pilot", SCRIPT)
        self.pilot = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.pilot)

    def request(self, number):
        return {"request_id": f"a-r{number}-openai", "control_id": "a", "repeat": number,
                "provider": "openai", "requested_model": "test-model",
                "system_sha256": "system", "prompt_sha256": "prompt"}

    def result(self, number, score, critical=False, abstain=False):
        return {**self.request(number), "status": "ok", "observed_model": "test-model",
                "judgment": {"scores": {name: score for name in self.pilot.semantic.RUBRICS},
                             "abstain": abstain, "critical_failures": ["invented fact"] if critical else [],
                             "evidence_refs": ["event-001"], "explanation": "Test fixture only."}}

    def test_pending_attempts_are_not_scored_as_zero(self):
        summary = self.pilot.summarize([self.request(0), self.request(1)], [])
        seat = summary["seats"][0]
        self.assertEqual((seat["expected"], seat["pending"], seat["scored"]), (2, 2, 0))
        self.assertIsNone(seat["mean_score"])
        self.assertEqual(seat["repeat_pairs"], 0)
        self.assertIsNone(seat["critical_flag_flip_rate"])

    def test_flip_rate_and_spread_use_same_output_repetitions(self):
        requests = [self.request(i) for i in range(3)]
        results = [self.result(0, 1), self.result(1, 3, critical=True), self.result(2, 3, critical=True)]
        seat = self.pilot.summarize(requests, results)["seats"][0]
        self.assertEqual(seat["repeat_pairs"], 3)
        self.assertAlmostEqual(seat["critical_flag_flip_rate"], 2 / 3)
        self.assertAlmostEqual(seat["score_vector_flip_rate"], 2 / 3)
        self.assertEqual(seat["controls"][0]["rubric_spread"]["grounding"]["range"], 2)

    def test_abstention_is_coverage_loss_and_a_distinct_flip(self):
        seat = self.pilot.summarize([self.request(i) for i in range(2)],
                                    [self.result(0, 4), self.result(1, 0, abstain=True)])["seats"][0]
        self.assertEqual((seat["scored"], seat["abstained"]), (1, 1))
        self.assertEqual(seat["coverage"], .5)
        self.assertEqual(seat["mean_score"], 4)
        self.assertEqual(seat["abstention_flip_rate"], 1)
        self.assertEqual(seat["score_pairs"], 0)
        self.assertIsNone(seat["score_vector_flip_rate"])

    def test_unknown_duplicate_and_mismatched_prompt_results_are_rejected(self):
        original = self.result(0, 4)
        for results in ([original, original], [{**original, "request_id": "other"}],
                        [{**original, "prompt_sha256": "different"}]):
            with self.subTest(results=results), self.assertRaises(ValueError):
                self.pilot.summarize([self.request(0)], results)

    def test_wrong_model_is_not_silently_counted_as_requested_seat(self):
        result = {**self.result(0, 4), "observed_model": "substituted-model"}
        seat = self.pilot.summarize([self.request(0)], [result])["seats"][0]
        self.assertEqual(seat["identity_mismatch"], 1)
        self.assertEqual(seat["scored"], 0)
        self.assertIsNone(seat["mean_score"])

    def test_prepared_packet_cannot_be_silently_changed_before_report(self):
        with tempfile.TemporaryDirectory() as folder:
            output = pathlib.Path(folder) / "packet"
            self.pilot.prepare(self.pilot.ROOT / "tools/dwelly_model/config.example.json", output, 1)
            (output / "schedule.json").write_text("[]")
            with self.assertRaisesRegex(ValueError, "packet_integrity"):
                self.pilot.report(output, output / "results.json")

    def test_serialized_judge_payload_excludes_control_labels_and_rationale(self):
        for control in self.pilot.controls():
            with self.subTest(control=control["control_id"]):
                _, prompt = self.pilot.semantic.judge_prompt(control["snapshot"], control["candidate"])
                payload = json.loads(prompt)
                self.assertEqual(set(payload), {"output_format", "visible_snapshot", "proposal"})
                self.assertEqual(set(payload["proposal"]), {"action"})
                self.assertNotIn(control["candidate"]["rationale"], prompt)
                self.assertNotIn(control["control_id"], prompt)
                self.assertNotIn("anchor_direction", prompt)


if __name__ == "__main__":
    unittest.main()
