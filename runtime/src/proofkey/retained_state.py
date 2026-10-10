"""Private immutable logical journal images; never release or disclosure authority."""
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
from typing import Protocol
import json
import math


_DOMAIN = 'case-store-retained-state-v1'
# Canonical complete inventory identity for the unchanged, fixed schema.sql v1.
_SCHEMA_HASH_V1 = 'b351849ccaa305758b1a2c15e75de09a6a4bf2bdd4dbe8e891046ceaa35aee56'
_TABLES = (
    ('admission_accounts', ('claimed_case_id', 'account_json', 'revision'), ('claimed_case_id',)),
    ('admission_attempts', ('attempt_id', 'claimed_case_id', 'dedup_hash', 'attempt_json', 'state'), ('attempt_id',)),
    ('admission_audit', ('sequence', 'claimed_case_id', 'event_json'), ('sequence',)),
    ('admission_entries', ('entry_id', 'attempt_id', 'claimed_case_id', 'charge_generation', 'lease_json', 'state'), ('entry_id',)),
    ('audit', ('sequence', 'case_id', 'event_json'), ('sequence',)),
    ('campaigns', ('permit_hash', 'campaign_id', 'permit_json', 'consumed_json', 'revision'), ('permit_hash',)),
    ('cases', ('case_id', 'checkpoint_json', 'revision'), ('case_id',)),
    ('entries', ('entry_id', 'case_id', 'generation', 'kind', 'subject_id', 'lease_json', 'state'), ('entry_id',)),
    ('intents', ('action_id', 'case_id', 'generation', 'fingerprint', 'intent_json', 'dispatch_state', 'verification_json'), ('action_id',)),
    ('invocations', ('invocation_id', 'case_id', 'generation', 'role', 'permit_hash', 'reservation_json', 'state', 'receipt_json'), ('invocation_id',)),
    ('original_requests', ('case_id', 'generation', 'request_json'), ('case_id', 'generation')),
    ('requests', ('case_id', 'generation', 'binding_json', 'versions_json', 'stop_requested', 'request_id', 'request_revision', 'consent_revision', 'fingerprint'), ('case_id', 'generation')),
    ('results', ('case_id', 'generation', 'result_json'), ('case_id', 'generation')),
    ('schema_meta', ('version',), ()),
    ('transfers', ('transfer_id', 'case_id', 'generation', 'transfer_json', 'state'), ('transfer_id',)),
    ('waits', ('question_id', 'case_id', 'generation', 'wait_json'), ('question_id',)),
)
_INTEGER_COLUMNS = frozenset(('sequence', 'revision', 'version', 'stop_requested'))
_NULLABLE = {
    'admission_accounts': frozenset(('claimed_case_id',)),
    'admission_attempts': frozenset(('attempt_id',)),
    'admission_entries': frozenset(('entry_id', 'charge_generation')),
    'campaigns': frozenset(('permit_hash',)),
    'cases': frozenset(('case_id', 'checkpoint_json')),
    'entries': frozenset(('entry_id', 'subject_id')),
    'intents': frozenset(('action_id', 'verification_json')),
    'invocations': frozenset(('invocation_id', 'receipt_json')),
    'requests': frozenset(('versions_json',)),
    'transfers': frozenset(('transfer_id',)),
    'waits': frozenset(('question_id',)),
}


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')


def _row_order(row, columns, keys):
    key = tuple((row[columns.index(column)] is not None, row[columns.index(column)]) for column in keys)
    # SQLite rowid-table PRIMARY KEY permits NULL ties, including identical rows.
    return key, _canonical(row) if any(not present for present, _ in key) else b''


class RetainedStateClock(Protocol):
    def now(self) -> datetime: ...
    def monotonic(self) -> float: ...


@dataclass(frozen=True, slots=True)
class RetainedStateLimitsV1:
    max_rows: int = 4096
    max_row_bytes: int = 262144
    max_payload_bytes: int = 4194304
    max_capture_seconds: float = 5.0
    max_sqlite_steps: int = 1000000

    def __post_init__(self):
        for field, ceiling in (('max_rows', 4096), ('max_row_bytes', 262144),
                               ('max_payload_bytes', 4194304), ('max_sqlite_steps', 1000000)):
            value = getattr(self, field)
            if type(value) is not int or not 0 < value <= ceiling:
                raise ValueError('Invalid retained-state limit')
        if (type(self.max_capture_seconds) is not float or not math.isfinite(self.max_capture_seconds)
                or not 0 < self.max_capture_seconds <= 5.0):
            raise ValueError('Invalid retained-state limit')


