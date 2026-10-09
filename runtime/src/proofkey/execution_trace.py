"""Bounded, content-free views of unverified CLI receipt claims.

This module observes no transport, readback, publication file or runtime state.
"""
from datetime import datetime
import json
import math
from typing import Annotated, Literal, get_args, get_origin
from types import UnionType
from typing import Union

from pydantic import BaseModel, ConfigDict, Field

from . import contracts, host_contracts
from .bootstrap import CliReceiptV1
from .contracts import FrozenDict, FrozenList, WireModel
from .host_contracts import BatchRunReceiptV1

MAX_INPUT_BYTES = 1_048_576
MAX_DEPTH = 64
MAX_NODES = 50_000
MAX_POSITIONS = 128
MAX_EFFECTS_PER_POSITION = 256
MAX_TOTAL_EFFECTS = 4_096
MAX_OUTPUT_BYTES = 262_144


class TraceError(ValueError):
    """Only a closed error code crosses the projection boundary."""

    def __init__(self, code="invalid_receipt"):
        super().__init__("trace_limit_exceeded" if code == "trace_limit_exceeded" else "invalid_receipt")


class _TraceModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True,
        allow_inf_nan=False, validate_default=True, revalidate_instances="always")


CaseAlias = Annotated[str, Field(pattern=r"^case-[1-9][0-9]{0,2}$")]
CommandAlias = Annotated[str, Field(pattern=r"^command-[1-9][0-9]{0,4}$")]
EffectAlias = Annotated[str, Field(pattern=r"^effect-[1-9][0-9]{0,3}$")]
RunAlias = Literal["run-1"]
ReleaseAlias = Literal["release-1"]
Count = Annotated[int, Field(ge=0, le=MAX_NODES)]
Ordinal = Annotated[int, Field(ge=0, lt=MAX_POSITIONS)]
PositionCount = Annotated[int, Field(ge=0, le=MAX_POSITIONS)]
Duration = Annotated[float, Field(ge=0)]
Publication = Literal["unknown", "not_started", "not_attempted", "partial", "committed"]


class EffectTraceV1(_TraceModel):
    effect: EffectAlias
    status: contracts.VerificationStatus
    basis: Literal["receipt_reported"] = "receipt_reported"


class PositionTraceV1(_TraceModel):
    ordinal: Ordinal
    case: CaseAlias | None
    command: CommandAlias | None
    admission_status: Literal["not_attempted", "unresolved", "joined"]
    execution_outcome: Literal["unknown", "not_started", "invalid_request", "denied", "result", "deadline_exceeded", "runtime_error"]
    host_outcome: host_contracts.Outcome | Literal["unknown"]
    host_started: bool | None
    access_status: Literal["unknown", "authorized", "denied", "error"]
    inventory_status: Literal["unknown", "committed", "partial", "unavailable", "not_admitted"]
    publication_status: Publication
    export_outcome: Literal["not_attempted", "written", "failed"]
    effects: tuple[EffectTraceV1, ...] = ()
    historical: bool | None = None
    wait_status: Literal["unknown", "none", "pending", "expired", "answered"] = "unknown"
    handoff_status: Literal["unknown", "none", "pending", "accepted", "rejected", "outcome_unknown"] = "unknown"
    media_status: Literal["unknown", "none", "pending", "completed", "failed", "unavailable", "outcome_unknown"] = "unknown"
    stop_requested: bool | None = None
    elapsed_seconds: Duration | None = None
    overrun_seconds: Duration | None = None


class ShutdownTraceV1(_TraceModel):
    admission_closed: bool
    owner_closed: bool
    inventory_failure: bool
    pending_commands: tuple[CommandAlias, ...]
    cancelled_commands: tuple[CommandAlias, ...]
    pending_count: Count
    cancelled_count: Count
    elapsed_seconds: Duration
    overrun_seconds: Duration


