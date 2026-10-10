"""Strict model-output compatibility; all provider replies here are synthetic."""
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.dwelly_cases import runner as cases
from tools.dwelly_cases.importer import import_cases
from tools.dwelly_cases.tests.fixtures import make_source
from tools.dwelly_model import runner
from tools.dwelly_model.tests.test_runner import config


class ModelJsonTests(unittest.TestCase):
    def parser(self):
        parser = getattr(runner, "_model_json", None)
        self.assertTrue(callable(parser), "model-output JSON parser is missing")
        return parser

    def test_bare_json_preserves_strict_decoding(self):
        parse = self.parser()
        self.assertEqual(parse(' \n{"ok":true,"message":"literal ``` text"}\t'),
                         {"ok": True, "message": "literal ``` text"})

    def test_one_complete_json_fence_allows_only_outside_whitespace(self):
        parse = self.parser()
        for newline in ("\n", "\r\n"):
            text = ' \t\n```json' + newline + '{"ok":true,"message":"literal ``` text"}' + newline + '```\n '
            with self.subTest(newline=repr(newline)):
                self.assertEqual(parse(text), {"ok": True, "message": "literal ``` text"})

    def test_prose_extra_fences_and_noncanonical_wrappers_are_rejected(self):
        parse = self.parser()
        invalid = (
            'Here is JSON:\n```json\n{"ok":true}\n```',
            '```json\n{"ok":true}\n```\nDone.',
            '```json\n{"ok":true}\n```\n```json\n{}\n```',
            '```json\n```json\n{"ok":true}\n```\n```',
            '```\n{"ok":true}\n```',
            '```JSON\n{"ok":true}\n```',
            '```json {"ok":true}\n```',
            '```json\n{"ok":true}```',
            '```json\n{"ok":true}\n',
            '{"ok":true}\n```',
        )
        for text in invalid:
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse(text)

    def test_duplicate_keys_nonfinite_values_and_trailing_data_stay_invalid(self):
        parse = self.parser()
        for body in ('{"ok":true,"ok":false}', '{"nested":{"x":1,"x":2}}',
                     '{"score":NaN}', '{"score":Infinity}', '{"score":-Infinity}',
                     '{"ok":true} {}', '{"ok":true} prose', '{"ok":'):
            for text in (body, "```json\n" + body + "\n```"):
                with self.subTest(text=text), self.assertRaises(ValueError):
                    parse(text)

    def test_bundle_json_decoder_does_not_accept_model_fences(self):
        with self.assertRaises(ValueError):
            cases.strict_json('```json\n{"ok":true}\n```')


class ModelJsonIntegrationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        source = self.root / "source"
        make_source(source)
        self.bundle = self.root / "bundle"
        import_cases(source, self.bundle, expected_cases=1)
        self.candidate = {
            "action": {"kind": "request_customer_choice", "recipient": "Ari, recipient",
                       "channel": "Customer portal", "message": "Do you prefer 15:00 or 17:00?"},
            "evidence_refs": ["event-001", "event-002"], "rationale": "A slot choice is missing.",
            "missing_information": ["Preferred slot"], "required_approvals": [],
        }
        self.judgment = {
            "scores": {"next_action": 3, "routing": 3, "required_details": 3, "grounding": 3,
                       "authority_consent": 3, "no_fabrication": 3, "escalation": 3, "clarity": 3},
            "explanation": "The request presents the visible alternatives.",
            "evidence_refs": ["event-001"], "critical_failures": [], "abstain": False,
        }

    def run_fenced(self, output, invalid_stage=None):
        emitted = []

        def transport(request, timeout):
            value = dict(self.candidate if not emitted else self.judgment)
            if (not emitted and invalid_stage == "proposal") or (emitted and invalid_stage == "judgment"):
                value["evidence_refs"] = ["event-999"]
            text = " \n```json\n" + json.dumps(value) + "\n```\t "
            if "openai.com" in request.full_url:
                body = {"status": "completed", "model": "synthetic-observed", "id": "synthetic-1",
                        "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}]}
            elif "anthropic.com" in request.full_url:
                body = {"model": "synthetic-observed", "id": "synthetic-1", "stop_reason": "end_turn",
                        "content": [{"type": "text", "text": text}]}
            else:
                body = {"modelVersion": "synthetic-observed", "responseId": "synthetic-1",
                        "candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": text}]}}]}
            emitted.append((text, body))
            response = io.BytesIO(json.dumps(body).encode())
            response.status = 200
            response.headers = {}
            return response

        configuration = config()
        configuration["proposer"] = dict(configuration["judges"][1])
        environment = {provider + "_TEST_KEY": "synthetic-key" for provider in ("OPENAI", "ANTHROPIC", "GEMINI")}
        with patch.dict("os.environ", environment, clear=True), patch.object(runner.providers, "_open", transport):
            result = runner.run_experiment(self.bundle, output, configuration, live=True,
                                           compare_baseline=False, include_reference=False)
        keys = ["delivery-logistics-001-proposer"] + [
            f"delivery-logistics-001-candidate-r0-judge{i}" for i in range(3)]
        for key, (text, body) in zip(keys, emitted):
            receipt = json.loads((output / "receipts" / (key + ".json")).read_text())
            self.assertEqual(receipt["status"], "received")
            self.assertEqual(receipt["response"]["text"], text)
            self.assertEqual(receipt["response"]["raw_response"], body)
        return result

    def test_fenced_proposer_and_all_provider_judges_validate_with_raw_receipts(self):
        output = self.root / "valid"
        result = self.run_fenced(output)
        self.assertEqual(result["proposal_count"], 1)
        self.assertEqual(result["live_calls"], 4)
        self.assertEqual(result["judge_coverage"]["scored_count"], 3)
        self.assertEqual(result["execution_errors"], {})
        proposal = json.loads((output / "proposals/delivery-logistics-001.json").read_text())
        self.assertEqual(proposal["action"], self.candidate["action"])
        for index in range(3):
            record = json.loads((output / "judgments" / f"delivery-logistics-001-candidate-r0-judge{index}.json").read_text())
            self.assertEqual(record["status"], "ok")
            self.assertEqual(record["judgment"], self.judgment)

    def test_fenced_json_still_requires_proposal_and_judgment_validation(self):
        for stage, proposals, calls in (("proposal", 0, 1), ("judgment", 1, 4)):
            with self.subTest(stage=stage):
                result = self.run_fenced(self.root / stage, invalid_stage=stage)
                self.assertEqual(result["proposal_count"], proposals)
                self.assertEqual(result["live_calls"], calls)
                self.assertEqual(result["judge_coverage"]["scored_count"], 0)
                self.assertEqual(set(result["execution_errors"].values()), {"invalid_" + stage})


if __name__ == "__main__":
    unittest.main()
