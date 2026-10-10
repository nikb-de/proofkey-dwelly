"""Small evidence-pattern baseline, never an operational executor or label reader."""
import re

from .widget import validate_input


def _unambiguous_completion(text):
    # Match the entire supported message grammar, not scattered affirmative
    # fragments. Any extra assertion (including a later retraction) abstains.
    # Only identifier/address/time slots vary; this is not general semantics.
    text = " ".join(text.split())
    shipment = r"[a-z]+-\d+"
    apartment = r"\d+[a-z]?"
    address = r"\d+ [a-z]+(?: [a-z]+){1,3}, [a-z]+(?: [a-z]+){1,3}"
    applied = (
        rf"your correction request was applied: {shipment} now reads apartment {apartment}, {address}\. "
        r"the address hold is cleared; it has not yet left the depot\."
    )
    saved_once = (
        rf"(?P<shipment>{shipment})'s saved address reads apartment {apartment}, {address}\. "
        r"your \d{2}:\d{2} correction saved before the session closed, and there is one entry\. "
        r"the address hold is cleared\. (?P=shipment) has not left the depot\."
    )
    return bool(re.fullmatch(applied, text) or re.fullmatch(saved_once, text))


def analyze(value):
    validate_input(value)
    result = {"schema_version": "proofkey-step-candidate-v1", "mode": "deterministic_fixture_baseline",
              "input_hash": value["input_hash"], "state": "unknown", "waiting_for": [],
              "next_action": {"type": "operator_review", "target_actor_id": None,
                              "description": "No supported evidence pattern; operator review required."},
              "evidence_event_ids": [], "uncertainty": ["Bounded fixture baseline; author labels are unvalidated."],
              "operational_effects": 0, "live_calls": 0, "physical_delivery": "not_inferred"}
    if not value["messages"]:
        return result
    message = value["messages"][-1]
    text = message["body"].casefold()
    roles = {actor["id"]: actor["role"].casefold() for actor in value["actors"]}
    sender_role = roles[message["from_actor"]]
    goal = value["goal"].casefold()
    address_goal = "адрес" in goal or "address" in goal
    confirmation_goal = "подтвержден" in goal or "confirmation" in goal

    def choose(state, action, target, description, waiting=None):
        result.update(state=state, waiting_for=waiting or [], evidence_event_ids=[message["event_id"]])
        result["next_action"] = {"type": action, "target_actor_id": target, "description": description}
        return result

    # Only an actually visible outgoing request justifies waiting. The text of
    # an inbound report about an earlier submission is not an outgoing message.
    outgoing = message["from_actor"] == value["our_actor_id"]
    apartment_request = address_goal and "please confirm the apartment number" in text
    readback_request = address_goal and "saved address and hold status" in text and "?" in text
    confirmation_request = confirmation_goal and ("подтвердите" in text or "please confirm" in text)
    if outgoing and (apartment_request or readback_request or confirmation_request):
        target = message["to_actor"]
        return choose("waiting", "wait", target, "Wait for the recipient of the observed request.", [target])
    if outgoing:
        return result
    if address_goal and sender_role == "executor" and _unambiguous_completion(text):
        result["uncertainty"].append("Service message supports coordination completion; physical delivery is not inferred.")
        return choose("completed", "infer_goal_completion", None, "Infer the stated address-correction goal is complete from the service confirmation.")
    executors = [actor["id"] for actor in value["actors"] if actor["role"].casefold() == "executor"]
    executor = executors[0] if len(executors) == 1 else None
    if address_goal and "session expired" in text and "may have saved" in text and "no correction reference" in text and executor:
        result["uncertainty"].append("Submission outcome is unknown. Do not resend before a readback confirms the saved state.")
        return choose("ready", "request_readback", executor, "Request saved address and hold status from the service; do not resend the correction.")
    if address_goal and sender_role == "recipient" and re.search(r"\bapartment\s+[0-9]+[a-z]?\b", text) and "please add" in text and executor:
        result["uncertainty"].append("Forwarding is proposed only; no outgoing service request is recorded at this step.")
        return choose("ready", "propose_forwarding", executor, "Propose forwarding the supplied apartment detail to the service for correction and confirmation.")
    return result
