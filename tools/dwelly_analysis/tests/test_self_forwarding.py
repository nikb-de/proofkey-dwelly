"""Offline routing regression tests; retained campaign records are read only."""
import copy
import json
from pathlib import Path
import unittest

from tools.dwelly_analysis import model


CASE = Path(__file__).resolve().parents[3] / "ANSWERS" / "025"
OUTPUT_FIELDS = {"state", "waiting_for", "next_action", "evidence_event_ids", "uncertainty"}


class SelfForwardingTests(unittest.TestCase):
    def setUp(self):
        self.evidence = json.loads((CASE / "INPUT.json").read_text())
        retained = json.loads((CASE / "SOURCE_RESULT.json").read_text())["candidate"]
        self.candidate = {key: retained[key] for key in OUTPUT_FIELDS}

    def parse(self, candidate):
        return model.parse(self.evidence, {"text": json.dumps(candidate)})

    def test_retained_customer_reply_cannot_forward_back_to_our_desk(self):
        evidence_before = copy.deepcopy(self.evidence)
        candidate_before = copy.deepcopy(self.candidate)
        self.assertEqual(self.candidate["next_action"]["target_actor_id"], self.evidence["our_actor_id"])
        self.assertIn("Reply to Lyra Fen (actor-05)", self.candidate["next_action"]["description"])
        with self.assertRaisesRegex(ValueError, "^invalid_model_output$"):
            self.parse(self.candidate)
        self.assertEqual(self.evidence, evidence_before)
        self.assertEqual(self.candidate, candidate_before)

    def test_forwarding_to_visible_customer_remains_accepted(self):
        self.candidate["next_action"]["target_actor_id"] = "actor-05"
        accepted = self.parse(self.candidate)
        self.assertEqual(accepted["next_action"], self.candidate["next_action"])
        self.assertEqual(accepted["operational_effects"], 0)

    def test_our_desk_can_still_receive_operator_review(self):
        self.candidate["next_action"] = {
            "type": "operator_review", "target_actor_id": self.evidence["our_actor_id"],
            "description": "Review the payout request at our escalation desk.",
        }
        accepted = self.parse(self.candidate)
        self.assertEqual(accepted["next_action"], self.candidate["next_action"])


if __name__ == "__main__":
    unittest.main()