class ExecutionTraceV1(_TraceModel):
    kind: Literal["proofkey-execution-trace-v1"] = "proofkey-execution-trace-v1"
    provenance: Literal["unverified_receipt_projection"] = "unverified_receipt_projection"
    transport_dispatch: Literal["unknown"] = "unknown"
    original_readback_observation: Literal["not_observed"] = "not_observed"
    publication_files_checked: Literal[False] = False
    bootstrap_failure: Literal["invalid_usage", "invalid_configuration", "invalid_input", "bootstrap_unavailable", "owner_pending"] | None = None
    run: RunAlias | None = None
    release: ReleaseAlias | None = None
    mode: host_contracts.Mode | None = None
    clock_mode: Literal["system_utc", "synthetic_replay"] | None = None
    input_outcome: Literal["unknown", "admitted", "invalid_command", "invalid_document"] = "unknown"
    run_outcome: Literal["unknown", "completed", "invalid_document", "deadline_exceeded", "publication_failed", "abandoned_pending", "runtime_error"] = "unknown"
    publication_status: Publication = "unknown"
    position_count: PositionCount | None = None
    positions: tuple[PositionTraceV1, ...] = ()
    unresolved_ordinals: tuple[Ordinal, ...] = ()
    pending_commands: tuple[CommandAlias, ...] = ()
    elapsed_seconds: Duration | None = None
    publication_seconds: Duration | None = None
    overrun_seconds: Duration | None = None
    shutdown: ShutdownTraceV1 | None = None


_INPUT_MODELS = {value for module in (contracts, host_contracts) for value in vars(module).values()
                 if isinstance(value, type) and issubclass(value, WireModel)} | {CliReceiptV1}
_OUTPUT_MODELS = {ExecutionTraceV1, PositionTraceV1, EffectTraceV1, ShutdownTraceV1}


def _model_options(annotation):
    if get_origin(annotation) is Annotated:
        return _model_options(get_args(annotation)[0])
    if get_origin(annotation) in (UnionType, Union):
        return set().union(*(_model_options(arg) for arg in get_args(annotation)))
    return {annotation} if isinstance(annotation, type) and issubclass(annotation, BaseModel) else set()


def _container_annotation(annotation, container):
    if get_origin(annotation) is Annotated:
        return _container_annotation(get_args(annotation)[0], container)
    if get_origin(annotation) in (UnionType, Union):
        for option in get_args(annotation):
            if get_origin(option) is container:
                return option
    return annotation


def _detach(value, allowed, *, annotation=None, active=None, budget=None, depth=0):
    """Inspect actual declared fields; serializers must never erase bad data."""
    if active is None:
        active, budget = set(), [0]
    budget[0] += 1
    if budget[0] > MAX_NODES or depth > MAX_DEPTH:
        raise TraceError("trace_limit_exceeded")
    kind = type(value)
    expected = _model_options(annotation)
    if expected and value is not None and kind not in expected:
        raise TraceError()
    if kind in (str, int, bool, type(None)):
        return value
    if kind is float:
        if not math.isfinite(value):
            raise TraceError()
        return value
    if kind is datetime:
        return value
    if kind not in allowed and kind not in (dict, FrozenDict, list, FrozenList, tuple):
        raise TraceError()
    identity = id(value)
    if identity in active:
        raise TraceError()
    active.add(identity)
    try:
        if kind in allowed:
            if annotation is not None and kind not in expected:
                raise TraceError()
            fields = kind.model_fields
            if set(value.__dict__) != set(fields) or getattr(value, "__pydantic_extra__", None):
                raise TraceError()
            return {name: _detach(value.__dict__[name], allowed, annotation=field.annotation,
                active=active, budget=budget, depth=depth + 1) for name, field in fields.items()}
        if kind in (dict, FrozenDict):
            result = {}
            container = _container_annotation(annotation, dict)
            arguments = get_args(container)
            child_annotation = arguments[1] if get_origin(container) is dict else annotation
            for key, item in value.items():
                if type(key) is not str:
                    raise TraceError()
                _detach(key, allowed, active=active, budget=budget, depth=depth + 1)
                result[key] = _detach(item, allowed, annotation=child_annotation,
                    active=active, budget=budget, depth=depth + 1)
            return result
        container = _container_annotation(annotation, tuple if kind is tuple else list)
        arguments = get_args(container)
        def child_annotation(index):
            if get_origin(container) is list or (get_origin(container) is tuple and arguments[-1] is Ellipsis):
                return arguments[0]
            if get_origin(container) is tuple and index < len(arguments):
                return arguments[index]
            return annotation
        result = [_detach(item, allowed, annotation=child_annotation(index),
            active=active, budget=budget, depth=depth + 1) for index, item in enumerate(value)]
        return tuple(result) if kind is tuple else result
    finally:
        active.remove(identity)


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise TraceError()
        value[key] = item
    return value


