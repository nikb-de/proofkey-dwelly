"""Breaks caught: stale evidence hits, joined references, overwritten review history."""
import importlib
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures/development"


def module(test, name):
    path = "proofkey.assessment." + name
    test.assertIsNotNone(importlib.util.find_spec(path), "Assessment helper is absent")
    return importlib.import_module(path)


def rows():
    return [json.loads(line) for line in (FIXTURES / "cases.jsonl").read_text().splitlines()]


class ReferenceTests(unittest.TestCase):
    def test_every_pinned_identity_change_misses_without_replacing_history(self):
        cache = module(self, "cache")
        pins = [str(i) * 64 for i in range(1, 8)]
        original = cache.cache_key(*pins)
        self.assertEqual(cache.cache_key(*pins), original)
        for index in range(7):
            changed = pins.copy()
            changed[index] = "a" * 64
            self.assertNotEqual(cache.cache_key(*changed), original)
        for invalid in ("candidate", "A" * 64, "g" * 64, "a" * 63, None):
            with self.assertRaises(ValueError):
                cache.cache_key(invalid, *pins[1:])

    def test_reference_rejects_changed_input_and_nested_hashes(self):
        c = module(self, "contracts")
        row = rows()[0]
        valid = c.CaseRow.model_validate(row)
        row["input"]["arguments"]["window_start"] = "wrong"
        with self.assertRaises(ValueError):
            c.CaseRow.model_validate(row)
        with self.assertRaises(TypeError):
            valid.input.arguments["window_start"] = "wrong"
        reference = valid.reference.model_dump(mode="json")
        reference["label"]["version"] = "v2"
        with self.assertRaises(ValueError):
            c.Reference.model_validate(reference)

    def test_error_and_missing_output_remain_unassessed_and_detached(self):
        c = module(self, "contracts")
        labels = module(self, "labels")
        row = c.CaseRow.model_validate(rows()[0])
        observed = c.Observation.capture(row, "1" * 64, output=None, error=b"synthetic-secret-error")
        verdict = labels.score_case(observed, row.reference)
        self.assertEqual(verdict.effect_verdicts["reschedule"].verdict, "unassessed")
        self.assertNotIn("synthetic-secret", verdict.model_dump_json())
        self.assertEqual(observed.error, b"synthetic-secret-error")
        self.assertIn("provisional_reference", verdict.qualification_limits)

    def test_initiated_return_never_scores_physical_receipt_or_refund(self):
        c = module(self, "contracts")
        labels = module(self, "labels")
        row = c.CaseRow.model_validate(rows()[5])
        output = {"effects": {"register_goods_refusal": {"status": "verified", "postcondition": {"refused": True}, "evidence_refs": ["refusal"]}, "create_return": {"status": "verified", "postcondition": {"return_status": "created", "inventory": {"item-1": 1}}, "evidence_refs": ["return"]}}, "forbidden_effects": ["refund"]}
        observed = c.Observation.capture(row, "1" * 64, output=output)
        verdict = labels.score_case(observed, row.reference)
        self.assertEqual(verdict.effect_verdicts["create_return"].verdict, "correct")
        self.assertEqual(verdict.effect_verdicts["forbidden_effects"].verdict, "incorrect")
        output["effects"]["create_return"]["postcondition"]["refund"] = True
        self.assertNotIn(b'"refund":true', observed.output_bytes)

    def test_wrong_join_is_rejected_and_prose_consensus_cannot_replace_evidence(self):
        c = module(self, "contracts")
        labels = module(self, "labels")
        row = c.CaseRow.model_validate(rows()[0])
        other = c.CaseRow.model_validate(rows()[3])
        observed = c.Observation.capture(row, "1" * 64, output={"effects": {}, "forbidden_effects": []})
        with self.assertRaises(ValueError):
            labels.score_case(observed, other.reference)
        self.assertEqual(labels.score_case(observed, row.reference).effect_verdicts["reschedule"].verdict, "incorrect")
        with self.assertRaises(ValueError):
            c.Observation.capture(row, "1" * 64, output={"success": True, "model_consensus": "success"})

    def test_review_appends_accept_change_ambiguity_without_erasing_proposal(self):
        labels = module(self, "labels")
        c = module(self, "contracts")
        row = c.CaseRow.model_validate(rows()[0])
        history = labels.LabelHistory.propose(row.reference, requested_model="offline-request", observed_model=None, prompt={"version": "v1"}, evidence_refs=("synthetic",), disagreements=("not-human-reviewed",))
        first_hash = history.label_set_hash
        accepted = history.review(reviewer="rehearsal-reviewer", disposition="accept", evidence_refs=("synthetic-review",))
        changed = accepted.review(reviewer="rehearsal-reviewer", disposition="change", evidence_refs=("synthetic-review-2",), replacement={"scope": "ambiguous"})
        ambiguous = changed.review(reviewer="rehearsal-reviewer", disposition="ambiguous", evidence_refs=("synthetic-review-3",))
        self.assertEqual(len(history.entries), 1)
        self.assertEqual(len(ambiguous.entries), 4)
        self.assertEqual(history.entries[0], ambiguous.entries[0])
        self.assertNotEqual(first_hash, ambiguous.label_set_hash)
        packet = json.loads(ambiguous.unsent_packet)
        self.assertEqual(packet["delivery"], "unsent")
        self.assertIsNone(packet["history"][0]["observed_model"])
        self.assertEqual(packet["history"][0]["status"], "provisional_llm")
        with self.assertRaises(ValueError):
            history.review(reviewer="fixture", disposition="approved", evidence_refs=("fake",))

    def test_reference_closed_metadata_rejects_unregistered_actual_flags_and_inconsistent_absence(self):
        c = module(self, "contracts")
        for key in ("source", "label", "rubric", "lineage"):
            supplied = rows()[0]
            target = supplied[key] if key == "source" else supplied["reference"][key]
            target["actual"] = True
            # Recompute identity to prove content hashing alone cannot admit an unknown flag.
            from proofkey.identity import fingerprint
            if key == "source":
                supplied["source_hash"] = fingerprint(target)
                supplied["reference"]["source_hash"] = supplied["source_hash"]
            else:
                supplied["reference"][key + "_hash"] = fingerprint(target)
            ref = supplied["reference"]
            ref["reference_hash"] = fingerprint({k: ref[k] for k in ("case_id", "input_hash", "source_hash", "required_behavior", "authority_assumptions", "provenance", "ambiguity", "exclusion")})
            with self.assertRaises(ValueError):
                c.CaseRow.model_validate(supplied)
        with self.assertRaises(ValueError):
            c.EffectRequirement(status="absent", postcondition={"refunded": True}, requires_evidence=True)

    def test_unspecified_effect_and_physical_claim_inside_return_postcondition_are_incorrect(self):
        c = module(self, "contracts")
        labels = module(self, "labels")
        row = c.CaseRow.model_validate(rows()[5])
        output = {"effects": {"register_goods_refusal": {"status": "verified", "postcondition": {"refused": True}, "evidence_refs": ["refusal"]}, "create_return": {"status": "verified", "postcondition": {"return_status": "created", "inventory": {"item-1": 1}, "physical_receipt": True}, "evidence_refs": ["return"]}, "undeclared_write": {"status": "verified", "postcondition": {}, "evidence_refs": ["other"]}}, "forbidden_effects": []}
        result = labels.score_case(c.Observation.capture(row, "1" * 64, output=output), row.reference)
        self.assertEqual(result.effect_verdicts["forbidden_effects"].verdict, "incorrect")
        self.assertEqual(result.effect_verdicts["undeclared_write"].verdict, "incorrect")

    def test_exact_observed_output_bytes_are_preserved_not_reserialized(self):
        c = module(self, "contracts")
        cache = module(self, "cache")
        row = c.CaseRow.model_validate(rows()[0])
        first_bytes = b'{ "effects": {}, "forbidden_effects": [] }'
        second_bytes = b'{"effects":{},"forbidden_effects":[]}'
        try:
            first = c.Observation.capture(row, "1" * 64, output=first_bytes)
            second = c.Observation.capture(row, "1" * 64, output=second_bytes)
        except ValueError:
            self.fail("Exact observed bytes were rejected instead of retained")
        self.assertEqual(first.output_bytes, first_bytes)
        self.assertNotEqual(first.output_hash, second.output_hash)
        self.assertNotEqual(cache.cache_key(first.candidate_hash, first.input_hash, first.output_hash, "2" * 64, first.label_hash, first.rubric_hash, first.lineage_hash), cache.cache_key(second.candidate_hash, second.input_hash, second.output_hash, "2" * 64, second.label_hash, second.rubric_hash, second.lineage_hash))
