"""Strict host bookkeeping, never wire permission or a reproduction receipt."""
import json
import math
from datetime import timedelta
from typing import Annotated, Literal, Union, get_args, get_origin
from types import UnionType

from pydantic import Field, TypeAdapter, model_validator

from .contracts import (CanonicalRequest, CaseResult, ExportReceipt, Hash, Identifier, NonnegativeFloat,
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


# Additive local library contracts; never source authority or authentication.
def _restore_library_json(value, annotation):
    """Restore only schema-declared tuples from JSON, never business JSON arrays.

    WireModel's before validator materializes JSON arrays into Python lists.
    Strict tuple fields therefore need an explicit local JSON-mode bridge.
    Python callers still must supply exact tuples; shared schemas stay unchanged.
    """
    origin, arguments = get_origin(annotation), get_args(annotation)
    if origin is Annotated:
        return _restore_library_json(value, arguments[0])
    if origin in (Union, UnionType):
        candidates = [item for item in arguments if isinstance(item, type) and issubclass(item, WireModel)]
        if type(value) is dict and candidates:
            for item in candidates:
                field = item.model_fields.get("kind")
                if field is not None and field.default == value.get("kind"):
                    return _restore_library_json(value, item)
            return _restore_library_json(value, candidates[0])
        return value
    if origin is tuple and type(value) is list:
        if len(arguments) == 2 and arguments[1] is Ellipsis:
            return tuple(_restore_library_json(item, arguments[0]) for item in value)
        return tuple(_restore_library_json(item, arguments[index]) if index < len(arguments) else item
                     for index, item in enumerate(value))
    if isinstance(annotation, type) and issubclass(annotation, WireModel) and type(value) is dict:
        return {key: _restore_library_json(item, annotation.model_fields[key].annotation)
                if key in annotation.model_fields else item for key, item in value.items()}
    return value


class _LibraryModel(WireModel):
    @model_validator(mode="before")
    @classmethod
    def declared_json_tuples(cls, value, info):
        return _restore_library_json(value, cls) if info.mode == "json" else value


class InterfaceLimitsV1(_LibraryModel):
    max_input_bytes: Annotated[int, Field(gt=0)] = 1048576
    max_positions: Annotated[int, Field(gt=0)] = 256
    max_depth: Annotated[int, Field(gt=0)] = 32
    max_run_bytes: Annotated[int, Field(gt=0)] = 4194304


class PublicationWindowV1(_LibraryModel):
    execution: ExecutionWindowV1
    deadline: Timestamp
    reserve_seconds: NonnegativeFloat
    monotonic_deadline: float

    @model_validator(mode="after")
    def original_anchor(self):
        reserve = timedelta(seconds=self.reserve_seconds)
        if (reserve.total_seconds() != self.reserve_seconds
                or self.deadline != self.execution.deadline + reserve
                or self.monotonic_deadline != self.execution.monotonic_deadline + self.reserve_seconds
                or self.deadline <= self.execution.captured_at):
            raise ValueError("Publication must retain the original window")
        return self


class BatchPositionInventoryV1(_LibraryModel):
    ordinal: Annotated[int, Field(ge=0)]
    supplied_id_shape: Literal["string", "missing", "non_string", "non_object"]
    supplied_case_id: str | None = None

    @model_validator(mode="after")
    def original_shape(self):
        if (self.supplied_id_shape == "string") != (self.supplied_case_id is not None):
            raise ValueError("Only actual supplied strings have an identity")
        return self


class ConsumedExportV1(_LibraryModel):
    actual_receipt: "ExportReceipt"
    actual_file_hashes: tuple[tuple[str, Hash], ...] = ()

    @model_validator(mode="after")
    def actual_export(self):
        from .identity import fingerprint
        receipt = self.actual_receipt
        if receipt.status == "written":
            if (tuple(name for name, _ in self.actual_file_hashes) != ("ANSWER.md", "REASONING.md")
                    or receipt.failure is not None or receipt.output_name != receipt.supplied_case_id
                    or receipt.output_hash != fingerprint(dict(self.actual_file_hashes))):
                raise ValueError("Written export requires actual fixed-file hashes")
        elif (self.actual_file_hashes or receipt.output_name is not None or receipt.output_hash is not None
              or receipt.failure not in EXPORT_FAILURES):
            raise ValueError("Failed export has no success fields")
        return self


EXPORT_FAILURES = ("unsafe_case_id", "unsafe_output_root", "output_ancestry_changed",
                   "output_integrity_failure", "invalid_result", "output_busy", "output_conflict", "export_io_error")

ExportFailureCode = Literal["unsafe_case_id", "unsafe_output_root", "output_ancestry_changed",
    "output_integrity_failure", "invalid_result", "output_busy", "output_conflict", "export_io_error"]
LibraryFailure = Failure | ExportFailureCode | Literal["invalid_document", "invalid_request",
    "result_scope_mismatch", "admission_unresolved", "publication_io_error", "publication_integrity_failure",
    "publication_limit_exceeded", "invalid_inventory"]
RunId = Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")]
Ordinal = Annotated[int, Field(ge=0, le=99999999)]


class BatchInputV1(_LibraryModel):
    kind: Literal["host-batch-input-v1"] = "host-batch-input-v1"
    encoding: Literal["exact_json_document_v1", "canonical_json_array_v1"]
    input_hash: Hash
    input_bytes: Annotated[int, Field(ge=0)]
    position_count: Annotated[int, Field(ge=0)]


class CommandInputInventoryV1(_LibraryModel):
    kind: Literal["host-command-input-v1"] = "host-command-input-v1"
    encoding: Literal["exact_json_document_v1", "canonical_closed_command_v1"]
    input_hash: Hash
    input_bytes: Annotated[int, Field(ge=0)]
    command_tag: Tag
    release_id: Identifier
    supplied_case_id: str | None = None


class RunReferenceV1(_LibraryModel):
    name: Annotated[str, Field(pattern=r"^(INPUT-INVENTORY|FINAL-MANIFEST|POSITION-[0-9]{8}-(ADMISSION|RESULT|PROGRESS))\.json$")]
    file_hash: Hash


class _ExportFacts(_LibraryModel):
    export_outcome: Literal["not_attempted", "written", "failed"] = "not_attempted"
    export: ConsumedExportV1 | None = None
    export_failure: ExportFailureCode | None = None

    @model_validator(mode="after")
    def coherent_export(self):
        if self.export_outcome == "not_attempted":
            if self.export is not None or self.export_failure is not None:
                raise ValueError("No invented export")
        elif self.export_outcome == "written":
            if self.export is None or self.export.actual_receipt.status != "written" or self.export_failure is not None:
                raise ValueError("Actual written export required")
        elif (self.export_failure is None or self.export is not None and
              (self.export.actual_receipt.status != "failed" or self.export.actual_receipt.failure != self.export_failure)):
            raise ValueError("Failed export requires a closed actual failure")
        return self


class BatchPositionReceiptV1(_ExportFacts):
    inventory: BatchPositionInventoryV1
    execution_outcome: Literal["not_started", "invalid_request", "denied", "result", "deadline_exceeded", "runtime_error"] = "not_started"
    command: CommandReceiptV1 | None = None
    result_hash: Hash | None = None
    failure: LibraryFailure | None = None
    admission_status: Literal["not_attempted", "unresolved", "joined"] = "not_attempted"
    publication_status: Literal["not_attempted", "committed", "partial"] = "not_attempted"
    references: tuple[RunReferenceV1, ...] = ()

    @model_validator(mode="after")
    def exact_position(self):
        from .identity import fingerprint
        if (self.admission_status == "joined") != (self.command is not None):
            raise ValueError("Only public returned commands join ordinals")
        result = self.command.result if self.command is not None else None
        if (self.execution_outcome == "result") != (result is not None):
            raise ValueError("Only actual result outcomes have results")
        if result is not None:
            if result.case_id != self.inventory.supplied_case_id or self.result_hash != fingerprint(result.model_dump(mode="json")):
                raise ValueError("Actual result must match supplied identity and hash")
        elif self.result_hash is not None or self.export_outcome != "not_attempted":
            raise ValueError("No unreturned result/export")
        if self.command is not None:
            mapping = {"result": "result", "denied": "denied", "expired": "deadline_exceeded",
                "started_pending": "deadline_exceeded", "cancelled_before_start": "not_started",
                "queue_full": "runtime_error", "unavailable": "runtime_error", "infrastructure_error": "runtime_error"}
            if self.execution_outcome != mapping.get(self.command.outcome):
                raise ValueError("Actual host outcome required")
        if self.export is not None and self.export.actual_receipt.supplied_case_id != self.inventory.supplied_case_id:
            raise ValueError("Export identity mismatch")
        _unique_references(self.references)
        return self


class _RunSnapshot(_LibraryModel):
    run_id: RunId
    release_id: Identifier
    mode: Mode
    clock_mode: Literal["system_utc", "synthetic_replay"]
    window: PublicationWindowV1
    references: tuple[RunReferenceV1, ...] = ()
    pending_command_ids: tuple[RunId, ...] = ()
    as_of: Timestamp

    @model_validator(mode="after")
    def no_self_reference(self):
        _unique_references(self.references)
        if any(ref.name == "FINAL-MANIFEST.json" for ref in self.references):
            raise ValueError("Snapshot cannot contain its own future hash")
        return self


class BatchManifestV1(_RunSnapshot):
    kind: Literal["host-batch-manifest-v1"] = "host-batch-manifest-v1"
    input: BatchInputV1
    inventories: tuple[BatchPositionInventoryV1, ...]
    positions: tuple[BatchPositionReceiptV1, ...]
    unresolved_admission_ordinals: tuple[Ordinal, ...] = ()

    @model_validator(mode="after")
    def all_positions(self):
        _batch_joins(self.input.position_count, self.positions, self.pending_command_ids,
                     self.unresolved_admission_ordinals, self.inventories)
        for position in self.positions:
            if position.command is not None:
                _command_run_join(position.command, self.release_id, self.mode, self.clock_mode, self.window)
            if any(ref not in self.references for ref in position.references):
                raise ValueError("Position references must join the snapshot")
        return self


class CommandManifestV1(_RunSnapshot, _ExportFacts):
    kind: Literal["host-command-manifest-v1"] = "host-command-manifest-v1"
    input: CommandInputInventoryV1
    command: CommandReceiptV1 | None = None
    unresolved_admission: bool = False

    @model_validator(mode="after")
    def exact_command(self):
        _standalone_joins(self)
        if self.command is not None:
            _command_run_join(self.command, self.release_id, self.mode, self.clock_mode, self.window)
        return self


class _RunMeasurements(_LibraryModel):
    run_id: RunId
    window: PublicationWindowV1
    publication_status: Literal["not_started", "partial", "committed"] = "not_started"
    final_reference: RunReferenceV1 | None = None
    started_at: Timestamp
    finished_at: Timestamp
    elapsed_seconds: NonnegativeFloat
    publication_seconds: NonnegativeFloat
    overrun_seconds: NonnegativeFloat
    command_elapsed_basis: Literal["retrieval_observation", "unavailable"] = "unavailable"
    pending_command_ids: tuple[RunId, ...] = ()

    @model_validator(mode="after")
    def final_readback(self):
        if (self.publication_status == "committed") != (self.final_reference is not None):
            raise ValueError("Committed publication requires actual final reference")
        if self.final_reference is not None and self.final_reference.name != "FINAL-MANIFEST.json":
            raise ValueError("Actual final marker required")
        if self.finished_at < self.started_at:
            raise ValueError("Reversed wrapper measurement")
        return self


class BatchRunReceiptV1(_RunMeasurements):
    kind: Literal["host-batch-run-receipt-v1"] = "host-batch-run-receipt-v1"
    input_outcome: Literal["admitted", "invalid_document"]
    input: BatchInputV1 | None
    position_count: Annotated[int, Field(ge=0)] | None
    positions: tuple[BatchPositionReceiptV1, ...] = ()
    release_id: Identifier
    mode: Mode
    clock_mode: Literal["system_utc", "synthetic_replay"]
    outcome: Literal["completed", "invalid_document", "deadline_exceeded", "publication_failed", "abandoned_pending", "runtime_error"]
    unresolved_admission_ordinals: tuple[Ordinal, ...] = ()
    observed_input_hash: Hash | None = None

    @model_validator(mode="after")
    def denominator_and_completion(self):
        if self.input_outcome == "invalid_document":
            if (self.input is not None or self.position_count is not None or self.positions
                    or self.pending_command_ids or self.unresolved_admission_ordinals
                    or self.publication_status != "not_started" or self.outcome != "invalid_document"):
                raise ValueError("Invalid documents have no invented denominator or publication")
        else:
            if self.input is None or self.position_count != self.input.position_count or self.observed_input_hash is not None:
                raise ValueError("Exact admitted input required")
            _batch_joins(self.position_count, self.positions, self.pending_command_ids, self.unresolved_admission_ordinals)
            if self.outcome == "completed" and (self.pending_command_ids or self.unresolved_admission_ordinals
                                                or self.publication_status != "committed"):
                raise ValueError("Completed coordinator requires joined final snapshot")
            if self.outcome == "invalid_document":
                raise ValueError("Admitted input is not an invalid document")
        return self


class CommandRunReceiptV1(_RunMeasurements, _ExportFacts):
    kind: Literal["host-command-run-receipt-v1"] = "host-command-run-receipt-v1"
    input_outcome: Literal["admitted", "invalid_command"]
    input: CommandInputInventoryV1 | None
    command: CommandReceiptV1 | None = None
    references: tuple[RunReferenceV1, ...] = ()
    unresolved_admission: bool = False

    @model_validator(mode="after")
    def actual_command_input(self):
        if self.input_outcome == "invalid_command":
            if (self.input is not None or self.command is not None or self.unresolved_admission
                    or self.pending_command_ids or self.publication_status != "not_started" or self.references
                    or self.export_outcome != "not_attempted"):
                raise ValueError("Invalid command cannot invent admission")
        elif self.input is None:
            raise ValueError("Admitted command input required")
        _standalone_joins(self)
        _unique_references(self.references)
        return self


class RunReadbackV1(_LibraryModel):
    kind: Literal["host-run-readback-v1"] = "host-run-readback-v1"
    run_id: RunId | None = None
    run_kind: Literal["command", "batch"] | None = None
    status: Literal["committed_snapshot", "partial", "invalid"]
    input_inventory: CommandInputInventoryV1 | BatchInputV1 | None = None
    position_inventories: tuple[BatchPositionInventoryV1, ...] = ()
    committed_references: tuple[RunReferenceV1, ...] = ()
    joined_command_ids: tuple[RunId, ...] = ()
    pending_command_ids: tuple[RunId, ...] = ()
    unresolved_admission_ordinals: tuple[Ordinal, ...] = ()
    final_manifest: BatchManifestV1 | CommandManifestV1 | None = None
    unknown_pending_names: tuple[str, ...] = ()
    failure: Literal["invalid_inventory", "publication_io_error", "publication_integrity_failure", "publication_limit_exceeded"] | None = None


class _OrdinalAdmissionV1(_LibraryModel):
    kind: Literal["host-ordinal-admission-v1"] = "host-ordinal-admission-v1"
    run_id: RunId
    ordinal: Ordinal
    inventory: BatchPositionInventoryV1 | CommandInputInventoryV1
    input_hash: Hash
    window: PublicationWindowV1
    admission_status: Literal["unresolved"] = "unresolved"
    as_of: Timestamp

    @model_validator(mode="after")
    def original_ordinal(self):
        if isinstance(self.inventory, BatchPositionInventoryV1) and self.inventory.ordinal != self.ordinal:
            raise ValueError("Admission ordinal mismatch")
        if isinstance(self.inventory, CommandInputInventoryV1) and self.ordinal != 0:
            raise ValueError("Standalone ordinal must be zero")
        return self


class _ResultPublicationV1(_LibraryModel):
    kind: Literal["host-result-publication-v1"] = "host-result-publication-v1"
    run_id: RunId
    ordinal: Ordinal
    result: CaseResult
    result_hash: Hash

    @model_validator(mode="after")
    def actual_hash(self):
        from .identity import fingerprint
        if self.result_hash != fingerprint(self.result.model_dump(mode="json")):
            raise ValueError("Actual scoped result hash required")
        return self


def _unique_references(references):
    if len({ref.name for ref in references}) != len(references):
        raise ValueError("Duplicate file references")


def _pending_command(command):
    return command is not None and (command.outcome == "started_pending" or
        command.queued_at is not None and command.finished_at is None and command.inventory_status == "partial")


def _batch_joins(count, positions, pending, unresolved, inventories=None):
    if len(positions) != count or tuple(p.inventory.ordinal for p in positions) != tuple(range(count)):
        raise ValueError("All original ordered positions required")
    if inventories is not None and tuple(p.inventory for p in positions) != inventories:
        raise ValueError("Original inventories must agree")
    ids = tuple(p.command.command_id for p in positions if p.command is not None)
    if len(set(ids)) != len(ids):
        raise ValueError("Returned command IDs must be unique")
    if pending != tuple(p.command.command_id for p in positions if _pending_command(p.command)):
        raise ValueError("Pending IDs must match factual positions")
    if unresolved != tuple(p.inventory.ordinal for p in positions if p.admission_status == "unresolved"):
        raise ValueError("Unresolved ordinals must match admissions")


def _command_run_join(command, release_id, mode, clock_mode, window):
    if (command.release_id, command.mode, command.clock_mode) != (release_id, mode, clock_mode):
        raise ValueError("Returned host configuration mismatch")
    if command.execution is not None and command.execution != window.execution:
        raise ValueError("Returned execution changed original anchors")


def _standalone_joins(value):
    command, summary = value.command, value.input
    if value.unresolved_admission and command is not None:
        raise ValueError("Returned command has a known join")
    pending = (command.command_id,) if _pending_command(command) else ()
    if value.pending_command_ids != pending:
        raise ValueError("Pending must match actual command")
    if command is not None and summary is not None:
        if ((command.release_id != summary.release_id and command.outcome != "denied")
                or command.command_tag is not None and command.command_tag != summary.command_tag):
            raise ValueError("Returned command input mismatch")
        if command.result is not None and command.result.case_id != summary.supplied_case_id:
            raise ValueError("Returned result identity mismatch")
    if value.export_outcome != "not_attempted" and (command is None or command.result is None):
        raise ValueError("Only actual returned results can be exported")
    if value.export is not None and value.export.actual_receipt.supplied_case_id != summary.supplied_case_id:
        raise ValueError("Actual export identity mismatch")
