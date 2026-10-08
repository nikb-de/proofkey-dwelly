"""Operation-specific verification of independent authoritative original reads."""
from .contracts import AuthorityReadback, EffectIntent, VerificationResult


_FACTS = {
    "reschedule": {"slot": "scheduling.slot"},
    "register_goods_refusal": {"inventory": "goods.inventory", "quantity": "goods.quantity",
                               "refusal": "goods.refusal"},
    "register_service_refusal": {"refusal": "service.refusal"},
    "create_return": {"inventory": "goods.inventory", "quantity": "goods.quantity",
                      "destination": "returns.destination", "return_status": "returns.status"},
    "send_clarification": {"recipient": "messaging.recipient", "question_id": "messaging.question_id",
                           "status": "messaging.status"},
    "send_status": {"recipient": "messaging.recipient", "status": "messaging.status"},
    "enqueue_handoff": {"packet_id": "operator.packet_id", "packet_revision": "operator.packet_revision",
                        "packet_hash": "operator.packet_hash", "disposition": "operator.handoff_disposition"},
    "transfer_owner": {"transfer_id": "operator.transfer_id", "packet_id": "operator.packet_id",
                       "packet_revision": "operator.packet_revision", "target_owner": "ownership.owner",
                       "state": "ownership.state", "epoch": "ownership.epoch",
                       "state_revision": "ownership.state_revision"},
}
_STAGES = {"reschedule": {"committed"}, "register_goods_refusal": {"committed"},
           "register_service_refusal": {"committed"}, "create_return": {"initiated", "received"},
           "send_clarification": {"sent", "delivered"}, "send_status": {"sent", "delivered"},
           "enqueue_handoff": {"queued"}, "transfer_owner": {"pending", "accepted"}}


def expected_facts(intent):
    """Translate declared postconditions; no broad case-completion alias exists."""
    aliases = _FACTS.get(intent.operation)
    if aliases is None or not intent.postcondition:
        return None
    values = {}
    for key, value in intent.postcondition.items():
        qualified = aliases.get(key, key if key in aliases.values() else None)
        if qualified is None or qualified in values:
            return None
        values[qualified] = value
    args = intent.arguments
    required = {
        "reschedule": {"scheduling.slot": args.get("slot")},
        "register_goods_refusal": {"goods.refusal": "verified", "goods.inventory": args.get("inventory")},
        "register_service_refusal": {"service.refusal": "verified"},
        "create_return": {"goods.inventory": args.get("inventory"), "returns.destination": args.get("destination")},
        "send_clarification": {"messaging.recipient": args.get("recipient"), "messaging.question_id": args.get("question_id")},
        "send_status": {"messaging.recipient": args.get("recipient")},
        "enqueue_handoff": {"operator.packet_id": args.get("packet_id"), "operator.packet_revision": args.get("packet_revision"),
                            "operator.packet_hash": args.get("packet_hash"), "operator.handoff_disposition": "pending"},
        "transfer_owner": {"operator.transfer_id": args.get("transfer_id"), "operator.packet_id": args.get("packet_id"),
                           "operator.packet_revision": args.get("packet_revision")},
    }[intent.operation]
    for key, value in required.items():
        if value is None or key not in values or values[key] != value or type(values[key]) is not type(value):
            return None
    if intent.operation in {"register_goods_refusal", "create_return"}:
        inventory = args.get("inventory")
        if (not isinstance(inventory, dict) or not inventory or any(type(q) is not int or q <= 0 for q in inventory.values())
                or type(values.get("goods.quantity")) is not int or values["goods.quantity"] != sum(inventory.values())):
            return None
    status_key = {"create_return": "returns.status", "send_clarification": "messaging.status",
                  "send_status": "messaging.status", "transfer_owner": "ownership.state"}.get(intent.operation)
    if status_key is not None and values.get(status_key) not in _STAGES[intent.operation]:
        return None
    if intent.operation == "transfer_owner" and values.get("ownership.state") == "accepted":
        if (values.get("ownership.owner") != args.get("target_owner") or type(values.get("ownership.epoch")) is not int
                or intent.ownership_epoch is None or values["ownership.epoch"] != intent.ownership_epoch + 1):
            return None
    elif intent.operation == "transfer_owner":
        if not isinstance(values.get("ownership.owner"), str) or type(values.get("ownership.epoch")) is not int or values["ownership.epoch"] != intent.ownership_epoch:
            return None
    return values


