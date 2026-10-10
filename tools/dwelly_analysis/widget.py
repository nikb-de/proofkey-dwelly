"""Validate authored snapshots and project only evidence into inference input.

Reference labels are deliberately handled by a separate function. Neither the
source digest nor authored agent state belongs to the inference contract.
"""
import copy
import hashlib
import json
import math

MAX_BYTES = 5 * 1024 * 1024
MAX_DEPTH = 64
MAX_NODES = 100000
INPUT_SCHEMA = "proofkey-step-input-v1"
EXCLUSIONS = ["agent_state", "status", "next_step", "result", "facts", "requests",
              "decision", "explanation", "annotations", "responsibility",
              "success_criteria", "constraints", "future_events"]


def check_json(value):
    """Bound even already-decoded Python values; reject non-JSON types/cycles."""
    stack = [(value, 0)]
    nodes = 0
    while stack:
        item, depth = stack.pop()
        nodes += 1
        if nodes > MAX_NODES or depth > MAX_DEPTH:
            raise ValueError("JSON resource limit exceeded")
        kind = type(item)
        if kind is dict:
            if any(type(k) is not str for k in item):
                raise ValueError("JSON keys must be strings")
            stack.extend((v, depth + 1) for v in item.values())
        elif kind is list:
            stack.extend((v, depth + 1) for v in item)
        elif kind is float:
            if not math.isfinite(item):
                raise ValueError("Non-finite JSON number")
        elif kind not in (str, int, bool, type(None)):
            raise ValueError("Unsupported JSON value")
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (ValueError, UnicodeError, OverflowError, RecursionError) as exc:
        raise ValueError("Invalid JSON encoding") from exc
    if len(encoded) > MAX_BYTES:
        raise ValueError("JSON byte limit exceeded")


def canonical_hash(value):
    check_json(value)
    data = json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _object(value):
    if type(value) is not dict:
        raise ValueError("Expected object")
    return value


def _array(value):
    if type(value) is not list:
        raise ValueError("Expected array")
    return value


def _string(value, allow_empty=False):
    if type(value) is not str or (not allow_empty and not value):
        raise ValueError("Expected string")
    return value


def _optional_strings(value, keys):
    for key in keys:
        if key in value:
            _string(value[key], allow_empty=True)


def _validate_state(state, visible_ids):
    _object(state)
    actors = _object(state.get("actors"))
    for actor_id, actor in actors.items():
        _string(actor_id)
        _object(actor)
        _string(actor.get("name"))
        _string(actor.get("role"))
        _optional_strings(actor, ("responsibility",))
        if "organization" in actor and actor["organization"] is not None:
            _string(actor["organization"], allow_empty=True)
        if "is_us" in actor and type(actor["is_us"]) is not bool:
            raise ValueError("Invalid actor flag")
    ours = _string(state.get("our_actor_id"))
    if ours not in actors:
        raise ValueError("Unknown our actor")
    if state.get("client_actor_id") is not None:
        if _string(state["client_actor_id"]) not in actors:
            raise ValueError("Unknown client actor")
    _string(state.get("goal"))
    agent = _object(state.get("agent_state"))
    status = agent.get("status")
    if status not in ("ready", "acting", "waiting", "completed"):
        raise ValueError("Invalid agent state")
    waiting = _array(agent.get("waiting_for"))
    for target in waiting:
        _object(target)
        if _string(target.get("actor_id")) not in actors:
            raise ValueError("Unknown wait target")
        _string(target.get("expected"))
        _optional_strings(target, ("request_id",))
    if "next_action" in agent and agent["next_action"] is not None:
        _string(agent["next_action"], allow_empty=True)
    if (status == "waiting") != bool(waiting):
        raise ValueError("Inconsistent waiting state")
    criteria = _array(state.get("success_criteria"))
    criterion_ids = set()
    for criterion in criteria:
        _object(criterion)
        _string(criterion.get("id")); _string(criterion.get("description"))
        if criterion["id"] in criterion_ids:
            raise ValueError("Duplicate criterion")
        criterion_ids.add(criterion["id"])
        if criterion.get("status") not in ("pending", "met"):
            raise ValueError("Invalid criterion status")
        for evidence_id in _array(criterion.get("evidence_event_ids")):
            if _string(evidence_id) not in visible_ids:
                raise ValueError("Future or unknown criterion evidence")
        if criterion["status"] == "met" and not criterion["evidence_event_ids"]:
            raise ValueError("Met criterion requires evidence")
    if status == "completed" and (not criteria or any(c["status"] != "met" for c in criteria)
                                  or agent.get("next_action") is not None):
        raise ValueError("Inconsistent completed state")
    message_ids = set()
    for message in _array(state.get("messages")):
        _object(message)
        event_id = _string(message.get("event_id"))
        if event_id not in visible_ids or event_id in message_ids:
            raise ValueError("Future, duplicate or unknown message")
        message_ids.add(event_id)
        for field in ("from_actor", "to_actor"):
            if _string(message.get(field)) not in actors:
                raise ValueError("Unknown message actor")
        if "body" not in message and "body_ru" not in message:
            raise ValueError("Missing message body")
        _optional_strings(message, ("body", "body_ru", "timestamp", "channel", "conversation_id"))
    for annotation in _array(state.get("annotations", [])):
        _object(annotation); _string(annotation.get("text"), allow_empty=True)
        _optional_strings(annotation, ("id", "kind", "title", "before_message_id"))
        if "source_event_ids" in annotation:
            for evidence_id in _array(annotation["source_event_ids"]):
                if _string(evidence_id) not in visible_ids:
                    raise ValueError("Future or unknown annotation evidence")
    return state


