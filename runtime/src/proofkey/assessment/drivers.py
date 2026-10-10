"""Trusted reference-free public sequences and separate declarative grading."""
from dataclasses import dataclass
from hashlib import sha256
import math
from time import monotonic
from typing import Callable
from .driver_contracts import (DriverManifest, DriverInput, DriverCapture, RunnerReceipt,
    DriverAssessment, PredicateOutcome, canonical_bytes, strict_loads, digest_bytes,
    require_bytes, require_object, require_event, require_text, require_int, require_source,
    MAX_EVENTS, MAX_ITEM_BYTES, MAX_RECEIPT_BYTES)


@dataclass(frozen=True, slots=True)
class RegisteredDriver:
    driver_id: str
    obligation: str
    variant: str
    case_id: str
    independence_group: str
    profile_name: str
    input_sequence_bytes: bytes
    scenario_bytes: bytes
    candidate_manifest_bytes: bytes
    profile_bytes: bytes
    process_bytes: bytes
    policy_bytes: bytes
    driver_code_bytes: bytes
    dependency_evidence: tuple[tuple[str, bytes], ...]
    callback: Callable
    source_snapshot: Callable | None = None
    max_seconds: float = 60.0
    max_events: int = MAX_EVENTS

    def __post_init__(self):
        for name in ("driver_id", "obligation", "variant", "case_id", "independence_group", "profile_name"):
            require_text(getattr(self, name))
        if self.obligation not in {f"R{i:02}" for i in range(1, 16)}:
            raise ValueError("Unknown obligation")
        for name in ("input_sequence_bytes", "scenario_bytes", "profile_bytes", "process_bytes", "policy_bytes"):
            strict_loads(getattr(self, name))
        require_bytes(self.driver_code_bytes)
        candidate = require_source(self.candidate_manifest_bytes)
        if (not callable(self.callback) or self.source_snapshot is not None and not callable(self.source_snapshot)
                or candidate["kind"] == "filesystem" and self.source_snapshot is None):
            raise ValueError("Trusted callback and concrete source accessor required")
        if (type(self.max_seconds) not in (int, float) or not 0 < self.max_seconds <= 60
                or not math.isfinite(self.max_seconds)):
            raise ValueError("Finite cooperative eligibility limit required")
        require_int(self.max_events, 1, MAX_EVENTS)
        if type(self.dependency_evidence) is not tuple or len(self.dependency_evidence) > MAX_EVENTS:
            raise ValueError("Immutable dependency evidence required")
        ids = set()
        for pair in self.dependency_evidence:
            if type(pair) is not tuple or len(pair) != 2:
                raise ValueError("Exact dependency pair required")
            identity, raw = pair
            require_text(identity)
            value = require_object(raw)
            if (identity in ids or set(value) != {"status"} or type(value["status"]) is not str
                    or value["status"] not in {"available", "unavailable"}):
                raise ValueError("Unique explicit dependency status required")
            ids.add(identity)

    def matches(self, manifest):
        """Every evidence entry is required, in trusted registration tuple order."""
        identities = {"case_bytes_hash": self.input_sequence_bytes, "scenario_hash": self.scenario_bytes,
            "candidate_manifest_hash": self.candidate_manifest_bytes, "driver_code_hash": self.driver_code_bytes,
            "profile_hash": self.profile_bytes, "process_hash": self.process_bytes, "policy_hash": self.policy_bytes}
        return (all(getattr(manifest, name) == getattr(self, name) for name in
                    ("driver_id", "obligation", "variant", "case_id", "independence_group", "profile_name"))
                and manifest.dependency_ids == tuple(identity for identity, _ in self.dependency_evidence)
                and all(getattr(manifest, name) == digest_bytes(raw) for name, raw in identities.items()))


@dataclass(frozen=True, slots=True)
class DriverRegistry:
    registrations: tuple[RegisteredDriver, ...]

    def __post_init__(self):
        if type(self.registrations) is not tuple or len(self.registrations) > 256:
            raise ValueError("Bounded immutable registry required")
        keys = set()
        for registration in self.registrations:
            if type(registration) is not RegisteredDriver:
                raise ValueError("Typed trusted registration required")
            registration.__post_init__()
            key = registration.driver_id, registration.variant
            if key in keys:
                raise ValueError("Duplicate driver/variant registration")
            keys.add(key)

    def resolve(self, manifest):
        if type(manifest) is not DriverManifest:
            raise ValueError("Exact driver manifest required")
        manifest = DriverManifest.from_bytes(manifest.to_bytes())
        for registration in self.registrations:
            if (registration.driver_id, registration.variant) == (manifest.driver_id, manifest.variant):
                registration.__post_init__()
                if not registration.matches(manifest):
                    raise LookupError("registration_mismatch")
                return registration
        raise LookupError("driver_unregistered")


class CaptureLimitError(ValueError):
    """A cooperative capture bound was reached; evidence is incomplete."""


