"""Serial library composition over the existing public creator-owned dispatcher."""
from datetime import timedelta
from hashlib import sha256
import json
import math
from pathlib import Path
import threading
from uuid import uuid4

from .batch_files import PublicationFailure, RunPublisher, _remaining
from .contracts import CanonicalRequest, CaseResult
from .execution import ExecutionContext
from .exporter import ExportFailure, export_case
from .host import HostDispatcher
from .host_contracts import (BatchInputV1, BatchManifestV1, BatchPositionInventoryV1, BatchPositionReceiptV1,
    BatchRunReceiptV1, CommandInputInventoryV1, CommandManifestV1, CommandReceiptV1, CommandRunReceiptV1,
    EXPORT_FAILURES, ExecutionWindowV1, InterfaceLimitsV1, PublicationWindowV1, RunCommandV1,
    _OrdinalAdmissionV1, _command_run_join, _pending_command, parse_command)
from .identity import fingerprint


def _config(dispatcher, execution, deadline, reserve, limits, clock, output_root, cancellation=None):
    if (type(dispatcher) is not HostDispatcher or type(execution) is not ExecutionContext
            or type(limits) is not InterfaceLimitsV1 or clock is not dispatcher.clock
            or cancellation is not None and type(cancellation) is not threading.Event):
        raise ValueError("Exact trusted library configuration required")
    if not isinstance(output_root, (str, Path)):
        raise ValueError("Explicit trusted output path required")
    path = Path(output_root)
    if not path.is_absolute() or ".." in path.parts or len(path.parts) > 64 or len(str(path)) > 1024:
        raise ValueError("Explicit bounded absolute output path required")
    try:
        window = PublicationWindowV1(execution=ExecutionWindowV1.from_context(execution), deadline=deadline,
            reserve_seconds=reserve, monotonic_deadline=execution.monotonic_deadline + reserve)
        _intake_boundary(window, clock)
        return window
    except Exception:
        raise ValueError("Invalid trusted library timing") from None


class _IntakeTimingFailure(ValueError):
    pass


def _intake_boundary(window, clock):
    try:
        if _remaining(window, clock) <= 0:
            raise ValueError
    except Exception:
        raise _IntakeTimingFailure("Unavailable trusted intake window") from None


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError
        result[key] = value
    return result


