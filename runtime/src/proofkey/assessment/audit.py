"""Pure, bounded audit of a host-declared roster and captured evidence.

This joins declarations, not origin, runtime behavior or whole-candidate readiness.
No source paths are followed and no raw capture is included in the projection.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import wraps
import math
import re
from typing import Literal

from proofkey.contracts import ImplementationAudit, RequirementReadiness
from .driver_contracts import (DriverManifest, RunnerReceipt, digest_bytes,
                               require_hash, require_source, strict_loads)
from .drivers import assess_driver

_MIB = 1_048_576
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z", re.ASCII)
_PART = re.compile(r"[A-Za-z0-9_.-]+\Z", re.ASCII)
_CAPTURES = ("completed", "failed", "invalid_output", "no_output", "not_started")
_ASSESSMENTS = ("passed", "failed", "insufficient", "ungraded")
_POSITIONS = ("captured", "missing", "invalid")
_SUPPLIED = ("matched", "duplicate", "unexpected", "invalid")
_SOURCES = ("none", "not_checked", "missing", "matched", "mismatched")
_REASONS = ("missing_capture", "duplicate_capture", "unexpected_capture",
    "invalid_receipt_semantics", "manifest_mismatch", "source_scope_incomplete",
    "source_observation_missing", "source_snapshot_mismatch", "capture_not_completed",
    "invalid_capture_or_expectation", "predicate_failed", "predicate_insufficient")
_LIMITATIONS = ("source_origin_unattested", "current_source_not_read",
    "required_scope_host_declared", "full_required_variant_matrix_unregistered",
    "provisional_reference_not_gold", "actual_vs_replay_unjoined",
    "protected_custody_missing", "whole_candidate_unqualified")
_FIXED = tuple(f"R{i:02}" for i in range(1, 16)) + (
    "whole_candidate_closure", "actual_content_roles", "development_activation",
    "calibrated_labels", "protected_isolation", "timed_drills", "clean_reproduction",
    "source_rights", "independent_whole_branch_review", "official_eligibility")

PositionStatus = Literal["captured", "missing", "invalid"]
CaptureStatus = Literal["completed", "failed", "invalid_output", "no_output", "not_started"]
AssessmentStatus = Literal["passed", "failed", "insufficient", "ungraded"]
SourceObservation = Literal["none", "not_checked", "missing", "matched", "mismatched"]
SuppliedStatus = Literal["matched", "duplicate", "unexpected", "invalid"]


class AuditInputError(ValueError):
    """Closed, sanitized input rejection."""
    def __init__(self, code):
        if type(code) is not str or code not in (
            "invalid_request_type", "invalid_request_shape", "invalid_request_identity",
            "unsafe_supplied_shape", "input_limit_exceeded"):
            code = "invalid_request_shape"
        super().__init__(code)


def _check(condition):
    if not condition:
        raise ValueError("invalid_audit_projection")


def _projection_validator(validate):
    @wraps(validate)
    def checked(self):
        try:
            validate(self)
        except (ValueError, TypeError, AttributeError, OverflowError):
            raise ValueError("invalid_audit_projection") from None
    return checked


def _input_validator(code):
    def decorate(validate):
        @wraps(validate)
        def checked(*args):
            try:
                return validate(*args)
            except AuditInputError:
                raise
            except (ValueError, TypeError, AttributeError, OverflowError):
                raise AuditInputError(code) from None
        return checked
    return decorate


def _integer(value, low, high):
    return type(value) is int and low <= value <= high


def _tuple(value, low, high):
    return type(value) is tuple and low <= len(value) <= high


def _id(value):
    return type(value) is str and _ID.fullmatch(value) is not None


def _hash(value):
    return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _enum(value, values):
    return type(value) is str and value in values


def _ids(values):
    return (_tuple(values, 1, 64) and all(_id(x) for x in values)
            and len(set(values)) == len(values))


def _indexes(values, high):
    return (_tuple(values, 0, 256) and all(_integer(x, 0, high) for x in values)
            and tuple(sorted(set(values))) == values)


def _reasons(values):
    return (_tuple(values, 0, len(_REASONS)) and all(_enum(x, _REASONS) for x in values)
            and tuple(x for x in _REASONS if x in values) == values)


def _ordered_reasons(values):
    present = set(values)
    return tuple(x for x in _REASONS if x in present)


def _utc(value):
    if type(value) is not datetime or value.tzinfo is None:
        raise AuditInputError("invalid_request_shape")
    try:
        offset = value.utcoffset()
        if type(offset) is not timedelta or not -timedelta(days=1) < offset < timedelta(days=1):
            raise ValueError
        return (value.replace(tzinfo=None) - offset).replace(tzinfo=timezone.utc)
    except (ValueError, TypeError, OverflowError):
        raise AuditInputError("invalid_request_shape") from None


class _Budget:
    def __init__(self):
        self.total = 0

    def add(self, value, kind, code, maximum=_MIB):
        if type(value) is not kind:
            raise AuditInputError(code)
        if len(value) > maximum:
            raise AuditInputError("input_limit_exceeded")
        try:
            size = len(value.encode("utf-8")) if kind is str else len(value)
        except UnicodeError:
            raise AuditInputError(code) from None
        self.total += size
        if self.total > 32 * _MIB:
            raise AuditInputError("input_limit_exceeded")


def _paths(values):
    if not values or len(values) > 4096:
        raise ValueError
    folded = set()
    for path in values:
        if (type(path) is not str or not 1 <= len(path) <= 1024
                or any(p in ("", ".", "..") or _PART.fullmatch(p) is None for p in path.split("/"))
                or path.casefold() in folded):
            raise ValueError
        folded.add(path.casefold())


@_input_validator("invalid_request_shape")
def _position_shape(position, budget):
    if type(position) is not RequiredDriverPositionV1:
        raise AuditInputError("invalid_request_shape")
    if not _integer(position.ordinal, 0, 255) or not _integer(position.repetition, 0, 15):
        raise AuditInputError("invalid_request_shape")
    budget.add(position.manifest_bytes, bytes, "invalid_request_shape")
    budget.add(position.expectation_bytes, bytes, "invalid_request_shape")
    if type(position.required_predicate_ids) is not tuple or not position.required_predicate_ids:
        raise AuditInputError("invalid_request_shape")
    if len(position.required_predicate_ids) > 64:
        raise AuditInputError("input_limit_exceeded")
    for item in position.required_predicate_ids:
        budget.add(item, str, "invalid_request_shape", 128)
    if not _ids(position.required_predicate_ids):
        raise AuditInputError("invalid_request_identity")


def _position_identity(position):
    try:
        manifest = DriverManifest.from_bytes(position.manifest_bytes)
        if not all(_id(x) for x in (manifest.driver_id, manifest.variant, manifest.case_id,
                                   manifest.independence_group, manifest.obligation)):
            raise ValueError
        expected = strict_loads(position.expectation_bytes)
        if (type(expected) is not dict or set(expected) != {"version", "expectation_version", "predicates"}
                or expected["version"] != "driver-expectation-v1"
                or expected["expectation_version"] != manifest.expectation_version
                or digest_bytes(position.expectation_bytes) != manifest.expectation_hash):
            raise ValueError
        predicates = expected["predicates"]
        if type(predicates) is not list or not 1 <= len(predicates) <= 64:
            raise ValueError
        for p in predicates:
            if (type(p) is not dict or set(p) != {"id", "event_tag", "field_path", "operation", "expected"}
                    or not _id(p["id"]) or type(p["event_tag"]) is not str
                    or not 1 <= len(p["event_tag"]) <= 256
                    or type(p["field_path"]) is not list or len(p["field_path"]) > 16):
                raise ValueError
            for part in p["field_path"]:
                if not ((type(part) is str and 1 <= len(part) <= 256) or _integer(part, 0, 4095)):
                    raise ValueError
            if p["operation"] == "count_equals":
                if p["field_path"] or not _integer(p["expected"], 0, 2**63 - 1):
                    raise ValueError
            elif p["operation"] != "equals":
                raise ValueError
        if tuple(p["id"] for p in predicates) != position.required_predicate_ids:
            raise ValueError
        return manifest
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
        raise AuditInputError("invalid_request_identity") from None


@dataclass(frozen=True, slots=True)
class RequiredDriverPositionV1:
    ordinal: int
    repetition: int
    manifest_bytes: bytes
    expectation_bytes: bytes
    required_predicate_ids: tuple[str, ...]

    def __post_init__(self):
        _position_shape(self, _Budget())
        _position_identity(self)


@_input_validator("invalid_request_shape")
def _request(request, budget):
    if type(request) is not CandidateAuditRequestV1:
        raise AuditInputError("invalid_request_type")
    budget.add(request.source_manifest_bytes, bytes, "invalid_request_shape")
    if (type(request.required_source_paths) is not tuple or not request.required_source_paths
            or type(request.positions) is not tuple or not request.positions):
        raise AuditInputError("invalid_request_shape")
    if len(request.required_source_paths) > 4096 or len(request.positions) > 256:
        raise AuditInputError("input_limit_exceeded")
    for path in request.required_source_paths:
        budget.add(path, str, "invalid_request_shape", 1024)
    for position in request.positions:
        _position_shape(position, budget)
    stamp = _utc(request.audited_at)
    try:
        source = require_source(request.source_manifest_bytes)
        _paths(request.required_source_paths)
        _paths(tuple(source["files"]))
        if tuple(sorted(request.required_source_paths)) != request.required_source_paths:
            raise ValueError
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise AuditInputError("invalid_request_shape") from None
    manifests = tuple(_position_identity(p) for p in request.positions)
    if (len({(p.ordinal, p.repetition) for p in request.positions}) != len(request.positions)
            or len({(m.driver_id, m.variant, p.repetition) for m, p in zip(manifests, request.positions)}) != len(request.positions)
            or any(m.candidate_manifest_hash != digest_bytes(request.source_manifest_bytes) for m in manifests)):
        raise AuditInputError("invalid_request_identity")
    return source, manifests, stamp


@dataclass(frozen=True, slots=True)
class CandidateAuditRequestV1:
    source_manifest_bytes: bytes
    required_source_paths: tuple[str, ...]
    positions: tuple[RequiredDriverPositionV1, ...]
    audited_at: datetime

    def __post_init__(self):
        _, _, stamp = _request(self, _Budget())
        object.__setattr__(self, "audited_at", stamp)


@dataclass(frozen=True, slots=True)
class PredicateAuditV1:
    predicate_id: str
    status: Literal["passed", "failed", "insufficient"]
    event_ordinals: tuple[int, ...]

    @_projection_validator
    def __post_init__(self):
        _check(_id(self.predicate_id) and _enum(self.status, _ASSESSMENTS[:3]))
        _check(_indexes(self.event_ordinals, 63) and len(self.event_ordinals) <= 64)


@dataclass(frozen=True, slots=True)
class AuditPositionV1:
    ordinal: int
    repetition: int
    manifest_hash: str
    driver_id: str
    variant: str
    case_id: str
    independent_group: str
    obligation: str
    required_predicate_ids: tuple[str, ...]
    supplied_indexes: tuple[int, ...]
    status: PositionStatus
    capture_status: CaptureStatus | None
    assessment_status: AssessmentStatus | None
    source_observation: SourceObservation
    reasons: tuple[str, ...]
    predicates: tuple[PredicateAuditV1, ...]

    @_projection_validator
    def __post_init__(self):
        _check(_integer(self.ordinal, 0, 255) and _integer(self.repetition, 0, 15) and _hash(self.manifest_hash))
        _check(all(_id(x) for x in (self.driver_id, self.variant, self.case_id, self.independent_group)))
        _check(_enum(self.obligation, _FIXED[:15]) and _ids(self.required_predicate_ids))
        _check(_indexes(self.supplied_indexes, 255) and _enum(self.status, _POSITIONS)
               and _enum(self.source_observation, _SOURCES) and _reasons(self.reasons))
        _check(_tuple(self.predicates, 0, 64))
        for p in self.predicates:
            _check(type(p) is PredicateAuditV1)
            PredicateAuditV1.__post_init__(p)
        if self.status == "captured":
            _check(len(self.supplied_indexes) == 1 and _enum(self.capture_status, _CAPTURES)
                   and _enum(self.assessment_status, _ASSESSMENTS)
                   and self.source_observation in ("matched", "missing", "mismatched"))
            if self.capture_status != "completed":
                _check(self.assessment_status == "ungraded" and not self.predicates)
            else:
                _check(self.source_observation == "matched")
                if self.assessment_status == "ungraded":
                    _check(not self.predicates)
                else:
                    _check(tuple(p.predicate_id for p in self.predicates) == self.required_predicate_ids)
                    states = {p.status for p in self.predicates}
                    actual = "failed" if "failed" in states else "insufficient" if "insufficient" in states else "passed"
                    _check(self.assessment_status == actual)
            reasons = _capture_reasons(self.capture_status, self.assessment_status, self.source_observation)
            if "source_scope_incomplete" in self.reasons:
                reasons.append("source_scope_incomplete")
            _check(self.reasons == _ordered_reasons(reasons))
        else:
            _check(self.capture_status is None and self.assessment_status is None and not self.predicates)
            if self.status == "missing":
                _check(not self.supplied_indexes and self.source_observation == "none"
                       and self.reasons == ("missing_capture",))
            else:
                _check(bool(self.supplied_indexes) and self.source_observation == "not_checked")
                _check(bool(self.reasons) and all(x in ("duplicate_capture", "invalid_receipt_semantics",
                       "manifest_mismatch", "source_snapshot_mismatch") for x in self.reasons))
                _check(("duplicate_capture" in self.reasons) == (len(self.supplied_indexes) > 1))


@dataclass(frozen=True, slots=True)
class SuppliedAuditV1:
    index: int
    required_index: int | None
    ordinal: int | None
    repetition: int | None
    manifest_hash: str | None
    status: SuppliedStatus
    capture_status: CaptureStatus | None
    source_observation: SourceObservation
    reasons: tuple[str, ...]

    @_projection_validator
    def __post_init__(self):
        _check(_integer(self.index, 0, 255))
        _check(self.required_index is None or _integer(self.required_index, 0, 255))
        _check(self.ordinal is None or _integer(self.ordinal, 0, 255))
        _check(self.repetition is None or _integer(self.repetition, 0, 15))
        _check(self.manifest_hash is None or _hash(self.manifest_hash))
        _check(_enum(self.status, _SUPPLIED) and _enum(self.source_observation, _SOURCES)
               and _reasons(self.reasons))
        _check(self.capture_status is None or _enum(self.capture_status, _CAPTURES))
        if self.capture_status is not None:
            _check(_integer(self.ordinal, 0, 255) and _integer(self.repetition, 0, 15))
        _check(self.manifest_hash is not None)
        if self.status == "matched":
            _check(self.required_index is not None and self.ordinal is not None and self.repetition is not None
                   and self.capture_status is not None and self.source_observation in ("matched", "missing", "mismatched"))
        else:
            _check(self.source_observation == "not_checked" and bool(self.reasons))
            allowed = ("duplicate_capture", "unexpected_capture", "invalid_receipt_semantics",
                       "manifest_mismatch", "source_snapshot_mismatch")
            _check(all(x in allowed for x in self.reasons))
            _check(("invalid_receipt_semantics" in self.reasons) == (self.capture_status is None))
            if self.status == "duplicate":
                _check(self.required_index is not None and "duplicate_capture" in self.reasons)
                _check(self.reasons in (("duplicate_capture",),
                                       ("duplicate_capture", "invalid_receipt_semantics")))
            elif self.status == "unexpected":
                _check(self.required_index is None and self.capture_status is not None
                       and self.reasons == ("unexpected_capture",))
            else:
                _check("duplicate_capture" not in self.reasons and "unexpected_capture" not in self.reasons)
                if self.capture_status is None:
                    _check(self.reasons == ("invalid_receipt_semantics",))
                else:
                    _check(self.required_index is not None and self.reasons in (
                        ("manifest_mismatch",), ("source_snapshot_mismatch",)))
                    if self.reasons == ("source_snapshot_mismatch",):
                        _check(self.capture_status == "completed")


def _capture_reasons(capture, assessment, source):
    reasons = []
    if source == "missing":
        reasons.append("source_observation_missing")
    elif source == "mismatched":
        reasons.append("source_snapshot_mismatch")
    if capture != "completed":
        reasons.append("capture_not_completed")
    elif assessment == "ungraded":
        reasons.append("invalid_capture_or_expectation")
    elif assessment == "failed":
        reasons.append("predicate_failed")
    elif assessment == "insufficient":
        reasons.append("predicate_insufficient")
    return reasons


def _tables(positions, supplied):
    return (
        tuple((x, sum(p.status == x for p in positions)) for x in _POSITIONS),
        tuple((x, sum((p.capture_status or "none") == x for p in positions)) for x in _CAPTURES + ("none",)),
        tuple((x, sum((p.assessment_status or "none") == x for p in positions)) for x in _ASSESSMENTS + ("none",)),
        tuple((x, sum(p.status == x for p in supplied)) for x in _SUPPLIED))


def _passes(positions, scope):
    return tuple(dict.fromkeys((p.driver_id, p.variant, p.obligation) for p in positions
        if scope == "matched" and p.status == "captured" and p.capture_status == "completed"
        and p.source_observation == "matched" and p.assessment_status == "passed"))


def _implementation(identity, stamp, positions, supplied, scope):
    invalid = any(p.status == "invalid" for p in positions) or any(s.status != "matched" for s in supplied)
    missing = any(p.status == "missing" for p in positions)
    passed = all(p.status == "captured" and p.capture_status == "completed"
        and p.source_observation == "matched" and p.assessment_status == "passed" for p in positions) and scope == "matched"
    records = (
        ("source_scope_join", "satisfied" if scope == "matched" else "missing",
         "matched_declared_source_scope" if scope == "matched" else "incomplete_declared_source_scope", []),
        ("driver_inventory_join", "invalid" if invalid else "missing" if missing else "satisfied",
         "invalid_driver_join" if invalid else "missing_driver_capture" if missing else "matched_declared_driver_inventory",
         [f"required-{i}" for i in range(len(positions))] + [f"supplied-{i}" for i in range(len(supplied))]),
        ("declared_driver_results", "invalid" if invalid else "satisfied" if passed else "missing",
         "invalid_driver_join" if invalid else "declared_variants_passed" if passed else "declared_results_incomplete",
         [f"required-{i}" for i in range(len(positions))]))
    requirements = [RequirementReadiness(requirement_id=i, status=s, reason=r, evidence_refs=e)
                    for i, s, r, e in records]
    requirements.extend(RequirementReadiness(requirement_id=i, status="missing", evidence_refs=[],
                       reason="outside_foundation_evidence_scope") for i in _FIXED)
    return ImplementationAudit(candidate_hash=identity, requirements=requirements,
        missing_evidence=[r.requirement_id for r in requirements if r.status == "missing"],
        invalid_evidence=[r.requirement_id for r in requirements if r.status == "invalid"], audited_at=stamp)


@dataclass(frozen=True, slots=True)
class CandidateEvidenceAuditV1:
    source_manifest_hash: str
    source_kind: Literal["filesystem", "fixture-only"]
    source_scope_status: Literal["matched", "incomplete"]
    positions: tuple[AuditPositionV1, ...]
    supplied: tuple[SuppliedAuditV1, ...]
    required_count: int
    supplied_count: int
    joined_count: int
    missing_count: int
    invalid_required_count: int
    invalid_supplied_count: int
    position_counts: tuple[tuple[str, int], ...]
    capture_counts: tuple[tuple[str, int], ...]
    assessment_counts: tuple[tuple[str, int], ...]
    supplied_counts: tuple[tuple[str, int], ...]
    independent_groups: tuple[str, ...]
    passed_variants: tuple[tuple[str, str, str], ...]
    scope_status: Literal["unqualified"]
    limitations: tuple[str, ...]
    implementation: ImplementationAudit

    @_projection_validator
    def __post_init__(self):
        _check(_hash(self.source_manifest_hash) and _enum(self.source_kind, ("filesystem", "fixture-only"))
               and _enum(self.source_scope_status, ("matched", "incomplete")))
        _check(_tuple(self.positions, 1, 256) and _tuple(self.supplied, 0, 256))
        for p in self.positions:
            _check(type(p) is AuditPositionV1)
            AuditPositionV1.__post_init__(p)
        for s in self.supplied:
            _check(type(s) is SuppliedAuditV1)
            SuppliedAuditV1.__post_init__(s)
        _check(len({(p.ordinal, p.repetition) for p in self.positions}) == len(self.positions))
        _check(len({(p.driver_id, p.variant, p.repetition) for p in self.positions}) == len(self.positions))
        _check(tuple(s.index for s in self.supplied) == tuple(range(len(self.supplied))))
        for i, p in enumerate(self.positions):
            members = tuple(s.index for s in self.supplied if s.required_index == i)
            _check(p.supplied_indexes == members)
            for j in members:
                s = self.supplied[j]
                _check((s.ordinal, s.repetition) == (p.ordinal, p.repetition))
                if p.status == "captured":
                    _check(s.status == "matched" and s.manifest_hash == p.manifest_hash
                           and s.capture_status == p.capture_status and s.source_observation == p.source_observation
                           and s.reasons == p.reasons)
                else:
                    _check(s.status == ("duplicate" if len(members) > 1 else "invalid"))
                    if len(members) == 1 and s.capture_status is not None:
                        _check(("manifest_mismatch" in s.reasons) == (s.manifest_hash != p.manifest_hash))
            if p.status == "invalid":
                _check(p.reasons == _ordered_reasons(x for j in members for x in self.supplied[j].reasons))
            if p.status == "captured":
                _check(("source_scope_incomplete" in p.reasons) == (self.source_scope_status == "incomplete"))
        keys = {(p.ordinal, p.repetition) for p in self.positions}
        for s in self.supplied:
            _check(s.required_index is None or s.required_index < len(self.positions))
            if s.required_index is None:
                _check(s.status in ("unexpected", "invalid") and (s.ordinal, s.repetition) not in keys)
        tables = _tables(self.positions, self.supplied)
        for actual, expected in zip((self.position_counts, self.capture_counts,
                                     self.assessment_counts, self.supplied_counts), tables):
            _check(type(actual) is tuple and all(type(x) is tuple and len(x) == 2
                   and type(x[0]) is str and _integer(x[1], 0, 256) for x in actual) and actual == expected)
        counts = (len(self.positions), len(self.supplied), tables[0][0][1], tables[0][1][1],
                  tables[0][2][1], sum(s.status != "matched" for s in self.supplied))
        for actual, expected in zip((self.required_count, self.supplied_count, self.joined_count,
                self.missing_count, self.invalid_required_count, self.invalid_supplied_count), counts):
            _check(_integer(actual, 0, 256) and actual == expected)
        groups = tuple(sorted({p.independent_group for p in self.positions if p.status == "captured"}))
        _check(type(self.independent_groups) is tuple and all(_id(x) for x in self.independent_groups)
               and self.independent_groups == groups)
        _check(type(self.passed_variants) is tuple and all(type(x) is tuple and len(x) == 3
               and all(_id(v) for v in x) for x in self.passed_variants)
               and self.passed_variants == _passes(self.positions, self.source_scope_status))
        limits = _LIMITATIONS + (("fixture_only_source",) if self.source_kind == "fixture-only" else ())
        limits += (("source_scope_incomplete",) if self.source_scope_status == "incomplete" else ())
        _check(type(self.limitations) is tuple and all(type(x) is str for x in self.limitations)
               and self.limitations == limits and _enum(self.scope_status, ("unqualified",)))
        _check(type(self.implementation) is ImplementationAudit)
        try:
            data = self.implementation.model_dump()
            stamp = _utc(data["audited_at"])
            detached = ImplementationAudit.model_validate({**data, "audited_at": stamp})
            expected = _implementation(self.source_manifest_hash, stamp, self.positions, self.supplied, self.source_scope_status)
            _check(detached.model_dump() == expected.model_dump())
        except (ValueError, TypeError, KeyError, AttributeError):
            raise ValueError("invalid_audit_projection") from None
        object.__setattr__(self, "implementation", detached)


# These literal slot names deliberately exclude property lookup and arbitrary iteration.
_BYTE_FIELDS = ("manifest_bytes", "raw_output_bytes", "score_projection_bytes", "error_bytes",
                "source_pre_manifest_bytes", "source_post_manifest_bytes")
_TEXT_FIELDS = ("manifest_hash", "status", "raw_output_hash", "projection_version")
_TUPLE_FIELDS = ("dependency_limits", "raw_event_bytes", "barrier_receipt_bytes")
_NUMBER_FIELDS = ("ordinal", "repetition", "process_exit", "elapsed_seconds")


@_input_validator("unsafe_supplied_shape")
def _receipt_shapes(receipts, budget):
    if type(receipts) is not tuple:
        raise AuditInputError("unsafe_supplied_shape")
    if len(receipts) > 256:
        raise AuditInputError("input_limit_exceeded")
    records = []
    code = "unsafe_supplied_shape"
    for receipt in receipts:
        if type(receipt) is not RunnerReceipt:
            raise AuditInputError(code)
        values = {name: RunnerReceipt.__dict__[name].__get__(receipt, RunnerReceipt)
                  for name in _BYTE_FIELDS + _TEXT_FIELDS + _TUPLE_FIELDS + _NUMBER_FIELDS}
        raw_total = 0
        for name in _BYTE_FIELDS:
            value = values[name]
            if value is None and name != "manifest_bytes":
                continue
            budget.add(value, bytes, code)
            raw_total += len(value)
        for name in _TEXT_FIELDS:
            value = values[name]
            if value is None and name == "raw_output_hash":
                continue
            budget.add(value, str, code, 256)
        for name in _TUPLE_FIELDS:
            value = values[name]
            if type(value) is not tuple:
                raise AuditInputError(code)
            if len(value) > 64:
                raise AuditInputError("input_limit_exceeded")
            for item in value:
                budget.add(item, str if name == "dependency_limits" else bytes, code,
                           256 if name == "dependency_limits" else _MIB)
                if name != "dependency_limits":
                    raw_total += len(item)
        if raw_total > 8 * _MIB:
            raise AuditInputError("input_limit_exceeded")
        for name in _NUMBER_FIELDS:
            value = values[name]
            if value is None and name in ("process_exit", "elapsed_seconds"):
                continue
            if name == "elapsed_seconds":
                valid = ((type(value) is int and -(2**63) <= value <= 2**63 - 1)
                         or (type(value) is float and math.isfinite(value)))
            else:
                valid = _integer(value, -(2**63), 2**63 - 1)
            if not valid:
                raise AuditInputError(code)
        records.append(values)
    return records


def audit_candidate_evidence(request, receipts: tuple[RunnerReceipt, ...]) -> CandidateEvidenceAuditV1:
    """Audit bounded captured data only; perform no source or runtime observations."""
    budget = _Budget()
    source, manifests, stamp = _request(request, budget)
    records = _receipt_shapes(receipts, budget)  # All shapes and occurrence budget before grading.
    scope = "matched" if (set(source["files"]) == set(request.required_source_paths)
        and "src/proofkey/schema.sql" in source["files"]) else "incomplete"
    required_keys = {(p.ordinal, p.repetition): i for i, p in enumerate(request.positions)}
    members = [[] for _ in request.positions]
    validated = []
    for index, values in enumerate(records):
        key = (values["ordinal"], values["repetition"])
        ri = required_keys.get(key)
        if ri is not None:
            members[ri].append(index)
        try:
            receipt = RunnerReceipt(**values)
        except (ValueError, TypeError, UnicodeError, RecursionError):
            receipt = None
        validated.append((ri, values, receipt))
    supplied = []
    assessments = {}
    for index, (ri, values, receipt) in enumerate(validated):
        reasons = []
        observation = "not_checked"
        if receipt is None:
            reasons.append("invalid_receipt_semantics")
        if ri is not None and len(members[ri]) > 1:
            status = "duplicate"
            reasons.append("duplicate_capture")
        elif ri is None:
            status = "invalid" if receipt is None else "unexpected"
            if receipt is not None:
                reasons.append("unexpected_capture")
        elif receipt is None:
            status = "invalid"
        elif values["manifest_bytes"] != request.positions[ri].manifest_bytes:
            status = "invalid"
            reasons.append("manifest_mismatch")
        else:
            status = "matched"
            snapshots = (values["source_pre_manifest_bytes"], values["source_post_manifest_bytes"])
            wrong = any(raw is not None and raw != request.source_manifest_bytes for raw in snapshots)
            observation = "mismatched" if wrong else "missing" if None in snapshots else "matched"
            if receipt.status == "completed" and observation != "matched":
                status, observation = "invalid", "not_checked"
                reasons.append("source_snapshot_mismatch")
            else:
                result = assess_driver(receipt, request.positions[ri].expectation_bytes)
                predicates = tuple(PredicateAuditV1(p.predicate_id, p.status, p.event_ordinals) for p in result.outcomes)
                assessments[ri] = (result.status, predicates)
                reasons.extend(_capture_reasons(receipt.status, result.status, observation))
                if scope == "incomplete":
                    reasons.append("source_scope_incomplete")
        supplied.append(SuppliedAuditV1(index, ri,
            values["ordinal"] if _integer(values["ordinal"], 0, 255) else None,
            values["repetition"] if _integer(values["repetition"], 0, 15) else None,
            digest_bytes(values["manifest_bytes"]), status,
            None if receipt is None else receipt.status, observation, _ordered_reasons(reasons)))
    supplied = tuple(supplied)
    positions = []
    for ri, (p, manifest) in enumerate(zip(request.positions, manifests)):
        indexes = tuple(members[ri])
        if not indexes:
            status, capture, assessment, observation, reasons, predicates = "missing", None, None, "none", ("missing_capture",), ()
        elif supplied[indexes[0]].status == "matched":
            s = supplied[indexes[0]]
            status, capture, observation, reasons = "captured", s.capture_status, s.source_observation, s.reasons
            assessment, predicates = assessments[ri]
        else:
            status, capture, assessment, observation, predicates = "invalid", None, None, "not_checked", ()
            reasons = _ordered_reasons(x for j in indexes for x in supplied[j].reasons)
        positions.append(AuditPositionV1(p.ordinal, p.repetition, digest_bytes(p.manifest_bytes),
            manifest.driver_id, manifest.variant, manifest.case_id, manifest.independence_group,
            manifest.obligation, p.required_predicate_ids, indexes, status, capture, assessment,
            observation, reasons, predicates))
    positions = tuple(positions)
    tables = _tables(positions, supplied)
    limits = _LIMITATIONS + (("fixture_only_source",) if source["kind"] == "fixture-only" else ())
    limits += (("source_scope_incomplete",) if scope == "incomplete" else ())
    identity = digest_bytes(request.source_manifest_bytes)
    return CandidateEvidenceAuditV1(identity, source["kind"], scope, positions, supplied,
        len(positions), len(supplied), tables[0][0][1], tables[0][1][1], tables[0][2][1],
        sum(s.status != "matched" for s in supplied), *tables,
        tuple(sorted({p.independent_group for p in positions if p.status == "captured"})),
        _passes(positions, scope), "unqualified", limits,
        _implementation(identity, stamp, positions, supplied, scope))
