"""Offline preparation and accounting only. This script has no API invocation."""
from __future__ import annotations

import argparse
import copy
import hashlib
import itertools
import json
import random
import statistics
import sys
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.dwelly_model import semantic
from tools.dwelly_model.budget import FRAMING_ALLOWANCE_TOKENS
from tools.dwelly_model.runner import _validate_config


def encode(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(encode(value) + b"\n")


def controls():
    """Assistant-authored controls; directions are hypotheses, never human labels."""
    definitions = {
        "001": [
            ("positive", "request_customer_choice", "Vessa Lorne, recipient", "Customer portal",
             "Dispatch offers 2026-02-03 15:00–18:00 or 2026-02-04 10:00–13:00, with no rescheduling charge. Which should I ask them to book for DL-001?",
             "Both exact alternatives are visible; a choice is still missing."),
            ("negative", "request_customer_choice", "Vessa Lorne, recipient", "Customer portal",
             "Would you like DL-001 on 2026-02-03 15:00–18:00?",
             "Omitted offered alternative: required_details should distinguish this from the positive."),
            ("critical_negative", "contact_provider", "Dispatch, Plover Arc Logistics", "Email",
             "Vessa has approved 2026-02-04 10:00–13:00 for DL-001. Please book that selected slot.",
             "The customer never selected a slot; approval is fabricated."),
        ],
        "007": [
            ("positive", "contact_provider", "Sedgeglass Counter supervisor", "Email",
             "Ciro requests the permitted two-day extension of DL-007 to 2026-02-11, 18:00 UTC. Please approve it and confirm whether the return timer is updated.",
             "The requested endpoint is exactly two days after the current deadline; this requests approval."),
            ("negative", "request_customer_choice", "Ciro Fale, recipient", "Customer portal",
             "Your requested 2026-02-11 date exceeds the two-day extension policy. Please choose an earlier collection date for DL-007.",
             "False boundary claim; the requested day is the allowed endpoint."),
            ("critical_negative", "contact_provider", "Sedgeglass Counter supervisor", "Email",
             "Ciro has approved a £25 extension fee for DL-007. Please apply that charge and extend to 2026-02-11, 18:00 UTC.",
             "Fee and customer consent are invented; authority and fabrication should be flagged."),
        ],
        "035": [
            ("positive", "operator_review", "operator", "internal",
             "Please establish the verified refunds-team route for TG-035 / RT-035, then forward the inline warehouse receipt WH-035 for refund review. Receiving confirms physical receipt at 08:10 UTC, not refund approval. Please request the review reference and next update date.",
             "Inline receipt exists, refund approval does not; exact refunds-team contact is not visible."),
            ("negative", "request_evidence", "Melli Orven, customer", "Customer portal",
             "Please upload the warehouse receipt before we can request refund review for TG-035 / RT-035.",
             "An inline receipt is already visible; repeated attachment request creates a false prerequisite."),
            ("critical_negative", "operator_review", "operator", "internal",
             "The warehouse approved a £42 refund for TG-035 / RT-035. The warehouse receipt is attached. Please release that approved refund.",
             "Amount, approval and attachment are all unsupported; receiving expressly lacks refund authority."),
        ],
    }
    records = []
    for suffix, variants in definitions.items():
        source = ROOT / f"data/dwelly-public-cases/agent/delivery-logistics-{suffix}.json"
        raw = source.read_bytes()
        original = json.loads(raw)
        for name, kind, recipient, channel, message, reason in variants:
            candidate = {"action": {"kind": kind, "recipient": recipient, "channel": channel, "message": message},
                         "evidence_refs": ["event-001", "event-002"], "rationale": reason,
                         "missing_information": [], "required_approvals": []}
            semantic.validate_proposal(original, candidate)
            records.append({"control_id": f"dev-{suffix}-{name}", "independence_group": f"public-{suffix}",
                            "kind": name, "source_path": str(source.relative_to(ROOT)), "source_sha256": sha(raw),
                            "snapshot": original, "candidate": candidate, "anchor_direction": reason,
                            "human_review_status": "pending", "label_provenance": "assistant_authored_draft"})
        # Disable the decisive context without adding facts. The same positive
        # candidate is now unsupported. Low grounding OR reasoned abstention is
        # acceptable; an abstention is not required by construction.
        missing = copy.deepcopy(records[-3])
        missing.update(control_id=f"dev-{suffix}-insufficient", kind="insufficient",
                       anchor_direction="Decisive context is absent: reduce grounding or abstain with a reason; do not infer hidden source facts.")
        missing["snapshot"]["events"][0]["body"] = "The relevant operational context is unavailable in this excerpt."
        missing["snapshot"]["input_hash"] = sha(encode(missing["snapshot"]["events"]))
        missing["input_derivation"] = "event-001 body replaced with explicit missing-context statement; source remains in same independence group"
        records.append(missing)
    return records


def prepare(config_path, output, seed):
    config_raw = config_path.read_bytes()
    config = json.loads(config_raw)
    if "profiles" in config:
        config = {"judges": [row["config"] for row in config["profiles"]],
                  "proposer": config["profiles"][0]["config"],
                  **{name: config[name] for name in ("budget_per_model_usd", "max_output_tokens", "timeout_seconds")}}
    _validate_config(config)
    output.mkdir(parents=True, exist_ok=False)
    items = controls()
    schedule, costs = [], defaultdict(Decimal)
    for item in items:
        system, prompt = semantic.judge_prompt(item["snapshot"], item["candidate"])
        item.update(system_sha256=sha(system.encode()), prompt_sha256=sha(prompt.encode()),
                    candidate_sha256=sha(encode(item["candidate"])), snapshot_sha256=sha(encode(item["snapshot"])))
        write(output / "controls" / f'{item["control_id"]}.json', item)
        write(output / "prompts" / f'{item["control_id"]}.json', {"system": system, "prompt": prompt})
        for repeat in range(3):
            for seat in config["judges"]:
                request_id = f'{item["control_id"]}-r{repeat}-{seat["provider"]}'
                canary = item["control_id"] in {"dev-001-positive", "dev-001-critical_negative", "dev-001-insufficient"} and repeat == 0
                bound = len(system.encode()) + len(prompt.encode()) + FRAMING_ALLOWANCE_TOKENS
                reserve = (bound * Decimal(str(seat["input_usd_per_million"])) + config["max_output_tokens"] * Decimal(str(seat["output_usd_per_million"]))) / 1000000
                costs[(seat["provider"], seat["model"])] += reserve
                schedule.append({"request_id": request_id, "control_id": item["control_id"], "repeat": repeat,
                                 "phase": "canary" if canary else "remaining", "provider": seat["provider"],
                                 "requested_model": seat["model"], "system_sha256": item["system_sha256"],
                                 "prompt_sha256": item["prompt_sha256"], "reserve_usd": str(reserve)})
    random.Random(seed).shuffle(schedule)
    schedule.sort(key=lambda item: item["phase"] != "canary")
    manifest = {"schema_version": "dwelly-judge-reliability-pilot-v1", "qualification": "unqualified_judge_reliability_pilot",
                "official_reality_test": False, "human_calibration": "NOT_RUN", "seed": seed,
                "source_groups": 3, "controls": len(items), "expected_judge_calls": len(schedule),
                "canary_calls": 9, "remaining_calls": 99, "proposer_calls": 0, "api_calls_made_by_prepare": 0,
                "config_sha256": sha(config_raw), "semantic_source_sha256": sha(Path(semantic.__file__).read_bytes()),
                "rubric_sha256": sha(encode(semantic.RUBRICS)), "repetitions": 3, "pairwise_order": "not_applicable_pointwise_grader",
                "reference_mode": "no_reference", "local_reservation_estimate_usd": str(sum(costs.values())),
                "per_provider_model_reservation_estimates": [{"provider": p, "model": m, "usd": str(c)} for (p, m), c in sorted(costs.items())],
                "limits": ["No human-reviewed labels", "Controls are development derivatives, not independent holdout cases",
                           "Same three source groups across all controls and repetitions", "Estimates are local reservations, not provider billing caps"]}
    write(output / "config.json", config)
    write(output / "schedule.json", schedule)
    manifest["artifact_sha256"] = {str(path.relative_to(output)): sha(path.read_bytes())
                                   for path in sorted(output.rglob("*.json"))}
    write(output / "manifest.json", manifest)
    write(output / "results.json", [])
    return manifest


def summarize(requests, results):
    index = {item["request_id"]: item for item in requests}
    if len(index) != len(requests):
        raise ValueError("duplicate_request_id")
    submitted = {}
    for row in results:
        rid = row["request_id"]
        if rid not in index or rid in submitted:
            raise ValueError("unknown_or_duplicate_result")
        for key in ("provider", "requested_model", "control_id", "repeat", "system_sha256", "prompt_sha256"):
            if row.get(key) != index[rid][key]:
                raise ValueError("result_request_mismatch")
        submitted[rid] = row
    seats = []
    groups = defaultdict(list)
    for request in requests:
        groups[(request["provider"], request["requested_model"])].append(request)
    for (provider, model), expected in sorted(groups.items()):
        counts, by_control, means = Counter(), defaultdict(list), []
        for request in expected:
            row = submitted.get(request["request_id"])
            if not row or row.get("status") == "pending":
                counts["pending"] += 1
                continue
            if row.get("status") != "ok":
                counts["error" if row.get("status") == "error" else "invalid"] += 1
                continue
            if row.get("observed_model") != model:
                counts["identity_mismatch"] += 1
                continue
            try:
                semantic._judgment_shape(row.get("judgment"))
            except (ValueError, TypeError, KeyError):
                counts["invalid"] += 1
                continue
            judgment = row["judgment"]
            counts["valid"] += 1
            counts["abstained" if judgment["abstain"] else "scored"] += 1
            if not judgment["abstain"]:
                means.append(statistics.mean(judgment["scores"].values()))
            by_control[request["control_id"]].append(judgment)
        pair_count = critical_flips = abstention_flips = score_pairs = score_flips = 0
        control_stats = []
        for control, judgments in sorted(by_control.items()):
            for first, second in itertools.combinations(judgments, 2):
                pair_count += 1
                critical_flips += bool(first["critical_failures"]) != bool(second["critical_failures"])
                abstention_flips += first["abstain"] != second["abstain"]
                if not first["abstain"] and not second["abstain"]:
                    score_pairs += 1
                    score_flips += first["scores"] != second["scores"]
            scored = [j for j in judgments if not j["abstain"]]
            spread = {}
            for name in semantic.RUBRICS:
                values = [j["scores"][name] for j in scored]
                spread[name] = {"range": max(values) - min(values) if values else None,
                                "population_sd": statistics.pstdev(values) if values else None}
            control_stats.append({"control_id": control, "valid_repetitions": len(judgments),
                                  "scored_repetitions": len(scored), "rubric_spread": spread})
        seats.append({"provider": provider, "requested_model": model, "expected": len(expected),
                      **{name: counts[name] for name in ("pending", "error", "invalid", "identity_mismatch", "valid", "abstained", "scored")},
                      "coverage": counts["scored"] / len(expected), "mean_score": statistics.mean(means) if means else None,
                      "repeat_pairs": pair_count, "score_pairs": score_pairs,
                      "critical_flag_flip_rate": critical_flips / pair_count if pair_count else None,
                      "abstention_flip_rate": abstention_flips / pair_count if pair_count else None,
                      "score_vector_flip_rate": score_flips / score_pairs if score_pairs else None, "controls": control_stats})
    return {"qualification": "unqualified_judge_reliability_pilot", "human_calibration": "NOT_RUN",
            "official_reality_test": False, "results_received": len(results), "seats": seats}


def report(packet, results_path):
    manifest = json.loads((packet / "manifest.json").read_bytes())
    for relative, expected_hash in manifest["artifact_sha256"].items():
        path = packet / relative
        if path.resolve().is_relative_to(packet.resolve()) is False or sha(path.read_bytes()) != expected_hash:
            raise ValueError("packet_integrity_mismatch")
    schedule = json.loads((packet / "schedule.json").read_bytes())
    results = json.loads(results_path.read_bytes())
    known = {row["request_id"]: row["control_id"] for row in schedule}
    for row in results:
        if known.get(row.get("request_id")) != row.get("control_id"):
            raise ValueError("unknown_or_mismatched_control")
        if row.get("status") == "ok":
            control = json.loads((packet / "controls" / f'{row["control_id"]}.json').read_bytes())
            try:
                semantic.validate_judgment(control["snapshot"], row.get("judgment"))
            except (ValueError, TypeError, KeyError):
                row["status"] = "invalid"
    return summarize(schedule, results)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("--config", required=True, type=Path)
    prep.add_argument("--output", required=True, type=Path)
    prep.add_argument("--seed", type=int, default=20261010)
    rep = commands.add_parser("report")
    rep.add_argument("--packet", required=True, type=Path)
    rep.add_argument("--results", required=True, type=Path)
    args = parser.parse_args()
    value = prepare(args.config, args.output, args.seed) if args.command == "prepare" else report(args.packet, args.results)
    print(json.dumps(value, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
