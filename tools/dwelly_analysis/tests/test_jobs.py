"""Real local PostgreSQL tests for durable model admission and recovery."""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import importlib
import os
import threading
import unittest
import uuid

try:
    jobs = importlib.import_module("tools.dwelly_analysis.jobs")
except ModuleNotFoundError:
    jobs = None

DSN = os.environ.get("PROOFKEY_TEST_DATABASE_URL")


def spec(profile_id="main", model="model-1"):
    return {"input": {"input_hash": "a" * 64, "messages": []},
            "reference": {"input_hash": "a" * 64}, "source": {"source_sha256": "b" * 64},
            "profile": {"id": profile_id, "label": profile_id,
                        "config": {"provider": "openai", "model": model}},
            "settings": {"max_output_tokens": 256, "timeout_seconds": 5},
            "profile_hash": "c" * 64, "prompt_hash": "d" * 64,
            "budget_key": "openai:" + model}


@unittest.skipUnless(DSN, "set PROOFKEY_TEST_DATABASE_URL for real PostgreSQL tests")
class AnalysisJobStoreTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(jobs, "PostgreSQL model job store is required")
        self.schema = "test_model_" + uuid.uuid4().hex
        self.addCleanup(self.drop_schema)
        jobs.migrate(DSN, schema=self.schema)
        self.store = jobs.AnalysisJobStore(DSN, schema=self.schema)
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
            connection.execute(sql.SQL("SET search_path TO {}, pg_catalog").format(sql.Identifier(self.schema)))
            cursor = connection.execute(statement, parameters)
            return cursor.fetchall() if cursor.description else None

    def submit(self, key="one", body=None, reservation="0.25", cap="1", scope="experiment"):
        return self.store.submit(key, body or spec(), Decimal(reservation), Decimal(cap), scope)

    def expire(self, job_id):
        self.sql("UPDATE model_jobs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE job_id=%s", (job_id,))

    def test_concurrent_identical_submission_reserves_once(self):
        barrier = threading.Barrier(2)
        def submit(_):
            barrier.wait()
            return self.submit()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(submit, range(2)))
        self.assertEqual({row["job_id"] for row, _ in results}, {results[0][0]["job_id"]})
        self.assertCountEqual([created for _, created in results], [True, False])
        self.assertEqual(self.sql("SELECT reserved_usd FROM model_budget_buckets"), [(Decimal("0.25"),)])
        self.assertEqual(self.sql("SELECT count(*) FROM model_jobs"), [(1,)])

    def test_conflicting_submission_does_not_reserve(self):
        self.submit()
        changed = spec()
        changed["prompt_hash"] = "e" * 64
        with self.assertRaisesRegex(ValueError, "^idempotency_conflict$"):
            self.submit(body=changed)
        with self.assertRaisesRegex(ValueError, "^idempotency_conflict$"):
            self.submit(reservation="0.3")
        self.assertEqual(self.sql("SELECT reserved_usd FROM model_budget_buckets"), [(Decimal("0.25"),)])

    def test_key_lookup_returns_frozen_job_without_another_reservation(self):
        self.assertTrue(callable(getattr(self.store, "get_by_key", None)), "idempotency lookup is required")
        first, _ = self.submit("reconnect-key")
        self.assertIsNone(self.store.get_by_key("unknown-key"))
        self.assertEqual(self.store.get_by_key("reconnect-key"), first)
        self.store.close()
        self.store = jobs.AnalysisJobStore(DSN, schema=self.schema)
        recovered = self.store.get_by_key("reconnect-key")
        self.assertEqual(recovered["job_id"], first["job_id"])
        self.assertEqual(recovered["spec"], spec())
        self.assertEqual(self.sql("SELECT reserved_usd FROM model_budget_buckets"), [(Decimal("0.25"),)])
        self.assertEqual(self.sql("SELECT count(*) FROM model_jobs"), [(1,)])

    def test_key_lookup_rejects_invalid_keys(self):
        self.assertTrue(callable(getattr(self.store, "get_by_key", None)), "idempotency lookup is required")
        for key in (None, True, "", "contains space", "x" * 129):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "^invalid_model_job$"):
                self.store.get_by_key(key)

    def test_high_precision_amount_changes_are_not_rounded_out_of_idempotency(self):
        self.submit(reservation="0.1234567890123456789012345678901")
        with self.assertRaisesRegex(ValueError, "^idempotency_conflict$"):
            self.submit(reservation="0.1234567890123456789012345678902")

    def test_failed_job_insert_rolls_back_new_budget_bucket(self):
        self.sql("ALTER TABLE model_jobs ADD CONSTRAINT test_reject CHECK (idempotency_key <> 'reject')")
        with self.assertRaisesRegex(ValueError, "^model_storage_error$"):
            self.submit("reject")
        self.assertEqual(self.sql("SELECT count(*) FROM model_budget_buckets"), [(0,)])
        self.assertEqual(self.sql("SELECT count(*) FROM model_jobs"), [(0,)])
        self.sql("ALTER TABLE model_jobs DROP CONSTRAINT test_reject")
        self.assertTrue(self.submit("reject")[1])

    def test_budget_race_is_atomic_and_scope_separates_experiments(self):
        barrier = threading.Barrier(2)
        def submit(index):
            barrier.wait()
            try:
                return self.submit(str(index), reservation="0.75")[1]
            except ValueError as error:
                return str(error)
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertCountEqual(list(pool.map(submit, range(2))), [True, "budget_exhausted"])
        self.assertEqual(self.sql("SELECT reserved_usd FROM model_budget_buckets"), [(Decimal("0.75"),)])
        self.assertTrue(self.submit("other-scope", reservation="0.75", scope="second")[1])

    def test_alias_profiles_share_provider_model_budget_and_cap_is_fixed(self):
        self.submit("main", reservation="0.75")
        with self.assertRaisesRegex(ValueError, "^budget_exhausted$"):
            self.submit("alias", spec("alias"), reservation="0.75")
        with self.assertRaisesRegex(ValueError, "^budget_cap_changed$"):
            self.submit("changed-cap", spec("alias"), cap="2")
        self.assertTrue(self.submit("other-model", spec(model="model-2"), reservation="0.75")[1])

    def test_invalid_amounts_and_alias_budget_keys_do_not_create_jobs(self):
        for reservation, cap in [("0", "1"), ("-1", "1"), ("NaN", "1"), ("Infinity", "1"),
                                 ("0.25", "25.01"), ("0.25", "0")]:
            with self.subTest(reservation=reservation, cap=cap), self.assertRaisesRegex(ValueError, "^invalid_model_job$"):
                self.submit(reservation=reservation, cap=cap)
        changed = spec()
        changed["budget_key"] = "alias-budget"
        with self.assertRaises(ValueError):
            self.submit(body=changed)
        self.assertEqual(self.sql("SELECT count(*) FROM model_jobs"), [(0,)])

    def test_valid_reservation_above_cap_is_budget_exhausted_without_writes(self):
        with self.assertRaisesRegex(ValueError, "^budget_exhausted$"):
            self.submit(reservation="2", cap="1")
        self.assertEqual(self.sql("SELECT count(*) FROM model_jobs"), [(0,)])
        self.assertEqual(self.sql("SELECT count(*) FROM model_budget_buckets"), [(0,)])

    def test_concurrent_claims_are_distinct_and_respect_global_limit(self):
        for index in range(4):
            self.submit(str(index), spec(str(index)), reservation="0.1")
        barrier = threading.Barrier(4)
        def claim(_):
            barrier.wait()
            return self.store.claim_next(max_running=3, per_profile=1)
        with ThreadPoolExecutor(max_workers=4) as pool:
            claims = [row for row in pool.map(claim, range(4)) if row]
        self.assertEqual(len(claims), 3)
        self.assertEqual(len({row["job_id"] for row in claims}), 3)
        self.assertIsNone(self.store.claim_next())

    def test_per_profile_limit_skips_busy_profile_without_blocking_others(self):
        self.submit("first")
        self.submit("second")
        third, _ = self.submit("third", spec("another"))
        self.assertEqual(self.store.claim_next()["spec"]["profile"]["id"], "main")
        self.assertEqual(self.store.claim_next()["job_id"], third["job_id"])
        self.assertIsNone(self.store.claim_next())

    def test_dispatch_is_once_and_wrong_tokens_cannot_publish(self):
        self.submit()
        claim = self.store.claim_next()
        job_id, token = claim["job_id"], claim["lease_token"]
        self.assertFalse(self.store.mark_dispatched(job_id, "bad-token"))
        self.assertTrue(self.store.mark_dispatched(job_id, token))
        self.assertFalse(self.store.mark_dispatched(job_id, token))
        self.assertFalse(self.store.record_response(job_id, "bad-token", {"text": "received"}))
        self.assertFalse(self.store.finish(job_id, "bad-token", status="failed", error="invalid_response"))
        self.assertEqual(self.store.get(job_id)["dispatch_attempts"], 1)

    def test_expired_undispatched_job_reclaims_with_new_token(self):
        self.submit()
        first = self.store.claim_next()
        self.expire(first["job_id"])
        self.store.recover_expired()
        second = self.store.claim_next()
        self.assertEqual(second["job_id"], first["job_id"])
        self.assertNotEqual(second["lease_token"], first["lease_token"])
        self.assertFalse(self.store.mark_dispatched(first["job_id"], first["lease_token"]))
        self.assertTrue(self.store.mark_dispatched(second["job_id"], second["lease_token"]))

    def test_expired_dispatched_job_is_unknown_and_never_reclaimed(self):
        self.submit()
        claim = self.store.claim_next()
        self.assertTrue(self.store.mark_dispatched(claim["job_id"], claim["lease_token"]))
        self.expire(claim["job_id"])
        self.store.recover_expired()
        row = self.store.get(claim["job_id"])
        self.assertEqual(row["status"], "outcome_unknown")
        self.assertIsNone(row["lease_token"])
        self.assertIsNotNone(row["finished_at"])
        self.assertIsNone(self.store.claim_next())
        self.assertFalse(self.store.record_response(claim["job_id"], claim["lease_token"], {"text": "late"}))
        self.assertEqual(self.sql("SELECT reserved_usd FROM model_budget_buckets"), [(Decimal("0.25"),)])

    def test_response_survives_reopen_and_is_reclaimed_for_parse_only(self):
        original, _ = self.submit()
        claim = self.store.claim_next()
        self.store.mark_dispatched(claim["job_id"], claim["lease_token"])
        self.assertTrue(self.store.record_response(claim["job_id"], claim["lease_token"], {"text": "retained"}))
        self.expire(claim["job_id"])
        self.store.close()
        self.store = jobs.AnalysisJobStore(DSN, schema=self.schema)
        recovered = self.store.claim_next()
        self.assertEqual(recovered["status"], "response_received")
        self.assertEqual(recovered["response"], {"text": "retained"})
        self.assertEqual(recovered["attempt_id"], original["attempt_id"])
        self.assertFalse(self.store.mark_dispatched(recovered["job_id"], recovered["lease_token"]))
        self.assertTrue(self.store.finish(recovered["job_id"], recovered["lease_token"], result={"candidate": "valid"}))
        self.assertEqual(self.store.get(original["job_id"])["status"], "succeeded")

    def test_terminal_result_is_immutable_and_duplicate_reads_survive_reopen(self):
        original, _ = self.submit()
        claim = self.store.claim_next()
        self.store.mark_dispatched(claim["job_id"], claim["lease_token"])
        self.store.record_response(claim["job_id"], claim["lease_token"], {"text": "retained"})
        self.assertTrue(self.store.finish(claim["job_id"], claim["lease_token"], result={"candidate": "first"}))
        self.assertFalse(self.store.finish(claim["job_id"], claim["lease_token"], result={"candidate": "changed"}))
        self.store.close()
        self.store = jobs.AnalysisJobStore(DSN, schema=self.schema)
        replay, created = self.submit()
        self.assertFalse(created)
        self.assertEqual(replay["job_id"], original["job_id"])
        self.assertEqual(replay["result"], {"candidate": "first"})
        self.assertEqual(replay["reserved_usd"], 0.25)

    def test_expired_token_cannot_store_response_or_finish_without_recovery(self):
        self.submit()
        claim = self.store.claim_next()
        self.store.mark_dispatched(claim["job_id"], claim["lease_token"])
        self.expire(claim["job_id"])
        self.assertFalse(self.store.record_response(claim["job_id"], claim["lease_token"], {"text": "late"}))
        self.assertFalse(self.store.finish(claim["job_id"], claim["lease_token"], status="failed", error="late"))

    def test_failure_retains_response_and_budget_without_success_result(self):
        self.submit()
        claim = self.store.claim_next()
        self.store.mark_dispatched(claim["job_id"], claim["lease_token"])
        self.store.record_response(claim["job_id"], claim["lease_token"], {"text": "invalid candidate"})
        self.assertTrue(self.store.finish(claim["job_id"], claim["lease_token"], status="failed", error="invalid_candidate"))
        failed = self.store.get(claim["job_id"])
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["response"], {"text": "invalid candidate"})
        self.assertIsNone(failed["result"])
        self.assertEqual(self.sql("SELECT reserved_usd FROM model_budget_buckets"), [(Decimal("0.25"),)])

    def test_explicit_migration_and_closed_store_errors_are_sanitized(self):
        jobs.migrate(DSN, schema=self.schema)
        self.assertTrue(self.submit()[1])
        self.store.close()
        with self.assertRaisesRegex(ValueError, "^model_storage_error$"):
            self.store.get("a" * 32)
        with self.assertRaises(KeyError):
            jobs.AnalysisJobStore(DSN, schema=self.schema).get("invalid")
        with self.assertRaisesRegex(ValueError, "^model_storage_error$"):
            jobs.AnalysisJobStore("not-a-connection-sentinel-private-value", schema=self.schema)


if __name__ == "__main__":
    unittest.main()
