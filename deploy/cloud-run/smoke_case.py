#!/usr/bin/env python3
"""Explicit synthetic smoke for the private Cloud Run case API; never deletes cases."""
import argparse
import json
import os
import re
import subprocess
import sys
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener


_LABEL = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
_TARGET = re.compile(r"https://((?:" + _LABEL + r"\.)+(?:europe-west2|a)\.run\.app)/?")
_CASE_ID = re.compile(r"smoke-[A-Za-z0-9][A-Za-z0-9-]{0,41}")
_MAX_RESPONSE = 1024 * 1024


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        return None


class _Client:
    def __init__(self, base_url, token, case_id):
        target = _TARGET.fullmatch(base_url) if type(base_url) is str else None
        if target is None or len(target[1]) > 253:
            raise ValueError("invalid_cloud_smoke_target")
        if type(case_id) is not str or _CASE_ID.fullmatch(case_id) is None:
            raise ValueError("invalid_cloud_smoke_case_id")
        if type(token) is not str or not 32 <= len(token) <= 4096 or re.fullmatch(r"[!-~]+", token) is None:
            raise ValueError("invalid_cloud_smoke_token")
        self.base_url = base_url.rstrip("/")
        self.case_id, self.token = case_id, token
        case_path = "/v1/cases/" + case_id
        self.get_paths = {"/v1/capabilities", case_path, case_path + "?revision=0", case_path + "/analysis-jobs"}
        self.post_paths = {"/v1/cases", case_path + "/events"}
        result = subprocess.run(["gcloud", "auth", "print-identity-token"],
                                check=True, capture_output=True, text=True, timeout=30)
        identity_token = result.stdout.strip()
        if len(identity_token) > 16384 or re.fullmatch(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", identity_token) is None:
            raise ValueError("invalid_cloud_identity_token")
        self.identity_token = identity_token
        self.opener = build_opener(_NoRedirect())

    def request(self, method, path, body=None, key=None, *, app_auth=True, iam_auth=True, origin=None):
        if not ((method == "GET" and path in self.get_paths) or (method == "POST" and path in self.post_paths)):
            raise ValueError("invalid_cloud_smoke_path")
        headers = {"Content-Type": "application/json"}
        if iam_auth:
            headers["X-Serverless-Authorization"] = "Bearer " + self.identity_token
        if app_auth:
            headers["Authorization"] = "Bearer " + (self.token if app_auth is True else app_auth)
        if origin is not None:
            headers["Origin"] = origin
        if key is not None:
            headers["Idempotency-Key"] = key
        data = None if body is None else json.dumps(body, allow_nan=False).encode("utf-8")
        request = Request(self.base_url + path, data=data, headers=headers, method=method)
        try:
            response = self.opener.open(request, timeout=15)
        except HTTPError as error:
            response = error
        with response:
            status = response.code if isinstance(response, HTTPError) else response.status
            if 300 <= status < 400:
                raise ValueError("cloud_smoke_redirect_refused")
            raw = response.read(_MAX_RESPONSE + 1)
        if len(raw) > _MAX_RESPONSE:
            raise ValueError("cloud_smoke_response_too_large")
        try:
            value = json.loads(raw)
        except (ValueError, UnicodeError, RecursionError):
            if status < 400:
                raise ValueError("invalid_cloud_smoke_response") from None
            value = None
        return status, value


def run(base_url, token, case_id, expect_existing=False):
    client = _Client(base_url, token, case_id)
    checks = 0

    def check(condition):
        nonlocal checks
        if not condition:
            raise AssertionError("cloud_smoke_check_failed")
        checks += 1

    def pending(snapshot):
        return (snapshot["analysis_status"] == "pending_not_started" and snapshot["runtime_binding"] is None
                and snapshot["authorization"] == "unverified" and snapshot["operational_effects"] == 0)

    case_path = "/v1/cases/" + case_id
    status, capabilities = client.request("GET", "/v1/capabilities")
    check(status == 200 and capabilities["storage"] == "postgresql"
          and capabilities["deployment_profile"] == "cloud-run-case-v1"
          and capabilities["managed_cloud_enabled"] is True)
    intake = capabilities["case_intake"]
    check(intake["enabled"] is True and intake["analysis_status"] == "pending_not_started"
          and intake["automated_analysis"] is False and intake["operational_effects"] == 0
          and capabilities["operational_effects"] == 0)
    check(client.request("GET", case_path, iam_auth=False)[0] in (401, 403))
    check(client.request("GET", case_path, app_auth=False)[0] == 401)
    check(client.request("GET", case_path, app_auth="invalid-synthetic-smoke-token")[0] == 401)
    check(client.request("GET", case_path, origin=client.base_url)[0] == 403)
    declaration = {"case_id": case_id,
        "links": {"order_id": "smoke-order", "customer_id": "smoke-customer", "operator_id": "smoke-operator"},
        "participants": ["smoke-customer", "smoke-operator"], "language": "en"}
    status, zero = client.request("POST", "/v1/cases", declaration, case_id + "-create")
    check(status == (200 if expect_existing else 201))
    check(zero["case_id"] == case_id and zero["revision"] == 0 and zero["events"] == []
          and re.fullmatch(r"[a-f0-9]{64}", zero["snapshot_hash"]) is not None)
    check(pending(zero))
    check(client.request("POST", "/v1/cases", declaration, case_id + "-create") == (200, zero))
    event = {"event_id": "smoke-event", "occurred_at": "2026-10-10T10:00:00Z", "channel": "chat",
             "sender_id": "smoke-customer", "recipient_ids": ["smoke-operator"], "kind": "message",
             "text": "Synthetic deployment smoke; no customer action requested.", "media": None}
    event_body = {"expected_revision": 0, "event": event}
    status, one = client.request("POST", case_path + "/events", event_body, case_id + "-append")
    check(status == (200 if expect_existing else 201))
    check(one["case_id"] == case_id and one["revision"] == 1
          and one["previous_snapshot_hash"] == zero["snapshot_hash"]
          and re.fullmatch(r"[a-f0-9]{64}", one["snapshot_hash"]) is not None
          and one["snapshot_hash"] != zero["snapshot_hash"])
    check(pending(one))
    check(one["events"] == [event])
    check(client.request("POST", case_path + "/events", event_body, case_id + "-append") == (200, one))
    check(client.request("GET", case_path + "?revision=0") == (200, zero))
    check(client.request("GET", case_path) == (200, one))
    status, outbox = client.request("GET", case_path + "/analysis-jobs")
    check(status == 200 and outbox["case_id"] == case_id and outbox["operational_effects"] == 0)
    check(len(outbox["jobs"]) == 2 and all(job["status"] == "pending" for job in outbox["jobs"]))
    check({job["revision"]: job["snapshot_hash"] for job in outbox["jobs"]}
          == {0: zero["snapshot_hash"], 1: one["snapshot_hash"]})
    return {"status": "passed", "case_id": case_id, "checks": checks,
            "existing_after_restart": expect_existing, "operational_effects": 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Exact HTTPS service or tag origin in europe-west2")
    parser.add_argument("--case-id", required=True, help="Explicit smoke- prefixed ASCII case ID, at most 48 characters")
    parser.add_argument("--expect-existing", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = run(args.base_url, os.environ.get("PROOFKEY_SERVICE_TOKEN", ""), args.case_id, args.expect_existing)
    except (HTTPError, URLError, subprocess.SubprocessError, OSError, TimeoutError,
            ValueError, AssertionError, KeyError, TypeError, UnicodeError):
        print(json.dumps({"status": "failed", "error": "cloud_smoke_failed"}), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
