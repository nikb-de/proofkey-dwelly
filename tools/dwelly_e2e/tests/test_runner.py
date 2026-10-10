"""Runner transport controls only; this HTTP double is not E2E evidence."""
import copy
import importlib
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from tools.dwelly_platform.models import project_snapshot
from tools.dwelly_service.cases import _snapshot


def plan(case_id="runner-case"):
    return {
        "case_id": case_id,
        "source": {"source_id": case_id, "step_index": 0, "family_id": "unit",
                   "source_sha256": "b" * 64, "qualification": "transport-test-only"},
        "declaration": {"case_id": case_id, "links": {"order_id": "order", "customer_id": "customer",
                        "operator_id": "operator"}, "participants": ["customer", "operator"], "language": "en"},
        "events": [{"event_id": "source-context", "occurred_at": "2026-02-03T00:00:00+00:00",
                    "channel": "internal", "sender_id": "operator", "recipient_ids": [],
                    "kind": "message", "text": "Untrusted source context", "media": None}],
        "expectation": {"qualification": "PRIVATE_EXPECTATION_MUST_NOT_BE_UPLOADED"},
    }


@pytest.fixture
def runner(monkeypatch):
    module = importlib.import_module("tools.dwelly_e2e.runner")
    monkeypatch.setattr(module, "case_plans", lambda run_id: [plan(), plan("runner-two")])
    monkeypatch.setattr(module, "evaluate", lambda job, detail, selected: [
        {"name": "transport_test_only", "category": "operational", "status": "pass",
         "expected": True, "actual": True}])
    monkeypatch.setattr(module, "summarize", lambda records, mode: {"fixture_only": mode == "simulated"})
    return module


@pytest.fixture
def http_double():
    state = {"requests": [], "profiles": {"enabled": True, "profiles": [
        {"id": "sim", "provider": "openai", "model": "SIMULATED-unit", "available": True}]},
        "status": "succeeded", "mutate": None, "cases": {}, "jobs": {}, "stop_code": None,
        "redirect": False, "drop_submit": False, "alter_input": False,
        "replay_mutate": None, "replay_stage": 1, "replay_counts": {}}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def reply(self, status, value):
            raw = json.dumps(value).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            state["requests"].append(("GET", self.path, None, dict(self.headers)))
            if self.path.endswith("capabilities"):
                if state["redirect"]:
                    self.send_response(302)
                    self.send_header("Location", "/api/platform/capabilities?redirected=1")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                return self.reply(200, {"models": state["profiles"]})
            if "/model-runs/" in self.path:
                job = copy.deepcopy(next(job for job in state["jobs"].values()
                                         if job["run_id"] == self.path.rsplit("/", 1)[-1]))
                if state["mutate"]:
                    state["mutate"](job)
                return self.reply(200, job)
            case = state["cases"][self.path.rsplit("/", 1)[-1]]
            return self.reply(200, {"case": case})

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            state["requests"].append(("POST", self.path, body, dict(self.headers)))
            if self.headers.get("X-ProofKey-Request") != "platform-v1" or not self.headers.get("Idempotency-Key"):
                return self.reply(403, {"error": {"code": "missing_request_marker"}})
            if self.path.endswith("/cases"):
                snapshot = _snapshot(body)
                case = {"case_id": body["case_id"], "snapshot": snapshot,
                        "states": {"analysis": "not_started"}, "actions": [], "external_effects": 0}
                state["cases"][body["case_id"]] = case
                return self.reply(201, {"case": case})
            case_id, action = self.path.split("/")[-2:]
            case = state["cases"][case_id]
            if action == "events":
                event = copy.deepcopy(body["event"])
                if state["alter_input"]:
                    event["text"] = "Altered source after upload"
                old = case["snapshot"]
                declaration = {key: old[key] for key in ("case_id", "links", "participants", "language")}
                case["snapshot"] = _snapshot(declaration, [*old["events"], event], old["snapshot_hash"])
                case["states"]["analysis"] = "stale" if state["jobs"] else "not_started"
                return self.reply(200, {"case": case})
            key = self.headers["Idempotency-Key"]
            if key in state["jobs"]:
                job = copy.deepcopy(state["jobs"][key])
                count = state["replay_counts"].get(key, 0) + 1
                state["replay_counts"][key] = count
                if state["replay_mutate"] and count == state["replay_stage"]:
                    state["replay_mutate"](job)
                return self.reply(202, job)
            if body["expected_revision"] != case["snapshot"]["revision"]:
                return self.reply(409, {"error": {"code": "revision_conflict"}})
            if state["stop_code"]:
                return self.reply(409, {"error": {"code": state["stop_code"]}})
            evidence = project_snapshot(case["snapshot"])
            job = {"run_id": str(len(state["jobs"]) + 1) * 32, "case_id": case_id, "status": state["status"],
                   "step_index": evidence["step_index"], "model_profile_id": body["model_profile_id"],
                   "input": evidence, "input_hash": evidence["input_hash"], "reference": None,
                   "source": {"kind": "platform_case", "case_id": case_id,
                              "revision": body["expected_revision"], "snapshot_hash": body["snapshot_hash"]},
                   "transaction": {"dispatch_attempts": 1, "automatic_retries": 0, "operational_effects": 0},
                   "receipt": {"provider": "openai", "requested_model": "SIMULATED-unit",
                               "observed_model": "SIMULATED-unit", "model_profile_id": "sim"},
                   "candidate": {}, "error": None}
            state["jobs"][key] = job
            case["states"]["analysis"] = "current"
            if state["drop_submit"]:
                self.close_connection = True
                return
            return self.reply(202, job)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}", state
    server.shutdown()
    server.server_close()
    thread.join(3)


