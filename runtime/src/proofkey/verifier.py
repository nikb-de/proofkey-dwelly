"""Operation-specific verification of independent authoritative original reads."""
from .contracts import AuthorityReadback, EffectIntent, VerificationResult
from .packet_contracts import (PacketContentV1, PacketContentReceiptV1, packet_enabled,
                                packet_postcondition, validate_packet_arguments, validate_packet_policy)
from .identity import fingerprint
from .ownership_contracts import (ownership_enabled, TransferArgumentsV1, TransferPostconditionV1,
    OriginalTransferIdentityV1, TransferSourceReceiptV1, TransferPendingV1, TransferAcceptedV1,
    TransferRejectedV1, TRANSFER_FIELDS_V1)
from pydantic import TypeAdapter


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


def expected_facts(intent, *, profile=None):
    """Translate declared postconditions; no broad case-completion alias exists."""
    if intent.operation == "enqueue_handoff" and packet_enabled(profile):
        try:
            content = validate_packet_arguments(intent.arguments, binding=intent.binding)
            validate_packet_policy(content, profile, process_version=intent.process_version, policy_version=intent.policy_version)
            wanted = packet_postcondition(intent.arguments)
            if intent.profile_version != profile.version or intent.postcondition != wanted:
                return None
            return {"operator." + key: value for key, value in wanted.items()}
        except (ValueError, TypeError, KeyError):
            return None
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


def verify(intent, authoritative_readback, *, profile=None):
    intent = EffectIntent.model_validate(intent.model_dump())
    read = AuthorityReadback.model_validate(authoritative_readback.model_dump())
    if intent.operation == "transfer_owner" and ownership_enabled(profile):
        return verify_registered_transfer(intent, read, profile=profile)

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
    if intent.operation == "enqueue_handoff" and packet_enabled(profile):
        return _verify_packet(intent, read, profile, result)
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


def verify_registered_transfer(intent, authoritative_readback, *, profile):
    """Historical exact source receipt only; current ownership requires separate CAS."""
    intent = EffectIntent.model_validate(intent.model_dump())
    read = AuthorityReadback.model_validate(authoritative_readback.model_dump())
    def result(status, reason, evidence=False):
        return VerificationResult(status=status, reason=reason, object_id=intent.binding.object_id,
            action_id=intent.action_id, fingerprint=intent.argument_fingerprint,
            postcondition=intent.postcondition, evidence_refs=read.evidence_refs if evidence else [],
            as_of=read.as_of if evidence else None)
    try:
        args = TransferArgumentsV1.model_validate(intent.arguments)
        post = TransferPostconditionV1.model_validate(intent.postcondition)
        original = OriginalTransferIdentityV1(binding=intent.binding, transfer_id=args.intent.transfer_id,
            action_id=intent.action_id, provider_key=intent.provider_key, argument_fingerprint=intent.argument_fingerprint)
        if (not ownership_enabled(profile) or intent.profile_version != profile.version
                or intent.operation != "transfer_owner" or intent.stage != "request" or intent.decision_id is not None
                or post.original != original or args.intent.binding != intent.binding
                or post.target_owner != args.intent.target_owner or post.packet.content_hash != args.content_hash
                or intent.deadline != args.intent.expires_at
                or (args.intent.expected_owner, args.intent.expected_epoch, args.intent.expected_state_revision,
                    args.intent.packet_id, args.intent.packet_hash, args.intent.packet_revision) !=
                   (post.packet.accepted_owner, post.packet.accepted_epoch, post.packet.accepted_state_revision,
                    post.packet.packet_id, post.packet.packet_hash, post.packet.packet_revision)
                or (intent.ownership_state_revision, intent.ownership_epoch) !=
                   (args.intent.expected_state_revision, args.intent.expected_epoch)
                or not TRANSFER_FIELDS_V1 <= intent.expected_revisions.revisions.keys()
                or intent.expected_revisions.revisions["operator.ownership_grant"] != args.grant_revision):
            return result("conflict", "registered_original_conflict")
        if any(actual is not None and actual != wanted for actual, wanted in (
                (read.object_id, intent.binding.object_id), (read.action_id, intent.action_id),
                (read.fingerprint, intent.argument_fingerprint))):
            return result("conflict", "original_identity_conflict")
        if read.action_id is None or read.fingerprint is None or not read.evidence_refs:
            return result("outcome_unknown", "original_evidence_missing")
        if read.operation != intent.operation:
            return result("conflict", "original_identity_conflict")
        facts = {}
        for obs in read.observations:
            key = obs.authority+"."+obs.fact
            if key in facts or obs.object_id != intent.binding.object_id or obs.observed_at > read.as_of:
                return result("conflict", "observation_identity_conflict")
            if obs.provider_at is None or obs.provider_at > obs.observed_at:
                return result("conflict", "observation_time_conflict")
            facts[key] = obs
        obs = facts.get("operator.transfer_receipt")
        if obs is None:
            return result("outcome_unknown", "registered_receipt_missing")
        receipt = TypeAdapter(TransferSourceReceiptV1).validate_python(obs.value)
        if (receipt.original != original or receipt.packet != post.packet or receipt.target_owner != post.target_owner
                or receipt.expected_revisions != intent.expected_revisions
                or isinstance(receipt, TransferPendingV1) and receipt.evidence_ref != obs.evidence_ref
                or isinstance(receipt, TransferRejectedV1) and receipt.nonexecution.evidence_ref != receipt.evidence_ref):
            return result("conflict", "registered_receipt_conflict")
        at = receipt.accepted_at if isinstance(receipt, TransferAcceptedV1) else receipt.pending_at if isinstance(receipt, TransferPendingV1) else receipt.rejected_at
        if at > read.as_of or obs.provider_at != at or at < post.packet.accepted_at:
            return result("conflict", "registered_receipt_time_conflict")
        if isinstance(receipt, TransferAcceptedV1):
            if read.stage != "accepted" or at >= intent.deadline or read.nonexecution.status == "proven":
                return result("conflict", "registered_acceptance_conflict")
            return result("verified", "authoritative_original_verified", True)
        if isinstance(receipt, TransferRejectedV1):
            if read.stage != "terminally_rejected" or read.nonexecution != receipt.nonexecution:
                return result("conflict", "registered_rejection_conflict")
            return result("rejected", "terminal_nonexecution", True)
        if read.stage != "pending" or read.nonexecution.status == "proven":
            return result("conflict", "registered_pending_conflict")
        return result("pending", "independent_completion_pending", True)
    except (ValueError, TypeError, KeyError, AttributeError):
        return result("conflict", "registered_receipt_conflict")