class EventSink:
    """Bounded capture/control only; no reference, host source or grader access.

    This trusted Python interface is not an arbitrary-hostile-code sandbox.
    Entered I/O cannot be forcibly cancelled by the cooperative clock checks.
    """
    __slots__ = ("_events", "_cutoff", "_count", "_item", "_budget", "_used", "_failure")

    def __init__(self, cutoff, count, item, budget):
        self._events, self._cutoff = [], cutoff
        self._count, self._item, self._budget, self._used = count, item, budget, 0
        self._failure = None

    @property
    def events(self):
        return tuple(self._events)

    def checkpoint(self):
        if self._failure is not None:
            raise self._failure
        if monotonic() >= self._cutoff:
            self._failure = TimeoutError("cooperative_sequence_cutoff")
            raise self._failure

    def emit(self, raw):
        self.checkpoint()
        try:
            require_event(raw)
            if len(raw) > self._item or len(self._events) >= self._count or self._used + len(raw) > self._budget:
                raise ValueError("capture_bound_exceeded_incomplete")
        except ValueError as error:
            omitted = ("; omitted_bytes=" + str(len(raw)) + "; omitted_sha256=" + sha256(raw).hexdigest()
                       if type(raw) is bytes else "; omitted_type=" + type(raw).__name__)
            self._failure = CaptureLimitError(str(error) + omitted)
            raise self._failure from error
        self._events.append(raw)
        self._used += len(raw)


def _error(error):
    """Keep bounded private error evidence, explicitly label any excluded tail."""
    try:
        message = str(error)
    except Exception:
        message = "error_message_unavailable"
    raw = message.encode("utf-8", errors="replace")
    return canonical_bytes({"type": type(error).__name__[:128], "message": raw[:1024].decode("utf-8", errors="replace"),
                            "message_bytes": len(raw), "message_hash": sha256(raw).hexdigest(),
                            "message_truncated": len(raw) > 1024})


def run_driver(registry, manifest, input_sequence_bytes, *, ordinal, repetition):
    if type(registry) is not DriverRegistry or type(manifest) is not DriverManifest:
        raise ValueError("Exact registry/manifest required")
    require_int(ordinal, 0, 255)
    require_int(repetition, 0, 15)
    raw = manifest.to_bytes()
    manifest = DriverManifest.from_bytes(raw)
    base = dict(manifest_bytes=raw, manifest_hash=digest_bytes(raw), ordinal=ordinal, repetition=repetition)
    # Resolve all joins/dependencies before any callback or source accessor entry.
    try:
        registration = registry.resolve(manifest)
        if manifest.execution_kind != "public_sequence":
            raise LookupError("execution_kind_unimplemented")
        if input_sequence_bytes != registration.input_sequence_bytes or type(input_sequence_bytes) is not bytes:
            raise LookupError("input_sequence_mismatch")
        evidence = dict(registration.dependency_evidence)
        if any(identity not in evidence or strict_loads(evidence[identity])["status"] != "available"
               for identity in manifest.dependency_ids):
            raise LookupError("dependency_unavailable")
    except (LookupError, ValueError) as error:
        return RunnerReceipt(**base, status="not_started", dependency_limits=(str(error)[:256] or "join_invalid",),
                             error_bytes=_error(error))
    start = monotonic()
    pre, post, output, projection, error = None, None, None, None, None
    status = "failed"
    # Reserve worst-case source/output/projection space before accepting events.
    budget = MAX_RECEIPT_BYTES - len(raw) - 4 * MAX_ITEM_BYTES - 4096
    sink = EventSink(start + registration.max_seconds, registration.max_events,
                     MAX_ITEM_BYTES, max(0, budget))
    source = registration.source_snapshot
    try:
        pre = registration.candidate_manifest_bytes if source is None else source()
        require_source(pre)
        if pre != registration.candidate_manifest_bytes:
            raise ValueError("source_pre_drift")
        view = DriverInput(registration.input_sequence_bytes, registration.scenario_bytes,
            manifest.case_id, manifest.obligation, manifest.variant, manifest.candidate_manifest_hash,
            manifest.profile_name, manifest.profile_hash, manifest.process_hash, manifest.policy_hash)
        sink.checkpoint()
        returned = registration.callback(view, sink)
        sink.checkpoint()
        if returned is None:
            status = "no_output"
        elif type(returned) is not DriverCapture:
            status, error = "invalid_output", _error(ValueError("untyped_callback_output"))
        else:
            output = returned.raw_output_bytes
            try:
                returned.__post_init__()
                if returned.raw_event_bytes != sink.events:
                    raise ValueError("capture_events_do_not_join_sink")
                if output is None:
                    status = "no_output"
                else:
                    require_object(output)
                    projection = returned.score_projection.output_bytes if returned.score_projection else None
                    status = "completed"
            except ValueError as invalid:
                status, error = "invalid_output", _error(invalid)
    except CaptureLimitError as invalid:
        status, error = "invalid_output", _error(invalid)
    except Exception as failure:
        status, error = "failed", _error(failure)
    finally:
        # Do not catch BaseException; interrupt/process exit cannot become success.
        if pre == registration.candidate_manifest_bytes:
            try:
                post = registration.candidate_manifest_bytes if source is None else source()
                require_source(post)
                if post != pre:
                    status, error = "failed", _error(ValueError("source_post_drift"))
            except Exception as failure:
                status, error = "failed", _error(failure)
    # Invalid accessor returns cannot masquerade as observed canonical snapshots.
    for name, value in (("pre", pre), ("post", post)):
        try:
            if value is not None:
                require_source(value)
        except ValueError:
            if name == "pre":
                pre = None
            else:
                post = None
    elapsed = monotonic() - start
    if elapsed > registration.max_seconds:
        status, error = "failed", _error(TimeoutError("observed_driver_limit_exceeded"))
    if type(output) is not bytes or len(output) > MAX_ITEM_BYTES:
        output, projection = None, None
    return RunnerReceipt(**base, status=status, raw_event_bytes=sink.events,
        raw_output_bytes=output, raw_output_hash=digest_bytes(output) if output is not None else None,
        score_projection_bytes=projection, error_bytes=error, elapsed_seconds=elapsed,
        source_pre_manifest_bytes=pre, source_post_manifest_bytes=post)


