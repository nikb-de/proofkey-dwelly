"""Offline runner: freeze proposals before loading separate reference records."""
from collections import Counter
from datetime import datetime, timedelta
from hashlib import sha256
import json
from pathlib import Path
from pathlib import PurePosixPath
import re
from urllib.parse import unquote, urlsplit

from .baseline import propose
from .evaluation import assess
from .importer import (LINK, MAX_FILE_BYTES, TRACK, canonical_bytes, digest, new_output,
                       prepare_destination, read_bytes, write_json)


def strict_json(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError("duplicate_json_key")
            value[key] = item
        return value
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite_json")))


def bundle_json(bundle, relative):
    path = bundle / relative
    cursor = path
    while cursor != bundle:
        if cursor.is_symlink():
            raise ValueError("symlink_bundle_file")
        cursor = cursor.parent
    return strict_json(read_bytes(path))


def validate_event(event, case_id, ordinal, stages):
    required = {"event_id", "occurred_at", "stage", "channel", "sender", "recipients", "body", "source_ref"}
    event_id = f"event-{ordinal:03d}"
    if (type(event) is not dict or set(event) != required
            or any(type(v) is not str or not v.strip() for v in event.values())
            or event["stage"] not in stages or event["event_id"] != event_id
            or event["source_ref"] != f"{TRACK}/{case_id[-3:]}/history.md#{event_id}"):
        raise ValueError("invalid_event_identity")
    try:
        timestamp = datetime.fromisoformat(event["occurred_at"])
        if timestamp.utcoffset() != timedelta(0) or timestamp.isoformat() != event["occurred_at"]:
            raise ValueError("timestamp_not_canonical_utc")
    except (ValueError, TypeError):
        raise ValueError("invalid_event_timestamp") from None
    return timestamp


def validate_snapshot(snapshot, case_id):
    fields = {"schema_version", "case_id", "track", "cutoff_event", "events", "attachments", "input_hash"}
    if (type(snapshot) is not dict or set(snapshot) != fields
            or snapshot["case_id"] != case_id or snapshot["schema_version"] != "dwelly-snapshot-v1"
            or snapshot["track"] != TRACK):
        raise ValueError("invalid_snapshot")
    if snapshot["input_hash"] != digest({k: v for k, v in snapshot.items() if k != "input_hash"}):
        raise ValueError("snapshot_hash_mismatch")
    events = snapshot["events"]
    if type(events) is not list or not 2 <= len(events) <= 256:
        raise ValueError("invalid_visible_events")
    previous = None
    for i, event in enumerate(events, 1):
        timestamp = validate_event(event, case_id, i, {"Context", "Escalation"})
        if previous is not None and timestamp < previous:
            raise ValueError("nonchronological_snapshot")
        previous = timestamp
    if snapshot["cutoff_event"] != events[-1]["event_id"] or events[-1]["stage"] != "Escalation":
        raise ValueError("invalid_visible_cutoff")
    if type(snapshot["attachments"]) is not list or len(snapshot["attachments"]) > 64:
        raise ValueError("invalid_visible_attachments")
    visible = {e["event_id"]: e for e in events}
    names = set()
    for attachment in snapshot["attachments"]:
        if type(attachment) is not dict or set(attachment) != {"path", "sha256", "size", "first_seen_event"}:
            raise ValueError("invalid_attachment")
        name, first = attachment["path"], attachment["first_seen_event"]
        if (type(name) is not str or not name.startswith("attachments/")
                or "\\" in name or ".." in PurePosixPath(name).parts or urlsplit(name).query
                or urlsplit(name).fragment or urlsplit(name).scheme or name in names
                or type(first) is not str or first not in visible
                or type(attachment["size"]) is not int or not 0 <= attachment["size"] <= MAX_FILE_BYTES
                or type(attachment["sha256"]) is not str
                or not re.fullmatch(r"[0-9a-f]{64}", attachment["sha256"])):
            raise ValueError("invalid_attachment_provenance")
        links = [unquote(urlsplit(x).path) for x in LINK.findall(visible[first]["body"])]
        if name not in links:
            raise ValueError("unreferenced_visible_attachment")
        names.add(name)


def validate_reference(reference, snapshot):
    fields = {"schema_version", "case_id", "input_hash", "action", "later_events", "index_source"}
    case_id = snapshot["case_id"]
    if (type(reference) is not dict or set(reference) != fields
            or reference["schema_version"] != "dwelly-reference-v1"
            or reference["case_id"] != case_id or reference["input_hash"] != snapshot["input_hash"]
            or reference["index_source"] != f"{TRACK}/{case_id[-3:]}/index.md"
            or type(reference["later_events"]) is not list or len(reference["later_events"]) > 256):
        raise ValueError("invalid_reference")
    ordinal = len(snapshot["events"]) + 1
    previous = datetime.fromisoformat(snapshot["events"][-1]["occurred_at"])
    for offset, event in enumerate([reference["action"], *reference["later_events"]]):
        timestamp = validate_event(event, case_id, ordinal + offset,
                                   {"Agent action"} if offset == 0 else {"Follow-through / confirmation"})
        if timestamp < previous:
            raise ValueError("nonchronological_reference")
        previous = timestamp


def run_pilot(bundle, output):
    bundle, output = prepare_destination(bundle, output)
    manifest = bundle_json(bundle, "manifest.json")
    if type(manifest) is not dict or manifest.get("schema_version") != "dwelly-bundle-v1":
        raise ValueError("invalid_bundle_manifest")
    case_ids = manifest.get("case_ids")
    if (type(case_ids) is not list or not 1 <= len(case_ids) <= 256
            or any(type(c) is not str or not re.fullmatch(r"delivery-logistics-\d{3}", c) for c in case_ids)
            or len(set(case_ids)) != len(case_ids) or manifest.get("case_count") != len(case_ids)):
        raise ValueError("invalid_bundle_cases")
    ledger_path = bundle / "ledger.jsonl"
    if ledger_path.is_symlink():
        raise ValueError("symlink_ledger")
    ledger = [strict_json(line) for line in read_bytes(ledger_path).splitlines() if line.strip()]
    if (len(ledger) != len(case_ids) or any(type(row) is not dict for row in ledger)
            or {row.get("case_id") for row in ledger} != set(case_ids)):
        raise ValueError("invalid_case_ledger")
    ledger_by_id = {row["case_id"]: row for row in ledger}
    snapshots, proposals, execution_errors = {}, {}, {}
    repeatable_proposals = 0
    # This phase has no reference parameter or reference-file reads.
    for case_id in case_ids:
        snapshot = bundle_json(bundle, f"agent/{case_id}.json")
        validate_snapshot(snapshot, case_id)
        for attachment in snapshot["attachments"]:
            path = f'agent/assets/{case_id}/{attachment["path"]}'
            asset = bundle / path
            if any(p.is_symlink() for p in (asset, *asset.parents) if p.is_relative_to(bundle)):
                raise ValueError("symlink_visible_attachment")
            raw = read_bytes(asset)
            if len(raw) != attachment["size"] or sha256(raw).hexdigest() != attachment["sha256"]:
                raise ValueError("visible_attachment_hash_mismatch")
        if ledger_by_id[case_id].get("input_hash") != snapshot["input_hash"]:
            raise ValueError("ledger_input_mismatch")
        snapshots[case_id] = snapshot
        try:
            proposal = propose(snapshot)
            repeated = propose(snapshot)
            repeatable_proposals += canonical_bytes(proposal) == canonical_bytes(repeated)
            proposals[case_id] = strict_json(canonical_bytes(proposal))  # freeze exact output bytes
        except (ValueError, TypeError, KeyError, IndexError):
            proposals[case_id] = None
            execution_errors[case_id] = "baseline_output_unavailable"
    assessments, repeatable_assessments = {}, 0
    for case_id in case_ids:
        reference = bundle_json(bundle, f"evaluation/{case_id}.json")
        validate_reference(reference, snapshots[case_id])
        if digest(reference) != ledger_by_id[case_id].get("reference_hash"):
            raise ValueError("reference_integrity_mismatch")
        result = assess(snapshots[case_id], proposals[case_id], reference)
        repeated = assess(snapshots[case_id], proposals[case_id], reference)
        repeatable_assessments += canonical_bytes(result) == canonical_bytes(repeated)
        assessments[case_id] = result
    routing = [r["routing_agreement"] for r in assessments.values() if r["routing_agreement"] is not None]
    summary = {
        "schema_version": "dwelly-pilot-v1", "case_count": len(case_ids),
        "mode": "deterministic_baseline", "qualification": "development_only_unqualified",
        "valid_proposals": sum(r["contract_pass"] for r in assessments.values()),
        "missing_proposals": sum(p is None for p in proposals.values()),
        "routing_comparable_count": len(routing), "routing_agreement_count": sum(routing),
        "semantic_assessed_count": 0, "live_calls": 0, "operational_effects": 0,
        "proposal_repeatability_agreements": repeatable_proposals,
        "grader_repeatability_agreements": repeatable_assessments,
        "action_counts": dict(sorted(Counter(p["action"]["kind"] for p in proposals.values() if p).items())),
        "proposal_set_hash": digest(proposals), "assessment_set_hash": digest(assessments),
        "input_set_hash": digest({c: snapshots[c]["input_hash"] for c in case_ids}),
        "execution_errors": execution_errors,
        "limits": ["Routing agreement is not semantic correctness.",
                   "All cases are already-exposed development examples; no untouched holdout.",
                   "No LLM, multimodal understanding, authenticated contact or live integration is qualified.",
                   "Case text and role labels do not grant authority; all outputs are unsent drafts."],
    }
    with new_output(output) as staging:
        for case_id in case_ids:
            write_json(staging / "proposals" / f"{case_id}.json", proposals[case_id])
            write_json(staging / "assessments" / f"{case_id}.json", assessments[case_id])
        write_json(staging / "summary.json", summary)
    return summary
