"""Immutable public driver evidence, separate from provisional legacy labels."""
from dataclasses import asdict, dataclass, fields
from hashlib import sha256
import json
import math

MAX_ITEM_BYTES = 1_048_576
MAX_RECEIPT_BYTES = 8 * MAX_ITEM_BYTES
MAX_EVENTS = 64


def require_text(value, *, maximum=256):
    if type(value) is not str or not value or len(value) > maximum:
        raise ValueError("Bounded nonempty exact string required")
    try:
        value.encode("utf-8")
    except UnicodeError:
        raise ValueError("UTF-8 string required") from None
    return value


def require_hash(value):
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError("Lowercase SHA-256 required")
    return value


def require_int(value, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError("Exact bounded integer required")
    return value


def require_bytes(raw):
    if type(raw) is not bytes or len(raw) > MAX_ITEM_BYTES:
        raise ValueError("Exact bounded immutable bytes required")
    return raw


def require_strings(values, *, maximum=64):
    if type(values) is not tuple or len(values) > maximum:
        raise ValueError("Bounded immutable string tuple required")
    for value in values:
        require_text(value)
    if len(set(values)) != len(values):
        raise ValueError("Duplicate string identity")


def _json_value(value, depth=0):
    if depth > 32:
        raise ValueError("JSON nesting exceeds bound")
    if value is None or type(value) is bool:
        return
    if type(value) is int:
        require_int(value, -(2**63), 2**63 - 1)
    elif type(value) is float:
        if not math.isfinite(value):
            raise ValueError("Finite JSON number required")
    elif type(value) is str:
        if len(value) > MAX_ITEM_BYTES:
            raise ValueError("JSON string exceeds bound")
        value.encode("utf-8")
    elif type(value) in (dict, list):
        if len(value) > 4096:
            raise ValueError("JSON collection exceeds bound")
        if type(value) is dict:
            for key, item in value.items():
                require_text(key, maximum=1024)
                _json_value(item, depth + 1)
        else:
            for item in value:
                _json_value(item, depth + 1)
    else:
        raise ValueError("Exact JSON types required")


def canonical_bytes(value):
    try:
        _json_value(value)
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                         allow_nan=False).encode("utf-8")
        return require_bytes(raw)
    except (TypeError, UnicodeError, RecursionError):
        raise ValueError("Invalid canonical JSON") from None


def strict_loads(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON field")
            result[key] = value
        return result
    require_bytes(raw)
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))
        if canonical_bytes(value) != raw:
            raise ValueError("Noncanonical JSON")
        return value
    except (TypeError, UnicodeError, RecursionError):
        raise ValueError("Invalid canonical JSON") from None


def digest_bytes(raw):
    require_bytes(raw)
    return sha256(raw).hexdigest()


def require_object(raw):
    value = strict_loads(raw)
    if type(value) is not dict:
        raise ValueError("Canonical object required")
    return value


def require_event(raw):
    value = require_object(raw)
    require_text(value.get("event_tag"))
    return value


def require_source(raw):
    value = require_object(raw)
    if (set(value) != {"version", "kind", "files"} or value["version"] != "candidate-source-v1"
            or type(value["kind"]) is not str or value["kind"] not in {"filesystem", "fixture-only"}
            or type(value["files"]) is not dict or not value["files"]):
        raise ValueError("Explicit complete source snapshot required")
    for name, identity in value["files"].items():
        require_text(name, maximum=1024)
        require_hash(identity)
    return value


@dataclass(frozen=True, slots=True)
class DriverManifest:
    version: str
    driver_id: str
    obligation: str
    variant: str
    case_id: str
    independence_group: str
    case_bytes_hash: str
    scenario_hash: str
    driver_code_hash: str
    candidate_manifest_hash: str
    profile_name: str
    profile_hash: str
    process_hash: str
    policy_hash: str
    expectation_version: str
    expectation_hash: str
    execution_kind: str
    dependency_ids: tuple[str, ...]

    def __post_init__(self):
        for field in fields(self):
            value = getattr(self, field.name)
            if field.name.endswith("_hash"):
                require_hash(value)
            elif field.name != "dependency_ids":
                require_text(value)
        require_strings(self.dependency_ids)
        if (self.version != "runtime-driver-v1" or self.obligation not in {f"R{i:02}" for i in range(1, 16)}
                or self.execution_kind not in {"public_sequence", "subprocess_barrier", "controlled_order"}):
            raise ValueError("Unknown driver manifest version/obligation/kind")

    def to_bytes(self):
        self.__post_init__()
        data = asdict(self)
        data["dependency_ids"] = list(self.dependency_ids)
        return canonical_bytes(data)

    def to_wire(self):
        return strict_loads(self.to_bytes())

    @classmethod
    def from_bytes(cls, raw):
        data = require_object(raw)
        if set(data) != {field.name for field in fields(cls)} or type(data["dependency_ids"]) is not list:
            raise ValueError("Exact manifest fields required")
        data["dependency_ids"] = tuple(data["dependency_ids"])
        return cls(**data)


