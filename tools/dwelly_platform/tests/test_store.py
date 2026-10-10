"""Real PostgreSQL tests of the integrated, external-effect-free platform."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import importlib
import os
import unittest
import uuid

from tools.dwelly_service.tests.test_cases import declaration, event

try:
    platform = importlib.import_module("tools.dwelly_platform.store")
except ModuleNotFoundError:
    platform = None

DSN = os.environ.get("PROOFKEY_TEST_DATABASE_URL")
PNG = bytes.fromhex("89504e470d0a1a0a") + b"image-content"


@unittest.skipUnless(DSN, "set PROOFKEY_TEST_DATABASE_URL for real PostgreSQL")
class PlatformStoreTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(platform, "platform persistence is required")
        self.schema = "platform_test_" + uuid.uuid4().hex
        self.addCleanup(self.drop_schema)
        platform.migrate(DSN, schema=self.schema)
        self.store = platform.PlatformStore(DSN, schema=self.schema, max_size=4)
        self.addCleanup(self.store.close)
        self.store.create("create", declaration())

    def drop_schema(self):
        import psycopg
        from psycopg import sql
        with psycopg.connect(DSN, autocommit=True) as connection:
            connection.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(self.schema)))

    def error(self, code, function, *args):
        with self.assertRaises(ValueError) as caught:
            function(*args)
        self.assertEqual(caught.exception.code, code)

    def body(self):
        current = self.store.get("demo-1")
        return {"expected_revision": current["revision"], "snapshot_hash": current["snapshot_hash"]}

    def proposal(self):
        self.store.append("demo-1", "append", event())
        start = datetime.now(timezone.utc) + timedelta(days=1)
        return {**self.body(), "action": {"type": "reschedule_delivery", "slot_start": start.isoformat(),
                "slot_end": (start + timedelta(hours=2)).isoformat(), "address_change": False},
                "evidence_event_ids": ["event-1"]}

    def approved(self):
        result = self.store.propose("demo-1", "propose", self.proposal())
        decision = result["decisions"][-1]["decision_id"]
        self.store.review("demo-1", "review", {"decision_id": decision, "verdict": "approve", "note": "Consent checked locally",
                                               "customer_consent_confirmed": True})
        return decision

    def test_canonical_history_and_separate_migrations_are_preserved(self):
        zero = self.store.get("demo-1")
        self.store.append("demo-1", "append", event())
        platform.migrate(DSN, schema=self.schema)
        self.assertEqual(self.store.get("demo-1", 0), zero)
        self.assertEqual(zero["schema_version"], "dwelly-local-case-v1")
        with self.store._transaction() as connection:
            self.assertEqual(connection.execute("SELECT version FROM schema_migrations").fetchall()[0][0], 1)
        self.assertEqual(self.store.detail("demo-1")["snapshot"], self.store.get("demo-1"))
        self.assertEqual(len(self.store.list_cases()), 1)

    def test_empty_analysis_requests_information_and_replays_body_bound(self):
        body = {**self.body(), "mode": "deterministic"}
        result = self.store.analyze("demo-1", "analyze", body)
        self.assertEqual(result["states"]["lifecycle"], "awaiting_information")
        self.assertEqual(result["decisions"][-1]["action"]["type"], "request_information")
        self.assertEqual(self.store.analyze("demo-1", "analyze", body), result)
        self.error("idempotency_conflict", self.store.analyze, "demo-1", "analyze", {**body, "snapshot_hash": "0" * 64})

    def test_revision_hash_and_evidence_are_admission_constraints(self):
        body = self.proposal()
        self.error("revision_conflict", self.store.propose, "demo-1", "rev", {**body, "expected_revision": 0})
        self.error("snapshot_conflict", self.store.propose, "demo-1", "hash", {**body, "snapshot_hash": "0" * 64})
        self.error("evidence_not_found", self.store.propose, "demo-1", "evidence", {**body, "evidence_event_ids": ["missing"]})
        self.assertEqual(self.store.detail("demo-1")["decisions"], [])

    def test_reschedule_approval_and_atomic_concurrent_replay(self):
        decision = self.approved()
        def execute(index):
            return self.store.execute("demo-1", "execute-" + str(index), {"decision_id": decision})
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(execute, range(4)))
        self.assertTrue(all(item["actions"] == results[0]["actions"] for item in results))
        receipt = results[0]["actions"][0]
        self.assertEqual(receipt["execution_mode"], "postgres_sandbox")
        self.assertEqual(receipt["sandbox_effects"], 1)
        self.assertEqual(receipt["external_effects"], 0)
        self.assertEqual(results[0]["states"]["lifecycle"], "resolved")
        with self.store._transaction() as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM platform_bookings").fetchone()[0], 1)

    def test_receipt_failure_rolls_back_booking_and_request_then_retry_succeeds(self):
        decision = self.approved()
        with self.store._transaction(write=True) as connection:
            connection.execute("""CREATE FUNCTION reject_test_receipt() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN RAISE EXCEPTION 'injected receipt failure'; END $$""")
            connection.execute("CREATE TRIGGER reject_test_receipt BEFORE INSERT ON platform_actions FOR EACH ROW EXECUTE FUNCTION reject_test_receipt()")
        self.error("case_storage_error", self.store.execute, "demo-1", "execute", {"decision_id": decision})
        with self.store._transaction(write=True) as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM platform_bookings").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT count(*) FROM platform_actions").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT count(*) FROM platform_requests WHERE scope='execute:demo-1'").fetchone()[0], 0)
            connection.execute("DROP TRIGGER reject_test_receipt ON platform_actions")
        first = self.store.execute("demo-1", "execute", {"decision_id": decision})
        self.store.close()
        self.store = platform.PlatformStore(DSN, schema=self.schema)
        self.addCleanup(self.store.close)
        self.assertEqual(self.store.execute("demo-1", "execute", {"decision_id": decision}), first)

    def test_stale_approval_and_superseded_decision_cannot_execute(self):
        decision = self.approved()
        self.store.append("demo-1", "append2", event("event-2", 1))
        self.error("revision_conflict", self.store.execute, "demo-1", "execute", {"decision_id": decision})
        self.assertEqual(self.store.detail("demo-1")["states"]["decision"], "superseded")

    def test_new_proposal_supersedes_old_approval(self):
        decision = self.approved()
        body = {**self.body(), "action": {"type": "refund"}, "evidence_event_ids": ["event-1"]}
        self.store.propose("demo-1", "new-propose", body)
        self.error("decision_superseded", self.store.execute, "demo-1", "execute", {"decision_id": decision})

    def test_unsupported_actions_and_unsafe_slots_remain_blocked(self):
        body = self.proposal()
        for index, action in enumerate(({"type": "refund"}, {**body["action"], "address_change": True},
                                       {**body["action"], "slot_end": "2026-01-01T00:00:00Z"},
                                       {**body["action"], "slot_start": "2030-01-01T00:00:00"})):
            result = self.store.propose("demo-1", "bad-" + str(index), {**body, "action": action})
            self.assertEqual(result["states"]["decision"], "blocked")
            self.error("action_blocked", self.store.execute, "demo-1", "execute-" + str(index),
                       {"decision_id": result["decisions"][-1]["decision_id"]})

    def test_consent_and_trusted_operator_attestation_are_required(self):
        result = self.store.propose("demo-1", "propose", self.proposal())
        decision = result["decisions"][-1]["decision_id"]
        review = {"decision_id": decision, "verdict": "approve", "note": "Checked", "customer_consent_confirmed": False}
        self.error("consent_required", self.store.review, "demo-1", "no-consent", review)
        self.error("approval_required", self.store.execute, "demo-1", "execute", {"decision_id": decision})
        result = self.store.review("demo-1", "consent", {**review, "customer_consent_confirmed": True})
        self.assertEqual(result["reviews"][-1]["operator_id"], "local-operator")
        self.assertIn("local", result["reviews"][-1]["attestation_scope"])
        self.assertEqual(result["reviews"][-1]["revision"], 1)
        self.assertEqual(result["reviews"][-1]["snapshot_hash"], result["snapshot"]["snapshot_hash"])

    def test_information_acknowledgement_is_audited_without_execution_permission(self):
        analyzed = self.store.analyze("demo-1", "analyze", {**self.body(), "mode": "deterministic"})
        decision = analyzed["decisions"][-1]["decision_id"]
        reviewed = self.store.review("demo-1", "acknowledge", {
            "decision_id": decision, "verdict": "approve", "note": "Information request checked",
            "customer_consent_confirmed": False})
        self.assertEqual(reviewed["states"]["decision"], "approved")
        self.assertEqual(reviewed["states"]["lifecycle"], "awaiting_information")
        self.assertEqual(reviewed["reviews"][-1]["revision"], 0)
        self.assertEqual(reviewed["reviews"][-1]["snapshot_hash"], reviewed["snapshot"]["snapshot_hash"])
        self.error("action_blocked", self.store.execute, "demo-1", "execute", {"decision_id": decision})
        self.assertEqual(self.store.detail("demo-1")["actions"], [])

    def test_operator_review_can_be_acknowledged_then_rejected_without_becoming_ready(self):
        self.store.append("demo-1", "append", event())
        analyzed = self.store.analyze("demo-1", "analyze", {**self.body(), "mode": "deterministic"})
        decision = analyzed["decisions"][-1]["decision_id"]
        review = {"decision_id": decision, "verdict": "approve", "note": "Evidence reviewed",
                  "customer_consent_confirmed": False}
        acknowledged = self.store.review("demo-1", "acknowledge", review)
        self.assertEqual(acknowledged["states"]["decision"], "approved")
        self.assertEqual(acknowledged["states"]["lifecycle"], "in_review")
        self.error("action_blocked", self.store.execute, "demo-1", "before-rejection", {"decision_id": decision})
        rejected = self.store.review("demo-1", "reject", {**review, "verdict": "reject"})
        self.assertEqual(rejected["states"]["decision"], "rejected")
        self.assertEqual(rejected["states"]["lifecycle"], "escalated")
        self.error("action_blocked", self.store.execute, "demo-1", "after-rejection", {"decision_id": decision})

    def test_blocked_refund_return_and_unknown_actions_can_be_rejected_but_never_approved(self):
        body = self.proposal()
        for index, action_type in enumerate(("refund", "return", "unknown_action")):
            proposed = self.store.propose("demo-1", "propose-" + str(index), {**body, "action": {"type": action_type}})
            decision = proposed["decisions"][-1]["decision_id"]
            review = {"decision_id": decision, "verdict": "approve", "note": "Unsupported action requires escalation",
                      "customer_consent_confirmed": True}
            self.error("action_blocked", self.store.review, "demo-1", "approve-" + str(index), review)
            self.error("action_blocked", self.store.execute, "demo-1", "before-" + str(index), {"decision_id": decision})
            rejected = self.store.review("demo-1", "reject-" + str(index), {**review, "verdict": "reject"})
            self.assertEqual(rejected["reviews"][-1]["decision_id"], decision)
            self.assertEqual(rejected["states"]["decision"], "rejected")
            self.assertEqual(rejected["states"]["lifecycle"], "escalated")
            self.error("action_blocked", self.store.execute, "demo-1", "after-" + str(index), {"decision_id": decision})
        self.assertEqual(self.store.detail("demo-1")["actions"], [])

    def test_unsafe_reschedule_can_be_rejected_without_consent(self):
        body = self.proposal()
        result = self.store.propose("demo-1", "propose", {**body, "action": {**body["action"], "address_change": True}})
        decision = result["decisions"][-1]["decision_id"]
        reviewed = self.store.review("demo-1", "reject", {"decision_id": decision, "verdict": "reject",
                                     "note": "Address change is unsupported", "customer_consent_confirmed": False})
        self.assertEqual(reviewed["states"]["decision"], "rejected")
        self.assertEqual(reviewed["states"]["lifecycle"], "escalated")

    def test_assets_are_private_hashed_case_bound_and_not_ocr(self):
        descriptor = self.store.put_asset("demo-1", "asset", "image/png", "../../photo.png", PNG)
        self.assertEqual(descriptor["sha256"], hashlib.sha256(PNG).hexdigest())
        self.assertEqual(self.store.put_asset("demo-1", "asset", "image/png", "../../photo.png", PNG), descriptor)
        meta, raw = self.store.get_asset("demo-1", descriptor["asset_id"])
        self.assertEqual(raw, PNG)
        self.assertNotIn("/", meta["filename"])
        self.store.create("create2", declaration("other"))
        self.error("asset_not_found", self.store.get_asset, "other", descriptor["asset_id"])
        media = event()
        media["event"].update(kind="photo", text=None, media=descriptor)
        self.store.append("demo-1", "media", media)
        self.assertEqual(self.store.detail("demo-1")["states"]["evidence"], "media_unprocessed")
        self.error("asset_not_found", self.store.append, "other", "foreign", media)

    def test_asset_signatures_limits_and_binding_are_enforced(self):
        self.error("invalid_asset", self.store.put_asset, "demo-1", "html", "image/png", "a.png", b"<script>alert(1)</script>")
        self.error("invalid_asset", self.store.put_asset, "demo-1", "mime", "text/html", "a.html", PNG)
        self.error("asset_too_large", self.store.put_asset, "demo-1", "large", "image/png", "a.png", PNG + b"x" * (10 * 1024 * 1024))
        self.store.put_asset("demo-1", "asset", "image/png", "a.png", PNG)
        self.error("idempotency_conflict", self.store.put_asset, "demo-1", "asset", "image/png", "a.png", PNG + b"different")
        with self.store._transaction(write=True) as connection:
            connection.execute("UPDATE platform_assets SET size_bytes=?", (100 * 1024 * 1024,))
        self.error("asset_capacity", self.store.put_asset, "demo-1", "capacity", "image/png", "b.png", PNG)

    def test_model_links_validate_historical_snapshot_and_global_job_ownership(self):
        original = self.body()
        self.store.append("demo-1", "append", event())
        self.store.link_model("demo-1", 0, original["snapshot_hash"], "a" * 32)
        self.store.link_model("demo-1", 0, original["snapshot_hash"], "a" * 32)
        self.assertEqual(self.store.detail("demo-1")["model_jobs"], [
            {"job_id": "a" * 32, "revision": 0, "snapshot_hash": original["snapshot_hash"]}])
        self.error("snapshot_conflict", self.store.link_model, "demo-1", 1, "b" * 64, "b" * 32)
        self.store.create("create2", declaration("other"))
        other = self.store.get("other")
        self.error("idempotency_conflict", self.store.link_model, "other", 0, other["snapshot_hash"], "a" * 32)

    def test_nonobject_mutation_body_is_a_public_validation_error(self):
        for operation in (self.store.analyze, self.store.propose, self.store.review, self.store.execute):
            for body in (None, [], [1], True, 1, "body"):
                with self.subTest(operation=operation.__name__, body=body):
                    self.error("invalid_platform_request", operation, "demo-1", "bad-body", body)

    def test_changed_asset_metadata_cannot_be_attached_and_append_rolls_back(self):
        descriptor = self.store.put_asset("demo-1", "asset", "image/png", "photo.png", PNG)
        media = event()
        media["event"].update(kind="photo", text=None, media={**descriptor, "sha256": "0" * 64})
        self.error("asset_mismatch", self.store.append, "demo-1", "bad-metadata", media)
        self.assertEqual(self.store.get("demo-1")["revision"], 0)
        self.assertEqual(len(self.store.analysis_jobs("demo-1")), 1)

    def test_review_key_is_body_bound_and_latest_rejection_prevents_execution(self):
        decision = self.approved()
        review = {"decision_id": decision, "verdict": "reject", "note": "Customer withdrew consent",
                  "customer_consent_confirmed": False}
        self.error("idempotency_conflict", self.store.review, "demo-1", "review", review)
        self.store.review("demo-1", "reject", review)
        self.error("approval_required", self.store.execute, "demo-1", "execute", {"decision_id": decision})
        self.assertEqual(self.store.detail("demo-1")["states"]["decision"], "rejected")

    def test_media_signatures_cover_all_supported_types_without_transcription(self):
        samples = {"image/jpeg": b"\xff\xd8\xff\xe0image", "audio/mpeg": b"ID3audio", "audio/wav": b"RIFF1234WAVEaudio",
                   "audio/mp4": b"\x00\x00\x00\x18ftypM4A audio", "audio/webm": b"\x1a\x45\xdf\xa3webmaudio"}
        for index, (mime, sample) in enumerate(samples.items()):
            descriptor = self.store.put_asset("demo-1", "asset-" + str(index), mime, "media", sample)
            self.assertEqual(self.store.get_asset("demo-1", descriptor["asset_id"])[1], sample)
            self.error("invalid_asset", self.store.put_asset, "demo-1", "wrong-" + str(index), mime, "media", b"unrelated")
        result = self.store.analyze("demo-1", "analyze", {**self.body(), "mode": "deterministic"})
        self.assertEqual(result["states"]["evidence"], "media_unprocessed")
        self.assertEqual(result["decisions"][-1]["action"]["type"], "request_information")


if __name__ == "__main__":
    unittest.main()
