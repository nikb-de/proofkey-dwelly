"""Bounded loopback HTTP runner for authored case checkpoints."""
import copy
from datetime import datetime, timedelta
import hashlib
import json
import math
from pathlib import Path
import re
import socket
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from tools.dwelly_platform.models import project_snapshot
from tools.dwelly_service.cases import _snapshot


TERMINAL = {"succeeded", "failed", "outcome_unknown", "unavailable"}
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")


def _safe(value):
    """Public API evidence only; redact accidentally reflected credential material."""
    if isinstance(value, dict):
        return {key: ("[REDACTED]" if re.search(r"authorization|api.?key|password|secret|access.?token|refresh.?token", key, re.I)
                      else _safe(item)) for key, item in value.items()}
    if isinstance(value, list):
        return [_safe(item) for item in value]
    if isinstance(value, str):
        value = re.sub(r"(?i)bearer\s+[^\s\"']+", "Bearer [REDACTED]", value)
        return re.sub(r"\bsk-[A-Za-z0-9_-]{8,}", "[REDACTED]", value)
    return value


def _save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_safe(value), ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def _key(run_id, plan, operation):
    identity = [run_id, plan["source"]["source_id"], plan["source"]["step_index"], operation]
    return "e2e:" + hashlib.sha256(json.dumps(identity, separators=(",", ":")).encode()).hexdigest()


class RunError(Exception):
    def __init__(self, code, *, status=None, unavailable=True):
        super().__init__(code)
        self.code, self.status, self.unavailable = code, status, unavailable


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class _HTTP:
    def __init__(self, origin, output):
        self.origin, self.output, self.sequence = origin, output, 0
        # Proxy environment variables must not route this local-only client elsewhere.
        self.opener = build_opener(ProxyHandler({}), _NoRedirect())

    def request(self, path, body=None, key=None, timeout=15):
        self.sequence += 1
        exchange = {"method": "GET" if body is None else "POST", "path": path}
        headers = {"Accept": "application/json", "Origin": self.origin}
        raw = None
        if body is not None:
            raw = json.dumps(body, ensure_ascii=False, allow_nan=False).encode()
            headers.update({"Content-Type": "application/json", "X-ProofKey-Request": "platform-v1",
                            "Idempotency-Key": key})
            exchange.update(body=body, idempotency_key=key)
        try:
            request = Request(self.origin + "/api/platform" + path, data=raw, headers=headers)
            try:
                response = self.opener.open(request, timeout=max(0.001, timeout))
            except HTTPError as error:
                response = error
            with response:
                exchange["http_status"] = response.status
                payload = response.read(2_000_001)
                if len(payload) > 2_000_000:
                    raise RunError("response_too_large")
                if 300 <= response.status < 400:
                    raise RunError("http_redirect_refused", status=response.status)
                try:
                    value = json.loads(payload)
                except (ValueError, UnicodeError):
                    raise RunError("invalid_json_response", status=response.status) from None
                exchange["response"] = value
                if not 200 <= response.status < 300:
                    error = value.get("error", {}) if isinstance(value, dict) else {}
                    code = error.get("code") if isinstance(error, dict) else None
                    if not isinstance(code, str) or not re.fullmatch(r"[a-zA-Z0-9_:-]{1,100}", code):
                        code = "http_" + str(response.status)
                    raise RunError(code, status=response.status)
                if not isinstance(value, dict):
                    raise RunError("invalid_json_response")
                return value
        except (URLError, TimeoutError, OSError, socket.timeout):
            exchange["error"] = "transport_unavailable"
            raise RunError("transport_unavailable") from None
        except RunError as error:
            exchange["error"] = error.code
            raise
        finally:
            _save(self.output / "http" / f"{self.sequence:04d}.json", exchange)


def _check(name, passed, expected, actual):
    return {"name": name, "category": "operational", "status": "pass" if passed else "fail",
            "expected": expected, "actual": actual}


