"""Read-only presentation data preserves recorded cutoffs and receipt meaning."""
import copy
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

try:
    showcase = importlib.import_module("tools.dwelly_platform.showcase")
except ModuleNotFoundError:
    showcase = None


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def capture(mode="llm"):
    """Small complete capture contract; no provider, database, or UI doubles."""
    source = [
        ("source-context", "coordinator", "internal", "Internal original booking context"),
        ("001", "vessa_lorne", "chat", "Please help move my lamp delivery."),
        ("audit-init", "coordinator", "internal", "internal audit must not appear"),
        ("audit-cancel", "coordinator", "internal", "internal cancellation audit"),
        ("002", "coordinator", "email", "Please cancel the morning delivery."),
        ("003", "dispatch", "email", "The original booking is cancelled."),
        ("readback-cancel", "dispatch", "email", "sandbox cancellation readback"),
        ("audit-cancelled", "coordinator", "internal", "internal confirmed audit"),
        ("004", "coordinator", "chat", "What delivery terms should I ask for?"),
        ("005", "vessa_lorne", "chat", "Please book 2026-10-13, 18:00–20:00 UTC. If I am not home, the concierge can take the lamp."),
        ("006", "coordinator", "email", "Can you book the requested evening and concierge?"),
        ("007", "dispatch", "email", "We can offer 2026-10-14, 10:00–13:00 UTC. The recipient must be present. There is no charge."),
        ("audit-offer", "coordinator", "internal", "internal offered audit"),
        ("008", "coordinator", "chat", "Please review the daytime offer, recipient present, no charge."),
        ("009", "vessa_lorne", "chat", "Yes. Book 2026-10-14, 10:00–13:00 UTC. I will be home."),
        ("audit-consent", "coordinator", "internal", "internal consent audit"),
        ("audit-request", "coordinator", "internal", "internal request audit"),
        ("010", "coordinator", "email", "Please book the accepted daytime slot."),
        ("011", "dispatch", "email", "Booking confirmed. This is not completed delivery."),
        ("readback-booking", "dispatch", "email", "sandbox booking readback"),
        ("audit-confirmed", "coordinator", "internal", "internal confirmed audit"),
    ]
    events = [{"event_id": eid, "sender_id": sender, "channel": channel,
               "recipient_ids": ["coordinator"], "kind": "message", "text": text,
               "occurred_at": "2026-10-10T09:10:00+00:00", "media": None}
              for eid, sender, channel, text in source]
    original = {"slot_start": "2026-10-11T09:00:00+00:00", "slot_end": "2026-10-11T12:00:00+00:00",
                "handover": "unspecified", "recipient_present": None,
                "charge": {"amount_minor": None, "currency": None}}
    offered = {"slot_start": "2026-10-14T10:00:00+00:00", "slot_end": "2026-10-14T13:00:00+00:00",
               "handover": "recipient_only", "recipient_present": True,
               "charge": {"amount_minor": 0, "currency": None}}
    report = {"case_id": "capture-case", "mode": mode, "status": "passed", "external_effects": 0,
              "physical_delivery": "not_confirmed", "model_calls": 5 if mode == "llm" else 0,
              "models": [], "http": [], "raw_video": "/private/raw.webm", "api_key": "secret",
              "provenance": {"source_sha256": "a" * 64, "source_path": "docs/source.json",
                             "qualification": "author_labels_unvalidated",
                             "date_transform": {"source_anchor_date": "2026-02-02", "anchor_date": "2026-10-10", "offset_days": 250, "timezone": "UTC"}}}
    for revision in range(22):
        snapshot = {"case_id": "capture-case", "revision": revision,
                    "links": {"order_id": "DL-001", "customer_id": "vessa_lorne", "operator_id": "coordinator"},
                    "participants": ["vessa_lorne", "coordinator", "dispatch"],
                    "language": "en", "schema_version": "dwelly-local-case-v1", "source_mode": "local_fixture",
                    "runtime_binding": None, "needs_analysis": True, "analysis_status": "pending_not_started",
                    "authorization": "unverified", "operational_effects": 0,
                    "previous_snapshot_hash": report["http"][-1]["response"]["case"]["snapshot"]["snapshot_hash"] if revision else None,
                    "events": copy.deepcopy(events[:revision])}
        snapshot["snapshot_hash"] = digest(snapshot)
        phase = ("booking_confirmed" if revision >= 21 else "booking_pending" if revision >= 17 else
                 "ready_to_book" if revision >= 16 else "awaiting_consent" if revision >= 13 else
                 "awaiting_terms" if revision >= 8 else "cancellation_pending" if revision >= 4 else "booked")
        coordination = {"case_id": "capture-case", "version": 7 if revision == 21 else 1,
                        "phase": phase, "revision": revision, "snapshot_hash": snapshot["snapshot_hash"],
                        "mode": "local_sandbox", "external_effects": 0, "physical_delivery": "not_confirmed",
                        "original_booking": {"booking_id": "synthetic-original", "terms": original},
                        "offer": {"offer_id": "offer-id", "terms_hash": digest(offered), "terms": offered,
                                  "created_revision": 13, "evidence_event_ids": ["007"]} if revision >= 13 else None,
                        "consent": {"offer_id": "offer-id", "terms_hash": digest(offered), "created_revision": 16,
                                    "evidence_event_ids": ["009"]} if revision >= 16 else None,
                        "pending_request": {"kind": "booking", "request_id": "booking-request", "created_revision": 17,
                                            "terms_hash": digest(offered), "mode": "local_sandbox", "external_effects": 0} if 17 <= revision < 21 else None,
                        "operation_receipts": [], "audit_history": [{"text": "do not expose internal audit"}]}
        if revision == 21:
            coordination["operation_receipts"] = [{"kind": "booking", "status": "confirmed_locally",
                "mode": "local_sandbox", "request_id": "booking-request", "terms_hash": digest(offered), "created_revision": 17,
                "evidence_event_ids": ["readback-booking"], "external_effects": 0}]
        detail = {"case_id": "capture-case", "snapshot": snapshot, "coordination": copy.deepcopy(coordination)}
        report["http"].append({"status": 200, "response": {"case": detail}})
    report["final"] = copy.deepcopy(report["http"][-1]["response"]["case"])
    if mode == "llm":
        for index, revision in enumerate([3, 10, 12, 15, 20]):
            snapshot = report["http"][revision]["response"]["case"]["snapshot"]
            evidence = ["001", "005", "007", "009", "011"][index]
            model_input = {"schema_version": "proofkey-step-input-v1", "case_id": "capture-case",
                           "step_index": revision, "cutoff_event_id": snapshot["events"][-1]["event_id"],
                           "goal": "Review the available case evidence and propose the next coordination step.",
                           "our_actor_id": "coordinator",
                           "actors": [{"id": actor, "name": actor, "role": "declared participant"}
                                      for actor in snapshot["participants"]],
                           "messages": [{"event_id": event["event_id"], "from_actor": event["sender_id"],
                                         "to_actor": event["recipient_ids"][0], "body": event["text"],
                                         "body_source": "body", "timestamp": event["occurred_at"],
                                         "channel": event["channel"]} for event in snapshot["events"]]}
            model_input["input_hash"] = digest(model_input)
            report["models"].append({"run_id": f"run-{index}", "case_id": "capture-case", "status": "succeeded",
                "step_index": revision, "source": {"kind": "platform_case", "case_id": "capture-case", "revision": revision, "snapshot_hash": snapshot["snapshot_hash"]},
                "input": model_input, "input_hash": model_input["input_hash"], "reference": None,
                "candidate": {"input_hash": model_input["input_hash"], "evidence_event_ids": [evidence], "next_action": {
                    "type": "request_information" if index == 0 else "propose_forwarding", "target_actor_id": "vessa_lorne",
                    "description": "Ask the recipient for alternative times." if index == 0 else f"Recorded proposal {index}."}},
                "receipt": {"provider": "openai", "observed_model": "gpt-6.1-sol", "requested_model": "gpt-6.1-sol", "latency_ms": 3000},
                "transaction": {"operational_effects": 0, "dispatch_attempts": 1, "automatic_retries": 0}})
    return report


