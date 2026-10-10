"""Bounded verification wrapper; production runner and expectations remain unchanged."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import psycopg
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.dwelly_analysis import catalog, model
from tools.dwelly_analysis.__main__ import load_provider_env
from tools.dwelly_analysis.jobs import AnalysisJobStore
from tools.dwelly_analysis.server import step_record
from tools.dwelly_analysis.worker import ModelRuntime
from tools.dwelly_e2e import runner
from tools.dwelly_e2e.cases import build_case
from tools.dwelly_platform.models import project_snapshot
from tools.dwelly_service.cases import _snapshot

OUT = Path(__file__).resolve().parent
DSN = "postgresql://postgres@127.0.0.1:63119/proofkey"
SCHEMA = "proofkey_live_e2e_20261010_models"
SCOPE = "platform-e2e-20261010"
PROFILES = ("openai-gpt-4-1-mini", "anthropic-claude-sonnet-4-6", "gemini-2-5-flash")
SELECTION = (("case-002-n4", 6), ("case-002", 5), ("case-002-n4", 5))
TEAM_SELECTION = (("team-001", 4), ("team-003", 4), ("team-025", 3))
RUN_IDS = dict(zip(PROFILES, ("r2-openai-1010", "r2-claude-1010", "r2-gemini-1010")))


def plans(run_id):
    return [build_case(source, cutoff, run_id) for source, cutoff in SELECTION]


def save(name, data):
    runner._save(OUT / name, data)


def db_snapshot():
    with psycopg.connect(DSN, row_factory=dict_row) as db:
        db.execute("SET TRANSACTION READ ONLY")
        db.execute("SET LOCAL search_path TO " + SCHEMA + ", pg_catalog")
        buckets = db.execute("SELECT budget_key, cap_usd::text, reserved_usd::text FROM model_budget_buckets WHERE budget_scope=%s ORDER BY budget_key", (SCOPE,)).fetchall()
        counts = db.execute("SELECT profile_id, status, count(*)::int AS jobs, sum(dispatch_attempts)::int AS dispatch_attempts, count(response)::int AS retained_responses, count(result)::int AS accepted_candidates, sum(reserved_usd)::text AS reserved_usd FROM model_jobs WHERE budget_scope=%s GROUP BY profile_id,status ORDER BY profile_id,status", (SCOPE,)).fetchall()
        rows = db.execute("SELECT job_id,profile_id,status,dispatch_attempts,response,result,error,reserved_usd::text,created_at::text,finished_at::text,spec FROM model_jobs WHERE budget_scope=%s ORDER BY created_at", (SCOPE,)).fetchall()
    settings = {}
    safe_rows = []
    for row in rows:
        spec = json.loads(row.pop("spec"))
        settings[row["profile_id"]] = {"profile": spec["profile"], "settings": spec["settings"]}
        row["case_id"] = spec["input"]["case_id"]
        for key in ("response", "result"):
            row[key] = None if row[key] is None else json.loads(row[key])
        safe_rows.append(row)
    return {"at": datetime.now(timezone.utc).isoformat(), "scope": SCOPE, "schema": SCHEMA,
            "buckets": buckets, "counts": counts, "settings": settings, "jobs": safe_rows}


def inventory():
    before = db_snapshot()
    save("database-before.json", before)
    caps = runner._HTTP("http://127.0.0.1:8105", OUT / "inventory-http").request("/capabilities")
    groups = {group: catalog.load_catalog(group=group) for group in ("legacy", "team")}
    files = ("tools/dwelly_e2e/runner.py", "tools/dwelly_e2e/cases.py", "tools/dwelly_e2e/checks.py",
             "tools/dwelly_analysis/model.py", "tools/dwelly_model/providers.py",
             "tools/dwelly_analysis/model-profiles.example.json", "datasets/team-handoff-v1/RUBRIC.md")
    selected = plans("r2-inventory-1010")
    estimates = {}
    for profile in PROFILES:
        frozen = before["settings"][profile]
        amounts = []
        inputs = []
        for plan in selected:
            snapshot = _snapshot(plan["declaration"])
            for event in plan["events"]:
                snapshot = _snapshot(plan["declaration"], [*snapshot["events"], event], snapshot["snapshot_hash"])
            inputs.append(project_snapshot(snapshot))
        inputs.extend(step_record(source, cutoff)["input"] for source, cutoff in TEAM_SELECTION)
        for evidence in inputs:
            amounts.append(model.reservation(evidence, frozen["profile"], frozen["settings"]["max_output_tokens"]))
        estimate = sum(Decimal(str(amount)) for amount in amounts)
        if estimate > Decimal("3"):
            raise RuntimeError("rerun_reservation_cap_exceeded")
        estimates[profile] = {"per_cutoff_usd": [str(amount) for amount in amounts], "total_usd": str(estimate), "maximum_additional_usd": "3"}
    result = {"at": datetime.now(timezone.utc).isoformat(), "capabilities": caps,
              "catalog": {group: {"documents": len(rows), "cutoffs": sum(row["steps"] + 1 for row in rows),
                                   "family_count": len({row["family_id"] for row in rows}), "rows": rows}
                          for group, rows in groups.items()},
              "canonical_handoff_seed_decisions": len(list((ROOT / "datasets/team-handoff-v1/examples/inputs").glob("*.json"))),
              "selection": [{"source": plan["source"], "expectation": plan["expectation"]} for plan in selected],
              "team_selection": [step_record(source, cutoff) for source, cutoff in TEAM_SELECTION],
              "reservation_estimates": estimates,
              "file_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in files},
              "qualification": "Three legacy cutoffs with unchanged strict ledger, plus three existing team cutoffs from independent source families using unchanged worker and reference comparison. Canonical seeds are inventoried, not run."}
    save("inventory.json", result)
    print(json.dumps({"inventory": {k: {s: v[s] for s in ("documents", "cutoffs", "family_count")} for k, v in result["catalog"].items()},
                      "additional_reservation_estimates": estimates, "current_buckets": before["buckets"]}, indent=2), flush=True)


def team_run(profile, runtime):
    output = OUT / profile / "team"
    records = []
    stopped = False
    for source, cutoff in TEAM_SELECTION:
        selected = step_record(source, cutoff)
        record = {"source_id": source, "step_index": cutoff, "input": selected["input"],
                  "reference": selected["reference"], "source": selected["source"], "status": "not_run", "checks": []}
        records.append(record)
        path = output / f"{source}-{cutoff}.json"
        if stopped:
            runner._save(path, record)
            continue
        selector = {"case_id": source, "step_index": cutoff, "expected_input_hash": selected["input"]["input_hash"],
                    "mode": "model", "model_profile_id": profile}
        key = "rerun-team-1010:" + profile + ":" + source + ":" + str(cutoff)
        job, created = runtime.submit(selector, key, selected)
        record.update(status="running", submitted_job=job, created=created)
        runner._save(path, record)
        deadline = time.monotonic() + 90
        while job["status"] not in runner.TERMINAL:
            if time.monotonic() >= deadline:
                record.update(status="unavailable", error="poll_timeout")
                stopped = True
                break
            time.sleep(0.2)
            job = runtime.get(job["run_id"])
            record["job"] = job
            runner._save(path, record)
        record["job"] = job
        if not stopped:
            durable = runtime.get(job["run_id"])
            replay, replay_created = runtime.submit(selector, key, selected)
            record.update(durable=durable, replay=replay)
            candidate = job.get("candidate")
            def check(name, passed, expected, actual):
                record["checks"].append({"name": name, "status": "pass" if passed else "fail", "expected": expected, "actual": actual})
            check("terminal_readback_unchanged", durable == job, "same terminal job", durable == job)
            check("terminal_replay_unchanged", replay == job and not replay_created, "same terminal job; no new job", replay == job and not replay_created)
            check("bound_original_input", job["input"] == selected["input"] and job["input_hash"] == selected["input"]["input_hash"], selected["input"]["input_hash"], job["input_hash"])
            check("reference_binding", job["reference"] == selected["reference"], "original unvalidated author reference", job["reference"] == selected["reference"])
            check("one_dispatch_zero_retries", job["transaction"]["dispatch_attempts"] == 1 and job["transaction"]["automatic_retries"] == 0, [1, 0], [job["transaction"]["dispatch_attempts"], job["transaction"]["automatic_retries"]])
            check("zero_operational_effects", job["transaction"]["operational_effects"] == 0 and (not candidate or candidate["operational_effects"] == 0), 0, job["transaction"]["operational_effects"])
            if job["status"] == "succeeded":
                evidence = set(m["event_id"] for m in selected["input"]["messages"])
                check("visible_evidence", set(candidate["evidence_event_ids"]) <= evidence, sorted(evidence), candidate["evidence_event_ids"])
                check("physical_delivery_not_inferred", candidate["physical_delivery"] == "not_inferred", "not_inferred", candidate["physical_delivery"])
                comparison = job["evaluation"]
                record.update(status="succeeded", state_agreement=comparison["state_agreement"], wait_target_agreement=comparison["wait_target_agreement"])
            else:
                record.update(status="unavailable", error=job.get("error"))
                stopped = True
        runner._save(path, record)
    result = {"records": records, "qualification": "Existing analysis ModelRuntime.submit/get methods and active platform worker share the same retained PostgreSQL budget and dispatch ledger. Team inputs are not projected through canonical platform cases; no platform UI claim. Existing comparison scores state/wait only, not free-text next-action semantics."}
    runner._save(output / "report.json", result)
    return {"attempted": sum(r["status"] != "not_run" for r in records), "valid_candidates": sum(r["status"] == "succeeded" for r in records),
            "state_agreement": sum(r.get("state_agreement", False) for r in records), "wait_target_agreement": sum(r.get("wait_target_agreement", False) for r in records)}


def execute():
    inv = json.loads((OUT / "inventory.json").read_text())
    baseline = json.loads((OUT / "database-before.json").read_text())
    current = db_snapshot()
    if current["buckets"] != baseline["buckets"] or runner._safe(current["settings"]) != baseline["settings"]:
        raise RuntimeError("database_changed_after_inventory")
    if any(row["status"] in {"queued", "running", "response_received"} for row in current["jobs"]):
        raise RuntimeError("pending_preexisting_jobs")
    for name, digest in inv["file_sha256"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise RuntimeError("source_changed_after_inventory:" + name)
    for profile in PROFILES:
        if (OUT / profile).exists():
            raise RuntimeError("immutable_run_output_already_exists")
    runner.case_plans = plans
    # Reuse the same existing admission methods and shared budget; only the already
    # running service dispatches. Credentials are loaded privately for availability
    # checks, never printed, serialized, or used for an extra direct provider call.
    settings = model.load_profiles(ROOT / "tools/dwelly_analysis/model-profiles.example.json")
    load_provider_env("/Users/nbk/.codex/worktrees/proofkey-runtime/Pitch project/.env")
    runtime = ModelRuntime(AnalysisJobStore(DSN, schema=SCHEMA), settings, SCOPE, allow_live=True)
    def one(profile):
        report = runner.run("http://127.0.0.1:8105", "live", profile, OUT / profile, RUN_IDS[profile], limit=3, poll_timeout=90)
        legacy = {key: report[key] for key in ("status", "exit_code", "coverage", "summary")}
        team = team_run(profile, runtime) if all(record["job"] and record["job"]["status"] == "succeeded" for record in report["records"]) else {"not_run": "legacy stop rule triggered"}
        return profile, {"legacy": legacy, "team": team}
    results = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(one, profile) for profile in PROFILES]
        for future in as_completed(futures):
            profile, result = future.result()
            results[profile] = result
            print(json.dumps({"profile": profile, **result}), flush=True)
    save("run-summary.json", results)
    save("database-after.json", db_snapshot())


def collect():
    after = db_snapshot()
    save("database-after.json", after)
    baseline = json.loads((OUT / "database-before.json").read_text())
    before_by_id = {row["job_id"]: row for row in baseline["jobs"]}
    new = [row for row in after["jobs"] if row["job_id"] not in before_by_id]
    before_buckets = {row["budget_key"]: row for row in baseline["buckets"]}
    deltas = [{"budget_key": row["budget_key"], "before": before_buckets[row["budget_key"]]["reserved_usd"],
               "after": row["reserved_usd"], "additional_usd": str(Decimal(row["reserved_usd"]) - Decimal(before_buckets[row["budget_key"]]["reserved_usd"]))}
              for row in after["buckets"]]
    result = {"new_jobs": new, "budget_deltas": deltas,
              "preexisting_jobs_unchanged": all(next(row for row in after["jobs"] if row["job_id"] == key) == old for key, old in before_by_id.items()),
              "new_jobs_count": len(new), "dispatch_attempts": sum(row["dispatch_attempts"] for row in new),
              "retained_responses": sum(row["response"] is not None for row in new),
              "accepted_candidates": sum(row["result"] is not None for row in new),
              "pending_new_jobs": [row["job_id"] for row in new if row["status"] in {"queued", "running", "response_received"}]}
    assert all(Decimal(row["additional_usd"]) <= Decimal("3") for row in deltas)
    save("accounting.json", result)
    print(json.dumps({key: value for key, value in result.items() if key != "new_jobs"}, indent=2), flush=True)


def execute_separate_team(profile):
    """Separately authorized distinct-input batch after the legacy stop; no retry."""
    if (OUT / profile / "team").exists():
        raise RuntimeError("immutable_team_batch_already_exists")
    baseline = json.loads((OUT / "database-before.json").read_text())
    known = {row["job_id"] for row in baseline["jobs"]}
    current = db_snapshot()
    new = [row for row in current["jobs"] if row["job_id"] not in known and row["profile_id"] == profile]
    if len(new) + len(TEAM_SELECTION) > 6:
        raise RuntimeError("provider_cutoff_cap_exceeded")
    settings = model.load_profiles(ROOT / "tools/dwelly_analysis/model-profiles.example.json")
    selected_profile = next(item for item in settings["profiles"] if item["id"] == profile)
    estimated = sum(model.reservation(step_record(source, cutoff)["input"], selected_profile, settings["max_output_tokens"])
                    for source, cutoff in TEAM_SELECTION)
    if sum(Decimal(row["reserved_usd"]) for row in new) + estimated > Decimal("3"):
        raise RuntimeError("provider_additional_budget_exceeded")
    load_provider_env("/Users/nbk/.codex/worktrees/proofkey-runtime/Pitch project/.env")
    runtime = ModelRuntime(AnalysisJobStore(DSN, schema=SCHEMA), settings, SCOPE, allow_live=True)
    result = team_run(profile, runtime)
    save(profile + "-separate-team-summary.json", result)
    print(json.dumps(result), flush=True)


def verify():
    accounting = json.loads((OUT / "accounting.json").read_text())
    inventory_data = json.loads((OUT / "inventory.json").read_text())
    assert accounting["preexisting_jobs_unchanged"] and not accounting["pending_new_jobs"]
    assert accounting["new_jobs_count"] == 15 and accounting["dispatch_attempts"] == 15
    assert accounting["retained_responses"] == 13 and accounting["accepted_candidates"] == 12
    assert all(Decimal(row["additional_usd"]) <= Decimal("3") for row in accounting["budget_deltas"])
    assert all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
               for name, digest in inventory_data["file_sha256"].items())
    summary = {}
    for profile in PROFILES:
        jobs = [row for row in accounting["new_jobs"] if row["profile_id"] == profile]
        assert len(jobs) <= 6 and all(row["dispatch_attempts"] == 1 for row in jobs)
        legacy = json.loads((OUT / profile / "report.json").read_text())
        team = json.loads((OUT / profile / "team/report.json").read_text())
        probe = json.loads((OUT / profile / "control-probe/probe.json").read_text())
        assert probe["status"] == "pass" and len(probe["checks"]) == 12
        assert all(check["status"] == "pass" for check in probe["checks"])
        for record in team["records"]:
            original = step_record(record["source_id"], record["step_index"])
            assert record["input"] == original["input"] and record["reference"] == original["reference"]
            if record["status"] == "succeeded":
                assert all(check["status"] == "pass" for check in record["checks"])
                assert record["job"]["transaction"]["automatic_retries"] == 0
                assert record["job"]["transaction"]["operational_effects"] == 0
        valid_legacy = [r for r in legacy["records"] if r["job"] and r["job"]["status"] == "succeeded"]
        valid_team = [r for r in team["records"] if r["status"] == "succeeded"]
        summary[profile] = {
            "dispatches": len(jobs), "retained_responses": sum(row["response"] is not None for row in jobs),
            "accepted_candidates": sum(row["result"] is not None for row in jobs),
            "legacy": {"selected": 3, "attempted": sum(r["job"] is not None for r in legacy["records"]),
                       "valid": len(valid_legacy), "full_ledger_match": sum(r["status"] == "succeeded" for r in valid_legacy)},
            "team": {"selected": 3, "attempted": sum(r["status"] != "not_run" for r in team["records"]),
                     "valid": len(valid_team), "state_agreement": sum(r["state_agreement"] for r in valid_team),
                     "wait_target_agreement": sum(r["wait_target_agreement"] for r in valid_team)},
            "observed_models": sorted({row["response"]["observed_model"] for row in jobs if row["response"]}),
            "stale_replay_assertions_passed": len(probe["checks"]),
            "errors": [{"case_id": row["case_id"], "error": row["error"]} for row in jobs if row["error"]]}
    save("summary.json", summary)
    load_provider_env("/Users/nbk/.codex/worktrees/proofkey-runtime/Pitch project/.env")
    secrets = [os.environ.get(name) for name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "ANTHROPIC_WORKSPACE_ID", "GEMINI_API_KEY")]
    files = [path for path in OUT.rglob("*") if path.is_file() and "__pycache__" not in path.parts]
    matches = [str(path.relative_to(OUT)) for path in files
               if any(secret and secret.encode() in path.read_bytes() for secret in secrets)]
    assert not matches, "credential_material_found_in_artifacts"
    checks = {"status": "passed", "at": datetime.now(timezone.utc).isoformat(),
              "source_hashes_unchanged": True, "team_input_references_unchanged": True,
              "prior_jobs_unchanged": True, "all_36_supplemental_stale_replay_checks_passed": True,
              "new_jobs": 15, "max_dispatches_per_provider": 6, "additional_budget_per_provider_below_3_usd": True,
              "pending_new_jobs": 0, "credential_scan_files": len(files), "credential_matches": 0}
    save("verification.json", checks)
    print(json.dumps({"verification": checks, "summary": summary}, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("inventory", "run", "collect", "team-openai", "team-gemini", "verify"))
    args = parser.parse_args()
    {"inventory": inventory, "run": execute, "collect": collect, "verify": verify,
     "team-openai": lambda: execute_separate_team("openai-gpt-4-1-mini"),
     "team-gemini": lambda: execute_separate_team("gemini-2-5-flash")}[args.command]()
