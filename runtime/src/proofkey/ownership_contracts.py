"""Closed synthetic ownership records; integrity data never authenticates a caller.

Host snapshots are internal transaction inputs. Their typed data and fixture hashes
do not establish source participation or permission outside a trusted producer.
"""
from datetime import datetime, timezone
import json
from typing import Annotated, Literal

from pydantic import Field, TypeAdapter, field_validator, model_validator

from .contracts import (AuthorityObservation, EffectIntent, Hash, HumanOwnership, Identifier,
    NonexecutionProof, NonnegativeInt, OperatorDecision, PhaseCheckpoint, RequestBinding,
    Revision, RevisionVector, Timestamp, WireModel, ProcessSpec)
from .identity import fingerprint, stable_action_id
from .process import material_fields

OWNERSHIP_BASES_V1 = {
    "permission_basis": "ownership-v1: source actor and target grant",
    "acknowledgement": "ownership-v1: acknowledgement is not acceptance",
    "readback": "ownership-v1: exact original typed receipt",
    "conditional_coverage": "ownership-v1: atomic case packet owner grant comparison",
    "idempotency_scope": "ownership-v1: binding operation stage original identity",
    "terminal_nonexecution_basis": "ownership-v1: durable original terminal rejection",
}
OWNERSHIP_MANIFEST_V1 = "synthetic-ownership-manifest-v1"
OWNERSHIP_FIELDS_V1 = frozenset({"operator.ownership_grant", "operator.ownership_packet"})
TRANSFER_FIELDS_V1 = material_fields("transfer_owner") | OWNERSHIP_FIELDS_V1
DecisionOperation = Literal["reschedule", "register_goods_refusal", "register_service_refusal", "create_return"]
Disposition = Literal["refund_review", "coverage_review", "internal_case_recommendation"]
MAX_OWNERSHIP_BYTES = 512 * 1024


def ownership_enabled(profile):
    """Closed code registration of a host profile, never a model/body grant."""
    names = {"transfer_owner": "ownership-transfer-v1", "record_operator_decision": "ownership-decision-v1",
             "record_operator_disposition": "ownership-disposition-v1"}
    if profile is None or not any(name in profile.capabilities and profile.capabilities[name].version == version
                                  for name, version in names.items()):
        return False
    if profile.version != "v1.4":
        raise ValueError("Unregistered ownership profile")
    from .packet_contracts import packet_enabled
    if not packet_enabled(profile):
        raise ValueError("Ownership requires registered packet semantics")
    for name, version in names.items():
        cap = profile.capabilities.get(name)
        if (cap is None or cap.version != version or cap.operation != name or cap.authority != "operator"
                or cap.evidence_mode != "synthetic" or cap.timeout_seconds is None):
            raise ValueError("Unregistered ownership capability")
        limits = cap.shared_limits
        if any(getattr(limits, field) is None for field in ("account_id", "quota", "concurrency", "rate_per_second")):
            raise ValueError("Ownership capability requires finite shared limits")
        for field, basis in OWNERSHIP_BASES_V1.items():
            contract = getattr(cap, field)
            supported = name == "transfer_owner" or field in {"permission_basis", "readback", "conditional_coverage"}
            if (contract.status != ("supported" if supported else "unsupported")
                    or (supported and (contract.basis != basis or contract.evidence_ref != OWNERSHIP_MANIFEST_V1))):
                raise ValueError("Unregistered ownership contract basis")
        if name == "transfer_owner" and set(cap.conditional_coverage.covered_fields) != TRANSFER_FIELDS_V1:
            raise ValueError("Incomplete ownership conditional coverage")
        fields = cap.conditional_coverage.covered_fields
        if len(fields) != len(set(fields)):
            raise ValueError("Duplicate ownership coverage")
    if any(profile.authorities.get(field) != field.partition(".")[0]
           for field in OWNERSHIP_FIELDS_V1 | {"operator.transfer_receipt"}):
        raise ValueError("Unregistered ownership authority")
    return True


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("Duplicate ownership JSON field")
        result[key] = value
    return result


