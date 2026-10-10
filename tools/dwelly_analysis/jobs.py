"""PostgreSQL model jobs: atomic admission, retained budgets and one dispatch.

Leases fence database publication. They do not make a provider request exactly
once: an expired dispatched attempt without a durable response stays unknown.
"""
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation, localcontext
import hashlib
import json
from pathlib import Path
import re
import uuid

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row

from tools.dwelly_service.postgres import _database_log_scope
from .widget import check_json


_SCHEMA = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,62}")
_KEY = re.compile(r"[A-Za-z0-9._:-]{1,128}")
_ID = re.compile(r"[a-f0-9]{32}")
_HASH = re.compile(r"[a-f0-9]{64}")
_ERROR = re.compile(r"[a-z][a-z0-9_]{0,63}")
_MAX_PENDING = 256
_OPTIONS = "-c statement_timeout=10000 -c lock_timeout=5000 -c idle_in_transaction_session_timeout=15000"


class JobError(ValueError):
    """A bounded public error code; never include database diagnostics."""


def _schema(value):
    if type(value) is not str or not _SCHEMA.fullmatch(value) or value.lower().startswith("pg_"):
        raise JobError("invalid_database_schema")
    return value


def _canonical(value):
    try:
        if type(value) is not dict:
            raise ValueError()
        check_json(value)
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
        raise JobError("invalid_model_job") from None


def _money(value):
    try:
        if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
            raise ValueError()
        amount = Decimal(str(value))
        if not amount.is_finite() or not Decimal(0) < amount <= Decimal(25):
            raise ValueError()
        # Avoid accepting unbounded numeric exponents/precision into PostgreSQL.
        if len(amount.as_tuple().digits) > 64 or amount.adjusted() < -32:
            raise ValueError()
        return amount
    except (ValueError, InvalidOperation):
        raise JobError("invalid_model_job") from None


def _decimal_text(value):
    # Decimal.normalize() obeys ambient precision and can erase differences in
    # valid monetary inputs. Fixed-point formatting is exact and context-free.
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


@contextmanager
def _connection(dsn, schema):
    try:
        with _database_log_scope():
            conninfo_to_dict(dsn)
            with psycopg.connect(dsn, connect_timeout=5, options=_OPTIONS, row_factory=dict_row) as connection:
                connection.execute(sql.SQL("SET LOCAL search_path TO {}, pg_catalog").format(sql.Identifier(schema)))
                yield connection
    except JobError:
        raise
    except (psycopg.Error, OSError, ValueError, TypeError, UnicodeError, OverflowError):
        raise JobError("model_storage_error") from None


def migrate(dsn, schema="proofkey_analysis"):
    """Explicitly create only the selected schema and its versioned job tables."""
    schema = _schema(schema)
    with _connection(dsn, schema) as connection:
        connection.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", ("proofkey:model-migrate:" + schema,))
        connection.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema)))
        connection.execute("CREATE TABLE IF NOT EXISTS model_schema_migrations (version INTEGER PRIMARY KEY)")
        rows = connection.execute("SELECT version FROM model_schema_migrations ORDER BY version").fetchall()
        if rows and rows != [{"version": 1}]:
            raise JobError("model_storage_error")
        if not rows:
            connection.execute((Path(__file__).with_name("migrations") / "001_model_jobs.sql").read_text(encoding="utf-8"))
            connection.execute("INSERT INTO model_schema_migrations VALUES (1)")


