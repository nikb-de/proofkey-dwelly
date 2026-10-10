"""Real local HTTP and SQLite contracts; no provider network is used."""
import http.client
import importlib
import json
from pathlib import Path
import sqlite3
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from tools.dwelly_cases.importer import import_cases
from tools.dwelly_cases.tests.fixtures import make_source
from tools.dwelly_model.tests.test_runner import config

try:
    store_module = importlib.import_module("tools.dwelly_service.store")
    server_module = importlib.import_module("tools.dwelly_service.server")
except ModuleNotFoundError:
    store_module = server_module = None


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(store_module, "persistent local service must be implemented")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.state = self.root / "state"
        self.store = store_module.JobStore(self.state)
        self.addCleanup(lambda: self.store.close())

    def test_submission_commits_and_idempotency_survives_reopen(self):
        first, created = self.store.submit("one", {"mode": "dry_run"})
        self.assertTrue(created)
        self.store.close()
        self.store = store_module.JobStore(self.state)
        again, created = self.store.submit("one", {"mode": "dry_run"})
        self.assertFalse(created)
        self.assertEqual(again["job_id"], first["job_id"])
        with self.assertRaisesRegex(ValueError, "idempotency_conflict"):
            self.store.submit("one", {"mode": "live"})

    def test_only_one_owner_can_open_the_queue(self):
        with self.assertRaisesRegex(ValueError, "state_locked"):
            store_module.JobStore(self.state)

    def test_queued_cancellation_is_durable_and_not_claimed(self):
        job, _ = self.store.submit("cancel", {"mode": "dry_run"})
        cancelled = self.store.cancel(job["job_id"])
        self.assertEqual(cancelled["status"], "cancelled")
        self.store.close()
        self.store = store_module.JobStore(self.state)
        self.assertIsNone(self.store.claim_next())
        self.assertEqual(self.store.get(job["job_id"])["status"], "cancelled")

    def test_restart_interrupts_running_job_and_preserves_queued_job(self):
        running, _ = self.store.submit("running", {"mode": "dry_run"})
        self.assertEqual(self.store.claim_next()["job_id"], running["job_id"])
        queued, _ = self.store.submit("queued", {"mode": "dry_run"})
        self.store.close()
        self.store = store_module.JobStore(self.state)
        self.assertEqual(self.store.get(running["job_id"])["status"], "interrupted")
        self.assertEqual(self.store.claim_next()["job_id"], queued["job_id"])

    def test_restart_accepts_valid_terminal_summary_but_not_symlinks(self):
        job, _ = self.store.submit("finished", {"mode": "dry_run"})
        self.store.claim_next()
        output = self.state / "jobs" / job["job_id"]
        output.mkdir()
        summary = {"schema_version": "dwelly-model-experiment-v1", "status": "completed",
                   "mode": "offline_dry_run", "live_calls": 0, "operational_effects": 0}
        (output / "summary.json").write_text(json.dumps(summary))
        self.store.close()
        self.store = store_module.JobStore(self.state)
        self.assertEqual(self.store.get(job["job_id"])["status"], "completed")
        self.assertEqual(self.store.summary(job["job_id"])["live_calls"], 0)
        (output / "summary.json").unlink()
        private = self.root / "private.json"
        private.write_text(json.dumps(summary))
        (output / "summary.json").symlink_to(private)
        with self.assertRaisesRegex(ValueError, "summary_unavailable"):
            self.store.summary(job["job_id"])

    def test_changed_inputs_and_symlinked_state_are_rejected(self):
        self.store.bind_inputs("first")
        with self.assertRaisesRegex(ValueError, "input_identity_changed"):
            self.store.bind_inputs("second")
        link = self.root / "state-link"
        link.symlink_to(self.state, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "unsafe_path"):
            store_module.JobStore(link)

    def test_progress_counts_only_complete_regular_json_artifacts(self):
        job, _ = self.store.submit("progress", {"mode": "dry_run"})
        folder = self.state / "jobs" / job["job_id"] / "proposals"
        folder.mkdir(parents=True)
        (folder / "complete.json").write_text('{"status":"proposed_unsent"}')
        (folder / "partial.json").write_text('{"status":')
        (folder / "link.json").symlink_to(folder / "complete.json")
        self.assertEqual(self.store.progress(job["job_id"])["proposals"], 1)

    def test_recovery_rejects_terminal_evidence_with_business_effects(self):
        job, _ = self.store.submit("invalid-summary", {"mode": "dry_run"})
        self.store.claim_next()
        output = self.store.output_path(job["job_id"])
        output.mkdir()
        (output / "summary.json").write_text(json.dumps({
            "schema_version": "dwelly-model-experiment-v1", "status": "completed",
            "mode": "offline_dry_run", "live_calls": 0, "operational_effects": 1}))
        self.store.close()
        self.store = store_module.JobStore(self.state)
        self.assertEqual(self.store.get(job["job_id"])["status"], "interrupted")

    def test_pending_queue_is_bounded_but_existing_idempotent_request_still_returns(self):
        first, _ = self.store.submit("job-0", {"mode": "dry_run"})
        for index in range(1, 256):
            self.store.submit("job-" + str(index), {"mode": "dry_run"})
        with self.assertRaisesRegex(ValueError, "queue_full"):
            self.store.submit("overflow", {"mode": "dry_run"})
        self.assertEqual(self.store.submit("job-0", {"mode": "dry_run"})[0]["job_id"], first["job_id"])


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(server_module, "authenticated HTTP service must be implemented")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        source = self.root / "source"
        make_source(source)
        self.bundle = self.root / "bundle"
        import_cases(source, self.bundle, expected_cases=1)
        self.config = self.root / "config.json"
        self.config.write_text(json.dumps(config()))
        self.state = self.root / "state"
        self.token = "local-test-token-with-enough-entropy"
        self.server = server_module.create_server(self.bundle, self.config, self.state,
                                                  token=self.token, port=0, start_worker=False)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.cleanup_server)

    def cleanup_server(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.thread.join(2)
            self.server = None

    def request(self, method, target, body=None, headers=None, auth=True):
        payload = json.dumps(body) if isinstance(body, dict) else body
        actual = {"Content-Type": "application/json"}
        if auth:
            actual["Authorization"] = "Bearer " + self.token
        actual.update(headers or {})
        client = http.client.HTTPConnection(*self.server.server_address, timeout=5)
        try:
            client.request(method, target, payload, actual)
            response = client.getresponse()
            raw = response.read()
            return response.status, json.loads(raw)
        finally:
            client.close()

    def submit(self, key="one", body=None):
        return self.request("POST", "/v1/jobs", body or {}, {"Idempotency-Key": key})

    def test_health_is_content_free_and_other_routes_require_authentication(self):
        status, result = self.request("GET", "/healthz", auth=False)
        self.assertEqual((status, result), (200, {"status": "ok"}))
        status, result = self.request("GET", "/v1/capabilities", auth=False)
        self.assertEqual(status, 401)
        self.assertNotIn(self.token, json.dumps(result))
        status, result = self.request("GET", "/v1/capabilities")
        self.assertEqual(status, 200)
        self.assertFalse(result["live_enabled"])
        self.assertEqual(result["operational_effects"], 0)
        self.assertNotIn(str(self.root), json.dumps(result))

    def test_origin_and_untrusted_host_are_rejected(self):
        self.assertEqual(self.request("GET", "/healthz", headers={"Origin": "https://evil.example"})[0], 403)
        self.assertEqual(self.request("GET", "/healthz", headers={"Host": "evil.example"})[0], 403)

    def test_invalid_inputs_are_rejected_before_enqueue(self):
        for body in ({"bundle": "/private/secret"}, {"limit": True}, {"limit": 51},
                     {"evaluate": "yes"}, {"max_parallel_requests": 0},
                     {"per_provider_limit": 9}, {"mode": "live"}, {"mode": "unknown"}):
            with self.subTest(body=body):
                status, result = self.submit(str(body), body)
                self.assertIn(status, (400, 403))
                self.assertNotIn("secret", json.dumps(result))
        for raw in ('{"limit":1,"limit":2}', '{"limit":NaN}', '{', '[]'):
            self.assertEqual(self.request("POST", "/v1/jobs", raw, {"Idempotency-Key": "bad"})[0], 400)
        self.assertIsNone(self.server.store.claim_next())

    def test_oversized_body_wrong_type_and_missing_key_are_rejected(self):
        self.assertEqual(self.request("POST", "/v1/jobs", "x" * 16385, {"Idempotency-Key": "big"})[0], 413)
        self.assertEqual(self.request("POST", "/v1/jobs", "{}", {"Content-Type": "text/plain", "Idempotency-Key": "type"})[0], 415)
        self.assertEqual(self.request("POST", "/v1/jobs", {})[0], 400)

    def test_default_normalization_idempotency_and_queued_cancel(self):
        status, first = self.submit()
        self.assertEqual(status, 202)
        status, again = self.submit(body={"mode": "dry_run", "limit": 1, "evaluate": False,
                                            "max_parallel_requests": 4, "per_provider_limit": 2})
        self.assertEqual(status, 200)
        self.assertEqual(first["job_id"], again["job_id"])
        self.assertEqual(self.submit(body={"limit": 2})[0], 409)
        job_id = first["job_id"]
        self.assertEqual(self.request("GET", f"/v1/jobs/{job_id}/summary")[0], 409)
        status, cancelled = self.request("POST", f"/v1/jobs/{job_id}/cancel", {})
        self.assertEqual((status, cancelled["status"]), (200, "cancelled"))
        self.assertIsNone(self.server.store.claim_next())
        self.assertEqual(self.request("GET", "/v1/jobs/../../config.json")[0], 404)

    def test_real_offline_job_completes_over_http_without_evaluation_or_network(self):
        self.server.start_worker()
        with patch("tools.dwelly_model.providers._open", side_effect=AssertionError("network forbidden")):
            status, result = self.submit("offline")
            self.assertEqual(status, 202)
            job_id = result["job_id"]
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                status, job = self.request("GET", f"/v1/jobs/{job_id}")
                if job["status"] not in ("queued", "running"):
                    break
                time.sleep(0.01)
        self.assertEqual(job["status"], "completed", job)
        status, summary = self.request("GET", f"/v1/jobs/{job_id}/summary")
        self.assertEqual(status, 200)
        self.assertEqual((summary["live_calls"], summary["operational_effects"]), (0, 0))
        self.assertEqual(job["progress"]["proposals"], 1)
        self.assertEqual(job["progress"]["judgments"], 0)
        self.assertNotIn("response", job)
        self.assertNotIn(str(self.root), json.dumps(job))
        status, proposals = self.request("GET", f"/v1/jobs/{job_id}/proposals")
        self.assertEqual(status, 200)
        self.assertEqual(proposals["proposals"][0]["case_id"], "delivery-logistics-001")
        self.assertEqual(proposals["proposals"][0]["action"]["kind"], "request_customer_choice")
        self.assertEqual(proposals["proposals"][0]["effects"], [])
        self.assertNotIn("response", json.dumps(proposals))

    def test_proposal_readback_omits_incomplete_unsafe_and_misidentified_files(self):
        _, result = self.submit("readback")
        job_id = result["job_id"]
        folder = self.state / "jobs" / job_id / "proposals"
        folder.mkdir(parents=True)
        (folder / "delivery-logistics-001.json").write_text('{"status":')
        (folder / "secrets.json").write_text('{"secret":"not-a-case"}')
        (folder / "delivery-logistics-002.json").symlink_to(self.config)
        status, result = self.request("GET", f"/v1/jobs/{job_id}/proposals")
        self.assertEqual(status, 200)
        self.assertEqual(result["proposals"], [])
        self.assertNotIn("secret", json.dumps(result))

    def test_managed_cloud_overlap_and_unsafe_config_are_refused(self):
        for marker in ("K_SERVICE", "CLOUD_RUN_JOB"):
            with patch.dict("os.environ", {marker: "test"}):
                with self.assertRaisesRegex(ValueError, "managed_cloud_unsupported"):
                    server_module.create_server(self.bundle, self.config, self.root / marker,
                                                token=self.token, port=0)
        with self.assertRaisesRegex(ValueError, "path_overlap"):
            server_module.create_server(self.bundle, self.config, self.bundle / "state", token=self.token, port=0)
        link = self.root / "linked-config.json"
        link.symlink_to(self.config)
        with self.assertRaisesRegex(ValueError, "unsafe_path"):
            server_module.create_server(self.bundle, link, self.root / "other-state", token=self.token, port=0)

    def test_sqlite_failures_return_content_free_service_unavailable(self):
        (self.state / "queue.sqlite3").write_bytes(b"damaged sqlite database")
        for method, path, body in (("GET", "/healthz", None), ("POST", "/v1/jobs", {})):
            with self.subTest(method=method):
                status, result = self.request(method, path, body, {"Idempotency-Key": "corrupt"})
                self.assertEqual(status, 503)
                self.assertNotIn("sqlite", json.dumps(result))
                self.assertNotIn(str(self.state), json.dumps(result))

    def test_worker_claim_failure_is_observable_and_new_submissions_are_rejected(self):
        with patch.object(self.server.store, "claim_next", side_effect=sqlite3.OperationalError("private details")):
            self.server.start_worker()
            self.server.worker.thread.join(2)
        self.assertFalse(self.server.worker.thread.is_alive())
        status, result = self.request("GET", "/healthz", auth=False)
        self.assertEqual(status, 503)
        self.assertNotIn("private details", json.dumps(result))
        self.assertEqual(self.submit("unhealthy")[0], 503)

    def test_active_cancellation_drains_reply_and_retains_shared_budget_across_jobs(self):
        self.cleanup_server()
        self.server = server_module.create_server(self.bundle, self.config, self.state,
                                                  token=self.token, port=0, allow_live=True)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        entered, release = threading.Event(), threading.Event()
        candidate = {"action": {"kind": "request_customer_choice", "recipient": "Ari, recipient",
                                "channel": "Customer portal", "message": "Do you prefer 15:00 or 17:00?"},
                     "evidence_refs": ["event-001", "event-002"], "rationale": "A slot choice is missing.",
                     "missing_information": ["Preferred slot"], "required_approvals": []}

        class Response:
            status = 200
            headers = {}

            def __enter__(self):
                entered.set()
                if not release.wait(5):
                    raise TimeoutError()
                return self

            def __exit__(self, *_args):
                pass

            def read(self, _size):
                return json.dumps({"status": "completed", "model": "synthetic-observed", "id": "synthetic-response",
                                   "output": [{"type": "message", "status": "completed", "content": [
                                       {"type": "output_text", "text": json.dumps(candidate)}]}],
                                   "usage": {"input_tokens": 20, "output_tokens": 30}}).encode()

        with patch.dict(os.environ, {"OPENAI_TEST_KEY": "synthetic-test-secret"}), \
                patch("tools.dwelly_model.providers._open", return_value=Response()):
            try:
                _, submitted = self.submit("active", {"mode": "live", "max_parallel_requests": 1})
                job_id = submitted["job_id"]
                self.assertTrue(entered.wait(3))
                _, cancelled = self.request("POST", f"/v1/jobs/{job_id}/cancel", {})
                self.assertTrue(cancelled["cancel_requested"])
            finally:
                release.set()
            for _ in range(500):
                _, job = self.request("GET", f"/v1/jobs/{job_id}")
                if job["status"] not in ("queued", "running"):
                    break
                time.sleep(0.01)
            self.assertEqual(job["status"], "cancelled", job)
            _, summary = self.request("GET", f"/v1/jobs/{job_id}/summary")
            self.assertEqual(summary["live_calls"], 1)
            self.assertGreater(summary["shared_budget"]["reserved_usd"], 0)
            _, proposals = self.request("GET", f"/v1/jobs/{job_id}/proposals")
            self.assertEqual(proposals["proposals"][0]["status"], "proposed_unsent")
            self.assertNotIn("synthetic-test-secret", json.dumps(proposals))
            _, second = self.submit("next-live", {"mode": "live", "max_parallel_requests": 1})
            for _ in range(500):
                _, job = self.request("GET", "/v1/jobs/" + second["job_id"])
                if job["status"] not in ("queued", "running"):
                    break
                time.sleep(0.01)
            self.assertEqual(job["status"], "completed", job)
            _, summary = self.request("GET", "/v1/jobs/" + second["job_id"] + "/summary")
            self.assertEqual(summary["shared_budget"]["reservation_count"], 2)

    def test_cli_refuses_managed_cloud_without_printing_token_or_creating_state(self):
        state = self.root / "cloud-state"
        environment = {**os.environ, "K_SERVICE": "test", "PROOFKEY_SERVICE_TOKEN": self.token}
        result = subprocess.run([sys.executable, "-B", "-m", "tools.dwelly_service", "--bundle", str(self.bundle),
                                 "--config", str(self.config), "--state-dir", str(state)],
                                capture_output=True, text=True, env=environment, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(state.exists())
        self.assertNotIn(self.token, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stderr), {"error": "service_start_failed"})

    def test_cli_corrupt_state_failure_is_sanitized(self):
        self.cleanup_server()
        (self.state / "queue.sqlite3").write_bytes(b"damaged database")
        environment = {key: value for key, value in os.environ.items() if key not in ("K_SERVICE", "CLOUD_RUN_JOB")}
        environment["PROOFKEY_SERVICE_TOKEN"] = self.token
        result = subprocess.run([sys.executable, "-B", "-m", "tools.dwelly_service", "--bundle", str(self.bundle),
                                 "--config", str(self.config), "--state-dir", str(self.state)],
                                capture_output=True, text=True, env=environment, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stderr.strip(), '{"error": "service_start_failed"}')


if __name__ == "__main__":
    unittest.main()
