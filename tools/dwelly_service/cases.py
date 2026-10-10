"""Local fixture intake; declarations are never execution authority."""
import hashlib
import json
import math
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime


MAX_REQUEST_BYTES = 16384
MAX_CASES = 256
MAX_EVENTS = 128
MAX_PARTICIPANTS = 16
MAX_TEXT = 4096
MAX_DEPTH = 16
MAX_SNAPSHOT_BYTES = (MAX_EVENTS + 1) * MAX_REQUEST_BYTES
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")
IDEMPOTENCY_KEY = re.compile(r"[A-Za-z0-9._:-]{1,128}")
HASH = re.compile(r"[a-f0-9]{64}")
DECLARATION_FIELDS = {"case_id", "links", "participants", "language"}
EVENT_FIELDS = {"event_id", "occurred_at", "channel", "sender_id", "recipient_ids", "kind", "text", "media"}
SNAPSHOT_FIELDS = DECLARATION_FIELDS | {"schema_version", "source_mode", "revision", "events",
                                      "previous_snapshot_hash", "snapshot_hash", "runtime_binding",
                                      "needs_analysis", "analysis_status", "authorization", "operational_effects"}
ERROR_CODES = frozenset({"invalid_case_request", "case_not_found", "revision_not_found",
                         "idempotency_conflict", "revision_conflict", "event_conflict",
                         "case_capacity", "case_storage_error"})


class CaseError(ValueError):
    def __init__(self, code):
        self.code = code if type(code) is str and code in ERROR_CODES else "case_storage_error"
        super().__init__(self.code)


def _require(condition):
    if not condition:
        raise CaseError("invalid_case_request")


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _bounded_json(value):
    """Reject non-JSON Python objects before encoding or traversing unbounded input."""
    pending, visited = [(value, 0)], 0
    while pending:
        item, depth = pending.pop()
        visited += 1
        _require(depth <= MAX_DEPTH and visited <= MAX_REQUEST_BYTES)
        kind = type(item)
        if kind is dict:
            _require(len(item) <= MAX_REQUEST_BYTES and all(type(key) is str for key in item))
            pending.extend((child, depth + 1) for pair in item.items() for child in pair)
        elif kind is list:
            _require(len(item) <= MAX_REQUEST_BYTES)
            pending.extend((child, depth + 1) for child in item)
        elif kind is str:
            _require(len(item) <= MAX_REQUEST_BYTES)
        elif kind is float:
            _require(math.isfinite(item))
        elif kind is int:
            _require(item.bit_length() <= MAX_REQUEST_BYTES * 4)
        else:
            _require(item is None or kind is bool)
    try:
        body = _canonical(value)
        _require(len(body.encode("utf-8")) <= MAX_REQUEST_BYTES)
        return json.loads(body), body
    except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
        raise CaseError("invalid_case_request") from None


def _identifier(value):
    _require(type(value) is str and IDENTIFIER.fullmatch(value) is not None)


def _ids(value, maximum):
    _require(type(value) is list and len(value) <= maximum)
    for item in value:
        _identifier(item)
    _require(len(set(value)) == len(value))


def _declaration(body):
    _require(type(body) is dict and set(body) == DECLARATION_FIELDS)
    _identifier(body["case_id"])
    links = body["links"]
    _require(type(links) is dict and set(links) == {"order_id", "customer_id", "operator_id"})
    for value in links.values():
        _identifier(value)
    _ids(body["participants"], MAX_PARTICIPANTS)
    _require(links["customer_id"] != links["operator_id"]
             and links["customer_id"] in body["participants"]
             and links["operator_id"] in body["participants"] and body["language"] == "en")


def _event(value, participants):
    _require(type(value) is dict and set(value) == EVENT_FIELDS)
    _identifier(value["event_id"])
    _require(type(value["occurred_at"]) is str and len(value["occurred_at"]) <= 64)
    try:
        timestamp = datetime.fromisoformat(value["occurred_at"].replace("Z", "+00:00"))
        _require(timestamp.tzinfo is not None and timestamp.utcoffset() is not None)
    except (ValueError, TypeError, OverflowError):
        raise CaseError("invalid_case_request") from None
    _require(value["channel"] in ("chat", "email", "phone", "internal"))
    _identifier(value["sender_id"])
    _ids(value["recipient_ids"], MAX_PARTICIPANTS)
    _require(value["sender_id"] in participants and all(item in participants for item in value["recipient_ids"]))
    text, media, kind = value["text"], value["media"], value["kind"]
    _require(text is None or type(text) is str and len(text) <= MAX_TEXT)
    if kind == "message":
        _require(type(text) is str and bool(text.strip()) and media is None)
        return
    _require(kind in ("photo", "voice_message", "call_recording"))
    _require(type(media) is dict and set(media) == {"asset_id", "sha256", "mime_type", "size_bytes"})
    _identifier(media["asset_id"])
    _require(type(media["sha256"]) is str and HASH.fullmatch(media["sha256"]) is not None)
    allowed = ("image/png", "image/jpeg") if kind == "photo" else ("audio/mpeg", "audio/wav", "audio/mp4", "audio/webm")
    limit = (10 if kind == "photo" else 25) * 1024 * 1024
    _require(media["mime_type"] in allowed and type(media["size_bytes"]) is int and 1 <= media["size_bytes"] <= limit)


