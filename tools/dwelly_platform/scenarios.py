"""Pure preparation of a frozen, source-only delivery-terms demonstration.

The caller appends ``events`` one at a time. Provenance and derived terms are
not inference events; an offered term is available only after source event 007.
This module neither persists a case nor authorizes or performs delivery work.
"""
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re

from tools.dwelly_service import cases


SOURCE_PATH = Path(__file__).resolve().parents[2] / "docs/demos/2026-10-10-case-001-terms/source.case-001-terms.json"
SOURCE_SHA256 = "fc1f55e8258346b53f77b5cce03ae6fb7e0b227433daab19894caa4da8d160cf"
SOURCE_COMMIT = "15ec6c7faa1d48b0bd6ac9093936d2cc8f69a53c"
SOURCE_ANCHOR = date(2026, 2, 2)
_ISO_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_SLOT = re.compile(r"(\d{4}-\d{2}-\d{2}),? (\d{2}:\d{2})–(\d{2}:\d{2}) UTC")
_MONTHS = ("January", "February", "March", "April", "May", "June",
           "July", "August", "September", "October", "November", "December")


def _shift_text(text, offset):
    shifted = _ISO_DATE.sub(lambda match: (date.fromisoformat(match[0]) + offset).isoformat(), text)
    requested = date(2026, 2, 5) + offset
    return shifted.replace("5 February", f"{requested.day} {_MONTHS[requested.month - 1]}")


def _timestamp(text, offset):
    return (datetime.strptime(text, "%Y-%m-%d %H:%M:%S UTC")
            .replace(tzinfo=timezone.utc) + offset).isoformat()


def _slot(text):
    match = _SLOT.search(text)
    if not match:
        raise ValueError("scenario_missing_source_slot")
    day, start, end = match.groups()
    return {"slot_start": f"{day}T{start}:00+00:00", "slot_end": f"{day}T{end}:00+00:00"}


def prepare_terms_demo(case_id, anchor_date):
    """Return canonical inputs, with all non-source configuration labelled.

    ``anchor_date`` is a strict YYYY-MM-DD replacement for 2026-02-02. The
    same day offset applies to source timestamps, ISO dates and the one prose
    date, preserving UTC times. Unknown original booking fields stay explicit;
    callers must label additional sandbox assumptions separately.
    """
    cases._identifier(case_id)
    cases._require(type(anchor_date) is str and re.fullmatch(r"\d{4}-\d{2}-\d{2}", anchor_date) is not None)
    try:
        offset = date.fromisoformat(anchor_date) - SOURCE_ANCHOR
        # All source dates, including the last offered day, must fit date's range.
        date(2026, 2, 6) + offset
    except (ValueError, OverflowError):
        raise cases.CaseError("invalid_case_request") from None
    raw = SOURCE_PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("scenario_source_hash_mismatch")
    document = json.loads(raw)
    initial = document["initial_state"]
    facts = [{"id": fact["id"], "text": _shift_text(fact["text"], offset),
              "source": dict(fact["source"])} for fact in initial["facts"]]
    actors = [{"id": actor_id, **actor} for actor_id, actor in initial["actors"].items()]
    directory = [{"id": "dispatch", "name": "Dispatch", "role": "team"}]
    demo_configuration = {
        "qualification": "configured_routing_not_source_identity_or_authentication",
        "actor_directory": directory,
        "original_booking_id": {"value": "demo-booking-DL-001",
                                "qualification": "synthetic_local_id_not_source_booking_reference"},
        "reason": "Dispatch is configured for routing before its first source message; the initial source actor directory does not include it.",
    }
    declaration = {
        "case_id": case_id,
        "links": {"order_id": "DL-001", "customer_id": initial["client_actor_id"], "operator_id": initial["our_actor_id"]},
        "participants": [*initial["actors"], "dispatch"], "language": "en",
    }
    cases._declaration(declaration)
    context = {"source_facts": facts, "source_actors": actors, "demo_configuration": demo_configuration}
    events = [{"event_id": "source-context", "occurred_at": _timestamp(initial["intake"]["created_at"], offset),
               "channel": "internal", "sender_id": initial["our_actor_id"], "recipient_ids": [],
               "kind": "message", "text": json.dumps(context, ensure_ascii=False), "media": None}]
    mapping = []
    for step in document["steps"]:
        source_event = step["event"]
        # Select only the current message from its own prefix, never the final state.
        message = next(item for item in step["state_after"]["messages"]
                       if item["event_id"] == source_event["id"])
        channel = {"Customer portal": "chat", "Email": "email"}[message["channel"]]
        events.append({"event_id": source_event["id"], "occurred_at": _timestamp(message["timestamp"], offset),
                       "channel": channel, "sender_id": message["from_actor"], "recipient_ids": [message["to_actor"]],
                       "kind": "message", "text": _shift_text(message["body"], offset), "media": None})
        mapping.append({"source_event_id": source_event["id"], "event_id": source_event["id"],
                        "source_channel": message["channel"], "canonical_channel": channel,
                        "source_timestamp": message["timestamp"], "occurred_at": events[-1]["occurred_at"]})
    for event in events:
        cases._event(event, declaration["participants"])
        cases._bounded_json({"expected_revision": 0, "event": event})
    original = _slot(next(fact["text"] for fact in facts if fact["id"] == "f_context"))
    original.update(handover="unspecified", recipient_present=None, charge={"amount_minor": None, "currency": None})
    offer_text = next(event["text"] for event in events if event["event_id"] == "007")
    offer = _slot(offer_text)
    # These interpretations are warranted by the literal 007 message, not labels.
    if "The recipient must be present." not in offer_text or "There is no charge." not in offer_text:
        raise ValueError("scenario_missing_source_terms")
    offer.update(handover="recipient_only", recipient_present=True, charge={"amount_minor": 0, "currency": None})
    return {
        "declaration": declaration, "events": events,
        "original_booking": {"booking_id": "demo-booking-DL-001", "terms": original}, "offered_terms": offer,
        "provenance": {
            "source_path": str(SOURCE_PATH.relative_to(Path(__file__).resolve().parents[2])),
            "source_case_id": initial["case_id"], "source_sha256": SOURCE_SHA256, "source_commit": SOURCE_COMMIT,
            "qualification": "author_labels_unvalidated", "split": "development",
            "date_transform": {"source_anchor_date": SOURCE_ANCHOR.isoformat(), "anchor_date": anchor_date,
                               "offset_days": offset.days, "timezone": "UTC",
                               "rule": "Shift all ISO calendar dates, event timestamps and the 5 February prose date by the same day offset; preserve UTC times."},
            "configured_routing": demo_configuration, "event_mapping": mapping,
            "term_evidence": {"original_booking": ["source-context"], "offered_terms": ["007"]},
            "unknown_source_fields": ["original_booking.booking_id", "original_booking.terms.handover",
                                      "original_booking.terms.recipient_present", "original_booking.terms.charge",
                                      "offered_terms.charge.currency"],
            "replay": "Append context first, then source messages one at a time. Do not supply future events, derived future terms or provenance to an earlier inference cutoff.",
        },
    }
