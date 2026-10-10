"""Offline integration tests for frozen proposals and conservative spend admission."""
import importlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.dwelly_cases.importer import import_cases
from tools.dwelly_cases.tests.fixtures import make_source

try:
    runner = importlib.import_module("tools.dwelly_model.runner")
    BudgetLedger = importlib.import_module("tools.dwelly_model.budget").BudgetLedger
except ModuleNotFoundError:
    runner = None
    BudgetLedger = None


def config():
    def seat(provider):
        return {"provider": provider, "model": "offline-model", "api_key_env": provider.upper() + "_TEST_KEY",
                "input_usd_per_million": 1, "output_usd_per_million": 2}
    return {"proposer": seat("openai"), "judges": [seat(p) for p in ("openai", "anthropic", "gemini")],
            "budget_per_model_usd": 25, "max_output_tokens": 256, "timeout_seconds": 5}


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(runner, "runner module must be implemented")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        source = self.root / "source"
        make_source(source)
        self.bundle = self.root / "bundle"
        import_cases(source, self.bundle, expected_cases=1)
        self.output = self.root / "experiment"

    def test_dry_run_needs_no_keys_and_persists_unsent_baseline_without_fake_judgments(self):
        with patch.dict("os.environ", {}, clear=True):
            result = runner.run_experiment(self.bundle, self.output, config(), limit=1)
        self.assertEqual(result["mode"], "offline_dry_run")
        self.assertEqual(result["live_calls"], 0)
        self.assertEqual(result["judge_coverage"]["expected_count"], 3)
        self.assertEqual(result["judge_coverage"]["scored_count"], 0)
        proposal = json.loads((self.output / "proposals/delivery-logistics-001.json").read_text())
        self.assertEqual(proposal["status"], "proposed_unsent")
        self.assertEqual(proposal["effects"], [])
        self.assertEqual(proposal["action"]["kind"], "request_customer_choice")
        self.assertTrue((self.output / "proposals-frozen.json").is_file())
        self.assertTrue((self.output / "budget.jsonl").is_file())
        self.assertTrue((self.output / "report.md").is_file())
        self.assertNotIn("SECRET_FUTURE_CONFIRMATION", (self.output / "snapshots/delivery-logistics-001.json").read_text())

    def test_preflight_presence_never_serializes_credentials(self):
        with patch.dict("os.environ", {"OPENAI_TEST_KEY": "secret-value"}, clear=True):
            result = runner.preflight(config())
        self.assertFalse(result["ready"])
        self.assertEqual(set(result["missing_credentials"]), {"ANTHROPIC_TEST_KEY", "GEMINI_TEST_KEY"})
        self.assertNotIn("secret-value", json.dumps(result))

    def test_missing_proposer_key_blocks_live_before_output(self):
        with patch.dict("os.environ", {}, clear=True), self.assertRaisesRegex(ValueError, "missing_proposer"):
            runner.run_experiment(self.bundle, self.output, config(), live=True)
        self.assertFalse(self.output.exists())

    def test_existing_destination_is_never_reused(self):
        self.output.mkdir()
        sentinel = self.output / "sentinel"
        sentinel.write_text("keep")
        with self.assertRaisesRegex(ValueError, "output_already_exists"):
            runner.run_experiment(self.bundle, self.output, config())
        self.assertEqual(sentinel.read_text(), "keep")

    def test_reference_tampering_is_detected_after_proposals_are_persisted(self):
        reference = self.bundle / "evaluation/delivery-logistics-001.json"
        data = json.loads(reference.read_text())
        data["action"]["body"] = "tampered action"
        reference.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "reference_integrity_mismatch"):
            runner.run_experiment(self.bundle, self.output, config())
        self.assertTrue((self.output / "proposals-frozen.json").exists())
        self.assertTrue((self.output / "failure.json").exists())

    def test_timeout_keeps_reservation_and_records_sanitized_error(self):
        with patch.dict("os.environ", {"OPENAI_TEST_KEY": "secret-value"}, clear=True), \
                patch("tools.dwelly_model.providers._open", side_effect=TimeoutError("secret-value")):
            result = runner.run_experiment(self.bundle, self.output, config(), live=True, compare_baseline=False)
        self.assertEqual(result["live_calls"], 1)
        self.assertEqual(result["proposal_count"], 0)
        self.assertGreater(result["budget"]["reserved_usd"], 0)
        self.assertNotIn("secret-value", json.dumps(result))
        self.assertEqual(result["judge_coverage"]["scored_count"], 0)

    def test_successful_api_boundary_freezes_first_and_judges_anonymous_candidates(self):
        candidate = {"action": {"kind": "request_customer_choice", "recipient": "Ari, recipient",
                                "channel": "Customer portal", "message": "Do you prefer 15:00 or 17:00?"},
                     "evidence_refs": ["event-001", "event-002"], "rationale": "A slot choice is missing.",
                     "missing_information": ["Preferred slot"], "required_approvals": []}
        judgment = {"scores": {key: 3 for key in runner.semantic.RUBRICS},
                    "explanation": "The request presents the visible alternatives.",
                    "evidence_refs": ["event-001"], "critical_failures": [], "abstain": False}
        observed = []

        class Response:
            status = 200
            headers = {"x-request-id": "offline-request"}

            def __init__(self, value):
                self.value = value

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def read(self, _limit):
                return json.dumps(self.value).encode()

        def transport(request, timeout):
            payload = json.loads(request.data)
            index = len(observed)
            observed.append((payload, (self.output / "proposals-frozen.json").exists()))
            text = json.dumps(candidate if index == 0 else judgment)
            if "openai.com" in request.full_url:
                value = {"status": "completed", "model": "observed-offline-model", "id": "response-1",
                         "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}]}
            elif "anthropic.com" in request.full_url:
                value = {"model": "observed-offline-model", "id": "response-1", "stop_reason": "end_turn",
                         "content": [{"type": "text", "text": text}]}
            else:
                value = {"modelVersion": "observed-offline-model", "responseId": "response-1",
                         "candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": text}]}}]}
            return Response(value)

        environment = {name: "offline-placeholder" for name in ("OPENAI_TEST_KEY", "ANTHROPIC_TEST_KEY", "GEMINI_TEST_KEY")}
        with patch.dict("os.environ", environment, clear=True), patch("tools.dwelly_model.providers._open", transport):
            result = runner.run_experiment(self.bundle, self.output, config(), live=True,
                                           include_reference=False, compare_baseline=True, repeat_judges=1)
        self.assertEqual(result["live_calls"], 13)
        self.assertEqual(result["judge_coverage"]["scored_count"], 3)
        self.assertEqual(result["all_judge_coverage"]["scored_count"], 12)
        self.assertFalse(observed[0][1])
        self.assertTrue(all(frozen for _, frozen in observed[1:]))
        for payload, _ in observed:
            self.assertNotIn("SECRET_FUTURE", json.dumps(payload))
            if "input" in payload:
                self.assertIn("json", payload["input"].lower())
        recorded_requests = [json.loads(path.read_text())
                             for path in (self.output / "requests").glob("*.json")]
        self.assertCountEqual(
            [(item["system"], item["prompt"]) for item in recorded_requests if item["provider"] == "openai"],
            [(payload["instructions"], payload["input"]) for payload, _ in observed if "input" in payload],
        )
        for payload, _ in observed[1:]:
            # Model selection is transport metadata; the actual judge content has no producer metadata.
            if "input" in payload:
                prompt = payload["input"]
            elif "messages" in payload:
                prompt = payload["messages"][0]["content"]
            else:
                prompt = payload["contents"][0]["parts"][0]["text"]
            body = json.loads(prompt)
            self.assertEqual(set(body), {"output_format", "visible_snapshot", "proposal"})
            self.assertEqual(body["output_format"], "json_object")
            self.assertEqual(set(body["proposal"]), {"action"})
        proposal = json.loads((self.output / "proposals/delivery-logistics-001.json").read_text())
        self.assertEqual(proposal["action"]["message"], "Do you prefer 15:00 or 17:00?")
        self.assertEqual(proposal["effects"], [])
        self.assertEqual(result["budget"]["reservation_count"], 13)
        receipt = json.loads((self.output / "receipts/delivery-logistics-001-proposer.json").read_text())
        self.assertEqual(receipt["response"]["observed_model"], "observed-offline-model")
        self.assertIsNone(receipt["response"]["input_tokens"])

    def test_missing_judges_stay_in_coverage_denominator(self):
        # A failed proposer must not fabricate judgments or silently replace missing seats.
        with patch.dict("os.environ", {"OPENAI_TEST_KEY": "offline-placeholder"}, clear=True), \
                patch("tools.dwelly_model.providers._open", side_effect=TimeoutError()):
            result = runner.run_experiment(self.bundle, self.output, config(), live=True, compare_baseline=False)
        self.assertEqual(result["judge_coverage"]["expected_count"], 3)
        self.assertEqual(result["judge_coverage"]["missing_count"], 3)
        self.assertIsNone(result["judge_coverage"]["mean_score"])

    def _run_nested_text(self, stage):
        candidate = {"action": {"kind": "request_customer_choice", "recipient": "Ari, recipient",
                                "channel": "Customer portal", "message": "Do you prefer 15:00 or 17:00?"},
                     "evidence_refs": ["event-001"], "rationale": "A slot choice is missing.",
                     "missing_information": [], "required_approvals": []}
        nested_text = "[" * 5000 + "0" + "]" * 5000
        responses = []

        class Response:
            status = 200
            headers = {}

            def __init__(self, text):
                self.text = text

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def read(self, _limit):
                return json.dumps({"status": "completed", "model": "offline-observed",
                                   "output": [{"type": "message", "content": [
                                       {"type": "output_text", "text": self.text}]}]}).encode()

        def transport(request, timeout):
            text = nested_text if stage == "proposer" or responses else json.dumps(candidate)
            responses.append(text)
            return Response(text)

        with patch.dict("os.environ", {"OPENAI_TEST_KEY": "offline-placeholder"}, clear=True), \
                patch("tools.dwelly_model.providers._open", transport):
            result = runner.run_experiment(self.bundle, self.output, config(), live=True, compare_baseline=False)
        expected_calls = 1 if stage == "proposer" else 2
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["live_calls"], expected_calls)
        self.assertEqual(result["budget"]["reservation_count"], expected_calls)
        self.assertGreater(result["budget"]["reserved_usd"], 0)
        self.assertEqual(result["judge_coverage"]["expected_count"], 3)
        self.assertEqual(result["judge_coverage"]["scored_count"], 0)
        self.assertIsNone(result["judge_coverage"]["mean_score"])
        self.assertTrue((self.output / "summary.json").is_file())
        self.assertFalse((self.output / "failure.json").exists())
        key = "delivery-logistics-001-" + ("proposer" if stage == "proposer" else "candidate-r0-judge0")
        self.assertEqual(result["execution_errors"][key], "invalid_" + ("proposal" if stage == "proposer" else "judgment"))
        receipt = json.loads((self.output / "receipts" / (key + ".json")).read_text())
        self.assertEqual(receipt["response"]["text"], nested_text)
        return result

    def test_deeply_nested_proposer_text_is_a_candidate_error_not_experiment_failure(self):
        result = self._run_nested_text("proposer")
        self.assertEqual(result["proposal_count"], 0)

    def test_deeply_nested_judge_text_is_a_seat_error_not_experiment_failure(self):
        result = self._run_nested_text("judge")
        self.assertEqual(result["proposal_count"], 1)
        record = json.loads((self.output / "judgments/delivery-logistics-001-candidate-r0-judge0.json").read_text())
        self.assertEqual(record["status"], "error")
        self.assertEqual(record["reason"], "invalid_judgment")
        self.assertIsNone(record["judgment"])


