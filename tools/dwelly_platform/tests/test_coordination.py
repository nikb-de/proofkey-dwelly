"""Coordination admission and transactional receipts against real PostgreSQL."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import os
import unittest
import uuid

from tools.dwelly_platform import store as platform
from tools.dwelly_service.tests.test_cases import declaration, event

DSN = os.environ.get("PROOFKEY_TEST_DATABASE_URL")


@unittest.skipUnless(DSN, "set PROOFKEY_TEST_DATABASE_URL for real PostgreSQL")
class CoordinationTests(unittest.TestCase):
    def setUp(self):
        self.schema = "coord_test_" + uuid.uuid4().hex
        self.addCleanup(self.drop_schema)
        platform.migrate(DSN, schema=self.schema)
        self.store = platform.PlatformStore(DSN, schema=self.schema)
        self.addCleanup(lambda: self.store.close())
        self.store.create("create", declaration())

    def drop_schema(self):
        import psycopg
        from psycopg import sql
        with psycopg.connect(DSN, autocommit=True) as connection:
            connection.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(self.schema)))

    def terms(self, **changes):
        start = datetime.now(timezone.utc) + timedelta(days=1)
        return {"slot_start": start.isoformat(), "slot_end": (start + timedelta(hours=2)).isoformat(),
                "handover": "recipient_only", "recipient_present": True,
                "charge": {"amount_minor": 1200, "currency": "GBP"}, **changes}

    def body(self, command, **params):
        current = self.store.get("demo-1")
        state = self.store.coordination_detail("demo-1")
        return {"command": command, "expected_revision": current["revision"], "snapshot_hash": current["snapshot_hash"],
                "expected_workflow_version": state["version"] if state else 0, **params}

    def command(self, command, **params):
        return self.store.coordination_command("demo-1", uuid.uuid4().hex, self.body(command, **params))

    def source(self, text, sender="customer-1", **changes):
        eid = "source-" + uuid.uuid4().hex
        body = event(eid, self.store.get("demo-1")["revision"])
        body["event"].update(text=text, sender_id=sender, **changes)
        self.store.append("demo-1", eid, body)
        return eid

    def initialize(self):
        return self.command("initialize", dispatch_actor_id="courier-1",
                            original_booking={"booking_id": "booking-old", "terms": self.terms()})

    def awaiting_terms(self):
        self.initialize()
        evidence = self.source("Please cancel the old booking")
        pending = self.command("request_cancellation", evidence_event_ids=[evidence])
        rid = pending["pending_request"]["request_id"]
        response = self.source("Cancelled request " + rid, "courier-1")
        return self.command("confirm_cancellation", request_id=rid, evidence_event_ids=[response])

    def offered(self):
        self.awaiting_terms()
        evidence = self.source("Replacement offer", "courier-1")
        return self.command("record_offer", terms=self.terms(), evidence_event_ids=[evidence])

    def consented(self):
        state = self.offered()
        evidence = self.source("I accept every offered term")
        return self.command("record_consent", offer_id=state["offer"]["offer_id"],
                            terms_hash=state["offer"]["terms_hash"], evidence_event_ids=[evidence])

    def error(self, code, function, *args, **kwargs):
        with self.assertRaises(ValueError) as caught:
            function(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)

    def test_initialize_audits_post_revision_and_replays_exactly(self):
        self.assertTrue(hasattr(self.store, "coordination_command"), "coordination commands must be implemented")
        body = self.body("initialize", dispatch_actor_id="courier-1",
                         original_booking={"booking_id": "booking-old", "terms": self.terms()})
        state = self.store.coordination_command("demo-1", "init", body)
        self.assertEqual((state["phase"], state["version"], state["revision"]), ("booked", 1, 1))
        self.assertEqual(state["snapshot_hash"], self.store.get("demo-1")["snapshot_hash"])
        self.assertEqual(state["external_effects"], 0)
        self.assertEqual(state["physical_delivery"], "not_confirmed")
        self.assertEqual(self.store.coordination_command("demo-1", "init", body), state)
        self.assertEqual(self.store.get("demo-1")["revision"], 1)
        self.assertEqual(self.store.get("demo-1")["events"][-1]["channel"], "internal")
        self.assertEqual(json.loads(self.store.get("demo-1")["events"][-1]["text"]).get("original_booking"), state["original_booking"])
        self.assertEqual(self.store.detail("demo-1")["coordination"], state)

    def test_full_flow_requires_correlated_new_dispatch_confirmation(self):
        state = self.consented()
        pending = self.command("request_booking", offer_id=state["offer"]["offer_id"], terms_hash=state["offer"]["terms_hash"])
        self.assertEqual(pending["phase"], "booking_pending")
        rid = pending["pending_request"]["request_id"]
        eid = self.source("Confirmed " + rid + " " + state["offer"]["terms_hash"], "courier-1")
        confirmed = self.command("confirm_booking", request_id=rid, terms_hash=state["offer"]["terms_hash"], evidence_event_ids=[eid])
        self.assertEqual(confirmed["phase"], "booking_confirmed")
        self.assertEqual(confirmed["physical_delivery"], "not_confirmed")
        self.assertEqual(confirmed["external_effects"], 0)
        self.assertEqual(len(confirmed["audit_history"]), 7)
        self.assertEqual(json.loads(self.store.get("demo-1")["events"][-1]["text"]).get("request_id"), rid)

    def test_wrong_actor_and_missing_request_correlation_cannot_confirm(self):
        self.initialize()
        evidence = self.source("Please cancel")
        pending = self.command("request_cancellation", evidence_event_ids=[evidence])
        rid = pending["pending_request"]["request_id"]
        wrong = self.source("Cancelled " + rid)
        self.error("evidence_actor_mismatch", self.command, "confirm_cancellation", request_id=rid, evidence_event_ids=[wrong])
        unrelated = self.source("Cancelled some other request", "courier-1")
        self.error("evidence_correlation_mismatch", self.command, "confirm_cancellation", request_id=rid, evidence_event_ids=[unrelated])

    def test_new_source_after_consent_blocks_booking_until_reaccepted(self):
        state = self.consented()
        self.source("Actually there is a new condition", "courier-1")
        self.error("consent_stale", self.command, "request_booking", offer_id=state["offer"]["offer_id"], terms_hash=state["offer"]["terms_hash"])

    def test_changed_offer_clears_consent_and_old_evidence_cannot_accept_new_offer(self):
        state = self.consented()
        old_evidence = state["consent"]["evidence_event_ids"]
        eid = self.source("A different charge applies", "courier-1")
        changed = self.command("record_offer", terms=self.terms(charge={"amount_minor": 2400, "currency": "GBP"}), evidence_event_ids=[eid])
        self.assertEqual(changed["phase"], "awaiting_consent")
        self.assertIsNone(changed["consent"])
        self.error("evidence_stale", self.command, "record_consent", offer_id=changed["offer"]["offer_id"],
                   terms_hash=changed["offer"]["terms_hash"], evidence_event_ids=old_evidence)
        self.error("offer_mismatch", self.command, "request_booking", offer_id=state["offer"]["offer_id"], terms_hash=state["offer"]["terms_hash"])

    def test_terms_and_payloads_are_strict_and_historical_original_is_allowed(self):
        historic = self.terms(slot_start="2020-01-01T10:00:00Z", slot_end="2020-01-01T12:00:00Z")
        self.command("initialize", dispatch_actor_id="courier-1", original_booking={"booking_id": "old", "terms": historic})
        self.error("invalid_coordination_request", self.command, "escalate", reason="Help", evidence_event_ids=[], extra=True)
        self.error("invalid_coordination_request", self.command, "escalate", reason="Help", evidence_event_ids=[])
        for changes in ({"recipient_present": False}, {"charge": {"amount_minor": True, "currency": "GBP"}},
                        {"slot_start": "2026-01-01T10:00:00"}, {"handover": "anywhere"},
                        {"handover": "concierge_allowed"}, {"unknown": True}):
            with self.subTest(changes=changes):
                fresh = deepcopy(self.terms(**changes))
                # Validate through a new initialized case to exercise admission.
                case_id = "bad-" + uuid.uuid4().hex
                self.store.create(case_id, declaration(case_id))
                snapshot = self.store.get(case_id)
                self.error("invalid_terms", self.store.coordination_command, case_id, "init", {
                    "command": "initialize", "expected_revision": 0, "snapshot_hash": snapshot["snapshot_hash"],
                    "expected_workflow_version": 0, "dispatch_actor_id": "courier-1", "original_booking": {"booking_id": "old", "terms": fresh}})

    def test_original_unknown_terms_and_zero_cost_unknown_currency_preserve_source(self):
        original = self.terms(handover="unspecified", recipient_present=None,
                              charge={"amount_minor": None, "currency": None})
        result = self.command("initialize", dispatch_actor_id="courier-1",
                              original_booking={"booking_id": "original", "terms": original})
        self.assertEqual(result["original_booking"]["terms"], original)
        eid = self.source("Cancel the original")
        pending = self.command("request_cancellation", evidence_event_ids=[eid])
        rid = pending["pending_request"]["request_id"]
        eid = self.source("Cancellation confirmed " + rid, "courier-1")
        self.command("confirm_cancellation", request_id=rid, evidence_event_ids=[eid])
        eid = self.source("No charge for concierge delivery", "courier-1")
        offer = self.command("record_offer", terms=self.terms(handover="concierge_allowed", recipient_present=False,
                             charge={"amount_minor": 0, "currency": None}), evidence_event_ids=[eid])
        self.assertIsNone(offer["offer"]["terms"]["charge"]["currency"])

    def test_old_wrong_route_and_reused_evidence_cannot_advance_workflow(self):
        self.initialize()
        old = self.source("Cancellation confirmed old", "courier-1")
        request_eid = self.source("Please cancel")
        pending = self.command("request_cancellation", evidence_event_ids=[request_eid])
        rid = pending["pending_request"]["request_id"]
        self.error("evidence_stale", self.command, "confirm_cancellation", request_id=rid, evidence_event_ids=[old])
        wrong_route = self.source("Cancelled " + rid, "courier-1", recipient_ids=["customer-1"])
        self.error("evidence_actor_mismatch", self.command, "confirm_cancellation", request_id=rid, evidence_event_ids=[wrong_route])
        eid = self.source("Cancelled " + rid, "courier-1")
        self.command("confirm_cancellation", request_id=rid, evidence_event_ids=[eid])
        self.error("evidence_stale", self.command, "record_offer", terms=self.terms(), evidence_event_ids=[eid])

    def test_stale_workflow_invalid_shapes_and_pending_offer_are_rejected(self):
        self.initialize()
        body = self.body("escalate", reason="Needs help", evidence_event_ids=[self.source("Please help")])
        self.error("workflow_conflict", self.store.coordination_command, "demo-1", "stale", {**body, "expected_workflow_version": 0})
        self.error("invalid_coordination_request", self.store.coordination_command, "demo-1", "bool", {**body, "expected_workflow_version": True})
        self.error("invalid_coordination_request", self.store.coordination_command, "demo-1", "extra", {**body, "clock_override": "tomorrow"})
        state = self.command("escalate", reason="Needs help", evidence_event_ids=[self.source("Please help")])
        self.assertEqual(state["phase"], "escalated")

    def test_concurrent_same_version_admits_one_and_restart_preserves_receipt(self):
        self.initialize()
        eid = self.source("Cancel please")
        body = self.body("request_cancellation", evidence_event_ids=[eid])
        def submit(index):
            try:
                return self.store.coordination_command("demo-1", "concurrent-" + str(index), body)
            except ValueError as error:
                return error.code
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(submit, (1, 2)))
        self.assertEqual(sum(isinstance(result, dict) for result in results), 1)
        self.assertIn("revision_conflict", results)
        saved = next(result for result in results if isinstance(result, dict))
        self.store.close()
        self.store = platform.PlatformStore(DSN, schema=self.schema)
        self.assertEqual(self.store.coordination_detail("demo-1"), saved)

    def test_audit_failure_rolls_back_workflow_head_and_idempotency(self):
        initial = self.initialize()
        eid = self.source("Cancel please")
        before = self.store.get("demo-1")
        body = self.body("request_cancellation", evidence_event_ids=[eid])
        with self.store._transaction(write=True) as connection:
            connection.execute("""CREATE FUNCTION reject_coord_audit() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN RAISE EXCEPTION 'injected audit failure'; END $$""")
            connection.execute("CREATE TRIGGER reject_coord_audit BEFORE INSERT ON case_snapshots FOR EACH ROW EXECUTE FUNCTION reject_coord_audit()")
        self.error("case_storage_error", self.store.coordination_command, "demo-1", "retry", body)
        self.assertEqual(self.store.get("demo-1"), before)
        self.assertEqual(self.store.coordination_detail("demo-1"), initial)
        with self.store._transaction(write=True) as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM platform_requests WHERE scope='coordination:demo-1' AND idempotency_key='retry'").fetchone()[0], 0)
            connection.execute("DROP TRIGGER reject_coord_audit ON case_snapshots")
        self.assertEqual(self.store.coordination_command("demo-1", "retry", body)["phase"], "cancellation_pending")