def _admit(inputs, limits, window, clock):
    _intake_boundary(window, clock)
    encoding = "canonical_json_array_v1"
    raw = None
    if type(inputs) is bytes:
        if len(inputs) > limits.max_input_bytes:
            raise ValueError
        raw = inputs
        _intake_boundary(window, clock)
        inputs = json.loads(inputs.decode("utf-8"), object_pairs_hook=_pairs,
                            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        encoding = "exact_json_document_v1"
    if type(inputs) not in (list, tuple) or len(inputs) > limits.max_positions:
        raise ValueError
    rows = []
    for value in inputs:
        _intake_boundary(window, clock)
        rows.append(value.model_dump(mode="json") if type(value) is CanonicalRequest else value)
    stack, ancestors, nodes, size = [(rows, 0, False)], set(), 0, 0
    while stack:
        value, depth, leaving = stack.pop()
        if leaving:
            ancestors.remove(id(value))
            continue
        nodes += 1
        if depth > limits.max_depth or nodes > limits.max_input_bytes or size > limits.max_input_bytes:
            raise ValueError
        if type(value) in (list, dict):
            if id(value) in ancestors:
                raise ValueError
            ancestors.add(id(value))
            stack.append((value, depth, True))
            if type(value) is dict:
                for key, child in value.items():
                    if type(key) is not str:
                        raise ValueError
                    size += len(key.encode("utf-8"))
                    stack.append((child, depth + 1, False))
            else:
                stack.extend((child, depth + 1, False) for child in value)
        elif type(value) is str:
            size += len(value.encode("utf-8"))
        elif type(value) in (int, bool) or value is None:
            size += 1
        elif type(value) is float and math.isfinite(value):
            size += 1
        else:
            raise ValueError
    _intake_boundary(window, clock)
    canonical = json.dumps(rows, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    if len(canonical) > limits.max_input_bytes:
        raise ValueError
    observed = raw if raw is not None else canonical
    _intake_boundary(window, clock)
    detached = json.loads(canonical)
    summary = BatchInputV1(encoding=encoding, input_hash=sha256(observed).hexdigest(), input_bytes=len(observed),
                           position_count=len(detached))
    inventories = []
    for ordinal, row in enumerate(detached):
        shape = "non_object" if type(row) is not dict else "missing" if "case_id" not in row else (
            "string" if type(row["case_id"]) is str else "non_string")
        inventories.append(BatchPositionInventoryV1(ordinal=ordinal, supplied_id_shape=shape,
            supplied_case_id=row["case_id"] if shape == "string" else None))
    _intake_boundary(window, clock)
    return tuple(detached), summary, tuple(inventories)


class _Measurements:
    def __init__(self, clock, window):
        self.clock, self.window = clock, window
        self.started_at = clock.now()
        self.start = clock.monotonic()
        self.publication = 0.0
        self.basis = "unavailable"

    def io(self, operation):
        start = self.clock.monotonic()
        try:
            return operation()
        finally:
            elapsed = self.clock.monotonic() - start
            if math.isfinite(elapsed) and elapsed >= 0:
                self.publication += elapsed

    def finish(self):
        now, mono = self.clock.now(), self.clock.monotonic()
        if now < self.started_at or not math.isfinite(mono) or mono < self.start:
            raise ValueError("Invalid final timing observation")
        return dict(started_at=self.started_at, finished_at=now, elapsed_seconds=mono - self.start,
                    publication_seconds=self.publication,
                    overrun_seconds=max(0.0, mono - self.window.monotonic_deadline,
                                        (now - self.window.deadline).total_seconds()),
                    command_elapsed_basis=self.basis)


def _check_publication(window, clock):
    if _remaining(window, clock) <= 0:
        raise PublicationFailure("deadline_exceeded")


def _consume(receipt, command, dispatcher, window):
    if type(receipt) is not CommandReceiptV1:
        raise ValueError
    fields = {key: getattr(receipt, key) for key in CommandReceiptV1.model_fields}
    if receipt.result is not None:
        fields["result"] = CaseResult.model_validate({key: getattr(receipt.result, key) for key in CaseResult.model_fields})
    actual = CommandReceiptV1.model_validate(fields)
    _command_run_join(actual, dispatcher.release.release_id, dispatcher.release.mode, dispatcher.clock.mode, window)
    unparsed = actual.command_tag is None and actual.payload_hash is None and actual.result is None and actual.inventory_status == "not_admitted"
    if not unparsed and (actual.command_tag != command.tag or actual.payload_hash != fingerprint(command.model_dump(mode="json"))):
        raise ValueError
    if actual.result is not None and actual.result.case_id != _case_id(command):
        raise _ResultScopeMismatch
    return actual


class _ResultScopeMismatch(ValueError):
    pass


def _case_id(command):
    if command.tag == "run":
        return command.request.case_id
    if command.tag == "reply":
        return command.reply.binding.case_id
    return getattr(command, "case_id", None)


def _export(publisher, result, root, measurement):
    publisher._boundary()
    try:
        actual = measurement.io(lambda: export_case(result, Path(root) / "ANSWERS"))
    except ExportFailure as error:
        reason = error.reason if error.reason in EXPORT_FAILURES else "export_io_error"
        return dict(export_outcome="failed", export_failure=reason, export=None)
    except Exception:
        return dict(export_outcome="failed", export_failure="export_io_error", export=None)
    try:
        _check_publication(publisher.window, publisher.clock)
        consumed = measurement.io(lambda: publisher.verify_export(actual, result))
    except PublicationFailure as error:
        raise _UnvalidatedExport(error.reason) from None
    return dict(export_outcome=consumed.actual_receipt.status, export=consumed,
                export_failure=consumed.actual_receipt.failure)


class _UnvalidatedExport(PublicationFailure):
    @property
    def facts(self):
        # A physical exporter attempt happened, but its returned success was not
        # consumed. Retain only a library failure, never invent a failed receipt.
        failure = "output_integrity_failure" if self.reason == "publication_integrity_failure" else "export_io_error"
        return dict(export_outcome="failed", export_failure=failure, export=None)


def _joined(position, receipt):
    mapping = {"result": "result", "denied": "denied", "expired": "deadline_exceeded",
        "started_pending": "deadline_exceeded", "cancelled_before_start": "not_started",
        "queue_full": "runtime_error", "unavailable": "runtime_error", "infrastructure_error": "runtime_error"}
    return position.model_copy(update=dict(command=receipt, admission_status="joined",
        execution_outcome=mapping[receipt.outcome], failure=receipt.failure,
        result_hash=fingerprint(receipt.result.model_dump(mode="json")) if receipt.result is not None else None))


def _batch_snapshot(run_id, summary, inventories, positions, dispatcher, window, references, clock):
    return BatchManifestV1(run_id=run_id, input=summary, inventories=inventories, positions=tuple(positions),
        release_id=dispatcher.release.release_id, mode=dispatcher.release.mode, clock_mode=clock.mode,
        window=window, references=tuple(references), as_of=clock.now(),
        pending_command_ids=tuple(p.command.command_id for p in positions if _pending_command(p.command)),
        unresolved_admission_ordinals=tuple(p.inventory.ordinal for p in positions if p.admission_status == "unresolved"))


def run_batch(inputs, dispatcher, proof_handle, execution, *, publication_deadline,
              publication_reserve_seconds, output_root, limits, clock, cancellation=None):
    window = _config(dispatcher, execution, publication_deadline, publication_reserve_seconds, limits, clock, output_root, cancellation)
    measurement, run_id = _Measurements(clock, window), uuid4().hex
    labels = dict(release_id=dispatcher.release.release_id, mode=dispatcher.release.mode, clock_mode=clock.mode)
    try:
        rows, summary, inventories = _admit(inputs, limits, window, clock)
    except _IntakeTimingFailure:
        raise ValueError("Unavailable trusted intake window") from None
    except (ValueError, TypeError, RecursionError, OverflowError):
        _intake_boundary(window, clock)
        observed = sha256(inputs).hexdigest() if type(inputs) is bytes and len(inputs) <= limits.max_input_bytes else None
        return BatchRunReceiptV1(run_id=run_id, input_outcome="invalid_document", input=None,
            position_count=None, window=window, outcome="invalid_document", observed_input_hash=observed,
            **labels, **measurement.finish())
    positions = [BatchPositionReceiptV1(inventory=inventory) for inventory in inventories]
    publisher, references, final, status, outcome = None, [], None, "partial", "completed"
    fenced = None
    try:
        publisher = measurement.io(lambda: RunPublisher(output_root, window=window, clock=clock, limits=limits))
        initial = _batch_snapshot(run_id, summary, inventories, positions, dispatcher, window, (), clock)
        references.append(measurement.io(lambda: publisher.publish_input(initial)))
        for ordinal, row in enumerate(rows):
            position = positions[ordinal]
            if fenced is not None:
                positions[ordinal] = position.model_copy(update={"execution_outcome": fenced,
                    "failure": "deadline_exceeded" if fenced == "deadline_exceeded" else None})
                continue
            if cancellation is not None and cancellation.is_set():
                fenced = "not_started"
                continue
            if execution.remaining_seconds(clock) <= 0:
                fenced, outcome = "deadline_exceeded", "deadline_exceeded"
                positions[ordinal] = position.model_copy(update={"execution_outcome": fenced, "failure": "deadline_exceeded"})
                continue
            try:
                request = CanonicalRequest.model_validate_json(json.dumps(row, ensure_ascii=False, allow_nan=False))
                command = RunCommandV1(release_id=dispatcher.release.release_id, request=request)
            except (ValueError, TypeError, RecursionError, OverflowError):
                position = position.model_copy(update={"execution_outcome": "invalid_request", "failure": "invalid_request"})
            else:
                admission = _OrdinalAdmissionV1(run_id=run_id, ordinal=ordinal, inventory=position.inventory,
                    input_hash=summary.input_hash, window=window, as_of=clock.now())
                admission_reference = measurement.io(lambda: publisher.publish_admission(ordinal, admission))
                references.append(admission_reference)
                position = position.model_copy(update={"admission_status": "unresolved", "publication_status": "partial",
                                                       "references": (admission_reference,)})
                positions[ordinal] = position
                try:
                    submission = dispatcher.enqueue(command, proof_handle, execution)
                    if cancellation is not None and cancellation.is_set():
                        dispatcher.cancel_queued(submission)
                    receipt = _consume(dispatcher.wait(submission), command, dispatcher, window)
                except Exception as error:
                    position = position.model_copy(update={"execution_outcome": "runtime_error",
                        "failure": "result_scope_mismatch" if isinstance(error, _ResultScopeMismatch) else "admission_unresolved"})
                    outcome, fenced = "abandoned_pending", "not_started"
                else:
                    position = _joined(position, receipt)
                    if receipt.elapsed_seconds is not None:
                        measurement.basis = "retrieval_observation"
                    positions[ordinal] = position
                    if _pending_command(receipt):
                        outcome, fenced = "abandoned_pending", "not_started"
                    if receipt.result is not None:
                        reference = measurement.io(lambda: publisher.publish_result(ordinal, receipt.result))
                        references.append(reference)
                        position = position.model_copy(update={"references": (*position.references, reference)})
                        positions[ordinal] = position
                        try:
                            position = position.model_copy(update=_export(publisher, receipt.result, output_root, measurement))
                        except _UnvalidatedExport as error:
                            positions[ordinal] = position.model_copy(update=error.facts)
                            raise
            position = position.model_copy(update={"publication_status": "committed"})
            positions[ordinal] = position
            reference = measurement.io(lambda: publisher.publish_progress(ordinal, position))
            references.append(reference)
            positions[ordinal] = position.model_copy(update={"references": (*position.references, reference)})
            current = measurement.io(publisher._readback)
            if current.status == "invalid":
                raise PublicationFailure("publication_integrity_failure")
        snapshot = _batch_snapshot(run_id, summary, inventories, positions, dispatcher, window, references, clock)
        final = measurement.io(lambda: publisher.publish_final(snapshot))
        current = measurement.io(publisher._readback)
        if current.status != "committed_snapshot" or current.final_manifest != snapshot:
            raise PublicationFailure("publication_integrity_failure")
        status = "committed"
    except Exception as error:
        final = None
        outcome = "deadline_exceeded" if isinstance(error, PublicationFailure) and error.reason == "deadline_exceeded" else "publication_failed"
        for index, position in enumerate(positions):
            committed_progress = any(ref.name == f"POSITION-{index:08d}-PROGRESS.json" for ref in position.references)
            if not committed_progress and (position.publication_status != "not_attempted" or position.admission_status != "not_attempted"):
                positions[index] = position.model_copy(update={"publication_status": "partial"})
            elif outcome == "deadline_exceeded" and position.admission_status == "not_attempted":
                positions[index] = position.model_copy(update={"execution_outcome": "deadline_exceeded", "failure": "deadline_exceeded"})
    finally:
        if publisher is not None:
            publisher.close()
    snapshot = _batch_snapshot(run_id, summary, inventories, positions, dispatcher, window, references, clock)
    return BatchRunReceiptV1(run_id=run_id, input_outcome="admitted", input=summary,
        position_count=summary.position_count, positions=tuple(positions), window=window, outcome=outcome,
        publication_status=status, final_reference=final, pending_command_ids=snapshot.pending_command_ids,
        unresolved_admission_ordinals=snapshot.unresolved_admission_ordinals, **labels, **measurement.finish())


def run_command(command, dispatcher, proof_handle, execution, *, publication_deadline,
                publication_reserve_seconds, output_root, limits, clock):
    window = _config(dispatcher, execution, publication_deadline, publication_reserve_seconds, limits, clock, output_root)
    measurement, run_id = _Measurements(clock, window), uuid4().hex
    try:
        _intake_boundary(window, clock)
        admitted = parse_command(command, max_bytes=limits.max_input_bytes)
        _intake_boundary(window, clock)
        raw = command if type(command) is bytes else json.dumps(admitted.model_dump(mode="json"), sort_keys=True,
            ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
        summary = CommandInputInventoryV1(encoding="exact_json_document_v1" if type(command) is bytes else "canonical_closed_command_v1",
            input_hash=sha256(raw).hexdigest(), input_bytes=len(raw), command_tag=admitted.tag,
            release_id=admitted.release_id, supplied_case_id=_case_id(admitted))
        _intake_boundary(window, clock)
    except _IntakeTimingFailure:
        raise ValueError("Unavailable trusted intake window") from None
    except (ValueError, TypeError, RecursionError, OverflowError):
        _intake_boundary(window, clock)
        return CommandRunReceiptV1(run_id=run_id, input_outcome="invalid_command", input=None,
                                    window=window, **measurement.finish())
    publisher, references, actual, final, status, unresolved = None, [], None, None, "partial", False
    export = dict(export_outcome="not_attempted", export=None, export_failure=None)
    def snapshot():
        return CommandManifestV1(run_id=run_id, input=summary, command=actual,
            release_id=dispatcher.release.release_id, mode=dispatcher.release.mode, clock_mode=clock.mode,
            window=window, unresolved_admission=unresolved, references=tuple(references), as_of=clock.now(),
            pending_command_ids=(actual.command_id,) if _pending_command(actual) else (), **export)
    try:
        publisher = measurement.io(lambda: RunPublisher(output_root, window=window, clock=clock, limits=limits))
        references.append(measurement.io(lambda: publisher.publish_input(snapshot())))
        if execution.remaining_seconds(clock) > 0:
            admission = _OrdinalAdmissionV1(run_id=run_id, ordinal=0, inventory=summary,
                input_hash=summary.input_hash, window=window, as_of=clock.now())
            references.append(measurement.io(lambda: publisher.publish_admission(0, admission)))
            unresolved = True
            actual = _consume(dispatcher.wait(dispatcher.enqueue(admitted, proof_handle, execution)), admitted, dispatcher, window)
            unresolved = False
            if actual.elapsed_seconds is not None:
                measurement.basis = "retrieval_observation"
            if actual.result is not None:
                references.append(measurement.io(lambda: publisher.publish_result(0, actual.result)))
                try:
                    export = _export(publisher, actual.result, output_root, measurement)
                except _UnvalidatedExport as error:
                    export = error.facts
                    raise
        progress = snapshot()
        references.append(measurement.io(lambda: publisher.publish_progress(0, progress)))
        current = measurement.io(publisher._readback)
        if current.status == "invalid":
            raise PublicationFailure("publication_integrity_failure")
        final_snapshot = snapshot()
        final = measurement.io(lambda: publisher.publish_final(final_snapshot))
        current = measurement.io(publisher._readback)
        if current.status != "committed_snapshot" or current.final_manifest != final_snapshot:
            raise PublicationFailure("publication_integrity_failure")
        status = "committed"
    except Exception:
        final = None
    finally:
        if publisher is not None:
            publisher.close()
    return CommandRunReceiptV1(run_id=run_id, input_outcome="admitted", input=summary, command=actual,
        window=window, publication_status=status, final_reference=final, references=tuple(references),
        unresolved_admission=unresolved, pending_command_ids=(actual.command_id,) if _pending_command(actual) else (),
        **export, **measurement.finish())