@pytest.mark.parametrize("patch", [
    {"base_url": "https://example.com"}, {"base_url": "http://127.0.0.1:8/other"},
    {"base_url": "http://x@127.0.0.1:8"}, {"base_url": "http://127.0.0.1:8?x=1"},
    {"mode": "test"}, {"limit": 0}, {"limit": 17}, {"limit": True},
    {"poll_timeout": 0}, {"run_id": "../escape"},
])
def test_invalid_configuration_never_makes_network_or_output(runner, http_double, tmp_path, patch):
    origin, state = http_double
    args = dict(base_url=origin, mode="simulated", profile_id="sim", output=tmp_path / "out",
                run_id="unit", limit=1, poll_timeout=1)
    args.update(patch)
    with pytest.raises(ValueError):
        runner.run(**args)
    assert not state["requests"]
    assert not (tmp_path / "out").exists()


def test_existing_output_is_never_overwritten(runner, http_double, tmp_path):
    origin, state = http_double
    with pytest.raises(FileExistsError):
        runner.run(origin, "simulated", "sim", tmp_path, "unit", limit=1)
    assert not state["requests"]


@pytest.mark.parametrize("profiles", [
    {"enabled": False, "profiles": []},
    {"enabled": True, "profiles": [{"id": "sim", "available": False, "reason": "missing_api_key"}]},
    {"enabled": True, "profiles": []},
])
def test_preflight_unavailable_writes_report_without_case_writes(runner, http_double, tmp_path, profiles):
    origin, state = http_double
    state["profiles"] = profiles
    output = tmp_path / "out"
    result = runner.run(origin, "simulated", "sim", output, "unit", limit=1)
    assert result["exit_code"] == 2
    assert result["status"] == "unavailable"
    assert result["records"][0]["status"] == "not_run"
    assert (output / "report.json").is_file()
    assert (output / "report.md").is_file()
    assert all(method == "GET" for method, *_ in state["requests"])


def test_simulated_profile_never_runs_in_live_mode(runner, http_double, tmp_path):
    origin, state = http_double
    result = runner.run(origin, "live", "sim", tmp_path / "out", "unit", limit=1)
    assert result["exit_code"] == 2
    assert result["error"] == "profile_mode_mismatch"
    assert result["qualification"].startswith("live mode requested;")
    assert all(method == "GET" for method, *_ in state["requests"])


def test_real_profile_never_runs_as_simulated(runner, http_double, tmp_path):
    origin, state = http_double
    state["profiles"]["profiles"][0]["model"] = "gpt-4.1-mini"
    result = runner.run(origin, "simulated", "sim", tmp_path / "out", "unit", limit=1)
    assert result["exit_code"] == 2
    assert all(method == "GET" for method, *_ in state["requests"])