def verify(intent, authoritative_readback):
    intent = EffectIntent.model_validate(intent.model_dump())
    read = AuthorityReadback.model_validate(authoritative_readback.model_dump())

    def result(status, reason, evidence=False):
        return VerificationResult(status=status, object_id=intent.binding.object_id,
            action_id=intent.action_id, fingerprint=intent.argument_fingerprint,
            postcondition=intent.postcondition, evidence_refs=read.evidence_refs if evidence else [],
            as_of=read.as_of if evidence else None, reason=reason)

    pairs = ((read.object_id, intent.binding.object_id), (read.action_id, intent.action_id),
             (read.fingerprint, intent.argument_fingerprint))
    if any(actual is not None and actual != expected for actual, expected in pairs):
        return result("conflict", "original_identity_conflict")
    if read.action_id is None or read.fingerprint is None or not read.evidence_refs:
        return result("outcome_unknown", "original_evidence_missing")
    if read.operation != intent.operation:
        return result("conflict", "original_identity_conflict")
    if read.stage == "terminally_rejected" and read.nonexecution.status == "proven":
        if read.nonexecution.evidence_ref not in read.evidence_refs:
            return result("outcome_unknown", "terminal_evidence_missing")
        return result("rejected", "terminal_nonexecution", True)
    if read.nonexecution.status == "proven":
        return result("conflict", "inconsistent_terminal_proof")
    expected = expected_facts(intent)
    if expected is None:
        return result("conflict", "unsupported_postcondition")
    if read.stage not in _STAGES[intent.operation]:
        return result("outcome_unknown", "execution_stage_unknown")
    facts = {}
    for observation in read.observations:
        key = observation.authority + "." + observation.fact
        if observation.object_id != intent.binding.object_id or key in facts:
            return result("conflict", "observation_identity_conflict")
        if observation.observed_at > read.as_of or (observation.provider_at is not None and observation.provider_at > read.as_of):
            return result("conflict", "observation_time_conflict")
        facts[key] = observation.value
    if not set(expected) <= set(facts):
        return result("outcome_unknown", "postcondition_evidence_missing")
    stage_fact = {"create_return": "returns.status", "send_status": "messaging.status",
                  "send_clarification": "messaging.status", "transfer_owner": "ownership.state"}.get(intent.operation)
    if stage_fact is not None and facts.get(stage_fact) != read.stage:
        return result("conflict", "execution_stage_conflict")
    if intent.operation == "transfer_owner":
        if (not isinstance(facts.get("ownership.state_revision"), str) or not facts["ownership.state_revision"]
                or type(facts.get("ownership.epoch")) is not int or intent.ownership_epoch is None
                or facts["ownership.epoch"] != intent.ownership_epoch + (read.stage == "accepted")
                or (read.stage == "accepted" and facts.get("ownership.owner") != intent.arguments.get("target_owner"))):
            return result("conflict", "ownership_evidence_conflict")
    progress = {("returns.status", "initiated", "received"), ("messaging.status", "sent", "delivered"),
                ("ownership.state", "pending", "accepted")}
    pending = stage_fact is not None and (stage_fact, facts[stage_fact], expected[stage_fact]) in progress
    for key, wanted in expected.items():
        actual = facts[key]
        if key == stage_fact and isinstance(actual, str) and isinstance(wanted, str):
            if (key, actual, wanted) in progress or (key, wanted, actual) in progress:
                continue
        if pending and intent.operation == "transfer_owner" and key in {"ownership.owner", "ownership.epoch"}:
            continue
        if actual != wanted or type(actual) is not type(wanted):
            return result("conflict", "postcondition_conflict")
    if intent.operation in {"register_goods_refusal", "create_return"}:
        inventory = facts["goods.inventory"]
        if not isinstance(inventory, dict) or any(type(q) is not int or q <= 0 for q in inventory.values()) or type(facts.get("goods.quantity")) is not int or facts["goods.quantity"] != sum(inventory.values()):
            return result("conflict", "whole_inventory_conflict")
    if pending:
        return result("pending", "independent_completion_pending", True)
    return result("verified", "authoritative_original_verified", True)