@dataclass(frozen=True, slots=True)
class RetainedStateSnapshotV1:
    kind: str
    schema_version: int
    schema_hash: str
    payload: bytes
    content_hash: str
    table_counts: tuple[tuple[str, int], ...]
    total_rows: int
    captured_at: datetime
    finished_at: datetime
    elapsed_seconds: float

    def __post_init__(self):
        try:
            self._validate()
        except (TypeError, ValueError, KeyError, IndexError, RecursionError, OverflowError):
            raise ValueError('Invalid retained-state snapshot') from None

    def _validate(self):
        if type(self.kind) is not str or self.kind != _DOMAIN or type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError()
        if type(self.payload) is not bytes or not 0 < len(self.payload) <= 4194304:
            raise ValueError()
        for value in (self.schema_hash, self.content_hash):
            if type(value) is not str or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
                raise ValueError()
        if sha256(self.payload).hexdigest() != self.content_hash:
            raise ValueError()
        for stamp in (self.captured_at, self.finished_at):
            if type(stamp) is not datetime or stamp.utcoffset() != timedelta(0):
                raise ValueError()
        if (self.finished_at < self.captured_at or self.finished_at - self.captured_at > timedelta(seconds=5)
                or type(self.elapsed_seconds) is not float or not math.isfinite(self.elapsed_seconds)
                or not 0 <= self.elapsed_seconds <= 5.0):
            raise ValueError()
        def pairs(items):
            result = {}
            for key, value in items:
                if key in result:
                    raise ValueError()
                result[key] = value
            return result
        data = json.loads(self.payload.decode('utf-8'), object_pairs_hook=pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError()))
        if (type(data) is not dict or set(data) != {'domain', 'schema_version', 'schema', 'tables'}
                or data['domain'] != _DOMAIN or type(data['schema_version']) is not int or data['schema_version'] != 1
                or _canonical(data) != self.payload):
            raise ValueError()
        schema = data['schema']
        if type(schema) is not list or len(schema) != len(_TABLES):
            raise ValueError()
        for row, (name, _, _) in zip(schema, _TABLES):
            if (type(row) is not list or len(row) != 3 or any(type(value) is not str for value in row)
                    or row[0] != 'table' or row[1] != name or not row[2]
                    or len(_canonical(row)) > 262144):
                raise ValueError()
        if sha256(_canonical(schema)).hexdigest() != self.schema_hash or self.schema_hash != _SCHEMA_HASH_V1:
            raise ValueError()
        tables = data['tables']
        if type(tables) is not list or len(tables) != len(_TABLES):
            raise ValueError()
        counts, total = [], 0
        for table, (name, columns, keys) in zip(tables, _TABLES):
            if (type(table) is not dict or set(table) != {'name', 'columns', 'rows'}
                    or table['name'] != name or table['columns'] != list(columns) or type(table['rows']) is not list):
                raise ValueError()
            previous = None
            for row in table['rows']:
                if type(row) is not list or len(row) != len(columns) or len(_canonical(row)) > 262144:
                    raise ValueError()
                for column, value in zip(columns, row):
                    if value is None:
                        if column not in _NULLABLE.get(name, ()):
                            raise ValueError()
                    elif type(value) is not (int if column in _INTEGER_COLUMNS else str):
                        raise ValueError()
                    elif type(value) is int and not -(1 << 63) <= value < (1 << 63):
                        raise ValueError()
                order = _row_order(row, columns, keys)
                if keys and previous is not None and (order < previous or
                        (order[0] == previous[0] and all(present for present, _ in order[0]))):
                    raise ValueError()
                previous = order
            if name == 'schema_meta' and table['rows'] != [[1]]:
                raise ValueError()
            counts.append((name, len(table['rows'])))
            total += len(table['rows'])
        if (type(self.total_rows) is not int or not 1 <= total <= 4096 or total != self.total_rows
                or type(self.table_counts) is not tuple or any(type(item) is not tuple or len(item) != 2
                    or type(item[0]) is not str or type(item[1]) is not int for item in self.table_counts)
                or self.table_counts != tuple(counts)):
            raise ValueError()
