"""Closed content-bound operator contracts, selected by a trusted capability.

Snapshots and digests are data. Only comparison with current provider-owned
facts establishes source permission; these helpers never grant permission.
"""
import json
from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from .contracts import (EvidenceAssertion, Hash, Identifier, NonnegativeInt, OperatorPacket,
                        OwnerState, RequestBinding, Revision, Timestamp, WireModel)
from .identity import fingerprint
from .process import material_fields

CONTRACT = "packet-content-v1"
MAX_CONTENT_BYTES = 256 * 1024
MAX_TEXT_BYTES = 16 * 1024
MAX_ORIGINALS, MAX_EXTRACTS, MAX_HISTORY, MAX_STOPS = 64, 128, 64, 64
PACKET_FIELDS = frozenset({"operator.packet_catalog", "operator.packet_access",
                          "ownership.owner", "ownership.state", "ownership.state_revision", "ownership.epoch"})
ARGUMENT_KEYS = frozenset({"packet_id", "packet_revision", "packet_hash", "recipient",
                           "packet_contract", "content_hash", "content"})
BASES = {
    "permission_basis": "packet-content-v1: current sender/operator catalog grant",
    "acknowledgement": "packet-content-v1: queue acknowledgement only",
    "readback": "packet-content-v1: immutable original content-store receipt",
    "conditional_coverage": "packet-content-v1: atomic current source and owner comparison",
}
MANIFEST_EVIDENCE = "synthetic-packet-manifest-v1"


def packet_enabled(profile):
    """A host-selected typed profile, never a body marker, selects semantics."""
    if profile is None:
        return False
    cap = profile.capabilities.get("enqueue_handoff")
    if cap is None or cap.version != CONTRACT:
        return False
    if profile.version not in {"v1.3", "v1.4"} or cap.operation != "enqueue_handoff" or cap.authority != "operator" or cap.evidence_mode != "synthetic":
        raise ValueError("Unregistered packet capability")
    for name, basis in BASES.items():
        contract = getattr(cap, name)
        if contract.status != "supported" or contract.basis != basis or contract.evidence_ref != MANIFEST_EVIDENCE:
            raise ValueError("Unregistered packet capability")
    coverage = cap.conditional_coverage.covered_fields
    if set(coverage) != material_fields("enqueue_handoff") | PACKET_FIELDS or len(coverage) != len(set(coverage)):
        raise ValueError("Incomplete packet conditional coverage")
    if any(profile.authorities.get(key) != key.partition(".")[0] for key in PACKET_FIELDS):
        raise ValueError("Unregistered packet authority")
    return True


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate packet JSON field")
        result[key] = value
    return result


def _ordered(items, key):
    identities = [getattr(item, key) for item in items]
    if len(identities) != len(set(identities)):
        raise ValueError("Duplicate packet identity")
    return sorted(items, key=lambda item: getattr(item, key))


def _text(value):
    if len(value.encode("utf-8")) > MAX_TEXT_BYTES:
        raise ValueError("Packet text exceeds finite contract limit")
    return value


