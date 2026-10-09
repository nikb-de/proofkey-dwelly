"""Deterministic policy over trusted designated observations and frozen scopes."""
from datetime import datetime

from .contracts import (ActionProposal, AuthContext, AuthorityObservation, CanonicalRequest, EnvironmentProfile,
                        GateDecision, PhaseCheckpoint, RequestBinding, VerificationResult)
from .identity import request_fingerprint
from .journal import IntentRecord
from .process import ProcessController, material_fields
from .profiles import requires_completed_service
from .verifier import expected_facts

STAGES = {"reschedule": "commit", "register_goods_refusal": "commit", "register_service_refusal": "commit",
          "create_return": "initiate", "send_clarification": "send", "send_status": "send",
          "enqueue_handoff": "enqueue", "transfer_owner": "request"}
BUSINESS = frozenset({"reschedule", "register_goods_refusal", "register_service_refusal", "create_return"})
IDENTITY_FIELDS = frozenset({"case.binding", "case.request_revision", "case.authorization", "case.generation",
                             "customer.consent_revision"})
OWNER_FIELDS = frozenset({"ownership.state", "ownership.state_revision", "ownership.epoch", "ownership.owner"})


def qualified_observations(profile, object_id, observations):
    """Host-only typed source data; duplicates and foreign objects fail closed."""
    facts = {}
    for raw in observations:
        if not isinstance(raw, AuthorityObservation):
            raise GateDenied("scope_denied")
        observation = AuthorityObservation.model_validate(raw.model_dump())
        key = observation.authority + "." + observation.fact
        if (observation.object_id != object_id or key in facts
                or profile.authorities.get(key, observation.authority) != observation.authority
                or (observation.provider_at is not None and observation.provider_at > observation.observed_at)):
            raise GateDenied("scope_denied")
        facts[key] = observation
    return facts


def required_fields(profile, operation):
    capability = profile.capabilities.get(operation)
    minimum = material_fields(operation)
    if operation in BUSINESS:
        minimum |= {"customer.request_fingerprint", "customer.consent_mode"}
        if operation == "reschedule":
            minimum |= {"scheduling.slot_details"}
        if operation == "register_service_refusal" and requires_completed_service(profile):
            minimum |= {"delivery.status"}
    if capability is None or operation not in STAGES:
        raise GateDenied("scope_denied")
    contracts = (capability.permission_basis, capability.acknowledgement, capability.readback,
                 capability.conditional_coverage)
    if any(c.status != "supported" or not c.basis or not c.evidence_ref for c in contracts):
        raise GateDenied("scope_denied")
    covered = set(capability.conditional_coverage.covered_fields)
    if not minimum <= covered or any(profile.authorities.get(key) != key.partition(".")[0] for key in covered):
        raise GateDenied("scope_denied")
    return frozenset(covered)


def _source_identity(request, values):
    binding = values.get("case.binding")
    fields = ("case_id", "object_id", "principal_id", "request_id")
    return (isinstance(binding, dict) and all(binding.get(field) == getattr(request, field) for field in fields)
            and values.get("case.request_revision") == request.request_revision
            and values.get("customer.consent_revision") == request.consent_revision
            and values.get("case.authorization") == "verified"
            and isinstance(values.get("case.generation"), str) and bool(values["case.generation"]))


def _interval(start, end):
    if not isinstance(start, str) or not isinstance(end, str):
        raise GateDenied("scope_denied")
    start, end = datetime.fromisoformat(start), datetime.fromisoformat(end)
    if start.utcoffset() is None or end.utcoffset() is None or end <= start:
        raise GateDenied("scope_denied")
    return start, end


class GateDenied(ValueError):
    """Sanitized denial; caller claims never become authenticated history."""


