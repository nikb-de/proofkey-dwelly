"""Case intake through real loopback HTTP and the durable local store."""
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from tools.dwelly_cases.importer import import_cases
from tools.dwelly_cases.tests.fixtures import make_source
from tools.dwelly_model.tests.test_runner import config
from tools.dwelly_service import server as server_module


def case_body(case_id="demo-1"):
    return {"case_id": case_id,
            "links": {"order_id": "order-1", "customer_id": "customer-1", "operator_id": "operator-1"},
            "participants": ["customer-1", "operator-1", "courier-1"], "language": "en"}


def event_body(event_id="event-1", revision=0):
    return {"expected_revision": revision,
            "event": {"event_id": event_id, "occurred_at": "2026-10-10T10:00:00Z", "channel": "chat",
                      "sender_id": "customer-1", "recipient_ids": ["operator-1"], "kind": "message",
                      "text": "Please move my delivery to tomorrow.", "media": None}}


class CaseHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        source = self.root / "source"
        make_source(source)
        self.bundle = self.root / "bundle"
        import_cases(source, self.bundle, expected_cases=1)
        self.config = self.root / "config.json"
        self.config.write_text(json.dumps(config()))
        self.state = self.root / "state"
        self.token = "local-case-test-token-with-enough-entropy"
        self.server = None
        self.start_server()
        self.addCleanup(self.stop_server)

    def start_server(self):
        self.server = server_module.create_server(self.bundle, self.config, self.state,
                                                  token=self.token, port=0, start_worker=False)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop_server(self):
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
            self.thread.join(2)
            self.server = None

    def request(self, method, target, body=None, headers=None, auth=True):
        payload = json.dumps(body) if isinstance(body, (dict, list)) else body
        actual = {"Content-Type": "application/json"}
        if auth:
            actual["Authorization"] = "Bearer " + self.token
        actual.update(headers or {})
        client = http.client.HTTPConnection(*self.server.server_address, timeout=5)
        try:
            client.request(method, target, payload, actual)
            response = client.getresponse()
            return response.status, json.loads(response.read())
        finally:
            client.close()

    def create_case(self, key="create-1", body=None):
        return self.request("POST", "/v1/cases", case_body() if body is None else body,
                            {"Idempotency-Key": key})

    def append_event(self, key="append-1", body=None, case_id="demo-1"):
        return self.request("POST", f"/v1/cases/{case_id}/events",
                            event_body() if body is None else body, {"Idempotency-Key": key})

    def raw_request(self, method, target, body="{}", headers=()):
        client = http.client.HTTPConnection(*self.server.server_address, timeout=5)
        try:
            client.putrequest(method, target)
            client.putheader("Authorization", "Bearer " + self.token)
            client.putheader("Content-Type", "application/json")
            client.putheader("Content-Length", str(len(body.encode())))
            for name, value in headers:
                client.putheader(name, value)
            client.endheaders(body.encode())
            response = client.getresponse()
            return response.status, json.loads(response.read())
        finally:
            client.close()

    def test_new_case_returns_pending_snapshot_and_exact_retry_returns_original(self):
        status, first = self.create_case()
        self.assertEqual(status, 201)
        self.assertEqual(first["case_id"], "demo-1")
        self.assertEqual(first["revision"], 0)
        self.assertEqual(first["events"], [])
        self.assertEqual(first["source_mode"], "local_fixture")
        self.assertIsNone(first["runtime_binding"])
        self.assertTrue(first["needs_analysis"])
        self.assertEqual(first["analysis_status"], "pending_not_started")
        self.assertEqual(first["authorization"], "unverified")
        self.assertEqual(first["operational_effects"], 0)
        self.assertIsNone(first["previous_snapshot_hash"])
        self.assertRegex(first["snapshot_hash"], r"^[a-f0-9]{64}$")
        self.assertEqual(self.create_case(), (200, first))

    def test_append_keeps_prior_snapshot_and_retries_original_revision(self):
        status, first = self.create_case()
        self.assertEqual(status, 201)
        status, second = self.append_event()
        self.assertEqual(status, 201)
        self.assertEqual(second["revision"], 1)
        self.assertEqual(second["previous_snapshot_hash"], first["snapshot_hash"])
        self.assertNotEqual(second["snapshot_hash"], first["snapshot_hash"])
        self.assertEqual(len(second["events"]), 1)
        self.assertEqual(second["events"][0]["text"], "Please move my delivery to tomorrow.")
        status, third = self.append_event("append-2", event_body("event-2", 1))
        self.assertEqual((status, third["revision"]), (201, 2))
        self.assertEqual(self.request("GET", "/v1/cases/demo-1"), (200, third))
        self.assertEqual(self.request("GET", "/v1/cases/demo-1?revision=0"), (200, first))
        self.assertEqual(self.request("GET", "/v1/cases/demo-1?revision=1"), (200, second))
        self.assertEqual(self.create_case(), (200, first))
        self.assertEqual(self.append_event(), (200, second))

    def test_idempotent_results_survive_server_restart(self):
        status, first = self.create_case()
        self.assertEqual(status, 201)
        status, second = self.append_event()
        self.assertEqual(status, 201)
        self.stop_server()
        self.start_server()
        self.assertEqual(self.create_case(), (200, first))
        self.assertEqual(self.append_event(), (200, second))
        self.assertEqual(self.request("GET", "/v1/cases/demo-1"), (200, second))

    def test_supported_media_metadata_stays_pending_without_a_fabricated_transcript(self):
        self.assertEqual(self.create_case()[0], 201)
        for revision, (kind, mime_type, size) in enumerate((
                ("photo", "image/jpeg", 10 * 1024 * 1024),
                ("voice_message", "audio/mpeg", 25 * 1024 * 1024),
                ("call_recording", "audio/wav", 25 * 1024 * 1024))):
            body = event_body("media-" + str(revision), revision)
            body["event"].update({"kind": kind, "text": None, "media": {
                "asset_id": "asset-" + str(revision), "sha256": "a" * 64,
                "mime_type": mime_type, "size_bytes": size}})
            status, snapshot = self.append_event("media-" + str(revision), body)
            self.assertEqual(status, 201)
            self.assertEqual(snapshot["events"][-1]["media"], body["event"]["media"])
            self.assertIsNone(snapshot["events"][-1]["text"])
            self.assertEqual(snapshot["analysis_status"], "pending_not_started")
            self.assertEqual(snapshot["operational_effects"], 0)

    def test_case_and_revision_misses_are_distinct_content_free_errors(self):
        self.assertEqual(self.request("GET", "/v1/cases/unknown"),
                         (404, {"error": "case_not_found"}))
        self.assertEqual(self.append_event(case_id="unknown"),
                         (404, {"error": "case_not_found"}))
        self.assertEqual(self.create_case()[0], 201)
        for revision in (1, 99999999999999999999999999999999999999999):
            with self.subTest(revision=revision):
                self.assertEqual(self.request("GET", f"/v1/cases/demo-1?revision={revision}"),
                                 (404, {"error": "revision_not_found"}))

    def test_queries_require_one_canonical_nonnegative_revision(self):
        self.assertEqual(self.create_case()[0], 201)
        for query in ("revision=", "revision=-1", "revision=+1", "revision=00", "revision=01",
                      "revision=1.0", "revision=true", "revision=0&revision=0", "revision=0&x=1",
                      "x=1", "revision=%30", "%72evision=0", "revision=0;foo=1", "revision=0#fragment"):
            with self.subTest(query=query):
                self.assertEqual(self.request("GET", "/v1/cases/demo-1?" + query),
                                 (400, {"error": "invalid_case_request"}))

    def test_case_routes_do_not_accept_extra_segments_encoded_ids_or_post_queries(self):
        for method, target in (("GET", "/v1/cases"), ("GET", "/v1/cases/demo-1/events"),
                               ("GET", "/v1/cases/../secret"), ("GET", "/v1/cases/%64emo-1"),
                               ("GET", "/v1/cases/demo-1/"), ("POST", "/v1/cases?revision=0"),
                               ("POST", "/v1/cases/demo-1/events?revision=0"),
                               ("POST", "/v1/cases/demo-1/events/extra")):
            with self.subTest(method=method, target=target):
                self.assertEqual(self.request(method, target, {} if method == "POST" else None)[0], 404)

    def test_case_routes_reuse_authentication_host_and_origin_guards(self):
        for method, target, body in (("POST", "/v1/cases", case_body()),
                                     ("POST", "/v1/cases/demo-1/events", event_body()),
                                     ("GET", "/v1/cases/demo-1", None)):
            with self.subTest(method=method, target=target):
                self.assertEqual(self.request(method, target, body, auth=False),
                                 (401, {"error": "unauthorized"}))
                self.assertEqual(self.request(method, target, body, {"Host": "evil.example"}),
                                 (403, {"error": "forbidden"}))
                self.assertEqual(self.request(method, target, body, {"Origin": "https://evil.example"}),
                                 (403, {"error": "forbidden"}))
        self.assertEqual(self.raw_request("POST", "/v1/cases", json.dumps(case_body()),
                                         (("Authorization", "Bearer " + self.token),))[0], 401)

    def test_case_posts_require_exactly_one_valid_idempotency_key(self):
        for target, body in (("/v1/cases", case_body()), ("/v1/cases/demo-1/events", event_body())):
            for key in (None, "", "space invalid", "a" * 129, "key/invalid"):
                with self.subTest(target=target, key=key):
                    headers = {} if key is None else {"Idempotency-Key": key}
                    self.assertEqual(self.request("POST", target, body, headers),
                                     (400, {"error": "invalid_case_request"}))
            self.assertEqual(self.raw_request("POST", target, json.dumps(body),
                                             (("Idempotency-Key", "one"), ("Idempotency-Key", "two"))),
                             (400, {"error": "invalid_case_request"}))

    def test_case_posts_reject_malformed_json_and_closed_contract_violations(self):
        invalid_create = ["{", '{"case_id":"a","case_id":"b"}', '{"case_id":NaN}', [], {},
                          case_body() | {"private_path": "/private/secret"},
                          case_body() | {"language": "ru"}]
        for index, body in enumerate(invalid_create):
            with self.subTest(body=body):
                self.assertEqual(self.create_case("invalid-" + str(index), body),
                                 (400, {"error": "invalid_case_request"}))
        self.assertEqual(self.create_case()[0], 201)
        bad_sender = event_body()
        bad_sender["event"]["sender_id"] = "outsider"
        bad_media = event_body()
        bad_media["event"].update({"kind": "photo", "text": None, "media": {
            "asset_id": "asset-1", "sha256": "a" * 64, "mime_type": "image/png", "size_bytes": 10,
            "url": "https://private.example/secret"}})
        for index, body in enumerate(({}, {"expected_revision": False, "event": event_body()["event"]},
                                      bad_sender, bad_media)):
            with self.subTest(body=body):
                self.assertEqual(self.append_event("bad-append-" + str(index), body),
                                 (400, {"error": "invalid_case_request"}))
        self.assertEqual(self.request("GET", "/v1/cases/demo-1")[1]["revision"], 0)

    def test_case_posts_keep_existing_body_limit_and_content_type_errors(self):
        for target in ("/v1/cases", "/v1/cases/demo-1/events"):
            with self.subTest(target=target):
                self.assertEqual(self.request("POST", target, "x" * 16385,
                                              {"Idempotency-Key": "large"}),
                                 (413, {"error": "request_too_large"}))
                self.assertEqual(self.request("POST", target, "{}",
                                              {"Idempotency-Key": "type", "Content-Type": "text/plain"}),
                                 (415, {"error": "unsupported_media_type"}))
                self.assertEqual(self.raw_request("POST", target, "{}",
                                                 (("Idempotency-Key", "length"), ("Content-Length", "2"))),
                                 (400, {"error": "invalid_case_request"}))

    def test_conflicts_return_409_without_changing_the_current_snapshot(self):
        self.assertEqual(self.create_case()[0], 201)
        changed = case_body() | {"participants": ["customer-1", "operator-1"]}
        self.assertEqual(self.create_case(body=changed), (409, {"error": "idempotency_conflict"}))
        self.assertEqual(self.create_case("another-key"), (409, {"error": "idempotency_conflict"}))
        status, first_event = self.append_event()
        self.assertEqual(status, 201)
        self.assertEqual(self.append_event(body=event_body("event-2", 0)),
                         (409, {"error": "idempotency_conflict"}))
        self.assertEqual(self.append_event("duplicate-event", event_body("event-1", 1)),
                         (409, {"error": "event_conflict"}))
        self.assertEqual(self.append_event("stale-revision", event_body("event-2", 0)),
                         (409, {"error": "revision_conflict"}))
        self.assertEqual(self.request("GET", "/v1/cases/demo-1"), (200, first_event))

    def test_concurrent_appends_commit_only_one_of_the_same_expected_revision(self):
        self.assertEqual(self.create_case()[0], 201)
        barrier = threading.Barrier(3)
        results = []

        def append(index):
            barrier.wait()
            results.append(self.append_event("race-" + str(index), event_body("race-" + str(index))))

        threads = [threading.Thread(target=append, args=(index,)) for index in range(2)]
        for thread in threads:
            thread.start()
        barrier.wait()
        for thread in threads:
            thread.join(5)
            self.assertFalse(thread.is_alive())
        self.assertEqual(sorted(status for status, _ in results), [201, 409])
        self.assertEqual(next(body for status, body in results if status == 409),
                         {"error": "revision_conflict"})
        snapshot = self.request("GET", "/v1/cases/demo-1")[1]
        self.assertEqual((snapshot["revision"], len(snapshot["events"])), (1, 1))

    def test_capacity_errors_are_429_and_existing_retries_still_work(self):
        status, first = self.create_case()
        self.assertEqual(status, 201)
        for index in range(1, 256):
            self.server.cases.create("fill-" + str(index), case_body("case-" + str(index)))
        self.assertEqual(self.create_case("overflow", case_body("overflow")),
                         (429, {"error": "case_capacity"}))
        self.assertEqual(self.create_case(), (200, first))
        status, first_event = self.append_event()
        self.assertEqual(status, 201)
        for revision in range(1, 128):
            self.server.cases.append("demo-1", "fill-event-" + str(revision),
                                     event_body("event-" + str(revision + 1), revision))
        self.assertEqual(self.append_event("overflow-event", event_body("event-129", 128)),
                         (429, {"error": "case_capacity"}))
        self.assertEqual(self.append_event(), (200, first_event))

    def test_corrupt_persisted_snapshot_fails_closed_without_private_content(self):
        self.assertEqual(self.create_case()[0], 201)
        with self.server.store._connect() as connection:
            connection.execute("UPDATE case_snapshots SET snapshot=? WHERE case_id=? AND revision=0",
                               ('{"private_secret":"must not escape"}', "demo-1"))
        for method, target, body in (("GET", "/v1/cases/demo-1", None),
                                     ("POST", "/v1/cases/demo-1/events", event_body())):
            with self.subTest(method=method):
                self.assertEqual(self.request(method, target, body, {"Idempotency-Key": "corrupt"}),
                                 (503, {"error": "case_storage_error"}))

    def test_corrupt_database_returns_sanitized_case_storage_error(self):
        (self.state / "queue.sqlite3").write_bytes(b"private damaged sqlite content")
        for method, target, body in (("GET", "/v1/cases/demo-1", None),
                                     ("POST", "/v1/cases", case_body()),
                                     ("POST", "/v1/cases/demo-1/events", event_body())):
            with self.subTest(method=method, target=target):
                self.assertEqual(self.request(method, target, body, {"Idempotency-Key": "corrupt"}),
                                 (503, {"error": "case_storage_error"}))

    def test_intake_never_submits_jobs_starts_worker_or_uses_provider_budget(self):
        with patch.object(self.server.store, "submit", side_effect=AssertionError("job submission forbidden")), \
                patch.object(self.server, "start_worker", side_effect=AssertionError("worker start forbidden")), \
                patch("tools.dwelly_service.worker.run_experiment", side_effect=AssertionError("analysis forbidden")), \
                patch("tools.dwelly_model.providers._open", side_effect=AssertionError("provider forbidden")), \
                patch("tools.dwelly_model.budget.BudgetLedger.reserve", side_effect=AssertionError("budget forbidden")):
            self.assertEqual(self.create_case()[0], 201)
            self.assertEqual(self.append_event()[0], 201)
            status, snapshot = self.request("GET", "/v1/cases/demo-1")
            self.assertEqual(status, 200)
            self.assertEqual(snapshot["analysis_status"], "pending_not_started")
            self.assertEqual(snapshot["operational_effects"], 0)
        with self.server.store._connect() as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM jobs").fetchone()[0], 0)
        self.assertIsNone(self.server.worker)
        self.assertFalse((self.state / "budget.jsonl").exists())
        self.assertEqual(list((self.state / "jobs").iterdir()), [])

    def test_capability_explicitly_discloses_pending_intake_without_analysis_or_effects(self):
        status, result = self.request("GET", "/v1/capabilities")
        self.assertEqual(status, 200)
        self.assertIn("case_intake", result)
        self.assertEqual(result["case_intake"], {
            "enabled": True, "source_mode": "local_fixture", "analysis_status": "pending_not_started",
            "automated_analysis": False, "runtime_binding": None, "authorization": "unverified",
            "operational_effects": 0})

    def test_case_initialization_failure_releases_ownership_and_never_starts_worker(self):
        self.stop_server()
        self.assertTrue(hasattr(server_module, "CaseStore"), "server must initialize durable case intake")
        with patch.object(server_module, "CaseStore", side_effect=OSError("private storage details")), \
                patch.object(server_module.ServiceServer, "start_worker",
                             side_effect=AssertionError("worker must not start after failed case initialization")):
            with self.assertRaises(OSError):
                server_module.create_server(self.bundle, self.config, self.state,
                                            token=self.token, port=0, start_worker=True)
        self.start_server()
        self.assertEqual(self.create_case()[0], 201)


if __name__ == "__main__":
    unittest.main()
