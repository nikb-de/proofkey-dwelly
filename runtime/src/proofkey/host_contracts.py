"""Strict host bookkeeping, never wire permission or a reproduction receipt."""
import json
import math
from typing import Annotated, Literal

from pydantic import Field, TypeAdapter, model_validator

from .contracts import (CanonicalRequest, CaseResult, Hash, Identifier, NonnegativeFloat,
                        ScopedReply, Timestamp, WireModel)
from .execution import ExecutionContext

Tag = Literal["run", "recover", "reply", "stop", "inspect-profile", "batch", "transfer"]
Mode = Literal["synthetic_replay", "offline_synthetic"]
Outcome = Literal["result", "inspection", "denied", "unavailable", "queue_full", "expired",
                  "cancelled_before_start", "started_pending", "infrastructure_error"]
Failure = Literal["invalid_command", "scope_denied", "queue_full", "deadline_exceeded", "cancelled_before_start",
                  "unavailable", "no_durable_inventory", "inventory_failed", "runtime_error", "host_closed"]


class HostLimitsV1(WireModel):
    queue_capacity: Annotated[int, Field(gt=0)] = 8
    max_command_bytes: Annotated[int, Field(gt=0)] = 65536
    max_execution_seconds: Annotated[float, Field(gt=0)] = 120.0
    inventory_max_bytes: Annotated[int, Field(gt=0)] = 262144
    shutdown_max_seconds: Annotated[float, Field(gt=0)] = 30.0


class _Command(WireModel):
    version: Literal["host-command-v1"] = "host-command-v1"
    release_id: Identifier


class RunCommandV1(_Command):
    tag: Literal["run"] = "run"
    request: CanonicalRequest


class RecoverCommandV1(_Command):
    tag: Literal["recover"] = "recover"
    case_id: Identifier


class ReplyCommandV1(_Command):
    tag: Literal["reply"] = "reply"
    reply: ScopedReply


class StopCommandV1(_Command):
    tag: Literal["stop"] = "stop"
    case_id: Identifier
    generation: Identifier


class InspectProfileCommandV1(_Command):
    tag: Literal["inspect-profile"] = "inspect-profile"


class UnavailableCommandV1(_Command):
    tag: Literal["batch", "transfer"]


HostCommand = Annotated[RunCommandV1 | RecoverCommandV1 | ReplyCommandV1 | StopCommandV1 |
                        InspectProfileCommandV1 | UnavailableCommandV1, Field(discriminator="tag")]
_COMMANDS = (RunCommandV1, RecoverCommandV1, ReplyCommandV1, StopCommandV1,
             InspectProfileCommandV1, UnavailableCommandV1)
_ADAPTER = TypeAdapter(HostCommand)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Invalid host command")
        result[key] = value
    return result


def _bounded_json(value, max_bytes):
    stack, count, size = [(value, 0)], 0, 0
    while stack:
        item, depth = stack.pop()
        count += 1
        if depth > 32 or count > max_bytes or size > max_bytes:
            raise ValueError("Invalid host command")
        if type(item) is dict:
            for key, child in item.items():
                if type(key) is not str:
                    raise ValueError("Invalid host command")
                size += len(key)
                stack.append((child, depth + 1))
        elif type(item) is list:
            stack.extend((child, depth + 1) for child in item)
        elif type(item) is str:
            size += len(item)
        elif type(item) in (bool, int) or item is None:
            size += 1
        elif type(item) is float and math.isfinite(item):
            size += 1
        else:
            raise ValueError("Invalid host command")
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    if len(encoded) > max_bytes:
        raise ValueError("Invalid host command")
    return encoded


