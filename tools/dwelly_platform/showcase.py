"""Read-only presentation bundles from completed local case recordings.

This module reads captured responses; it does not import the platform store,
contact providers, append source messages, or execute coordination commands.
"""
from copy import deepcopy
import argparse
import json
from pathlib import Path
import re

from tools.dwelly_analysis.widget import canonical_hash
from .models import project_snapshot


_MODEL_REVISIONS = (3, 10, 12, 15, 20)
_SCENES = (
    ("request", "customer", 3, 3, ("001",), "Your day changed. Your delivery can too.",
     "A request, in your words", "The recipient asks the desk to move a delivery she cannot attend."),
    ("review", "operator", 11, 10, ("004", "005", "006"), "One conversation. A clear next step.",
     "Operator workspace", "The recorded operator forwards the requested evening window and concierge handover to Dispatch."),
    ("change", "operator", 13, 12, ("007",), "Changed terms need a fresh decision.",
     "Dispatch proposes an alternative", "The alternative is a daytime window, with the recipient present and no charge."),
    ("consent", "customer", 14, None, ("008", "009"), "You decide before we book.",
     "Review the complete offer", "Replay the recorded acceptance to continue. This does not submit a new acceptance."),
    ("confirmed", "customer", 21, 20, ("010", "011"), "Booked. With a receipt to show it.",
     "Local booking confirmation", "The recorded Dispatch readback confirms the local booking. Physical delivery is not confirmed."),
)
_NAMES = {"vessa_lorne": ("Vessa Lorne", "customer"),
          "coordinator": ("Iona Quill", "operator"), "dispatch": ("Dispatch", "dispatch")}
_QUALIFICATION = ("Recorded replay of a synthetic source scenario with rebased dates. "
                  "Operator-reviewed local sandbox; Dispatch readbacks are simulated. "
                  "No new model call, message, booking, or customer acceptance is sent by this replay.")


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _pick(value, fields):
    _require(isinstance(value, dict), "Invalid recorded object")
    return {field: deepcopy(value[field]) for field in fields if field in value}


def _terms(value):
    result = _pick(value, ("slot_start", "slot_end", "handover", "recipient_present"))
    result["charge"] = _pick(value["charge"], ("amount_minor", "currency"))
    return result


def _coordination(value, case_id, snapshot, history):
    _require(value.get("case_id") == case_id and value.get("mode") == "local_sandbox" and
             value.get("external_effects") == 0 and value.get("physical_delivery") == "not_confirmed",
             "Coordination is not a matching local sandbox record")
    revision = value.get("revision")
    _require(type(revision) is int and 0 <= revision <= snapshot["revision"] and revision in history and
             value.get("snapshot_hash") == history[revision]["snapshot"]["snapshot_hash"],
             "Coordination is outside its recorded snapshot cutoff")
    visible = {event["event_id"] for event in history[revision]["snapshot"]["events"]}
    for field in ("offer", "consent", "pending_request", "operation_receipts"):
        records = value.get(field) or []
        if field != "operation_receipts":
            records = [records] if records else []
        _require(isinstance(records, list), "Invalid nested coordination records")
        for record in records:
            _require(isinstance(record, dict) and type(record.get("created_revision")) is int and
                     0 <= record["created_revision"] <= revision and record["created_revision"] in history,
                     "Nested coordination record is outside its recorded cutoff")
            evidence = record.get("evidence_event_ids", [])
            cutoff = (history[record["created_revision"]]["snapshot"]["events"]
                      if field in ("offer", "consent") else None)
            evidence_ids = {event["event_id"] for event in cutoff} if cutoff is not None else visible
            _require(isinstance(evidence, list) and all(isinstance(item, str) for item in evidence) and
                     len(evidence) == len(set(evidence)) and set(evidence) <= evidence_ids,
                     "Nested coordination evidence is outside its recorded cutoff")
    offer = value.get("offer")
    if offer:
        _require(offer.get("terms_hash") == canonical_hash(offer.get("terms")),
                 "Recorded offer terms do not match their hash")
        consent = value.get("consent")
        if consent:
            _require(consent.get("offer_id") == offer.get("offer_id") and
                     consent.get("terms_hash") == offer.get("terms_hash"),
                     "Recorded consent does not match its offer")
        for record in [value.get("pending_request"), *value.get("operation_receipts", [])]:
            if record and record.get("kind") == "booking":
                _require(record.get("terms_hash") == offer.get("terms_hash"),
                         "Recorded booking does not match its offer")
    result = _pick(value, ("case_id", "phase", "version", "revision", "snapshot_hash", "mode",
                           "external_effects", "physical_delivery"))
    booking = value.get("original_booking")
    result["original_booking"] = {"booking_id": booking["booking_id"], "terms": _terms(booking["terms"])} if booking else None
    offer = value.get("offer")
    result["offer"] = _pick(offer, ("offer_id", "terms_hash", "created_revision", "evidence_event_ids")) if offer else None
    if offer:
        result["offer"]["terms"] = _terms(offer["terms"])
    result["consent"] = _pick(value["consent"], ("offer_id", "terms_hash", "created_revision", "evidence_event_ids", "mode", "authenticated")) if value.get("consent") else None
    result["pending_request"] = _pick(value["pending_request"], ("request_id", "kind", "created_revision", "status", "mode", "external_effects", "terms_hash")) if value.get("pending_request") else None
    result["operation_receipts"] = [_pick(receipt, ("request_id", "kind", "created_revision", "status", "mode", "external_effects", "terms_hash", "evidence_event_ids", "confirmed_at")) for receipt in value.get("operation_receipts", [])]
    return result


