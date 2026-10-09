"""Closed offline assessment data; content hashes never establish trusted origin.

Only trusted host code constructs these records. No mode or approval flag can
turn this foundation into actual processing, calibrated labels or a holdout.
"""
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Literal

from pydantic import Field, JsonValue, model_validator
from proofkey.contracts import (CanonicalRequest, CaseAssessment, Hash, Identifier,
                               WireModel)
from proofkey.identity import fingerprint, validate_json

MAX_POSITIONS = 256
MAX_BYTES = 1_048_576


def canonical_bytes(value):
    validate_json(value)
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                         allow_nan=False).encode("utf-8")
    if len(encoded) > MAX_BYTES:
        raise ValueError("Assessment content exceeds bound")
    return encoded


def digest_bytes(value):
    if type(value) is not bytes or len(value) > MAX_BYTES:
        raise ValueError("Bounded exact bytes required")
    return sha256(value).hexdigest()


def require_hash(value):
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError("Strict SHA-256 identity required")
    return value


def strict_loads(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Invalid assessment JSON")
            result[key] = value
        return result
    if type(raw) is not bytes or len(raw) > MAX_BYTES:
        raise ValueError("Bounded exact bytes required")
    try:
        result = json.loads(raw, object_pairs_hook=pairs,
                            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Invalid assessment JSON")))
        validate_json(result)
    except (TypeError, ValueError, UnicodeError, RecursionError):
        raise ValueError("Invalid assessment JSON") from None
    return result


class EffectRequirement(WireModel):
    status: Literal["verified", "rejected", "pending", "outcome_unknown", "absent"]
    postcondition: dict[str, JsonValue]
    requires_evidence: bool

    @model_validator(mode="after")
    def absence_has_no_completion(self):
        if self.status == "absent" and (self.postcondition or self.requires_evidence):
            raise ValueError("Absent effect cannot assert completion evidence")
        return self


class SourceDescriptor(WireModel):
    origin: Literal["synthetic"]
    family: Literal["rescheduling", "whole_order_return", "service_handoff"]
    generator: Identifier
    fault_instructions: list[Identifier]
    rights: Literal["rehearsal-only"]


class LabelDescriptor(WireModel):
    version: Identifier
    mode: Literal["replay", "unknown"]
    observed_model: Identifier | None
    status: Literal["provisional_llm"]
    campaign: Literal["none"]


class RubricDescriptor(WireModel):
    version: Identifier
    status: Literal["provisional"]
    anchor: Identifier
    forbidden_effects: list[Literal["physical_receipt", "refund", "payment", "internal_case_creation"]]


class LineageDescriptor(WireModel):
    version: Identifier
    processing: Literal["unavailable", "synthetic", "recorded_replay", "deterministic"]
    runtime_driver: Literal["pending"]
    obligations: list[Identifier]

    @model_validator(mode="after")
    def obligations_are_pending(self):
        if not set(self.obligations) <= {f"R{n:02d}" for n in range(1, 16)}:
            raise ValueError("Known pending obligation required")
        return self


class GraderDescriptor(WireModel):
    route: Identifier
    model: Identifier | None = None
    requested_model: Identifier | None = None
    observed_model: Identifier | None = None
    prompt: JsonValue = None
    version: Identifier = "unspecified"
    configuration: dict[str, JsonValue] = Field(default_factory=dict)


class Reference(WireModel):
    case_id: Identifier
    input_hash: Hash
    source_hash: Hash
    required_behavior: dict[Identifier, EffectRequirement]
    authority_assumptions: list[Identifier]
    provenance: list[Identifier]
    ambiguity: list[Identifier]
    exclusion: Identifier | None
    label: dict[str, JsonValue]
    rubric: dict[str, JsonValue]
    lineage: dict[str, JsonValue]
    reference_hash: Hash
    label_hash: Hash
    rubric_hash: Hash
    lineage_hash: Hash

    @model_validator(mode="after")
    def content_joins(self):
        LabelDescriptor.model_validate(self.label)
        RubricDescriptor.model_validate(self.rubric)
        LineageDescriptor.model_validate(self.lineage)
        data = self.model_dump(mode="json")
        required = {key: data[key] for key in ("case_id", "input_hash", "source_hash", "required_behavior",
                    "authority_assumptions", "provenance", "ambiguity", "exclusion")}
        if self.reference_hash != fingerprint(required):
            raise ValueError("Assessment reference identity mismatch")
        for name in ("label", "rubric", "lineage"):
            if data[name + "_hash"] != fingerprint(data[name]):
                raise ValueError("Assessment metadata identity mismatch")
        if not self.required_behavior or not self.authority_assumptions or not self.provenance:
            raise ValueError("Independent provisional behavior evidence required")
        if self.label.get("status") != "provisional_llm" or self.label.get("mode") not in {"replay", "unknown"}:
            raise ValueError("Only provisional offline reference labels supported")
        if self.rubric.get("status") != "provisional":
            raise ValueError("Only provisional offline rubric supported")
        canonical_bytes(data)
        return self

    def sources(self):
        return {name: getattr(self, name) for name in ("source_hash", "reference_hash", "label_hash", "rubric_hash", "lineage_hash")}


class CaseRow(WireModel):
    case_id: Identifier
    source: dict[str, JsonValue]
    source_hash: Hash
    independence_group: Identifier
    tags: list[Identifier]
    control: Literal["positive", "unsafe", "insufficient"]
    input: CanonicalRequest
    input_hash: Hash
    reference: Reference
    split: Literal["development", "validation", "rehearsal"]
    split_seed: int
    allocation: Literal["before_feedback"]
    feedback: bool
    profile_name: Identifier
    profile_hash: Hash

    @model_validator(mode="after")
    def joins(self):
        SourceDescriptor.model_validate(self.source)
        if self.source.get("origin") != "synthetic" or self.source.get("rights") != "rehearsal-only":
            raise ValueError("Safe synthetic rehearsal source required")
        if self.source_hash != fingerprint(self.source) or self.input_hash != fingerprint(self.input.model_dump(mode="json")):
            raise ValueError("Assessment input/source identity mismatch")
        if (self.case_id != self.input.case_id or self.case_id != self.reference.case_id
                or self.input_hash != self.reference.input_hash or self.source_hash != self.reference.source_hash):
            raise ValueError("Assessment case identity mismatch")
        if self.profile_name not in {"flat-v1", "flat-v1.1", "flat-v1.2", "flat-v1.3", "nested-v1", "nested-v1.1", "nested-v1.2", "nested-v1.3"}:
            raise ValueError("Known offline profile required")
        canonical_bytes(self.model_dump(mode="json"))
        return self


class EffectEvidence(WireModel):
    status: Literal["verified", "rejected", "pending", "outcome_unknown"]
    postcondition: dict[str, JsonValue]
    evidence_refs: list[Identifier]


class ObservedOutput(WireModel):
    effects: dict[Identifier, EffectEvidence]
    forbidden_effects: list[Identifier]


@dataclass(frozen=True)
class Observation:
    case_id: str
    independence_group: str
    candidate_hash: str
    input_hash: str
    source_hash: str
    reference_hash: str
    label_hash: str
    rubric_hash: str
    lineage_hash: str
    output_bytes: bytes | None
    output_hash: str | None
    error: bytes | None

    def __post_init__(self):
        for name in ("candidate_hash", "input_hash", "source_hash", "reference_hash", "label_hash", "rubric_hash", "lineage_hash"):
            require_hash(getattr(self, name))
        if self.output_bytes is not None:
            parsed = ObservedOutput.model_validate(strict_loads(self.output_bytes))
            if digest_bytes(self.output_bytes) != self.output_hash:
                raise ValueError("Assessment observed byte identity mismatch")
            canonical_bytes(parsed.model_dump(mode="json"))
        elif self.output_hash is not None:
            raise ValueError("Missing output cannot have output identity")
        if self.error is not None:
            digest_bytes(self.error)

    @classmethod
    def capture(cls, row, candidate_hash, *, output, error=None):
        if not isinstance(row, CaseRow):
            raise TypeError("Typed frozen case required")
        try:
            if type(output) is bytes:
                ObservedOutput.model_validate(strict_loads(output))
                raw = output
            else:
                raw = None if output is None else canonical_bytes(ObservedOutput.model_validate(output).model_dump(mode="json"))
        except (TypeError, ValueError):
            raise ValueError("Invalid observed assessment output") from None
        return cls(row.case_id, row.independence_group, require_hash(candidate_hash), row.input_hash,
                   row.source_hash, row.reference.reference_hash, row.reference.label_hash,
                   row.reference.rubric_hash, row.reference.lineage_hash, raw,
                   None if raw is None else digest_bytes(raw), error)


@dataclass(frozen=True)
class ExecutionPosition:
    """Private returned evidence, separate from strictly scoreable output."""
    ordinal: int
    repetition: int
    observation: Observation
    outcome: Literal["valid_output", "invalid_output", "no_output", "callback_error"]
    returned_bytes: bytes | None
    returned_hash: str | None
    validation_error: bytes | None = None

    def __post_init__(self):
        if (type(self.ordinal) is not int or not 0 <= self.ordinal < MAX_POSITIONS
                or type(self.repetition) is not int or not 0 <= self.repetition < 16
                or not isinstance(self.observation, Observation)):
            raise ValueError("Bounded typed execution position required")
        if self.returned_hash != (None if self.returned_bytes is None else digest_bytes(self.returned_bytes)):
            raise ValueError("Returned byte identity mismatch")
        if self.validation_error is not None:
            digest_bytes(self.validation_error)
            if self.outcome != "invalid_output":
                raise ValueError("Validation failure requires invalid returned output")
        o = self.observation
        if self.outcome == "valid_output":
            valid = self.returned_bytes is not None and o.output_bytes == self.returned_bytes and o.error is None
        elif self.outcome == "invalid_output":
            valid = o.output_bytes is None and o.error == b"Invalid observed assessment output"
            if self.returned_bytes is not None:
                try:
                    ObservedOutput.model_validate(strict_loads(self.returned_bytes))
                except Exception:
                    pass
                else:
                    valid = False
        elif self.outcome == "no_output":
            valid = self.returned_bytes is None and o.output_bytes is None and o.error is None
        elif self.outcome == "callback_error":
            valid = self.returned_bytes is None and o.output_bytes is None and o.error is not None
        else:
            valid = False
        if not valid:
            raise ValueError("Execution outcome/evidence mismatch")

    @classmethod
    def capture_returned(cls, row, candidate_hash, *, output, ordinal, repetition):
        raw, validation_error = None, None
        try:
            if output is not None:
                raw = output if type(output) is bytes else canonical_bytes(output)
                digest_bytes(raw)  # Bound before retaining or validating shape.
            observation = Observation.capture(row, candidate_hash, output=raw)
            outcome = "no_output" if output is None else "valid_output"
        except Exception as exc:
            # Ordinary validation failures belong to this position. Process
            # exit/interrupt BaseExceptions must still propagate to the host.
            try:
                validation_error = (type(exc).__name__ + ":" + str(exc)).encode("utf-8")[:MAX_BYTES]
            except Exception:
                validation_error = type(exc).__name__.encode("utf-8")[:MAX_BYTES]
            if raw is not None and (type(raw) is not bytes or len(raw) > MAX_BYTES):
                raw = None  # Oversize/nonserializable returns cannot enter bounded storage.
            observation = Observation.capture(row, candidate_hash, output=None,
                error=b"Invalid observed assessment output")
            outcome = "invalid_output"
        return cls(ordinal, repetition, observation, outcome, raw,
                   None if raw is None else digest_bytes(raw), validation_error)


@dataclass(frozen=True)
class AssessmentPosition:
    ordinal: int
    assessment: CaseAssessment | None = None
    error: bytes | None = None

    def __post_init__(self):
        if type(self.ordinal) is not int or not 0 <= self.ordinal < MAX_POSITIONS:
            raise ValueError("Bounded assessment ordinal required")
        if self.assessment is not None:
            if not isinstance(self.assessment, CaseAssessment):
                raise TypeError("Typed assessment required")
            object.__setattr__(self, "assessment", CaseAssessment.model_validate(self.assessment))
        if self.error is not None:
            digest_bytes(self.error)


@dataclass(frozen=True)
class DrillPacket:
    positions: tuple[str, ...]
    case_bytes: tuple[bytes | None, ...]
    baseline_bytes: bytes
    packet_bytes: bytes

    def __post_init__(self):
        if type(self.positions) is not tuple or not self.positions or len(self.positions) > MAX_POSITIONS:
            raise ValueError("Bounded frozen drill positions required")
        if any(type(x) is not str or not x.strip() for x in self.positions):
            raise ValueError("Declared drill identities required")
        if type(self.case_bytes) is not tuple or len(self.case_bytes) != len(self.positions):
            raise ValueError("Every drill position needs frozen content or explicit absence")
        for case_id, raw in zip(self.positions, self.case_bytes):
            if raw is not None and CaseRow.model_validate(strict_loads(raw)).case_id != case_id:
                raise ValueError("Drill case identity mismatch")
        strict_loads(self.baseline_bytes)
        if strict_loads(self.packet_bytes) != {"positions": [{"case_id": case_id, "case_hash": None if raw is None else digest_bytes(raw)}
                for case_id, raw in zip(self.positions, self.case_bytes)], "baseline_hash": digest_bytes(self.baseline_bytes)}:
            raise ValueError("Drill packet identity mismatch")

    @classmethod
    def capture(cls, positions, *, baseline):
        supplied = tuple(positions)
        if not supplied or len(supplied) > MAX_POSITIONS or any(not isinstance(item, (str, CaseRow)) for item in supplied):
            raise ValueError("Bounded typed workload rows or explicit ID-only positions required")
        positions = tuple(item.case_id if isinstance(item, CaseRow) else item for item in supplied)
        case_bytes = tuple(canonical_bytes(item.model_dump(mode="json")) if isinstance(item, CaseRow) else None for item in supplied)
        baseline_bytes = canonical_bytes(baseline)
        return cls(positions, case_bytes, baseline_bytes, canonical_bytes({"positions": [{"case_id": case_id,
            "case_hash": None if raw is None else digest_bytes(raw)} for case_id, raw in zip(positions, case_bytes)],
            "baseline_hash": digest_bytes(baseline_bytes)}))

    @property
    def packet_hash(self):
        return digest_bytes(self.packet_bytes)