class AnalysisJobStore:
    def __init__(self, dsn, schema="proofkey_analysis"):
        self.schema = _schema(schema)
        self._dsn = dsn
        try:
            with self._transaction() as connection:
                if connection.execute("SELECT version FROM model_schema_migrations ORDER BY version").fetchall() != [{"version": 1}]:
                    raise JobError("model_storage_error")
                connection.execute("SELECT job_id FROM model_jobs LIMIT 0")
                connection.execute("SELECT budget_key FROM model_budget_buckets LIMIT 0")
        except BaseException:
            self.close()
            raise

    @contextmanager
    def _transaction(self, write=False):
        if self._dsn is None:
            raise JobError("model_storage_error")
        with _connection(self._dsn, self.schema) as connection:
            if write:
                # A short schema-wide admission lock makes capacity, budget and
                # per-profile checks atomic across processes for this pilot.
                connection.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", ("proofkey:model-write:" + self.schema,))
            yield connection

    def close(self):
        self._dsn = None

    @staticmethod
    def _row(row):
        if row is None:
            raise KeyError("job_not_found")
        try:
            result = dict(row)
            for key in ("spec", "response", "result"):
                if result[key] is not None:
                    decoded = json.loads(result[key])
                    if _canonical(decoded) != result[key]:
                        raise ValueError()
                    result[key] = decoded
            result["reserved_usd"] = float(result["reserved_usd"])
            for key in ("created_at", "started_at", "finished_at", "lease_expires_at"):
                if result[key] is not None:
                    result[key] = result[key].isoformat()
            return result
        except (ValueError, KeyError, TypeError, UnicodeError, RecursionError, OverflowError):
            raise JobError("model_storage_error") from None

    def submit(self, key, spec, reservation, cap, scope):
        if type(key) is not str or not _KEY.fullmatch(key) or type(scope) is not str or not _KEY.fullmatch(scope):
            raise JobError("invalid_model_job")
        encoded = _canonical(spec)
        try:
            required = {"input", "reference", "source", "profile", "settings", "profile_hash", "prompt_hash", "budget_key"}
            if not required <= set(spec) or any(type(spec[field]) is not dict for field in ("input", "reference", "source", "profile", "settings")):
                raise ValueError()
            profile = spec["profile"]
            profile_id = profile["id"]
            config = profile["config"]
            if type(profile_id) is not str or not _KEY.fullmatch(profile_id):
                raise ValueError()
            if (type(config) is not dict or config["provider"] not in {"openai", "anthropic", "gemini"}
                    or type(config["model"]) is not str or not config["model"] or len(config["model"]) > 256
                    or any(ord(character) < 32 for character in config["model"])):
                raise ValueError()
            budget_key = config["provider"] + ":" + config["model"]
            if spec["budget_key"] != budget_key or any(type(spec[field]) is not str or not _HASH.fullmatch(spec[field]) for field in ("profile_hash", "prompt_hash")):
                raise ValueError()
        except (KeyError, TypeError, ValueError):
            raise JobError("invalid_model_job") from None
        amount, ceiling = _money(reservation), _money(cap)
        if amount > ceiling:
            raise JobError("budget_exhausted")
        fingerprint = hashlib.sha256(_canonical({"spec": spec, "reservation": _decimal_text(amount),
                                                "cap": _decimal_text(ceiling), "scope": scope}).encode("utf-8")).hexdigest()
        with self._transaction(write=True) as connection:
            existing = connection.execute("SELECT * FROM model_jobs WHERE idempotency_key=%s", (key,)).fetchone()
            if existing:
                if existing["fingerprint"] != fingerprint:
                    raise JobError("idempotency_conflict")
                return self._row(existing), False
            if connection.execute("SELECT count(*) AS count FROM model_jobs WHERE status IN ('queued','running','response_received')").fetchone()["count"] >= _MAX_PENDING:
                raise JobError("queue_full")
            bucket = connection.execute("SELECT * FROM model_budget_buckets WHERE budget_scope=%s AND budget_key=%s", (scope, budget_key)).fetchone()
            if bucket and bucket["cap_usd"] != ceiling:
                raise JobError("budget_cap_changed")
            with localcontext() as decimal_context:
                decimal_context.prec = 100
                if bucket and bucket["reserved_usd"] + amount > ceiling:
                    raise JobError("budget_exhausted")
            if not bucket:
                connection.execute("INSERT INTO model_budget_buckets (budget_scope,budget_key,cap_usd) VALUES (%s,%s,%s)", (scope, budget_key, ceiling))
            connection.execute("UPDATE model_budget_buckets SET reserved_usd=reserved_usd+%s WHERE budget_scope=%s AND budget_key=%s", (amount, scope, budget_key))
            row = connection.execute("""INSERT INTO model_jobs
                (job_id,idempotency_key,fingerprint,spec,profile_id,budget_scope,budget_key,reserved_usd,attempt_id)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *""",
                (uuid.uuid4().hex, key, fingerprint, encoded, profile_id, scope, budget_key, amount, uuid.uuid4().hex)).fetchone()
            return self._row(row), True

    def get(self, job_id):
        if type(job_id) is not str or not _ID.fullmatch(job_id):
            raise KeyError("job_not_found")
        with self._transaction() as connection:
            return self._row(connection.execute("SELECT * FROM model_jobs WHERE job_id=%s", (job_id,)).fetchone())

    def get_by_key(self, key):
        """Read frozen admission by key; never reserve or change job state."""
        if type(key) is not str or not _KEY.fullmatch(key):
            raise JobError("invalid_model_job")
        with self._transaction() as connection:
            row = connection.execute("SELECT * FROM model_jobs WHERE idempotency_key=%s", (key,)).fetchone()
            return None if row is None else self._row(row)

    @staticmethod
    def _recover(connection):
        # All checks use database time. A saved response only needs local parsing.
        unknown = connection.execute("""UPDATE model_jobs SET status='outcome_unknown',
            error='provider_outcome_unknown', finished_at=clock_timestamp(), lease_token=NULL, lease_expires_at=NULL
            WHERE status='running' AND lease_expires_at <= clock_timestamp()
                AND dispatch_attempts=1 AND response IS NULL""").rowcount
        requeued = connection.execute("""UPDATE model_jobs SET status='queued', lease_token=NULL, lease_expires_at=NULL
            WHERE status='running' AND lease_expires_at <= clock_timestamp() AND dispatch_attempts=0""").rowcount
        responses = connection.execute("""UPDATE model_jobs SET lease_token=NULL, lease_expires_at=NULL
            WHERE status='response_received' AND lease_expires_at <= clock_timestamp()""").rowcount
        return {"outcome_unknown": unknown, "requeued": requeued, "response_recovered": responses}

    def recover_expired(self):
        with self._transaction(write=True) as connection:
            return self._recover(connection)

    def claim_next(self, lease_seconds=120, max_running=3, per_profile=1):
        if any(type(value) is not int for value in (lease_seconds, max_running, per_profile)) or not 1 <= lease_seconds <= 3600 or not 1 <= max_running <= 3 or not 1 <= per_profile <= max_running:
            raise JobError("invalid_model_job")
        with self._transaction(write=True) as connection:
            self._recover(connection)
            active = connection.execute("""SELECT profile_id FROM model_jobs
                WHERE status IN ('running','response_received') AND lease_expires_at > clock_timestamp()""").fetchall()
            if len(active) >= max_running:
                return None
            counts = {}
            for item in active:
                counts[item["profile_id"]] = counts.get(item["profile_id"], 0) + 1
            rows = connection.execute("""SELECT job_id,profile_id FROM model_jobs
                WHERE status='queued' OR (status='response_received' AND lease_token IS NULL)
                ORDER BY created_at,job_id""").fetchall()
            chosen = next((row for row in rows if counts.get(row["profile_id"], 0) < per_profile), None)
            if chosen is None:
                return None
            row = connection.execute("""UPDATE model_jobs SET
                status=CASE WHEN status='queued' THEN 'running' ELSE status END,
                lease_token=%s, lease_expires_at=clock_timestamp()+(%s * interval '1 second'),
                started_at=COALESCE(started_at,clock_timestamp()) WHERE job_id=%s RETURNING *""",
                (uuid.uuid4().hex, lease_seconds, chosen["job_id"])).fetchone()
            return self._row(row)

    @staticmethod
    def _valid_identity(job_id, token):
        return type(job_id) is str and _ID.fullmatch(job_id) is not None and type(token) is str and _ID.fullmatch(token) is not None

    def mark_dispatched(self, job_id, token):
        if not self._valid_identity(job_id, token):
            return False
        with self._transaction(write=True) as connection:
            return connection.execute("""UPDATE model_jobs SET dispatch_attempts=1
                WHERE job_id=%s AND lease_token=%s AND lease_expires_at > clock_timestamp()
                    AND status='running' AND dispatch_attempts=0 RETURNING job_id""", (job_id, token)).fetchone() is not None

    def record_response(self, job_id, token, response):
        if not self._valid_identity(job_id, token):
            return False
        encoded = _canonical(response)
        with self._transaction(write=True) as connection:
            return connection.execute("""UPDATE model_jobs SET status='response_received',response=%s
                WHERE job_id=%s AND lease_token=%s AND lease_expires_at > clock_timestamp()
                    AND status='running' AND dispatch_attempts=1 AND response IS NULL RETURNING job_id""", (encoded, job_id, token)).fetchone() is not None

    def finish(self, job_id, token, result=None, error=None, status="succeeded"):
        if not self._valid_identity(job_id, token):
            return False
        if status not in {"succeeded", "failed", "outcome_unknown"} or (error is not None and (type(error) is not str or not _ERROR.fullmatch(error))):
            raise JobError("invalid_model_job")
        if (status == "succeeded" and (result is None or error is not None)) or (status != "succeeded" and (result is not None or error is None)):
            raise JobError("invalid_model_job")
        encoded = _canonical(result) if result is not None else None
        with self._transaction(write=True) as connection:
            return connection.execute("""UPDATE model_jobs SET status=%s,result=%s,error=%s,
                finished_at=clock_timestamp(),lease_token=NULL,lease_expires_at=NULL
                WHERE job_id=%s AND lease_token=%s AND lease_expires_at > clock_timestamp()
                    AND status IN ('running','response_received')
                    AND (%s <> 'succeeded' OR status='response_received') RETURNING job_id""",
                (status, encoded, error, job_id, token, status)).fetchone() is not None