def _bounded(value):
    if isinstance(value, str) and len(value.encode("utf-8")) > 4096:
        raise ValueError("Ownership string exceeds finite limit")
    if isinstance(value, dict):
        for key, item in value.items():
            _bounded(key)
            _bounded(item)
    elif isinstance(value, (list, tuple)):
        if len(value) > 64:
            raise ValueError("Ownership array exceeds finite limit")
        for item in value:
            _bounded(item)


class OwnershipModel(WireModel):
    @model_validator(mode="before")
    @classmethod
    def bounded(cls, value):
        _bounded(value)
        return value

    @field_validator("*", mode="after")
    @classmethod
    def utc(cls, value):
        return value.astimezone(timezone.utc) if isinstance(value, datetime) else value

    @field_validator("simulated", mode="before", check_fields=False)
    @classmethod
    def strict_simulated(cls, value, info):
        if info.field_name == "simulated" and type(value) is not bool:
            raise ValueError("Simulation marker must be strict boolean true")
        return value

    @model_validator(mode="after")
    def total_bounds(self):
        data = self.model_dump(mode="json")
        _bounded(data)
        if len(json.dumps(data, ensure_ascii=False).encode("utf-8")) > MAX_OWNERSHIP_BYTES:
            raise ValueError("Ownership record exceeds finite byte limit")
        return self

    @classmethod
    def model_validate_json(cls, json_data, **kwargs):
        if len(json_data.encode("utf-8") if isinstance(json_data, str) else json_data) > MAX_OWNERSHIP_BYTES:
            raise ValueError("Ownership JSON exceeds finite limit")
        value = json.loads(json_data, object_pairs_hook=_pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Nonfinite ownership number")))
        return cls.model_validate(value, **kwargs)


class OwnershipProcessRegistryV1(OwnershipModel):
    """Detached constructor configuration selected only by a trusted host.

    Hashes attest canonical integrity. This registry is neither profile review
    nor actor/source authentication, and it enables no provider route.
    """
    kind: Literal["ownership_process_registry_v1"] = "ownership_process_registry_v1"
    profile_id: Identifier
    profile_version: Revision
    profile_hash: Hash
    policy_hash: Hash
    process_hash: Hash
    processes: dict[Identifier, ProcessSpec]

    @model_validator(mode="before")
    @classmethod
    def bounded(cls, value):
        # Existing finite process graphs contain more than 64 edges. They keep
        # their own graph contract; source observation lists remain <=64.
        if isinstance(value, dict):
            _bounded({key: item for key, item in value.items() if key != "processes"})
        return value

    @model_validator(mode="after")
    def total_bounds(self):
        data = self.model_dump(mode="json")
        _bounded({key: value for key, value in data.items() if key != "processes"})
        if len(json.dumps(data, ensure_ascii=False).encode("utf-8")) > MAX_OWNERSHIP_BYTES:
            raise ValueError("Ownership process registry exceeds finite byte limit")
        return self

    @model_validator(mode="after")
    def canonical_graphs(self):
        from .process import validate_process
        if self.profile_version != "v1.4" or not self.processes or len(self.processes) > 64:
            raise ValueError("Ownership requires a finite exact v1.4 process registry")
        data = self.model_dump(mode="json")
        if self.process_hash != fingerprint(data["processes"]):
            raise ValueError("Ownership process bundle hash mismatch")
        for spec in self.processes.values():
            validate_process(spec)
            if any(len(getattr(spec, name)) > 256 for name in ("edges", "phases", "operations", "prerequisites", "waits", "approvals")):
                raise ValueError("Ownership registry graph exceeds finite limit")
            raw = spec.model_dump(mode="json")
            if spec.release_hash != fingerprint({key: value for key, value in raw.items() if key != "release_hash"}):
                raise ValueError("Ownership process release hash mismatch")
        return self


def _unique(value):
    if len(value) != len(set(value)):
        raise ValueError("Duplicate ownership scope identity")
    return sorted(value)


class OwnershipPacketV1(OwnershipModel):
    kind: Literal["ownership_packet_v1"] = "ownership_packet_v1"
    binding: RequestBinding
    packet_id: Identifier
    packet_hash: Hash
    packet_revision: Revision
    content_hash: Hash | None
    accepted_owner: Identifier
    accepted_epoch: NonnegativeInt
    accepted_state_revision: Revision
    acceptance_evidence: Identifier
    accepted_at: Timestamp
    simulated: Literal[True]


class OwnershipGrantV1(OwnershipModel):
    kind: Literal["ownership_grant_v1"] = "ownership_grant_v1"
    grant_id: Identifier
    binding: RequestBinding
    actor_id: Identifier
    actor_type: Literal["human"]
    packet_id: Identifier
    packet_hash: Hash
    packet_revision: Revision
    content_hash: Hash | None
    owner: Identifier
    epoch: NonnegativeInt
    state_revision: Revision
    may_initiate_transfer: bool
    target_owners: Annotated[list[Identifier], Field(max_length=16)]
    decision_operations: Annotated[list[DecisionOperation], Field(max_length=4)]
    may_record_nonaction_decision: bool
    dispositions: Annotated[list[Disposition], Field(max_length=3)]
    issued_at: Timestamp
    expires_at: Timestamp
    evidence_ref: Identifier
    fixture_hash: Hash
    simulated: Literal[True]

    _unique_scope = field_validator("target_owners", "decision_operations", "dispositions")(_unique)

    @model_validator(mode="after")
    def ordered_times(self):
        if self.issued_at >= self.expires_at:
            raise ValueError("Grant interval must be finite and ordered")
        return self


class TransferArgumentsV1(OwnershipModel):
    kind: Literal["ownership_transfer_arguments_v1"] = "ownership_transfer_arguments_v1"
    intent: "TransferIntent"
    content_hash: Hash | None
    grant_id: Identifier
    grant_revision: Revision


from .contracts import TransferIntent
TransferArgumentsV1.model_rebuild()


class OriginalTransferIdentityV1(OwnershipModel):
    binding: RequestBinding
    transfer_id: Identifier
    action_id: Identifier
    provider_key: Identifier
    argument_fingerprint: Hash

    @model_validator(mode="after")
    def stable_original(self):
        key = stable_action_id(self.binding, "transfer_owner", "request")
        if (self.transfer_id, self.action_id, self.provider_key) != (key, key, key):
            raise ValueError("Transfer identity must equal the one original binding key")
        return self


class TransferPostconditionV1(OwnershipModel):
    kind: Literal["ownership_transfer_postcondition_v1"] = "ownership_transfer_postcondition_v1"
    original: OriginalTransferIdentityV1
    packet: OwnershipPacketV1
    target_owner: Identifier
    accepted_epoch: NonnegativeInt

    @model_validator(mode="after")
    def successor(self):
        if (self.original.binding != self.packet.binding or self.target_owner == self.packet.accepted_owner
                or self.accepted_epoch != self.packet.accepted_epoch + 1):
            raise ValueError("Transfer postcondition must name an exact next owner epoch")
        return self


class TransferPendingV1(OwnershipModel):
    kind: Literal["transfer_pending_v1"] = "transfer_pending_v1"
    original: OriginalTransferIdentityV1
    packet: OwnershipPacketV1
    target_owner: Identifier
    expected_revisions: RevisionVector
    pending_state_revision: Revision
    pending_at: Timestamp
    evidence_ref: Identifier
    simulated: Literal[True]

    @model_validator(mode="after")
    def predecessor(self):
        if (self.original.binding != self.packet.binding or self.target_owner == self.packet.accepted_owner
                or self.pending_state_revision == self.packet.accepted_state_revision
                or self.pending_at < self.packet.accepted_at):
            raise ValueError("Pending receipt predecessor mismatch")
        return self


class TransferAcceptedV1(OwnershipModel):
    kind: Literal["transfer_accepted_v1"] = "transfer_accepted_v1"
    original: OriginalTransferIdentityV1
    packet: OwnershipPacketV1
    target_owner: Identifier
    expected_revisions: RevisionVector
    pending_state_revision: Revision | None
    accepted_state_revision: Revision
    accepted_epoch: NonnegativeInt
    accepted_at: Timestamp
    acceptance_evidence: Identifier
    target_instruction_hash: Hash
    simulated: Literal[True]

    @model_validator(mode="after")
    def successor(self):
        if (self.original.binding != self.packet.binding or self.target_owner == self.packet.accepted_owner
                or self.accepted_epoch != self.packet.accepted_epoch + 1
                or self.accepted_state_revision in {self.packet.accepted_state_revision, self.pending_state_revision}
                or self.accepted_at < self.packet.accepted_at):
            raise ValueError("Acceptance does not establish an exact successor")
        return self


class TransferRejectedV1(OwnershipModel):
    kind: Literal["transfer_rejected_v1"] = "transfer_rejected_v1"
    original: OriginalTransferIdentityV1
    packet: OwnershipPacketV1
    target_owner: Identifier
    expected_revisions: RevisionVector
    retained_state_revision: Revision
    rejected_at: Timestamp
    nonexecution: NonexecutionProof
    evidence_ref: Identifier
    simulated: Literal[True]

    @model_validator(mode="after")
    def definite(self):
        if (self.original.binding != self.packet.binding or self.target_owner == self.packet.accepted_owner
                or self.nonexecution.status != "proven"
                or self.nonexecution.basis != OWNERSHIP_BASES_V1["terminal_nonexecution_basis"]
                or self.rejected_at < self.packet.accepted_at):
            raise ValueError("Rejection requires exact registered terminal nonexecution")
        return self


TransferSourceReceiptV1 = Annotated[TransferPendingV1 | TransferAcceptedV1 | TransferRejectedV1,
                                   Field(discriminator="kind")]


class DecisionEffectScopeV1(OwnershipModel):
    operation: DecisionOperation
    stage: Literal["commit", "initiate"]
    action_id: Identifier
    argument_fingerprint: Hash

    @model_validator(mode="after")
    def operation_stage(self):
        if self.stage != ("initiate" if self.operation == "create_return" else "commit"):
            raise ValueError("Decision operation stage mismatch")
        return self


class OperatorDecisionSubmissionV1(OwnershipModel):
    kind: Literal["operator_decision_submission_v1"] = "operator_decision_submission_v1"
    decision: OperatorDecision
    content_hash: Hash | None
    effect_scope: DecisionEffectScopeV1 | None

    @model_validator(mode="after")
    def scoped(self):
        decision, scope = self.decision, self.effect_scope
        if not decision.simulated or decision.owner != decision.actor_id:
            raise ValueError("Decision requires simulated current owner actor")
        if decision.decision == "approve":
            if (scope is None or decision.scope != [scope.operation]
                    or scope.action_id != stable_action_id(decision.binding, scope.operation, scope.stage)):
                raise ValueError("Approval requires exact original effect scope")
        elif scope is not None or decision.scope:
            raise ValueError("Nonaction decisions cannot grant action scope")
        return self


class OperatorDispositionV1(OwnershipModel):
    kind: Literal["operator_disposition_v1"] = "operator_disposition_v1"
    record_id: Identifier
    replay_id: Identifier
    binding: RequestBinding
    packet_id: Identifier
    packet_hash: Hash
    packet_revision: Revision
    content_hash: Hash | None
    owner: Identifier
    epoch: NonnegativeInt
    state_revision: Revision
    actor_id: Identifier
    proof_reference: Identifier
    disposition: Disposition
    rationale: Annotated[str, Field(min_length=1)]
    evidence_refs: Annotated[list[Identifier], Field(max_length=32)]
    expires_at: Timestamp
    simulated: Literal[True]

    _unique_evidence = field_validator("evidence_refs")(_unique)

    @model_validator(mode="after")
    def owner_actor(self):
        if self.owner != self.actor_id:
            raise ValueError("Disposition actor must be current owner")
        return self


class OwnershipSourceReadV1(OwnershipModel):
    binding: RequestBinding
    checkpoint: PhaseCheckpoint
    packet: OwnershipPacketV1
    grant: OwnershipGrantV1
    observations: Annotated[list[AuthorityObservation], Field(min_length=1, max_length=64)]
    read_entry_ids: Annotated[list[Identifier], Field(min_length=1, max_length=64)]
    as_of: Timestamp
    profile_hash: Hash
    process_hash: Hash
    policy_hash: Hash

    _unique_entries = field_validator("read_entry_ids")(_unique)

    @model_validator(mode="after")
    def coherent(self):
        if self.checkpoint.binding != self.binding or self.packet.binding != self.binding or self.grant.binding != self.binding:
            raise ValueError("Ownership source binding mismatch")
        identities = [item.authority + "." + item.fact for item in self.observations]
        if len(set(identities)) != len(identities):
            raise ValueError("Duplicate ownership source observation")
        if any(item.object_id != self.binding.object_id or item.observed_at > self.as_of for item in self.observations):
            raise ValueError("Ownership source observation identity/time mismatch")
        packet, grant = self.packet, self.grant
        if ((grant.packet_id, grant.packet_hash, grant.packet_revision, grant.content_hash,
             grant.owner, grant.epoch, grant.state_revision) !=
            (packet.packet_id, packet.packet_hash, packet.packet_revision, packet.content_hash,
             packet.accepted_owner, packet.accepted_epoch, packet.accepted_state_revision)):
            raise ValueError("Grant and packet ownership tuple differ")
        return self


class OwnershipCurrentReadV1(OwnershipModel):
    binding: RequestBinding
    checkpoint: PhaseCheckpoint
    ownership: HumanOwnership
    packet: OwnershipPacketV1
    observations: Annotated[list[AuthorityObservation], Field(min_length=1, max_length=64)]
    read_entry_ids: Annotated[list[Identifier], Field(min_length=1, max_length=64)]
    as_of: Timestamp
    profile_hash: Hash
    process_hash: Hash
    policy_hash: Hash

    _unique_entries = field_validator("read_entry_ids")(_unique)

    @model_validator(mode="after")
    def coherent(self):
        ownership, packet = self.ownership, self.packet
        if any(value.binding != self.binding for value in (self.checkpoint, ownership, packet)):
            raise ValueError("Ownership confirmation binding mismatch")
        if ((ownership.packet_id, ownership.packet_hash, ownership.packet_revision, ownership.owner, ownership.epoch) !=
            (packet.packet_id, packet.packet_hash, packet.packet_revision, packet.accepted_owner, packet.accepted_epoch)):
            raise ValueError("Ownership confirmation packet mismatch")
        identities = [item.authority + "." + item.fact for item in self.observations]
        if len(identities) != len(set(identities)) or any(item.object_id != self.binding.object_id
                or item.observed_at > self.as_of for item in self.observations):
            raise ValueError("Ownership confirmation observation mismatch")
        return self


class TransferRecordV1(OwnershipModel):
    kind: Literal["transfer_record_v1"] = "transfer_record_v1"
    intent: TransferIntent
    effect: EffectIntent
    origin_checkpoint: PhaseCheckpoint
    origin_checkpoint_hash: Hash
    original_input_hash: Hash
    profile_hash: Hash
    process_hash: Hash
    policy_hash: Hash
    registration_source: OwnershipSourceReadV1
    registered_at: Timestamp
    lifecycle: Literal["prepared", "pending", "accepted", "outcome_unknown", "rejected"]
    source_receipt: TransferSourceReceiptV1 | None

    @model_validator(mode="after")
    def links(self):
        intent, effect, source = self.intent, self.effect, self.registration_source
        args = TransferArgumentsV1.model_validate(effect.arguments)
        post = TransferPostconditionV1.model_validate(effect.postcondition)
        original = OriginalTransferIdentityV1(binding=intent.binding, transfer_id=intent.transfer_id,
            action_id=effect.action_id, provider_key=effect.provider_key, argument_fingerprint=effect.argument_fingerprint)
        if (intent.binding != effect.binding or effect.operation != "transfer_owner" or effect.stage != "request"
                or effect.deadline != intent.expires_at or effect.decision_id is not None or args.intent != intent
                or args.content_hash != source.packet.content_hash or args.grant_id != source.grant.grant_id
                or post.original != original or post.packet != source.packet or post.target_owner != intent.target_owner
                or source.checkpoint != self.origin_checkpoint or source.binding != intent.binding
                or self.origin_checkpoint_hash != fingerprint(self.origin_checkpoint.model_dump(mode="json"))
                or any(getattr(source, field) != getattr(self, field) for field in ("profile_hash", "process_hash", "policy_hash"))
                or (intent.expected_owner, intent.expected_epoch, intent.expected_state_revision,
                    intent.packet_id, intent.packet_hash, intent.packet_revision) !=
                   (source.packet.accepted_owner, source.packet.accepted_epoch, source.packet.accepted_state_revision,
                    source.packet.packet_id, source.packet.packet_hash, source.packet.packet_revision)
                or (effect.ownership_state_revision, effect.ownership_epoch) != (intent.expected_state_revision, intent.expected_epoch)
                or self.registered_at >= intent.expires_at or intent.expires_at > min(source.grant.expires_at, self.origin_checkpoint.deadline)):
            raise ValueError("Transfer immutable linkage mismatch")
        receipt = self.source_receipt
        if receipt is not None:
            if (receipt.original != original or receipt.packet != source.packet
                    or receipt.target_owner != intent.target_owner or receipt.expected_revisions != effect.expected_revisions):
                raise ValueError("Receipt differs from registered original")
            at = getattr(receipt, "accepted_at", getattr(receipt, "pending_at", getattr(receipt, "rejected_at", None)))
            if at < self.registered_at or (isinstance(receipt, TransferAcceptedV1) and at >= intent.expires_at):
                raise ValueError("Receipt time outside registered original bounds")
        terminal = {"accepted": TransferAcceptedV1, "rejected": TransferRejectedV1, "pending": TransferPendingV1}
        if self.lifecycle in terminal and not isinstance(receipt, terminal[self.lifecycle]):
            raise ValueError("Transfer lifecycle lacks matching receipt")
        if self.lifecycle == "prepared" and receipt is not None:
            raise ValueError("Prepared transfer cannot contain source execution evidence")
        if self.lifecycle == "outcome_unknown" and isinstance(receipt, (TransferAcceptedV1, TransferRejectedV1)):
            raise ValueError("Unknown transfer cannot contain terminal source evidence")
        if (not source.grant.may_initiate_transfer or intent.target_owner not in source.grant.target_owners
                or source.grant.actor_id != intent.expected_owner
                or not source.grant.issued_at <= self.registered_at < source.grant.expires_at
                or self.origin_checkpoint.stop.requested or self.origin_checkpoint.ownership_state != "accepted"
                or (self.origin_checkpoint.ownership_state_revision, self.origin_checkpoint.ownership_epoch) !=
                   (intent.expected_state_revision, intent.expected_epoch)):
            raise ValueError("Transfer original source grant/accepted scope mismatch")
        return self


class OwnerObservedV1(OwnershipModel):
    kind: Literal["owner_observed_v1"] = "owner_observed_v1"
    source: OwnershipSourceReadV1
    ownership: HumanOwnership


class TransferRegisteredV1(OwnershipModel):
    kind: Literal["transfer_registered_v1"] = "transfer_registered_v1"
    binding: RequestBinding
    transfer_id: Identifier
    original_effect_hash: Hash
    origin_checkpoint_hash: Hash


class TransferResolvedV1(OwnershipModel):
    kind: Literal["transfer_resolved_v1"] = "transfer_resolved_v1"
    binding: RequestBinding
    transfer_id: Identifier
    receipt_hash: Hash
    ownership: HumanOwnership
    source_current: OwnershipCurrentReadV1

    @model_validator(mode="after")
    def source_link(self):
        if self.source_current.binding != self.binding or self.ownership.binding != self.binding:
            raise ValueError("Terminal ownership event current-source binding mismatch")
        return self


class TransferReceiptRecordedV1(OwnershipModel):
    """Nonterminal source receipt inventory, never a resolution or permission."""
    kind: Literal["transfer_receipt_recorded_v1"] = "transfer_receipt_recorded_v1"
    binding: RequestBinding
    transfer_id: Identifier
    receipt: TransferPendingV1
    receipt_hash: Hash
    source_current: OwnershipCurrentReadV1

    @model_validator(mode="after")
    def receipt_link(self):
        if (self.receipt.original.binding != self.binding or self.receipt.original.transfer_id != self.transfer_id
                or self.source_current.binding != self.binding
                or self.receipt_hash != fingerprint(self.receipt.model_dump(mode="json"))):
            raise ValueError("Nonterminal receipt audit linkage mismatch")
        return self


class DecisionRecordedV1(OwnershipModel):
    kind: Literal["decision_recorded_v1"] = "decision_recorded_v1"
    submission: OperatorDecisionSubmissionV1
    payload_hash: Hash
    source: OwnershipSourceReadV1
    recorded_at: Timestamp

    @model_validator(mode="after")
    def hash_link(self):
        if self.payload_hash != fingerprint(self.submission.model_dump(mode="json")) or self.submission.decision.binding != self.source.binding:
            raise ValueError("Decision event payload mismatch")
        return self


class DecisionConsumedV1(OwnershipModel):
    kind: Literal["decision_consumed_v1"] = "decision_consumed_v1"
    binding: RequestBinding
    decision_id: Identifier
    replay_id: Identifier
    payload_hash: Hash
    action_id: Identifier
    argument_fingerprint: Hash
    consumed_at: Timestamp


class DispositionRecordedV1(OwnershipModel):
    kind: Literal["disposition_recorded_v1"] = "disposition_recorded_v1"
    disposition: OperatorDispositionV1
    payload_hash: Hash
    source: OwnershipSourceReadV1
    recorded_at: Timestamp

    @model_validator(mode="after")
    def hash_link(self):
        if self.payload_hash != fingerprint(self.disposition.model_dump(mode="json")) or self.disposition.binding != self.source.binding:
            raise ValueError("Disposition event payload mismatch")
        return self


OwnershipEventV1 = Annotated[OwnerObservedV1 | TransferRegisteredV1 | TransferResolvedV1 |
    TransferReceiptRecordedV1 | DecisionRecordedV1 | DecisionConsumedV1 | DispositionRecordedV1, Field(discriminator="kind")]


class SyntheticTargetAcceptanceV1(OwnershipModel):
    kind: Literal["synthetic_target_acceptance_v1"] = "synthetic_target_acceptance_v1"
    original: OriginalTransferIdentityV1
    packet: OwnershipPacketV1
    target_owner: Identifier
    expected_revisions: RevisionVector
    expires_at: Timestamp
    fixture_hash: Hash
    evidence_ref: Identifier
    simulated: Literal[True]
