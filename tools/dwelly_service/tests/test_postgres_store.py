"""Real PostgreSQL contracts; opt in with PROOFKEY_TEST_DATABASE_URL."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
import importlib
import json
import logging
import os
from pathlib import Path
import subprocess
import socket
import sys
import tempfile
import threading
import unittest
import uuid
from unittest.mock import patch

from tools.dwelly_service.cases import CaseError, CaseStore
from tools.dwelly_service.store import JobStore
from tools.dwelly_service.tests.test_cases import declaration, event

try:
    postgres = importlib.import_module("tools.dwelly_service.postgres")
except ModuleNotFoundError:
    postgres = None

DSN = os.environ.get("PROOFKEY_TEST_DATABASE_URL")


@unittest.skipIf(postgres is None and not DSN, "PostgreSQL logging tests require optional PostgreSQL dependencies")
class PostgresLoggingTests(unittest.TestCase):
    def test_malformed_connection_strings_never_reach_pool_logs(self):
        self.assertIsNotNone(postgres)
        logger = logging.getLogger("psycopg.pool")
        for value in ("sentinel_private_password", "postgresql://localhost/db?sentinel_private_option=yes"):
            with self.subTest(value=value), self.assertLogs(logger, level="DEBUG") as captured:
                with self.assertRaisesRegex(CaseError, "^case_storage_error$"):
                    postgres.PostgresCaseStore(value, max_size=1)
                logger.warning("unrelated_external_pool_warning")
            output = "\n".join(captured.output)
            self.assertNotIn("sentinel_private", output)
            self.assertIn("unrelated_external_pool_warning", output)

    def test_real_pool_connect_reconnect_timeout_and_close_logs_are_content_free(self):
        self.assertIsNotNone(postgres)
        from psycopg_pool import ConnectionPool
        logger = logging.getLogger("psycopg")
        with socket.socket() as reserved:
            reserved.bind(("127.0.0.1", 0))
            port = reserved.getsockname()[1]
            reserved.close()
            def short_pool(*args, **kwargs):
                kwargs.update(timeout=2, reconnect_timeout=0.1)
                return ConnectionPool(*args, **kwargs)
            with patch.object(postgres, "ConnectionPool", short_pool), self.assertLogs(logger, level="DEBUG") as captured:
                with self.assertRaisesRegex(CaseError, "^case_storage_error$"):
                    postgres.PostgresCaseStore(f"postgresql://sentinel_private_user:sentinel_private_password@127.0.0.1:{port}/sentinel_private_db", max_size=1)
                logger.warning("unrelated_external_pool_warning")
        output = "\n".join(captured.output)
        self.assertNotIn("sentinel_private", output)
        self.assertNotIn(str(port), output)
        self.assertNotIn("127.0.0.1", output)
        self.assertIn("unrelated_external_pool_warning", output)
        self.assertIn("proofkey_database_pool_event", output)
        self.assertTrue(any(record.levelno >= logging.WARNING and record.getMessage() == "proofkey_database_pool_event"
                            for record in captured.records))


@unittest.skipUnless(DSN, "set PROOFKEY_TEST_DATABASE_URL for real PostgreSQL tests")
class PostgresStoreTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(postgres, "PostgreSQL case storage must be implemented")
        self.schema = "test_" + uuid.uuid4().hex
        self.addCleanup(self.drop_schema)
        postgres.migrate(DSN, schema=self.schema)
        self.store = postgres.PostgresCaseStore(DSN, schema=self.schema, max_size=2)
        self.addCleanup(lambda: self.store.close())

    def drop_schema(self):
        import psycopg
        from psycopg import sql
        with psycopg.connect(DSN, autocommit=True) as connection:
            connection.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(self.schema)))

    def sql(self, statement, parameters=()):
        import psycopg
        from psycopg import sql
        with psycopg.connect(DSN) as connection:
            connection.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(self.schema)))
            return connection.execute(statement, parameters).fetchall() if statement.lstrip().upper().startswith("SELECT") else connection.execute(statement, parameters)

    def test_snapshots_match_sqlite_and_survive_restart_with_exact_retries(self):
        with tempfile.TemporaryDirectory() as directory:
            owner = JobStore(Path(directory).resolve())
            self.addCleanup(owner.close)
            sqlite = CaseStore(owner)
            for target in (sqlite, self.store):
                target.create("create", declaration())
                target.append("demo-1", "append", event())
            for revision in (0, 1):
                self.assertEqual(self.store.get("demo-1", revision), sqlite.get("demo-1", revision))
                with owner._connect() as connection:
                    original_text = connection.execute("SELECT snapshot FROM case_snapshots WHERE revision=?", (revision,)).fetchone()[0]
                self.assertEqual(self.sql("SELECT snapshot FROM case_snapshots WHERE revision=%s", (revision,))[0][0], original_text)
            original = self.store.get("demo-1", 0)
            self.store.close()
            self.store = postgres.PostgresCaseStore(DSN, schema=self.schema, max_size=2)
            self.assertEqual(self.store.create("create", declaration()), (original, False))
            self.assertEqual(self.store.append("demo-1", "append", event())[1], False)
            self.assertEqual(len(self.store.analysis_jobs("demo-1")), 2)

    def test_competing_appends_commit_one_revision_and_one_intent(self):
        self.store.create("create", declaration())
        barrier = threading.Barrier(2)
        def append(index):
            barrier.wait()
            try:
                return self.store.append("demo-1", "append-" + str(index), event("event-" + str(index)))[0]["revision"]
            except CaseError as error:
                return error.code
        with ThreadPoolExecutor(max_workers=2) as executor:
            self.assertCountEqual(list(executor.map(append, (1, 2))), [1, "revision_conflict"])
        self.assertEqual(len(self.store.analysis_jobs("demo-1")), 2)

    def test_outbox_failure_rolls_back_snapshot_head_and_idempotency(self):
        self.store.create("create", declaration())
        self.sql("ALTER TABLE analysis_outbox ADD CONSTRAINT reject_new CHECK (revision = 0)")
        with self.assertRaisesRegex(CaseError, "^case_storage_error$"):
            self.store.append("demo-1", "append", event())
        self.assertEqual(self.store.get("demo-1")["revision"], 0)
        self.assertEqual(len(self.store.analysis_jobs("demo-1")), 1)
        self.sql("ALTER TABLE analysis_outbox DROP CONSTRAINT reject_new")
        self.assertTrue(self.store.append("demo-1", "append", event())[1])

    def test_expired_lease_is_reclaimed_and_old_token_cannot_ack(self):
        self.store.create("create", declaration())
        first = self.store.claim_analysis("worker-1", lease_seconds=60)
        self.assertIsNotNone(first)
        self.assertIsNone(self.store.claim_analysis("worker-2"))
        self.assertFalse(self.store.ack_analysis(first["job_id"], "bad-token"))
        self.sql("UPDATE analysis_outbox SET lease_expires_at = clock_timestamp() - interval '1 second'")
        self.assertFalse(self.store.ack_analysis(first["job_id"], first["lease_token"]))
        self.store.close()
        self.store = postgres.PostgresCaseStore(DSN, schema=self.schema, max_size=2)
        second = self.store.claim_analysis("worker-2")
        self.assertEqual(second["job_id"], first["job_id"])
        self.assertNotEqual(second["lease_token"], first["lease_token"])
        self.assertFalse(self.store.ack_analysis(first["job_id"], first["lease_token"]))
        self.assertTrue(self.store.ack_analysis(second["job_id"], second["lease_token"]))
        self.assertFalse(self.store.ack_analysis(second["job_id"], second["lease_token"]))
        self.assertEqual(self.store.analysis_jobs("demo-1")[0]["status"], "completed")

    def test_parallel_claims_are_distinct_and_public_metadata_hides_leases(self):
        self.store.create("create", declaration())
        self.store.append("demo-1", "append", event())
        with ThreadPoolExecutor(max_workers=2) as executor:
            claims = list(executor.map(self.store.claim_analysis, ("worker-1", "worker-2")))
        self.assertEqual(len({claim["job_id"] for claim in claims}), 2)
        for row in self.store.analysis_jobs("demo-1"):
            self.assertEqual(set(row), {"job_id", "case_id", "revision", "snapshot_hash", "status"})
            self.assertEqual(row["snapshot_hash"], self.store.get("demo-1", row["revision"])["snapshot_hash"])

    def test_migrations_are_explicit_idempotent_and_schema_names_are_validated(self):
        postgres.migrate(DSN, schema=self.schema)
        self.store.check_ready()
        for invalid in ("public;DROP SCHEMA public", "a.b", "", None, "a" * 64):
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(ValueError, "^invalid_database_schema$"):
                    postgres.PostgresCaseStore(DSN, schema=invalid)
        for size in (0, -1, True, 129):
            with self.subTest(size=size):
                with self.assertRaisesRegex(ValueError, "^invalid_database_pool$"):
                    postgres.PostgresCaseStore(DSN, schema=self.schema, max_size=size)

    def test_closed_store_fails_with_sanitized_error(self):
        self.store.close()
        with self.assertRaisesRegex(CaseError, "^case_storage_error$"):
            self.store.check_ready()

    def test_independent_pools_commit_one_exact_retry_and_one_intent(self):
        second = postgres.PostgresCaseStore(DSN, schema=self.schema, max_size=1)
        self.addCleanup(second.close)
        barrier = threading.Barrier(2)
        def create(store):
            barrier.wait()
            return store.create("same-key", declaration())
        with ThreadPoolExecutor(max_workers=2) as executor:
            first, other = list(executor.map(create, (self.store, second)))
        self.assertEqual(first[0], other[0])
        self.assertCountEqual([first[1], other[1]], [True, False])
        self.assertEqual(len(second.analysis_jobs("demo-1")), 1)

    def test_bounded_pool_blocks_a_third_borrower(self):
        from psycopg_pool import PoolTimeout
        with ExitStack() as stack:
            stack.enter_context(self.store.pool.connection())
            stack.enter_context(self.store.pool.connection())
            with self.assertRaises(PoolTimeout):
                with self.store.pool.connection(timeout=0.02):
                    self.fail("third connection exceeds max_size=2")
        self.store.check_ready()

    def test_constructor_never_migrates_a_missing_schema(self):
        absent = "absent_" + uuid.uuid4().hex
        with self.assertRaisesRegex(CaseError, "^case_storage_error$"):
            postgres.PostgresCaseStore(DSN, schema=absent, max_size=1)
        self.assertEqual(self.sql("SELECT schema_name FROM information_schema.schemata WHERE schema_name=%s", (absent,)), [])

    def test_invalid_lease_inputs_and_corrupt_snapshots_are_rejected(self):
        self.store.create("create", declaration())
        for duration in (0, -1, True, "60", 3601):
            with self.subTest(duration=duration):
                with self.assertRaisesRegex(CaseError, "^invalid_case_request$"):
                    self.store.claim_analysis("worker", lease_seconds=duration)
        self.assertEqual(self.store.analysis_jobs("demo-1")[0]["status"], "pending")
        self.sql("UPDATE case_snapshots SET snapshot='private corrupt content'")
        with self.assertRaisesRegex(CaseError, "^case_storage_error$"):
            self.store.get("demo-1")
        with self.assertRaisesRegex(CaseError, "^case_storage_error$"):
            self.store.analysis_jobs("demo-1")

    def test_outbox_corruption_cannot_be_exposed_or_claimed_as_valid_work(self):
        self.store.create("create", declaration())
        self.sql("UPDATE analysis_outbox SET snapshot_hash=%s", ("f" * 64,))
        with self.assertRaisesRegex(CaseError, "^case_storage_error$"):
            self.store.analysis_jobs("demo-1")
        with self.assertRaisesRegex(CaseError, "^case_storage_error$"):
            self.store.claim_analysis("worker")
        self.assertEqual(self.sql("SELECT status FROM analysis_outbox"), [("pending",)])

    def test_separate_processes_share_idempotency_and_durable_intents(self):
        script = """import json, os, sys