def test_redirect_is_not_followed(runner, http_double, tmp_path):
    origin, state = http_double
    state["redirect"] = True
    result = runner.run(origin, "simulated", "sim", tmp_path / "out", "unit", limit=1)
    assert result["exit_code"] == 2
    assert len(state["requests"]) == 1


def test_terminal_replay_and_stale_probe_preserve_frozen_evidence(runner, http_double, tmp_path):
    origin, state = http_double
    output = tmp_path / "out"
    result = runner.run(origin, "simulated", "sim", output, "unit", limit=1)
    assert result["exit_code"] == 0
    assert result["qualification"] == "fixture-only; zero live provider evidence"
    record = result["records"][0]
    assert record["detail"]["states"]["analysis"] == "current"
    assert record["detail"]["snapshot"]["revision"] == 1
    assert result["probe"]["detail"]["states"]["analysis"] == "stale"
    assert result["probe"]["detail"]["snapshot"]["revision"] == 2
    assert result["probe"]["status"] == "pass"
    assert len(state["jobs"]) == 1
    uploads = json.dumps([body for method, _, body, _ in state["requests"] if method == "POST"])
    assert "PRIVATE_EXPECTATION" not in uploads
    submissions = [headers["Idempotency-Key"] for method, path, _, headers in state["requests"]
                   if method == "POST" and path.endswith("model-runs")]
    assert submissions[0] == submissions[1] == submissions[3]
    assert submissions[2] != submissions[0]
    assert len(list(output.rglob("*.json"))) >= 7
    assert "fixture-only" in (output / "report.md").read_text()


@pytest.mark.parametrize("mutation", [
    lambda job: job.update(run_id="2" * 32),
    lambda job: job.update(model_profile_id="wrong"),
    lambda job: job["source"].update(snapshot_hash="f" * 64),
    lambda job: job.update(input_hash="f" * 64),
    lambda job: job["receipt"].update(observed_model="unmarked-fake"),
])
def test_changed_readback_binding_never_counts_as_success(runner, http_double, tmp_path, mutation):
    origin, state = http_double
    state["mutate"] = mutation
    result = runner.run(origin, "simulated", "sim", tmp_path / "out", "unit", limit=1)
    assert result["exit_code"] == 1
    assert result["records"][0]["status"] == "failed"


def test_timeout_retains_first_job_and_marks_remaining_not_run(runner, http_double, tmp_path):
    origin, state = http_double
    state["status"] = "running"
    result = runner.run(origin, "simulated", "sim", tmp_path / "out", "unit", poll_timeout=0.02)
    assert result["exit_code"] == 2
    assert result["records"][0]["status"] == "unavailable"
    assert result["records"][0]["job"]["run_id"] == "1" * 32
    assert result["records"][1]["status"] == "not_run"
    assert len(state["jobs"]) == 1
    assert len([1 for method, path, *_ in state["requests"] if method == "POST" and path.endswith("model-runs")]) == 1


@pytest.mark.parametrize("stop_code", ["budget_exhausted", "model_credentials_unavailable", "http_401"])
def test_dispatch_failure_is_saved_and_does_not_start_next_case(runner, http_double, tmp_path, stop_code):
    origin, state = http_double
    state["stop_code"] = stop_code
    output = tmp_path / "out"
    result = runner.run(origin, "simulated", "sim", output, "unit")
    assert result["exit_code"] == 2
    assert result["records"][0]["error"] == stop_code
    assert result["records"][1]["status"] == "not_run"
    assert len(state["cases"]) == 1
    assert stop_code in (output / "report.json").read_text()


def test_outcome_unknown_is_not_automatically_replayed(runner, http_double, tmp_path):
    origin, state = http_double
    state["status"] = "outcome_unknown"
    result = runner.run(origin, "simulated", "sim", tmp_path / "out", "unit")
    assert result["exit_code"] == 2
    assert result["records"][1]["status"] == "not_run"
    assert len([1 for method, path, *_ in state["requests"] if method == "POST" and path.endswith("model-runs")]) == 1


