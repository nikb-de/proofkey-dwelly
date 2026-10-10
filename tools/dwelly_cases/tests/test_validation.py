import copy
import unittest

from tools.dwelly_cases.baseline import propose
from tools.dwelly_cases.evaluation import assess
from tools.dwelly_cases.importer import digest
from tools.dwelly_cases.runner import validate_snapshot
from tools.dwelly_cases.tests.test_pilot import event, reference, snapshot


class BoundaryValidationTests(unittest.TestCase):
    def assert_invalid_snapshot(self, source):
        source["input_hash"] = digest({k: v for k, v in source.items() if k != "input_hash"})
        with self.assertRaises(ValueError):
            validate_snapshot(source, source["case_id"])

    def test_self_hashed_future_source_reference_is_rejected(self):
        source = snapshot()
        source["events"][0]["source_ref"] = "Delivery & Logistics/001/history.md#event-004"
        self.assert_invalid_snapshot(source)

    def test_malformed_and_reversed_timestamps_rejected(self):
        for value in ("tomorrow", "2026-09-01T00:00:00+00:00", "2026-10-01T10:02:00"):
            source = snapshot()
            source["events"][1]["occurred_at"] = value
            self.assert_invalid_snapshot(source)

    def test_future_or_escaped_attachment_rejected_even_with_valid_self_hash(self):
        for name, first in (("../evaluation/secret.json", "event-001"),
                            ("attachments/a.png", "event-003")):
            source = snapshot()
            source["attachments"] = [{"path": name, "first_seen_event": first,
                                       "size": 3, "sha256": "a" * 64}]
            self.assert_invalid_snapshot(source)

    def test_malformed_reference_is_invalid_not_unscored_success(self):
        source = snapshot()
        for action in (None, {}, {"recipients": [], "channel": "Email"}):
            target = reference(source)
            target["action"] = action
            result = assess(source, propose(source), target)
            self.assertFalse(result["contract_pass"])
            self.assertIn("invalid_reference_action", result["violations"])
            self.assertIsNone(result["routing_agreement"])

    def test_common_unsupported_payment_claims_are_caught(self):
        source = snapshot()
        for text in ("Your refund has been issued.", "We transferred the funds to your account.",
                     "The payment was successful."):
            result = propose(source)
            result["action"]["message"] = text
            verdict = assess(source, result, reference(source))
            self.assertFalse(verdict["contract_pass"])
            self.assertIn("unsupported_completion_claim", verdict["violations"])

    def test_unknown_liquid_leak_is_not_routine_delivery_contact(self):
        source = snapshot([event(1, "An unidentified liquid is leaking from the parcel. Movement stopped.",
                                 "Depot coordinator, Plover Arc Logistics", "Delivery desk"),
                           event(2, "The driver reports an unknown leak; please help.", "Customer", "Delivery desk")])
        self.assertEqual(propose(source)["action"]["kind"], "safety_escalation")

    def test_explicit_safety_takeover_is_not_routine_status_contact(self):
        source = snapshot([
            event(1, "A wet patch is visible under one carton. Contents have not been assessed. Staff have stopped moving it and are keeping clear pending safety review.",
                  "Depot shift coordinator, Plover Arc Logistics", "Delivery desk"),
            event(2, "Please get our safety lead to take over this incident now. Do not route it to a driver or ask the customer to collect it.",
                  "Depot shift coordinator, Plover Arc Logistics", "Delivery desk")])
        self.assertEqual(propose(source)["action"]["kind"], "safety_escalation")


if __name__ == "__main__":
    unittest.main()
