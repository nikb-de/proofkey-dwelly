"""Single SQLite authority for local intent recovery and shared pre-entry budgets.

No external action is performed here. A successful pre-entry commit is required
before a gateway enters transport; it is not proof of an external outcome.
"""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import codecs
from pathlib import Path
import json
import math
import sqlite3
import threading
from typing import Literal
from uuid import uuid4

from pydantic import TypeAdapter, model_validator

from .budget import BudgetExceeded, check_time, debit, initial_budget, preserve_budget, tool_timeout, validate_budget
from .contracts import (AuthorityObservation, CampaignPermit, CanonicalRequest, EffectIntent, InvocationRequest, InvocationReservation,
                        Hash, Identifier, NonnegativeFloat, NonnegativeInt, PositiveFloat, Revision, Timestamp,
                        PhaseCheckpoint, ProcessingReceipt, ReadTarget, RequestBinding, SavedResult,
                        ScopedReply, StopState, TransferIntent, VerificationResult, WaitState, WireModel)
from .identity import fingerprint, request_fingerprint
from .execution import ExecutionContext
from .retained_state import (RetainedStateClock, RetainedStateLimitsV1, RetainedStateSnapshotV1,
                             _DOMAIN, _TABLES, _INTEGER_COLUMNS, _NULLABLE, _canonical, _row_order)
from .wait_contracts import ControlReadScopeV1, RefusalAdmissionHistoryV1, WaitRecordV1
from .ownership_contracts import OperatorDecisionSubmissionV1, OwnershipEventV1, OwnershipProcessRegistryV1


class JournalFailure(RuntimeError):
    """Storage/identity failure; never permission to enter a transport."""


class _RetainedCaptureGuard:
    """One original window, private cooperative SQLite instruction accounting."""
    def __init__(self, execution, clock, limits):
        self.execution, self.clock, self.limits = execution, clock, limits
        self.last_utc, self.last_tick = execution.captured_at, execution.captured_monotonic
        self.steps, self.interrupted = 0, None

    def check(self):
        invalid = False
        try:
            now, tick = self.clock.now(), self.clock.monotonic()
            if (type(now) is not datetime or now.utcoffset() is None or type(tick) is not float
                    or not math.isfinite(tick)):
                raise ValueError()
            now = now.astimezone(timezone.utc)
        except Exception:
            invalid = True
        if invalid:
            raise JournalFailure('retained_state_invalid')
        if now < self.last_utc or tick < self.last_tick:
            raise JournalFailure('retained_state_invalid')
        self.last_utc, self.last_tick = now, tick
        if now >= self.execution.deadline or tick >= self.execution.monotonic_deadline:
            raise JournalFailure('retained_state_timeout')
        return now, tick

    def progress(self):
        self.steps += 1
        try:
            if self.steps > self.limits.max_sqlite_steps:
                raise JournalFailure('retained_state_limit')
            self.check()
        except (JournalFailure, ValueError, TypeError, OverflowError) as error:
            self.interrupted = (str(error) if isinstance(error, JournalFailure) else 'retained_state_invalid')
            return 1
        return 0


class IntentRecord(WireModel):
    intent: EffectIntent
    state: Literal["prepared", "dispatching", "verified", "rejected", "pending", "outcome_unknown", "conflict"]
    verification: VerificationResult | None = None


class TransferRecord(WireModel):
    intent: TransferIntent
    state: Literal["prepared", "pending", "accepted", "outcome_unknown", "rejected"]


class CheckpointAudit(WireModel):
    kind: Literal["checkpoint"] = "checkpoint"
    checkpoint_hash: Hash
    entry_id: Identifier | None = None
    refusal_history: RefusalAdmissionHistoryV1 | None = None
    ownership_event: OwnershipEventV1 | None = None


class CampaignUsage(WireModel):
    invocations: NonnegativeInt
    cost: NonnegativeFloat
    usage: dict[str, NonnegativeFloat]


class FrozenVersions(WireModel):
    profile_version: Revision
    process_version: Revision
    policy_version: Revision


class EntryLease(WireModel):
    """Host-only active-time reservation; a snapshot is never entry permission."""
    entry_id: Identifier
    case_id: Identifier
    generation: Identifier
    kind: Literal["effect", "provider", "read", "disclosure_read"]
    subject_id: Identifier | None = None
    reserved_seconds: PositiveFloat
    started_at: Timestamp
    deadline: Timestamp
    state: Literal["active", "settled", "overrun"] = "active"
    elapsed_seconds: NonnegativeFloat | None = None
    control_scope: ControlReadScopeV1 | None = None

    @model_validator(mode="after")
    def consistent_completion(self):
        if self.entry_id.startswith("control:") != (self.control_scope is not None):
            raise ValueError("Tagged control entry cannot decode as a legacy lease")
        if self.control_scope is not None and (self.kind != "read" or self.subject_id is not None
                or (self.case_id, self.generation) != (self.control_scope.binding.case_id, self.control_scope.binding.generation)):
            raise ValueError("Control scope requires its exact original read lease")
        if self.reserved_seconds > 10.0 or self.deadline <= self.started_at or self.deadline > self.started_at + timedelta(seconds=self.reserved_seconds):
            raise ValueError("Lease must retain its bounded entry deadline")
        if self.state == "active" and self.elapsed_seconds is not None:
            raise ValueError("Active lease cannot pretend observed completion")
        if self.state != "active" and self.elapsed_seconds is None:
            raise ValueError("Finished lease requires observed elapsed time")
        if self.state == "settled" and self.elapsed_seconds > self.reserved_seconds:
            raise ValueError("Overrun cannot refund capacity")
        if self.state == "overrun" and self.elapsed_seconds <= self.reserved_seconds:
            raise ValueError("Overrun must retain its observed violation")
        return self


def _json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate stored JSON key")
            result[key] = value
        return result
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))
    except (ValueError, TypeError) as error:
        raise JournalFailure("Stored JSON is malformed") from error


def _read(model, raw):
    try:
        return model.model_validate(_json(raw))
    except (ValueError, TypeError) as error:
        raise JournalFailure("Stored record incompatible with strict wire schema") from error


def _typed(model, value):
    if not isinstance(value, model):
        raise JournalFailure("Expected typed immutable record")
    return _read(model, value.model_dump_json())


def _usage(raw):
    return _read(CampaignUsage, raw).model_dump()


