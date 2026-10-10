"""Durable local intake contracts using the actual SQLite owner."""
import importlib
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
import json
import tempfile
import threading
import unittest
from pathlib import Path

from tools.dwelly_service.store import JobStore

try:
    cases = importlib.import_module("tools.dwelly_service.cases")
except ModuleNotFoundError:
    cases = None


def declaration(case_id="demo-1"):
    return {"case_id": case_id,
            "links": {"order_id": "order-1", "customer_id": "customer-1", "operator_id": "operator-1"},
            "participants": ["customer-1", "operator-1", "courier-1"], "language": "en"}


def event(event_id="event-1", expected_revision=0):
    return {"expected_revision": expected_revision, "event": {
        "event_id": event_id, "occurred_at": "2026-10-10T10:00:00Z", "channel": "chat",
        "sender_id": "customer-1", "recipient_ids": ["operator-1"], "kind": "message",
        "text": "Please move my delivery to tomorrow.", "media": None}}


class CaseStoreTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(cases, "local case storage must be implemented")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name).resolve() / "state"
        self.owner = JobStore(self.state)
        self.addCleanup(lambda: self.owner.close())
        self.store = cases.CaseStore(self.owner)

    def assert_case_error(self, code, function, *args):
        with self.assertRaises(ValueError) as caught:
            function(*args)
        self.assertIsInstance(caught.exception, cases.CaseError)
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(str(caught.exception), code)

    def test_creation_is_persisted_pending_and_does_not_create_jobs(self):
        first, created = self.store.create("create-1", declaration())
        self.assertTrue(created)
        self.assertEqual(first["schema_version"], "dwelly-local-case-v1")
        self.assertEqual(first["revision"], 0)
        self.assertEqual(first["events"], [])
        self.assertIsNone(first["previous_snapshot_hash"])
        self.assertIsNone(first["runtime_binding"])
        self.assertEqual(first["source_mode"], "local_fixture")
        self.assertEqual(first["authorization"], "unverified")
        self.assertEqual(first["analysis_status"], "pending_not_started")
        self.assertIs(first["needs_analysis"], True)
        self.assertEqual(first["operational_effects"], 0)
        self.assertRegex(first["snapshot_hash"], r"^[0-9a-f]{64}$")
        self.assertEqual(self.store.get("demo-1"), first)
        self.assertIsNone(self.owner.claim_next())
        self.owner.close()
        self.owner = JobStore(self.state)
        self.store = cases.CaseStore(self.owner)
        self.assertEqual(self.store.get("demo-1", 0), first)
        self.assertEqual(self.store.create("create-1", declaration()), (first, False))

    def test_creation_retries_conflict_on_changed_body_or_duplicate_identity(self):
        first, _ = self.store.create("create-1", declaration())
        changed = declaration()
        changed["links"]["order_id"] = "order-2"
        self.assert_case_error("idempotency_conflict", self.store.create, "create-1", changed)
        self.assert_case_error("idempotency_conflict", self.store.create, "another-key", declaration())
        self.assertEqual(self.store.get("demo-1"), first)

    def test_append_preserves_history_and_uses_received_order(self):
        zero, _ = self.store.create("create-1", declaration())
        earlier = event()
        earlier["event"]["occurred_at"] = "2040-01-01T10:00:00+02:00"
        one, created = self.store.append("demo-1", "append-1", earlier)
        later = event("event-2", 1)
        later["event"]["occurred_at"] = "2000-01-01T10:00:00Z"
        two, _ = self.store.append("demo-1", "append-2", later)
        self.assertTrue(created)
        self.assertEqual(one["revision"], 1)
        self.assertEqual(two["revision"], 2)
        self.assertEqual(one["previous_snapshot_hash"], zero["snapshot_hash"])
        self.assertEqual(two["previous_snapshot_hash"], one["snapshot_hash"])
        self.assertNotEqual(one["snapshot_hash"], zero["snapshot_hash"])
        self.assertEqual([item["event_id"] for item in two["events"]], ["event-1", "event-2"])
        self.assertEqual(self.store.get("demo-1", 0), zero)
        self.assertEqual(self.store.get("demo-1", 1), one)
        self.assertEqual(self.store.get("demo-1"), two)
        self.assertEqual(self.store.create("create-1", declaration()), (zero, False))
        self.assertEqual(self.store.append("demo-1", "append-1", earlier), (one, False))
        self.owner.close()
        self.owner = JobStore(self.state)
        self.store = cases.CaseStore(self.owner)
        self.assertEqual(self.store.append("demo-1", "append-1", earlier), (one, False))
        two["events"][0]["text"] = "Caller mutation"
        self.assertEqual(self.store.get("demo-1")["events"][0]["text"], earlier["event"]["text"])
        self.assertIsNone(self.owner.claim_next())

    def test_append_conflicts_do_not_mutate_the_case(self):
        self.store.create("create-1", declaration())
        one, _ = self.store.append("demo-1", "append-1", event())
        changed = event()
        changed["event"]["text"] = "Different body"
        self.assert_case_error("idempotency_conflict", self.store.append, "demo-1", "append-1", changed)
        self.assert_case_error("event_conflict", self.store.append, "demo-1", "another-key", event(expected_revision=1))
        self.assert_case_error("revision_conflict", self.store.append, "demo-1", "append-2", event("event-2", 0))
        self.assertEqual(self.store.get("demo-1"), one)

    def test_concurrent_expected_revision_commits_only_one_event(self):
        self.store.create("create-1", declaration())
        barrier = threading.Barrier(2)

        def append(index):
            barrier.wait()
            try:
                return self.store.append("demo-1", "key-" + str(index), event("event-" + str(index)))[0]["revision"]
            except ValueError as error:
                return error.code

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(append, (1, 2)))
        self.assertCountEqual(results, [1, "revision_conflict"])
        self.assertEqual(len(self.store.get("demo-1")["events"]), 1)

    def test_invalid_case_declarations_are_closed_and_consistent(self):
        invalid = []
        for field, value in (("case_id", "../secret"), ("case_id", "a" * 65), ("case_id", []),
                             ("language", "fr"), ("language", ["en"]), ("participants", []),
                             ("participants", ["customer-1", "operator-1", "customer-1"]),
                             ("participants", ["customer-1"]), ("participants", "customer-1")):
            body = declaration()
            body[field] = value
            invalid.append(body)
        for links in ({"order_id": "order-1", "customer_id": "customer-1"},
                      {"order_id": "order-1", "customer_id": "customer-1", "operator_id": "customer-1"},
                      {"order_id": "bad/id", "customer_id": "customer-1", "operator_id": "operator-1"}):
            body = declaration()
            body["links"] = links
            invalid.append(body)
        invalid.extend([{}, [], {**declaration(), "runtime_binding": "approved"}])
        for index, body in enumerate(invalid):
            with self.subTest(index=index):
                self.assert_case_error("invalid_case_request", self.store.create, "invalid-" + str(index), body)
        for key in ("", "x" * 129, "space key", None, 1, []):
            with self.subTest(key=key):
                self.assert_case_error("invalid_case_request", self.store.create, key, declaration())
        self.assert_case_error("case_not_found", self.store.get, "demo-1")

    def test_invalid_events_are_rejected_without_changing_revision(self):
        zero, _ = self.store.create("create-1", declaration())
        invalid = []
        for field, value in (("event_id", "bad/id"), ("occurred_at", "2026-10-10T10:00:00"),
                             ("occurred_at", "not-a-time"), ("occurred_at", []), ("channel", "sms"),
                             ("channel", []), ("sender_id", "stranger"), ("recipient_ids", ["stranger"]),
                             ("recipient_ids", ["operator-1", "operator-1"]), ("recipient_ids", "operator-1"),
                             ("kind", "approval"), ("kind", []), ("text", ""), ("text", "   "),
                             ("text", None), ("text", "x" * 4097), ("media", {"url": "https://private.invalid"})):
            body = event()
            body["event"][field] = value
            invalid.append(body)
        for value in (True, -1, 1.0, "0", None):
            body = event()
            body["expected_revision"] = value
            invalid.append(body)
        invalid.extend([{}, {**event(), "approved": True}, {**event(), "event": {}}])
        for index, body in enumerate(invalid):
            with self.subTest(index=index):
                self.assert_case_error("invalid_case_request", self.store.append, "demo-1", "bad-" + str(index), body)
        self.assertEqual(self.store.get("demo-1"), zero)

    def test_missing_and_invalid_revision_queries_return_bounded_errors(self):
        self.store.create("create-1", declaration())
        self.assert_case_error("case_not_found", self.store.get, "missing")
        self.assert_case_error("case_not_found", self.store.append, "missing", "key", event())
        for value in (-1, True, "0", [], 0.0):
            with self.subTest(value=value):
                self.assert_case_error("invalid_case_request", self.store.get, "demo-1", value)
        for value in (1, 10 ** 100):
            self.assert_case_error("revision_not_found", self.store.get, "demo-1", value)

    def test_direct_python_inputs_reject_cycles_nonfinite_and_nonjson_types(self):
        self.store.create("create-1", declaration())
        cyclic = []
        cyclic.append(cyclic)
        deep = []
        for _ in range(100):
            deep = [deep]
        invalid_values = [float("nan"), float("inf"), float("-inf"), b"secret", {1: "bad"},
                          {None: "bad"}, object(), {"bad"}, cyclic, deep, "\ud800", 10 ** 10000]
        for index, value in enumerate(invalid_values):
            body = event()
            body["event"]["text"] = value
            with self.subTest(index=index):
                self.assert_case_error("invalid_case_request", self.store.append, "demo-1", "bad-" + str(index), body)
        self.assertEqual(self.store.get("demo-1")["revision"], 0)

    def test_media_metadata_is_typed_bounded_and_not_processed(self):
        self.store.create("create-1", declaration())
        revision = 0
        for kind, mimes, limit in (("photo", ["image/png", "image/jpeg"], 10 * 1024 * 1024),
                                   ("voice_message", ["audio/mpeg", "audio/wav", "audio/mp4", "audio/webm"], 25 * 1024 * 1024),
                                   ("call_recording", ["audio/mpeg", "audio/wav", "audio/mp4", "audio/webm"], 25 * 1024 * 1024)):
            for mime in mimes:
                body = event("media-" + str(revision), revision)
                body["event"].update(kind=kind, text=None, media={"asset_id": "asset-1", "sha256": "a" * 64,
                                                                "mime_type": mime, "size_bytes": limit})
                current, _ = self.store.append("demo-1", "media-key-" + str(revision), body)
                revision += 1
                self.assertEqual(current["events"][-1], body["event"])
                self.assertIsNone(current["runtime_binding"])
                for field, value in (("asset_id", "file:///tmp/private"), ("sha256", "x" * 64),
                                     ("size_bytes", limit + 1), ("size_bytes", True), ("size_bytes", 0),
                                     ("mime_type", "text/plain"), ("url", "https://private.invalid")):
                    invalid = deepcopy(body)
                    invalid["expected_revision"] = revision
                    invalid["event"]["event_id"] = "bad-media"
                    invalid["event"]["media"][field] = value
                    self.assert_case_error("invalid_case_request", self.store.append, "demo-1", "bad-media", invalid)
        self.assertEqual(self.store.get("demo-1")["revision"], 10)
        self.assertIsNone(self.owner.claim_next())

    def test_input_bounds_do_not_limit_the_aggregate_snapshot_to_one_request(self):
        body = declaration()
        body["participants"] += ["person-" + str(i) for i in range(13)]
        self.store.create("create-1", body)
        oversized = deepcopy(body)
        oversized["case_id"] = "other"
        oversized["participants"].append("one-too-many")
        self.assert_case_error("invalid_case_request", self.store.create, "too-many", oversized)
        for index in range(6):
            body = event("event-" + str(index), index)
            body["event"]["recipient_ids"] = declaration()["participants"] + ["person-" + str(i) for i in range(13)]
            body["event"]["text"] = "x" * 4096
            current, _ = self.store.append("demo-1", "key-" + str(index), body)
        self.assertGreater(len(json.dumps(current)), 16384)
        self.assertEqual(self.store.get("demo-1"), current)
        too_large = event("large", 6)
        too_large["event"]["text"] = "\U0001f600" * 4096
        self.assert_case_error("invalid_case_request", self.store.append, "demo-1", "large", too_large)

    def test_case_and_event_capacity_preserve_existing_retries(self):
        zero, _ = self.store.create("create-0", declaration())
        for index in range(1, 256):
            self.store.create("create-" + str(index), declaration("case-" + str(index)))
        self.assert_case_error("case_capacity", self.store.create, "overflow", declaration("overflow"))
        self.assertEqual(self.store.create("create-0", declaration()), (zero, False))
        one = None
        for index in range(128):
            current, _ = self.store.append("demo-1", "event-" + str(index), event("event-" + str(index), index))
            if index == 0:
                one = current
        self.assertEqual(current["revision"], 128)
        self.assert_case_error("case_capacity", self.store.append, "demo-1", "event-overflow", event("overflow", 128))
        self.assertEqual(self.store.append("demo-1", "event-0", event("event-0", 0)), (one, False))
        self.assertEqual(self.store.get("demo-1"), current)
        with self.owner._connect() as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM case_heads").fetchone()[0], 256)
            self.assertEqual(connection.execute("SELECT count(*) FROM case_snapshots WHERE case_id='demo-1'").fetchone()[0], 129)

    def save_snapshot(self, value, revision, rehash=True):
        value = deepcopy(value)
        if rehash:
            value.pop("snapshot_hash", None)
            encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
            value["snapshot_hash"] = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        with self.owner._connect() as connection:
            connection.execute("UPDATE case_snapshots SET snapshot=? WHERE case_id='demo-1' AND revision=?", (encoded, revision))
        return value

    def test_snapshot_readback_rejects_invalid_shape_semantics_and_hash(self):
        zero, _ = self.store.create("create-1", declaration())
        one, _ = self.store.append("demo-1", "append-1", event())
        corruptions = [("unhashed text", "text", "changed", False)]
        for field, value in (("authorization", "verified"), ("operational_effects", True),
                             ("operational_effects", 1), ("runtime_binding", {}), ("needs_analysis", False),
                             ("analysis_status", "completed"), ("source_mode", "live"), ("schema_version", "other"),
                             ("case_id", "other-case"), ("revision", True), ("revision", 2),
                             ("previous_snapshot_hash", "b" * 64), ("unknown", "injected"),
                             ("language", "fr"), ("events", []), ("events", None)):
            corruptions.append((field, field, value, True))
        for label, field, value, rehash in corruptions:
            invalid = deepcopy(one)
            if field == "text":
                invalid["events"][0]["text"] = value
            else:
                invalid[field] = value
            self.save_snapshot(invalid, 1, rehash=rehash)
            with self.subTest(label=label):
                self.assert_case_error("case_storage_error", self.store.get, "demo-1")
                self.assert_case_error("case_storage_error", self.store.get, "demo-1", 0)
                self.assert_case_error("case_storage_error", self.store.append, "demo-1", "append-2", event("event-2", 1))
                self.assert_case_error("case_storage_error", self.store.create, "create-1", declaration())
            self.save_snapshot(one, 1)
        self.assertEqual(self.store.get("demo-1", 0), zero)

    def test_history_detects_rehashed_prefix_and_declaration_changes(self):
        zero, _ = self.store.create("create-1", declaration())
        one, _ = self.store.append("demo-1", "append-1", event())
        two, _ = self.store.append("demo-1", "append-2", event("event-2", 1))
        invalid = deepcopy(one)
        invalid["events"][0]["text"] = "History rewritten"
        altered_one = self.save_snapshot(invalid, 1)
        invalid_two = deepcopy(two)
        invalid_two["previous_snapshot_hash"] = altered_one["snapshot_hash"]
        self.save_snapshot(invalid_two, 2)
        self.assert_case_error("case_storage_error", self.store.get, "demo-1")
        self.save_snapshot(one, 1)
        self.save_snapshot(two, 2)
        invalid_two = deepcopy(two)
        invalid_two["links"]["order_id"] = "different-order"
        self.save_snapshot(invalid_two, 2)
        self.assert_case_error("case_storage_error", self.store.get, "demo-1")
        self.save_snapshot(two, 2)
        invalid_zero = deepcopy(zero)
        invalid_zero["previous_snapshot_hash"] = "a" * 64
        self.save_snapshot(invalid_zero, 0)
        self.assert_case_error("case_storage_error", self.store.get, "demo-1")

    def test_history_detects_missing_revisions_and_invalid_head(self):
        self.store.create("create-1", declaration())
        self.store.append("demo-1", "append-1", event())
        with self.owner._connect() as connection:
            connection.execute("UPDATE case_heads SET current_revision=2 WHERE case_id='demo-1'")
        self.assert_case_error("case_storage_error", self.store.get, "demo-1")
        with self.owner._connect() as connection:
            connection.execute("UPDATE case_heads SET current_revision=1 WHERE case_id='demo-1'")
            connection.execute("DELETE FROM case_snapshots WHERE case_id='demo-1' AND revision=0")
        self.assert_case_error("case_storage_error", self.store.get, "demo-1")

    def test_rehashed_event_prefix_cannot_replace_integer_with_boolean(self):
        self.store.create("create-1", declaration())
        media = event()
        media["event"].update(kind="photo", text=None,
                              media={"asset_id": "asset-1", "sha256": "a" * 64,
                                     "mime_type": "image/png", "size_bytes": 1})
        self.store.append("demo-1", "append-1", media)
        two, _ = self.store.append("demo-1", "append-2", event("event-2", 1))
        two["events"][0]["media"]["size_bytes"] = True
        self.save_snapshot(two, 2)
        self.assert_case_error("case_storage_error", self.store.get, "demo-1")

    def test_malformed_duplicate_key_and_oversized_storage_are_rejected(self):
        zero, _ = self.store.create("create-1", declaration())
        raw = json.dumps(zero, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for payload in ("{", "null", '[]', '{"revision":0,' + raw[1:],
                        raw.replace('"revision":0', '"revision":NaN'), "x" * (129 * 16384 + 1)):
            with self.owner._connect() as connection:
                connection.execute("UPDATE case_snapshots SET snapshot=? WHERE case_id='demo-1'", (payload,))
            with self.subTest(prefix=payload[:20]):
                self.assert_case_error("case_storage_error", self.store.get, "demo-1")
        self.save_snapshot(zero, 0)
        self.assertEqual(self.store.get("demo-1"), zero)

    def test_corrupt_idempotency_mapping_cannot_return_unrelated_revision(self):
        self.store.create("create-1", declaration())
        self.store.append("demo-1", "append-1", event())
        for field, value in (("revision", 0), ("revision", 200), ("case_id", "missing"),
                             ("body", "{"), ("body", json.dumps(event("different-event")))):
            with self.owner._connect() as connection:
                connection.execute("UPDATE case_requests SET " + field + "=? WHERE scope='append:demo-1'", (value,))
            with self.subTest(field=field, value=value):
                self.assert_case_error("case_storage_error", self.store.append, "demo-1", "append-1", event())
            with self.owner._connect() as connection:
                connection.execute("UPDATE case_requests SET revision=1,case_id='demo-1',body=? WHERE scope='append:demo-1'",
                                   (json.dumps(event(), ensure_ascii=False, sort_keys=True, separators=(",", ":")),))

    def test_unavailable_owner_and_corrupt_database_have_content_free_errors(self):
        self.store.create("create-1", declaration())
        self.owner.close()
        self.assert_case_error("case_storage_error", self.store.get, "demo-1")
        self.assert_case_error("case_storage_error", cases.CaseStore, self.owner)
        self.owner = JobStore(self.state)
        self.store = cases.CaseStore(self.owner)
        self.owner.database.write_bytes(b"private invalid database content")
        self.assert_case_error("case_storage_error", self.store.get, "demo-1")


if __name__ == "__main__":
    unittest.main()
