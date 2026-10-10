"""Source-bound local coordination attestations; never contacts a carrier."""
from copy import deepcopy
from datetime import datetime
import hashlib
import json
import re
import uuid

from tools.dwelly_service.cases import MAX_TEXT, _canonical, _identifier
from tools.dwelly_analysis import model
from .domain import check_snapshot, require
from .models import project_snapshot


_COMMON = {"command", "expected_revision", "snapshot_hash", "expected_workflow_version"}
_MODEL_FIELDS = {"model_run_id", "model_review_note"}
_PARAMETERS = {
    "initialize": {"dispatch_actor_id", "original_booking"},
    "request_cancellation": {"evidence_event_ids"},
    "confirm_cancellation": {"request_id", "evidence_event_ids"},
    "record_offer": {"terms", "evidence_event_ids"},
    "record_consent": {"offer_id", "terms_hash", "evidence_event_ids"},
    "record_local_acceptance": {"offer_id", "terms_hash", "acknowledged"},
    "request_booking": {"offer_id", "terms_hash"},
    "confirm_booking": {"request_id", "terms_hash", "evidence_event_ids"},
    "escalate": {"reason", "evidence_event_ids"},
}
_PHASES = {
    "request_cancellation": {"booked"}, "confirm_cancellation": {"cancellation_pending"},
    "record_offer": {"awaiting_terms", "awaiting_consent", "ready_to_book"},
    "record_consent": {"awaiting_consent", "ready_to_book"},
    "record_local_acceptance": {"awaiting_consent"},
    "request_booking": {"ready_to_book"}, "confirm_booking": {"booking_pending"},
    "escalate": {"booked", "cancellation_pending", "awaiting_terms", "awaiting_consent", "ready_to_book", "booking_pending"},
}


def _model_context(snapshot, body, resolver):
    """Validate a frozen advisory result, never derive command authority from it."""
    require(callable(resolver), "model_context_unavailable")
    try:
        job = resolver(body["model_run_id"])
    except Exception as error:
        code = ("model_context_stale" if str(error) in {"model_job_binding_mismatch", "snapshot_hash_mismatch"}
                else "model_context_unavailable")
        require(False, code)
    require(type(job) is dict and job.get("status") == "succeeded", "model_context_unavailable")
    require(job.get("run_id") == body["model_run_id"], "invalid_model_context")
    require("reference" in job and job["reference"] is None, "invalid_model_context")
    source = {"kind": "platform_case", "case_id": snapshot["case_id"], "revision": snapshot["revision"],
              "snapshot_hash": snapshot["snapshot_hash"]}
    projected = project_snapshot(snapshot)
    require(job.get("case_id") == snapshot["case_id"] and
            type(job.get("step_index")) is int and job["step_index"] == snapshot["revision"] and
            type(job.get("source")) is dict and type(job["source"].get("revision")) is int and
            job["source"] == source and job.get("input") == projected and
            job.get("input_hash", projected["input_hash"]) == projected["input_hash"], "model_context_stale")
    candidate = job.get("candidate")
    require(type(candidate) is dict and candidate.get("schema_version") == "proofkey-step-candidate-v1",
            "invalid_model_context")
    require(candidate.get("input_hash") == projected["input_hash"], "model_context_stale")
    try:
        validated = model.parse(projected, {"text": _canonical({field: candidate[field] for field in
            ("state", "waiting_for", "next_action", "evidence_event_ids", "uncertainty")})})
    except (ValueError, TypeError, KeyError, RecursionError, OverflowError, UnicodeError):
        require(False, "invalid_model_context")
    require(candidate == validated, "invalid_model_context")
    selected = body.get("evidence_event_ids", [])
    require(type(selected) is list and all(type(item) is str for item in selected) and
            set(selected) <= set(validated["evidence_event_ids"]), "invalid_model_context")
    return {"run_id": job["run_id"], "input_hash": projected["input_hash"],
            "source_revision": snapshot["revision"], "source_snapshot_hash": snapshot["snapshot_hash"],
            "candidate_hash": hashlib.sha256(_canonical(validated).encode("utf-8")).hexdigest(),
            "model_review_note": body["model_review_note"]}