class PolicyGate:
    def __init__(self, profile):
        if not isinstance(profile, EnvironmentProfile):
            raise ValueError("Trusted typed profile required")
        self.profile = EnvironmentProfile.model_validate(profile.model_dump())

    def bind_request(self, request, auth, observations):
        if not isinstance(request, CanonicalRequest) or not isinstance(auth, AuthContext):
            raise GateDenied("scope_denied")
        facts = qualified_observations(self.profile, request.object_id, observations)
        values = {key: observation.value for key, observation in facts.items()}
        if (not IDENTITY_FIELDS <= facts.keys() or not _source_identity(request, values)
                or auth.caller_id != request.principal_id):
            raise GateDenied("scope_denied")
        fields = ("case_id", "object_id", "principal_id", "request_id", "request_revision", "consent_revision")
        return RequestBinding(**{key: getattr(request, key) for key in fields},
            generation=values["case.generation"], fingerprint=request_fingerprint(request))

    @staticmethod
    def _service_predecessor(record, checkpoint):
        if not isinstance(record, IntentRecord):
            raise GateDenied("scope_denied")
        record = IntentRecord.model_validate(record.model_dump())
        intent, result = record.intent, record.verification
        if (intent.binding != checkpoint.binding or intent.operation != "register_service_refusal"
                or intent.stage != "commit" or intent.arguments != {"scope": "service"}
                or any(getattr(intent, key) != getattr(checkpoint, key) for key in
                       ("profile_version", "process_version", "policy_version"))
                or record.state != "verified" or result is None or result.status != "verified"
                or expected_facts(intent) != {"service.refusal": "verified"}
                or result.object_id != intent.binding.object_id or result.action_id != intent.action_id
                or result.fingerprint != intent.argument_fingerprint or result.postcondition != intent.postcondition
                or not result.evidence_refs or result.as_of is None):
            raise GateDenied("scope_denied")

    def evaluate(self, request, proposal, observations, checkpoint, *, journal_predecessor=None):
        try:
            if not isinstance(request, CanonicalRequest) or not isinstance(proposal, ActionProposal) or not isinstance(checkpoint, PhaseCheckpoint):
                raise GateDenied("scope_denied")
            fields = required_fields(self.profile, proposal.operation)
            facts = qualified_observations(self.profile, request.object_id, observations)
            values = {key: obs.value for key, obs in facts.items()}
            spec = self.profile.processes.get(request.kind)
            binding = checkpoint.binding
            if (spec is None or not (fields | OWNER_FIELDS) <= facts.keys() or not _source_identity(request, values)
                    or binding.fingerprint != request_fingerprint(request)
                    or any(getattr(request, key) != getattr(binding, key) for key in
                           ("case_id", "object_id", "principal_id", "request_id", "request_revision", "consent_revision"))
                    or values["case.generation"] != binding.generation or checkpoint.stop.requested
                    or checkpoint.profile_version != self.profile.version or checkpoint.process_version != spec.version
                    or checkpoint.policy_version != values["policy.version"]
                    or checkpoint.ownership_state != "accepted" or values["ownership.state"] != "accepted"
                    or checkpoint.ownership_state_revision != values["ownership.state_revision"]
                    or checkpoint.ownership_epoch != values["ownership.epoch"]
                    or values["delivery.risk"] != "safe" or values["delivery.stage"] != "eligible"
                    or proposal.stage != STAGES[proposal.operation]):
                raise GateDenied("scope_denied")
            graph = dict(values)
            graph.update({"case.generation": "current", "case.authority": "fresh", "operator.packet": "current"})
            args, operation = proposal.arguments, proposal.operation
            if operation == "enqueue_handoff" and request.kind == "service_refusal" and checkpoint.phase == "refusal_complete":
                self._service_predecessor(journal_predecessor, checkpoint)
                graph["service.refusal"] = "verified"
            if operation in BUSINESS:
                if (values.get("customer.request_fingerprint") != binding.fingerprint
                        or values.get("customer.consent") != "granted"
                        or values.get("customer.consent_mode") != request.consent_mode):
                    raise GateDenied("scope_denied")
                request_keys = {"reschedule_window": {"window_start", "window_end", "inventory"},
                                "reschedule_exact": {"slot", "inventory"}, "goods_refusal": {"inventory"},
                                "service_refusal": {"scope"}}.get(request.kind)
                if request_keys is None or not set(request.arguments) <= request_keys:
                    raise GateDenied("scope_denied")
                if operation == "reschedule":
                    if request.kind not in {"reschedule_window", "reschedule_exact"} or set(args) != {"slot"}:
                        raise GateDenied("scope_denied")
                    slot = args["slot"]
                    capacity, slots = values.get("scheduling.capacity"), values.get("scheduling.slot_details")
                    if not isinstance(slot, str) or not isinstance(capacity, list) or slot not in capacity or not isinstance(slots, dict) or not isinstance(slots.get(slot), dict):
                        raise GateDenied("scope_denied")
                    start, end = _interval(slots[slot].get("start"), slots[slot].get("end"))
                    if request.kind == "reschedule_window":
                        lower, upper = _interval(request.arguments.get("window_start"), request.arguments.get("window_end"))
                        if request.consent_mode != "window" or start < lower or end > upper:
                            raise GateDenied("scope_denied")
                        graph["customer.consent"] = "window"
                    else:
                        if request.consent_mode != "exact_slot" or request.arguments.get("slot") != slot:
                            raise GateDenied("scope_denied")
                        graph.update({"customer.consent": "exact_slot", "customer.confirmation": "verified"})
                elif operation in {"register_goods_refusal", "create_return"}:
                    inventory = values.get("goods.inventory")
                    allowed = {"inventory"} if operation == "register_goods_refusal" else {"inventory", "destination"}
                    if (request.kind != "goods_refusal" or set(args) != allowed or not isinstance(inventory, dict) or not inventory
                            or any(type(q) is not int or q <= 0 for q in inventory.values())
                            or type(values.get("goods.quantity")) is not int or sum(inventory.values()) != values["goods.quantity"]
                            or args.get("inventory") != inventory or request.arguments.get("inventory") != inventory):
                        raise GateDenied("scope_denied")
                    if (not isinstance(request.arguments.get("inventory"), dict)
                            or any(type(q) is not int or q <= 0 for q in request.arguments["inventory"].values())
                            or any(type(q) is not int for q in args["inventory"].values())):
                        raise GateDenied("scope_denied")
                    graph["customer.refusal_scope"] = "whole_goods"
                    if operation == "create_return" and (values.get("goods.refusal") != "verified" or args.get("destination") != values.get("returns.destination")):
                        raise GateDenied("scope_denied")
                else:
                    if (request.kind != "service_refusal" or args != {"scope": "service"}
                            or request.arguments.get("scope", "service") != "service"
                            or (requires_completed_service(self.profile) and values.get("delivery.status") != "completed")):
                        raise GateDenied("scope_denied")
                    graph["customer.refusal_scope"] = "service"
            elif operation in {"send_status", "send_clarification"}:
                keys = {"recipient", "text"} | ({"question_id"} if operation == "send_clarification" else set())
                if (set(args) != keys or values.get("messaging.permission") != "granted" or args.get("recipient") != values.get("messaging.recipient")
                        or not isinstance(args.get("text"), str) or not args["text"].strip()
                        or (operation == "send_clarification" and (not isinstance(args.get("question_id"), str) or not args["question_id"].strip()))):
                    raise GateDenied("scope_denied")
            else:
                keys = {"packet_id", "packet_revision", "packet_hash"} | ({"recipient"} if operation == "enqueue_handoff" else {"transfer_id", "target_owner"})
                if (set(args) != keys or any(not isinstance(value, str) or not value.strip() for value in args.values())
                        or args["packet_revision"] != values.get("operator.packet_revision") or args["packet_hash"] != values.get("operator.packet_hash")):
                    raise GateDenied("scope_denied")
                if operation == "enqueue_handoff" and args["recipient"] != values.get("operator.recipient"):
                    raise GateDenied("scope_denied")
                if operation == "transfer_owner" and args["target_owner"] == values["ownership.owner"]:
                    raise GateDenied("scope_denied")
            if not ProcessController(self.profile, request.kind).permits(checkpoint.phase, proposal.operation, graph):
                raise GateDenied("scope_denied")
            return GateDecision(allowed=True, reason="designated_scope_verified")
        except (GateDenied, ValueError, TypeError, KeyError):
            return GateDecision(allowed=False, reason="scope_denied", verification=VerificationResult(status="rejected", reason="scope_denied"))
