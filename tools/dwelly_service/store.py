"""SQLite queue on private persistent POSIX storage, with one process owner."""
import fcntl
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import time
import uuid

from tools.dwelly_cases.baseline import propose
from tools.dwelly_cases.runner import strict_json, validate_snapshot
from tools.dwelly_model.budget import sync_directory
from tools.dwelly_model import semantic


TERMINAL = frozenset({"completed", "cancelled", "failed", "interrupted"})
JOB_ID = re.compile(r"[a-f0-9]{32}")
MAX_PENDING_JOBS = 256


def safe_path(value):
    """Reject symlinks instead of silently following an operator input or state path."""
    path = Path(value).absolute()
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError("unsafe_path")
    return path.resolve()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


class JobStore:
    def __init__(self, root):
        self.root = safe_path(root)
        self.lock = None
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not self.root.is_dir() or self.root.stat().st_uid != os.getuid():
            raise ValueError("unsafe_state_directory")
        os.chmod(self.root, 0o700)
        self.jobs = safe_path(self.root / "jobs")
        self.jobs.mkdir(mode=0o700, exist_ok=True)
        if not self.jobs.is_dir():
            raise ValueError("unsafe_state_directory")
        os.chmod(self.jobs, 0o700)
        for name in ("queue.sqlite3", "queue.sqlite3-journal", "queue.sqlite3-wal", "queue.sqlite3-shm", "owner.lock", "budget.jsonl"):
            safe_path(self.root / name)
        descriptor = os.open(self.root / "owner.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        self.lock = os.fdopen(descriptor, "a+b")
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise ValueError("unsafe_state_lock")
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ValueError("state_locked") from None
            self.database = self.root / "queue.sqlite3"
            with self._connect() as connection:
                connection.execute("PRAGMA journal_mode=DELETE")
                connection.execute("CREATE TABLE IF NOT EXISTS metadata (name TEXT PRIMARY KEY, value TEXT NOT NULL)")
                connection.execute("""CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY, idempotency_key TEXT UNIQUE NOT NULL,
                    body TEXT NOT NULL, fingerprint TEXT NOT NULL, status TEXT NOT NULL,
                    created REAL NOT NULL, updated REAL NOT NULL,
                    cancel_requested INTEGER NOT NULL DEFAULT 0, error TEXT)""")
            os.chmod(self.database, 0o600)
            sync_directory(self.root)
            self._recover()
        except BaseException:
            self.close()
            raise

    @contextmanager
    def _connect(self):
        if self.lock is None:
            raise ValueError("store_closed")
        connection = sqlite3.connect(str(self.database), timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA synchronous=FULL")
            with connection:
                yield connection
        finally:
            connection.close()

    def close(self):
        if self.lock is not None:
            self.lock.close()
            self.lock = None

    def bind_inputs(self, identity):
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT value FROM metadata WHERE name='input_identity'").fetchone()
            if row and row[0] != identity:
                raise ValueError("input_identity_changed")
            connection.execute("INSERT OR IGNORE INTO metadata VALUES ('input_identity', ?)", (identity,))

    @staticmethod
    def _row(row):
        if row is None:
            raise KeyError("job_not_found")
        return {"job_id": row["job_id"], "spec": json.loads(row["body"]), "status": row["status"],
                "created_at": row["created"], "updated_at": row["updated"],
                "cancel_requested": bool(row["cancel_requested"]), "error": row["error"]}

    def submit(self, key, spec):
        body = _canonical(spec)
        fingerprint = hashlib.sha256(body.encode()).hexdigest()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute("SELECT * FROM jobs WHERE idempotency_key=?", (key,)).fetchone()
            if existing:
                if existing["fingerprint"] != fingerprint:
                    raise ValueError("idempotency_conflict")
                return self._row(existing), False
            pending = connection.execute("SELECT count(*) FROM jobs WHERE status IN ('queued', 'running')").fetchone()[0]
            if pending >= MAX_PENDING_JOBS:
                raise ValueError("queue_full")
            job_id, now = uuid.uuid4().hex, time.time()
            connection.execute("INSERT INTO jobs VALUES (?, ?, ?, ?, 'queued', ?, ?, 0, NULL)",
                               (job_id, key, body, fingerprint, now, now))
            row = connection.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
        return self._row(row), True

    def check_ready(self):
        with self._connect() as connection:
            connection.execute("SELECT count(*) FROM jobs").fetchone()

    def get(self, job_id):
        if not isinstance(job_id, str) or JOB_ID.fullmatch(job_id) is None:
            raise KeyError("job_not_found")
        with self._connect() as connection:
            return self._row(connection.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone())

    def claim_next(self):
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if connection.execute("SELECT 1 FROM jobs WHERE status='running'").fetchone():
                return None
            row = connection.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY created, job_id LIMIT 1").fetchone()
            if row is None:
                return None
            connection.execute("UPDATE jobs SET status='running', updated=? WHERE job_id=?", (time.time(), row["job_id"]))
            row = connection.execute("SELECT * FROM jobs WHERE job_id=?", (row["job_id"],)).fetchone()
        return self._row(row)

    def cancel(self, job_id):
        self.get(job_id)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("""UPDATE jobs SET cancel_requested=1,
                status=CASE WHEN status='queued' THEN 'cancelled' ELSE status END, updated=?
                WHERE job_id=? AND status IN ('queued', 'running')""", (time.time(), job_id))
        return self.get(job_id)

    def cancelled(self, job_id):
        return self.get(job_id)["cancel_requested"]

    def finish(self, job_id, status, error=None):
        if status not in TERMINAL or error not in (None, "execution_failed", "process_interrupted", "invalid_terminal_summary"):
            raise ValueError("invalid_terminal_state")
        with self._connect() as connection:
            connection.execute("UPDATE jobs SET status=?, error=?, updated=? WHERE job_id=? AND status='running'",
                               (status, error, time.time(), job_id))

    def output_path(self, job_id):
        self.get(job_id)
        path = safe_path(self.jobs / job_id)
        if not path.is_relative_to(self.jobs):
            raise ValueError("unsafe_path")
        return path

    def summary(self, job_id):
        job = self.get(job_id)
        try:
            path = safe_path(self.output_path(job_id) / "summary.json")
            descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(descriptor, "rb") as stream:
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_size > 4 * 1024 * 1024:
                    raise ValueError("invalid_summary")
                data = stream.read(4 * 1024 * 1024 + 1)
            value = strict_json(data)
            expected_mode = "live_api" if job["spec"].get("mode") == "live" else "offline_dry_run"
            if (type(value) is not dict or value.get("schema_version") != "dwelly-model-experiment-v1"
                    or value.get("status") not in {"completed", "cancelled"}
                    or value.get("mode") != expected_mode or value.get("operational_effects") != 0
                    or type(value.get("live_calls")) is not int or value["live_calls"] < 0
                    or expected_mode == "offline_dry_run" and value["live_calls"] != 0):
                raise ValueError("invalid_summary")
            return value
        except (OSError, ValueError, TypeError, RecursionError, OverflowError):
            raise ValueError("summary_unavailable") from None

    @staticmethod
    def _read_json(path, limit):
        descriptor = os.open(safe_path(path), os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(descriptor, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
                raise ValueError("invalid_artifact")
            value = stream.read(limit + 1)
        if len(value) > limit:
            raise ValueError("invalid_artifact")
        return strict_json(value)

    def proposals(self, job_id):
        """Read only complete, validated unsent envelopes, never arbitrary artifacts."""
        job = self.get(job_id)
        values = []
        try:
            output = self.output_path(job_id)
            folder = safe_path(output / "proposals")
            if not folder.is_dir():
                return values
            for path in sorted(folder.iterdir()):
                if not re.fullmatch(r"delivery-logistics-\d{3}\.json", path.name):
                    continue
                if len(values) >= min(job["spec"].get("limit", 1), 50):
                    break
                try:
                    value = self._read_json(path, 65536)
                    snapshot = self._read_json(output / "snapshots" / path.name, 4 * 1024 * 1024)
                    case_id = path.stem
                    validate_snapshot(snapshot, case_id)
                    if (type(value) is not dict or value.get("case_id") != case_id
                            or value.get("input_hash") != snapshot["input_hash"]
                            or value.get("status") != "proposed_unsent" or value.get("effects") != []):
                        continue
                    if value.get("schema_version") == "dwelly-proposal-v1":
                        if job["spec"].get("mode") == "live" or value != propose(snapshot):
                            continue
                    elif value.get("schema_version") == "dwelly-model-proposal-v1":
                        envelope = {"schema_version", "case_id", "input_hash", "status", "effects", "mode"}
                        if (set(value) != envelope | semantic.PROPOSAL_FIELDS
                                or job["spec"].get("mode") != "live" or value.get("mode") != "live_api"):
                            continue
                        semantic.validate_proposal(snapshot, {key: value[key] for key in semantic.PROPOSAL_FIELDS})
                    else:
                        continue
                    values.append(value)
                except (OSError, ValueError, TypeError, KeyError, RecursionError, OverflowError):
                    continue
        except (OSError, ValueError):
            return []
        return values

    def progress(self, job_id):
        result = {"proposals": 0, "receipts": 0, "judgments": 0}
        try:
            output = self.output_path(job_id)
            for name in result:
                folder = safe_path(output / name)
                if folder.is_dir():
                    for item in folder.iterdir():
                        if item.is_symlink() or not item.is_file() or item.suffix != ".json":
                            continue
                        try:
                            if item.stat().st_size > 4 * 1024 * 1024:
                                continue
                            with item.open("rb") as stream:
                                strict_json(stream.read(4 * 1024 * 1024 + 1))
                        except (OSError, ValueError, TypeError, RecursionError, OverflowError):
                            continue
                        result[name] += 1
        except (OSError, ValueError):
            pass
        return result

    def _recover(self):
        with self._connect() as connection:
            rows = connection.execute("SELECT job_id FROM jobs WHERE status='running'").fetchall()
        for row in rows:
            try:
                summary = self.summary(row[0])
            except ValueError:
                self.finish(row[0], "interrupted", "process_interrupted")
            else:
                self.finish(row[0], summary["status"])
