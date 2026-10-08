"""Canonical wire contracts. Profiles select allowed operations; bodies cannot.

Nested records describe evidence, not authority grants. Unknown capability
contracts remain explicit unknown. All identifiers are opaque strings, so
authority providers need not share an identifier syntax.
"""
from __future__ import annotations

from datetime import datetime
import math
from typing import Annotated, Literal

from pydantic import (AwareDatetime, BaseModel, BeforeValidator, ConfigDict, Field,
                      JsonValue, StringConstraints, model_serializer, model_validator)

from .identity import fingerprint, stable_action_id

Identifier = Annotated[str, StringConstraints(min_length=1, pattern=r"\S")]
Revision = Identifier
Hash = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]


def _parse_timestamp(value):
    # Wire dictionaries and JSON strings accept only ISO timestamps, never epochs.
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError("Expected an aware ISO timestamp") from None
    return value


Timestamp = Annotated[AwareDatetime, BeforeValidator(_parse_timestamp)]
NonnegativeInt = Annotated[int, Field(ge=0)]
NonnegativeFloat = Annotated[float, Field(ge=0)]
PositiveFloat = Annotated[float, Field(gt=0)]
ProcessingStatus = Literal["pending", "running", "completed", "failed", "outcome_unknown", "unavailable"]
DispatchStatus = Literal["rejected", "acknowledged", "outcome_unknown"]
VerificationStatus = Literal["verified", "rejected", "pending", "outcome_unknown", "conflict"]
GenericReasonCode = Literal["denied", "unavailable", "invalid_request", "runtime_error", "deadline_exceeded"]
EvidenceMode = Literal["unknown", "synthetic", "replay", "actual"]
ApprovalMode = Literal["simulated", "actual"]
ProcessorRole = Literal["extraction", "transcription", "planning"]
OwnerState = Literal["unowned", "pending", "accepted", "transfer_pending", "stopped"]


class FrozenDict(dict):
    """JSON-serializable defensive mapping; mutators cannot alter its snapshot."""
    def _immutable(self, *args, **kwargs):
        raise TypeError("Wire mappings are immutable snapshots")

    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = __ior__ = _immutable

    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self


class FrozenList(list):
    """Preserves a JSON array's semantics while blocking ordinary mutation."""
    def _immutable(self, *args, **kwargs):
        raise TypeError("Wire arrays are immutable snapshots")

    __setitem__ = __delitem__ = append = clear = extend = insert = pop = remove = reverse = sort = __iadd__ = __imul__ = _immutable

    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self


def _snapshot(value):
    if isinstance(value, dict):
        return FrozenDict({key: _snapshot(item) for key, item in value.items()})
    if isinstance(value, list):
        return FrozenList(_snapshot(item) for item in value)
    return value