def _message(event):
    sender = event.get("sender_id")
    _require(sender in _NAMES and event.get("channel") != "internal" and
             event.get("kind") == "message" and isinstance(event.get("text"), str),
             "A showcase message must be recorded external source text")
    name, role = _NAMES[sender]
    return {"event_id": event["event_id"], "sender": name, "sender_id": sender, "role": role,
            "text": event["text"], "time": event["occurred_at"]}


def _model(job, snapshot, case_id):
    source, candidate, model_input = job.get("source", {}), job.get("candidate", {}), job.get("input", {})
    revision, digest = snapshot["revision"], snapshot["snapshot_hash"]
    _require(job.get("case_id") == case_id and job.get("status") == "succeeded" and
             job.get("reference", "missing") is None and job.get("step_index") == revision and
             source == {"case_id": case_id, "kind": "platform_case", "revision": revision, "snapshot_hash": digest},
             "Model receipt does not match the recorded case cutoff")
    projected = project_snapshot(snapshot)
    _require(model_input == projected and
             job.get("input_hash") == projected["input_hash"] == candidate.get("input_hash"),
             "Model input binding does not match its candidate")
    source_ids = {event["event_id"] for event in snapshot["events"]}
    input_ids = {event["event_id"] for event in model_input.get("messages", [])}
    evidence = candidate.get("evidence_event_ids")
    _require(input_ids == source_ids and isinstance(evidence, list) and set(evidence) <= source_ids,
             "Model evidence includes messages outside its recorded cutoff")
    transaction, receipt = job.get("transaction", {}), job.get("receipt", {})
    _require(transaction.get("operational_effects") == 0 and
             isinstance(receipt.get("observed_model"), str) and isinstance(receipt.get("requested_model"), str),
             "Model receipt is missing its identity or local-effect boundary")
    action = candidate.get("next_action", {})
    _require(isinstance(action.get("type"), str) and isinstance(action.get("description"), str),
             "Model proposal is missing")
    return {"run_id": job["run_id"], "case_id": case_id, "model": receipt["observed_model"],
            "requested_model": receipt["requested_model"], "provider": receipt.get("provider"),
            "request_id": receipt.get("request_id"), "status": job["status"],
            "input_hash": job["input_hash"],
            "usage": _pick(receipt.get("usage", {}), ("input_tokens", "output_tokens")),
            "action": action["type"], "description": action["description"],
            "target_actor_id": action.get("target_actor_id"), "evidence_event_ids": deepcopy(evidence),
            "source_revision": revision, "source_snapshot_hash": digest, "advisory_only": True,
            "latency_ms": receipt.get("latency_ms"), "operational_effects": 0,
            "dispatch_attempts": transaction.get("dispatch_attempts"),
            "automatic_retries": transaction.get("automatic_retries")}


