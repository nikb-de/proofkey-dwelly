"""PostgreSQL platform data shares canonical case transactions and write locks."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import re
import uuid

import psycopg

from tools.dwelly_service import postgres
from tools.dwelly_service.cases import _bounded_json, _canonical, _identifier, _key
from .domain import PlatformError, action_checks, check_snapshot, project, project_coordination, require
from .coordination import CoordinationMixin


def migrate(database_url, *, schema="public"):
    postgres.migrate(database_url, schema=schema)
    schema = postgres._schema(schema)
    try:
        with postgres._database_log_scope(), psycopg.connect(database_url, connect_timeout=10) as connection:
            connection.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", ("proofkey:migrate:" + schema,))
            postgres._search_path(connection, schema)
            connection.execute("CREATE TABLE IF NOT EXISTS platform_schema_migrations (version INTEGER PRIMARY KEY)")
            versions = connection.execute("SELECT version FROM platform_schema_migrations ORDER BY version").fetchall()
            require(versions in ([], [(1,)], [(1,), (2,)]), "platform_storage_error")
            if not versions:
                connection.execute((Path(__file__).parent / "migrations/001_platform.sql").read_text(encoding="utf-8"))
                connection.execute("INSERT INTO platform_schema_migrations VALUES (1)")
            if (2,) not in versions:
                connection.execute((Path(__file__).parent / "migrations/002_coordination.sql").read_text(encoding="utf-8"))
                connection.execute("INSERT INTO platform_schema_migrations VALUES (2)")
    except PlatformError:
        raise
    except postgres._DB_ERRORS:
        raise PlatformError("platform_storage_error") from None


class PlatformStore(CoordinationMixin, postgres.PostgresCaseStore):
    def __init__(self, *args, operator_identity="local-operator", **kwargs):
        _identifier(operator_identity)
        self.operator_identity = operator_identity
        super().__init__(*args, **kwargs)

    def check_ready(self):
        super().check_ready()
        with self._transaction() as connection:
            versions = connection.execute("SELECT version FROM platform_schema_migrations ORDER BY version").fetchall()
            require([row[0] for row in versions] == [1, 2], "platform_storage_error")
            for table in ("platform_decisions", "platform_reviews", "platform_bookings", "platform_actions",
                          "platform_assets", "platform_model_links", "platform_requests", "platform_coordination"):
                connection.execute("SELECT 1 FROM " + table + " LIMIT 0")

    @staticmethod
    def _now(connection):
        return connection.execute("SELECT clock_timestamp()").fetchone()[0]

    def _after_revision(self, connection, snapshot):
        if snapshot["events"]:
            media = snapshot["events"][-1]["media"]
            if media is not None:
                asset = self._asset(connection, snapshot["case_id"], media["asset_id"])
                require(all(asset[field] == media[field] for field in ("asset_id", "sha256", "mime_type", "size_bytes")),
                        "asset_mismatch")
        super()._after_revision(connection, snapshot)

    @staticmethod
    def _records(connection, table, case_id):
        return [json.loads(row[0]) for row in connection.execute(
            "SELECT record FROM " + table + " WHERE case_id=? ORDER BY sequence", (case_id,)).fetchall()]

    def _detail(self, connection, case_id):
        snapshot = self._history(connection, case_id)[-1]
        decisions = self._records(connection, "platform_decisions", case_id)
        reviews = self._records(connection, "platform_reviews", case_id)
        actions = self._records(connection, "platform_actions", case_id)
        assets = [dict(row) for row in connection.execute(
            "SELECT asset_id,sha256,mime_type,size_bytes,filename FROM platform_assets WHERE case_id=? ORDER BY sequence", (case_id,)).fetchall()]
        links = [dict(row) for row in connection.execute(
            "SELECT job_id,revision,snapshot_hash FROM platform_model_links WHERE case_id=? ORDER BY sequence", (case_id,)).fetchall()]
        result = project(snapshot, decisions, reviews, actions, assets, links)
        return project_coordination(result, self._coordination_detail(connection, case_id))

    def detail(self, case_id):
        _identifier(case_id)
        with self._transaction() as connection:
            return self._detail(connection, case_id)

    def list_cases(self):
        with self._transaction() as connection:
            result = []
            for row in connection.execute("SELECT case_id FROM case_heads ORDER BY case_id").fetchall():
                detail = self._detail(connection, row[0])
                result.append({"case_id": row[0], "revision": detail["snapshot"]["revision"],
                               "links": detail["snapshot"]["links"], "states": detail["states"], "external_effects": 0})
            return result

    @contextmanager
    def _request(self, case_id, operation, key, body):
        _identifier(case_id)
        _key(key)
        body, encoded = _bounded_json(body)
        require(type(body) is dict)
        scope = operation + ":" + case_id
        with self._transaction(write=True) as connection:
            self._history(connection, case_id)
            row = connection.execute("SELECT body,result FROM platform_requests WHERE scope=? AND idempotency_key=?", (scope, key)).fetchone()
            if row:
                require(row["body"] == encoded, "idempotency_conflict")
                yield connection, body, json.loads(row["result"]), lambda result: None
            else:
                def save(result):
                    connection.execute("INSERT INTO platform_requests VALUES (?,?,?,?)", (scope, key, encoded, _canonical(result)))
                yield connection, body, None, save

    def _decision(self, connection, snapshot, kind, action, evidence):
        require(type(action) is dict and type(action.get("type")) is str, "invalid_platform_request")
        require(type(evidence) is list and all(type(item) is str for item in evidence)
                and len(set(evidence)) == len(evidence), "invalid_platform_request")
        require(set(evidence) <= {event["event_id"] for event in snapshot["events"]}, "evidence_not_found")
        now = self._now(connection)
        checks = action_checks(action, evidence, now)
        record = {"decision_id": uuid.uuid4().hex, "case_id": snapshot["case_id"], "revision": snapshot["revision"],
                  "snapshot_hash": snapshot["snapshot_hash"], "kind": kind, "action": action,
                  "checks": checks, "evidence_event_ids": evidence, "created_at": now.isoformat()}
        connection.execute("INSERT INTO platform_decisions (decision_id,case_id,revision,record) VALUES (?,?,?,?)",
                           (record["decision_id"], record["case_id"], record["revision"], _canonical(record)))

    def analyze(self, case_id, key, body):
        with self._request(case_id, "analyze", key, body) as (connection, body, replay, save):
            if replay is not None:
                return replay
            require(set(body) == {"expected_revision", "snapshot_hash", "mode"} and body["mode"] == "deterministic")
            snapshot = self._history(connection, case_id)[-1]
            check_snapshot(snapshot, body)
            text = [event["event_id"] for event in snapshot["events"] if event["kind"] == "message"]
            action = ({"type": "operator_review", "message": "An operator must review the supplied evidence."} if text else
                      {"type": "request_information", "message": "Please provide text describing the request. Uploaded media has not been transcribed or read."})
            self._decision(connection, snapshot, "deterministic", action, text)
            result = self._detail(connection, case_id)
            save(result)
            return result

    def propose(self, case_id, key, body):
        with self._request(case_id, "propose", key, body) as (connection, body, replay, save):
            if replay is not None:
                return replay
            require(set(body) == {"expected_revision", "snapshot_hash", "action", "evidence_event_ids"})
            snapshot = self._history(connection, case_id)[-1]
            check_snapshot(snapshot, body)
            self._decision(connection, snapshot, "operator", body["action"], body["evidence_event_ids"])
            result = self._detail(connection, case_id)
            save(result)
            return result

    def _current_decision(self, connection, case_id, decision_id):
        require(type(decision_id) is str, "invalid_platform_request")
        records = self._records(connection, "platform_decisions", case_id)
        match = next((item for item in records if item["decision_id"] == decision_id), None)
        require(match is not None, "decision_not_found")
        snapshot = self._history(connection, case_id)[-1]
        check_snapshot(snapshot, {"expected_revision": match["revision"], "snapshot_hash": match["snapshot_hash"]})
        require(records[-1]["decision_id"] == decision_id, "decision_superseded")
        return match

    @staticmethod
    def _require_executable(decision, now):
        require(decision["action"]["type"] == "reschedule_delivery", "action_blocked")
        require(all(item["passed"] for item in decision["checks"]), "action_blocked")
        require(all(item["passed"] for item in action_checks(decision["action"], decision["evidence_event_ids"], now)),
                "action_blocked")

    def review(self, case_id, key, body):
        with self._request(case_id, "review", key, body) as (connection, body, replay, save):
            if replay is not None:
                return replay
            require(set(body) == {"decision_id", "verdict", "note", "customer_consent_confirmed"})
            require(body["verdict"] in ("approve", "reject") and type(body["note"]) is str and
                    0 < len(body["note"].strip()) <= 4096 and type(body["customer_consent_confirmed"]) is bool)
            decision = self._current_decision(connection, case_id, body["decision_id"])
            now = self._now(connection)
            if body["verdict"] == "approve":
                if decision["action"]["type"] not in ("operator_review", "request_information"):
                    self._require_executable(decision, now)
                    require(body["customer_consent_confirmed"], "consent_required")
            require(not any(item["decision_id"] == decision["decision_id"] for item in self._records(connection, "platform_actions", case_id)),
                    "already_executed")
            record = {"review_id": uuid.uuid4().hex, "case_id": case_id, **body, "operator_id": self.operator_identity,
                      "revision": decision["revision"], "snapshot_hash": decision["snapshot_hash"],
                      "attestation_scope": "local_operator_attestation_not_customer_identity_verification",
                      "created_at": now.isoformat()}
            connection.execute("INSERT INTO platform_reviews (review_id,decision_id,case_id,record) VALUES (?,?,?,?)",
                               (record["review_id"], record["decision_id"], case_id, _canonical(record)))
            result = self._detail(connection, case_id)
            save(result)
            return result

    def execute(self, case_id, key, body):
        with self._request(case_id, "execute", key, body) as (connection, body, replay, save):
            if replay is not None:
                return replay
            require(set(body) == {"decision_id"} and type(body["decision_id"]) is str)
            actions = self._records(connection, "platform_actions", case_id)
            if any(item["decision_id"] == body["decision_id"] for item in actions):
                result = self._detail(connection, case_id)
                save(result)
                return result
            decision = self._current_decision(connection, case_id, body["decision_id"])
            now = self._now(connection)
            self._require_executable(decision, now)
            reviews = [item for item in self._records(connection, "platform_reviews", case_id) if item["decision_id"] == decision["decision_id"]]
            require(reviews and reviews[-1]["verdict"] == "approve" and reviews[-1]["customer_consent_confirmed"], "approval_required")
            action_id, booking_id = uuid.uuid4().hex, uuid.uuid4().hex
            action = decision["action"]
            connection.execute("INSERT INTO platform_bookings VALUES (?,?,?,?,?,?)",
                               (booking_id, decision["decision_id"], case_id, action["slot_start"], action["slot_end"], False))
            record = {"action_id": action_id, "booking_id": booking_id, "decision_id": decision["decision_id"], "case_id": case_id,
                      "revision": decision["revision"], "snapshot_hash": decision["snapshot_hash"], "action": action,
                      "review_id": reviews[-1]["review_id"], "execution_mode": "postgres_sandbox", "sandbox_effects": 1,
                      "external_effects": 0, "status": "verified", "message": "Sandbox booking recorded locally. No carrier was contacted.",
                      "created_at": now.isoformat()}
            connection.execute("INSERT INTO platform_actions (action_id,decision_id,booking_id,case_id,record) VALUES (?,?,?,?,?)",
                               (action_id, decision["decision_id"], booking_id, case_id, _canonical(record)))
            result = self._detail(connection, case_id)
            save(result)
            return result

    @staticmethod
    def _asset(connection, case_id, asset_id):
        row = connection.execute("SELECT asset_id,case_id,sha256,mime_type,size_bytes,filename FROM platform_assets WHERE case_id=? AND asset_id=?",
                                 (case_id, asset_id)).fetchone()
        require(row is not None, "asset_not_found")
        return dict(row)

    @staticmethod
    def _validate_asset(mime, filename, data):
        require(type(mime) is str and type(filename) is str and type(data) is bytes and len(data) > 0, "invalid_asset")
        require(mime in ("image/png", "image/jpeg", "audio/mpeg", "audio/wav", "audio/mp4", "audio/webm"), "invalid_asset")
        require(len(data) <= (10 if mime.startswith("image/") else 25) * 1024 * 1024, "asset_too_large")
        valid = {"image/png": data.startswith(b"\x89PNG\r\n\x1a\n"), "image/jpeg": data.startswith(b"\xff\xd8\xff"),
                 "audio/mpeg": data.startswith(b"ID3") or (len(data) >= 2 and data[0] == 255 and data[1] & 224 == 224),
                 "audio/wav": data.startswith(b"RIFF") and data[8:12] == b"WAVE",
                 "audio/mp4": len(data) >= 12 and data[4:8] == b"ftyp" and data[8:12] in (b"M4A ", b"isom", b"mp42", b"mp41"),
                 "audio/webm": data.startswith(b"\x1a\x45\xdf\xa3") and b"webm" in data[:4096]}
        require(valid[mime], "invalid_asset")

    def put_asset(self, case_id, key, mime, filename, data):
        self._validate_asset(mime, filename, data)
        with self._transaction(write=True) as connection:
            return self._put_asset(connection, case_id, key, mime, filename, data)

    def _put_asset(self, connection, case_id, key, mime, filename, data):
        """Store an asset within the caller's canonical write transaction."""
        _identifier(case_id)
        _key(key)
        self._validate_asset(mime, filename, data)
        sha256 = hashlib.sha256(data).hexdigest()
        body = {"mime_type": mime, "filename": filename, "sha256": sha256, "size_bytes": len(data)}
        body, encoded = _bounded_json(body)
        self._history(connection, case_id)
        scope = "asset:" + case_id
        row = connection.execute("SELECT body,result FROM platform_requests WHERE scope=? AND idempotency_key=?", (scope, key)).fetchone()
        if row:
            require(row["body"] == encoded, "idempotency_conflict")
            return json.loads(row["result"])
        total = connection.execute("SELECT COALESCE(sum(size_bytes),0) FROM platform_assets WHERE case_id=?", (case_id,)).fetchone()[0]
        require(total + len(data) <= 100 * 1024 * 1024, "asset_capacity")
        safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", filename.replace("\\", "/").split("/")[-1])[:128].strip(".") or "attachment"
        descriptor = {"asset_id": uuid.uuid4().hex, "sha256": sha256, "mime_type": mime, "size_bytes": len(data)}
        connection.execute("INSERT INTO platform_assets (asset_id,case_id,sha256,mime_type,size_bytes,filename,data) VALUES (?,?,?,?,?,?,?)",
                           (descriptor["asset_id"], case_id, sha256, mime, len(data), safe_name, data))
        connection.execute("INSERT INTO platform_requests VALUES (?,?,?,?)", (scope, key, encoded, _canonical(descriptor)))
        return descriptor

    def get_asset(self, case_id, asset_id):
        _identifier(case_id)
        _identifier(asset_id)
        with self._transaction() as connection:
            metadata = self._asset(connection, case_id, asset_id)
            data = bytes(connection.execute("SELECT data FROM platform_assets WHERE case_id=? AND asset_id=?", (case_id, asset_id)).fetchone()[0])
            require(len(data) == metadata["size_bytes"] and hashlib.sha256(data).hexdigest() == metadata["sha256"], "platform_storage_error")
            return metadata, data

    def admit_model(self, case_id, revision, snapshot_hash, callback):
        """Hold the canonical case lock across local model-job admission only.

        The callback queues a durable job; it must not dispatch a provider or
        acquire this case lock again. Linking runs after this guard releases.
        """
        _identifier(case_id)
        require(type(revision) is int and revision >= 0 and callable(callback))
        result, failure = None, None
        with self._transaction(write=True) as connection:
            current = self._history(connection, case_id)[-1]
            require(current['revision'] == revision, 'revision_conflict')
            require(current['snapshot_hash'] == snapshot_hash, 'snapshot_hash_mismatch')
            try:
                result = callback()
            except Exception as error:
                # The case transaction wraps generic ValueErrors as storage
                # failures. Preserve bounded runtime admission errors after
                # releasing this read-only guard instead.
                failure = error
        if failure is not None:
            raise failure
        return result

    def link_model(self, case_id, revision, snapshot_hash, job_id):
        _identifier(case_id)
        require(type(revision) is int and revision >= 0 and type(job_id) is str and re.fullmatch(r"[a-f0-9]{32}", job_id) is not None)
        with self._transaction(write=True) as connection:
            history = self._history(connection, case_id)
            require(revision < len(history), "revision_not_found")
            require(history[revision]["snapshot_hash"] == snapshot_hash, "snapshot_conflict")
            existing = connection.execute("SELECT case_id,revision,snapshot_hash FROM platform_model_links WHERE job_id=?", (job_id,)).fetchone()
            if existing:
                require(existing["case_id"] == case_id and existing["revision"] == revision and existing["snapshot_hash"] == snapshot_hash,
                        "idempotency_conflict")
            else:
                connection.execute("INSERT INTO platform_model_links (job_id,case_id,revision,snapshot_hash) VALUES (?,?,?,?)",
                                   (job_id, case_id, revision, snapshot_hash))
            return self._detail(connection, case_id)