def _append_request(body, participants):
    _require(type(body) is dict and set(body) == {"expected_revision", "event"})
    _require(type(body["expected_revision"]) is int and body["expected_revision"] >= 0)
    _event(body["event"], participants)


def _key(key):
    _require(type(key) is str and IDEMPOTENCY_KEY.fullmatch(key) is not None)


def _snapshot(body, events=None, previous=None):
    events = [] if events is None else events
    value = {"schema_version": "dwelly-local-case-v1", "source_mode": "local_fixture", **body,
             "revision": len(events), "events": events,
             "previous_snapshot_hash": previous, "runtime_binding": None,
             "needs_analysis": True, "analysis_status": "pending_not_started",
             "authorization": "unverified", "operational_effects": 0}
    value["snapshot_hash"] = hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()
    return value


def _unique_pairs(pairs):
    value = dict(pairs)
    _require(len(value) == len(pairs))
    return value


def _stored_json(raw, limit):
    try:
        _require(type(raw) is str and len(raw) <= limit and len(raw.encode("utf-8")) <= limit)
        value = json.loads(raw, object_pairs_hook=_unique_pairs)
        _require(_canonical(value) == raw)
        return value
    except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
        raise CaseError("case_storage_error") from None


def _validate_snapshot(value, case_id, revision, previous):
    _require(type(value) is dict and set(value) == SNAPSHOT_FIELDS)
    _require(value["schema_version"] == "dwelly-local-case-v1" and value["source_mode"] == "local_fixture"
             and value["runtime_binding"] is None and value["needs_analysis"] is True
             and value["analysis_status"] == "pending_not_started" and value["authorization"] == "unverified"
             and type(value["operational_effects"]) is int and value["operational_effects"] == 0)
    declaration = {field: value[field] for field in DECLARATION_FIELDS}
    _declaration(declaration)
    _bounded_json(declaration)
    _require(value["case_id"] == case_id and type(value["revision"]) is int and value["revision"] == revision)
    events = value["events"]
    _require(type(events) is list and len(events) == revision)
    _require(value["previous_snapshot_hash"] == (None if previous is None else previous["snapshot_hash"]))
    if previous is not None:
        _require(all(value[field] == previous[field] for field in DECLARATION_FIELDS)
                 and _canonical(events[:-1]) == _canonical(previous["events"]))
        # The exact prefix was validated at the prior revision in this same read.
        _event(events[-1], value["participants"])
        _bounded_json({"expected_revision": revision - 1, "event": events[-1]})
        _require(events[-1]["event_id"] not in {item["event_id"] for item in previous["events"]})
    _require(type(value["snapshot_hash"]) is str and HASH.fullmatch(value["snapshot_hash"]) is not None)
    core = {key: item for key, item in value.items() if key != "snapshot_hash"}
    _require(hashlib.sha256(_canonical(core).encode("utf-8")).hexdigest() == value["snapshot_hash"])


