"""Real HTTP over real PostgreSQL; skipped unless the disposable test DSN is set."""
import contextlib
import http.client
import io
import json
import os
import threading
import unittest
import uuid


DSN = os.environ.get("PROOFKEY_TEST_DATABASE_URL")


@unittest.skipUnless(DSN, "set PROOFKEY_TEST_DATABASE_URL to a disposable PostgreSQL database")
class PostgresHTTPTests(unittest.TestCase):
    def setUp(self):
        from tools.dwelly_service import case_api
        from tools.dwelly_service.postgres import PostgresCaseStore, migrate
        self.api = case_api
        self.schema = "http_test_" + uuid.uuid4().hex
        migrate(DSN, schema=self.schema)
        self.store = PostgresCaseStore(DSN, schema=self.schema)
        self.addCleanup(self.drop_schema)
        self.token = "test-only-not-a-real-service-secret"
        self.start()
        self.addCleanup(self.stop)

    def drop_schema(self):
        import psycopg
        from psycopg import sql
        self.store.close()
        with psycopg.connect(DSN) as conn:
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.schema)))

    def start(self):
        self.server = self.api.create_case_server(self.store, token=self.token, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
            self.thread.join(3)
            self.server = None

    def request(self, method, path, body=None, *, headers=None, auth=True):
        payload = json.dumps(body) if isinstance(body, (dict, list)) else body
        fields = {"Content-Type": "application/json"}
        if auth:
            fields["Authorization"] = "Bearer " + self.token
        fields.update(headers or {})
        client = http.client.HTTPConnection(*self.server.server_address, timeout=6)
        try:
            client.request(method, path, payload, fields)
            response = client.getresponse()
            return response.status, json.loads(response.read())
        finally:
            client.close()

    @staticmethod
    def declaration():
        return {"case_id": "sample", "links": {"order_id": "order", "customer_id": "customer",
                "operator_id": "operator"}, "participants": ["customer", "operator"], "language": "en"}

    @staticmethod
    def event(event_id="msg1", revision=0):
        return {"expected_revision": revision, "event": {"event_id": event_id,
                "occurred_at": "2026-10-10T10:00:00Z", "channel": "chat", "sender_id": "customer",
                "recipient_ids": ["operator"], "kind": "message", "text": "Please reschedule.", "media": None}}

    def create(self, body=None, key="create"):
        return self.request("POST", "/v1/cases", self.declaration() if body is None else body,
                            headers={"Idempotency-Key": key})

    def append(self, body=None, key="append"):
        return self.request("POST", "/v1/cases/sample/events", self.event() if body is None else body,
                            headers={"Idempotency-Key": key})

    def test_case_history_and_exact_retries_survive_new_api_and_pool(self):
        status, first = self.create()
        self.assertEqual(status, 201)
        status, second = self.append()
        self.assertEqual(status, 201)
        self.assertEqual(second["previous_snapshot_hash"], first["snapshot_hash"])
        self.assertEqual(second["analysis_status"], "pending_not_started")
        self.assertEqual(second["authorization"], "unverified")
        self.assertEqual(second["operational_effects"], 0)
        self.stop()
        from tools.dwelly_service.postgres import PostgresCaseStore
        self.store = PostgresCaseStore(DSN, schema=self.schema)
        self.start()
        self.assertEqual(self.create(), (200, first))
        self.assertEqual(self.append(), (200, second))
        self.assertEqual(self.request("GET", "/v1/cases/sample?revision=0"), (200, first))
        self.assertEqual(self.request("GET", "/v1/cases/sample"), (200, second))

    def test_authority_auth_origin_and_route_boundaries(self):
        self.assertEqual(self.request("GET", "/healthz", auth=False), (200, {"status": "ok"}))
        self.assertEqual(self.request("GET", "/readyz", auth=False), (200, {"status": "ready"}))
        self.assertEqual(self.request("GET", "/v1/capabilities", auth=False)[0], 401)
        for headers in ({"Host": "evil.example"}, {"Origin": "null"}, {"Origin": "https://evil.example"}):
            self.assertEqual(self.request("GET", "/v1/capabilities", headers=headers)[0], 403)
        for path in ("/v1/jobs", "/v1/cases/sample/events/extra", "/v1/cases/%73ample", "/v1/cases"):
            self.assertEqual(self.request("GET", path)[0], 404)
        self.assertEqual(self.request("POST", "/v1/jobs", {})[0], 404)

    def test_outbox_is_pending_and_contains_no_lease_or_evaluator_data(self):
        self.assertEqual(self.create()[0], 201)
        self.assertEqual(self.append()[0], 201)
        status, response = self.request("GET", "/v1/cases/sample/analysis-jobs")
        self.assertEqual(status, 200)
        self.assertEqual(set(response), {"case_id", "jobs", "operational_effects"})
        self.assertEqual(len(response["jobs"]), 2)
        self.assertTrue(all(job["status"] == "pending" for job in response["jobs"]))
        self.assertEqual(response["operational_effects"], 0)
        encoded = json.dumps(response)
        for forbidden in ("lease_token", "lease_owner", "rationale", "expected_disposition", "criteria", "postgresql://"):
            self.assertNotIn(forbidden, encoded)
        capabilities = self.request("GET", "/v1/capabilities")[1]
        self.assertEqual(capabilities["storage"], "postgresql")
        self.assertFalse(capabilities["case_intake"]["automated_analysis"])

    def test_validation_and_conflicts_keep_public_error_contract(self):
        for body in ("{", '{"case_id":"a","case_id":"b"}', [], {}, self.declaration() | {"language": "ru"}):
            self.assertEqual(self.create(body), (400, {"error": "invalid_case_request"}))
        self.assertEqual(self.create()[0], 201)
        self.assertEqual(self.create(self.declaration() | {"language": "fr"})[0], 400)
        self.assertEqual(self.append()[0], 201)
        self.assertEqual(self.append(self.event("msg2"), "different"), (409, {"error": "revision_conflict"}))
        self.assertEqual(self.request("GET", "/v1/cases/absent"), (404, {"error": "case_not_found"}))
        self.assertEqual(self.request("GET", "/v1/cases/sample?revision=9"), (404, {"error": "revision_not_found"}))
        self.assertEqual(self.request("GET", "/v1/cases/sample?revision=00"), (400, {"error": "invalid_case_request"}))
        self.assertEqual(self.request("POST", "/v1/cases", self.declaration()), (400, {"error": "invalid_case_request"}))

    def test_media_metadata_does_not_imply_upload_or_analysis(self):
        self.assertEqual(self.create()[0], 201)
        event = self.event()
        event["event"].update(kind="photo", text=None, media={"asset_id": "photo1", "sha256": "a" * 64,
                               "mime_type": "image/png", "size_bytes": 20})
        status, snapshot = self.append(event)
        self.assertEqual(status, 201)
        self.assertIsNone(snapshot["events"][0]["text"])
        self.assertEqual(snapshot["analysis_status"], "pending_not_started")
        self.assertIsNone(snapshot["runtime_binding"])

    def test_closed_store_readiness_and_requests_fail_without_private_detail(self):
        self.assertEqual(self.create()[0], 201)
        self.store.close()
        self.assertEqual(self.request("GET", "/healthz", auth=False)[0], 200)
        self.assertEqual(self.request("GET", "/readyz", auth=False), (503, {"error": "storage_unavailable"}))
        self.assertEqual(self.request("GET", "/v1/cases/sample"), (503, {"error": "case_storage_error"}))

    def test_failed_bind_does_not_close_the_callers_store_or_hide_the_error(self):
        with self.assertRaises(OSError):
            self.api.create_case_server(self.store, token=self.token,
                                        port=self.server.server_address[1])
        self.assertEqual(self.create()[0], 201)


class ConfigurationTests(unittest.TestCase):
    def test_cli_rejects_missing_or_invalid_configuration_without_echoing_input(self):
        from tools.dwelly_service.case_api import main
        for env in ({}, {"PROOFKEY_DATABASE_URL": "postgresql://user:private@host/db", "PROOFKEY_DB_POOL_MAX": "secret"}):
            with self.subTest(env_keys=list(env)):
                from unittest.mock import patch
                out, err = io.StringIO(), io.StringIO()
                with patch.dict(os.environ, env, clear=True), contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
                    self.assertNotEqual(main(["serve"]), 0)
                self.assertNotIn("private", err.getvalue() + out.getvalue())
                self.assertNotIn("secret", err.getvalue() + out.getvalue())


if __name__ == "__main__":
    unittest.main()