from tools.dwelly_service.postgres import PostgresCaseStore
store = PostgresCaseStore(os.environ['PROOFKEY_TEST_DATABASE_URL'], schema=sys.argv[1], max_size=1)
try:
    snapshot, created = store.create('process-retry', json.loads(sys.argv[2]))
    print(json.dumps({'created': created, 'snapshot_hash': snapshot['snapshot_hash']}))
finally:
    store.close()
"""
        args = [sys.executable, "-c", script, self.schema, json.dumps(declaration())]
        processes = [subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(2)]
        results = []
        for process in processes:
            stdout, stderr = process.communicate(timeout=30)
            self.assertEqual(process.returncode, 0, stderr)
            results.append(json.loads(stdout))
        self.assertCountEqual([row["created"] for row in results], [True, False])
        self.assertEqual(results[0]["snapshot_hash"], results[1]["snapshot_hash"])
        self.assertEqual(len(self.store.analysis_jobs("demo-1")), 1)

    def test_broken_connection_cleanup_does_not_log_connection_details(self):
        self.store.create("create", declaration())
        with self.assertLogs("psycopg", level="DEBUG") as captured:
            with self.store._transaction() as connection:
                connection.connection.close()
            self.store.close()
        self.assertTrue(any(record.levelno >= logging.WARNING for record in captured.records))
        for record in captured.records:
            self.assertEqual(record.getMessage(), "proofkey_database_pool_event")