def assess_driver(receipt, expectation_bytes):
    if type(receipt) is not RunnerReceipt:
        raise ValueError("Exact captured receipt required")
    base = dict(manifest_hash=receipt.manifest_hash, ordinal=receipt.ordinal, repetition=receipt.repetition)
    try:
        receipt.__post_init__()
        manifest = DriverManifest.from_bytes(receipt.manifest_bytes)
        expected = require_object(expectation_bytes)
        if (digest_bytes(expectation_bytes) != manifest.expectation_hash
                or set(expected) != {"version", "expectation_version", "predicates"}
                or expected["version"] != "driver-expectation-v1"
                or expected["expectation_version"] != manifest.expectation_version):
            raise ValueError("expectation_join_invalid")
        predicates = expected["predicates"]
        if type(predicates) is not list or not 1 <= len(predicates) <= MAX_EVENTS:
            raise ValueError("bounded_nonempty_predicates_required")
        ids = set()
        for predicate in predicates:
            if type(predicate) is not dict or set(predicate) != {"id", "event_tag", "field_path", "operation", "expected"}:
                raise ValueError("exact_predicate_fields_required")
            require_text(predicate["id"])
            require_text(predicate["event_tag"])
            if predicate["id"] in ids:
                raise ValueError("duplicate_predicate_id")
            ids.add(predicate["id"])
            path = predicate["field_path"]
            if type(path) is not list or len(path) > 16:
                raise ValueError("bounded_predicate_path_required")
            for part in path:
                if type(part) is str:
                    require_text(part)
                else:
                    require_int(part, 0, 4095)
            if predicate["operation"] == "count_equals":
                require_int(predicate["expected"], 0, 2**63 - 1)
                if path:
                    raise ValueError("count_path_must_be_empty")
            elif predicate["operation"] != "equals":
                raise ValueError("unknown_predicate_operation")
        if receipt.status != "completed":
            return DriverAssessment(**base, status="ungraded", outcomes=(), reason="capture_not_completed")
    except ValueError:
        return DriverAssessment(**base, status="ungraded", outcomes=(), reason="invalid_capture_or_expectation")
    events, outcomes = receipt.events(), []
    for predicate in predicates:
        ordinals = tuple(i for i, event in enumerate(events) if event["event_tag"] == predicate["event_tag"])
        status = "insufficient"
        if ordinals and predicate["operation"] == "count_equals":
            status = "passed" if len(ordinals) == predicate["expected"] else "failed"
        elif len(ordinals) == 1 and predicate["operation"] == "equals":
            observed = events[ordinals[0]]
            try:
                for part in predicate["field_path"]:
                    if type(part) is str and type(observed) is dict and part in observed:
                        observed = observed[part]
                    elif type(part) is int and type(observed) is list and part < len(observed):
                        observed = observed[part]
                    else:
                        raise LookupError("observed_path_missing")
                status = "passed" if canonical_bytes(observed) == canonical_bytes(predicate["expected"]) else "failed"
            except LookupError:
                pass
        outcomes.append(PredicateOutcome(predicate["id"], status, ordinals,
            tuple(receipt.raw_event_bytes[i] for i in ordinals)))
    statuses = {outcome.status for outcome in outcomes}
    status = "failed" if "failed" in statuses else "insufficient" if "insufficient" in statuses else "passed"
    return DriverAssessment(**base, status=status, outcomes=tuple(outcomes))