class CaseStore:
    def __init__(self, job_store):
        self.owner = job_store
        with self._transaction(write=True) as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS case_heads (case_id TEXT PRIMARY KEY, current_revision INTEGER NOT NULL)")
            connection.execute("""CREATE TABLE IF NOT EXISTS case_snapshots (
                case_id TEXT NOT NULL, revision INTEGER NOT NULL, snapshot TEXT NOT NULL,
                PRIMARY KEY (case_id, revision))""")
            connection.execute("""CREATE TABLE IF NOT EXISTS case_requests (
                scope TEXT NOT NULL, idempotency_key TEXT NOT NULL, body TEXT NOT NULL,
                case_id TEXT NOT NULL, revision INTEGER NOT NULL,
                PRIMARY KEY (scope, idempotency_key))""")

    @contextmanager
    def _transaction(self, write=False):
        try:
            with self.owner._connect() as connection:
                connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
                yield connection
        except CaseError:
            raise
        except (sqlite3.Error, OSError, ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
            raise CaseError("case_storage_error") from None

    def _history(self, connection, case_id):
        head = connection.execute("SELECT current_revision FROM case_heads WHERE case_id=?", (case_id,)).fetchone()
        if head is None:
            if connection.execute("SELECT 1 FROM case_snapshots WHERE case_id=? LIMIT 1", (case_id,)).fetchone():
                raise CaseError("case_storage_error")
            raise CaseError("case_not_found")
        try:
            _require(type(head[0]) is int and 0 <= head[0] <= MAX_EVENTS)
            rows = connection.execute("SELECT revision,snapshot FROM case_snapshots WHERE case_id=? ORDER BY revision LIMIT ?",
                                      (case_id, MAX_EVENTS + 2)).fetchall()
            _require(len(rows) == head[0] + 1)
            history = []
            for revision, row in enumerate(rows):
                _require(type(row["revision"]) is int and row["revision"] == revision)
                value = _stored_json(row["snapshot"], MAX_SNAPSHOT_BYTES)
                _validate_snapshot(value, case_id, revision, history[-1] if history else None)
                history.append(value)
            return history
        except (ValueError, TypeError, KeyError, UnicodeError, RecursionError, OverflowError):
            raise CaseError("case_storage_error") from None

    def _retry(self, connection, scope, key, encoded):
        row = connection.execute("SELECT * FROM case_requests WHERE scope=? AND idempotency_key=?", (scope, key)).fetchone()
        if row is None:
            return None
        try:
            _identifier(row["case_id"])
            original = _stored_json(row["body"], MAX_REQUEST_BYTES)
            history = self._history(connection, row["case_id"])
            revision = row["revision"]
            _require(type(revision) is int and 0 <= revision < len(history))
            saved = history[revision]
            if scope == "create":
                _declaration(original)
                _require(revision == 0 and original == {field: saved[field] for field in DECLARATION_FIELDS})
            else:
                _require(scope == "append:" + row["case_id"] and revision > 0)
                _append_request(original, saved["participants"])
                _require(original["expected_revision"] == revision - 1 and original["event"] == saved["events"][-1])
        except (ValueError, TypeError, KeyError, UnicodeError, RecursionError, OverflowError):
            raise CaseError("case_storage_error") from None
        if row["body"] != encoded:
            raise CaseError("idempotency_conflict")
        return saved

    def _after_revision(self, connection, snapshot):
        """Allow a backend to persist related work inside the revision transaction."""

    def create(self, key, body):
        _key(key)
        body, encoded = _bounded_json(body)
        _declaration(body)
        with self._transaction(write=True) as connection:
            existing = self._retry(connection, "create", key, encoded)
            if existing is not None:
                return existing, False
            if connection.execute("SELECT 1 FROM case_heads WHERE case_id=?", (body["case_id"],)).fetchone():
                raise CaseError("idempotency_conflict")
            if connection.execute("SELECT count(*) FROM case_heads").fetchone()[0] >= MAX_CASES:
                raise CaseError("case_capacity")
            value = _snapshot(body)
            connection.execute("INSERT INTO case_heads VALUES (?, 0)", (body["case_id"],))
            connection.execute("INSERT INTO case_snapshots VALUES (?, 0, ?)", (body["case_id"], _canonical(value)))
            connection.execute("INSERT INTO case_requests VALUES ('create', ?, ?, ?, 0)", (key, encoded, body["case_id"]))
            self._after_revision(connection, value)
            return self._history(connection, body["case_id"])[0], True

    def append(self, case_id, key, body):
        _identifier(case_id)
        _key(key)
        body, _encoded = _bounded_json(body)
        with self._transaction(write=True) as connection:
            return self._append(connection, case_id, key, body)

    def _append(self, connection, case_id, key, body):
        """Append using an already-held canonical write transaction.

        Callers own the transaction and its write lock; this never opens another
        connection. The public append and atomic inbound promotion share all
        validation, immutable snapshots, idempotency, and outbox hooks here.
        """
        _identifier(case_id)
        _key(key)
        body, encoded = _bounded_json(body)
        history = self._history(connection, case_id)
        current = history[-1]
        _append_request(body, current["participants"])
        existing = self._retry(connection, "append:" + case_id, key, encoded)
        if existing is not None:
            return existing, False
        if any(item["event_id"] == body["event"]["event_id"] for item in current["events"]):
            raise CaseError("event_conflict")
        if body["expected_revision"] != current["revision"]:
            raise CaseError("revision_conflict")
        if current["revision"] >= MAX_EVENTS:
            raise CaseError("case_capacity")
        declaration = {field: current[field] for field in DECLARATION_FIELDS}
        value = _snapshot(declaration, current["events"] + [body["event"]], current["snapshot_hash"])
        connection.execute("INSERT INTO case_snapshots VALUES (?, ?, ?)", (case_id, value["revision"], _canonical(value)))
        connection.execute("UPDATE case_heads SET current_revision=? WHERE case_id=?", (value["revision"], case_id))
        connection.execute("INSERT INTO case_requests VALUES (?, ?, ?, ?, ?)",
                           ("append:" + case_id, key, encoded, case_id, value["revision"]))
        self._after_revision(connection, value)
        return self._history(connection, case_id)[-1], True

    def get(self, case_id, revision=None):
        _identifier(case_id)
        _require(revision is None or type(revision) is int and revision >= 0)
        with self._transaction() as connection:
            history = self._history(connection, case_id)
            if revision is None:
                return history[-1]
            if revision >= len(history):
                raise CaseError("revision_not_found")
            return history[revision]
