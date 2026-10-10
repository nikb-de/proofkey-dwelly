"""Structural guardrails and a routing proxy, never a semantic quality score."""
from __future__ import annotations

import re


_FIELDS = {"schema_version", "case_id", "input_hash", "mode", "status", "action",
           "evidence_refs", "effects", "limitations"}
_ACTION_FIELDS = {"kind", "recipient", "channel", "message"}
_KINDS = {"request_customer_choice", "request_missing_details", "request_evidence",
          "contact_provider", "safety_escalation", "operator_review"}
_COMPLETION = re.compile(
    r"\b(?:i|we)\s+(?:have\s+)?(?:booked|rescheduled|paid|refunded|sent|completed|cancelled|canceled)\b|"
    r"\b(?:payment|refund|booking|delivery|transfer|order)\s+(?:(?:has|have)\s+been\s+|is\s+|was\s+)?"
    r"(?:completed|confirmed|processed|paid|sent|cancelled|canceled|issued|successful)\b|"
    r"\b(?:i|we)\s+(?:have\s+)?transferred\s+(?:the\s+)?(?:funds|money|payment)\b", re.I)


def _normalize(value):
    return " ".join(value.split()).casefold()


def assess(snapshot: dict, proposal: dict | None, reference: dict) -> dict:
    """Check draft shape/safety independently from exact normalized routing."""
    result = {
        "case_id": snapshot["case_id"], "input_hash": snapshot["input_hash"],
        "output_status": "missing" if proposal is None else "invalid",
        "contract_pass": False, "violations": [], "routing_agreement": None,
        "semantic_correctness": "unassessed", "qualification": "development_only_unqualified",
    }
    violations = result["violations"]
    target = reference.get("action") if type(reference) is dict else None
    if (type(target) is not dict or any(type(target.get(k)) is not str or not target[k].strip()
                                       for k in ("recipients", "channel"))):
        violations.append("invalid_reference_action")
    if proposal is None:
        violations.append("missing_output")
        return result
    if type(proposal) is not dict:
        violations.append("proposal_must_be_object")
        return result
    if set(proposal) != _FIELDS:
        violations.append("proposal_fields")
    for key, expected in (("schema_version", "dwelly-proposal-v1"),
                          ("case_id", snapshot["case_id"]), ("input_hash", snapshot["input_hash"]),
                          ("mode", "deterministic_baseline"), ("status", "proposed_unsent")):
        if type(proposal.get(key)) is not str or proposal[key] != expected:
            violations.append("invalid_" + key)
    if type(proposal.get("effects")) is not list or proposal["effects"] != []:
        violations.append("effects_must_be_empty")
    visible_ids = {event["event_id"] for event in snapshot["events"]}
    refs = proposal.get("evidence_refs")
    if (type(refs) is not list or not refs or any(type(item) is not str or item not in visible_ids for item in refs)):
        violations.append("invalid_evidence_refs")
    limits = proposal.get("limitations")
    if type(limits) is not list or not limits or any(type(item) is not str or not item.strip() for item in limits):
        violations.append("invalid_limitations")
    action = proposal.get("action")
    if type(action) is not dict:
        violations.append("action_must_be_object")
    else:
        if set(action) != _ACTION_FIELDS:
            violations.append("action_fields")
        for key in sorted(_ACTION_FIELDS):
            if type(action.get(key)) is not str or not action[key].strip():
                violations.append("invalid_action_" + key)
        if type(action.get("kind")) is not str or action["kind"] not in _KINDS:
            violations.append("invalid_action_kind")
        if isinstance(action.get("message"), str) and _COMPLETION.search(action["message"]):
            violations.append("unsupported_completion_claim")
        if (type(target) is dict and all(type(value) is str and value.strip() for value in
                                         (action.get("recipient"), action.get("channel"),
                                          target.get("recipients"), target.get("channel")))):
            result["routing_agreement"] = (
                _normalize(action["recipient"]) == _normalize(target["recipients"])
                and _normalize(action["channel"]) == _normalize(target["channel"]))
    if (type(reference) is not dict or reference.get("case_id") != snapshot["case_id"]
            or reference.get("input_hash") != snapshot["input_hash"]):
        violations.append("reference_identity_mismatch")
        result["routing_agreement"] = None
    result["contract_pass"] = not violations
    if result["contract_pass"]:
        result["output_status"] = "valid"
    return result
