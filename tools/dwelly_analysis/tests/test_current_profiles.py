"""Offline regression checks for the reviewed current API profile snapshot."""
from decimal import Decimal
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.dwelly_analysis import model


PROFILE_PATH = Path(__file__).parents[1] / "model-profiles.current.json"


class CurrentProfilesTests(unittest.TestCase):
    def test_current_snapshot_loads_with_exact_reviewed_ids_and_rates(self):
        settings = model.load_profiles(PROFILE_PATH)
        actual = {
            p["config"]["provider"]: (
                p["config"]["model"],
                Decimal(str(p["config"]["input_usd_per_million"])),
                Decimal(str(p["config"]["output_usd_per_million"])),
            )
            for p in settings["profiles"]
        }
        self.assertEqual(len(settings["profiles"]), 3)
        self.assertEqual(actual, {
            "openai": ("gpt-6.1-sol", Decimal("2"), Decimal("10")),
            "anthropic": ("claude-sonnet-5-5", Decimal("2"), Decimal("10")),
            "gemini": ("gemini-3.8-flash", Decimal("0.75"), Decimal("3.75")),
        })
        self.assertEqual(settings["budget_per_model_usd"], 25)
        self.assertEqual(settings["max_output_tokens"], 8192)
        self.assertEqual(settings["timeout_seconds"], 120)

    def test_current_profiles_are_unavailable_without_credentials_and_make_no_calls(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(
            model.providers, "complete", side_effect=AssertionError("no provider calls allowed")
        ) as complete:
            profiles = model.public_profiles(model.load_profiles(PROFILE_PATH))
        self.assertTrue(all(not profile["available"] for profile in profiles))
        self.assertTrue(all(profile["reason"] == "missing_api_key" for profile in profiles))
        self.assertEqual(complete.call_count, 0)


if __name__ == "__main__":
    unittest.main()