def _bindings(job, snapshot, profile, run_id=None):
    expected_source = {"kind": "platform_case", "case_id": snapshot["case_id"],
                       "revision": snapshot["revision"], "snapshot_hash": snapshot["snapshot_hash"]}
    evidence = project_snapshot(snapshot)
    checks = [
        _check("frozen_source_binding", job.get("source") == expected_source, expected_source, job.get("source")),
        _check("frozen_input_binding", job.get("input") == evidence and job.get("input_hash") == evidence["input_hash"],
               evidence["input_hash"], job.get("input_hash")),
        _check("case_profile_binding", (job.get("case_id"), job.get("step_index"), job.get("model_profile_id")) ==
               (snapshot["case_id"], snapshot["revision"], profile["id"]),
               [snapshot["case_id"], snapshot["revision"], profile["id"]],
               [job.get("case_id"), job.get("step_index"), job.get("model_profile_id")]),
        _check("no_reference_upload", job.get("reference") is None, None, job.get("reference")),
    ]
    if run_id is not None:
        checks.append(_check("first_run_id_preserved", job.get("run_id") == run_id, run_id, job.get("run_id")))
    if job.get("status") == "succeeded":
        receipt = job.get("receipt") or {}
        expected = [profile["id"], profile.get("provider"), profile.get("model")]
        actual = [receipt.get("model_profile_id"), receipt.get("provider"), receipt.get("requested_model")]
        checks.append(_check("provider_receipt_binding", expected == actual, expected, actual))
        simulated = any(str(profile.get(key, "")).upper().startswith("SIMULATED") for key in ("provider", "model"))
        observed = receipt.get("observed_model")
        if simulated:
            checks.append(_check("simulated_receipt_label", isinstance(observed, str) and observed.upper().startswith("SIMULATED"),
                                 "SIMULATED prefix", observed))
        else:
            checks.append(_check("live_receipt_label", not (isinstance(observed, str) and observed.upper().startswith("SIMULATED")),
                                 "no SIMULATED prefix", observed))
    return checks


def _require_checks(checks):
    if any(check["status"] == "fail" for check in checks):
        raise RunError("binding_or_operational_check_failed", unavailable=False)


def _same_terminal_job(name, expected, actual):
    """A terminal job is immutable: no response/result/transaction fields may drift."""
    changed = sorted(key for key in set(expected) | set(actual) if expected.get(key) != actual.get(key)
                     or (key in expected) != (key in actual))
    return _check(name, actual == expected, "exact same terminal job (all fields)", changed)


def _stop_job(job):
    if job.get("status") in {"outcome_unknown", "unavailable"}:
        return True
    code = (job.get("error") or {}).get("code", "")
    return ("budget" in code or "api_key" in code or "credentials" in code
            or code in {"http_401", "http_403", "missing_workspace_id", "invalid_workspace_id"})