def _verify_packet(intent, read, profile, result):
    expected = expected_facts(intent, profile=profile)
    if expected is None:
        return result("conflict", "unsupported_postcondition")
    if read.stage != "queued":
        return result("outcome_unknown", "execution_stage_unknown")
    facts, observations = {}, {}
    for obs in read.observations:
        key = obs.authority + "." + obs.fact
        if key in facts or obs.object_id != intent.binding.object_id:
            return result("conflict", "observation_identity_conflict")
        if obs.observed_at > read.as_of or obs.provider_at is not None and obs.provider_at > read.as_of:
            return result("conflict", "observation_time_conflict")
        facts[key], observations[key] = obs.value, obs
    raw = facts.get("operator.packet_content_receipt")
    if raw is None:
        return result("outcome_unknown", "packet_content_evidence_missing")
    try:
        receipt = PacketContentReceiptV1.model_validate(raw)
        content = validate_packet_arguments(intent.arguments, binding=intent.binding)
        obs = observations["operator.packet_content_receipt"]
        if (receipt.owner_status != "pending" or receipt.acceptance is not None
                or receipt.stored_at > read.as_of or receipt.stored_at < content.as_of
                or receipt.evidence_ref != obs.evidence_ref or obs.provider_at != receipt.stored_at
                or receipt.generation != intent.binding.generation or receipt.action_id != intent.action_id
                or receipt.provider_key != intent.provider_key or receipt.argument_fingerprint != intent.argument_fingerprint
                or receipt.owner != content.source.owner or receipt.epoch != content.source.epoch
                or receipt.state_revision != content.source.state_revision
                or any(getattr(receipt, key) != value for key, value in packet_postcondition(intent.arguments).items())):
            return result("conflict", "packet_receipt_conflict")
        for key in ("packet_id", "packet_hash", "packet_revision"):
            if facts.get("operator." + key) != getattr(receipt, key):
                return result("conflict", "packet_source_commitment_conflict")
        if facts.get("operator.handoff_disposition") != "pending":
            return result("conflict", "packet_owner_status_conflict")
        if "operator.packet_content" in facts:
            disclosed = PacketContentV1.model_validate(facts["operator.packet_content"])
            if fingerprint(disclosed.model_dump(mode="json")) != receipt.content_hash:
                return result("conflict", "packet_content_digest_conflict")
    except (ValueError, TypeError, KeyError):
        return result("conflict", "packet_receipt_conflict")
    return result("verified", "authoritative_content_stored_owner_pending", True)