def build_showcase(report):
    """Project one passed capture without changing or executing its contents."""
    _require(isinstance(report, dict) and report.get("status") == "passed" and
             report.get("mode") in ("llm", "synthetic") and report.get("external_effects") == 0 and
             report.get("physical_delivery") == "not_confirmed", "A passed local capture is required")
    case_id, mode = report["case_id"], report["mode"]
    provenance = report["provenance"]
    _require(provenance.get("qualification") == "author_labels_unvalidated" and
             re.fullmatch(r"[a-f0-9]{64}", provenance.get("source_sha256", "")) is not None and
             isinstance(provenance.get("date_transform"), dict), "Source provenance is incomplete")
    history = {}
    for exchange in report["http"]:
        detail = exchange.get("response", {}).get("case")
        if not isinstance(detail, dict) or "snapshot" not in detail:
            continue
        snapshot = detail["snapshot"]
        _require(detail.get("case_id") == snapshot.get("case_id") == case_id and
                 snapshot.get("links", {}).get("order_id") == "DL-001" and
                 snapshot.get("links", {}).get("customer_id") == "vessa_lorne" and
                 snapshot.get("links", {}).get("operator_id") == "coordinator" and
                 snapshot.get("revision") == len(snapshot.get("events", [])), "Captured snapshot identity is inconsistent")
        _require(snapshot.get("snapshot_hash") == canonical_hash({key: value for key, value in snapshot.items()
                                                                 if key != "snapshot_hash"}),
                 "Captured snapshot content does not match its hash")
        prior = history.get(snapshot["revision"])
        _require(not prior or prior["snapshot"]["snapshot_hash"] == snapshot["snapshot_hash"],
                 "Conflicting snapshots at a recorded revision")
        history[snapshot["revision"]] = detail
    previous = None
    for revision in sorted(history):
        snapshot = history[revision]["snapshot"]
        if previous is not None:
            _require(snapshot["events"][:previous["revision"]] == previous["events"] and
                     all(snapshot.get(field) == previous.get(field) for field in ("links", "participants", "language")),
                     "Captured snapshots do not preserve their historical source prefix")
            if revision == previous["revision"] + 1:
                _require(snapshot.get("previous_snapshot_hash") == previous["snapshot_hash"],
                         "Captured snapshot hash chain is inconsistent")
        previous = snapshot
    required = {3, 10, 11, 12, 13, 14, 15, 20, 21}
    _require(required <= history.keys(), "A required historical snapshot is missing")
    models = report.get("models", [])
    _require(len(models) == report.get("model_calls") == (5 if mode == "llm" else 0),
             "Model count does not match the capture mode")
    recorded_models = {}
    for job in models:
        revision = job.get("source", {}).get("revision")
        _require(revision in _MODEL_REVISIONS and revision not in recorded_models,
                 "Unexpected or duplicate model cutoff")
        recorded_models[revision] = _model(job, history[revision]["snapshot"], case_id)
    _require(mode != "llm" or set(recorded_models) == set(_MODEL_REVISIONS), "A required model receipt is missing")
    final = report["final"]
    _require(final.get("case_id") == case_id and final.get("snapshot", {}).get("case_id") == case_id,
             "Final case identity does not match")
    final_coordination = _coordination(final["coordination"], case_id, final["snapshot"], history)
    _require(final_coordination.get("phase") == "booking_confirmed", "Final booking is not confirmed locally")
    final_snapshot = final["snapshot"]
    _require(final_snapshot.get("revision") == final_coordination.get("revision") == 21 and
             final_snapshot.get("snapshot_hash") == final_coordination.get("snapshot_hash") ==
             history[21]["snapshot"]["snapshot_hash"] and final_snapshot == history[21]["snapshot"],
             "Final receipt is not bound to the recorded final snapshot")
    offer, consent = final_coordination.get("offer"), final_coordination.get("consent")
    _require(isinstance(offer, dict) and isinstance(consent, dict) and
             consent.get("offer_id") == offer.get("offer_id") and
             consent.get("terms_hash") == offer.get("terms_hash"), "Final booking has no matching recorded consent")
    receipts = [receipt for receipt in final_coordination["operation_receipts"]
                if receipt.get("kind") == "booking" and receipt.get("status") == "confirmed_locally" and
                receipt.get("mode") == "local_sandbox" and receipt.get("external_effects") == 0]
    _require(bool(receipts), "A confirmed local booking receipt is required")
    receipt = receipts[-1]
    _require(receipt.get("request_id") and receipt.get("terms_hash") == final_coordination.get("offer", {}).get("terms_hash") and
             set(receipt.get("evidence_event_ids", [])) <= {e["event_id"] for e in final["snapshot"]["events"]},
             "Booking receipt is not bound to the accepted offer and source")
    scenes = []
    for scene_id, role, revision, model_revision, ids, title, eyebrow, description in _SCENES:
        detail = history[revision]
        # Acceptance 009 is read at its own later cutoff; never insert it into
        # the pre-acceptance review snapshot or show its model as current.
        visible = {event["event_id"]: event for event in detail["snapshot"]["events"]}
        acceptance = None
        if scene_id == "consent":
            later = {event["event_id"]: event for event in history[15]["snapshot"]["events"]}
            _require("009" in later, "Recorded acceptance is missing")
            acceptance = _message(later["009"])
        message_ids = ids[:-1] if scene_id == "consent" else ids
        _require(all(identifier in visible for identifier in message_ids), "Scene source is outside its cutoff")
        coordination = _coordination(detail["coordination"], case_id, detail["snapshot"], history)
        scene = {"id": scene_id, "role": role, "phase": coordination["phase"], "title": title,
                 "eyebrow": eyebrow, "description": description,
                 "messages": [_message(visible[identifier]) for identifier in message_ids],
                 "model": deepcopy(recorded_models.get(model_revision)), "coordination": coordination,
                 "qualification": _QUALIFICATION, "source_event_ids": list(ids),
                 "snapshot_revision": revision, "snapshot_hash": detail["snapshot"]["snapshot_hash"]}
        if acceptance:
            scene["acceptance_message"] = acceptance
            scene["post_acceptance_model"] = deepcopy(recorded_models.get(15))
        scenes.append(scene)
    requested = next(event for event in history[11]["snapshot"]["events"] if event["event_id"] == "005")
    slot = re.search(r"(\d{4}-\d{2}-\d{2}),? (\d{2}:\d{2})–(\d{2}:\d{2}) UTC", requested["text"])
    _require(slot is not None and "concierge can take" in requested["text"], "Requested source terms are unsupported")
    day, start, end = slot.groups()
    return {"schema_version": "proofkey-showcase-v1", "mode": mode, "case_id": case_id,
            "order_id": "DL-001", "customer_name": "Vessa Lorne", "item": "Desk lamp",
            "source": {"sha256": provenance["source_sha256"], "path": provenance["source_path"],
                       "qualification": provenance["qualification"], "date_transform": deepcopy(provenance["date_transform"])},
            "original_terms": _terms(history[3]["coordination"]["original_booking"]["terms"]),
            "requested_terms": {"slot_start": f"{day}T{start}:00+00:00", "slot_end": f"{day}T{end}:00+00:00",
                                "handover": "concierge_allowed", "recipient_present": False,
                                "charge": {"amount_minor": None, "currency": None}},
            "offered_terms": _terms(history[13]["coordination"]["offer"]["terms"]), "scenes": scenes,
            "model_receipts": [deepcopy(recorded_models[revision]) for revision in _MODEL_REVISIONS if revision in recorded_models],
            "receipt": {"booking_confirmed": True, "external_effects": 0,
                        "physical_delivery": "not_confirmed", "request_id": receipt["request_id"]}}


def load_showcase(report_path):
    """Read a local recording file into the sanitized presentation contract."""
    path = Path(report_path)
    _require(path.stat().st_size <= 16 * 1024 * 1024, "Capture report exceeds 16 MiB")
    return build_showcase(json.loads(path.read_text(encoding="utf-8")))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        _require(args.report.resolve() != args.output.resolve(), "Output must not replace the source capture")
        bundle = load_showcase(args.report)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as destination:
            json.dump(bundle, destination, ensure_ascii=False, allow_nan=False, indent=2)
            destination.write("\n")
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