def _scan_depth(text):
    depth, quoted, escaped = 0, False, False
    for character in text:
        if quoted:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                quoted = False
        elif character == '"':
            quoted = True
        elif character in "[{":
            depth += 1
            if depth > MAX_DEPTH:
                raise TraceError("trace_limit_exceeded")
        elif character in "]}":
            depth -= 1


def parse_cli_receipt(data: bytes) -> CliReceiptV1:
    """Parse only bounded UTF-8 JSON, preserving invalid/extra fields for validation."""
    if type(data) is not bytes:
        raise TraceError()
    if len(data) > MAX_INPUT_BYTES:
        raise TraceError("trace_limit_exceeded")
    try:
        text = data.decode("utf-8")
        _scan_depth(text)
        tree = json.loads(text, object_pairs_hook=_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(TraceError()))
        _detach(tree, set())
        encoded = json.dumps(tree, ensure_ascii=False, allow_nan=False)
        receipt = CliReceiptV1.model_validate_json(encoded)
        _validated_receipt(receipt)
        return receipt
    except TraceError:
        raise
    except (ValueError, TypeError, RecursionError, OverflowError):
        raise TraceError() from None


def _validated_receipt(receipt):
    if type(receipt) is not CliReceiptV1:
        raise TraceError()
    try:
        detached = _detach(receipt, _INPUT_MODELS, annotation=CliReceiptV1)
        value = CliReceiptV1.model_validate(detached)
        run = value.run
        if run is None:
            return value
        commands = ([p.command for p in run.positions] if type(run) is BatchRunReceiptV1 else [run.command])
        count = len(run.positions) if type(run) is BatchRunReceiptV1 else int(run.input is not None)
        if count > MAX_POSITIONS:
            raise TraceError("trace_limit_exceeded")
        total, ids = 0, set()
        for command in commands:
            if command is None:
                continue
            if command.command_id in ids:
                raise TraceError()
            ids.add(command.command_id)
            if type(run) is BatchRunReceiptV1:
                release, mode, clock = run.release_id, run.mode, run.clock_mode
            else:
                release, mode, clock = run.input.release_id, command.mode, command.clock_mode
            if (command.release_id, command.mode, command.clock_mode) != (release, mode, clock):
                raise TraceError()
            size = len(command.result.effects) if command.result is not None else 0
            total += size
            if size > MAX_EFFECTS_PER_POSITION or total > MAX_TOTAL_EFFECTS:
                raise TraceError("trace_limit_exceeded")
        return value
    except TraceError:
        raise
    except (ValueError, TypeError, AttributeError, RecursionError, OverflowError):
        raise TraceError() from None


