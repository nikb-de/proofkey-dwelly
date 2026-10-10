"""Offline controls for routing proxies and the unsent proposal contract."""
import copy
import hashlib
import inspect
import json
import unittest

from tools.dwelly_cases.baseline import propose
from tools.dwelly_cases.evaluation import assess


def event(number, body, sender="Customer", recipients="Delivery provider", channel="Email"):
    return {
        "event_id": f"event-{number:03d}", "occurred_at": f"2026-10-01T10:{number:02d}:00+00:00",
        "stage": "Context" if number == 1 else "Escalation", "channel": channel,
        "sender": sender, "recipients": recipients, "body": body,
        "source_ref": f"Delivery & Logistics/001/history.md#event-{number:03d}",
    }


def snapshot(events=None, case_id="delivery-logistics-001"):
    result = {
        "schema_version": "dwelly-snapshot-v1", "case_id": case_id,
        "track": "Delivery & Logistics", "cutoff_event": "event-002",
        "events": events or [event(1, "The parcel has not arrived."),
                              event(2, "Can you ask the delivery provider for an update?")],
        "attachments": [],
    }
    result["input_hash"] = hashlib.sha256(json.dumps(
        result, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    return result


def reference(source, recipient="Delivery provider", channel="Email"):
    action = event(3, "A historical example, never input to propose.", "Agent", recipient, channel)
    action["stage"] = "Agent action"
    return {"schema_version": "dwelly-reference-v1", "case_id": source["case_id"],
            "input_hash": source["input_hash"], "action": action,
            "later_events": [], "index_source": "Delivery & Logistics/001/index.md"}


class BaselineTests(unittest.TestCase):
    def test_offered_slots_require_customer_choice(self):
        source = snapshot([event(1, "Available slots: Tuesday 10:00 or Wednesday 14:00.",
                                 "Delivery provider", "Customer"),
                           event(2, "I need to reschedule, which can you arrange?")])
        result = propose(source)
        self.assertEqual(result["action"]["kind"], "request_customer_choice")
        self.assertEqual(result["action"]["recipient"], "Customer")
        self.assertIn("choose", result["action"]["message"].lower())
        self.assertEqual(result["status"], "proposed_unsent")
        self.assertEqual(result["effects"], [])
        self.assertTrue(result["evidence_refs"])

    def test_named_recipient_suffix_requires_choice_without_role_rewriting(self):
        source = snapshot([event(1, "Available slots: Tuesday 10:00 or Wednesday 14:00.",
                                 "Courier dispatch", "Vessa Lorne"),
                           event(2, "I need to reschedule, which can you arrange?",
                                 "Vessa Lorne, recipient", "Courier dispatch")])
        action = propose(source)["action"]
        self.assertEqual(action["kind"], "request_customer_choice")
        self.assertEqual(action["recipient"], "Vessa Lorne, recipient")

    def test_canonical_visible_rescheduling_inventory_requires_choice(self):
        source = snapshot([
            {"body": "DL-001 is booked for 2026-02-03, 09:00–12:00 UTC. Our rescheduling inventory currently has 2026-02-03 15:00–18:00 or 2026-02-04 10:00–13:00. There is no rescheduling charge.",
             "channel": "Email", "event_id": "event-001", "occurred_at": "2026-02-02T09:00:00+00:00",
             "recipients": "Iona Quill, Rivet Delivery Desk", "sender": "Dispatch, Plover Arc Logistics",
             "source_ref": "Delivery & Logistics/001/history.md#event-001", "stage": "Context"},
            {"body": "I have a work meeting during the morning delivery. Could you help move my lamp delivery? Please use this order-linked message thread.",
             "channel": "Customer portal", "event_id": "event-002", "occurred_at": "2026-02-02T09:10:00+00:00",
             "recipients": "Iona Quill, Rivet Delivery Desk", "sender": "Vessa Lorne, recipient",
             "source_ref": "Delivery & Logistics/001/history.md#event-002", "stage": "Escalation"},
        ])
        self.assertEqual(source["input_hash"], "61a5aba50bf8ec8d244f3f8da871f3b572c3859141a8c40e2a52bf8bb19285e7")
        action = propose(source)["action"]
        self.assertEqual(action["kind"], "request_customer_choice")
        self.assertEqual(action["recipient"], "Vessa Lorne, recipient")
        self.assertEqual(action["channel"], "Customer portal")

    def test_single_window_start_and_end_are_not_two_choices(self):
        source = snapshot([event(1, "Available delivery slot: 2026-02-03 15:00–18:00 UTC.",
                                 "Delivery provider", "Customer"),
                           event(2, "I need to reschedule my delivery.")])
        self.assertEqual(propose(source)["action"]["kind"], "contact_provider")

    def test_missing_address_requests_apartment_and_access(self):
        source = snapshot([event(1, "Driver cannot deliver: apartment number and access code are missing.",
                                 "Delivery provider", "Customer")])
        action = propose(source)["action"]
        self.assertEqual(action["kind"], "request_missing_details")
        self.assertEqual(action["recipient"], "Customer")
        self.assertIn("apartment", action["message"].lower())
        self.assertIn("access", action["message"].lower())

    def test_explicit_slot_choice_is_not_requested_again(self):
        source = snapshot([event(1, "Available slots: Tuesday 10:00 or Wednesday 14:00.",
                                 "Delivery provider", "Customer"),
                           event(2, "Tuesday 10:00 works; please book that delivery slot.")])
        self.assertEqual(propose(source)["action"]["kind"], "contact_provider")

    def test_only_missing_apartment_is_requested(self):
        source = snapshot([event(1, "The apartment number is missing from the delivery address.",
                                 "Courier dispatch", "Customer")])
        message = propose(source)["action"]["message"].lower()
        self.assertIn("apartment", message)
        self.assertNotIn("access", message)
        self.assertNotIn("code", message)

    def test_missing_access_never_requests_permanent_door_code(self):
        source = snapshot([event(1, "The courier needs access instructions for the locked entrance.",
                                 "Courier dispatch", "Customer")])
        action = propose(source)["action"]
        self.assertEqual(action["kind"], "request_missing_details")
        self.assertIn("access", action["message"].lower())
        self.assertNotIn("code", action["message"].lower())

    def test_customer_evidence_request(self):
        source = snapshot([event(1, "Please request photos of the damaged parcel from the customer.",
                                 "Delivery provider", "Customer")])
        action = propose(source)["action"]
        self.assertEqual(action["kind"], "request_evidence")
        self.assertEqual(action["recipient"], "Customer")
        self.assertIn("photo", action["message"].lower())

    def test_damage_intake_requests_photos_from_named_visible_recipient(self):
        source = snapshot([event(1, "Please send the required photos of the damaged parcel.",
                                 "Damage intake, Tallowmere Goods", "Vessa Lorne")])
        action = propose(source)["action"]
        self.assertEqual(action["kind"], "request_evidence")
        self.assertEqual(action["recipient"], "Vessa Lorne")
        self.assertEqual(action["channel"], "Email")

    def test_fallback_contacts_observed_provider_without_claiming_resolution(self):
        source = snapshot()
        result = propose(source)
        self.assertEqual(result["action"]["kind"], "contact_provider")
        self.assertEqual(result["action"]["recipient"], "Delivery provider")
        self.assertEqual(result["action"]["channel"], "Email")
        self.assertEqual(result["effects"], [])
        self.assertTrue(assess(source, result, reference(source))["contract_pass"])

    def test_safety_escalation_never_claims_emergency_action(self):
        source = snapshot([event(1, "There is a gas leak at the entrance; immediate danger.")])
        action = propose(source)["action"]
        self.assertEqual(action["kind"], "safety_escalation")
        self.assertEqual(action["recipient"], "operator")
        self.assertEqual(action["channel"], "internal")
        self.assertIn("review", action["message"].lower())

    def test_unknown_context_and_missing_roles_abstain(self):
        source = snapshot([event(1, "Handle this somehow.", "Unknown person", "Support desk")])
        result = propose(source)
        self.assertEqual(result["action"]["kind"], "operator_review")
        self.assertEqual(result["effects"], [])
        self.assertTrue(result["limitations"])

    def test_generic_recipient_label_does_not_establish_customer_role(self):
        source = snapshot([event(1, "Apartment number is missing from the address.",
                                 "Unknown person", "Recipient")])
        self.assertEqual(propose(source)["action"]["kind"], "operator_review")

    def test_reference_is_not_parameter_and_case_id_does_not_choose_policy(self):
        self.assertEqual(list(inspect.signature(propose).parameters), ["snapshot"])
        first, second = snapshot(), snapshot(case_id="delivery-logistics-999")
        self.assertEqual(propose(first)["action"], propose(second)["action"])
        before = copy.deepcopy(first)
        propose(first)
        self.assertEqual(first, before)

    def test_repeat_and_case_order_are_deterministic(self):
        cases = [snapshot(), snapshot([event(1, "Unknown", "A", "B")], "delivery-logistics-999")]
        direct = {case["case_id"]: propose(case) for case in cases}
        reverse = {case["case_id"]: propose(case) for case in reversed(cases)}
        self.assertEqual(direct, reverse)
        self.assertEqual(propose(cases[0]), propose(cases[0]))


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.source = snapshot()
        self.proposal = propose(self.source)
        self.reference = reference(self.source)

    def test_good_control_only_measures_contract_and_route(self):
        result = assess(self.source, self.proposal, self.reference)
        self.assertEqual(result["output_status"], "valid")
        self.assertTrue(result["contract_pass"])
        self.assertTrue(result["routing_agreement"])
        self.assertEqual(result["semantic_correctness"], "unassessed")
        self.assertEqual(result["qualification"], "development_only_unqualified")
        self.assertNotIn("score", result)

    def test_wrong_route_is_not_semantic_incorrectness(self):
        self.proposal["action"]["recipient"] = "Customer"
        result = assess(self.source, self.proposal, self.reference)
        self.assertTrue(result["contract_pass"])
        self.assertFalse(result["routing_agreement"])
        self.assertEqual(result["semantic_correctness"], "unassessed")

    def test_completion_and_effects_fail_despite_matching_route(self):
        for field, value in (("effects", [{"kind": "payment"}]),
                             ("status", "completed"),
                             ("message", "We have completed the payment.")):
            with self.subTest(field=field):
                proposal = copy.deepcopy(self.proposal)
                if field == "message":
                    proposal["action"][field] = value
                else:
                    proposal[field] = value
                result = assess(self.source, proposal, self.reference)
                self.assertFalse(result["contract_pass"])
                self.assertEqual(result["output_status"], "invalid")
                self.assertTrue(result["violations"])
                self.assertTrue(result["routing_agreement"])
                self.assertEqual(result["semantic_correctness"], "unassessed")

    def test_missing_or_malformed_outputs_remain_explicit(self):
        for proposal, status in ((None, "missing"), ({}, "invalid"), ([], "invalid"),
                                 ({"action": {"recipient": 1, "channel": []}}, "invalid")):
            with self.subTest(proposal=proposal):
                result = assess(self.source, proposal, self.reference)
                self.assertEqual(result["output_status"], status)
                self.assertFalse(result["contract_pass"])
                self.assertIsNone(result["routing_agreement"])
                self.assertTrue(result["violations"])
                self.assertNotIn("score", result)

    def test_normalizes_only_case_and_whitespace_not_role_suffixes(self):
        self.proposal["action"]["recipient"] = " delivery   PROVIDER "
        self.proposal["action"]["channel"] = " email "
        self.assertTrue(assess(self.source, self.proposal, self.reference)["routing_agreement"])
        self.proposal["action"]["recipient"] = "Delivery provider, recipient"
        self.assertFalse(assess(self.source, self.proposal, self.reference)["routing_agreement"])

    def test_identity_citations_and_unknown_fields_are_checked(self):
        for field, value in (("input_hash", "wrong"), ("case_id", "wrong"),
                             ("evidence_refs", []), ("evidence_refs", ["event-003"]),
                             ("hidden_instruction", "send now")):
            with self.subTest(field=field):
                proposal = copy.deepcopy(self.proposal)
                proposal[field] = value
                self.assertFalse(assess(self.source, proposal, self.reference)["contract_pass"])

    def test_nested_malformed_values_are_invalid_without_crashing(self):
        for key in ("kind", "recipient", "channel", "message"):
            for value in ([], {}, True, None):
                with self.subTest(key=key, value=value):
                    proposal = copy.deepcopy(self.proposal)
                    proposal["action"][key] = value
                    result = assess(self.source, proposal, self.reference)
                    self.assertEqual(result["output_status"], "invalid")
                    self.assertFalse(result["contract_pass"])
                    self.assertTrue(result["violations"])

    def test_repeated_reordered_evaluation_is_stable_and_does_not_mutate(self):
        inputs = [(self.proposal, self.reference), (None, self.reference)]
        before = copy.deepcopy(inputs)
        forward = [assess(self.source, *pair) for pair in inputs]
        backward = [assess(self.source, *pair) for pair in reversed(inputs)]
        self.assertEqual(forward, list(reversed(backward)))
        self.assertEqual(inputs, before)


if __name__ == "__main__":
    unittest.main()
