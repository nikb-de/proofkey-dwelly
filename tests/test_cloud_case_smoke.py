"""Offline transport tests for the explicitly targeted cloud smoke CLI."""
from email.message import Message
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError
from urllib.request import HTTPSHandler, build_opener
from urllib.response import addinfourl


SCRIPT = Path(__file__).resolve().parents[1] / "deploy/cloud-run/smoke_case.py"
URL = "https://proofkey-case-123456.europe-west2.run.app"
CASE_ID = "smoke-contract"
APP_TOKEN = "synthetic-application-secret-32chars"
ID_TOKEN = "syntheticheader.syntheticpayload.syntheticsignature"


class Response(io.BytesIO):
    def __init__(self, status, body):
        super().__init__(json.dumps(body).encode())
        self.status = status


class SyntheticTransport:
    """Transport fixture: no sockets, gcloud, model calls, or external effects."""
    def __init__(self, existing=False):
        self.requests = []
        self.created = self.appended = existing
        self.zero = {"case_id": CASE_ID, "revision": 0, "events": [], "snapshot_hash": "a" * 64,
                     "previous_snapshot_hash": None, "analysis_status": "pending_not_started",
                     "runtime_binding": None, "authorization": "unverified", "operational_effects": 0}
        self.one = {**self.zero, "revision": 1, "events": [{"event_id": "smoke-event"}],
                    "snapshot_hash": "b" * 64, "previous_snapshot_hash": "a" * 64}
        self.outbox = {"case_id": CASE_ID, "operational_effects": 0, "jobs": [
            {"revision": 0, "status": "pending", "snapshot_hash": "a" * 64},
            {"revision": 1, "status": "pending", "snapshot_hash": "b" * 64}]}
        self.capabilities = {"storage": "postgresql", "operational_effects": 0,
            "max_cases": 100, "max_events_per_case": 1000, "media_upload": False, "analysis_outbox": True,
            "deployment_profile": "cloud-run-case-v1", "managed_cloud_enabled": True,
            "case_intake": {"enabled": True, "source_mode": "local_fixture", "analysis_status": "pending_not_started",
                            "automated_analysis": False, "runtime_binding": None, "authorization": "unverified",
                            "operational_effects": 0}}

    def open(self, request, timeout):
        self.requests.append(request)
        headers = {name.lower(): value for name, value in request.header_items()}
        path = request.full_url.removeprefix(URL)
        if "x-serverless-authorization" not in headers:
            return Response(403, {"error": "gateway_denied"})
        if path == "/healthz":
            response = io.BytesIO(b"<!doctype html><title>404 Not Found</title>")
            response.status = 404
            return response
        if path == "/readyz":
            return Response(200, {"status": "ready"})
        if headers.get("authorization") != "Bearer " + APP_TOKEN:
            return Response(401, {"error": "unauthorized"})
        if "origin" in headers:
            return Response(403, {"error": "forbidden"})
        if path == "/v1/capabilities":
            return Response(200, self.capabilities)
        if request.method == "POST" and path == "/v1/cases":
            status = 200 if self.created else 201
            self.created = True
            return Response(status, self.zero)
        if request.method == "POST" and path == "/v1/cases/" + CASE_ID + "/events":
            status = 200 if self.appended else 201
            self.appended = True
            self.one["events"] = [json.loads(request.data)["event"]]
            return Response(status, self.one)
        if path == "/v1/cases/" + CASE_ID + "?revision=0":
            return Response(200, self.zero)
        if path == "/v1/cases/" + CASE_ID:
            return Response(200, self.one)
        if path == "/v1/cases/" + CASE_ID + "/analysis-jobs":
            return Response(200, self.outbox)
        raise AssertionError("smoke requested an unapproved path")


class CloudSmokeTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.is_file(), "cloud-specific smoke CLI must be implemented")
        spec = importlib.util.spec_from_file_location("cloud_case_smoke", SCRIPT)
        self.smoke = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.smoke)
        self.token_process = patch.object(self.smoke.subprocess, "run", return_value=
            subprocess.CompletedProcess(["gcloud"], 0, stdout=ID_TOKEN + "\n", stderr=""))
        self.gcloud = self.token_process.start()
        self.addCleanup(self.token_process.stop)

    def client(self, url=URL, token=APP_TOKEN, case_id=CASE_ID):
        return self.smoke._Client(url, token, case_id)

    def test_accepts_only_explicit_supported_https_origins(self):
        for url in (URL, URL + "/", "https://proofkey-case-abcdef.a.run.app"):
            with self.subTest(url=url):
                self.assertEqual(self.client(url).base_url, url.rstrip("/"))

    def test_invalid_targets_fail_before_gcloud_or_transport(self):
        for url in ("", "http://proofkey-case.a.run.app", "https://run.app", "https://a.run.app",
                    "https://evil.example", URL + ".evil.example", URL + ":443", URL + "/path",
                    URL + "?x=1", URL + "#fragment", "https://user:private@proofkey.a.run.app",
                    " https://proofkey.a.run.app", URL + "\n", "https://bad..a.run.app",
                    "https://-bad.a.run.app", "https://bad_.a.run.app", "https://*.a.run.app",
                    "https://proofkey-case.us-central1.run.app", "https://127.0.0.1"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                self.client(url)
        self.gcloud.assert_not_called()

    def test_synthetic_case_id_is_explicit_ascii_and_bounded(self):
        for case_id in ("", "case-1", "smoke-", "smoke-../bad", "smoke-with_space", "smoke-é", "smoke-" + "a" * 43):
            with self.subTest(case_id=case_id), self.assertRaises(ValueError):
                self.client(case_id=case_id)
        self.gcloud.assert_not_called()

    def test_bad_application_token_fails_before_identity_token_request(self):
        for token in ("", "x" * 31, "x" * 4097, "x" * 32 + "\n", "x" * 32 + "é"):
            with self.subTest(length=len(token)), self.assertRaises(ValueError):
                self.client(token=token)
        self.gcloud.assert_not_called()

    def test_fetches_identity_token_privately_and_keeps_header_layers_separate(self):
        client = self.client()
        transport = SyntheticTransport()
        client.opener = transport
        client.request("GET", "/v1/cases/" + CASE_ID)
        self.gcloud.assert_called_once_with(["gcloud", "auth", "print-identity-token"],
                                           check=True, capture_output=True, text=True, timeout=30)
        headers = {name.lower(): value for name, value in transport.requests[0].header_items()}
        self.assertEqual(headers["authorization"], "Bearer " + APP_TOKEN)
        self.assertEqual(headers["x-serverless-authorization"], "Bearer " + ID_TOKEN)

    def test_invalid_gcloud_output_never_reaches_http(self):
        for output in ("", "\n", ID_TOKEN + "\nprivate", "private token", "one.two", "one.two.three\rInjected:value"):
            self.gcloud.return_value.stdout = output
            with self.subTest(output_length=len(output)), patch.object(self.smoke, "build_opener") as opener, \
                    self.assertRaises(ValueError):
                self.client()
            opener.assert_not_called()

    def test_only_fixed_case_routes_and_capabilities_can_be_requested(self):
        client = self.client()
        client.opener = Mock()
        for method, path in (("GET", "/v1/unknown"), ("POST", "/v1/jobs"),
                             ("GET", "/v1/cases/other"), ("GET", "/v1/cases/" + CASE_ID + "?revision=1"),
                             ("GET", "https://evil.example/"), ("GET", "/healthz"), ("GET", "/readyz"),
                             ("POST", "/v1/capabilities"),
                             ("DELETE", "/v1/cases/" + CASE_ID)):
            with self.subTest(method=method, path=path), self.assertRaises(ValueError):
                client.request(method, path)
        client.opener.open.assert_not_called()

    def test_redirect_is_rejected_without_following_or_sending_tokens_to_target(self):
        visited = []

        class RedirectTransport(HTTPSHandler):
            def https_open(self, request):
                visited.append(request.full_url)
                headers = Message()
                headers["Location"] = "https://attacker.invalid/steal"
                response = addinfourl(io.BytesIO(b"redirect"), headers, request.full_url, 302)
                response.msg = "Found"
                return response

        with patch.object(self.smoke, "build_opener", side_effect=lambda *handlers: build_opener(*handlers, RedirectTransport())):
            client = self.client()
            with self.assertRaises(ValueError):
                client.request("GET", "/v1/capabilities")
        self.assertEqual(visited, [URL + "/v1/capabilities"])

    def test_http_auth_denial_can_be_html_without_leaking_body(self):
        client = self.client()
        error = HTTPError(URL, 403, "private " + APP_TOKEN, {}, io.BytesIO(b"private gateway response"))
        client.opener = Mock()
        client.opener.open.side_effect = error
        self.assertEqual(client.request("GET", "/v1/cases/" + CASE_ID, iam_auth=False), (403, None))

    def test_complete_smoke_checks_synthetic_history_outbox_and_negative_guards(self):
        transport = SyntheticTransport()
        with patch.object(self.smoke, "build_opener", return_value=transport):
            result = self.smoke.run(URL, APP_TOKEN, CASE_ID)
        self.assertEqual(result, {"status": "passed", "case_id": CASE_ID, "checks": 20,
                                  "existing_after_restart": False, "operational_effects": 0})
        paths = {request.full_url.removeprefix(URL) for request in transport.requests}
        self.assertEqual(paths, {"/v1/capabilities", "/v1/cases", "/v1/cases/" + CASE_ID,
                               "/v1/cases/" + CASE_ID + "/events", "/v1/cases/" + CASE_ID + "?revision=0",
                               "/v1/cases/" + CASE_ID + "/analysis-jobs"})
        requests = [{name.lower(): value for name, value in request.header_items()} for request in transport.requests]
        self.assertEqual(transport.requests[0].full_url, URL + "/v1/capabilities")
        self.assertEqual(requests[0]["authorization"], "Bearer " + APP_TOKEN)
        self.assertEqual(requests[0]["x-serverless-authorization"], "Bearer " + ID_TOKEN)
        self.assertTrue(any("x-serverless-authorization" not in headers for headers in requests))
        self.assertTrue(any("authorization" not in headers for headers in requests))
        self.assertTrue(any(headers.get("authorization") == "Bearer invalid-synthetic-smoke-token" for headers in requests))
        self.assertTrue(any("origin" in headers for headers in requests))
        bodies = [json.loads(request.data) for request in transport.requests if request.data]
        self.assertTrue(all(body.get("case_id", CASE_ID) == CASE_ID for body in bodies))
        self.assertTrue(all("smoke" in body.get("case_id", body["event"]["event_id"] if "event" in body else "")
                            for body in bodies))

    def test_wrong_deployment_or_active_analysis_capabilities_fail_smoke(self):
        for path, value in (("storage", "sqlite"), ("deployment_profile", "local"), ("managed_cloud_enabled", False),
                            ("operational_effects", 1), ("case_intake.enabled", False),
                            ("case_intake.analysis_status", "completed"), ("case_intake.automated_analysis", True),
                            ("case_intake.operational_effects", 1)):
            transport = SyntheticTransport()
            target = transport.capabilities
            names = path.split(".")
            for name in names[:-1]:
                target = target[name]
            target[names[-1]] = value
            with self.subTest(path=path), patch.object(self.smoke, "build_opener", return_value=transport), \
                    self.assertRaises(AssertionError):
                self.smoke.run(URL, APP_TOKEN, CASE_ID)

    def test_existing_case_is_required_when_rechecking_after_restart(self):
        with patch.object(self.smoke, "build_opener", return_value=SyntheticTransport(existing=True)):
            self.assertTrue(self.smoke.run(URL, APP_TOKEN, CASE_ID, expect_existing=True)["existing_after_restart"])
        with patch.object(self.smoke, "build_opener", return_value=SyntheticTransport(existing=False)):
            with self.assertRaises(AssertionError):
                self.smoke.run(URL, APP_TOKEN, CASE_ID, expect_existing=True)

    def test_snapshot_operational_claim_fails_smoke(self):
        for field, value in (("analysis_status", "completed"), ("operational_effects", 1), ("runtime_binding", "bound")):
            transport = SyntheticTransport()
            transport.one[field] = value
            with self.subTest(field=field), patch.object(self.smoke, "build_opener", return_value=transport), \
                    self.assertRaises(AssertionError):
                self.smoke.run(URL, APP_TOKEN, CASE_ID)

    def test_corrupted_outbox_fails_smoke(self):
        for defect in ("wrong_count", "processed", "wrong_hash", "operational_effects", "wrong_case"):
            transport = SyntheticTransport()
            if defect == "wrong_count":
                transport.outbox["jobs"].pop()
            elif defect == "processed":
                transport.outbox["jobs"][0]["status"] = "completed"
            elif defect == "wrong_hash":
                transport.outbox["jobs"][1]["snapshot_hash"] = "c" * 64
            elif defect == "operational_effects":
                transport.outbox["operational_effects"] = 1
            else:
                transport.outbox["case_id"] = "smoke-unrelated"
            with self.subTest(defect=defect), patch.object(self.smoke, "build_opener", return_value=transport), \
                    self.assertRaises(AssertionError):
                self.smoke.run(URL, APP_TOKEN, CASE_ID)

    def test_deeply_nested_response_uses_sanitized_failure_path(self):
        response = io.BytesIO(b"[" * 2000 + b"0" + b"]" * 2000)
        response.status = 200
        transport = Mock()
        transport.open.return_value = response
        out, err = io.StringIO(), io.StringIO()
        with patch.dict(os.environ, {"PROOFKEY_SERVICE_TOKEN": APP_TOKEN}), \
                patch.object(self.smoke, "build_opener", return_value=transport), \
                patch("sys.stdout", out), patch("sys.stderr", err):
            self.assertEqual(self.smoke.main(["--base-url", URL, "--case-id", CASE_ID]), 1)
        self.assertEqual(out.getvalue(), "")
        self.assertEqual(json.loads(err.getvalue()), {"status": "failed", "error": "cloud_smoke_failed"})

    def test_main_prints_only_sanitized_result_on_token_or_network_failure(self):
        for stage in ("identity_token", "http"):
            out, err = io.StringIO(), io.StringIO()
            transport = Mock()
            transport.open.side_effect = URLError(ID_TOKEN + APP_TOKEN)
            error = subprocess.CalledProcessError(1, ["gcloud"], output=ID_TOKEN, stderr=APP_TOKEN)
            with self.subTest(stage=stage), patch.dict(os.environ, {"PROOFKEY_SERVICE_TOKEN": APP_TOKEN}), \
                    patch.object(self.smoke, "build_opener", return_value=transport), \
                    patch.object(self.smoke.subprocess, "run", side_effect=error if stage == "identity_token" else None,
                                 return_value=subprocess.CompletedProcess(["gcloud"], 0, stdout=ID_TOKEN, stderr="")), \
                    patch("sys.stdout", out), patch("sys.stderr", err):
                self.assertEqual(self.smoke.main(["--base-url", URL, "--case-id", CASE_ID]), 1)
            self.assertEqual(out.getvalue(), "")
            self.assertEqual(json.loads(err.getvalue()), {"status": "failed", "error": "cloud_smoke_failed"})
            self.assertNotIn(APP_TOKEN, out.getvalue() + err.getvalue())
            self.assertNotIn(ID_TOKEN, out.getvalue() + err.getvalue())

    def test_main_success_output_does_not_contain_tokens(self):
        out, err = io.StringIO(), io.StringIO()
        with patch.dict(os.environ, {"PROOFKEY_SERVICE_TOKEN": APP_TOKEN}), \
                patch.object(self.smoke, "build_opener", return_value=SyntheticTransport()), \
                patch("sys.stdout", out), patch("sys.stderr", err):
            self.assertEqual(self.smoke.main(["--base-url", URL, "--case-id", CASE_ID]), 0)
        self.assertEqual(json.loads(out.getvalue())["status"], "passed")
        self.assertEqual(err.getvalue(), "")
        self.assertNotIn(APP_TOKEN, out.getvalue())
        self.assertNotIn(ID_TOKEN, out.getvalue())


if __name__ == "__main__":
    unittest.main()