def _probe(client, record, profile, run_id, output):
    plan, snapshot, original = record["plan"], record["detail"]["snapshot"], record["job"]
    body = {"expected_revision": snapshot["revision"], "snapshot_hash": snapshot["snapshot_hash"],
            "model_profile_id": profile["id"]}
    event = {"event_id": "e2e-stale-probe", "occurred_at":
             (datetime.fromisoformat(snapshot["events"][-1]["occurred_at"].replace("Z", "+00:00")) + timedelta(seconds=1)).isoformat(),
             "channel": "internal", "sender_id": snapshot["links"]["operator_id"], "recipient_ids": [],
             "kind": "message", "text": "SYNTHETIC E2E PROBE: later evidence only; not part of the authored source or semantic evaluation.",
             "media": None}
    result = {"status": "failed", "case_id": plan["case_id"], "event": event, "checks": []}
    try:
        appended = client.request(f"/cases/{plan['case_id']}/events", {"expected_revision": snapshot["revision"], "event": event},
                                  _key(run_id, plan, "stale-event"))
        result["append"] = appended
        _save(output / "probe.json", result)
        detail = client.request(f"/cases/{plan['case_id']}")["case"]
        result["detail"] = detail
        result["checks"].extend([
            _check("later_evidence_stales_analysis", detail.get("states", {}).get("analysis") == "stale", "stale", detail.get("states", {}).get("analysis")),
            _check("probe_has_no_actions", detail.get("actions") == [] and detail.get("external_effects") == 0, [], detail.get("actions")),
        ])
        try:
            unexpected = client.request(f"/cases/{plan['case_id']}/model-runs", body, _key(run_id, plan, "stale-fresh"))
            result["fresh_submission"] = unexpected
            result["checks"].append(_check("old_revision_new_key_rejected", False, "revision_conflict", "accepted"))
            # An incorrect server has admitted a new attempt; do not issue any more writes.
            return result
        except RunError as error:
            result["fresh_submission_error"] = {"code": error.code, "http_status": error.status}
            result["checks"].append(_check("old_revision_new_key_rejected", error.status == 409 and error.code == "revision_conflict",
                                           "revision_conflict", error.code))
        _require_checks(result["checks"])
        replay = client.request(f"/cases/{plan['case_id']}/model-runs", body, _key(run_id, plan, "submit"))
        result["replay"] = replay
        checks = _bindings(replay, snapshot, profile, original["run_id"])
        checks.append(_same_terminal_job("probe_terminal_job_unchanged", original, replay))
        checks.append(_check("probe_dispatch_unchanged", replay.get("transaction", {}).get("dispatch_attempts") ==
                             original.get("transaction", {}).get("dispatch_attempts"), original.get("transaction"), replay.get("transaction")))
        result["checks"].extend(checks)
        _require_checks(result["checks"])
        result["status"] = "pass"
    except (RunError, KeyError, TypeError, ValueError) as error:
        result["error"] = error.code if isinstance(error, RunError) else "invalid_probe_response"
    finally:
        _save(output / "probe.json", result)
    return result


def case_plans(run_id):
    from .cases import case_plans as build
    return build(run_id)


def evaluate(job, detail, plan):
    from .checks import evaluate as check
    return check(job, detail, plan)


def summarize(records, mode):
    from .checks import summarize as summary
    return summary(records, mode)