class ShowcaseTests(unittest.TestCase):
    def build(self, report=None):
        self.assertIsNotNone(showcase, "read-only showcase builder must exist")
        return showcase.build_showcase(report or capture())

    def test_llm_scenes_preserve_source_cutoffs_and_verbatim_proposals(self):
        bundle = self.build()
        self.assertEqual(bundle["schema_version"], "proofkey-showcase-v1")
        self.assertEqual(bundle["case_id"], "capture-case")
        self.assertEqual([s["id"] for s in bundle["scenes"]], ["request", "review", "change", "consent", "confirmed"])
        self.assertEqual([s["source_event_ids"] for s in bundle["scenes"]], [["001"], ["004", "005", "006"], ["007"], ["008", "009"], ["010", "011"]])
        self.assertEqual([s["phase"] for s in bundle["scenes"]], ["booked", "awaiting_terms", "awaiting_consent", "awaiting_consent", "booking_confirmed"])
        self.assertEqual([s["model"]["source_revision"] if s["model"] else None for s in bundle["scenes"]], [3, 10, 12, None, 20])
        self.assertEqual(bundle["scenes"][0]["model"]["action"], "request_information")
        self.assertEqual(bundle["scenes"][0]["model"]["description"], "Ask the recipient for alternative times.")
        self.assertTrue(all(m["advisory_only"] for m in bundle["model_receipts"]))
        self.assertEqual([m["event_id"] for m in bundle["scenes"][3]["messages"]], ["008"])
        self.assertEqual(bundle["scenes"][3]["acceptance_message"]["event_id"], "009")
        self.assertEqual(bundle["scenes"][3]["snapshot_revision"], 14)
        self.assertEqual(bundle["scenes"][3]["post_acceptance_model"]["source_revision"], 15)

    def test_terms_keep_unknown_price_and_explicit_attendance(self):
        bundle = self.build()
        self.assertEqual(bundle["requested_terms"], {"slot_start": "2026-10-13T18:00:00+00:00", "slot_end": "2026-10-13T20:00:00+00:00", "handover": "concierge_allowed", "recipient_present": False, "charge": {"amount_minor": None, "currency": None}})
        self.assertIsNone(bundle["original_terms"]["charge"]["amount_minor"])
        self.assertEqual(bundle["offered_terms"]["charge"], {"amount_minor": 0, "currency": None})
        self.assertIs(bundle["offered_terms"]["recipient_present"], True)

    def test_synthetic_capture_does_not_acquire_model_identity(self):
        bundle = self.build(capture("synthetic"))
        self.assertEqual(bundle["mode"], "synthetic")
        self.assertTrue(all(scene["model"] is None for scene in bundle["scenes"]))
        self.assertIn("replay", bundle["scenes"][0]["qualification"].lower())
        self.assertEqual(bundle["source"]["qualification"], "author_labels_unvalidated")
        self.assertEqual(bundle["source"]["date_transform"]["offset_days"], 250)

    def test_provider_receipt_identity_is_preserved_without_transport_secrets(self):
        report = capture()
        report["models"][0]["receipt"].update(request_id="req_recorded", usage={"input_tokens": 1366, "output_tokens": 163}, api_key="secret")
        report["models"][0]["transaction"]["idempotency_key"] = "private-request-key"
        model = self.build(report)["model_receipts"][0]
        self.assertEqual(model.get("request_id"), "req_recorded")
        self.assertEqual(model["usage"], {"input_tokens": 1366, "output_tokens": 163})
        self.assertEqual(model["status"], "succeeded")
        self.assertEqual(model["input_hash"], digest({k: v for k, v in report["models"][0]["input"].items() if k != "input_hash"}))
        self.assertNotIn("secret", json.dumps(model))
        self.assertNotIn("private-request-key", json.dumps(model))

    def test_earlier_scenes_have_no_final_receipt_or_raw_internal_content(self):
        report = capture()
        report["final"]["private_note"] = "future replacement must not change earlier source"
        bundle = self.build(report)
        self.assertEqual(bundle["scenes"][0]["messages"][0]["text"], "Please help move my lamp delivery.")
        self.assertTrue(all(not scene["coordination"]["operation_receipts"] for scene in bundle["scenes"][:-1]))
        rendered = json.dumps(bundle)
        for forbidden in ("raw_video", "api_key", "/private/", "audit_history", "internal audit must not appear", "future replacement"):
            self.assertNotIn(forbidden, rendered)
        self.assertEqual(bundle["receipt"], {"booking_confirmed": True, "external_effects": 0, "physical_delivery": "not_confirmed", "request_id": "booking-request"})

    def test_rejects_foreign_or_future_model_binding(self):
        for field, value in (("case_id", "another-case"), ("snapshot_hash", "d" * 64), ("revision", 21)):
            report = capture()
            report["models"][0]["source"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.build(report)
        report = capture()
        report["models"][0]["candidate"]["evidence_event_ids"] = ["011"]
        with self.assertRaises(ValueError):
            self.build(report)

    def test_rejects_changed_model_content_even_when_event_ids_still_match(self):
        for field, value in (("body", "Future booking confirmed."), ("from_actor", "dispatch"),
                             ("timestamp", "2030-01-01T00:00:00Z")):
            for rehash in (False, True):
                report = capture()
                job = report["models"][0]
                job["input"]["messages"][1][field] = value
                if rehash:
                    changed_hash = digest({k: v for k, v in job["input"].items() if k != "input_hash"})
                    job["input_hash"] = job["input"]["input_hash"] = job["candidate"]["input_hash"] = changed_hash
                with self.subTest(field=field, rehash=rehash), self.assertRaises(ValueError):
                    self.build(report)

    def test_rejects_reordered_model_messages_and_forged_input_hashes(self):
        report = capture()
        report["models"][0]["input"]["messages"].reverse()
        with self.assertRaises(ValueError):
            self.build(report)
        report = capture()
        job = report["models"][0]
        job["input_hash"] = job["input"]["input_hash"] = job["candidate"]["input_hash"] = "c" * 64
        with self.assertRaises(ValueError):
            self.build(report)

    def test_rejects_snapshot_content_changed_without_its_hash(self):
        report = capture()
        report["http"][3]["response"]["case"]["snapshot"]["events"][1]["text"] = "Forged source."
        with self.assertRaises(ValueError):
            self.build(report)

    def test_rejects_future_coordination_in_an_early_scene(self):
        report = capture()
        report["http"][3]["response"]["case"]["coordination"] = copy.deepcopy(report["final"]["coordination"])
        with self.assertRaises(ValueError):
            self.build(report)

    def test_accepts_older_coordination_bound_to_its_recorded_snapshot(self):
        report = capture()
        report["http"][11]["response"]["case"]["coordination"] = copy.deepcopy(report["http"][8]["response"]["case"]["coordination"])
        scene = self.build(report)["scenes"][1]
        self.assertEqual(scene["snapshot_revision"], 11)
        self.assertEqual(scene["coordination"]["revision"], 8)
        self.assertEqual(scene["phase"], "awaiting_terms")

    def test_rejects_coordination_without_matching_historical_hash(self):
        report = capture()
        report["http"][11]["response"]["case"]["coordination"]["snapshot_hash"] = "f" * 64
        with self.assertRaises(ValueError):
            self.build(report)

    def test_rejects_nested_coordination_records_after_the_cutoff(self):
        for field in ("offer", "consent", "pending_request", "operation_receipts"):
            report = capture()
            target = report["final"]["coordination"][field]
            if field == "pending_request":
                target = copy.deepcopy(report["http"][17]["response"]["case"]["coordination"][field])
                report["final"]["coordination"][field] = target
            if isinstance(target, list):
                target = target[0]
            target["created_revision"] = 22
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.build(report)

    def test_rejects_nested_record_without_its_recorded_creation_cutoff(self):
        report = capture()
        report["http"].pop(16)
        with self.assertRaises(ValueError):
            self.build(report)

    def test_rejects_nested_evidence_outside_coordination_snapshot(self):
        for field in ("offer", "consent", "operation_receipts"):
            report = capture()
            coordination = report["http"][14]["response"]["case"]["coordination"]
            if field != "offer":
                coordination[field] = copy.deepcopy(report["final"]["coordination"][field])
            target = coordination[field][0] if isinstance(coordination[field], list) else coordination[field]
            target["created_revision"] = 13
            target["evidence_event_ids"] = ["011"]
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.build(report)

    def test_rejects_offer_terms_changed_without_the_recorded_hash(self):
        report = capture()
        report["final"]["coordination"]["offer"]["terms"]["charge"]["amount_minor"] = 10000
        with self.assertRaises(ValueError):
            self.build(report)

    def test_rejects_unconfirmed_or_externally_effectful_receipt(self):
        for change in ({"phase": "booking_pending"}, {"external_effects": 1}, {"physical_delivery": "confirmed"}, {"operation_receipts": []}):
            report = capture()
            report["final"]["coordination"].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.build(report)

    def test_final_receipt_requires_matching_consent_and_recorded_snapshot(self):
        for field, value in (("consent", None), ("snapshot_hash", "f" * 64), ("revision", 20)):
            report = capture()
            report["final"]["coordination"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.build(report)
        report = capture()
        report["final"]["coordination"]["consent"]["terms_hash"] = "f" * 64
        with self.assertRaises(ValueError):
            self.build(report)

    def test_rejects_incomplete_or_failed_capture_without_filling_future_data(self):
        for mutate in (lambda r: r.update(status="failed"), lambda r: r["http"].pop(3), lambda r: r["models"].pop()):
            report = capture()
            mutate(report)
            with self.assertRaises(ValueError):
                self.build(report)

    def test_cli_writes_bundle_without_modifying_the_report(self):
        self.assertIsNotNone(showcase, "read-only showcase builder must exist")
        with tempfile.TemporaryDirectory() as temporary:
            report_path, output = Path(temporary) / "capture.json", Path(temporary) / "bundle.json"
            raw = json.dumps(capture())
            report_path.write_text(raw)
            result = subprocess.run([sys.executable, "-m", "tools.dwelly_platform.showcase", "--report", str(report_path), "--output", str(output)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(output.read_text())["case_id"], "capture-case")
            self.assertEqual(report_path.read_text(), raw)
            same = subprocess.run([sys.executable, "-m", "tools.dwelly_platform.showcase", "--report", str(report_path), "--output", str(report_path)], capture_output=True, text=True)
            self.assertNotEqual(same.returncode, 0)
            self.assertEqual(report_path.read_text(), raw)


if __name__ == "__main__":
    unittest.main()