@dataclass(frozen=True, slots=True)
class RunnerReceipt:
    manifest_bytes: bytes
    manifest_hash: str
    ordinal: int
    repetition: int
    status: str
    dependency_limits: tuple[str, ...] = ()
    raw_event_bytes: tuple[bytes, ...] = ()
    raw_output_bytes: bytes | None = None
    raw_output_hash: str | None = None
    score_projection_bytes: bytes | None = None
    projection_version: str = "effect-projection-v1"
    error_bytes: bytes | None = None
    process_exit: int | None = None
    barrier_receipt_bytes: tuple[bytes, ...] = ()
    elapsed_seconds: float | None = None
    source_pre_manifest_bytes: bytes | None = None
    source_post_manifest_bytes: bytes | None = None

    def __post_init__(self):
        manifest = DriverManifest.from_bytes(self.manifest_bytes)
        require_hash(self.manifest_hash)
        if digest_bytes(self.manifest_bytes) != self.manifest_hash:
            raise ValueError("Manifest hash differs from captured bytes")
        require_int(self.ordinal, 0, 255)
        require_int(self.repetition, 0, 15)
        if type(self.status) is not str or self.status not in {
                "completed", "failed", "invalid_output", "no_output", "not_started"}:
            raise ValueError("Unknown capture status")
        require_strings(self.dependency_limits)
        require_text(self.projection_version)
        if self.projection_version != "effect-projection-v1":
            raise ValueError("Unknown projection version")
        total = len(self.manifest_bytes)
        for name in ("raw_event_bytes", "barrier_receipt_bytes"):
            values = getattr(self, name)
            if type(values) is not tuple or len(values) > MAX_EVENTS:
                raise ValueError("Bounded immutable capture tuple required")
            for raw in values:
                require_event(raw) if name == "raw_event_bytes" else require_object(raw)
                total += len(raw)
        for name in ("raw_output_bytes", "score_projection_bytes", "error_bytes",
                     "source_pre_manifest_bytes", "source_post_manifest_bytes"):
            raw = getattr(self, name)
            if raw is not None:
                require_bytes(raw)
                total += len(raw)
                if name in {"source_pre_manifest_bytes", "source_post_manifest_bytes"}:
                    require_source(raw)
        if total > MAX_RECEIPT_BYTES:
            raise ValueError("Aggregate receipt exceeds bound")
        if self.raw_output_bytes is None:
            if self.raw_output_hash is not None or self.score_projection_bytes is not None or self.status == "completed":
                raise ValueError("Missing output cannot have hash/projection/success")
        else:
            require_hash(self.raw_output_hash)
            if digest_bytes(self.raw_output_bytes) != self.raw_output_hash:
                raise ValueError("Output hash differs from captured bytes")
            if self.status in {"no_output", "not_started"}:
                raise ValueError("Unavailable position cannot contain output")
        if self.score_projection_bytes is not None:
            EffectProjection(self.score_projection_bytes)
        if self.elapsed_seconds is not None:
            if type(self.elapsed_seconds) is int:
                require_int(self.elapsed_seconds, 0, 2**63 - 1)
            if (type(self.elapsed_seconds) not in (int, float) or not math.isfinite(self.elapsed_seconds)
                    or self.elapsed_seconds < 0):
                raise ValueError("Finite nonnegative observed elapsed required")
        if self.process_exit is not None:
            require_int(self.process_exit, -(2**31), 2**31 - 1)
        if self.status == "completed":
            require_object(self.raw_output_bytes)
            if (self.source_pre_manifest_bytes is None or self.source_post_manifest_bytes is None
                    or self.source_pre_manifest_bytes != self.source_post_manifest_bytes
                    or digest_bytes(self.source_pre_manifest_bytes) != manifest.candidate_manifest_hash
                    or self.elapsed_seconds is None or self.elapsed_seconds > 60
                    or self.error_bytes is not None or self.dependency_limits or self.process_exit not in (None, 0)):
                raise ValueError("Completed capture requires joined source and eligibility")

    def events(self):
        """Fresh detached trace objects; never aliases into captured evidence."""
        return tuple(require_event(raw) for raw in self.raw_event_bytes)