class CaseStore:
    SCHEMA_VERSION = 1

    def __init__(self, path, before_commit=None, *, ownership_processes=None):
        self._db = None
        self._owner_thread = threading.get_ident()
        self._execution = None
        self._before_commit = before_commit
        self._ownership_processes = (None if ownership_processes is None else
            _typed(OwnershipProcessRegistryV1, ownership_processes))
        try:
            schema = Path(__file__).with_name("schema.sql").read_text()
            reference = sqlite3.connect(":memory:")
            try:
                reference.executescript(schema)
                self._expected_schema = reference.execute("SELECT type,name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name").fetchall()
            finally:
                reference.close()
            self._db = sqlite3.connect(str(path), isolation_level=None, timeout=10)
            self._db.row_factory = sqlite3.Row
            self._db.execute("PRAGMA foreign_keys=ON")
            self._db.execute("PRAGMA journal_mode=WAL")
            self._db.execute("PRAGMA synchronous=FULL")
            if self.settings != {"journal_mode": "wal", "synchronous": 2, "foreign_keys": 1}:
                raise JournalFailure("Required SQLite durability settings unavailable")
            tables = {row[0] for row in self._db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not tables:
                self._db.executescript("BEGIN IMMEDIATE;\n" + schema + "\nCOMMIT;")
            self._db.execute("BEGIN")
            self._validate_all()
            self._db.execute("COMMIT")
        except (sqlite3.Error, OSError, ValueError, JournalFailure) as error:
            self.close()
            raise JournalFailure("Journal cannot be opened safely") from error

    @property
    def settings(self):
        return {name: self._db.execute("PRAGMA " + name).fetchone()[0]
                for name in ("journal_mode", "synchronous", "foreign_keys")}

    def close(self):
        if self._db is not None:
            self._db.close()
            self._db = None

    def capture_retained_state(self, *, execution: ExecutionContext, clock: RetainedStateClock,
                               limits: RetainedStateLimitsV1 = RetainedStateLimitsV1()) -> RetainedStateSnapshotV1:
        """Private as-of retained image; never an activation/current-state lease."""
        from hashlib import sha256
        if (threading.get_ident() != self._owner_thread or self._db is None or self._execution is not None
                or self._db.in_transaction or type(execution) is not ExecutionContext):
            raise JournalFailure('retained_state_scope')
        guard = None
        try:
            if type(limits) is not RetainedStateLimitsV1:
                raise JournalFailure('retained_state_invalid')
            RetainedStateLimitsV1(limits.max_rows, limits.max_row_bytes, limits.max_payload_bytes,
                                  limits.max_capture_seconds, limits.max_sqlite_steps)
            ExecutionContext(execution.deadline, execution.captured_at, execution.captured_monotonic,
                             execution.monotonic_deadline)
            duration = (execution.deadline - execution.captured_at).total_seconds()
            if duration > limits.max_capture_seconds:
                raise JournalFailure('retained_state_scope')
            guard = _RetainedCaptureGuard(execution, clock, limits)
            guard.check()
            with self.execution_scope(execution, clock):
                try:
                    self._db.set_progress_handler(guard.progress, 1)
                    self._db.execute('BEGIN')
                    schema, expected_bytes = self._retained_preflight(guard, limits)
                    guard.check()
                    self._validate_all()
                    guard.check()
                    tables = []
                    for name, columns, keys in _TABLES:
                        guard.check()
                        sql = 'SELECT ' + ','.join(columns) + ' FROM ' + name
                        if keys:
                            sql += ' ORDER BY ' + ','.join(keys)
                        rows = []
                        for row in self._db.execute(sql):
                            guard.check()
                            rows.append(tuple(row))
                        if keys and any(column in _NULLABLE.get(name, ()) for column in keys):
                            def order(row):
                                guard.check()
                                return _row_order(row, columns, keys)
                            rows.sort(key=order)
                            guard.check()
                        tables.append(dict(name=name, columns=columns, rows=rows))
                    data = dict(domain=_DOMAIN, schema_version=1, schema=schema, tables=tables)
                    buffer = bytearray()
                    encoder = json.JSONEncoder(sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
                    for token in encoder.iterencode(data):
                        guard.check()
                        chunk = token.encode('utf-8')
                        if len(buffer) + len(chunk) > limits.max_payload_bytes:
                            raise JournalFailure('retained_state_limit')
                        buffer.extend(chunk)
                    payload = bytes(buffer)
                    if len(payload) != expected_bytes:
                        raise JournalFailure('retained_state_invalid')
                    finished, tick = guard.check()
                    snapshot = RetainedStateSnapshotV1(_DOMAIN, 1, sha256(_canonical(schema)).hexdigest(),
                        payload, sha256(payload).hexdigest(), tuple((table['name'], len(table['rows'])) for table in tables),
                        sum(len(table['rows']) for table in tables), execution.captured_at, finished,
                        tick - execution.captured_monotonic)
                    guard.check()
                    self._db.execute('COMMIT')
                finally:
                    # Cleanup must remain possible when the original window or VM budget is exhausted.
                    self._db.set_progress_handler(None, 0)
                    if self._db.in_transaction:
                        self._db.execute('ROLLBACK')
            finished, tick = guard.check()
            # The detached object is still private here; stamp the final sample after validation/cleanup.
            object.__setattr__(snapshot, 'finished_at', finished)
            object.__setattr__(snapshot, 'elapsed_seconds', tick - execution.captured_monotonic)
            return snapshot
        except sqlite3.Error:
            reason = guard.interrupted if guard and guard.interrupted else 'retained_state_storage'
        except JournalFailure as error:
            reason = str(error)
            if reason not in {'retained_state_scope', 'retained_state_limit', 'retained_state_timeout',
                              'retained_state_invalid', 'retained_state_storage'}:
                reason = 'retained_state_invalid'
        except Exception:
            reason = 'retained_state_invalid'
        # Raise after leaving the handler: callers cannot inspect a raw content/SQL exception chain.
        raise JournalFailure(reason)

    def _retained_preflight(self, guard, limits):
        """Bound all original scalars before legacy eager schema/model validation."""
        skeleton = dict(domain=_DOMAIN, schema_version=1, schema=[],
            tables=[dict(name=name, columns=columns, rows=[]) for name, columns, _ in _TABLES])
        payload_bytes = len(_canonical(skeleton))
        if payload_bytes > limits.max_payload_bytes:
            raise JournalFailure('retained_state_limit')

        def row_bytes(table, columns, rowid, metadata, index):
            nonlocal payload_bytes
            encoded = 2 + max(0, len(columns) - 1)
            for number, column in enumerate(columns):
                guard.check()
                kind, length = metadata[2 * number:2 * number + 2]
                expected = 'integer' if column in _INTEGER_COLUMNS else 'text'
                if kind == 'null':
                    if column not in _NULLABLE.get(table, ()):
                        raise JournalFailure('retained_state_invalid')
                    encoded += 4
                elif kind != expected or type(length) is not int or length < 0:
                    raise JournalFailure('retained_state_invalid')
                elif kind == 'integer':
                    encoded += length
                else:
                    # Raw length is a necessary lower bound, not a substitute encoded-row ceiling.
                    if encoded + length + 2 > limits.max_row_bytes or payload_bytes + encoded + length + 2 > limits.max_payload_bytes:
                        raise JournalFailure('retained_state_limit')
                    encoded += 2
                    decoder = codecs.getincrementaldecoder('utf-8')('strict')
                    for offset in range(0, length, 4096):
                        guard.check()
                        raw = self._db.execute('SELECT substr(CAST(' + column + ' AS BLOB),?,?) FROM ' + table + ' WHERE rowid=?',
                            (offset + 1, min(4096, length - offset), rowid)).fetchone()
                        if raw is None or type(raw[0]) is not bytes or len(raw[0]) != min(4096, length - offset):
                            raise JournalFailure('retained_state_invalid')
                        fragment = decoder.decode(raw[0], final=offset + 4096 >= length)
                        encoded += len(_canonical(fragment)) - 2
                        if encoded > limits.max_row_bytes or payload_bytes + encoded + int(index > 0) > limits.max_payload_bytes:
                            raise JournalFailure('retained_state_limit')
                if encoded > limits.max_row_bytes or payload_bytes + encoded + int(index > 0) > limits.max_payload_bytes:
                    raise JournalFailure('retained_state_limit')
            payload_bytes += encoded + int(index > 0)

        # First read pins the snapshot without retrieving any unchecked schema SQL or name.
        metadata_sql = "SELECT rowid," + ','.join('typeof(' + column + '),length(CAST(' + column + ' AS BLOB))'
            for column in ('type', 'name', 'sql')) + " FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name LIMIT ?"
        schema = []
        for index, metadata in enumerate(self._db.execute(metadata_sql, (len(self._expected_schema) + 1,))):
            guard.check()
            if index >= len(self._expected_schema):
                raise JournalFailure('retained_state_invalid')
            row_bytes('sqlite_master', ('type', 'name', 'sql'), metadata[0], tuple(metadata)[1:], index)
            row = self._db.execute('SELECT type,name,sql FROM sqlite_master WHERE rowid=?', (metadata[0],)).fetchone()
            if row is None or tuple(row) != self._expected_schema[index]:
                raise JournalFailure('retained_state_invalid')
            schema.append(tuple(row))
        if len(schema) != len(self._expected_schema):
            raise JournalFailure('retained_state_invalid')
        total_rows = 0
        for name, columns, keys in _TABLES:
            guard.check()
            # Bound actual live column metadata too: cached shape need not match tampered DDL text.
            actual_columns = 0
            column_sql = ('SELECT cid,length(CAST(name AS BLOB)),length(CAST(type AS BLOB)),"notnull",pk,'
                          'typeof(dflt_value),length(CAST(dflt_value AS BLOB)) FROM pragma_table_info(?) LIMIT ?')
            for index, metadata in enumerate(self._db.execute(column_sql, (name, len(columns) + 1))):
                guard.check()
                if index >= len(columns):
                    raise JournalFailure('retained_state_invalid')
                column = columns[index]
                kind = 'INTEGER' if column in _INTEGER_COLUMNS else 'TEXT'
                nullable = column in _NULLABLE.get(name, ()) or (column == 'sequence' and name in ('audit', 'admission_audit'))
                default = '0' if name == 'requests' and column == 'stop_requested' else None
                expected = (index, len(column.encode('utf-8')), len(kind), int(not nullable),
                    keys.index(column) + 1 if column in keys else 0, 'text' if default else 'null', 1 if default else None)
                if tuple(metadata) != expected:
                    raise JournalFailure('retained_state_invalid')
                actual = self._db.execute('SELECT name,type,dflt_value FROM pragma_table_info(?) WHERE cid=? LIMIT 1', (name, index)).fetchone()
                if actual is None or tuple(actual) != (column, kind, default):
                    raise JournalFailure('retained_state_invalid')
                actual_columns += 1
            if actual_columns != len(columns):
                raise JournalFailure('retained_state_invalid')
            sql = 'SELECT rowid,' + ','.join('typeof(' + column + '),length(CAST(' + column + ' AS BLOB))' for column in columns) + ' FROM ' + name
            if keys:
                sql += ' ORDER BY ' + ','.join(keys)
            sql += ' LIMIT ?'
            for index, metadata in enumerate(self._db.execute(sql, (limits.max_rows - total_rows + 1,))):
                guard.check()
                total_rows += 1
                if total_rows > limits.max_rows:
                    raise JournalFailure('retained_state_limit')
                row_bytes(name, columns, metadata[0], tuple(metadata)[1:], index)
        return schema, payload_bytes

    @contextmanager
    def execution_scope(self, execution, clock):
        """Trusted creator-thread window; no auth grant or reentrant scope."""
        if (threading.get_ident() != self._owner_thread or self._db is None
                or self._execution is not None or self._db.in_transaction or type(execution) is not ExecutionContext):
            raise JournalFailure("Execution scope unavailable")
        ExecutionContext(execution.deadline, execution.captured_at,
                         execution.captured_monotonic, execution.monotonic_deadline)
        now, cutoff = execution.window(clock)
        previous = self._db.execute("PRAGMA busy_timeout").fetchone()[0]
        self._db.execute("PRAGMA busy_timeout=" + str(min(previous, max(0, int((cutoff - now).total_seconds() * 1000)))))
        self._execution = (execution, clock, previous)
        try:
            yield
        finally:
            self._execution = None
            if self._db is not None:
                self._db.execute("PRAGMA busy_timeout=" + str(previous))

    def _entry_window(self, now, deadline=None):
        if self._execution is not None:
            execution, clock, _ = self._execution
            now, cutoff = execution.window(clock)
            if cutoff <= now:
                raise BudgetExceeded("Host execution window exhausted")
            deadline = cutoff if deadline is None else min(deadline, cutoff)
        return now, deadline

    @property
    def _ownership(self):
        from .ownership_store import OwnershipStore
        if not hasattr(self, "_ownership_helper"):
            self._ownership_helper = OwnershipStore(self)
        return self._ownership_helper

    def register_transfer_atomic(self, intent, effect, source, now):
        return self._ownership.register(intent, effect, source, now)

    def begin_registered_transfer(self, transfer_id, expected_current, now):
        return self._ownership.begin(transfer_id, expected_current, now)

    def transfer_record(self, transfer_id):
        return self._ownership.record(transfer_id)

    def human_ownership(self, binding):
        return self._ownership.human(binding)

    def apply_transfer_receipt_atomic(self, transfer_id, receipt, source_current, expected_current, now):
        return self._ownership.apply(transfer_id, receipt, source_current, expected_current, now)

    def mark_transfer_unknown_atomic(self, transfer_id, expected_current):
        return self._ownership.unknown(transfer_id, expected_current)

    def record_decision_atomic(self, submission, source, now):
        return self._ownership.decision(submission, source, now)

    def decision_record(self, binding: RequestBinding, decision_id: Identifier) -> OperatorDecisionSubmissionV1:
        """Trusted-host historical original; never current decision permission."""
        if threading.get_ident() != self._owner_thread:
            raise JournalFailure("Journal creator thread required")
        binding = _typed(RequestBinding, binding)
        try:
            decision_id = TypeAdapter(Identifier).validate_python(decision_id, strict=True)
        except (ValueError, TypeError) as error:
            raise JournalFailure("Expected strict decision identifier") from error
        self._schema()
        return self._ownership.decision_record(binding, decision_id)

    def record_disposition_atomic(self, disposition, source, now):
        return self._ownership.disposition(disposition, source, now)

    def consume_decision_atomic(self, decision_id, effect, expected_current, now):
        # Only begin_dispatch may invoke this while entering the exact effect.
        if not getattr(self, "_decision_entry_active", False) or not self._db.in_transaction:
            raise JournalFailure("Decision consumption requires the shared effect-entry transaction")
        return self._ownership.consume(decision_id, effect, expected_current, now)

    @property
    def _admission(self):
        from .admission import AdmissionLedger
        if not hasattr(self, "_admission_helper"):
            self._admission_helper = AdmissionLedger(self)
        return self._admission_helper

    def start_admission(self, attempt_id, auth, request, now, deadline):
        return self._admission.start(attempt_id, auth, request, now, deadline)

    def begin_admission_read(self, attempt_id, now):
        return self._admission.begin(attempt_id, now)

    def finish_admission_read(self, entry_id, elapsed_seconds):
        return self._admission.finish(entry_id, elapsed_seconds)

    def admission_account(self, claimed_case_id):
        return self._admission.account(claimed_case_id)

    def admission_attempt(self, attempt_id):
        return self._admission.attempt(attempt_id)

    def admission_entry(self, entry_id):
        return self._admission.entry(entry_id)

    def admit_from_attempt(self, attempt_id, binding, request, checkpoint):
        return self._admission.admit(attempt_id, binding, request, checkpoint)

    def admit_refusal_after_stopped_reschedule(self, attempt_id, binding, request, checkpoint, expected_previous_binding):
        """Restricted atomic storage admission; gateway must authenticate fresh sources."""
        return self._admission.admit_refusal(attempt_id, binding, request, checkpoint, expected_previous_binding)

    def _admit_refusal(self, binding, request, checkpoint, expected_previous_binding):
        binding, request = _typed(RequestBinding, binding), _typed(CanonicalRequest, request)
        checkpoint = _typed(PhaseCheckpoint, checkpoint)
        expected = _typed(RequestBinding, expected_previous_binding)
        current = self.checkpoint(binding.case_id)
        predecessor = self.original_request(expected.case_id, expected.generation)
        if (current.binding != expected or predecessor is None or predecessor.kind not in {"reschedule_window", "reschedule_exact"}
                or not self.generation_stop(expected).requested or not current.stop.requested
                or request.kind not in {"goods_refusal", "service_refusal"}
                or binding.generation == expected.generation or binding.request_id == expected.request_id
                or binding.supersedes_generation != expected.generation
                or (binding.case_id, binding.object_id, binding.principal_id) !=
                   (expected.case_id, expected.object_id, expected.principal_id)
                or self._db.execute("SELECT 1 FROM requests WHERE case_id=? AND generation=?", (binding.case_id, binding.generation)).fetchone()
                or checkpoint.binding != binding or checkpoint.phase != "intake" or checkpoint.next_gate != "extract_input"
                or checkpoint.stop != StopState() or checkpoint.question_id is not None or checkpoint.awaited_fields
                or checkpoint.observations or checkpoint.processing_status != "pending"
                or checkpoint.ownership_state in {"pending", "transfer_pending", "stopped"}
                or checkpoint.deadline > current.deadline):
            raise JournalFailure("Refusal requires a fresh explicit intake and exact stopped reschedule predecessor")
        self._request_identity(binding, request)
        try:
            budget = preserve_budget(checkpoint.budget, current.budget)
        except ValueError as error:
            raise JournalFailure("Refusal cannot reset shared case accounting") from error
        budget = budget.model_copy(update={"deadline": min(budget.deadline, checkpoint.deadline)})
        checkpoint = checkpoint.model_copy(update={"budget": budget})
        self.bind(binding)
        self.save_request(binding, request)
        self._db.execute("UPDATE requests SET versions_json=? WHERE case_id=? AND generation=?",
            (json.dumps(self._versions(checkpoint)), binding.case_id, binding.generation))
        history = RefusalAdmissionHistoryV1(predecessor=current,
            predecessor_input_hash=fingerprint(predecessor.model_dump(mode="json")), successor_binding=binding)
        self._write_checkpoint(checkpoint, refusal_history=history)
        self._admission.import_pending(binding.case_id)

    def _schema(self):
        if self._db is None:
            raise JournalFailure("Journal is closed")
        try:
            actual = [tuple(row) for row in self._db.execute("SELECT type,name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name")]
            if actual != self._expected_schema:
                raise JournalFailure("Incompatible journal table/constraint schema")
            rows = self._db.execute("SELECT version FROM schema_meta").fetchall()
            if len(rows) != 1 or type(rows[0][0]) is not int or rows[0][0] != self.SCHEMA_VERSION:
                raise JournalFailure("Incompatible journal schema version")
        except sqlite3.Error as error:
            raise JournalFailure("Missing journal schema") from error

    @contextmanager
    def _transaction(self):
        if threading.get_ident() != self._owner_thread:
            raise JournalFailure("Journal creator thread required")
        if self._execution is not None:
            execution, clock, previous = self._execution
            now, cutoff = execution.window(clock)
            timeout = min(previous, max(0, int((cutoff - now).total_seconds() * 1000)))
            self._db.execute("PRAGMA busy_timeout=" + str(timeout))
        if self._db is not None and self._db.in_transaction:
            # Atomic host admission composes the same production operations.
            yield
            return
        try:
            self._schema()
            self._db.execute("BEGIN IMMEDIATE")
            yield
            if self._before_commit is not None:
                self._before_commit()
            self._db.execute("COMMIT")
        except BaseException as error:
            if self._db is not None and self._db.in_transaction:
                self._db.execute("ROLLBACK")
            if isinstance(error, sqlite3.Error):
                raise JournalFailure("Journal transaction failed") from error
            raise

    def _binding(self, case_id, generation):
        self._schema()
        row = self._db.execute("SELECT * FROM requests WHERE case_id=? AND generation=?", (case_id, generation)).fetchone()
        if row is None:
            raise JournalFailure("Unknown request generation")
        value = _read(RequestBinding, row["binding_json"])
        if row["versions_json"] is not None:
            _read(FrozenVersions, row["versions_json"])
        if (value.case_id, value.generation, value.request_id, value.request_revision, value.consent_revision, value.fingerprint) != (
            row["case_id"], row["generation"], row["request_id"], row["request_revision"], row["consent_revision"], row["fingerprint"]):
            raise JournalFailure("Binding index differs from stored identity")
        return value

    def _assert_binding(self, binding):
        if self._binding(binding.case_id, binding.generation) != binding:
            raise JournalFailure("Immutable request binding conflict")

    def bind(self, binding: RequestBinding):
        binding = _typed(RequestBinding, binding)
        with self._transaction():
            row = self._db.execute("SELECT 1 FROM requests WHERE case_id=? AND generation=?", (binding.case_id, binding.generation)).fetchone()
            if row:
                self._assert_binding(binding)
                return
            old = self._db.execute("SELECT checkpoint_json FROM cases WHERE case_id=?", (binding.case_id,)).fetchone()
            if old and old[0]:
                current = self.checkpoint(binding.case_id)
                if binding.supersedes_generation != current.binding.generation:
                    raise JournalFailure("New generation requires exact supersession")
                if (binding.object_id, binding.principal_id) != (current.binding.object_id, current.binding.principal_id):
                    raise JournalFailure("Case identity cannot change")
            self._db.execute("INSERT OR IGNORE INTO cases VALUES(?,NULL,0)", (binding.case_id,))
            self._db.execute("INSERT INTO requests VALUES(?,?,?,NULL,0,?,?,?,?)", (binding.case_id, binding.generation,
                binding.model_dump_json(), binding.request_id, binding.request_revision, binding.consent_revision, binding.fingerprint))

    def find_request(self, case_id, request_id, request_revision, consent_revision, fingerprint):
        self._schema()
        row = self._db.execute("SELECT generation FROM requests WHERE case_id=? AND request_id=? AND request_revision=? AND consent_revision=? AND fingerprint=?",
                              (case_id, request_id, request_revision, consent_revision, fingerprint)).fetchone()
        return self._binding(case_id, row[0]) if row else None

    def request_bindings(self, case_id) -> tuple[RequestBinding, ...]:
        """Complete local inventory in generation order; never disclosure authority."""
        self._schema()
        rows = self._db.execute("SELECT generation FROM requests WHERE case_id=? ORDER BY generation", (case_id,)).fetchall()
        return tuple(self._binding(case_id, row[0]) for row in rows)

    def admit(self, binding: RequestBinding, request: CanonicalRequest, checkpoint: PhaseCheckpoint):
        """Atomically persist original untrusted claims, binding and checkpoint."""
        if _typed(PhaseCheckpoint, checkpoint).binding != _typed(RequestBinding, binding):
            raise JournalFailure("Admission checkpoint differs from binding")
        with self._transaction():
            self.bind(binding)
            self.save_request(binding, request)
            self.save_checkpoint(checkpoint)
            self._admission.import_pending(binding.case_id)

    @staticmethod
    def _request_identity(binding, request):
        fields = ("case_id", "object_id", "principal_id", "request_id", "request_revision", "consent_revision")
        if (any(getattr(binding, field) != getattr(request, field) for field in fields)
                or binding.fingerprint != request_fingerprint(request)):
            raise JournalFailure("Original input differs from historical business binding")

    def save_request(self, binding: RequestBinding, request: CanonicalRequest):
        binding, request = _typed(RequestBinding, binding), _typed(CanonicalRequest, request)
        self._request_identity(binding, request)
        with self._transaction():
            self._assert_binding(binding)
            old = self.original_request(binding.case_id, binding.generation)
            if old is not None:
                if old != request:
                    raise JournalFailure("Historical input/lineage snapshot is immutable")
                return
            self._db.execute("INSERT INTO original_requests VALUES(?,?,?)", (binding.case_id, binding.generation, request.model_dump_json()))

    def original_request(self, case_id, generation):
        """Host-scoped recovery getter; user claims are never authority facts."""
        binding = self._binding(case_id, generation)
        row = self._db.execute("SELECT request_json FROM original_requests WHERE case_id=? AND generation=?", (case_id, generation)).fetchone()
        if row is None:
            return None
        value = _read(CanonicalRequest, row[0])
        self._request_identity(binding, value)
        return value

    def has_case(self, case_id):
        """Storage existence only; never disclosure authority."""
        self._schema()
        return self._db.execute("SELECT 1 FROM cases WHERE case_id=?", (case_id,)).fetchone() is not None

    def checkpoint(self, case_id):
        self._schema()
        row = self._db.execute("SELECT checkpoint_json FROM cases WHERE case_id=?", (case_id,)).fetchone()
        if row is None or row[0] is None:
            raise JournalFailure("Case has no checkpoint")
        value = _read(PhaseCheckpoint, row[0])
        try:
            validate_budget(value.budget)
        except ValueError as error:
            raise JournalFailure("Stored budget incompatible with finite accounting") from error
        self._assert_binding(value.binding)
        if value.binding.case_id != case_id or value.deadline > value.budget.deadline:
            raise JournalFailure("Checkpoint scope/deadline mismatch")
        versions = self._db.execute("SELECT versions_json,stop_requested FROM requests WHERE case_id=? AND generation=?", (case_id, value.binding.generation)).fetchone()
        if _json(versions[0]) != self._versions(value) or (versions[1] and not value.stop.requested):
            raise JournalFailure("Checkpoint version/stop conflict")
        audit = self._db.execute("SELECT event_json FROM audit WHERE case_id=? ORDER BY sequence DESC LIMIT 1", (case_id,)).fetchone()
        if audit is None or _read(CheckpointAudit, audit[0]).checkpoint_hash != fingerprint(value.model_dump(mode="json")):
            raise JournalFailure("Checkpoint differs from committed accounting audit")
        audited_entry = _read(CheckpointAudit, audit[0]).entry_id
        if audited_entry is not None and self.entry(audited_entry).case_id != case_id:
            raise JournalFailure("Checkpoint audit references another case entry")
        self._ownership.check_fence(value)
        self._ownership.validate_events(case_id)
        return value

    @staticmethod
    def _versions(value):
        return {key: getattr(value, key) for key in ("profile_version", "process_version", "policy_version")}

    def _write_checkpoint(self, value, *, entry_id=None, refusal_history=None, ownership_event=None):
        self._ownership.check_fence(value)
        self._db.execute("UPDATE cases SET checkpoint_json=?,revision=revision+1 WHERE case_id=?", (value.model_dump_json(), value.binding.case_id))
        audit = CheckpointAudit(checkpoint_hash=fingerprint(value.model_dump(mode="json")), entry_id=entry_id,
            refusal_history=refusal_history, ownership_event=ownership_event)
        self._db.execute("INSERT INTO audit(case_id,event_json) VALUES(?,?)", (value.binding.case_id, audit.model_dump_json()))

    def save_checkpoint(self, checkpoint: PhaseCheckpoint):
        value = _typed(PhaseCheckpoint, checkpoint)
        with self._transaction():
            self._assert_binding(value.binding)
            row = self._db.execute("SELECT checkpoint_json FROM cases WHERE case_id=?", (value.binding.case_id,)).fetchone()
            versions = self._db.execute("SELECT versions_json,stop_requested FROM requests WHERE case_id=? AND generation=?", (value.binding.case_id, value.binding.generation)).fetchone()
            if versions[0] is not None and _json(versions[0]) != self._versions(value):
                raise JournalFailure("Frozen generation versions changed")
            data = value.model_dump()
            try:
                if row[0]:
                    current = self.checkpoint(value.binding.case_id)
                    if value.binding != current.binding and value.binding.supersedes_generation != current.binding.generation:
                        raise JournalFailure("Checkpoint cannot reactivate old generation")
                    if value.deadline > current.deadline:
                        raise JournalFailure("Absolute deadline cannot extend")
                    data["budget"] = preserve_budget(value.budget, current.budget)
                    if current.stop.requested:
                        data["stop"] = current.stop
                else:
                    initial_budget(value.budget)
                if value.deadline > value.budget.deadline:
                    raise JournalFailure("Checkpoint deadline exceeds case budget")
            except ValueError as error:
                raise JournalFailure("Invalid checkpoint accounting") from error
            if versions[1]:
                data["stop"] = StopState(requested=True)
            budget_data = data["budget"].model_dump() if isinstance(data["budget"], WireModel) else data["budget"]
            budget_data["deadline"] = min(budget_data["deadline"], value.deadline)
            data["budget"] = budget_data
            value = PhaseCheckpoint.model_validate(data)
            self._db.execute("UPDATE requests SET versions_json=?,stop_requested=? WHERE case_id=? AND generation=?",
                (json.dumps(self._versions(value)), int(value.stop.requested), value.binding.case_id, value.binding.generation))
            self._write_checkpoint(value)

    def set_stop(self, case_id, generation):
        with self._transaction():
            self._binding(case_id, generation)
            value = self.checkpoint(case_id)
            self._db.execute("UPDATE requests SET stop_requested=1 WHERE case_id=? AND generation=?", (case_id, generation))
            if value.binding.generation == generation:
                data = value.model_dump()
                data["stop"] = value.stop if value.stop.requested else StopState(requested=True)
                value = PhaseCheckpoint.model_validate(data)
                self._write_checkpoint(value)
            for row in self._db.execute("SELECT question_id FROM waits WHERE case_id=? AND generation=?", (case_id, generation)).fetchall():
                record = self._wait_value(row[0])
                if isinstance(record, WaitRecordV1) and record.lifecycle == "pending":
                    stopped = record.model_copy(update={"lifecycle": "stopped", "successor_hash": fingerprint(value.model_dump(mode="json"))})
                    self._db.execute("UPDATE waits SET wait_json=? WHERE question_id=?", (stopped.model_dump_json(), row[0]))

    def generation_stop(self, binding: RequestBinding):
        """Original generation stop bookkeeping, never a caller permission grant."""
        binding = _typed(RequestBinding, binding)
        self._assert_binding(binding)
        stopped = bool(self._db.execute("SELECT stop_requested FROM requests WHERE case_id=? AND generation=?",
            (binding.case_id, binding.generation)).fetchone()[0])
        current = self.checkpoint(binding.case_id)
        if current.binding == binding:
            return current.stop
        for row in self._db.execute("SELECT event_json FROM audit WHERE case_id=? ORDER BY sequence DESC", (binding.case_id,)).fetchall():
            history = _read(CheckpointAudit, row[0]).refusal_history
            if history is not None and history.predecessor.binding == binding:
                self._validate_refusal_history(history)
                return history.predecessor.stop
        return StopState(requested=stopped)

    def _validate_refusal_history(self, history):
        old = history.predecessor.binding
        self._assert_binding(old)
        self._assert_binding(history.successor_binding)
        original = self.original_request(old.case_id, old.generation)
        successor = self.original_request(old.case_id, history.successor_binding.generation)
        row = self._db.execute("SELECT versions_json,stop_requested FROM requests WHERE case_id=? AND generation=?",
            (old.case_id, old.generation)).fetchone()
        if (original is None or original.kind not in {"reschedule_window", "reschedule_exact"}
                or successor is None or successor.kind not in {"goods_refusal", "service_refusal"}
                or history.predecessor_input_hash != fingerprint(original.model_dump(mode="json"))
                or not row[1] or _json(row[0]) != self._versions(history.predecessor)):
            raise JournalFailure("Refusal history differs from exact immutable predecessor/stop")
        if not self._audited_checkpoint_hash(old.case_id, fingerprint(history.predecessor.model_dump(mode="json"))):
            raise JournalFailure("Refusal predecessor checkpoint has no original audit")

    def _audited_checkpoint_hash(self, case_id, checkpoint_hash):
        return any(_read(CheckpointAudit, row[0]).checkpoint_hash == checkpoint_hash
            for row in self._db.execute("SELECT event_json FROM audit WHERE case_id=?", (case_id,)).fetchall())

    def _intent(self, action_id):
        self._schema()
        row = self._db.execute("SELECT * FROM intents WHERE action_id=?", (action_id,)).fetchone()
        if row is None:
            raise JournalFailure("Unknown prepared action")
        intent = _read(EffectIntent, row["intent_json"])
        self._assert_binding(intent.binding)
        versions = self._db.execute("SELECT versions_json FROM requests WHERE case_id=? AND generation=?", (intent.binding.case_id, intent.binding.generation)).fetchone()[0]
        if versions is None or _json(versions) != self._versions(intent):
            raise JournalFailure("Intent differs from original frozen versions")
        if (intent.action_id, intent.binding.case_id, intent.binding.generation, intent.argument_fingerprint) != (
            row["action_id"], row["case_id"], row["generation"], row["fingerprint"]):
            raise JournalFailure("Intent indexed identity mismatch")
        verification = _read(VerificationResult, row["verification_json"]) if row["verification_json"] else None
        record = IntentRecord(intent=intent, state=row["dispatch_state"], verification=verification)
        if verification is not None:
            self._verification_identity(intent, verification)
        if record.state in {"verified", "rejected", "pending", "outcome_unknown", "conflict"} and (verification is None or verification.status != record.state):
            raise JournalFailure("Intent state/verification mismatch")
        if record.state in {"prepared", "dispatching"} and verification is not None:
            raise JournalFailure("Unverified intent state carries incompatible verification")
        return record

    def intents(self, case_id):
        self._schema()
        return tuple(self._intent(row[0]) for row in self._db.execute("SELECT action_id FROM intents WHERE case_id=? ORDER BY rowid", (case_id,)).fetchall())

    def intent(self, action_id):
        """Trusted-host exact original lookup; never a public existence endpoint."""
        return self._intent(action_id)

    def prepare(self, intent: EffectIntent):
        intent = _typed(EffectIntent, intent)
        with self._transaction():
            self._assert_binding(intent.binding)
            checkpoint = self.checkpoint(intent.binding.case_id)
            if intent.binding != checkpoint.binding or self._versions(intent) != self._versions(checkpoint) or intent.deadline > checkpoint.deadline:
                raise JournalFailure("Intent differs from current frozen execution scope")
            if self._db.execute("SELECT 1 FROM intents WHERE action_id=?", (intent.action_id,)).fetchone():
                if self._intent(intent.action_id).intent != intent:
                    raise JournalFailure("Prepared immutable intent conflict")
                return
            self._db.execute("INSERT INTO intents VALUES(?,?,?,?,?,'prepared',NULL)", (intent.action_id, intent.binding.case_id,
                intent.binding.generation, intent.argument_fingerprint, intent.model_dump_json()))

    def begin_dispatch(self, intent: EffectIntent, now, is_resend=False):
        intent = _typed(EffectIntent, intent)
        if type(is_resend) is not bool:
            raise JournalFailure("Resend mode must be strict boolean")
        with self._transaction():
            now, _ = self._entry_window(now)
            self._admission.require_imported(intent.binding.case_id)
            record = self._intent(intent.action_id)
            if record.intent != intent:
                raise JournalFailure("Dispatch intent substitution")
            if intent.operation == "transfer_owner" and intent.arguments.get("kind") == "ownership_transfer_arguments_v1":
                raise JournalFailure("Registered ownership transfer requires its narrow original entry")
            value = self.checkpoint(intent.binding.case_id)
            if self.original_request(intent.binding.case_id, intent.binding.generation) is None:
                raise JournalFailure("Original input must be durable before external entry")
            if value.binding != intent.binding or value.stop.requested or value.ownership_state in {"pending", "transfer_pending", "stopped"}:
                raise JournalFailure("Current stop/generation/ownership fences dispatch")
            if ((intent.ownership_epoch is not None and intent.ownership_epoch != value.ownership_epoch)
                    or (intent.ownership_state_revision is not None and intent.ownership_state_revision != value.ownership_state_revision)):
                raise JournalFailure("Prepared ownership decision is stale")
            if now >= intent.deadline:
                raise BudgetExceeded("Intent deadline expired")
            if intent.decision_id is not None:
                self._decision_entry_active = True
                try:
                    self.consume_decision_atomic(intent.decision_id, intent, value, now)
                finally:
                    self._decision_entry_active = False
            return self._enter_effect(record, value, now, is_resend)

    def _enter_effect(self, record, value, now, is_resend=False):
        """Shared debt/lease accounting, called only inside an entry transaction."""
        intent = record.intent
        now, _ = self._entry_window(now)
        budget = value.budget
        if is_resend:
            if record.state not in {"dispatching", "pending", "outcome_unknown", "rejected"}:
                raise JournalFailure("Resend requires eligible unresolved/rejected original and fresh gateway contract proof")
            budget = debit(budget, "retries:" + intent.action_id, 1, now)
        else:
            if record.state != "prepared":
                raise JournalFailure("Entry already consumed; reconcile original action")
            budget = debit(budget, "effects", 1, now, handoff=intent.operation == "enqueue_handoff")
            if intent.operation == "send_clarification" and not self._wait_charged_clarification(intent):
                budget = debit(budget, "clarifications", 1, now)
        budget = debit(budget, "tool_calls", 1, now)
        attempt = budget.retries.get(intent.action_id, 0) + 1
        budget, lease = self._reserve_entry(value, budget, now, "effect:" + intent.action_id + ":" + str(attempt),
            "effect", intent.action_id, scope_deadline=intent.deadline)
        self._write_checkpoint(PhaseCheckpoint.model_validate({**value.model_dump(), "budget": budget}))
        self._db.execute("UPDATE intents SET dispatch_state='dispatching',verification_json=NULL WHERE action_id=?", (intent.action_id,))
        return lease

    def _reserve_entry(self, checkpoint, budget, now, entry_id, kind, subject_id=None, *, scope_deadline=None, scope_binding=None, control_scope=None):
        deadline = min(budget.deadline, checkpoint.deadline)
        if scope_deadline is not None:
            deadline = min(deadline, scope_deadline)
        now, deadline = self._entry_window(now, deadline)
        seconds = min(tool_timeout(budget, now), (deadline - now).total_seconds())
        if seconds <= 0:
            raise BudgetExceeded("Original entry scope deadline exhausted")
        budget = debit(budget, "active_seconds", seconds, now)
        binding = checkpoint.binding if scope_binding is None else scope_binding
        lease = EntryLease(entry_id=entry_id, case_id=binding.case_id, generation=binding.generation,
            kind=kind, subject_id=subject_id, reserved_seconds=seconds, started_at=now,
            deadline=min(deadline, now + timedelta(seconds=seconds)), control_scope=control_scope)
        self._db.execute("INSERT INTO entries VALUES(?,?,?,?,?,?,?)", (lease.entry_id, lease.case_id,
            lease.generation, lease.kind, lease.subject_id, lease.model_dump_json(), lease.state))
        return budget, lease

    def begin_read(self, case_id, now, action_id=None):
        """Pre-debit one physical read and its active slice, including failures."""
        with self._transaction():
            now, _ = self._entry_window(now)
            self._admission.require_imported(case_id)
            value = self.checkpoint(case_id)
            if self.original_request(case_id, value.binding.generation) is None:
                raise JournalFailure("Original input must be durable before external read")
            if action_id is None:
                if value.stop.requested:
                    raise JournalFailure("Stopped recovery requires original intent scope")
                budget = debit(value.budget, "tool_calls", 1, now)
            else:
                if self._intent(action_id).intent.binding.case_id != case_id:
                    raise JournalFailure("Read action belongs to another case")
                budget = debit(value.budget, "reconciliation_reads:" + action_id, 1, now)
            scope_deadline = None if action_id is None else self._intent(action_id).intent.deadline
            budget, lease = self._reserve_entry(value, budget, now, "read:" + uuid4().hex, "read", action_id,
                                              scope_deadline=scope_deadline)
            self._write_checkpoint(PhaseCheckpoint.model_validate({**value.model_dump(), "budget": budget}))
            return lease

    def begin_disclosure_read(self, binding: RequestBinding, now):
        """Host-scoped saved-result disclosure entry; current ACL/purpose is external.

        Historical binding/input/result scope is retained, while the current
        shared case ledger pays for the read. This is not business recovery,
        new authority intake, generation admission or a permission grant.
        """
        binding = _typed(RequestBinding, binding)
        with self._transaction():
            now, _ = self._entry_window(now)
            self._admission.require_imported(binding.case_id)
            self._assert_binding(binding)
            if self.original_request(binding.case_id, binding.generation) is None:
                raise JournalFailure("Disclosure requires durable original historical input")
            result = self.saved_result(binding.case_id, binding.generation)
            if result is None:
                raise JournalFailure("Disclosure requires the exact saved historical result")
            current = self.checkpoint(binding.case_id)
            budget = debit(current.budget, "tool_calls", 1, now)
            result_hash = fingerprint(result.model_dump(mode="json"))
            budget, lease = self._reserve_entry(current, budget, now, "disclosure:" + uuid4().hex,
                "disclosure_read", result_hash, scope_binding=binding)
            self._write_checkpoint(PhaseCheckpoint.model_validate({**current.model_dump(), "budget": budget}), entry_id=lease.entry_id)
            return lease

    def begin_control_read(self, binding: RequestBinding, target, purpose, now):
        """Pre-charge narrow physical identity/control reads, including stopped originals."""
        binding, target = _typed(RequestBinding, binding), _typed(ReadTarget, target)
        with self._transaction():
            now, _ = self._entry_window(now)
            self._admission.require_imported(binding.case_id)
            self._assert_binding(binding)
            original = self.original_request(binding.case_id, binding.generation)
            if original is None:
                raise JournalFailure("Control read requires exact durable original input")
            try:
                scope = ControlReadScopeV1(binding=binding, original_input_hash=fingerprint(original.model_dump(mode="json")),
                    target=target, purpose=purpose)
            except (ValueError, TypeError) as error:
                raise JournalFailure("Invalid control purpose/target") from error
            current = self.checkpoint(binding.case_id)
            budget = debit(current.budget, "tool_calls", 1, now)
            budget, lease = self._reserve_entry(current, budget, now,
                "control:" + fingerprint(scope.model_dump(mode="json")) + ":" + uuid4().hex, "read",
                scope_binding=binding, control_scope=scope)
            self._write_checkpoint(current.model_copy(update={"budget": budget}), entry_id=lease.entry_id)
            return lease

    def entry(self, entry_id):
        self._schema()
        row = self._db.execute("SELECT * FROM entries WHERE entry_id=?", (entry_id,)).fetchone()
        if row is None:
            raise JournalFailure("Unknown entry reservation")
        lease = _read(EntryLease, row["lease_json"])
        self._binding(lease.case_id, lease.generation)
        if (lease.entry_id, lease.case_id, lease.generation, lease.kind, lease.subject_id, lease.state) != (
            row["entry_id"], row["case_id"], row["generation"], row["kind"], row["subject_id"], row["state"]):
            raise JournalFailure("Entry reservation index/scope conflict")
        if lease.kind == "disclosure_read":
            result = self.saved_result(lease.case_id, lease.generation)
            if (self.original_request(lease.case_id, lease.generation) is None or result is None
                    or lease.subject_id != fingerprint(result.model_dump(mode="json"))):
                raise JournalFailure("Disclosure lease differs from immutable historical scope")
        if lease.control_scope is not None:
            scope = lease.control_scope
            self._assert_binding(scope.binding)
            original = self.original_request(lease.case_id, lease.generation)
            if (original is None or scope.original_input_hash != fingerprint(original.model_dump(mode="json"))
                    or not lease.entry_id.startswith("control:" + fingerprint(scope.model_dump(mode="json")) + ":")):
                raise JournalFailure("Control lease differs from immutable original input")
        return lease

    def finish_entry(self, entry_id, elapsed_seconds):
        """Trusted host settles observed completed calls once; never exceptions/unknowns.

        Interrupted/timeout/nonterminal calls retain the full slice. An observed
        timeout violation durably forfeits the remaining active allowance.
        """
        if type(elapsed_seconds) not in (int, float) or not math.isfinite(elapsed_seconds) or elapsed_seconds < 0:
            raise JournalFailure("Completion requires finite nonnegative elapsed time")
        overrun = False
        with self._transaction():
            lease = self.entry(entry_id)
            if lease.state != "active":
                raise JournalFailure("Entry completion already consumed")
            if self._admission.exhausted(lease.case_id):
                raise BudgetExceeded("Observed admission overrun permanently exhausted case active capacity")
            if self._db.execute("SELECT 1 FROM entries WHERE case_id=? AND state='overrun'", (lease.case_id,)).fetchone():
                raise BudgetExceeded("Observed overrun permanently exhausted case active capacity")
            checkpoint = self.checkpoint(lease.case_id)
            data = checkpoint.model_dump()
            if elapsed_seconds > lease.reserved_seconds:
                overrun = True
                data["budget"]["active_seconds"] = checkpoint.budget.max_active_seconds
                state = "overrun"
            else:
                data["budget"]["active_seconds"] -= lease.reserved_seconds - elapsed_seconds
                state = "settled"
                if data["budget"]["active_seconds"] < 0:
                    raise JournalFailure("Completion would roll back unrelated accounting")
            finished = EntryLease.model_validate({**lease.model_dump(), "state": state, "elapsed_seconds": elapsed_seconds})
            self._db.execute("UPDATE entries SET lease_json=?,state=? WHERE entry_id=?", (finished.model_dump_json(), state, entry_id))
            self._write_checkpoint(PhaseCheckpoint.model_validate(data))
        if overrun:
            raise BudgetExceeded("Observed external entry exceeded reserved timeout; capacity exhausted")

    @staticmethod
    def _verification_identity(intent, verification):
        pairs = ((verification.object_id, intent.binding.object_id), (verification.action_id, intent.action_id),
                 (verification.fingerprint, intent.argument_fingerprint), (verification.postcondition, intent.postcondition))
        if any(actual is not None and actual != expected for actual, expected in pairs):
            raise JournalFailure("Verification differs from immutable effect identity/postcondition")

    def record_verification(self, action_id, verification: VerificationResult):
        verification = _typed(VerificationResult, verification)
        with self._transaction():
            record = self._intent(action_id)
            if record.state == "prepared":
                raise JournalFailure("Unentered intent cannot have provider verification")
            self._verification_identity(record.intent, verification)
            if record.state == "verified" and record.verification != verification:
                raise JournalFailure("Verified result is immutable")
            self._db.execute("UPDATE intents SET dispatch_state=?,verification_json=? WHERE action_id=?",
                             (verification.status, verification.model_dump_json(), action_id))

    def consume(self, case_id, kind, amount, now):
        with self._transaction():
            value = self.checkpoint(case_id)
            if kind.startswith(("reconciliation_reads:", "retries:")):
                record = self._intent(kind.split(":", 1)[1])
                if record.intent.binding.case_id != case_id:
                    raise JournalFailure("Accounting action belongs to another case")
            try:
                budget = debit(value.budget, kind, amount, now)
            except ValueError as error:
                raise JournalFailure("Invalid debit") from error
            self._write_checkpoint(PhaseCheckpoint.model_validate({**value.model_dump(), "budget": budget}))

    def register_campaign(self, permit: CampaignPermit):
        """Trusted host registration only; request bodies cannot call this grant API."""
        permit = _typed(CampaignPermit, permit)
        data = permit.model_dump(mode="json")
        if permit.permit_hash != fingerprint({k: v for k, v in data.items() if k != "permit_hash"}):
            raise JournalFailure("Campaign permit self-hash mismatch")
        if not permit.input_hashes or len(permit.input_hashes) != len(set(permit.input_hashes)):
            raise JournalFailure("Campaign requires a distinct input allowlist")
        with self._transaction():
            row = self._db.execute("SELECT permit_json FROM campaigns WHERE permit_hash=?", (permit.permit_hash,)).fetchone()
            if row:
                if _read(CampaignPermit, row[0]) != permit:
                    raise JournalFailure("Immutable permit conflict")
                return
            self._db.execute("INSERT INTO campaigns VALUES(?,?,?, ?,0)", (permit.permit_hash, permit.campaign_id,
                permit.model_dump_json(), json.dumps({"invocations": 0, "cost": 0.0, "usage": {}})))

    def _campaign(self, permit_hash):
        self._schema()
        row = self._db.execute("SELECT * FROM campaigns WHERE permit_hash=?", (permit_hash,)).fetchone()
        if row is None:
            raise JournalFailure("Campaign not registered by trusted host")
        permit = _read(CampaignPermit, row["permit_json"])
        data = permit.model_dump(mode="json")
        if (permit.permit_hash != permit_hash or permit.campaign_id != row["campaign_id"]
                or fingerprint({k: v for k, v in data.items() if k != "permit_hash"}) != permit_hash):
            raise JournalFailure("Stored permit identity/hash conflict")
        usage = _usage(row["consumed_json"])
        if (usage["invocations"] > permit.max_invocations or usage["cost"] > permit.max_cost
                or any(key not in permit.max_usage or val > permit.max_usage[key] for key, val in usage["usage"].items())):
            raise JournalFailure("Stored campaign exceeds permit")
        reservations = [_read(InvocationReservation, row[0]) for row in self._db.execute(
            "SELECT reservation_json FROM invocations WHERE permit_hash=? ORDER BY rowid", (permit_hash,)).fetchall()]
        expected = {"invocations": len(reservations), "cost": 0.0, "usage": {}}
        for reservation in reservations:
            expected["cost"] += reservation.worst_case_cost
            for key, amount in reservation.reserved_usage.items():
                expected["usage"][key] = expected["usage"].get(key, 0.0) + amount
        if usage != expected:
            raise JournalFailure("Campaign accounting differs from committed reservation debts")
        return permit, usage

    def campaign_usage(self, permit_hash):
        return self._campaign(permit_hash)[1]

    def reserve_invocation(self, request: InvocationRequest, now):
        request = _typed(InvocationRequest, request)
        identity = request.identity
        with self._transaction():
            now, _ = self._entry_window(now)
            self._admission.require_imported(identity.case_id)
            if self._db.execute("SELECT 1 FROM invocations WHERE invocation_id=?", (request.invocation_id,)).fetchone():
                raise JournalFailure("Invocation ID already consumed; new entry needs a new ID")
            value = self.checkpoint(identity.case_id)
            if self.original_request(identity.case_id, identity.generation) is None:
                raise JournalFailure("Original input must be durable before provider entry")
            if value.binding.generation != identity.generation or value.stop.requested or value.ownership_state in {"pending", "transfer_pending", "stopped"}:
                raise JournalFailure("Current scope fences provider entry")
            permit, consumed = self._campaign(identity.permit_hash)
            if ((identity.campaign_id, identity.role, identity.provider, identity.model, identity.endpoint) !=
                    (permit.campaign_id, permit.role, permit.provider, permit.model, permit.endpoint)
                    or not identity.input_hashes or len(identity.input_hashes) != len(set(identity.input_hashes))
                    or not set(identity.input_hashes) <= set(permit.input_hashes)
                    or identity.profile_version != value.profile_version or identity.process_version != value.process_version
                    or identity.deadline > value.deadline or identity.deadline > permit.expires_at):
                raise JournalFailure("Invocation differs from exact permit/execution scope")
            check_time(value.budget, now)
            if now >= identity.deadline or now >= permit.expires_at:
                raise BudgetExceeded("Provider permit/deadline expired")
            role = value.budget.role_allowances.get(identity.role)
            if role is None:
                raise BudgetExceeded("Provider role disabled by trusted case configuration")
            for count, cap in ((role.invocations + 1, role.max_invocations), (role.cost + request.worst_case_cost, role.max_cost),
                               (consumed["invocations"] + 1, permit.max_invocations), (consumed["cost"] + request.worst_case_cost, permit.max_cost)):
                if count > cap:
                    raise BudgetExceeded("Provider invocation/cost allowance exhausted")
            usage = dict(role.usage)
            shared_usage = dict(consumed["usage"])
            for name, amount in request.requested_usage.items():
                if (name not in role.usage_allowances or name not in permit.max_usage
                        or usage.get(name, 0) + amount > role.usage_allowances[name]
                        or shared_usage.get(name, 0) + amount > permit.max_usage[name]):
                    raise BudgetExceeded("Provider usage allowance exhausted")
                usage[name] = usage.get(name, 0) + amount
                shared_usage[name] = shared_usage.get(name, 0) + amount
            budget = debit(value.budget, "tool_calls", 1, now)
            if identity.role == "planning":
                budget = debit(budget, "planner_calls", 1, now)
            data = budget.model_dump()
            data["role_allowances"][identity.role].update(invocations=role.invocations + 1, usage=usage, cost=role.cost + request.worst_case_cost)
            budget = type(budget).model_validate(data)
            budget, _ = self._reserve_entry(value, budget, now, "invocation:" + request.invocation_id, "provider",
                request.invocation_id, scope_deadline=min(identity.deadline, permit.expires_at))
            self._write_checkpoint(PhaseCheckpoint.model_validate({**value.model_dump(), "budget": budget}))
            shared = dict(invocations=consumed["invocations"] + 1, cost=consumed["cost"] + request.worst_case_cost, usage=shared_usage)
            self._db.execute("UPDATE campaigns SET consumed_json=?,revision=revision+1 WHERE permit_hash=?", (json.dumps(shared), permit.permit_hash))
            reserved = InvocationReservation(identity=identity, invocation_id=request.invocation_id,
                reserved_usage=request.requested_usage, worst_case_cost=request.worst_case_cost, status="consumed",
                case_debit=1, role_debit=1, campaign_debit=1, reserved_at=now)
            self._db.execute("INSERT INTO invocations VALUES(?,?,?,?,?,?,'consumed',NULL)", (request.invocation_id,
                identity.case_id, identity.generation, identity.role, permit.permit_hash, reserved.model_dump_json()))
            return reserved

    def _invocation(self, invocation_id):
        self._schema()
        row = self._db.execute("SELECT * FROM invocations WHERE invocation_id=?", (invocation_id,)).fetchone()
        if row is None:
            raise JournalFailure("Unknown consumed invocation")
        reservation = _read(InvocationReservation, row["reservation_json"])
        if ((reservation.invocation_id, reservation.identity.case_id, reservation.identity.generation, reservation.identity.role,
             reservation.identity.permit_hash, reservation.status) != (row["invocation_id"], row["case_id"], row["generation"], row["role"], row["permit_hash"], row["state"])):
            raise JournalFailure("Invocation indexed identity mismatch")
        self._binding(row["case_id"], row["generation"])
        permit, _ = self._campaign(row["permit_hash"])
        identity = reservation.identity
        versions = _json(self._db.execute("SELECT versions_json FROM requests WHERE case_id=? AND generation=?", (identity.case_id, identity.generation)).fetchone()[0])
        if ((identity.campaign_id, identity.role, identity.provider, identity.model, identity.endpoint) !=
                (permit.campaign_id, permit.role, permit.provider, permit.model, permit.endpoint)
                or not identity.input_hashes or not set(identity.input_hashes) <= set(permit.input_hashes)
                or identity.profile_version != versions["profile_version"] or identity.process_version != versions["process_version"]
                or (reservation.case_debit, reservation.role_debit, reservation.campaign_debit) != (1, 1, 1)):
            raise JournalFailure("Reservation differs from original permit/frozen scope/debits")
        receipt = _read(ProcessingReceipt, row["receipt_json"]) if row["receipt_json"] else None
        if receipt:
            self._receipt_identity(reservation, receipt)
            state = "failed" if receipt.status == "unavailable" else receipt.status
            if receipt.status not in {"completed", "failed", "outcome_unknown", "unavailable"} or state != reservation.status:
                raise JournalFailure("Reservation/receipt recovery state mismatch")
        elif reservation.status != "consumed":
            raise JournalFailure("Finished reservation has no processing receipt")
        return reservation, receipt

    def invocation(self, invocation_id):
        """Recovery inspection is evidence only, never a reusable entry grant."""
        return self._invocation(invocation_id)

    def processing_attempts(self, binding: RequestBinding) -> tuple[tuple[InvocationReservation, ProcessingReceipt | None], ...]:
        """Detached durable attempts in insertion order; no provider reentry."""
        if threading.get_ident() != self._owner_thread:
            raise JournalFailure("Journal creator thread required")
        binding = _typed(RequestBinding, binding)
        self._assert_binding(binding)
        if self.original_request(binding.case_id, binding.generation) is None:
            raise JournalFailure("Processing inventory requires immutable original request")
        rows = self._db.execute("SELECT invocation_id FROM invocations WHERE case_id=? AND generation=? ORDER BY rowid",
                                (binding.case_id, binding.generation)).fetchall()
        return tuple(self._invocation(row[0]) for row in rows)

    @staticmethod
    def _receipt_identity(reservation, receipt):
        identity = reservation.identity
        if ((receipt.invocation_id, receipt.role, receipt.provider, receipt.requested_model, receipt.prompt_hash,
             receipt.version, receipt.input_hashes) != (reservation.invocation_id, identity.role, identity.provider,
             identity.model, identity.prompt_hash, identity.version, identity.input_hashes)):
            raise JournalFailure("Processing receipt input/route identity mismatch")
        if any(name not in reservation.reserved_usage or amount > reservation.reserved_usage[name] for name, amount in receipt.usage.items()):
            raise JournalFailure("Receipt exceeds pre-reserved worst-case usage")

    def record_processing(self, invocation_id, receipt: ProcessingReceipt):
        receipt = _typed(ProcessingReceipt, receipt)
        with self._transaction():
            reservation, old_receipt = self._invocation(invocation_id)
            self._receipt_identity(reservation, receipt)
            if old_receipt is not None:
                if old_receipt != receipt:
                    raise JournalFailure("Processing receipt already recorded")
                return
            if receipt.status not in {"completed", "failed", "outcome_unknown", "unavailable"}:
                raise JournalFailure("Processing receipt must retain terminal/unknown attempt")
            state = "failed" if receipt.status == "unavailable" else receipt.status
            updated = InvocationReservation.model_validate({**reservation.model_dump(), "status": state})
            self._db.execute("UPDATE invocations SET reservation_json=?,state=?,receipt_json=? WHERE invocation_id=?",
                (updated.model_dump_json(), state, receipt.model_dump_json(), invocation_id))

    def save_result(self, result: SavedResult):
        result = _typed(SavedResult, result)
        with self._transaction():
            self._assert_binding(result.binding)
            existing = self.saved_result(result.case_id, result.binding.generation)
            if existing is not None:
                if existing != result:
                    raise JournalFailure("Saved generation result is immutable")
                return
            self._db.execute("INSERT INTO results VALUES(?,?,?)", (result.case_id, result.binding.generation, result.model_dump_json()))

    def saved_result(self, case_id, generation):
        self._schema()
        row = self._db.execute("SELECT result_json FROM results WHERE case_id=? AND generation=?", (case_id, generation)).fetchone()
        if row is None:
            return None
        value = _read(SavedResult, row[0])
        self._assert_binding(value.binding)
        if (value.case_id, value.binding.generation) != (case_id, generation):
            raise JournalFailure("Result scope mismatch")
        return value

    def save_wait(self, wait: WaitState):
        wait = _typed(WaitState, wait)
        with self._transaction():
            self._assert_binding(wait.binding)
            old = self.wait(wait.question_id)
            if old is not None:
                if old != wait:
                    raise JournalFailure("Immutable question conflict")
                return
            self._db.execute("INSERT INTO waits VALUES(?,?,?,?)", (wait.question_id, wait.binding.case_id,
                wait.binding.generation, wait.model_dump_json()))

    def wait(self, question_id):
        value = self._wait_value(question_id)
        return value.wait if isinstance(value, WaitRecordV1) else value

    def _wait_value(self, question_id):
        self._schema()
        row = self._db.execute("SELECT * FROM waits WHERE question_id=?", (question_id,)).fetchone()
        if row is None:
            return None
        raw = _json(row["wait_json"])
        value = _read(WaitRecordV1 if isinstance(raw, dict) and "kind" in raw else WaitState, row["wait_json"])
        wait = value.wait if isinstance(value, WaitRecordV1) else value
        self._assert_binding(wait.binding)
        if (wait.question_id, wait.binding.case_id, wait.binding.generation) != (row["question_id"], row["case_id"], row["generation"]):
            raise JournalFailure("Wait scope mismatch")
        if isinstance(value, WaitRecordV1):
            row_versions = self._db.execute("SELECT versions_json FROM requests WHERE case_id=? AND generation=?",
                (wait.binding.case_id, wait.binding.generation)).fetchone()[0]
            if _json(row_versions) != self._versions(value.origin_checkpoint):
                raise JournalFailure("Wait differs from frozen generation versions")
            if not self._audited_checkpoint_hash(wait.binding.case_id, value.origin_hash):
                raise JournalFailure("Wait original control checkpoint has no committed audit")
            if value.successor_hash is not None and not self._audited_checkpoint_hash(wait.binding.case_id, value.successor_hash):
                raise JournalFailure("Wait disposition has no committed successor audit")
            try:
                validate_budget(wait.budget)
            except ValueError as error:
                raise JournalFailure("Wait accounting is incompatible") from error
        return value

    def load_wait_record(self, question_id):
        value = self._wait_value(question_id)
        if not isinstance(value, WaitRecordV1):
            raise JournalFailure("Unknown or legacy question has no resumable scope")
        return value

    def create_wait_atomic(self, record: WaitRecordV1, now):
        """Persist bounded scope/debit before send; keep the physical origin active."""
        record = _typed(WaitRecordV1, record)
        with self._transaction():
            self._admission.require_imported(record.wait.binding.case_id)
            existing = self._wait_value(record.wait.question_id)
            if existing is not None:
                if existing != record:
                    raise JournalFailure("Immutable question conflict")
                return existing.wait
            current = self.checkpoint(record.wait.binding.case_id)
            self._assert_binding(record.wait.binding)
            if (current != record.origin_checkpoint or record.lifecycle != "pending" or now != record.created_at
                    or self.original_request(current.binding.case_id, current.binding.generation) is None):
                raise JournalFailure("Wait creation requires exact current original control checkpoint")
            if self._db.execute("SELECT 1 FROM intents WHERE action_id=?", (record.communication_action_id,)).fetchone():
                communication = self._intent(record.communication_action_id)
                if (communication.state != "prepared" or communication.intent.binding != current.binding
                        or self._versions(communication.intent) != self._versions(current)
                        or (communication.intent.operation == "send_clarification" and
                            (communication.intent.arguments.get("question_id") != record.wait.question_id
                             or communication.intent.arguments.get("recipient") != record.wait.recipient))):
                    raise JournalFailure("Wait must be persisted before its exact original communication enters")
            check_time(current.budget, now)
            for row in self._db.execute("SELECT question_id FROM waits WHERE case_id=? AND generation=?",
                    (current.binding.case_id, current.binding.generation)).fetchall():
                old = self._wait_value(row[0])
                if isinstance(old, WaitRecordV1) and (old.lifecycle == "pending" or old.communication_action_id == record.communication_action_id):
                    raise JournalFailure("Question or physical communication already scoped")
            budget = current.budget
            if record.communication_edge.operation == "send_clarification":
                budget = debit(budget, "clarifications", 1, now)
            self._db.execute("INSERT INTO waits VALUES(?,?,?,?)", (record.wait.question_id, current.binding.case_id,
                current.binding.generation, record.model_dump_json()))
            self._write_checkpoint(current.model_copy(update={"budget": budget}))
            return record.wait

    def _wait_charged_clarification(self, intent):
        current = self.checkpoint(intent.binding.case_id)
        for row in self._db.execute("SELECT question_id FROM waits WHERE case_id=? AND generation=?",
                (intent.binding.case_id, intent.binding.generation)).fetchall():
            value = self._wait_value(row[0])
            if isinstance(value, WaitRecordV1) and value.communication_action_id == intent.action_id:
                if (value.communication_edge.operation != intent.operation or value.lifecycle != "pending"
                        or value.wait.binding != intent.binding or self._versions(value.origin_checkpoint) != self._versions(intent)
                        or value.origin_checkpoint.phase != current.phase
                        or intent.arguments.get("question_id") != value.wait.question_id
                        or intent.arguments.get("recipient") != value.wait.recipient
                        or (current.ownership_state, current.ownership_state_revision, current.ownership_epoch) !=
                           (value.owner_state, value.owner_revision, value.owner_epoch)
                        or (intent.ownership_state_revision, intent.ownership_epoch) != (value.owner_revision, value.owner_epoch)):
                    raise JournalFailure("Clarification intent differs from its pre-send scope")
                return True
        return False

    def _current_wait(self, question_id, expected_current):
        expected = _typed(PhaseCheckpoint, expected_current)
        record = self.load_wait_record(question_id)
        current = self.checkpoint(record.wait.binding.case_id)
        if (current != expected or record.lifecycle != "pending" or current.binding != record.wait.binding
                or self._versions(current) != self._versions(record.origin_checkpoint)
                or current.stop.requested or self.generation_stop(current.binding).requested
                or current.question_id != question_id or current.phase != record.wait_phase
                or current.awaited_fields != record.wait.awaited_fields
                or (current.ownership_state, current.ownership_state_revision, current.ownership_epoch) !=
                   (record.owner_state, record.owner_revision, record.owner_epoch)):
            raise JournalFailure("Question is not pending in the exact current control context")
        return record, current

    def _wait_successor(self, record, current, successor, edge):
        successor = _typed(PhaseCheckpoint, successor)
        if (successor.binding != current.binding or self._versions(successor) != self._versions(current)
                or successor.phase != edge.target or successor.deadline > current.deadline
                or not any(e.origin == successor.phase and e.operation == successor.next_gate for e in record.process.edges)):
            raise JournalFailure("Successor must retain its graph-specific declared continuation")
        try:
            budget = preserve_budget(successor.budget, current.budget)
        except ValueError as error:
            raise JournalFailure("Wait successor cannot reset case budgets") from error
        data = successor.model_dump()
        data.update(budget=budget, deadline=min(current.deadline, successor.deadline), stop=current.stop,
            ownership_state=current.ownership_state, ownership_state_revision=current.ownership_state_revision,
            ownership_epoch=current.ownership_epoch, observations=[], question_id=None, awaited_fields=[])
        data["budget"] = budget.model_copy(update={"deadline": min(budget.deadline, data["deadline"])})
        return PhaseCheckpoint.model_validate(data)

    def _finish_wait(self, record, successor, lifecycle, **receipt):
        finished = record.model_copy(update={"lifecycle": lifecycle,
            "successor_hash": fingerprint(successor.model_dump(mode="json")), **receipt})
        self._db.execute("UPDATE waits SET wait_json=? WHERE question_id=?", (finished.model_dump_json(), record.wait.question_id))
        self._write_checkpoint(successor)
        return successor

    def consume_wait_reply_atomic(self, question_id, expected_current, reply, successor, now):
        """One-use storage transition; authentic source/reply authority is external."""
        reply = _typed(ScopedReply, reply)
        with self._transaction():
            record, current = self._current_wait(question_id, expected_current)
            check_time(current.budget, now)
            if (reply.question_id != question_id or reply.binding != current.binding
                    or reply.actor_id != record.wait.recipient
                    or reply.request_revision != current.binding.request_revision
                    or reply.consent_revision != current.binding.consent_revision
                    or reply.owner_state_revision != record.owner_revision
                    or set(reply.fields) != set(record.wait.awaited_fields)
                    or not record.created_at <= reply.received_at <= now < record.wait.expires_at):
                raise JournalFailure("Reply differs from pending immutable question scope")
            successor = self._wait_successor(record, current, successor, record.accept_edge)
            return self._finish_wait(record, successor, "answered",
                accepted_reply_hash=fingerprint(reply.model_dump(mode="json")), accepted_actor=reply.actor_id,
                accepted_reply=reply)

    def expire_wait_atomic(self, question_id, expected_current, successor, now):
        with self._transaction():
            record, current = self._current_wait(question_id, expected_current)
            if not hasattr(now, "utcoffset") or now.utcoffset() is None or now < record.wait.expires_at:
                raise JournalFailure("Wait requires an observed finite expiry")
            successor = self._wait_successor(record, current, successor, record.expiry_edge)
            return self._finish_wait(record, successor, "expired")

    def attach_wait_reply_sources_atomic(self, question_id, expected_consumed, observations) -> PhaseCheckpoint:
        """Attach detached host sources only to the exact one-use successor.

        Typing/integrity is not source authentication; the leased gateway owns
        that authority. No reply receipt, control field or accounting is merged.
        """
        with self._transaction():
            expected = _typed(PhaseCheckpoint, expected_consumed)
            if not isinstance(observations, (list, tuple)) or len(observations) > 64:
                raise JournalFailure("Invalid wait reply source attachment")
            sources = [_typed(AuthorityObservation, item) for item in observations]
            identities = {(item.authority, item.fact) for item in sources}
            if (len(identities) != len(sources)
                    or any(item.object_id != expected.binding.object_id for item in sources)):
                raise JournalFailure("Invalid wait reply source attachment")
            record = self.load_wait_record(question_id)
            current = self.checkpoint(record.wait.binding.case_id)
            if (record.lifecycle != "answered" or record.wait.binding != expected.binding
                    or self._versions(expected) != self._versions(record.origin_checkpoint)
                    or record.successor_hash != fingerprint(expected.model_dump(mode="json"))
                    or expected.observations or expected.question_id is not None or expected.awaited_fields
                    or expected.phase != record.accept_edge.target
                    or not any(edge.origin == expected.phase and edge.operation == expected.next_gate
                               for edge in record.process.edges)
                    or (expected.ownership_state, expected.ownership_state_revision, expected.ownership_epoch) !=
                       (record.owner_state, record.owner_revision, record.owner_epoch)
                    or expected.stop.requested or self.generation_stop(expected.binding).requested
                    or current != expected):
                raise JournalFailure("Invalid wait reply source attachment")
            attached = PhaseCheckpoint.model_validate({**current.model_dump(), "observations": sources})
            self._write_checkpoint(attached)
            return attached

    def stop_waits_atomic(self, binding, expected_current):
        binding, expected = _typed(RequestBinding, binding), _typed(PhaseCheckpoint, expected_current)
        with self._transaction():
            current = self.checkpoint(binding.case_id)
            if current != expected or current.binding != binding:
                raise JournalFailure("Stop requires exact current control checkpoint")
            self.set_stop(binding.case_id, binding.generation)
            return self.checkpoint(binding.case_id)

    def save_transfer(self, intent: TransferIntent, state="prepared"):
        intent = _typed(TransferIntent, intent)
        record = TransferRecord(intent=intent, state=state)
        with self._transaction():
            self._assert_binding(intent.binding)
            old = self.transfer(intent.transfer_id)
            if old is not None and old.intent != intent:
                raise JournalFailure("Immutable transfer conflict")
            if old is not None and old.state in {"accepted", "rejected"} and old.state != state:
                raise JournalFailure("Terminal legacy transfer cannot roll back")
            if self._ownership.is_tagged(intent.transfer_id):
                raise JournalFailure("Registered transfer cannot use legacy mutation API")
            self._db.execute("INSERT INTO transfers VALUES(?,?,?,?,?) ON CONFLICT(transfer_id) DO UPDATE SET state=excluded.state",
                (intent.transfer_id, intent.case_id, intent.binding.generation, intent.model_dump_json(), record.state))

    def transfer(self, transfer_id):
        self._schema()
        row = self._db.execute("SELECT * FROM transfers WHERE transfer_id=?", (transfer_id,)).fetchone()
        if row is None:
            return None
        raw = _json(row["transfer_json"])
        if raw.get("kind") == "transfer_record_v1":
            registered = self.transfer_record(transfer_id)
            return TransferRecord(intent=registered.intent, state=registered.lifecycle)
        if "kind" in raw:
            raise JournalFailure("Unknown stored transfer tag")
        value = _read(TransferIntent, row["transfer_json"])
        self._assert_binding(value.binding)
        if (value.transfer_id, value.case_id, value.binding.generation) != (row["transfer_id"], row["case_id"], row["generation"]):
            raise JournalFailure("Transfer scope mismatch")
        return TransferRecord(intent=value, state=row["state"])

    def _validate_all(self):
        self._schema()
        if self._db.execute("PRAGMA integrity_check").fetchone()[0] != "ok" or self._db.execute("PRAGMA foreign_key_check").fetchall():
            raise JournalFailure("Journal integrity constraints failed")
        for row in self._db.execute("SELECT case_id,generation FROM requests").fetchall():
            self._binding(*row)
        for row in self._db.execute("SELECT case_id,generation FROM original_requests").fetchall():
            self.original_request(*row)
        for row in self._db.execute("SELECT case_id FROM cases WHERE checkpoint_json IS NOT NULL").fetchall():
            self.checkpoint(row[0])
        for row in self._db.execute("SELECT action_id FROM intents").fetchall():
            self._intent(row[0])
        for row in self._db.execute("SELECT permit_hash FROM campaigns").fetchall():
            self._campaign(row[0])
        for row in self._db.execute("SELECT invocation_id FROM invocations").fetchall():
            self._invocation(row[0])
        for row in self._db.execute("SELECT entry_id FROM entries").fetchall():
            self.entry(row[0])
        for row in self._db.execute("SELECT question_id FROM waits").fetchall():
            self.wait(row[0])
        for row in self._db.execute("SELECT transfer_id FROM transfers").fetchall():
            self.transfer(row[0])
        for row in self._db.execute("SELECT case_id,generation FROM results").fetchall():
            self.saved_result(*row)
        for row in self._db.execute("SELECT case_id,event_json FROM audit").fetchall():
            audit = _read(CheckpointAudit, row[1])
            if audit.entry_id is not None and self.entry(audit.entry_id).case_id != row[0]:
                raise JournalFailure("Audit references another case entry")
            if audit.refusal_history is not None:
                if audit.refusal_history.predecessor.binding.case_id != row[0]:
                    raise JournalFailure("Refusal audit history belongs to another case")
                self._validate_refusal_history(audit.refusal_history)
        self._admission.validate_all()
        self._ownership.validate_events()
