"""Frozen-input API experiments. Every output is an unsent, unqualified draft."""
from contextlib import ExitStack
from copy import deepcopy
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re

from tools.dwelly_cases import runner as cases
from tools.dwelly_cases.baseline import propose
from tools.dwelly_cases.importer import canonical_bytes, digest, prepare_destination, read_bytes
from .budget import BudgetLedger, positive_decimal, sync_directory
from .cloud_guard import reject_live_cloud
from .parallel import dispatch
from . import providers, semantic


def _validate_config(config):
    fields = {"proposer", "judges", "budget_per_model_usd", "max_output_tokens", "timeout_seconds"}
    seat_fields = {"provider", "model", "api_key_env", "input_usd_per_million", "output_usd_per_million"}
    if type(config) is not dict or set(config) != fields:
        raise ValueError("invalid_config")
    cap = positive_decimal(config["budget_per_model_usd"], "budget")
    if cap > 25:
        raise ValueError("budget_above_25_usd")
    if type(config["max_output_tokens"]) is not int or not 1 <= config["max_output_tokens"] <= 65536:
        raise ValueError("invalid_max_output_tokens")
    timeout = config["timeout_seconds"]
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 600:
        raise ValueError("invalid_timeout_seconds")
    judges = config["judges"]
    if type(judges) is not list or len(judges) != 3:
        raise ValueError("exactly_three_judges_required")
    rates = {}
    for seat in [config["proposer"], *judges]:
        if (type(seat) is not dict or not seat_fields <= set(seat)
                or set(seat) - seat_fields - {"workspace_id_env"}):
            raise ValueError("invalid_provider_config")
        if seat["provider"] not in {"openai", "anthropic", "gemini"}:
            raise ValueError("unsupported_provider")
        if (type(seat["model"]) is not str or not seat["model"].strip() or len(seat["model"]) > 256
                or any(ord(c) < 32 for c in seat["model"])):
            raise ValueError("invalid_model")
        if type(seat["api_key_env"]) is not str or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", seat["api_key_env"]):
            raise ValueError("invalid_api_key_env")
        if "workspace_id_env" in seat:
            if (seat["provider"] != "anthropic" or type(seat["workspace_id_env"]) is not str
                    or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", seat["workspace_id_env"])):
                raise ValueError("invalid_workspace_id_env")
        pair = (positive_decimal(seat["input_usd_per_million"], "input_price"),
                positive_decimal(seat["output_usd_per_million"], "output_price"))
        key = (seat["provider"], seat["model"])
        if key in rates and rates[key] != pair:
            raise ValueError("inconsistent_model_prices")
        rates[key] = pair
    if {s["provider"] for s in judges} != {"openai", "anthropic", "gemini"}:
        raise ValueError("three_distinct_judge_providers_required")


def preflight(config):
    """Check configuration and environment-key names; never fetch key values."""
    _validate_config(config)
    names = sorted({seat["api_key_env"] for seat in [config["proposer"], *config["judges"]]})
    missing = [name for name in names if name not in os.environ]
    workspace_names = sorted({seat["workspace_id_env"] for seat in [config["proposer"], *config["judges"]]
                              if "workspace_id_env" in seat})
    missing_workspace = [name for name in workspace_names if name not in os.environ]
    return {"ready": not missing and not missing_workspace, "missing_credentials": missing,
            "credential_presence": {name: name in os.environ for name in names},
            "missing_workspace_config": missing_workspace,
            "workspace_config_presence": {name: name in os.environ for name in workspace_names},
            "network_checked": False, "billing_checked": False,
            "note": "Presence only; key/workspace values, permissions, expiration and billing are not validated."}


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(canonical_bytes(value) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    sync_directory(path.parent)


def _error_code(error):
    if isinstance(error, providers.ProviderError):
        code = error.code
        if re.fullmatch(r"(?:http_[0-9]{3}|invalid_config|missing_api_key|invalid_api_key|missing_workspace_id|invalid_workspace_id|timeout|network_error|response_too_large|invalid_response|incomplete_response|missing_text)", code):
            return code
        return "provider_error"
    if isinstance(error, TimeoutError):
        return "timeout"
    if isinstance(error, ValueError) and error.args and error.args[0] in {"budget_exhausted", "duplicate_request"}:
        return error.args[0]
    return "invalid_output" if isinstance(error, (ValueError, TypeError, KeyError)) else "request_failed"


def _model_json(text):
    """Decode model text, allowing one complete outer JSON Markdown fence."""
    if not isinstance(text, str):
        raise ValueError("invalid_model_json")
    text = text.strip()
    if text.startswith("```"):
        fenced = re.fullmatch(r"```json\r?\n(.*)\r?\n```", text, re.DOTALL)
        if fenced is None:
            raise ValueError("invalid_model_json_fence")
        text = fenced.group(1)
    return cases.strict_json(text)


def _baseline_candidate(baseline):
    return {"action": baseline["action"], "evidence_refs": baseline["evidence_refs"],
            "rationale": "Draft based on the visible communication context.",
            "missing_information": [], "required_approvals": ["Operator review before sending."]}


def _envelope(snapshot, candidate, mode):
    return {"schema_version": "dwelly-model-proposal-v1", "case_id": snapshot["case_id"],
            "input_hash": snapshot["input_hash"], "status": "proposed_unsent", "effects": [],
            "mode": mode, **candidate}


def _load_inputs(bundle, limit):
    manifest = cases.bundle_json(bundle, "manifest.json")
    if type(manifest) is not dict or manifest.get("schema_version") != "dwelly-bundle-v1":
        raise ValueError("invalid_bundle_manifest")
    ids = manifest.get("case_ids")
    if (type(ids) is not list or not 1 <= len(ids) <= 256 or manifest.get("case_count") != len(ids)
            or any(type(c) is not str or not re.fullmatch(r"delivery-logistics-\d{3}", c) for c in ids)
            or len(set(ids)) != len(ids)):
        raise ValueError("invalid_bundle_cases")
    ledger_path = bundle / "ledger.jsonl"
    if ledger_path.is_symlink():
        raise ValueError("symlink_ledger")
    rows = [cases.strict_json(line) for line in read_bytes(ledger_path).splitlines() if line.strip()]
    if len(rows) != len(ids) or any(type(row) is not dict for row in rows):
        raise ValueError("invalid_case_ledger")
    ledger = {row.get("case_id"): row for row in rows}
    if set(ledger) != set(ids):
        raise ValueError("invalid_case_ledger")
    snapshots = {}
    for case_id in ids[:limit]:
        snapshot = cases.bundle_json(bundle, f"agent/{case_id}.json")
        cases.validate_snapshot(snapshot, case_id)
        if ledger[case_id].get("input_hash") != snapshot["input_hash"]:
            raise ValueError("ledger_input_mismatch")
        for attachment in snapshot["attachments"]:
            path = bundle / "agent/assets" / case_id / attachment["path"]
            if any(p.is_symlink() for p in (path, *path.parents) if p.is_relative_to(bundle)):
                raise ValueError("symlink_visible_attachment")
            raw = read_bytes(path)
            if len(raw) != attachment["size"] or sha256(raw).hexdigest() != attachment["sha256"]:
                raise ValueError("visible_attachment_hash_mismatch")
        snapshots[case_id] = snapshot
    return snapshots, ledger


def run_experiment(bundle, output, config, *, live=False, limit=50, include_reference=True,
                   compare_baseline=True, repeat_judges=0, max_parallel_requests=1,
                   per_provider_limit=1, proposals_only=False, cancel_requested=None,
                   shared_budget_path=None):
    """Write an exclusive, non-resumable experiment; never send a business action."""
    checked = preflight(config)
    if any(type(value) is not bool for value in (live, include_reference, compare_baseline, proposals_only)):
        raise ValueError("invalid_mode")
    if type(limit) is not int or not 1 <= limit <= 50:
        raise ValueError("invalid_limit")
    if type(repeat_judges) is not int or not 0 <= repeat_judges <= 10:
        raise ValueError("invalid_repeat_judges")
    if type(max_parallel_requests) is not int or not 1 <= max_parallel_requests <= 16:
        raise ValueError("invalid_max_parallel_requests")
    if type(per_provider_limit) is not int or not 1 <= per_provider_limit <= 8:
        raise ValueError("invalid_per_provider_limit")
    if cancel_requested is not None and not callable(cancel_requested):
        raise ValueError("invalid_cancel_requested")
    cancelled = False

    def cancellation_requested():
        nonlocal cancelled
        if not cancelled and cancel_requested is not None:
            value = cancel_requested()
            if type(value) is not bool:
                raise ValueError("invalid_cancel_result")
            cancelled = value
        return cancelled

    cancellation_requested()
    reject_live_cloud(live)
    config = deepcopy(config)
    if live and config["proposer"]["api_key_env"] not in os.environ:
        raise ValueError("missing_proposer_credential")
    bundle, output = prepare_destination(bundle, output)
    if shared_budget_path is not None:
        shared_budget_path = Path(shared_budget_path).resolve()
        if shared_budget_path == output / "budget.jsonl":
            raise ValueError("shared_budget_must_be_separate")
    snapshots, input_ledger = _load_inputs(bundle, limit)
    # mkdir is the exclusive experiment lock. A failed/crashed run remains reserved.
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir(mode=0o700)
    sync_directory(output.parent)
    mode = "live_api" if live else "offline_dry_run"
    state = {"schema_version": "dwelly-model-experiment-v1", "mode": mode,
             "qualification": "development_only_unqualified", "case_count": len(snapshots),
             "live_calls": 0, "operational_effects": 0, "execution_errors": {},
             "include_reference": include_reference, "compare_baseline": compare_baseline,
             "repeat_judges": repeat_judges, "preflight": checked,
             "max_parallel_requests": max_parallel_requests, "per_provider_limit": per_provider_limit,
             "proposals_only": proposals_only,
             "same_provider_judge_relationship": [s["provider"] for s in config["judges"]
                                                   if s["provider"] == config["proposer"]["provider"]]}
    _write(output / "config.json", config)
    # Immutable start evidence; summary.json or failure.json carries terminal status.
    _write(output / "manifest.json", {**state, "status": "running", "record_type": "experiment_started",
                                       "terminal_records": ["summary.json", "failure.json"]})
    proposals, baselines, primary_seats, all_seats = {}, {}, [], []
    try:
        with ExitStack() as stack:
            shared = (stack.enter_context(BudgetLedger(shared_budget_path, config["budget_per_model_usd"]))
                      if shared_budget_path is not None else None)
            budget = stack.enter_context(BudgetLedger(output / "budget.jsonl", config["budget_per_model_usd"]))
            namespace = sha256(str(output).encode("utf-8")).hexdigest()
            completed_requests = set()

            def admit(task):
                seat, system, prompt, request_key = task
                metadata = {"request_key": request_key, "provider": seat["provider"], "requested_model": seat["model"]}
                try:
                    if shared is not None:
                        shared.reserve(seat, system, prompt, config["max_output_tokens"], namespace + ":" + request_key)
                    reservation = budget.reserve(seat, system, prompt, config["max_output_tokens"], request_key)
                except ValueError as error:
                    code = _error_code(error)
                    _write(output / "receipts" / f"{request_key}.json", {**metadata, "status": "not_sent", "error": code})
                    state["execution_errors"][request_key] = code
                    return False
                _write(output / "requests" / f"{request_key}.json", {**metadata, "system": system, "prompt": prompt,
                                                                        "reservation": reservation})
                state["live_calls"] += 1
                return True

            def settle(task, result, error):
                seat, _, _, request_key = task
                metadata = {"request_key": request_key, "provider": seat["provider"], "requested_model": seat["model"]}
                outcome = "error" if error is not None else "received"
                for ledger, key in ((budget, request_key), (shared, namespace + ":" + request_key)):
                    if ledger is not None:
                        ledger.record_outcome(key, outcome, result.get("input_tokens") if result else None,
                                              result.get("output_tokens") if result else None)
                if error is not None:
                    code = _error_code(error)
                    _write(output / "receipts" / f"{request_key}.json", {**metadata, "status": "error", "error": code})
                    state["execution_errors"][request_key] = code
                else:
                    _write(output / "receipts" / f"{request_key}.json", {**metadata, "status": "received", "response": result})
                completed_requests.add(request_key)

            def run_requests(tasks, on_result):
                def finish(task, result, error):
                    settle(task, result, error)
                    on_result(task, result)
                dispatch(tasks, admit=admit, settle=finish, cancelled=cancellation_requested,
                         max_parallel_requests=max_parallel_requests, per_provider_limit=per_provider_limit,
                         max_output_tokens=config["max_output_tokens"], timeout=config["timeout_seconds"])

            # No reference reads or evaluator calls exist in this proposal phase.
            proposal_tasks = []
            for case_id, snapshot in snapshots.items():
                _write(output / "snapshots" / f"{case_id}.json", snapshot)
                baseline = propose(snapshot)
                baselines[case_id] = baseline
                _write(output / "baseline_proposals" / f"{case_id}.json", baseline)
                proposals[case_id] = None if live or cancellation_requested() else baseline
                if live:
                    system, prompt = semantic.proposal_prompt(snapshot)
                    proposal_tasks.append((config["proposer"], system, prompt, f"{case_id}-proposer"))

            def proposal_result(task, response):
                request_key = task[3]
                case_id = request_key.removesuffix("-proposer")
                snapshot = snapshots[case_id]
                if response is not None:
                    try:
                        candidate = semantic.validate_proposal(snapshot, _model_json(response["text"]))
                        proposals[case_id] = _envelope(snapshot, candidate, mode)
                    except (ValueError, TypeError, KeyError, RecursionError, OverflowError):
                        state["execution_errors"][request_key] = "invalid_proposal"
                _write(output / "proposals" / f"{case_id}.json", proposals[case_id])

            run_requests(proposal_tasks, proposal_result)
            for case_id in snapshots:
                if f"{case_id}-proposer" in completed_requests:
                    continue
                _write(output / "proposals" / f"{case_id}.json", proposals[case_id])
            _write(output / "proposals-frozen.json", {"proposal_set_hash": digest(proposals),
                                                       "baseline_set_hash": digest(baselines),
                                                       "input_set_hash": digest({c: s["input_hash"] for c, s in snapshots.items()})})
            # All proposals above are persisted before the first reference file is opened.
            judge_tasks, records, assessments = [], {}, []
            for case_id, snapshot in (() if proposals_only else snapshots.items()):
                reference = None
                if not cancellation_requested():
                    reference = cases.bundle_json(bundle, f"evaluation/{case_id}.json")
                    cases.validate_reference(reference, snapshot)
                    if digest(reference) != input_ledger[case_id].get("reference_hash"):
                        raise ValueError("reference_integrity_mismatch")
                    _write(output / "reference-validation" / f"{case_id}.json", {"reference_hash": digest(reference), "valid": True})
                variants = [("candidate", proposals[case_id])]
                if live and compare_baseline:
                    variants.append(("baseline", _envelope(snapshot, _baseline_candidate(baselines[case_id]), "baseline")))
                for variant, proposal in variants:
                    for repeat in range(repeat_judges + 1):
                        keys = []
                        for index, seat in enumerate(config["judges"]):
                            request_key = f"{case_id}-{variant}-r{repeat}-judge{index}"
                            record = {"provider": seat["provider"], "requested_model": seat["model"],
                                      "status": "missing", "judgment": None, "reason": "offline_dry_run"}
                            if cancellation_requested():
                                record["reason"] = "cancelled"
                            elif live and proposal is None:
                                record["reason"] = "proposal_unavailable"
                            elif live and seat["api_key_env"] not in os.environ:
                                record["reason"] = "missing_credential"
                            elif live:
                                candidate = {key: proposal[key] for key in semantic.PROPOSAL_FIELDS}
                                system, prompt = semantic.judge_prompt(snapshot, candidate,
                                                                     reference["action"] if include_reference else None)
                                judge_tasks.append((seat, system, prompt, request_key))
                                record["reason"] = "cancelled"  # If admission stops before this seat.
                            records[request_key] = (snapshot, record)
                            keys.append(request_key)
                        assessments.append((case_id, variant, repeat, keys))

            def judgment_result(task, response):
                request_key = task[3]
                snapshot, record = records[request_key]
                if response is None:
                    record.update(status="error", reason=state["execution_errors"].get(request_key, "request_failed"))
                    return
                try:
                    judgment = semantic.validate_judgment(snapshot, _model_json(response["text"]))
                    record.update(status="ok", judgment=judgment, reason=None,
                                  observed_model=response.get("observed_model"))
                except (ValueError, TypeError, KeyError, RecursionError, OverflowError):
                    record.update(status="error", reason="invalid_judgment")
                    state["execution_errors"][request_key] = "invalid_judgment"

            run_requests(judge_tasks, judgment_result)
            for task in judge_tasks:
                if task[3] in state["execution_errors"] and task[3] not in completed_requests:
                    judgment_result(task, None)
            for request_key, (_, record) in records.items():
                _write(output / "judgments" / f"{request_key}.json", record)
            for case_id, variant, repeat, keys in assessments:
                seats = [records[key][1] for key in keys]
                all_seats.extend(seats)
                if variant == "candidate" and repeat == 0:
                    primary_seats.extend(seats)
                _write(output / "assessments" / f"{case_id}-{variant}-r{repeat}.json", semantic.aggregate(seats))
            state["proposal_count"] = sum(p is not None for p in proposals.values())
            state["judge_coverage"] = semantic.aggregate(primary_seats)
            state["all_judge_coverage"] = semantic.aggregate(all_seats)
            state["budget"] = budget.summary()
            if shared is not None:
                state["shared_budget"] = shared.summary()
                state["experiment_namespace"] = namespace
            state["proposal_set_hash"] = digest(proposals)
            state["status"] = "cancelled" if cancellation_requested() else "completed"
            state["limits"] = ["Public development examples; no untouched holdout or human quality approval.",
                               "Judges and repeats are uncalibrated assessments, not authorization.",
                               "Local reservations depend on configured prices; provider billing may differ.",
                               "Attachment hashes are validated; models receive metadata, not attachment contents.",
                               "All contacts remain unsent proposals; no business effects are executed."]
            _write(output / "summary.json", state)
            report = ("# Dwelly model experiment\n\n" + f"Mode: {mode}. Status: {state['status']}. Cases: {len(snapshots)}.\n\n"
                      + "`manifest.json` is immutable start evidence; `summary.json` records this terminal result.\n\n"
                      + f"API calls: {state['live_calls']}. Valid proposals: {state['proposal_count']}. "
                      + f"Reserved USD: {state['budget']['reserved_usd']:.6f}.\n\n"
                      + "Primary judge coverage:\n\n```json\n" + json.dumps(state["judge_coverage"], indent=2) + "\n```\n\n"
                      + "\n".join("- " + item for item in state["limits"]) + "\n")
            with (output / "report.md").open("x", encoding="utf-8") as stream:
                stream.write(report)
            return state
    except BaseException as error:
        # Keep all reservations, raw responses and partial proposals for investigation.
        _write(output / "failure.json", {"status": "failed", "error": _error_code(error),
                                         "live_calls": state["live_calls"], "resumable": False})
        raise
