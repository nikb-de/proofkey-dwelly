"""Explanatory rendering cannot manufacture adaptation authority."""
import unittest
from proofkey.factory import derive_view, prepare_proposal, FactoryDenied
from test_adaptation_factory import candidate_profile, encoded


class ProcessViewTests(unittest.TestCase):
    def test_view_includes_semantics_and_explicit_reference_context(self):
        process = candidate_profile().processes["reschedule_window"]
        before = encoded(process.model_dump(mode="json"))
        view = derive_view(process, "a" * 64)
        self.assertIn("explanatory", view)
        self.assertIn("Release context reference: " + "a" * 64, view)
        self.assertIn(process.release_hash, view)
        self.assertIn(process.process_id, view)
        for value in ("scheduling.slot", "S0", "wait_operator", "Readiness", "Wait", "Completion", "Acknowledgement", "Readback", "Approval"):
            self.assertIn(value, view)
        self.assertEqual(view, derive_view(process, "a" * 64))
        self.assertEqual(before, encoded(process.model_dump(mode="json")))

    def test_labels_escape_and_edited_view_never_registers_or_activates(self):
        process = candidate_profile().processes["reschedule_window"]
        altered = process.model_copy(update={"process_id": '<script>alert("x")</script>'})
        view = derive_view(altered, '<svg onload="bad">')
        self.assertNotIn("<script>", view)
        self.assertNotIn("<svg", view)
        self.assertIn("&lt;script&gt;", view)
        with self.assertRaises(FactoryDenied):
            prepare_proposal(encoded({"view": view + " approved"}), candidate_profile(), b"{}")
        self.assertNotIn("approved", derive_view(process, "a" * 64))


if __name__ == "__main__":
    unittest.main()
