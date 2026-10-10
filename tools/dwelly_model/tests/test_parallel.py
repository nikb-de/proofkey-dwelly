"""Offline behavioral checks for parallel admission and cancellation."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import shutil
import threading
import unittest
from unittest.mock import patch
import tempfile

from tools.dwelly_cases.importer import import_cases
from tools.dwelly_cases.tests.fixtures import make_source
from tools.dwelly_model import runner
from tools.dwelly_model.__main__ import main
from tools.dwelly_model.tests.test_runner import config


class Response:
    status = 200
    headers = {}

    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self, _limit):
        return json.dumps(self.body).encode()


class ParallelTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        source = self.root / "source"
        for number in ("001", "002", "003"):
            case = make_source(source, number)
            history = case / "history.md"
            history.write_text(history.read_text().replace("There are", f"Fixture {number}. There are"))
        self.bundle = self.root / "bundle"
        import_cases(source, self.bundle, expected_cases=3)
        self.output = self.root / "experiment"
        self.env = patch.dict(os.environ, {provider + "_TEST_KEY": "offline-placeholder"
                                          for provider in ("OPENAI", "ANTHROPIC", "GEMINI")}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def transport(self, request, timeout):
        wire = json.loads(request.data)
        prompt = wire.get("input") or (wire["messages"][0]["content"] if "messages" in wire
                                       else wire["contents"][0]["parts"][0]["text"])
        payload = json.loads(prompt)
        if "proposal" in payload:
            self.assertTrue((self.output / "proposals-frozen.json").is_file())
            value = {"scores": {key: 3 for key in runner.semantic.RUBRICS}, "explanation": "Visible request.",
                     "evidence_refs": ["event-001"], "critical_failures": [], "abstain": False}
        else:
            number = payload["visible_snapshot"]["events"][0]["body"].split()[1].rstrip(".")
            value = {"action": {"kind": "request_customer_choice", "recipient": "Ari, recipient",
                                "channel": "Customer portal", "message": "Please choose a slot for " + number},
                     "evidence_refs": ["event-001"], "rationale": "Choice is missing.",
                     "missing_information": ["Slot"], "required_approvals": []}
        text = json.dumps(value)
        if "openai.com" in request.full_url:
            body = {"status": "completed", "model": "offline-observed", "id": "response",
                    "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}]}
        elif "anthropic.com" in request.full_url:
            body = {"model": "offline-observed", "id": "response", "stop_reason": "end_turn",
                    "content": [{"type": "text", "text": text}]}
        else:
            body = {"modelVersion": "offline-observed", "responseId": "response",
                    "candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": text}]}}]}
        return Response(body)

    def test_out_of_order_proposals_overlap_and_all_judges_wait_for_freeze(self):
        second_finished = threading.Event()
        lock = threading.Lock()
        active = peak = 0
        per_provider, provider_peak = {}, {}
        completion = []
        owner = threading.get_ident()
        original_write = runner._write

        def write(path, value):
            self.assertEqual(threading.get_ident(), owner)
            original_write(path, value)

        def transport(request, timeout):
            nonlocal active, peak
            provider = request.full_url.split("/")[2]
            with lock:
                active += 1
                peak = max(peak, active)
                per_provider[provider] = per_provider.get(provider, 0) + 1
                provider_peak[provider] = max(provider_peak.get(provider, 0), per_provider[provider])
            try:
                wire = json.loads(request.data)
                prompt = wire.get("input", "")
                is_proposal = bool(prompt and "proposal" not in json.loads(prompt))
                if is_proposal and "Fixture 001." in prompt:
                    self.assertTrue(second_finished.wait(3), "second call must overlap first")
                result = self.transport(request, timeout)
                if is_proposal:
                    number = json.loads(prompt)["visible_snapshot"]["events"][0]["body"].split()[1]
                    completion.append(number)
                    if number == "002.":
                        second_finished.set()
                return result
            finally:
                with lock:
                    active -= 1
                    per_provider[provider] -= 1

        with patch("tools.dwelly_model.providers._open", transport), patch.object(runner, "_write", write):
            result = runner.run_experiment(self.bundle, self.output, config(), live=True, limit=3,
                                           compare_baseline=False, max_parallel_requests=3, per_provider_limit=2)
        self.assertEqual(result["proposal_count"], 3)
        self.assertEqual(result["judge_coverage"]["scored_count"], 9)
        self.assertEqual(completion[:2], ["002.", "001."])
        self.assertGreaterEqual(peak, 2)
        self.assertLessEqual(peak, 3)
        self.assertTrue(all(value <= 2 for value in provider_peak.values()))
        rows = [json.loads(line) for line in (self.output / "budget.jsonl").read_text().splitlines()]
        self.assertEqual([row["request_key"] for row in rows if row["event"] == "reserve"][:3],
                         [f"delivery-logistics-{n}-proposer" for n in ("001", "002", "003")])
        for number in ("001", "002", "003"):
            proposal = json.loads((self.output / f"proposals/delivery-logistics-{number}.json").read_text())
            self.assertTrue(proposal["action"]["message"].endswith(number))

    def test_proposals_only_never_needs_evaluation_even_offline(self):
        shutil.rmtree(self.bundle / "evaluation")
        for live in (False, True):
            with self.subTest(live=live), patch("tools.dwelly_model.providers._open", self.transport):
                result = runner.run_experiment(self.bundle, self.root / str(live), config(), limit=1,
                                               live=live, proposals_only=True)
                self.assertEqual(result["proposal_count"], 1)
                self.assertEqual(result["judge_coverage"]["expected_count"], 0)
                self.assertEqual(result["live_calls"], int(live))

    def test_cancellation_drains_inflight_and_admits_no_next_call(self):
        started, release, cancelled = threading.Event(), threading.Event(), threading.Event()

        def transport(request, timeout):
            started.set()
            self.assertTrue(release.wait(3))
            return self.transport(request, timeout)

        with patch("tools.dwelly_model.providers._open", transport), ThreadPoolExecutor(1) as caller:
            future = caller.submit(runner.run_experiment, self.bundle, self.output, config(), live=True,
                                   limit=3, proposals_only=True, cancel_requested=cancelled.is_set)
            try:
                self.assertTrue(started.wait(3))
                cancelled.set()
                self.assertFalse(future.done())
            finally:
                release.set()
            result = future.result(timeout=5)
        self.assertEqual(result["status"], "cancelled")
        self.assertEqual(result["live_calls"], 1)
        self.assertEqual(result["proposal_count"], 1)
        self.assertEqual(result["budget"]["reservation_count"], 1)
        self.assertEqual(len(list((self.output / "receipts").glob("*.json"))), 1)

    def test_shared_ledger_prevents_fresh_output_from_resetting_near_cap(self):
        settings = config()
        settings.update(budget_per_model_usd=0.2, max_output_tokens=65536)
        shared = self.root / "shared/budget.jsonl"
        with patch("tools.dwelly_model.providers._open", self.transport):
            first = runner.run_experiment(self.bundle, self.output, settings, live=True, limit=1,
                                          proposals_only=True, shared_budget_path=shared)
            second = runner.run_experiment(self.bundle, self.root / "second", settings, live=True, limit=1,
                                           proposals_only=True, shared_budget_path=shared)
        self.assertEqual(first["proposal_count"], 1)
        self.assertEqual(second["proposal_count"], 0)
        self.assertEqual(second["live_calls"], 0)
        self.assertEqual(second["execution_errors"]["delivery-logistics-001-proposer"], "budget_exhausted")
        rows = [json.loads(line) for line in shared.read_text().splitlines()]
        self.assertEqual(sum(row["event"] == "reserve" for row in rows), 1)
        self.assertNotEqual(next(row["request_key"] for row in rows if row["event"] == "reserve"),
                            "delivery-logistics-001-proposer")

    def test_shared_keys_distinguish_two_successful_outputs(self):
        shared = self.root / "shared/budget.jsonl"
        with patch("tools.dwelly_model.providers._open", self.transport):
            for output in (self.output, self.root / "second"):
                result = runner.run_experiment(self.bundle, output, config(), live=True, limit=1,
                                               proposals_only=True, shared_budget_path=shared)
                self.assertEqual(result["proposal_count"], 1)
        rows = [json.loads(line) for line in shared.read_text().splitlines()]
        keys = [row["request_key"] for row in rows if row["event"] == "reserve"]
        self.assertEqual(len(set(keys)), 2)
        self.assertEqual({row["request_key"] for row in rows if row["event"] == "outcome"}, set(keys))

    def test_invalid_parallel_options_are_rejected_before_output(self):
        for field, values in (("max_parallel_requests", (True, 0, 17)),
                              ("per_provider_limit", (False, 0, 9))):
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    runner.run_experiment(self.bundle, self.output, config(), **{field: value})
                self.assertFalse(self.output.exists())

    def test_parallel_provider_failure_retains_reservation(self):
        with patch("tools.dwelly_model.providers._open", side_effect=TimeoutError()):
            result = runner.run_experiment(self.bundle, self.output, config(), live=True, limit=3,
                                           proposals_only=True, max_parallel_requests=3, per_provider_limit=2)
        self.assertEqual(result["proposal_count"], 0)
        self.assertEqual(result["live_calls"], 3)
        self.assertEqual(result["budget"]["reservation_count"], 3)
        self.assertGreater(result["budget"]["reserved_usd"], 0)

    def test_shared_ledger_rejects_changed_cap_without_dispatch(self):
        shared = self.root / "shared/budget.jsonl"
        with patch("tools.dwelly_model.providers._open", self.transport):
            runner.run_experiment(self.bundle, self.output, config(), live=True, limit=1,
                                  proposals_only=True, shared_budget_path=shared)
        settings = config()
        settings["budget_per_model_usd"] = 24
        with patch("tools.dwelly_model.providers._open") as transport, self.assertRaisesRegex(ValueError, "budget_cap_changed"):
            runner.run_experiment(self.bundle, self.root / "second", settings, live=True, limit=1,
                                  proposals_only=True, shared_budget_path=shared)
        transport.assert_not_called()

    def test_live_cloud_guard_runs_before_output_but_not_read_only_preflight(self):
        for marker in ("K_SERVICE", "CLOUD_RUN_JOB"):
            with self.subTest(marker=marker), patch.dict(os.environ, {marker: "offline-test"}):
                self.assertTrue(runner.preflight(config())["ready"])
                with patch("tools.dwelly_model.providers._open") as transport, self.assertRaisesRegex(ValueError, "live_cloud_unavailable"):
                    runner.run_experiment(self.bundle, self.output, config(), live=True, limit=1)
                transport.assert_not_called()
                self.assertFalse(self.output.exists())

    def test_cli_parallel_proposals_only_works_without_evaluation(self):
        shutil.rmtree(self.bundle / "evaluation")
        config_path = self.root / "config.json"
        config_path.write_text(json.dumps(config()))
        stdout = StringIO()
        with redirect_stdout(stdout), patch("tools.dwelly_model.providers._open") as transport:
            status = main(["dry-run", "--config", str(config_path), "--bundle", str(self.bundle),
                           "--output", str(self.output), "--limit", "1", "--proposals-only",
                           "--max-parallel-requests", "4", "--per-provider-limit", "2"])
        self.assertEqual(status, 0)
        result = json.loads(stdout.getvalue())
        self.assertEqual(result["max_parallel_requests"], 4)
        self.assertEqual(result["per_provider_limit"], 2)
        self.assertEqual(result["judge_coverage"]["expected_count"], 0)
        transport.assert_not_called()

    def test_cli_invalid_parallel_limit_is_sanitized_before_output(self):
        config_path = self.root / "config.json"
        config_path.write_text(json.dumps(config()))
        stderr = StringIO()
        with redirect_stderr(stderr):
            status = main(["dry-run", "--config", str(config_path), "--bundle", str(self.bundle),
                           "--output", str(self.output), "--max-parallel-requests", "0"])
        self.assertEqual(status, 2)
        self.assertEqual(json.loads(stderr.getvalue())["error"], "invalid_input_or_run_failed")
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