def test_lost_submission_ack_does_not_retry_or_advance(runner, http_double, tmp_path):
    origin, state = http_double
    state["drop_submit"] = True
    result = runner.run(origin, "simulated", "sim", tmp_path / "out", "unit")
    assert result["exit_code"] == 2
    assert result["records"][0]["status"] == "unavailable"
    assert result["records"][1]["status"] == "not_run"
    assert len(state["jobs"]) == 1
    assert len([1 for method, path, *_ in state["requests"] if method == "POST" and path.endswith("model-runs")]) == 1


def test_semantic_failure_is_retained_while_remaining_checkpoints_run(runner, http_double, tmp_path, monkeypatch):
    origin, state = http_double
    monkeypatch.setattr(runner, "evaluate", lambda job, detail, selected: [
        {"name": "output_available", "category": "operational", "status": "pass", "expected": True, "actual": True},
        {"name": "wrong_wait_target", "category": "semantic", "status": "fail", "expected": "customer", "actual": "operator"}])
    result = runner.run(origin, "simulated", "sim", tmp_path / "out", "unit")
    assert result["exit_code"] == 1
    assert [record["status"] for record in result["records"]] == ["failed", "failed"]
    assert len(state["jobs"]) == 2
    assert result["probe"]["status"] == "pass"


def test_no_secret_values_are_written_from_untrusted_error_payload(runner, http_double, tmp_path):
    origin, state = http_double
    state["profiles"]["profiles"][0]["api_key"] = "secret-value-not-for-report"
    output = tmp_path / "out"
    runner.run(origin, "simulated", "sim", output, "unit", limit=1)
    assert all("secret-value-not-for-report" not in file.read_text() for file in output.rglob("*.json"))


def test_changed_uploaded_source_stops_before_provider_admission(runner, http_double, tmp_path):
    origin, state = http_double
    state["alter_input"] = True
    result = runner.run(origin, "simulated", "sim", tmp_path / "out", "unit", limit=1)
    assert result["exit_code"] == 1
    assert not state["jobs"]


@pytest.mark.parametrize("stage", [1, 2])
@pytest.mark.parametrize("mutation", [
    lambda job: job.update(status="queued", candidate=None, receipt=None),
    lambda job: job.update(candidate={"changed": True}),
    lambda job: job["receipt"].update(request_id="other-request"),
    lambda job: job["transaction"].update(attempt_id="different-attempt"),
])
def test_terminal_and_probe_replay_preserve_entire_immutable_job(runner, http_double, tmp_path, stage, mutation):
    origin, state = http_double
    state["replay_mutate"], state["replay_stage"] = mutation, stage
    result = runner.run(origin, "simulated", "sim", tmp_path / "out", "unit", limit=1)
    assert result["exit_code"] == 1
    if stage == 1:
        assert result["records"][0]["status"] == "failed"
    else:
        assert result["probe"]["status"] == "failed"


@pytest.mark.parametrize("models", [None, [], "wrong", {"enabled": True, "profiles": None},
    {"enabled": True, "profiles": {}}, {"enabled": True, "profiles": ["wrong"]},
    {"enabled": True, "profiles": [None]}, {"enabled": True, "profiles": [True]},
    {"enabled": "true", "profiles": []}])
def test_malformed_nested_capabilities_finalize_unavailable_report(runner, http_double, tmp_path, models):
    origin, state = http_double
    state["profiles"] = models
    output = tmp_path / "out"
    result = runner.run(origin, "simulated", "sim", output, "unit", limit=1)
    assert result["exit_code"] == 2
    assert result["error"] == "invalid_preflight_response"
    assert result["coverage"]["not_run"] == 1
    assert (output / "report.json").exists() and (output / "report.md").exists()
    assert not state["jobs"]


def test_reflected_token_is_redacted_in_all_artifacts(runner, http_double, tmp_path):
    origin, state = http_double
    state["stop_code"] = "sk-SYNTHETIC_REVIEW_TOKEN_123456"
    output = tmp_path / "out"
    runner.run(origin, "simulated", "sim", output, "unit", limit=1)
    assert all("sk-SYNTHETIC_REVIEW_TOKEN_123456" not in file.read_text()
               for file in output.rglob("*") if file.is_file())