def parse_command(value, *, max_bytes=65536):
    """Detach bounded exact command input; no custom serializers or authority."""
    try:
        if type(max_bytes) is not int or max_bytes <= 0:
            raise ValueError
        if type(value) in _COMMANDS:
            value = value.model_dump(mode="json")
        elif type(value) is bytes:
            if len(value) > max_bytes:
                raise ValueError
            value = json.loads(value, object_pairs_hook=_pairs,
                               parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        if type(value) is not dict:
            raise ValueError
        encoded = _bounded_json(value, max_bytes)
        return _ADAPTER.validate_json(encoded)
    except (ValueError, TypeError, RecursionError, OverflowError):
        raise ValueError("Invalid host command") from None


class ExecutionWindowV1(WireModel):
    deadline: Timestamp
    captured_at: Timestamp
    captured_monotonic: float
    monotonic_deadline: float

    @model_validator(mode="after")
    def exact_window(self):
        ExecutionContext(self.deadline, self.captured_at, self.captured_monotonic, self.monotonic_deadline)
        return self

    @classmethod
    def from_context(cls, execution):
        if type(execution) is not ExecutionContext:
            raise ValueError("Exact host context required")
        return cls(**{name: getattr(execution, name) for name in cls.model_fields})


class DetachedProfileViewV1(WireModel):
    release_id: Identifier
    mode: Mode
    profile_id: Identifier
    profile_version: Identifier
    profile_file_hash: Hash
    profile_hash: Hash
    process_hash: Hash
    policy_hash: Hash
    fixture_hash: Hash


class InventoryReferenceV1(WireModel):
    name: Annotated[str, Field(pattern=r"^COMMAND-[0-9]{8}-[012]\.json$")]
    file_hash: Hash


class CommandReceiptV1(WireModel):
    kind: Literal["host-command-receipt-v1"] = "host-command-receipt-v1"
    command_id: Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")]
    command_tag: Tag | None
    release_id: Identifier
    mode: Mode
    clock_mode: Literal["system_utc", "synthetic_replay"]
    outcome: Outcome
    payload_hash: Hash | None = None
    execution: ExecutionWindowV1 | None = None
    queued_at: Timestamp | None = None
    started_at: Timestamp | None = None
    finished_at: Timestamp | None = None
    elapsed_seconds: NonnegativeFloat | None = None
    overrun_seconds: NonnegativeFloat | None = None
    result: CaseResult | None = None
    inspection: DetachedProfileViewV1 | None = None
    inventory_status: Literal["committed", "partial", "unavailable", "not_admitted"]
    inventory_references: tuple[InventoryReferenceV1, ...] = ()
    failure: Failure | None = None

    @model_validator(mode="after")
    def factual_shape(self):
        if (self.outcome == "result") != (self.result is not None):
            raise ValueError("Actual returned result required")
        if (self.outcome == "inspection") != (self.inspection is not None):
            raise ValueError("Actual detached inspection required")
        if self.outcome == "cancelled_before_start" and self.started_at is not None:
            raise ValueError("Started work cannot be cancelled-before-start")
        if self.outcome == "started_pending" and (self.started_at is None or self.finished_at is not None):
            raise ValueError("Started pending requires actual start without completion")
        return self


class CommandInventoryV1(WireModel):
    kind: Literal["host-command-inventory-v1"] = "host-command-inventory-v1"
    command_id: Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")]
    command_tag: Tag
    release_id: Identifier
    mode: Mode
    payload_hash: Hash
    execution: ExecutionWindowV1
    phase: Literal["queued", "started", "finished"]
    timestamp: Timestamp
    outcome: Outcome | None = None
    failure: Failure | None = None
    result_hash: Hash | None = None

    @model_validator(mode="after")
    def factual_phase(self):
        if (self.phase == "finished") != (self.outcome is not None):
            raise ValueError("Only finished inventory records an outcome")
        if self.result_hash is not None and (self.phase != "finished" or self.outcome not in {"result", "inspection"}):
            raise ValueError("No unreturned result digest")
        if self.phase == "finished" and self.outcome in {"result", "inspection"} and self.result_hash is None:
            raise ValueError("Returned evidence digest required")
        if self.outcome == "started_pending":
            raise ValueError("Pending is not a factual finished state")
        return self


class ShutdownReceiptV1(WireModel):
    kind: Literal["host-shutdown-receipt-v1"] = "host-shutdown-receipt-v1"
    admission_closed: bool
    owner_closed: bool
    pending_command_ids: tuple[str, ...]
    cancelled_command_ids: tuple[str, ...]
    started_at: Timestamp
    finished_at: Timestamp
    elapsed_seconds: NonnegativeFloat
    overrun_seconds: NonnegativeFloat
    inventory_failure: bool = False