class PacketModel(WireModel):
    @field_validator("*", mode="after")
    @classmethod
    def utc_timestamps(cls, value):
        return value.astimezone(timezone.utc) if isinstance(value, datetime) else value

    @classmethod
    def model_validate_json(cls, json_data, **kwargs):
        # Pydantic's JSON decoder accepts duplicate keys; source contracts do not.
        value = json.loads(json_data, object_pairs_hook=_pairs,
                           parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Nonfinite packet number")))
        return cls.model_validate(value, **kwargs)


class PacketObservationRefV1(PacketModel):
    identity: Identifier
    revision: Revision
    evidence_ref: Identifier


class PacketSourceIdentityV1(PacketModel):
    version: Literal["packet-source-v1"] = "packet-source-v1"
    binding: RequestBinding
    packet_id: Identifier
    packet_revision: Revision
    packet_hash: Hash
    observations: Annotated[list[PacketObservationRefV1], Field(max_length=64)]
    recipient: Identifier
    owner: Identifier
    owner_state: OwnerState
    state_revision: Revision
    epoch: NonnegativeInt

    @field_validator("observations")
    @classmethod
    def sorted_observations(cls, value):
        return _ordered(value, "identity")


class PacketOriginalRefV1(PacketModel):
    version: Literal["packet-original-v1"] = "packet-original-v1"
    artifact_id: Identifier
    case_id: Identifier
    original_hash: Hash
    mime_type: Identifier
    source_handle: Identifier
    source_hash: Hash
    lineage_hash: Hash
    observed_at: Timestamp

    @field_validator("source_handle")
    @classmethod
    def opaque_handle(cls, value):
        if any(character in value for character in "/\\:") or any(character.isspace() for character in value):
            raise ValueError("Original source handle must be an opaque registry identifier")
        return value


class PacketExtractV1(PacketModel):
    version: Literal["packet-extract-v1"] = "packet-extract-v1"
    extract_id: Identifier
    extract_reference: Identifier
    original_hash: Hash
    content_hash: Hash
    content: str
    processing_receipt_reference: Identifier
    assertion: EvidenceAssertion

    _bounded_text = field_validator("content")(_text)

    @model_validator(mode="after")
    def extraction_links(self):
        _text(self.assertion.claim)
        if (self.assertion.content_hash != self.content_hash
                or self.assertion.processing_receipt_id != self.processing_receipt_reference):
            raise ValueError("Extract processing links disagree")
        return self


class PacketRestrictionV1(PacketModel):
    version: Literal["packet-restriction-v1"] = "packet-restriction-v1"
    restriction_id: Identifier
    code: Literal["unavailable", "recipient_denied", "processing_unknown"]
    display_label: str

    _bounded_text = field_validator("display_label")(_text)


class PacketCatalogV1(PacketModel):
    version: Literal["packet-catalog-v1"] = "packet-catalog-v1"
    case_id: Identifier
    object_id: Identifier
    complete: bool
    revision: Revision
    relevant_set_id: Identifier
    originals: Annotated[list[PacketOriginalRefV1], Field(max_length=MAX_ORIGINALS)]
    extracts: Annotated[list[PacketExtractV1], Field(max_length=MAX_EXTRACTS)]
    restrictions: Annotated[list[PacketRestrictionV1], Field(max_length=MAX_ORIGINALS)]

    @field_validator("originals", "extracts", "restrictions")
    @classmethod
    def sorted_unique_inventory(cls, value, info):
        return _ordered(value, {"originals": "artifact_id", "extracts": "extract_id", "restrictions": "restriction_id"}[info.field_name])

    @model_validator(mode="after")
    def lineage_links(self):
        originals = {item.artifact_id: item for item in self.originals}
        if any(item.case_id != self.case_id for item in self.originals):
            raise ValueError("Catalog contains a foreign original")
        for extract in self.extracts:
            original = originals.get(extract.assertion.artifact_id)
            if (original is None or extract.original_hash != original.original_hash
                    or extract.assertion.lineage_hash != original.lineage_hash):
                raise ValueError("Extract does not link to its catalog original")
        return self


class PacketOriginalGrantV1(PacketModel):
    artifact_id: Identifier
    original_hash: Hash


class PacketExtractGrantV1(PacketModel):
    extract_id: Identifier
    content_hash: Hash


class PacketAccessSnapshotV1(PacketModel):
    version: Literal["packet-access-v1"] = "packet-access-v1"
    decision_id: Identifier
    revision: Revision
    case_id: Identifier
    object_id: Identifier
    sender: Identifier
    recipient: Identifier
    role: Literal["operator"]
    purpose: Literal["operator_packet"]
    catalog_hash: Hash
    permitted_originals: Annotated[list[PacketOriginalGrantV1], Field(max_length=MAX_ORIGINALS)]
    permitted_extracts: Annotated[list[PacketExtractGrantV1], Field(max_length=MAX_EXTRACTS)]
    issued_at: Timestamp
    expires_at: Timestamp
    metadata_restrictions: Annotated[list[PacketRestrictionV1], Field(max_length=MAX_ORIGINALS)]

    @field_validator("permitted_originals", "permitted_extracts", "metadata_restrictions")
    @classmethod
    def sorted_unique_grants(cls, value, info):
        return _ordered(value, {"permitted_originals": "artifact_id", "permitted_extracts": "extract_id", "metadata_restrictions": "restriction_id"}[info.field_name])

    @model_validator(mode="after")
    def finite_expiry(self):
        if self.expires_at <= self.issued_at:
            raise ValueError("Access requires a finite positive expiry")
        return self


class PacketEffectHistoryV1(PacketModel):
    version: Literal["packet-history-v1"] = "packet-history-v1"
    binding: RequestBinding
    action_id: Identifier
    provider_key: Identifier
    argument_fingerprint: Hash
    operation: Literal["reschedule", "register_goods_refusal", "register_service_refusal", "create_return",
                       "send_clarification", "send_status", "enqueue_handoff", "transfer_owner"]
    stage: Identifier
    profile_version: Revision
    process_version: Revision
    policy_version: Revision
    dispatch_state: Literal["prepared", "dispatching", "rejected", "acknowledged", "outcome_unknown", "unknown"]
    verification_state: Literal["unverified", "verified", "rejected", "pending", "outcome_unknown", "conflict"]
    as_of: Timestamp
    evidence_refs: Annotated[list[Identifier], Field(max_length=64)]
    unresolved: bool

    @model_validator(mode="after")
    def independent_verification(self):
        if self.verification_state == "verified" and (self.unresolved or not self.evidence_refs):
            raise ValueError("Verified history needs independent evidence and resolved state")
        return self


class PacketGenerationStopV1(PacketModel):
    version: Literal["packet-stop-v1"] = "packet-stop-v1"
    generation: Identifier
    # Local stop provenance can prove a stop record while its timestamp is
    # unknown. Explicit null preserves that uncertainty; no time is fabricated.
    requested_at: Timestamp | None
    evidence_ref: Identifier


class PacketPolicyRefV1(PacketModel):
    version: Literal["packet-policy-v1"] = "packet-policy-v1"
    profile_id: Identifier
    profile_version: Revision
    profile_hash: Hash
    process_version: Revision
    process_hash: Hash
    policy_id: Literal["synthetic-test-policy-v1"]
    policy_hash: Hash
    observed_version: Revision
    references: Annotated[list[Identifier], Field(max_length=64)]

    @field_validator("references")
    @classmethod
    def sorted_refs(cls, value):
        if len(value) != len(set(value)):
            raise ValueError("Duplicate policy reference")
        return sorted(value)


class PacketUntrustedRecordV1(PacketModel):
    record_id: Identifier
    description: str
    source_refs: Annotated[list[Identifier], Field(min_length=1, max_length=64)]
    trust: Literal["untrusted_evidence"] = "untrusted_evidence"

    _bounded_text = field_validator("description")(_text)


class PacketContentV1(PacketModel):
    version: Literal["packet-content-v1"] = CONTRACT
    source: PacketSourceIdentityV1
    catalog: PacketCatalogV1
    access: PacketAccessSnapshotV1
    as_of: Timestamp
    history: Annotated[list[PacketEffectHistoryV1], Field(max_length=MAX_HISTORY)]
    generation_stops: Annotated[list[PacketGenerationStopV1], Field(max_length=MAX_STOPS)]
    policy: PacketPolicyRefV1
    conflicts: Annotated[list[PacketUntrustedRecordV1], Field(max_length=64)]
    unknowns: Annotated[list[PacketUntrustedRecordV1], Field(max_length=64)]
    disposition: Literal["review_facts", "refund_review", "coverage_review", "internal_case_review"]
    expires_at: Timestamp

    @field_validator("history", "generation_stops", "conflicts", "unknowns")
    @classmethod
    def sorted_records(cls, value, info):
        return _ordered(value, {"history": "action_id", "generation_stops": "generation",
                                "conflicts": "record_id", "unknowns": "record_id"}[info.field_name])

    @model_validator(mode="after")
    def bounded_content(self):
        binding = self.source.binding
        if any(item.binding.case_id != binding.case_id or item.binding.object_id != binding.object_id for item in self.history):
            raise ValueError("History contains a foreign case/object")
        if self.expires_at <= self.as_of or self.expires_at > self.access.expires_at:
            raise ValueError("Content expiry is outside source access")
        encoded = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode("utf-8")
        if len(encoded) > MAX_CONTENT_BYTES:
            raise ValueError("Packet content exceeds finite contract limit")
        return self


class PreparedPacketV1(PacketModel):
    version: Literal["prepared-packet-v1"] = "prepared-packet-v1"
    packet: OperatorPacket
    content: PacketContentV1
    content_hash: Hash
    checkpoint_hash: Hash

    @model_validator(mode="after")
    def immutable_projection(self):
        source, packet = self.content.source, self.packet
        validate_packet_scope(self.content.catalog, self.content.access, case_id=source.binding.case_id,
            object_id=source.binding.object_id, sender=source.binding.principal_id, recipient=source.recipient,
            now=self.content.as_of)
        if (self.content_hash != fingerprint(self.content.model_dump(mode="json")) or packet.binding != source.binding
                or any(getattr(packet, key) != getattr(source, key) for key in
                       ("packet_id", "packet_hash", "packet_revision", "owner", "owner_state", "epoch", "state_revision"))
                or packet.expires_at != self.content.expires_at
                or set(packet.source_scope) != {ref.identity for ref in source.observations}
                or len(packet.source_scope) != len(set(packet.source_scope))):
            raise ValueError("Prepared packet projection/digest disagrees")
        return self


class PacketAcceptanceV1(PacketModel):
    version: Literal["packet-acceptance-v1"] = "packet-acceptance-v1"
    acceptance_id: Identifier
    evidence_ref: Identifier
    accepted_at: Timestamp
    content_hash: Hash
    recipient: Identifier
    generation: Identifier
    action_id: Identifier
    provider_key: Identifier


class PacketContentReceiptV1(PacketModel):
    version: Literal["packet-content-receipt-v1"] = "packet-content-receipt-v1"
    packet_id: Identifier
    packet_hash: Hash
    packet_revision: Revision
    content_hash: Hash
    catalog_revision: Revision
    access_revision: Revision
    recipient: Identifier
    generation: Identifier
    action_id: Identifier
    provider_key: Identifier
    argument_fingerprint: Hash
    owner: Identifier
    state_revision: Revision
    epoch: NonnegativeInt
    stored_at: Timestamp
    evidence_ref: Identifier
    content_status: Literal["stored"]
    owner_status: Literal["pending", "accepted"]
    acceptance: PacketAcceptanceV1 | None = None

    @model_validator(mode="after")
    def acceptance_is_separate(self):
        if self.owner_status == "pending" and self.acceptance is not None:
            raise ValueError("Pending original receipt cannot contain acceptance")
        if self.owner_status == "accepted":
            a = self.acceptance
            if a is None or any(getattr(a, key) != getattr(self, key) for key in
                                ("content_hash", "recipient", "generation", "action_id", "provider_key")) or a.accepted_at < self.stored_at:
                raise ValueError("Acceptance is not bound to original digest/identity")
        return self


def validate_packet_scope(catalog, access, *, case_id, object_id, sender, recipient, now):
    catalog = PacketCatalogV1.model_validate(catalog.model_dump() if isinstance(catalog, PacketCatalogV1) else catalog)
    access = PacketAccessSnapshotV1.model_validate(access.model_dump() if isinstance(access, PacketAccessSnapshotV1) else access)
    if (not catalog.complete or catalog.case_id != case_id or catalog.object_id != object_id
            or access.case_id != case_id or access.object_id != object_id or access.sender != sender
            or access.recipient != recipient or not access.issued_at <= now < access.expires_at
            or access.catalog_hash != fingerprint(catalog.model_dump(mode="json"))
            or [(x.artifact_id, x.original_hash) for x in catalog.originals] != [(x.artifact_id, x.original_hash) for x in access.permitted_originals]
            or [(x.extract_id, x.content_hash) for x in catalog.extracts] != [(x.extract_id, x.content_hash) for x in access.permitted_extracts]
            or catalog.restrictions != access.metadata_restrictions):
        raise ValueError("Packet source scope denied")
    return catalog, access


def validate_packet_arguments(arguments, *, binding=None):
    if set(arguments) != ARGUMENT_KEYS or arguments["packet_contract"] != CONTRACT:
        raise ValueError("Packet arguments must exactly match registered contract")
    content = PacketContentV1.model_validate(arguments["content"])
    source = content.source
    if (arguments["content_hash"] != fingerprint(content.model_dump(mode="json"))
            or any(arguments[key] != getattr(source, key) for key in ("packet_id", "packet_revision", "packet_hash", "recipient"))
            or binding is not None and source.binding != binding):
        raise ValueError("Packet argument commitments disagree")
    validate_packet_scope(content.catalog, content.access, case_id=source.binding.case_id,
                          object_id=source.binding.object_id, sender=source.binding.principal_id,
                          recipient=source.recipient, now=content.as_of)
    return content


def validate_packet_policy(content, profile, *, process_version, policy_version):
    policy = content.policy
    if (policy.profile_id != profile.profile_id or policy.profile_version != profile.version
            or policy.profile_hash != profile.release_hash or policy.process_hash != profile.process_hash
            or policy.policy_hash != profile.policy_hash or policy.process_version != process_version
            or policy.observed_version != policy_version or policy.references != ["synthetic-test-policy-v1"]):
        raise ValueError("Packet policy is not the trusted frozen profile")


def packet_postcondition(arguments):
    content = validate_packet_arguments(arguments)
    return {"packet_id": content.source.packet_id, "packet_hash": content.source.packet_hash,
            "packet_revision": content.source.packet_revision, "content_hash": arguments["content_hash"],
            "catalog_revision": content.catalog.revision, "access_revision": content.access.revision,
            "recipient": content.source.recipient, "content_status": "stored", "owner_status": "pending"}