def validate_document(document):
    """Fail closed for malformed, oversized, or internally inconsistent sources."""
    check_json(document)
    _object(document)
    if document.get("schema_version") != "case-step-viewer/1.0":
        raise ValueError("Unsupported source schema")
    _string(document.get("title"))
    _optional_strings(document, ("initial_explanation",))
    steps = _array(document.get("steps"))
    if len(steps) > 1000:
        raise ValueError("Too many steps")
    seen = set()
    previous = _validate_state(document.get("initial_state"), seen)
    for step in steps:
        _object(step)
        _string(step.get("explanation"), allow_empty=True)
        event = _object(step.get("event"))
        event_id = _string(event.get("id"))
        if event_id in seen:
            raise ValueError("Duplicate event")
        seen.add(event_id)
        _string(event.get("title"))
        _optional_strings(event, ("label", "timestamp", "actor_id", "message_id"))
        kind = event.get("type")
        if kind not in ("message_sent", "message_received", "action", "state_changed"):
            raise ValueError("Unknown event type")
        state = _validate_state(step.get("state_after"), seen)
        prior_messages = previous["messages"]
        if state["messages"][:len(prior_messages)] != prior_messages:
            raise ValueError("Message history is not an immutable prefix")
        previous = state
        if kind in ("message_sent", "message_received"):
            matches = [m for m in state["messages"] if m["event_id"] == event.get("message_id", event_id)]
            if len(matches) != 1 or matches[0]["event_id"] != event_id:
                raise ValueError("Event has no matching message")
            message = matches[0]
            outgoing = message["from_actor"] == state["our_actor_id"]
            incoming = message["to_actor"] == state["our_actor_id"]
            if (kind == "message_sent" and (not outgoing or incoming)) or (
                    kind == "message_received" and (not incoming or outgoing)):
                raise ValueError("Invalid message direction")
            if "actor_id" in event and event["actor_id"] != message["from_actor"]:
                raise ValueError("Event actor mismatch")
    return document


def _select(document, step_index):
    validate_document(document)
    if type(step_index) is not int or not 0 <= step_index <= len(document["steps"]):
        raise ValueError("Invalid step index")
    return document["initial_state"] if step_index == 0 else document["steps"][step_index - 1]["state_after"]


def project(document, step_index, case_id):
    state = _select(document, step_index)
    _string(case_id)
    result = {"schema_version": INPUT_SCHEMA, "case_id": case_id, "step_index": step_index,
              "cutoff_event_id": None if step_index == 0 else document["steps"][step_index - 1]["event"]["id"],
              "goal": document["initial_state"]["goal"], "our_actor_id": state["our_actor_id"],
              "actors": [{"id": key, "name": actor["name"], "role": actor["role"]}
                         for key, actor in state["actors"].items()], "messages": []}
    for message in state["messages"]:
        body_source = "body" if "body" in message else "body_ru"
        item = {key: message[key] for key in ("event_id", "from_actor", "to_actor")}
        item.update(body=message[body_source], body_source=body_source)
        item.update({key: message[key] for key in ("timestamp", "channel", "conversation_id") if key in message})
        result["messages"].append(item)
    result["input_hash"] = canonical_hash(result)
    return result


def validate_input(value):
    check_json(value)
    _object(value)
    fields = {"schema_version", "case_id", "step_index", "cutoff_event_id", "goal",
              "our_actor_id", "actors", "messages", "input_hash"}
    if set(value) != fields or value.get("schema_version") != INPUT_SCHEMA:
        raise ValueError("Unsupported inference input")
    for key in ("case_id", "goal", "our_actor_id", "input_hash"):
        _string(value[key])
    if type(value["step_index"]) is not int or not 0 <= value["step_index"] <= 1000:
        raise ValueError("Invalid input step")
    if value["step_index"] == 0:
        if value["cutoff_event_id"] is not None or value["messages"]:
            raise ValueError("Invalid start input")
    else:
        _string(value["cutoff_event_id"])
    actors = set()
    for actor in _array(value["actors"]):
        _object(actor)
        if set(actor) != {"id", "name", "role"}:
            raise ValueError("Invalid input actor")
        for key in actor: _string(actor[key])
        if actor["id"] in actors:
            raise ValueError("Duplicate input actor")
        actors.add(actor["id"])
    if value["our_actor_id"] not in actors:
        raise ValueError("Unknown our actor")
    ids = set()
    for message in _array(value["messages"]):
        _object(message)
        required = {"event_id", "from_actor", "to_actor", "body", "body_source"}
        if not required <= set(message) or set(message) - required - {"timestamp", "channel", "conversation_id"}:
            raise ValueError("Invalid input message")
        for key in message: _string(message[key], allow_empty=key in ("body", "timestamp", "channel", "conversation_id"))
        if message["body_source"] not in ("body", "body_ru"):
            raise ValueError("Invalid body provenance")
        if message["event_id"] in ids or message["from_actor"] not in actors or message["to_actor"] not in actors:
            raise ValueError("Invalid input message reference")
        ids.add(message["event_id"])
    expected = canonical_hash({k: v for k, v in value.items() if k != "input_hash"})
    if value["input_hash"] != expected:
        raise ValueError("Input hash mismatch")
    return value


def reference(document, step_index, projection):
    """Read labels for comparison only; bind them to an exact projected input."""
    validate_input(projection)
    if projection != project(document, step_index, projection["case_id"]):
        raise ValueError("Reference input binding mismatch")
    state = _select(document, step_index)["agent_state"]
    return {"schema_version": "proofkey-step-reference-v1", "input_hash": projection["input_hash"],
            "qualification": "author_labels_unvalidated", "state": state["status"],
            "waiting_for": [item["actor_id"] for item in state["waiting_for"]],
            "next_action": state.get("next_action"), "source_agent_state": copy.deepcopy(state)}