def run(base_url, mode, profile_id, output, run_id, limit=16, poll_timeout=90):
    """Run at most sixteen source cutoffs, retaining every response before continuing.

    Validation errors raise before I/O. Operational failures return an unavailable
    report (exit 2); failed checks return exit 1. There is no provider retry path.
    """
    parsed = urlsplit(base_url)
    try:
        port = parsed.port
    except ValueError:
        raise ValueError("invalid_loopback_origin") from None
    if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}
            or parsed.username is not None or parsed.password is not None
            or parsed.path not in {"", "/"} or parsed.query or parsed.fragment
            or (port is not None and not 1 <= port <= 65535)):
        raise ValueError("invalid_loopback_origin")
    if mode not in {"live", "simulated"}:
        raise ValueError("invalid_mode")
    if type(limit) is not int or not 1 <= limit <= 16:
        raise ValueError("invalid_limit")
    if type(poll_timeout) not in {int, float} or not math.isfinite(poll_timeout) or not 0 < poll_timeout <= 600:
        raise ValueError("invalid_poll_timeout")
    if not isinstance(run_id, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,31}", run_id) is None:
        raise ValueError("invalid_run_id")
    if not isinstance(profile_id, str) or IDENTIFIER.fullmatch(profile_id) is None:
        raise ValueError("invalid_profile_id")
    plans = case_plans(run_id)[:limit]
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    origin = base_url.rstrip("/")
    client = _HTTP(origin, output)
    report = {"schema_version": "dwelly-e2e-report-v1", "run_id": run_id, "mode": mode,
              "requested_profile_id": profile_id, "base_url": origin, "status": "unavailable", "exit_code": 2,
              "qualification": "fixture-only; zero live provider evidence" if mode == "simulated" else
                  "live mode requested; execution evidence depends on status and receipts; authored expectations unvalidated; no held-out accuracy claim",
              "records": [{"plan": selected, "job": None, "detail": None, "checks": [], "status": "not_run"}
                          for selected in plans], "probe": None}
    for index, record in enumerate(report["records"]):
        _save(output / "checkpoints" / f"{index:02d}" / "source.json", record["plan"])
    try:
        caps = client.request("/capabilities")
        models = caps.get("models")
        if (type(models) is not dict or type(models.get("enabled")) is not bool
                or type(models.get("profiles")) is not list
                or any(type(profile) is not dict or type(profile.get("id")) is not str
                       or type(profile.get("available")) is not bool for profile in models["profiles"])):
            raise RunError("invalid_preflight_response")
        profiles = models["profiles"]
        if len({profile["id"] for profile in profiles}) != len(profiles):
            raise RunError("invalid_preflight_response")
        selected = next((p for p in profiles if p["id"] == profile_id), None)
        report["profile"] = selected
        _save(output / "preflight.json", {"models_enabled": models.get("enabled"), "profile": selected})
        if models.get("enabled") is not True:
            raise RunError("model_execution_disabled")
        if selected is None:
            raise RunError("unknown_model_profile")
        if selected.get("available") is not True:
            raise RunError("model_credentials_unavailable")
        if any(type(selected.get(key)) is not str or not selected[key] for key in ("provider", "model")):
            raise RunError("invalid_preflight_response")
        simulated = any(str(selected.get(key, "")).upper().startswith("SIMULATED") for key in ("provider", "model"))
        if (mode == "simulated") != simulated:
            raise RunError("profile_mode_mismatch")
        last_success = None
        stop = False
        for index, record in enumerate(report["records"]):
            if stop:
                break
            plan = record["plan"]
            checkpoint = output / "checkpoints" / f"{index:02d}" / "record.json"
            record["status"] = "running"
            try:
                detail = client.request("/cases", plan["declaration"], _key(run_id, plan, "create"))["case"]
                record["detail"] = detail
                _save(checkpoint, record)
                for event in plan["events"]:
                    detail = client.request(f"/cases/{plan['case_id']}/events",
                        {"expected_revision": detail["snapshot"]["revision"], "event": event},
                        _key(run_id, plan, "event:" + event["event_id"]))["case"]
                    record["detail"] = detail
                    _save(checkpoint, record)
                snapshot = copy.deepcopy(detail["snapshot"])
                expected_snapshot = _snapshot(plan["declaration"])
                for event in plan["events"]:
                    expected_snapshot = _snapshot(plan["declaration"], [*expected_snapshot["events"], event],
                                                  expected_snapshot["snapshot_hash"])
                record["checks"].append(_check("source_snapshot_before_dispatch", snapshot == expected_snapshot,
                                                expected_snapshot["snapshot_hash"], snapshot.get("snapshot_hash")))
                _require_checks(record["checks"])
                binding = {"expected_revision": snapshot["revision"], "snapshot_hash": snapshot["snapshot_hash"],
                           "model_profile_id": profile_id}
                job = client.request(f"/cases/{plan['case_id']}/model-runs", binding, _key(run_id, plan, "submit"))
                record["job"] = job
                _save(checkpoint, record)
                first_id = job.get("run_id")
                if not isinstance(first_id, str) or re.fullmatch(r"[a-f0-9]{32}", first_id) is None:
                    raise RunError("invalid_run_id_response", unavailable=False)
                record["checks"].extend(_bindings(job, snapshot, selected, first_id))
                _require_checks(record["checks"])
                deadline = time.monotonic() + poll_timeout
                while job.get("status") not in TERMINAL:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise RunError("poll_timeout")
                    job = client.request("/model-runs/" + first_id, timeout=min(15, remaining))
                    record["job"] = job
                    _save(checkpoint, record)
                    current_checks = _bindings(job, snapshot, selected, first_id)
                    if any(check["status"] == "fail" for check in current_checks):
                        record["checks"].extend(current_checks)
                        _save(checkpoint, record)
                        _require_checks(current_checks)
                    if job.get("status") not in TERMINAL:
                        time.sleep(min(0.1, max(0, deadline - time.monotonic())))
                if _stop_job(job):
                    raise RunError((job.get("error") or {}).get("code") or job["status"])
                # The terminal GET tests durable observation even for immediately completed submissions.
                durable = client.request("/model-runs/" + first_id)
                record["job"] = durable
                record["checks"].extend(_bindings(durable, snapshot, selected, first_id))
                record["checks"].append(_same_terminal_job("terminal_readback_unchanged", job, durable))
                _save(checkpoint, record)
                _require_checks(record["checks"])
                if durable.get("status") != job.get("status"):
                    raise RunError("terminal_status_changed", unavailable=False)
                if _stop_job(durable):
                    raise RunError((durable.get("error") or {}).get("code") or durable["status"])
                replay = client.request(f"/cases/{plan['case_id']}/model-runs", binding, _key(run_id, plan, "submit"))
                record["replay"] = replay
                record["checks"].extend(_bindings(replay, snapshot, selected, first_id))
                record["checks"].append(_same_terminal_job("terminal_replay_unchanged", durable, replay))
                expected_attempts = durable.get("transaction", {}).get("dispatch_attempts")
                actual_attempts = replay.get("transaction", {}).get("dispatch_attempts")
                record["checks"].append(_check("terminal_replay_no_dispatch", expected_attempts == actual_attempts,
                                                expected_attempts, actual_attempts))
                _require_checks(record["checks"])
                detail = client.request(f"/cases/{plan['case_id']}")["case"]
                record["detail"] = detail
                record["checks"].extend(evaluate(durable, detail, plan))
                if durable.get("status") != "succeeded" or any(check["status"] == "not_run" for check in record["checks"]):
                    raise RunError("model_output_unavailable")
                # A semantic mismatch is a measured result, so retain it and
                # continue the bounded experiment without changing the model.
                record["status"] = "failed" if any(check["status"] == "fail" for check in record["checks"]) else "succeeded"
                last_success = record
            except RunError as error:
                record.update(status="unavailable" if error.unavailable else "failed", error=error.code)
                # Uncertain dispatch, unavailable infrastructure, and binding violations never advance to another cutoff.
                stop = True
            except (KeyError, TypeError, ValueError) as error:
                record.update(status="failed", error="invalid_platform_response")
                stop = True
            finally:
                _save(checkpoint, record)
        if last_success is not None and not stop:
            report["probe"] = _probe(client, last_success, selected, run_id, output)
        failures = any(record["status"] == "failed" for record in report["records"])
        unavailable = any(record["status"] in {"unavailable", "not_run"} for record in report["records"])
        if failures or (report["probe"] is not None and report["probe"]["status"] != "pass"):
            report.update(status="failed", exit_code=1)
        elif not unavailable and report["records"] and report["probe"] is not None:
            report.update(status="passed", exit_code=0)
    except RunError as error:
        report["error"] = error.code
    except (KeyError, TypeError, ValueError):
        report.update(error="invalid_preflight_response")
    for index, record in enumerate(report["records"]):
        if not any(check["name"] == "output_available" for check in record["checks"]):
            pending = evaluate(record["job"], record["detail"], record["plan"])
            if record["status"] == "not_run":
                for check in pending:
                    check["status"] = "not_run"
                    check["actual"] = "checkpoint_not_attempted"
            record["checks"].extend(pending)
        _save(output / "checkpoints" / f"{index:02d}" / "record.json", record)
    report["summary"] = summarize(report["records"], mode)
    report["coverage"] = {"requested": len(report["records"]), **{
        status: sum(record["status"] == status for record in report["records"])
        for status in ("succeeded", "failed", "unavailable", "not_run")}}
    # Both serializations and the caller-visible result share the same redaction.
    report = _safe(report)
    _save(output / "report.json", report)
    rows = ["# Case model E2E report", "", f"Status: {report['status']} (exit {report['exit_code']})",
            f"Mode: {mode}. {report['qualification']}", f"Requested profile: {report['requested_profile_id']}", "",
            "| Source | Cutoff | Status | Error |", "|---|---:|---|---|"]
    for record in report["records"]:
        rows.append(f"| {record['plan']['source']['source_id']} | {record['plan']['source']['step_index']} | "
                    f"{record['status']} | {record.get('error', '')} |")
    if report.get("error"):
        rows.extend(["", "Preflight error: " + report["error"]])
    rows.extend(["", "Semantic and operational counts (separate):", "```json",
                 json.dumps(report["summary"], ensure_ascii=False, indent=2), "```", "",
                 "Source families and author expectations are not independent held-out accuracy evidence."])
    (output / "report.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    return report