@dataclass(frozen=True, slots=True)
class EffectProjection:
    """Optional legacy effect-only companion, never trace obligation evidence."""
    output_bytes: bytes
    version: str = "effect-projection-v1"

    def __post_init__(self):
        from .contracts import ObservedOutput
        if type(self.version) is not str or self.version != "effect-projection-v1":
            raise ValueError("Unknown effect projection")
        ObservedOutput.model_validate(require_object(self.output_bytes))


@dataclass(frozen=True, slots=True)
class DriverInput:
    input_sequence_bytes: bytes
    scenario_bytes: bytes
    case_id: str
    obligation: str
    variant: str
    candidate_manifest_hash: str
    profile_name: str
    profile_hash: str
    process_hash: str
    policy_hash: str

    def __post_init__(self):
        for name in ("input_sequence_bytes", "scenario_bytes"):
            strict_loads(getattr(self, name))
        for name in ("case_id", "obligation", "variant", "profile_name"):
            require_text(getattr(self, name))
        if self.obligation not in {f"R{i:02}" for i in range(1, 16)}:
            raise ValueError("Unknown obligation")
        for name in ("candidate_manifest_hash", "profile_hash", "process_hash", "policy_hash"):
            require_hash(getattr(self, name))


@dataclass(frozen=True, slots=True)
class DriverCapture:
    """Trusted callback return; events must exactly join the observed sink."""
    raw_event_bytes: tuple[bytes, ...]
    raw_output_bytes: bytes | None
    score_projection: EffectProjection | None = None

    def __post_init__(self):
        if type(self.raw_event_bytes) is not tuple or len(self.raw_event_bytes) > MAX_EVENTS:
            raise ValueError("Bounded captured event tuple required")
        for raw in self.raw_event_bytes:
            require_event(raw)
        if self.raw_output_bytes is not None:
            require_bytes(self.raw_output_bytes)
        if self.score_projection is not None and type(self.score_projection) is not EffectProjection:
            raise ValueError("Typed effect projection required")
        if self.raw_output_bytes is None and self.score_projection is not None:
            raise ValueError("Missing output cannot project effects")


@dataclass(frozen=True, slots=True)
class PredicateOutcome:
    predicate_id: str
    status: str
    event_ordinals: tuple[int, ...]
    raw_event_bytes: tuple[bytes, ...]

    def __post_init__(self):
        require_text(self.predicate_id)
        require_text(self.status)
        if self.status not in {"passed", "failed", "insufficient"}:
            raise ValueError("Unknown predicate outcome")
        if (type(self.event_ordinals) is not tuple or type(self.raw_event_bytes) is not tuple
                or len(self.event_ordinals) != len(self.raw_event_bytes) or len(self.event_ordinals) > MAX_EVENTS):
            raise ValueError("Exact bounded raw trace references required")
        for ordinal, raw in zip(self.event_ordinals, self.raw_event_bytes):
            require_int(ordinal, 0, 63)
            require_event(raw)


@dataclass(frozen=True, slots=True)
class DriverAssessment:
    manifest_hash: str
    ordinal: int
    repetition: int
    status: str
    outcomes: tuple[PredicateOutcome, ...]
    reason: str | None = None

    def __post_init__(self):
        require_hash(self.manifest_hash)
        require_int(self.ordinal, 0, 255)
        require_int(self.repetition, 0, 15)
        require_text(self.status)
        if self.status not in {"passed", "failed", "insufficient", "ungraded"}:
            raise ValueError("Unknown driver assessment")
        if type(self.outcomes) is not tuple or len(self.outcomes) > MAX_EVENTS or any(
                type(outcome) is not PredicateOutcome for outcome in self.outcomes):
            raise ValueError("Typed immutable predicate outcomes required")
        if self.reason is not None:
            require_text(self.reason)
