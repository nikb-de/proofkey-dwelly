"""Pure, bounded policy and honest projections for the local case platform."""
from datetime import datetime

from tools.dwelly_service.cases import CaseError


class PlatformError(CaseError):
    """Platform machine error, preserved by the canonical transaction boundary."""
    def __init__(self, code):
        self.code = code
        ValueError.__init__(self, code)


def require(condition, code="invalid_platform_request"):
    if not condition:
        raise PlatformError(code)


def check_snapshot(snapshot, body):
    require(type(body.get("expected_revision")) is int, "invalid_platform_request")
    require(body["expected_revision"] == snapshot["revision"], "revision_conflict")
    require(body.get("snapshot_hash") == snapshot["snapshot_hash"], "snapshot_conflict")


def action_checks(action, evidence_ids, now):
    checks = []
    def check(name, passed, message):
        checks.append({"name": name, "passed": bool(passed), "message": message})
    supported = action.get("type") == "reschedule_delivery"
    check("supported_action", supported, "Only a local sandbox delivery reschedule can execute.")
    if not supported:
        return checks
    check("visible_evidence", bool(evidence_ids), "At least one visible evidence event is required.")
    check("same_address", action.get("address_change") is False, "The delivery address must remain unchanged.")
    try:
        start = datetime.fromisoformat(action["slot_start"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(action["slot_end"].replace("Z", "+00:00"))
        aware = start.tzinfo is not None and end.tzinfo is not None
        valid = aware and start > now and 0 < (end - start).total_seconds() <= 8 * 3600
    except (KeyError, ValueError, TypeError, AttributeError, OverflowError):
        valid = False
    check("future_bounded_slot", valid, "Use timezone-aware future times with a slot no longer than eight hours.")
    return checks


def project(snapshot, decisions, reviews, actions, assets, model_jobs):
    text = any(event["kind"] == "message" for event in snapshot["events"])
    media = bool(assets) or any(event["kind"] != "message" for event in snapshot["events"])
    evidence = "mixed" if text and media else "text_available" if text else "media_unprocessed" if media else "empty"
    states = {"lifecycle": "new", "evidence": evidence, "analysis": "not_started", "decision": "none",
              "action": "verified" if actions else "none"}
    latest = decisions[-1] if decisions else None
    if latest:
        current = latest["revision"] == snapshot["revision"] and latest["snapshot_hash"] == snapshot["snapshot_hash"]
        states.update(analysis="current" if current else "stale", decision="proposed" if current else "superseded",
                      lifecycle="in_review")
        if current:
            if latest["action"]["type"] == "request_information":
                states["lifecycle"] = "awaiting_information"
            elif latest["action"]["type"] == "operator_review":
                states["lifecycle"] = "in_review"
            elif not all(check["passed"] for check in latest["checks"]):
                states.update(decision="blocked", lifecycle="escalated")
            else:
                states["lifecycle"] = "awaiting_approval"
            matching = [item for item in reviews if item["decision_id"] == latest["decision_id"]]
            if matching:
                approved = matching[-1]["verdict"] == "approve"
                states["decision"] = "approved" if approved else "rejected"
                if not approved:
                    states["lifecycle"] = "escalated"
                elif latest["action"]["type"] == "operator_review":
                    states["lifecycle"] = "in_review"
                elif latest["action"]["type"] == "request_information":
                    states["lifecycle"] = "awaiting_information"
                elif latest["action"]["type"] == "reschedule_delivery" and all(check["passed"] for check in latest["checks"]):
                    states["lifecycle"] = "ready"
                else:
                    states.update(decision="blocked", lifecycle="escalated")
            if any(item["decision_id"] == latest["decision_id"] for item in actions):
                states["lifecycle"] = "resolved"
    return {"schema_version": "proofkey-platform-case-v1", "case_id": snapshot["case_id"], "snapshot": snapshot,
            "states": states, "decisions": decisions, "reviews": reviews, "actions": actions,
            "assets": assets, "model_jobs": model_jobs, "external_effects": 0}


def project_coordination(detail, coordination):
    """Add source freshness without conflating booking with physical delivery."""
    detail["coordination"] = coordination
    states = detail["states"]
    if coordination is None:
        states.update(coordination="not_initialized", coordination_freshness="not_initialized")
        return detail
    snapshot = detail["snapshot"]
    current = (coordination["revision"] == snapshot["revision"] and
               coordination["snapshot_hash"] == snapshot["snapshot_hash"])
    states.update(coordination=coordination["phase"], coordination_freshness="current" if current else "stale")
    latest = detail["decisions"][-1] if detail["decisions"] else None
    current_decision = (latest is not None and latest["revision"] == snapshot["revision"] and
                        latest["snapshot_hash"] == snapshot["snapshot_hash"])
    if not current_decision:
        states["lifecycle"] = ({
            "booked": "in_review", "cancellation_pending": "awaiting_information",
            "awaiting_terms": "awaiting_information", "awaiting_consent": "awaiting_approval",
            "ready_to_book": "ready", "booking_pending": "awaiting_information",
            "booking_confirmed": "resolved", "escalated": "escalated",
        }[coordination["phase"]] if current else "in_review")
    return detail