def build_execution_trace(receipt: CliReceiptV1) -> ExecutionTraceV1:
    receipt = _validated_receipt(receipt)
    aliases = {}

    def alias(namespace, identity):
        if identity is None:
            return None
        values = aliases.setdefault(namespace, {})
        if identity not in values:
            values[identity] = f"{namespace}-{len(values) + 1}"
        return values[identity]

    def position(ordinal, case_id, command, admission, execution, publication, export):
        result = command.result if command is not None else None
        return PositionTraceV1(ordinal=ordinal, case=alias("case", case_id),
            command=alias("command", command.command_id) if command else None,
            admission_status=admission, execution_outcome=execution,
            host_outcome=command.outcome if command else "unknown",
            host_started=command.started_at is not None if command else None,
            access_status=result.status if result else "unknown",
            inventory_status=command.inventory_status if command else "unknown",
            publication_status=publication, export_outcome=export,
            effects=tuple(EffectTraceV1(effect=alias("effect", key), status=effect.status)
                for key, effect in sorted(result.effects.items())) if result else (),
            historical=result.historical if result else None,
            wait_status=result.wait_status if result else "unknown",
            handoff_status=result.handoff_status if result else "unknown",
            media_status=result.media_status if result else "unknown",
            stop_requested=result.stop.requested if result else None,
            elapsed_seconds=command.elapsed_seconds if command else None,
            overrun_seconds=command.overrun_seconds if command else None)

    run = receipt.run
    fields = {"bootstrap_failure": receipt.failure}
    if run is not None:
        fields.update(run=alias("run", run.run_id), input_outcome=run.input_outcome,
            publication_status=run.publication_status, elapsed_seconds=run.elapsed_seconds,
            publication_seconds=run.publication_seconds, overrun_seconds=run.overrun_seconds)
        if type(run) is BatchRunReceiptV1:
            fields.update(release=alias("release", run.release_id), mode=run.mode,
                clock_mode=run.clock_mode, position_count=run.position_count, run_outcome=run.outcome,
                unresolved_ordinals=run.unresolved_admission_ordinals,
                positions=tuple(position(p.inventory.ordinal, p.inventory.supplied_case_id,
                    p.command, p.admission_status, p.execution_outcome, p.publication_status,
                    p.export_outcome) for p in run.positions))
        else:
            command = run.command
            fields.update(release=alias("release", run.input.release_id) if run.input else None,
                mode=command.mode if command else None, clock_mode=command.clock_mode if command else None,
                position_count=1 if run.input else None,
                unresolved_ordinals=(0,) if run.unresolved_admission else ())
            if run.input:
                fields["positions"] = (position(0, run.input.supplied_case_id, command,
                    "joined" if command else "unresolved" if run.unresolved_admission else "not_attempted",
                    "result" if command and command.result else "unknown", run.publication_status,
                    run.export_outcome),)
        fields["pending_commands"] = tuple(alias("command", item) for item in run.pending_command_ids)
    shutdown = receipt.shutdown
    if shutdown is not None:
        fields["shutdown"] = ShutdownTraceV1(admission_closed=shutdown.admission_closed,
            owner_closed=shutdown.owner_closed, inventory_failure=shutdown.inventory_failure,
            pending_commands=tuple(alias("command", item) for item in shutdown.pending_command_ids),
            cancelled_commands=tuple(alias("command", item) for item in shutdown.cancelled_command_ids),
            pending_count=len(shutdown.pending_command_ids), cancelled_count=len(shutdown.cancelled_command_ids),
            elapsed_seconds=shutdown.elapsed_seconds, overrun_seconds=shutdown.overrun_seconds)
    return ExecutionTraceV1(**fields)


def _trace_shape(value):
    """Check the representation the local projector can actually produce."""
    count = value.position_count
    if count is None:
        if value.positions or value.unresolved_ordinals:
            raise TraceError()
    elif len(value.positions) != count or tuple(p.ordinal for p in value.positions) != tuple(range(count)):
        raise TraceError()
    if value.run is None and (value.release is not None or value.mode is not None
            or value.clock_mode is not None or value.input_outcome != "unknown"
            or value.run_outcome != "unknown" or value.publication_status != "unknown"
            or count is not None or value.pending_commands or value.elapsed_seconds is not None
            or value.publication_seconds is not None or value.overrun_seconds is not None):
        raise TraceError()
    if value.input_outcome == "admitted" and count is None:
        raise TraceError()
    if value.unresolved_ordinals != tuple(p.ordinal for p in value.positions if p.admission_status == "unresolved"):
        raise TraceError()

    seen = {"case": set(), "command": set(), "effect": set()}
    def counter(namespace, token):
        if token is None:
            return
        known = seen[namespace]
        if token not in known:
            if token != f"{namespace}-{len(known) + 1}":
                raise TraceError()
            known.add(token)

    commands = []
    for row in value.positions:
        counter("case", row.case)
        counter("command", row.command)
        if (row.command is not None) != (row.admission_status == "joined"):
            raise TraceError()
        if row.command is not None:
            if row.command in commands:
                raise TraceError()
            commands.append(row.command)
        row_effects = set()
        for effect in row.effects:
            counter("effect", effect.effect)
            if effect.effect in row_effects:
                raise TraceError()
            row_effects.add(effect.effect)
    pending = set(value.pending_commands)
    if (len(pending) != len(value.pending_commands)
            or tuple(command for command in commands if command in pending) != value.pending_commands
            or any(row.host_outcome == "started_pending" and row.command not in pending for row in value.positions)):
        raise TraceError()
    # Shutdown is only envelope-grouped: it may introduce additional command identities.
    if value.shutdown is not None:
        shutdown = value.shutdown
        if (shutdown.pending_count != len(shutdown.pending_commands)
                or shutdown.cancelled_count != len(shutdown.cancelled_commands)):
            raise TraceError()
        for command in (*shutdown.pending_commands, *shutdown.cancelled_commands):
            counter("command", command)


