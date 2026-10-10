#!/usr/bin/env python3
"""Synthetic HTTP smoke. Reuse --case-id after restart; never deletes cases."""
import argparse
import json
import os
import sys
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def run(base_url, token, case_id, expect_existing=False):
    def request(method, path, body=None, key=None, authenticated=True):
        headers = {"Content-Type": "application/json"}
        if authenticated:
            headers["Authorization"] = "Bearer " + token
        if key:
            headers["Idempotency-Key"] = key
        data = None if body is None else json.dumps(body).encode()
        with urlopen(Request(base_url + path, data=data, headers=headers, method=method), timeout=10) as response:
            return response.status, json.load(response)

    checks = 0

    def check(condition):
        nonlocal checks
        if not condition:
            raise AssertionError("smoke_check_failed")
        checks += 1

    check(request("GET", "/healthz", authenticated=False)[0] == 200)
    check(request("GET", "/readyz", authenticated=False)[0] == 200)
    check(request("GET", "/v1/capabilities")[0] == 200)
    declaration = {
        "case_id": case_id,
        "links": {"order_id": "smoke-order", "customer_id": "smoke-customer", "operator_id": "smoke-operator"},
        "participants": ["smoke-customer", "smoke-operator"], "language": "en",
    }
    status, zero = request("POST", "/v1/cases", declaration, case_id + "-create")
    check(status == (200 if expect_existing else 201))
    check(zero["revision"] == 0 and zero["events"] == [])
    retry_status, retry_zero = request("POST", "/v1/cases", declaration, case_id + "-create")
    check(retry_status == 200 and retry_zero == zero)
    event = {"expected_revision": 0, "event": {
        "event_id": "smoke-event", "occurred_at": "2026-10-10T10:00:00Z", "channel": "chat",
        "sender_id": "smoke-customer", "recipient_ids": ["smoke-operator"], "kind": "message",
        "text": "Synthetic deployment smoke; no customer action requested.", "media": None,
    }}
    status, one = request("POST", "/v1/cases/" + case_id + "/events", event, case_id + "-append")
    check(status == (200 if expect_existing else 201))
    check(one["revision"] == 1 and one["previous_snapshot_hash"] == zero["snapshot_hash"])
    retry_status, retry_one = request("POST", "/v1/cases/" + case_id + "/events", event, case_id + "-append")
    check(retry_status == 200 and retry_one == one)
    check(request("GET", "/v1/cases/" + case_id + "?revision=0")[1] == zero)
    check(request("GET", "/v1/cases/" + case_id)[1] == one)
    status, outbox = request("GET", "/v1/cases/" + case_id + "/analysis-jobs")
    check(status == 200 and outbox["case_id"] == case_id and outbox["operational_effects"] == 0)
    check(len(outbox["jobs"]) == 2 and all(job["status"] == "pending" for job in outbox["jobs"]))
    check({job["revision"] for job in outbox["jobs"]} == {0, 1})
    check(all(job["snapshot_hash"] in {zero["snapshot_hash"], one["snapshot_hash"]} for job in outbox["jobs"]))
    return {"status": "passed", "case_id": case_id, "checks": checks,
            "existing_after_restart": expect_existing, "operational_effects": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--case-id", default="smoke-" + uuid.uuid4().hex[:16])
    parser.add_argument("--expect-existing", action="store_true")
    args = parser.parse_args()
    token = os.environ.get("PROOFKEY_SERVICE_TOKEN", "")
    target = urlsplit(args.base_url)
    if target.scheme != "http" or target.hostname not in {"localhost", "127.0.0.1"} or target.username or target.password or target.query or target.fragment or target.path not in {"", "/"}:
        parser.error("base URL must be a local HTTP origin")
    if not token or not args.case_id.startswith("smoke-") or len(args.case_id) > 48 or not all(c.isascii() and (c.isalnum() or c == "-") for c in args.case_id):
        parser.error("set PROOFKEY_SERVICE_TOKEN and use a smoke- prefixed ASCII case ID")
    try:
        result = run(args.base_url.rstrip("/"), token, args.case_id, args.expect_existing)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, AssertionError, KeyError, TypeError):
        print(json.dumps({"status": "failed", "error": "smoke_failed"}), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