def _terms(value, now, *, historical=False):
    require(type(value) is dict and set(value) == {"slot_start", "slot_end", "handover", "recipient_present", "charge"}, "invalid_terms")
    require(value["handover"] in (("recipient_only", "concierge_allowed", "unspecified") if historical else ("recipient_only", "concierge_allowed")) and
            (type(value["recipient_present"]) is bool or historical and value["recipient_present"] is None),
            "invalid_terms")
    require(value["handover"] != "recipient_only" or value["recipient_present"], "invalid_terms")
    require(value["handover"] != "concierge_allowed" or value["recipient_present"] is False, "invalid_terms")
    charge = value["charge"]
    require(type(charge) is dict and set(charge) == {"amount_minor", "currency"}, "invalid_terms")
    amount, currency = charge["amount_minor"], charge["currency"]
    unknown_original = historical and amount is None and currency is None
    valid_amount = type(amount) is int and amount >= 0
    valid_currency = type(currency) is str and re.fullmatch(r"[A-Z]{3}", currency) is not None
    require(unknown_original or valid_amount and (valid_currency or amount == 0 and currency is None), "invalid_terms")
    try:
        require(all(type(value[field]) is str and len(value[field]) <= 64 for field in ("slot_start", "slot_end")), "invalid_terms")
        start = datetime.fromisoformat(value["slot_start"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(value["slot_end"].replace("Z", "+00:00"))
        require(start.utcoffset() is not None and end.utcoffset() is not None and
                0 < (end - start).total_seconds() <= 8 * 3600 and (historical or start > now), "invalid_terms")
    except (TypeError, ValueError, OverflowError):
        require(False, "invalid_terms")
    return deepcopy(value)


def _evidence(snapshot, ids, actor=None, *, newer_than=None, correlation=(), used=()):
    require(type(ids) is list and 0 < len(ids) <= 128 and all(type(item) is str for item in ids) and
            len(set(ids)) == len(ids), "invalid_coordination_request")
    indexed = {event["event_id"]: (index + 1, event) for index, event in enumerate(snapshot["events"])}
    require(all(item in indexed for item in ids), "evidence_not_found")
    for identifier in ids:
        revision, event = indexed[identifier]
        require(event["kind"] == "message" and event["channel"] != "internal" and
                (actor is None or event["sender_id"] == actor) and
                snapshot["links"]["operator_id"] in event["recipient_ids"], "evidence_actor_mismatch")
        require((newer_than is None or revision > newer_than) and identifier not in used, "evidence_stale")
        # Correlation is literal and bounded, not inferred from a model's assertion.
        require(all(re.search(r"(?<![A-Za-z0-9_-])" + re.escape(token) + r"(?![A-Za-z0-9_-])", event["text"])
                    for token in correlation), "evidence_correlation_mismatch")
    return list(ids)


class CoordinationMixin:
    def _coordination_detail(self, connection, case_id):
        row = connection.execute("SELECT record FROM platform_coordination WHERE case_id=? ORDER BY version DESC LIMIT 1", (case_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def coordination_detail(self, case_id):
        _identifier(case_id)
        with self._transaction() as connection:
            self._history(connection, case_id)
            return self._coordination_detail(connection, case_id)

    def coordination_command(self, case_id, key, body, model_resolver=None):
        with self._request(case_id, "coordination", key, body) as (connection, body, replay, save):
            if replay is not None:
                return replay
            command = body.get("command")
            attached = bool(set(body) & _MODEL_FIELDS)
            if attached:
                require(_MODEL_FIELDS <= set(body) and command not in ("initialize", "record_local_acceptance") and
                        type(body["model_run_id"]) is str and
                        re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", body["model_run_id"]) is not None and
                        type(body["model_review_note"]) is str and body["model_review_note"].strip() and
                        len(body["model_review_note"]) <= 1000,
                        "invalid_model_context")
            require(type(command) is str and command in _PARAMETERS and
                    set(body) == _COMMON | _PARAMETERS[command] | (_MODEL_FIELDS if attached else set()),
                    "invalid_coordination_request")
            require(type(body["expected_workflow_version"]) is int and body["expected_workflow_version"] >= 0,
                    "invalid_coordination_request")
            snapshot = self._history(connection, case_id)[-1]
            check_snapshot(snapshot, body)
            prior = self._coordination_detail(connection, case_id)
            require(body["expected_workflow_version"] == (prior["version"] if prior else 0), "workflow_conflict")
            context = _model_context(snapshot, body, model_resolver) if attached else None
            append_snapshot = snapshot
            now = self._now(connection)
            evidence = []
            if command == "initialize":
                require(prior is None, "coordination_already_initialized")
                dispatch = body["dispatch_actor_id"]
                require(type(dispatch) is str and dispatch in snapshot["participants"] and
                        dispatch not in (snapshot["links"]["customer_id"], snapshot["links"]["operator_id"]),
                        "invalid_coordination_request")
                booking = body["original_booking"]
                require(type(booking) is dict and set(booking) == {"booking_id", "terms"} and
                        type(booking["booking_id"]) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", booking["booking_id"]),
                        "invalid_coordination_request")
                state = {"case_id": case_id, "version": 0, "phase": "booked", "dispatch_actor_id": dispatch,
                         "original_booking": {"booking_id": booking["booking_id"], "terms": _terms(booking["terms"], now, historical=True)},
                         "offer": None, "consent": None, "pending_request": None,
                         "operation_receipts": [], "audit_history": [], "mode": "local_sandbox", "external_effects": 0,
                         "physical_delivery": "not_confirmed"}
            else:
                require(prior is not None, "coordination_not_initialized")
                state = deepcopy(prior)
                # Identity checks precede phase checks so stale offer IDs cannot be
                # mistaken for an acceptable reference merely due to state changes.
                if command in ("record_consent", "record_local_acceptance", "request_booking"):
                    require(state["offer"] is not None and body["offer_id"] == state["offer"]["offer_id"] and
                            body["terms_hash"] == state["offer"]["terms_hash"], "offer_mismatch")
                require(state["phase"] in _PHASES[command], "coordination_transition_blocked")
                used = {item for audit in state["audit_history"] for item in audit["evidence_event_ids"]}
                if command == "request_cancellation":
                    evidence = _evidence(snapshot, body["evidence_event_ids"], snapshot["links"]["customer_id"], used=used)
                    state["pending_request"] = self._coordination_request("cancellation", snapshot)
                    state["phase"] = "cancellation_pending"
                elif command in ("confirm_cancellation", "confirm_booking"):
                    pending = state["pending_request"]
                    require(body["request_id"] == pending["request_id"], "evidence_correlation_mismatch")
                    correlation = [pending["request_id"]]
                    if command == "confirm_booking":
                        require(body["terms_hash"] == pending["terms_hash"], "offer_mismatch")
                        correlation.append(pending["terms_hash"])
                    evidence = _evidence(snapshot, body["evidence_event_ids"], state["dispatch_actor_id"],
                                         newer_than=pending["created_revision"], correlation=correlation, used=used)
                    state["operation_receipts"].append({**pending, "status": "confirmed_locally", "evidence_event_ids": evidence,
                                                         "confirmed_at": now.isoformat(), "external_effects": 0})
                    state["pending_request"] = None
                    state["phase"] = "awaiting_terms" if command == "confirm_cancellation" else "booking_confirmed"
                elif command == "record_offer":
                    evidence = _evidence(snapshot, body["evidence_event_ids"], state["dispatch_actor_id"], used=used)
                    terms = _terms(body["terms"], now)
                    state["offer"] = {"offer_id": uuid.uuid4().hex, "terms": terms,
                                      "terms_hash": hashlib.sha256(_canonical(terms).encode("utf-8")).hexdigest(),
                                      "created_revision": snapshot["revision"] + 1, "evidence_event_ids": evidence}
                    state["consent"] = None
                    state["phase"] = "awaiting_consent"
                elif command == "record_consent":
                    evidence = _evidence(snapshot, body["evidence_event_ids"], snapshot["links"]["customer_id"],
                                         newer_than=state["offer"]["created_revision"], used=used)
                    state["consent"] = {"offer_id": body["offer_id"], "terms_hash": body["terms_hash"],
                                        "evidence_event_ids": evidence, "created_revision": snapshot["revision"] + 1}
                    state["phase"] = "ready_to_book"
                elif command == "record_local_acceptance":
                    require(body["acknowledged"] is True, "invalid_coordination_request")
                    _terms(state["offer"]["terms"], now)
                    simulated_id = "local-acceptance-" + uuid.uuid4().hex
                    notice = ("LOCAL PREVIEW: Simulated customer acceptance, not authenticated customer consent. "
                              "Operator-assisted local preview only. I acknowledge every term of offer " + body["offer_id"] +
                              " with terms hash " + body["terms_hash"] +
                              ". No carrier was contacted. Physical delivery is not confirmed.")
                    append_snapshot, _ = self._append(connection, case_id, simulated_id, {
                        "expected_revision": snapshot["revision"], "event": {
                            "event_id": simulated_id, "occurred_at": now.isoformat(), "channel": "chat",
                            "sender_id": snapshot["links"]["customer_id"],
                            "recipient_ids": [snapshot["links"]["operator_id"]],
                            "kind": "message", "text": notice, "media": None}})
                    evidence = _evidence(append_snapshot, [simulated_id], snapshot["links"]["customer_id"],
                                         newer_than=state["offer"]["created_revision"], used=used)
                    state["consent"] = {"offer_id": body["offer_id"], "terms_hash": body["terms_hash"],
                                        "evidence_event_ids": evidence, "created_revision": append_snapshot["revision"] + 1,
                                        "mode": "local_preview_simulation", "authenticated": False}
                    state["phase"] = "ready_to_book"
                elif command == "request_booking":
                    require(state["consent"] is not None, "consent_required")
                    require(snapshot["revision"] == state["consent"]["created_revision"], "consent_stale")
                    _terms(state["offer"]["terms"], now)
                    state["pending_request"] = self._coordination_request("booking", snapshot, terms_hash=body["terms_hash"])
                    state["phase"] = "booking_pending"
                elif command == "escalate":
                    require(type(body["reason"]) is str and 0 < len(body["reason"].strip()) <= 2048, "invalid_coordination_request")
                    evidence = _evidence(snapshot, body["evidence_event_ids"])
                    state["escalation"] = {"reason": body["reason"], "evidence_event_ids": evidence}
                    state["phase"] = "escalated"
            state["version"] += 1
            audit_id = uuid.uuid4().hex
            audit = {"audit_id": audit_id, "command": command, "version": state["version"],
                     "operator_id": self.operator_identity, "source_revision": snapshot["revision"],
                     "source_snapshot_hash": snapshot["snapshot_hash"], "evidence_event_ids": evidence,
                     "created_at": now.isoformat(), "mode": "local_sandbox", "external_effects": 0,
                     "attestation_scope": "local_operator_attestation_not_customer_or_carrier_authentication"}
            if context is not None:
                audit["model_context"] = context
            if state["pending_request"]:
                audit["request_id"] = state["pending_request"]["request_id"]
            elif "request_id" in body:
                audit["request_id"] = body["request_id"]
            audit_text = {**audit, "phase": state["phase"], "notice": "Local sandbox attestation. No real dispatch or carrier contact. Physical delivery not confirmed."}
            if command == "initialize":
                audit_text["original_booking"] = state["original_booking"]
            if state["offer"]:
                audit_text["offer"] = state["offer"]
            if command == "escalate":
                audit_text["escalation"] = state["escalation"]
            encoded_audit = _canonical(audit_text)
            require(len(encoded_audit) <= MAX_TEXT, "coordination_audit_too_large")
            updated, _ = self._append(connection, case_id, "coordination-audit-" + audit_id, {
                "expected_revision": append_snapshot["revision"], "event": {"event_id": "coord-" + audit_id,
                "occurred_at": now.isoformat(), "channel": "internal", "sender_id": snapshot["links"]["operator_id"],
                "recipient_ids": [], "kind": "message", "text": encoded_audit, "media": None}})
            state["revision"], state["snapshot_hash"] = updated["revision"], updated["snapshot_hash"]
            audit["revision"] = updated["revision"]
            state["audit_history"].append(audit)
            connection.execute("INSERT INTO platform_coordination (case_id,version,record) VALUES (?,?,?)",
                               (case_id, state["version"], _canonical(state)))
            save(state)
            return state

    @staticmethod
    def _coordination_request(kind, snapshot, **fields):
        return {"request_id": uuid.uuid4().hex, "kind": kind, "created_revision": snapshot["revision"] + 1,
                "status": "pending_local_readback", "mode": "local_sandbox", "external_effects": 0, **fields}