class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(BudgetLedger, "budget module must be implemented")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "budget.jsonl"

    def test_full_reservation_is_durable_and_cutoff_prevents_next_admission(self):
        seat = config()["proposer"]
        seat.update(input_usd_per_million=1000, output_usd_per_million=1000)
        with BudgetLedger(self.path, 1) as ledger:
            first = ledger.reserve(seat, "a", "b", 100, "proposal-1")
            self.assertGreater(first["reserved_usd"], 0.6)
            with self.assertRaisesRegex(ValueError, "budget_exhausted"):
                ledger.reserve(seat, "a", "b", 100, "proposal-2")
        rows = [json.loads(line) for line in self.path.read_text().splitlines()]
        self.assertEqual(len([r for r in rows if r["event"] == "reserve"]), 1)

    def test_active_ledger_has_exclusive_lock_and_duplicate_request_is_denied(self):
        with BudgetLedger(self.path, 25) as ledger:
            ledger.reserve(config()["proposer"], "system", "prompt", 10, "one")
            with self.assertRaisesRegex(ValueError, "duplicate_request"):
                ledger.reserve(config()["proposer"], "system", "prompt", 10, "one")
            with self.assertRaisesRegex(ValueError, "budget_locked"):
                with BudgetLedger(self.path, 25):
                    pass

    def test_invalid_budget_or_prices_are_denied(self):
        for cap in (0, -1, 26, float("nan"), float("inf")):
            with self.subTest(cap=cap), self.assertRaises(ValueError):
                BudgetLedger(self.path, cap)
        with BudgetLedger(self.path, 25) as ledger:
            for price in (0, -1, float("nan"), float("inf")):
                seat = config()["proposer"]
                seat["input_usd_per_million"] = price
                with self.subTest(price=price), self.assertRaises(ValueError):
                    ledger.reserve(seat, "a", "b", 100, str(price))

    def test_reopening_preserves_spend_and_prevents_duplicate_admission(self):
        with BudgetLedger(self.path, 25) as ledger:
            ledger.reserve(config()["proposer"], "system", "prompt", 10, "first")
            ledger.record_outcome("first", "error")
            spent = ledger.summary()["reserved_usd"]
        with BudgetLedger(self.path, 25) as ledger:
            self.assertEqual(ledger.summary()["reserved_usd"], spent)
            with self.assertRaisesRegex(ValueError, "duplicate_request"):
                ledger.reserve(config()["proposer"], "system", "prompt", 10, "first")


if __name__ == "__main__":
    unittest.main()