def _finite(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Wire numbers must be finite")
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("Wire mapping keys must be strings")
            _finite(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _finite(item)


class WireModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True,
                              allow_inf_nan=False, validate_default=True,
                              revalidate_instances="always")

    @model_validator(mode="before")
    @classmethod
    def finite_numbers(cls, value):
        _finite(value)
        return value

    @model_validator(mode="after")
    def immutable_snapshot(self):
        for name in type(self).model_fields:
            object.__setattr__(self, name, _snapshot(getattr(self, name)))
        return self

    def model_copy(self, *, update=None, deep=False):
        """Copying a frozen contract must not become an unchecked mutation API."""
        return type(self).model_validate({**self.model_dump(), **(update or {})})


class CanonicalRequest(WireModel):
    case_id: Identifier
    object_id: Identifier
    principal_id: Identifier
    request_id: Identifier
    request_revision: Revision
    consent_revision: Revision
    kind: Identifier
    consent_mode: Literal["window", "exact_slot", "unknown"]
    arguments: dict[str, JsonValue]
    evidence_ids: list[Identifier]
    narrative: str | None = None


class AuthContext(WireModel):
    caller_id: Identifier
    proof_reference: Identifier


class ReadTarget(WireModel):
    """Tagged selectors accept only publicly named identities, never world keys."""
    kind: Literal["authority_facts", "original_effect", "transfer", "operator_packet", "question"]
    authority: Identifier | None = None
    facts: list[Identifier] | None = None
    operation: Identifier | None = None
    generation: Identifier | None = None
    action_id: Identifier | None = None
    provider_key: Identifier | None = None
    fingerprint: Hash | None = None
    transfer_id: Identifier | None = None
    packet_id: Identifier | None = None
    packet_revision: Revision | None = None
    question_id: Identifier | None = None

    @model_validator(mode="after")
    def tagged_fields(self):
        required = {
            "authority_facts": {"authority", "facts"},
            "original_effect": {"operation", "generation", "action_id", "provider_key", "fingerprint"},
            "transfer": {"transfer_id", "packet_id", "packet_revision"},
            "operator_packet": {"packet_id", "packet_revision"},
            "question": {"question_id"},
        }[self.kind]
        supplied = {name for name in type(self).model_fields if name != "kind" and getattr(self, name) is not None}
        if supplied != required or (self.kind == "authority_facts" and not self.facts):
            raise ValueError("Read target fields must exactly match its tag")
        return self


class ReadRequest(WireModel):
    case_id: Identifier
    object_id: Identifier
    caller_id: Identifier
    proof_reference: Identifier
    purpose: Identifier
    deadline: Timestamp
    target: ReadTarget


class RequestBinding(WireModel):
    case_id: Identifier
    object_id: Identifier
    principal_id: Identifier
    request_id: Identifier
    request_revision: Revision
    consent_revision: Revision
    generation: Identifier
    fingerprint: Hash
    supersedes_generation: Identifier | None = None


class AuthorityObservation(WireModel):
    authority: Identifier
    fact: Identifier
    object_id: Identifier
    value: JsonValue
    revision: Revision
    provider_at: Timestamp | None = None
    observed_at: Timestamp
    evidence_ref: Identifier


class NonexecutionProof(WireModel):
    status: Literal["unknown", "proven"] = "unknown"
    basis: Identifier | None = None
    evidence_ref: Identifier | None = None

    @model_validator(mode="after")
    def proven_requires_evidence(self):
        if self.status == "proven" and (self.basis is None or self.evidence_ref is None):
            raise ValueError("Terminal nonexecution requires a contract basis and evidence")
        return self


class AuthorityReadback(WireModel):
    operation: Identifier
    object_id: Identifier
    observations: list[AuthorityObservation]
    provider_request_id: Identifier | None = None
    action_id: Identifier | None = None
    fingerprint: Hash | None = None
    stage: Identifier
    nonexecution: NonexecutionProof = Field(default_factory=NonexecutionProof)
    as_of: Timestamp
    evidence_refs: list[Identifier]


class RevisionVector(WireModel):
    """Keys are material designated authority.fact identities, not only providers."""
    revisions: dict[Identifier, Revision]

    @model_validator(mode="after")
    def qualified_fact_identities(self):
        for identity in self.revisions:
            _require_fact_identity(identity)
        return self


def _require_fact_identity(identity):
    authority, separator, fact = identity.partition(".")
    if not separator or not authority.strip() or not fact.strip():
        raise ValueError("Material fact identity must be authority.fact")


class CapabilityContract(WireModel):
    status: Literal["unknown", "supported", "unsupported"] = "unknown"
    basis: Identifier | None = None
    covered_fields: list[Identifier] = Field(default_factory=list)
    evidence_ref: Identifier | None = None

    @model_validator(mode="after")
    def supported_requires_basis(self):
        if self.status == "supported" and self.basis is None:
            raise ValueError("Supported capability requires its designated contract basis")
        return self


class SharedAccountLimits(WireModel):
    account_id: Identifier | None = None
    quota: NonnegativeInt | None = None
    concurrency: NonnegativeInt | None = None
    rate_per_second: NonnegativeFloat | None = None


class OperationCapability(WireModel):
    operation: Identifier
    authority: Identifier
    permission_basis: CapabilityContract = Field(default_factory=CapabilityContract)
    acknowledgement: CapabilityContract = Field(default_factory=CapabilityContract)
    readback: CapabilityContract = Field(default_factory=CapabilityContract)
    idempotency_scope: CapabilityContract = Field(default_factory=CapabilityContract)
    conditional_coverage: CapabilityContract = Field(default_factory=CapabilityContract)
    timeout_seconds: PositiveFloat | None = None
    terminal_nonexecution_basis: CapabilityContract = Field(default_factory=CapabilityContract)
    shared_limits: SharedAccountLimits = Field(default_factory=SharedAccountLimits)
    evidence_mode: EvidenceMode = "unknown"
    version: Revision | None = None

    @model_validator(mode="after")
    def qualified_conditional_coverage(self):
        for identity in self.conditional_coverage.covered_fields:
            _require_fact_identity(identity)
        return self


class EffectIntent(WireModel):
    binding: RequestBinding
    operation: Identifier
    stage: Identifier
    action_id: Identifier
    provider_key: Identifier
    arguments: dict[str, JsonValue]
    argument_fingerprint: Hash
    profile_version: Revision
    process_version: Revision
    policy_version: Revision
    consent_revision: Revision
    expected_revisions: RevisionVector
    postcondition: dict[str, JsonValue]
    deadline: Timestamp
    decision_id: Identifier | None = None
    ownership_state_revision: Revision | None = None
    ownership_epoch: NonnegativeInt | None = None

    @model_validator(mode="after")
    def bound_identity(self):
        if self.argument_fingerprint != fingerprint(self.arguments):
            raise ValueError("Intent arguments do not match fingerprint")
        if self.action_id != stable_action_id(self.binding, self.operation, self.stage):
            raise ValueError("Intent action ID does not match binding/operation/stage")
        if self.consent_revision != self.binding.consent_revision:
            raise ValueError("Intent consent revision does not match binding")
        return self


class DispatchResult(WireModel):
    status: DispatchStatus
    provider_request_id: Identifier | None = None
    evidence_refs: list[Identifier] = Field(default_factory=list)
    reason: str | None = None


class VerificationResult(WireModel):
    status: VerificationStatus
    object_id: Identifier | None = None
    action_id: Identifier | None = None
    fingerprint: Hash | None = None
    postcondition: dict[str, JsonValue] | None = None
    evidence_refs: list[Identifier] = Field(default_factory=list)
    as_of: Timestamp | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def verified_requires_evidence(self):
        if self.status == "verified" and (not self.object_id or not self.action_id or not self.fingerprint
                or self.postcondition is None or not self.evidence_refs or self.as_of is None):
            raise ValueError("Verified effect requires identity, postcondition and authoritative evidence/as-of")
        return self


class RoleAllowance(WireModel):
    invocations: NonnegativeInt = 0
    max_invocations: NonnegativeInt
    usage: dict[str, NonnegativeFloat] = Field(default_factory=dict)
    usage_allowances: dict[str, NonnegativeFloat] = Field(default_factory=dict)
    cost: NonnegativeFloat = 0.0
    max_cost: NonnegativeFloat = 0.0


class AccountPressure(WireModel):
    account_id: Identifier
    concurrent_calls: NonnegativeInt = 0
    quota_consumed: NonnegativeInt = 0
    retry_after: Timestamp | None = None


class BudgetLedger(WireModel):
    case_id: Identifier
    deadline: Timestamp
    active_seconds: NonnegativeFloat = 0.0
    max_active_seconds: PositiveFloat = 120.0
    planner_calls: NonnegativeInt = 0
    max_planner_calls: NonnegativeInt = 4
    tool_calls: NonnegativeInt = 0
    max_tool_calls: NonnegativeInt = 24
    effects: NonnegativeInt = 0
    max_effects: NonnegativeInt = 6
    reserved_handoff_effects: NonnegativeInt = 1
    reconciliation_reads: dict[Identifier, NonnegativeInt] = Field(default_factory=dict)
    max_reconciliation_reads: NonnegativeInt = 3
    retries: dict[Identifier, NonnegativeInt] = Field(default_factory=dict)
    max_retries: NonnegativeInt = 1
    clarifications: NonnegativeInt = 0
    max_clarifications: NonnegativeInt = 2
    max_tool_seconds: PositiveFloat = 10.0
    role_allowances: dict[Identifier, RoleAllowance] = Field(default_factory=dict)
    shared_account_pressure: dict[Identifier, AccountPressure] = Field(default_factory=dict)


class StopState(WireModel):
    requested: bool = False
    requested_at: Timestamp | None = None
    reason: str | None = None


class PhaseCheckpoint(WireModel):
    binding: RequestBinding
    phase: Identifier
    next_gate: Identifier
    profile_version: Revision
    process_version: Revision
    policy_version: Revision
    processing_status: ProcessingStatus
    observations: list[AuthorityObservation] = Field(default_factory=list)
    question_id: Identifier | None = None
    awaited_fields: list[Identifier] = Field(default_factory=list)
    ownership_state: OwnerState = "unowned"
    ownership_state_revision: Revision | None = None
    ownership_epoch: NonnegativeInt = 0
    stop: StopState = Field(default_factory=StopState)
    budget: BudgetLedger
    deadline: Timestamp

    @model_validator(mode="after")
    def same_case_budget(self):
        if self.budget.case_id != self.binding.case_id:
            raise ValueError("Checkpoint budget belongs to another case")
        return self


class WaitState(WireModel):
    question_id: Identifier
    binding: RequestBinding
    origin: Identifier
    next_gate: Identifier
    recipient: Identifier
    owner_state_revision: Revision
    awaited_fields: list[Identifier]
    expires_at: Timestamp
    budget: BudgetLedger

    @model_validator(mode="after")
    def same_case_budget(self):
        if self.budget.case_id != self.binding.case_id:
            raise ValueError("Wait budget belongs to another case")
        return self


class ScopedReply(WireModel):
    question_id: Identifier
    binding: RequestBinding
    actor_id: Identifier
    proof_reference: Identifier
    request_revision: Revision
    consent_revision: Revision
    owner_state_revision: Revision
    fields: dict[str, JsonValue]
    received_at: Timestamp
    simulated: bool


class OperatorPacket(WireModel):
    packet_id: Identifier
    case_id: Identifier
    object_id: Identifier
    binding: RequestBinding
    packet_hash: Hash
    packet_revision: Revision
    owner: Identifier
    owner_state: OwnerState
    epoch: NonnegativeInt
    state_revision: Revision
    source_scope: list[Identifier]
    expires_at: Timestamp
    replay_id: Identifier

    @model_validator(mode="after")
    def same_binding(self):
        if self.case_id != self.binding.case_id or self.object_id != self.binding.object_id:
            raise ValueError("Operator packet case/object differs from binding")
        return self


class OperatorReceipt(WireModel):
    packet_id: Identifier
    packet_hash: Hash
    packet_revision: Revision
    binding: RequestBinding
    owner: Identifier
    epoch: NonnegativeInt
    state_revision: Revision
    status: Literal["accepted", "rejected", "pending", "outcome_unknown"]
    evidence_ref: Identifier | None = None
    received_at: Timestamp
    replay_id: Identifier
    simulated: bool


class OperatorDecision(WireModel):
    decision_id: Identifier
    packet_id: Identifier
    packet_hash: Hash
    packet_revision: Revision
    binding: RequestBinding
    owner: Identifier
    epoch: NonnegativeInt
    state_revision: Revision
    actor_id: Identifier
    proof_reference: Identifier
    decision: Literal["approve", "reject", "clarify", "stop"]
    scope: list[Identifier]
    expires_at: Timestamp
    replay_id: Identifier
    simulated: bool


class TransferIntent(WireModel):
    transfer_id: Identifier
    binding: RequestBinding
    case_id: Identifier
    packet_id: Identifier
    packet_hash: Hash
    packet_revision: Revision
    expected_owner: Identifier
    expected_state_revision: Revision
    expected_epoch: NonnegativeInt
    target_owner: Identifier
    expires_at: Timestamp

    @model_validator(mode="after")
    def same_binding(self):
        if self.case_id != self.binding.case_id:
            raise ValueError("Transfer case differs from binding")
        return self


class HumanOwnership(WireModel):
    binding: RequestBinding
    owner: Identifier
    epoch: NonnegativeInt
    state_revision: Revision
    packet_id: Identifier
    packet_hash: Hash
    packet_revision: Revision
    state: OwnerState
    acceptance_evidence: Identifier | None = None
    pending_evidence: Identifier | None = None
    transfer_id: Identifier | None = None


class TextSpan(WireModel):
    kind: Literal["text_span"]
    start: NonnegativeInt
    end: NonnegativeInt

    @model_validator(mode="after")
    def ordered(self):
        if self.end < self.start:
            raise ValueError("Text span ends before it starts")
        return self


class Region(WireModel):
    x: NonnegativeFloat
    y: NonnegativeFloat
    width: PositiveFloat
    height: PositiveFloat
    units: Literal["pixels", "normalized"]


class PageRegion(WireModel):
    kind: Literal["page_region"]
    page: Annotated[int, Field(ge=1)]
    region: Region | None = None


class AudioTime(WireModel):
    kind: Literal["audio_time"]
    start_seconds: NonnegativeFloat
    end_seconds: NonnegativeFloat

    @model_validator(mode="after")
    def ordered(self):
        if self.end_seconds < self.start_seconds:
            raise ValueError("Audio span ends before it starts")
        return self


class UnknownLocator(WireModel):
    kind: Literal["unknown"] = "unknown"
    reason: Identifier


Locator = Annotated[TextSpan | PageRegion | AudioTime | UnknownLocator, Field(discriminator="kind")]


class EvidenceAssertion(WireModel):
    artifact_id: Identifier
    content_hash: Hash
    lineage_hash: Hash
    locator: Locator
    uncertainty: Literal["unverified", "uncertain", "confirmed", "conflicting"]
    processing_receipt_id: Identifier
    claim: str


class ArtifactRecord(WireModel):
    artifact_id: Identifier
    original_hash: Hash
    mime_type: Identifier
    source: Identifier
    case_id: Identifier
    access: Literal["unknown", "synthetic", "public", "authorized", "restricted"]
    created_at: Timestamp
    lineage_hash: Hash
    parent_hashes: list[Hash] = Field(default_factory=list)
    source_reference: Identifier | None = None


class ActionProposal(WireModel):
    operation: Identifier
    stage: Identifier
    arguments: dict[str, JsonValue]
    evidence_refs: list[Identifier]


class AssertionsOutput(WireModel):
    kind: Literal["assertions"]
    assertions: list[EvidenceAssertion]


class TranscriptSegment(WireModel):
    text: str
    locator: Locator


class TranscriptOutput(WireModel):
    kind: Literal["transcript"]
    text: str
    segments: list[TranscriptSegment] = Field(default_factory=list)


class ProposalOutput(WireModel):
    kind: Literal["proposal"]
    proposal: ActionProposal


ProcessingOutput = Annotated[AssertionsOutput | TranscriptOutput | ProposalOutput, Field(discriminator="kind")]


class ProcessingReceipt(WireModel):
    invocation_id: Identifier
    role: ProcessorRole
    provider: Identifier
    requested_model: Identifier
    observed_model: Identifier | None = None
    provider_request_id: Identifier | None = None
    prompt_hash: Hash
    version: Revision
    input_hashes: list[Hash]
    # "actual" denotes the declared actual provider/coding role, not a parser.
    mode: Literal["intake_only", "deterministic", "recorded_replay", "replay", "synthetic", "actual", "unavailable"]
    status: ProcessingStatus
    latency_seconds: NonnegativeFloat
    usage: dict[str, NonnegativeFloat]
    output: ProcessingOutput | None = None
    output_hashes: list[Hash] = Field(default_factory=list)
    output_refs: list[Identifier] = Field(default_factory=list)
    available_coordinates: list[Locator] = Field(default_factory=list)
    processed_at: Timestamp
    reason: str | None = None


class CampaignPermit(WireModel):
    campaign_id: Identifier
    permit_hash: Hash
    input_hashes: list[Hash]
    role: ProcessorRole
    provider: Identifier
    model: Identifier
    endpoint: Identifier
    privacy_approval: Identifier
    rights_approval: Identifier
    max_cost: NonnegativeFloat
    max_usage: dict[str, NonnegativeFloat]
    max_invocations: NonnegativeInt
    expires_at: Timestamp
    approval_receipt: Identifier
    mode: ApprovalMode


class ProcessorIdentity(WireModel):
    case_id: Identifier
    generation: Identifier
    role: ProcessorRole
    campaign_id: Identifier
    permit_hash: Hash
    input_hashes: list[Hash]
    provider: Identifier
    model: Identifier
    endpoint: Identifier
    prompt_hash: Hash
    version: Revision
    profile_version: Revision
    process_version: Revision
    deadline: Timestamp


class InvocationRequest(WireModel):
    identity: ProcessorIdentity
    invocation_id: Identifier
    requested_usage: dict[str, NonnegativeFloat]
    worst_case_cost: NonnegativeFloat


class InvocationReservation(WireModel):
    identity: ProcessorIdentity
    invocation_id: Identifier
    reserved_usage: dict[str, NonnegativeFloat]
    worst_case_cost: NonnegativeFloat
    status: Literal["reserved", "consumed", "outcome_unknown", "completed", "failed"]
    case_debit: NonnegativeInt
    role_debit: NonnegativeInt
    campaign_debit: NonnegativeInt
    reserved_at: Timestamp


class GateDecision(WireModel):
    allowed: bool
    reason: Identifier
    verification: VerificationResult | None = None

    @model_validator(mode="after")
    def denial_is_rejection(self):
        if not self.allowed and (self.verification is None or self.verification.status != "rejected"):
            raise ValueError("Gate denial requires rejected verification")
        return self


class CaseResult(WireModel):
    status: Literal["authorized", "denied", "error"]
    correlation_id: Identifier | None = None
    reason: GenericReasonCode | None = None
    binding: RequestBinding | None = None
    fingerprint: Hash | None = None
    result_version: Revision | None = None
    as_of: Timestamp | None = None
    effects: dict[Identifier, VerificationResult] = Field(default_factory=dict)
    stop: StopState = Field(default_factory=StopState)
    wait_status: Literal["none", "pending", "expired", "answered"] = "none"
    handoff_status: Literal["none", "pending", "accepted", "rejected", "outcome_unknown"] = "none"
    media_status: Literal["none", "pending", "completed", "failed", "unavailable", "outcome_unknown"] = "none"
    evidence_refs: list[Identifier] = Field(default_factory=list)
    policy_refs: list[Identifier] = Field(default_factory=list)
    rationale: str | None = None
    historical: bool = False

    @model_serializer(mode="wrap")
    def scoped_wire(self, handler):
        wire = handler(self)
        if self.status != "authorized":
            return {key: wire[key] for key in ("status", "correlation_id", "reason") if key in wire}
        return wire

    @model_validator(mode="after")
    def access_scope(self):
        if self.status == "authorized":
            if (self.binding is None or self.fingerprint is None or self.result_version is None
                    or self.as_of is None or self.rationale is None):
                raise ValueError("Authorized result requires binding, fingerprint, version/as-of and rationale")
            if self.fingerprint != self.binding.fingerprint:
                raise ValueError("Result fingerprint differs from historical request binding")
        elif (self.correlation_id is None or self.reason is None or self.binding is not None
                or self.fingerprint is not None or self.result_version is not None or self.as_of is not None
                or self.effects or self.evidence_refs or self.policy_refs or self.rationale is not None
                or self.historical or self.stop != StopState() or self.wait_status != "none"
                or self.handoff_status != "none" or self.media_status != "none"):
            raise ValueError("Denied/error response contains only correlation identity and generic reason")
        return self

    @property
    def case_id(self) -> str:
        return self.binding.case_id if self.binding is not None else self.correlation_id

    @property
    def exportable(self) -> bool:
        return True


class SavedResult(CaseResult):
    status: Literal["authorized"] = "authorized"
    binding: RequestBinding
    fingerprint: Hash
    result_version: Revision
    as_of: Timestamp
    rationale: str


class ProcessEdge(WireModel):
    origin: Identifier
    target: Identifier
    operation: Identifier | None = None
    condition: Identifier | None = None


class Prerequisite(WireModel):
    phase: Identifier
    authority: Identifier
    fact: Identifier
    expected: JsonValue


class WaitContract(WireModel):
    phase: Identifier
    next_gate: Identifier
    awaited_fields: list[Identifier]
    recipient_role: Identifier
    expiry_seconds: PositiveFloat


class ApprovalContract(WireModel):
    operation: Identifier
    required_scope: list[Identifier]
    approver_role: Identifier


class CompletionContract(WireModel):
    phase: Identifier
    required_operations: list[Identifier]


class ProcessSpec(WireModel):
    process_id: Identifier
    version: Revision
    release_hash: Hash
    phases: list[Identifier]
    edges: list[ProcessEdge]
    operations: list[Identifier]
    prerequisites: list[Prerequisite] = Field(default_factory=list)
    waits: list[WaitContract] = Field(default_factory=list)
    approvals: list[ApprovalContract] = Field(default_factory=list)
    acknowledgements: dict[Identifier, CapabilityContract] = Field(default_factory=dict)
    readbacks: dict[Identifier, CapabilityContract] = Field(default_factory=dict)
    completion: CompletionContract


class FieldMapping(WireModel):
    source_path: Identifier
    canonical_field: Identifier
    value_map: dict[str, JsonValue] = Field(default_factory=dict)


class EnvironmentProfile(WireModel):
    profile_id: Identifier
    version: Revision
    release_hash: Hash
    mappings: dict[Identifier, FieldMapping]
    authorities: dict[Identifier, Identifier]
    capabilities: dict[Identifier, OperationCapability]
    policy_hash: Hash
    process_hash: Hash
    # Versioned ProcessSpecs are resolved inside this immutable bundle.
    processes: dict[Identifier, ProcessSpec] = Field(default_factory=dict)


class AdaptationDiff(WireModel):
    path: Identifier
    before: JsonValue
    after: JsonValue


class MigrationPlan(WireModel):
    strategy: Literal["preserve", "compatible", "explicit_migration"]
    affected_contracts: list[Identifier]


class AdaptationProposal(WireModel):
    proposal_id: Identifier
    source_hash: Hash
    baseline_hash: Hash
    proposal_hash: Hash
    diff: list[AdaptationDiff]
    test_hash: Hash
    migration: MigrationPlan
    agent_hash: Hash


class HumanReviewApproval(WireModel):
    proposal_hash: Hash
    regression_hash: Hash
    reviewer_id: Identifier
    proof_reference: Identifier
    scope: list[Identifier]
    decision: Literal["approved", "rejected"]
    reviewed_at: Timestamp
    mode: ApprovalMode


class ReviewPacket(WireModel):
    proposal_hash: Hash
    regression_hash: Hash
    affected_pending_contracts: list[Identifier]
    approval: HumanReviewApproval | None = None
    proposed_profile: EnvironmentProfile | None = None
    proposed_processes: dict[Identifier, ProcessSpec] = Field(default_factory=dict)
    compatibility: MigrationPlan | None = None


class ReleaseReceipt(WireModel):
    version: Revision
    release_hash: Hash
    proposal_hash: Hash
    regression_hash: Hash
    profile_hash: Hash
    process_hash: Hash
    policy_hash: Hash
    preserved_contract_hashes: list[Hash]
    approval: HumanReviewApproval
    released_at: Timestamp


class ExportReceipt(WireModel):
    supplied_case_id: str
    output_name: Identifier | None = None
    output_hash: Hash | None = None
    status: Literal["written", "failed"]
    failure: str | None = None
    as_of: Timestamp


class BatchReceipt(WireModel):
    supplied_case_ids: list[str]
    exports: list[ExportReceipt]
    deadline: Timestamp
    active_seconds: NonnegativeFloat
    as_of: Timestamp
    measured_reserve_seconds: NonnegativeFloat


class AssessmentSources(WireModel):
    source_hash: Hash
    reference_hash: Hash
    label_hash: Hash
    rubric_hash: Hash
    lineage_hash: Hash


class Denominators(WireModel):
    total_cases: NonnegativeInt
    included_cases: NonnegativeInt
    ambiguous_cases: NonnegativeInt
    excluded_cases: NonnegativeInt


class AuditFinding(WireModel):
    requirement_id: Identifier
    severity: Literal["info", "warning", "error"]
    reason: Identifier
    evidence_refs: list[Identifier]


class LedgerAudit(AssessmentSources, Denominators):
    findings: list[AuditFinding]


class EffectVerdict(WireModel):
    verdict: Literal["correct", "incorrect", "ambiguous", "unassessed"]
    evidence_refs: list[Identifier]
    reason: str | None = None


class RepeatabilityResult(WireModel):
    runs: NonnegativeInt
    agreements: NonnegativeInt


class SensitivityResult(WireModel):
    trials: NonnegativeInt
    detected: NonnegativeInt


class NoiseResult(WireModel):
    trials: NonnegativeInt
    disagreements: NonnegativeInt


class CaseAssessment(AssessmentSources):
    case_id: Identifier
    effect_verdicts: dict[Identifier, EffectVerdict]
    repeatability: RepeatabilityResult
    sensitivity: SensitivityResult
    noise: NoiseResult
    qualification_limits: list[Identifier]


class QualificationReceipt(AssessmentSources, Denominators):
    candidate_hash: Hash
    assessment_hashes: list[Hash]
    status: Literal["rehearsal", "protected", "incomplete", "qualified"]
    qualification_limits: list[Identifier]
    as_of: Timestamp


class DrillWait(WireModel):
    case_id: Identifier
    question_id: Identifier
    started_at: Timestamp
    ended_at: Timestamp | None = None


class DrillReceipt(WireModel):
    workload_hash: Hash
    candidate_hash: Hash
    baseline_hash: Hash
    result_hash: Hash
    started_at: Timestamp
    ended_at: Timestamp
    active_seconds: NonnegativeFloat
    wall_seconds: NonnegativeFloat
    waits: list[DrillWait]
    partial_case_ids: list[Identifier]
    mode: Literal["rehearsal", "protected"]


class IsolationProbe(WireModel):
    name: Identifier
    enforced: bool
    evidence_ref: Identifier


class IsolationReceipt(WireModel):
    candidate_hash: Hash
    workload_hash: Hash
    result_hash: Hash
    identity_hash: Hash
    custody_hash: Hash
    probes: list[IsolationProbe]
    status: Literal["rehearsal", "protected", "failed"]
    observed_at: Timestamp


class SourceReleaseReceipt(WireModel):
    candidate_hash: Hash
    file_hashes: dict[Identifier, Hash]
    rights_hash: Hash
    dependency_hash: Hash
    release_hash: Hash
    created_at: Timestamp


class CommandReceipt(WireModel):
    command: list[Identifier]
    exit_code: int
    artifact_hashes: dict[Identifier, Hash]


class ReproductionReceipt(WireModel):
    candidate_hash: Hash
    commands: list[CommandReceipt]
    observed_artifact_hashes: dict[Identifier, Hash]
    started_at: Timestamp
    ended_at: Timestamp


class RequirementReadiness(WireModel):
    requirement_id: Identifier
    status: Literal["satisfied", "missing", "invalid"]
    evidence_refs: list[Identifier]
    reason: Identifier


class ImplementationAudit(WireModel):
    candidate_hash: Hash
    requirements: list[RequirementReadiness]
    missing_evidence: list[Identifier]
    invalid_evidence: list[Identifier]
    audited_at: Timestamp
