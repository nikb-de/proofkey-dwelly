"""Source-only preparation, including chronological evidence boundaries."""
import hashlib
import importlib
import json
from datetime import datetime
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.dwelly_service import cases

try:
    scenarios = importlib.import_module("tools.dwelly_platform.scenarios")
except ModuleNotFoundError:
    scenarios = None

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "docs/demos/2026-10-10-case-001-terms/source.case-001-terms.json"
SOURCE_SHA = "fc1f55e8258346b53f77b5cce03ae6fb7e0b227433daab19894caa4da8d160cf"


class TermsDemoTests(unittest.TestCase):
    def prepare(self, case_id="terms-demo", anchor_date="2026-10-10"):
        self.assertIsNotNone(scenarios, "source-only scenario adapter must exist")
        return scenarios.prepare_terms_demo(case_id, anchor_date)

    def test_source_messages_become_valid_canonical_events_and_keep_original_ids(self):
        demo = self.prepare()
        cases._declaration(demo["declaration"])
        self.assertEqual(demo["declaration"], {
            "case_id": "terms-demo", "links": {"order_id": "DL-001", "customer_id": "vessa_lorne",
            "operator_id": "coordinator"}, "participants": ["coordinator", "vessa_lorne", "dispatch"],
            "language": "en"})
        self.assertEqual([item["event_id"] for item in demo["events"]],
                         ["source-context", "001", "002", "003", "004", "005", "006", "007", "008", "009", "010", "011"])
        for item in demo["events"]:
            cases._event(item, demo["declaration"]["participants"])
            cases._bounded_json({"expected_revision": 0, "event": item})
        self.assertEqual(demo["events"][1]["channel"], "chat")
        self.assertEqual(demo["events"][2]["channel"], "email")
        self.assertEqual(demo["events"][7]["sender_id"], "dispatch")
        self.assertEqual(demo["events"][7]["recipient_ids"], ["coordinator"])

    def test_date_rebasing_changes_timestamps_iso_dates_and_spelled_out_date(self):
        demo = self.prepare()
        events = demo["events"]
        self.assertEqual(events[0]["occurred_at"], "2026-10-10T09:00:00+00:00")
        self.assertEqual(events[-1]["occurred_at"], "2026-10-10T10:31:00+00:00")
        self.assertIn("2026-10-11 09:00–12:00 UTC", events[2]["text"])
        self.assertIn("13 October, 18:00–20:00", events[8]["text"])
        self.assertIn("2026-10-14, 10:00–13:00 UTC", events[8]["text"])
        self.assertNotIn("2026-02-", json.dumps(events))
        self.assertEqual([datetime.fromisoformat(e["occurred_at"]) for e in events],
                         sorted(datetime.fromisoformat(e["occurred_at"]) for e in events))

    def test_identity_transform_preserves_every_original_message_byte(self):
        raw = SOURCE.read_bytes()
        document = json.loads(raw)
        demo = self.prepare(anchor_date="2026-02-02")
        for step, event in zip(document["steps"], demo["events"][1:]):
            source_message = next(m for m in step["state_after"]["messages"]
                                  if m["event_id"] == step["event"]["id"])
            self.assertEqual(event["text"], source_message["body"])
        self.assertEqual(SOURCE.read_bytes(), raw)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), SOURCE_SHA)

    def test_context_has_initial_facts_and_separately_labelled_configured_dispatch(self):
        context = json.loads(self.prepare()["events"][0]["text"])
        self.assertEqual([actor["id"] for actor in context["source_actors"]], ["coordinator", "vessa_lorne"])
        self.assertEqual(context["demo_configuration"]["actor_directory"][0]["id"], "dispatch")
        self.assertEqual(context["demo_configuration"]["qualification"], "configured_routing_not_source_identity_or_authentication")
        self.assertIn("Shipment DL-001.", [fact["text"] for fact in context["source_facts"]])
        self.assertIn("2026-10-11", context["source_facts"][2]["text"])

    def test_every_cutoff_contains_only_initial_context_and_its_visible_source_prefix(self):
        demo = self.prepare(anchor_date="2026-02-02")
        document = json.loads(SOURCE.read_bytes())
        forbidden = {"agent_state", "explanation", "next_action", "decision", "result", "success_criteria", "requests"}
        context = json.loads(demo["events"][0]["text"])
        self.assertTrue(forbidden.isdisjoint(context))
        self.assertNotIn("2026-02-06", demo["events"][0]["text"])
        for cutoff in range(12):
            visible = demo["events"][:cutoff + 1]
            self.assertEqual(len(visible), cutoff + 1)
            for i, event in enumerate(visible[1:], 1):
                messages = document["steps"][i - 1]["state_after"]["messages"]
                current = next(m for m in messages if m["event_id"] == event["event_id"])
                self.assertEqual(event["text"], current["body"])
                self.assertEqual(set(event), cases.EVENT_FIELDS)
            cases._snapshot(demo["declaration"], visible)

    def test_provenance_records_source_transform_and_development_qualification(self):
        provenance = self.prepare()["provenance"]
        self.assertEqual(provenance["source_sha256"], SOURCE_SHA)
        self.assertEqual(provenance["source_commit"], "15ec6c7faa1d48b0bd6ac9093936d2cc8f69a53c")
        self.assertEqual(provenance["qualification"], "author_labels_unvalidated")
        self.assertEqual(provenance["split"], "development")
        self.assertEqual(provenance["date_transform"]["source_anchor_date"], "2026-02-02")
        self.assertEqual(provenance["date_transform"]["anchor_date"], "2026-10-10")
        self.assertEqual(len(provenance["event_mapping"]), 11)
        self.assertEqual(provenance["event_mapping"][0]["source_channel"], "Customer portal")

    def test_source_derived_terms_keep_unsupported_original_fields_unknown(self):
        demo = self.prepare()
        self.assertEqual(demo["original_booking"]["terms"]["slot_start"], "2026-10-11T09:00:00+00:00")
        self.assertEqual(demo["original_booking"]["terms"]["slot_end"], "2026-10-11T12:00:00+00:00")
        self.assertEqual(demo["original_booking"]["booking_id"], "demo-booking-DL-001")
        self.assertEqual(demo["original_booking"]["terms"]["charge"], {"amount_minor": None, "currency": None})
        self.assertEqual(demo["original_booking"]["terms"]["handover"], "unspecified")
        self.assertIsNone(demo["original_booking"]["terms"]["recipient_present"])
        self.assertEqual(demo["provenance"]["configured_routing"]["original_booking_id"], {
            "value": "demo-booking-DL-001", "qualification": "synthetic_local_id_not_source_booking_reference"})
        self.assertEqual(demo["offered_terms"]["slot_start"], "2026-10-14T10:00:00+00:00")
        self.assertEqual(demo["offered_terms"]["handover"], "recipient_only")
        self.assertIs(demo["offered_terms"]["recipient_present"], True)
        self.assertEqual(demo["offered_terms"]["charge"], {"amount_minor": 0, "currency": None})
        self.assertEqual(demo["provenance"]["term_evidence"]["offered_terms"], ["007"])

    def test_unsafe_case_ids_and_noncanonical_dates_fail_closed(self):
        for invalid in (True, None, 12, "", "../terms", "terms/foo", "x" * 65):
            with self.subTest(case_id=invalid), self.assertRaises(cases.CaseError):
                self.prepare(case_id=invalid)
        for invalid in (True, None, 12, "", "2026-2-2", "2026-02-30", "2026-02-02T00:00:00Z", "9999-12-31"):
            with self.subTest(anchor_date=invalid), self.assertRaises(cases.CaseError):
                self.prepare(anchor_date=invalid)

    def test_changed_frozen_source_is_rejected_before_parsing(self):
        self.assertIsNotNone(scenarios)
        with patch.object(Path, "read_bytes", return_value=b'{"unexpected": true}'):
            with self.assertRaisesRegex(ValueError, "scenario_source_hash_mismatch"):
                self.prepare()

    def test_mutating_one_prepared_result_does_not_change_later_calls(self):
        first = self.prepare()
        first["events"][1]["text"] = "Changed by caller"
        first["declaration"]["participants"].append("someone")
        second = self.prepare()
        self.assertNotEqual(first["events"][1]["text"], second["events"][1]["text"])
        self.assertNotIn("someone", second["declaration"]["participants"])