def _validated_trace(trace):
    if type(trace) is not ExecutionTraceV1:
        raise TraceError()
    try:
        detached = _detach(trace, _OUTPUT_MODELS, annotation=ExecutionTraceV1)
        value = ExecutionTraceV1.model_validate(detached)
        if len(value.positions) > MAX_POSITIONS or sum(len(p.effects) for p in value.positions) > MAX_TOTAL_EFFECTS:
            raise TraceError("trace_limit_exceeded")
        if any(len(p.effects) > MAX_EFFECTS_PER_POSITION for p in value.positions):
            raise TraceError("trace_limit_exceeded")
        # Literal[False] accepts integer zero in Pydantic; retain exact boolean type.
        if type(detached["publication_files_checked"]) is not bool:
            raise TraceError()
        _trace_shape(value)
        return value
    except TraceError:
        raise
    except (ValueError, TypeError, AttributeError, RecursionError, OverflowError):
        raise TraceError() from None


def _bounded_output(text):
    if len(text.encode("utf-8")) > MAX_OUTPUT_BYTES:
        raise TraceError("trace_limit_exceeded")
    return text


def render_trace_json(trace: ExecutionTraceV1) -> str:
    value = _validated_trace(trace)
    return _bounded_output(value.model_dump_json())


def render_trace_markdown(trace: ExecutionTraceV1) -> str:
    value = _validated_trace(trace)
    # Every interpolated value has passed the closed output schema.
    lines = ["# Execution receipt trace", "", "Provenance: unverified_receipt_projection",
        "Transport dispatch: unknown", "Original readback observation: not_observed",
        "Publication files checked: false", "",
        f"Bootstrap failure: {value.bootstrap_failure or 'none'}",
        f"Run: {value.run or 'unknown'}; release: {value.release or 'unknown'}",
        f"Mode: {value.mode or 'unknown'}; clock: {value.clock_mode or 'unknown'}",
        f"Input: {value.input_outcome}; run outcome: {value.run_outcome}; publication: {value.publication_status}",
        f"Position count: {value.position_count if value.position_count is not None else 'unknown'}",
        f"Unresolved ordinals: {', '.join(str(i) for i in value.unresolved_ordinals) or 'none'}",
        f"Pending commands: {', '.join(value.pending_commands) or 'none'}", "",
        "| Ordinal | Case | Command | Admission | Execution | Host | Started | Access | Inventory | Publication | Export |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    def fact(item):
        return "unknown" if item is None else str(item).lower()
    for row in value.positions:
        lines.append("| " + " | ".join(str(item) for item in (row.ordinal, row.case or "unknown",
            row.command or "unknown", row.admission_status, row.execution_outcome, row.host_outcome,
            fact(row.host_started), row.access_status, row.inventory_status, row.publication_status,
            row.export_outcome)) + " |")
    lines.append("")
    for row in value.positions:
        lines.append(f"Position {row.ordinal} result: historical={fact(row.historical)}; wait={row.wait_status}; "
            f"handoff={row.handoff_status}; media={row.media_status}; stop_requested={fact(row.stop_requested)}; "
            f"elapsed_seconds={fact(row.elapsed_seconds)}; overrun_seconds={fact(row.overrun_seconds)}")
        for effect in row.effects:
            lines.append(f"Position {row.ordinal} effect {effect.effect}: {effect.status} (receipt_reported)")
    lines.extend(["", f"Run elapsed_seconds={fact(value.elapsed_seconds)}; "
        f"publication_seconds={fact(value.publication_seconds)}; overrun_seconds={fact(value.overrun_seconds)}"])
    if value.shutdown is None:
        lines.append("Shutdown: unknown")
    else:
        shutdown = value.shutdown
        lines.extend([f"Shutdown: admission_closed={fact(shutdown.admission_closed)}; "
            f"owner_closed={fact(shutdown.owner_closed)}; inventory_failure={fact(shutdown.inventory_failure)}",
            f"Shutdown pending: {', '.join(shutdown.pending_commands) or 'none'}; count={shutdown.pending_count}",
            f"Shutdown cancelled: {', '.join(shutdown.cancelled_commands) or 'none'}; count={shutdown.cancelled_count}",
            f"Shutdown elapsed_seconds={shutdown.elapsed_seconds}; overrun_seconds={shutdown.overrun_seconds}"])
    return _bounded_output("\n".join(lines))
