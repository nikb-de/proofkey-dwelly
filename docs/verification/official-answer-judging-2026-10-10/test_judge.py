import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


class JudgeTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).with_name("judge.py")
        self.assertTrue(path.exists(), "official answer judge is not implemented")
        spec = importlib.util.spec_from_file_location("official_judge", path)
        self.judge = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.judge)

    def test_packet_preserves_exact_published_text_and_null_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "packet"
            manifest = self.judge.prepare(out)
            self.assertEqual(manifest["planned_attempts"], 90)
            for case in ("001", "014", "030"):
                payload = json.loads((out / "prompts" / f"{case}.json").read_text())["payload"]
                for name in ("INPUT.json", "ANSWER.md", "REASONING.md"):
                    self.assertEqual(payload[name], (self.judge.ROOT / "ANSWERS" / case / name).read_text())
                source = json.loads((self.judge.ROOT / "ANSWERS" / case / "SOURCE_RESULT.json").read_text())
                self.assertEqual(payload["candidate"], source["candidate"])
                self.assertNotIn("profile_id", payload)
                self.assertNotIn("response", payload)
            self.assertIsNone(json.loads((out / "prompts/014.json").read_text())["payload"]["candidate"])

    def test_missing_candidate_requires_abstention_without_zero_score_accuracy(self):
        source = json.loads((self.judge.ROOT / "ANSWERS/014/INPUT.json").read_text())
        judgment = {"scores": {name: 0 for name in self.judge.semantic.RUBRICS}, "explanation": "No accepted answer exists.",
                    "evidence_refs": [], "critical_failures": [], "abstain": False}
        with self.assertRaises(ValueError):
            self.judge.validate(source, None, judgment)
        judgment["abstain"] = True
        self.assertTrue(self.judge.validate(source, None, judgment)["abstain"])

    def test_summary_counts_missing_scheduled_cases_and_separates_abstention(self):
        seats = {"openai": {"model": "test"}}
        schedule = [{"provider": "openai", "case_id": f"{n:03}"} for n in range(1, 31)]
        judgment = {"scores": {k: 4 for k in self.judge.semantic.RUBRICS}, "abstain": True,
                    "critical_failures": [], "explanation": "Unavailable", "evidence_refs": []}
        result = self.judge.summarize(seats, schedule, [{"provider": "openai", "case_id": "014", "status": "ok", "judgment": judgment}], {"openai": 1})
        self.assertEqual(result["openai"]["expected"], 30)
        self.assertEqual(result["openai"]["missing"], 29)
        self.assertEqual(result["openai"]["assessment"]["expected_count"], 30)

    def test_rate_limit_stops_only_affected_seat_and_preserves_receipts(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "packet"
            self.judge.prepare(out)
            def fail(config, *args, **kwargs):
                raise self.judge.providers.ProviderError("http_429")
            with patch.object(self.judge.providers, "complete", side_effect=fail):
                result = self.judge.run(out)
            self.assertTrue(all(1 <= p["attempted"] <= 2 for p in result["providers"].values()))
            self.assertEqual(set(result["stopped"].values()), {"http_429"})
            for path in (out / "live/intents").glob("*.json"):
                self.assertIn("created_at", json.loads(path.read_text()))
            for path in (out / "live/records").glob("*.json"):
                self.assertIn("completed_at", json.loads(path.read_text()))

    def test_budget_refusal_retains_other_active_results(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "packet"
            self.judge.prepare(out)
            reserve = self.judge.BudgetLedger.reserve
            def limited(ledger, config, *args, **kwargs):
                if config["provider"] == "openai":
                    raise ValueError("budget_exhausted")
                return reserve(ledger, config, *args, **kwargs)
            with patch.object(self.judge.BudgetLedger, "reserve", limited), patch.object(self.judge.providers, "complete", side_effect=self.judge.providers.ProviderError("http_429")):
                result = self.judge.run(out)
            self.assertEqual(result["stopped"]["openai"], "budget_admission_budget_exhausted")
            self.assertEqual(result["providers"]["openai"]["attempted"], 0)
            self.assertGreater(result["recorded"], 0)

    def test_deadline_stops_before_any_dispatch(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "packet"
            self.judge.prepare(out)
            with patch.object(self.judge.providers, "complete") as complete:
                result = self.judge.run(out, dispatch_seconds=0)
            complete.assert_not_called()
            self.assertEqual(result["attempted"], 0)
            self.assertEqual(set(result["stopped"].values()), {"dispatch_deadline"})
            self.assertTrue(all(p["expected"] == 30 and p["missing"] == 30 for p in result["providers"].values()))

    def test_worker_rechecks_deadline_before_transport(self):
        with patch.object(self.judge.providers, "complete") as complete:
            with self.assertRaises(self.judge.providers.ProviderError):
                self.judge.dispatch({}, "system", "prompt", 0)
        complete.assert_not_called()

    def test_original_attachment_derivatives_are_valid_citation_targets(self):
        source = json.loads((self.judge.ROOT / "ANSWERS/006/INPUT.json").read_text())
        judgment = {"scores": {k: 4 for k in self.judge.semantic.RUBRICS}, "abstain": False,
                    "critical_failures": [], "explanation": "The retained tracking extraction differs from the reported parcel.",
                    "evidence_refs": ["attachment-tracking-screen"]}
        self.assertEqual(self.judge.validate(source, {}, judgment)["evidence_refs"], ["attachment-tracking-screen"])

    def test_snapshot_rejects_future_or_post_cutoff_business_supplement(self):
        for field, value in (("timestamp", "2030-01-01T00:00:00+00:00"), ("channel", "email")):
            source = json.loads((self.judge.ROOT / "ANSWERS/006/INPUT.json").read_text())
            source["messages"][-1][field] = value
            with self.assertRaises(ValueError):
                self.judge.snapshot(source)


if __name__ == "__main__":
    unittest.main()
