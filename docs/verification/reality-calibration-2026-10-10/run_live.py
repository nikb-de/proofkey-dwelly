"""Bounded judge-only pilot. No retries, proposal generation or business effects."""
import argparse
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import fcntl
import json
import os
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pilot
from tools.dwelly_model import providers
from tools.dwelly_model.budget import BudgetLedger, sync_directory
from tools.dwelly_model.runner import _model_json


def durable(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    sync_directory(path.parent)


def load_env(path, config):
    names = {seat["api_key_env"] for seat in config["judges"]}
    names.update(seat["workspace_id_env"] for seat in config["judges"] if "workspace_id_env" in seat)
    for line in path.read_text().splitlines():
        line = line.strip()
        if line.startswith("export "):
            line = line[7:]
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() in names:
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            if not value:
                raise ValueError("empty_configured_credential")
            os.environ[name.strip()] = value


def canary_gate(records):
    by_provider = {}
    for record in records:
        by_provider.setdefault(record["provider"], {})[record["control_id"]] = record
    approved, reasons = [], {}
    for provider, group in by_provider.items():
        needed = ["dev-001-positive", "dev-001-critical_negative", "dev-001-insufficient"]
        if any(name not in group or group[name]["status"] != "ok" for name in needed):
            reasons[provider] = "missing_or_invalid_canary"
            continue
        good, bad, missing = (group[name]["judgment"] for name in needed)
        if (good["abstain"] or good["critical_failures"] or good["scores"]["next_action"] < 3
                or good["scores"]["grounding"] < 3):
            reasons[provider] = "positive_control_not_separated"
        elif not (bad["critical_failures"] or bad["scores"]["grounding"] <= 1 or bad["scores"]["no_fabrication"] <= 1):
            reasons[provider] = "fabrication_control_not_detected"
        elif not (missing["abstain"] or missing["scores"]["grounding"] <= 2):
            reasons[provider] = "missing_evidence_control_not_detected"
        else:
            approved.append(provider)
    return {"approved_seats": sorted(approved), "rejected_seats": reasons,
            "qualification": "provisional_control_signal_only_not_human_calibration"}


def execute(packet, phase, *, transport=providers.complete, deadline_seconds=900):
    # Verify frozen source artifacts; result files are deliberately separate.
    pilot.report(packet, packet / "results.json")
    config = json.loads((packet / "config.json").read_bytes())
    schedule = json.loads((packet / "schedule.json").read_bytes())
    live = packet / "live"
    live.mkdir(exist_ok=True)
    status_path = live / f"status-{phase}.json"
    if status_path.exists():
        return json.loads(status_path.read_bytes())
    gate_path = live / "canary-gate.json"
    if phase == "remaining" and not gate_path.exists():
        raise ValueError("canary_gate_required")
    eligible = set(json.loads(gate_path.read_bytes())["approved_seats"]) if phase == "remaining" else {s["provider"] for s in config["judges"]}
    pending = [row for row in schedule if row["phase"] == phase and row["provider"] in eligible]
    seats = {seat["provider"]: seat for seat in config["judges"]}
    stopped, start = {}, time.monotonic()
    for path in (live / "stopped").glob("*.json") if (live / "stopped").exists() else []:
        stopped[path.stem] = json.loads(path.read_bytes())["reason"]
    lock = (live / "runner.lock").open("a+")
    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    def stop(provider, reason):
        stopped[provider] = reason
        path = live / "stopped" / f"{provider}.json"
        if not path.exists():
            durable(path, {"reason": reason})
    with lock, BudgetLedger(live / "calibration-budget.jsonl", config["budget_per_model_usd"]) as budget, ThreadPoolExecutor(max_workers=3) as pool:
        active = {}
        while pending or active:
            if time.monotonic() - start >= deadline_seconds:
                pending = []
            active_providers = {row["provider"] for row in active.values()}
            for row in pending[:]:
                if row["provider"] in stopped:
                    pending.remove(row)
                    continue
                if len(active) >= 3 or row["provider"] in active_providers:
                    continue
                pending.remove(row)
                rid = row["request_id"]
                intent_path = live / "intents" / f"{rid}.json"
                result_path = live / "records" / f"{rid}.json"
                if intent_path.exists() or result_path.exists():
                    continue  # An unknown outcome is not retried.
                payload = json.loads((packet / "prompts" / f'{row["control_id"]}.json').read_bytes())
                try:
                    reservation = budget.reserve(seats[row["provider"]], payload["system"], payload["prompt"], config["max_output_tokens"], rid)
                except ValueError:
                    stop(row["provider"], "budget_admission_failed")
                    continue
                durable(intent_path, {**row, "reservation": reservation, "status": "intent_durable_before_dispatch"})
                future = pool.submit(transport, seats[row["provider"]], payload["system"], payload["prompt"],
                                     max_output_tokens=config["max_output_tokens"], timeout=config["timeout_seconds"])
                active[future] = row
                active_providers.add(row["provider"])
            if not active:
                if pending:
                    continue
                break
            done, _ = wait(active, timeout=5, return_when=FIRST_COMPLETED)
            for future in done:
                row = active.pop(future)
                record = {**row, "status": "error", "judgment": None}
                response = None
                try:
                    response = future.result()
                    record.update(response=response, observed_model=response.get("observed_model"))
                    if response.get("observed_model") != row["requested_model"]:
                        record["error"] = "model_identity_mismatch"
                        stop(row["provider"], record["error"])
                    else:
                        control = json.loads((packet / "controls" / f'{row["control_id"]}.json').read_bytes())
                        record["judgment"] = pilot.semantic.validate_judgment(control["snapshot"], _model_json(response["text"]))
                        record["status"] = "ok"
                except providers.ProviderError as error:
                    record["error"] = error.code
                    if error.code in {"http_401", "http_403", "http_404", "http_429", "missing_api_key", "invalid_api_key"}:
                        stop(row["provider"], error.code)
                except (ValueError, TypeError, KeyError, RecursionError):
                    record["error"] = "invalid_judgment"
                    stop(row["provider"], "invalid_judgment")
                except Exception:
                    record["error"] = "unexpected_transport_error"
                    stop(row["provider"], "unexpected_transport_error")
                budget.record_outcome(row["request_id"], record["status"], response.get("input_tokens") if response else None, response.get("output_tokens") if response else None)
                durable(live / "records" / f'{row["request_id"]}.json', record)
                print(json.dumps({"request_id": row["request_id"], "status": record["status"], "observed_model": record.get("observed_model"), "error": record.get("error")}), flush=True)
        records = [json.loads(path.read_bytes()) for path in sorted((live / "records").glob("*.json"))] if (live / "records").exists() else []
        if phase == "canary" and not gate_path.exists():
            durable(gate_path, canary_gate(records))
        output = {"phase": phase, "attempted_total": len(list((live / "intents").glob("*.json"))) if (live / "intents").exists() else 0,
                  "recorded_total": len(records), "stopped_seats": stopped, "budget": budget.summary(),
                  "summary": pilot.summarize(schedule, records)}
        durable(live / f"results-{phase}.json", records)
        durable(status_path, output)
        return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--phase", choices=["canary", "remaining"], required=True)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--live", action="store_true", required=True)
    parser.add_argument("--deadline-seconds", type=int, default=900)
    args = parser.parse_args()
    config = json.loads((args.packet / "config.json").read_bytes())
    load_env(args.env_file, config)
    result = execute(args.packet, args.phase, deadline_seconds=args.deadline_seconds)
    print(json.dumps({"phase": result["phase"], "attempted_total": result["attempted_total"],
                      "recorded_total": result["recorded_total"], "stopped_seats": result["stopped_seats"], "budget": result["budget"]}, indent=2))


if __name__ == "__main__":
    main()
