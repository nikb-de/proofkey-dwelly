"""Only simulated provider calls; verifies live orchestration stop boundaries."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


class LiveTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).with_name("run_live.py")
        self.assertTrue(path.exists(), "bounded live runner is not implemented")
        spec = importlib.util.spec_from_file_location("calibration_live", path)
        self.live = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.live)

    def test_http404_stops_each_seat_without_retry_or_spending_on_remaining_attempts(self):
        with tempfile.TemporaryDirectory() as folder:
            packet = Path(folder) / "packet"
            self.live.pilot.prepare(self.live.pilot.ROOT / "tools/dwelly_analysis/model-profiles.current.json", packet, 1)
            calls = []
            def missing(seat, *args, **kwargs):
                calls.append(seat["provider"])
                raise self.live.providers.ProviderError("http_404")
            receipt = self.live.execute(packet, "canary", transport=missing)
            self.assertEqual(sorted(calls), ["anthropic", "gemini", "openai"])
            self.assertEqual(receipt["attempted_total"], 3)
            self.assertEqual(len(receipt["stopped_seats"]), 3)
            again = self.live.execute(packet, "canary", transport=missing)
            self.assertEqual(len(calls), 3)
            self.assertEqual(again["attempted_total"], 3)

    def test_remaining_phase_requires_saved_control_gate(self):
        with tempfile.TemporaryDirectory() as folder:
            packet = Path(folder) / "packet"
            self.live.pilot.prepare(self.live.pilot.ROOT / "tools/dwelly_analysis/model-profiles.current.json", packet, 1)
            with self.assertRaisesRegex(ValueError, "canary_gate"):
                self.live.execute(packet, "remaining")


if __name__ == "__main__":
    unittest.main()
