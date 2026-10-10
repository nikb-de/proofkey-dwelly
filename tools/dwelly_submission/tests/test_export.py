"""Offline export must preserve recorded outcomes rather than improve them."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class SubmissionExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.output = self.root / "ANSWERS"

    def record(self, status="succeeded", candidate=True):
        value = {
            "status": "failed",
            "checks": [{"name": "state_agreement", "status": "fail"}],
            "job": {
                "schema_version": "proofkey-model-job-v1",
                "case_id": "Case-A", "step_index": 3, "status": status,
                "input": {"case_id": "Case-A", "messages": [{"event_id": "003", "body": "I will open the gate."}]},
                "input_hash": "retained-system-hash",
                "candidate": {
                    "state": "waiting", "next_action": {"type": "wait", "description": "Wait for actual driver confirmation.", "target_actor_id": "driver"},
                    "waiting_for": ["driver"], "uncertainty": ["Handover is unconfirmed."],
                    "evidence_event_ids": ["003"], "operational_effects": 0,
                    "physical_delivery": "not_inferred",
                } if candidate else None,
                "error": {"code": "incomplete_response"} if status == "outcome_unknown" else None,
                "receipt": {"requested_model": "retained-model", "observed_model": "retained-model-1"},
                "transaction": {"dispatch_attempts": 1, "automatic_retries": 0, "operational_effects": 0},
                "evaluation": {"state_agreement": False},
            },
        }
        path = self.root / "record.json"
        path.write_text(json.dumps(value, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        return path, value

    def run_cli(self, record, *extra):
        return subprocess.run([sys.executable, "-m", "tools.dwelly_submission", "--record", str(record),
                               "--output", str(self.output), *extra], capture_output=True, text=True)

    def test_preserves_exact_source_and_model_output_without_execution_claim(self):
        source, value = self.record()
        result = self.run_cli(source)
        self.assertEqual(result.returncode, 0, result.stderr)
        case = self.output / "Case-A"
        self.assertEqual((case / "SOURCE_RECORD.json").read_bytes(), source.read_bytes())
        answer = (case / "ANSWER.md").read_text()
        self.assertIn("development", answer)
        self.assertIn("Wait for actual driver confirmation.", answer)
        self.assertIn("No operational action was executed by this export", answer)
        self.assertIn('"state_agreement": false', answer)
        self.assertIn('"record_status": "failed"', answer)
        receipt = json.loads((case / "EXPORT.json").read_text())
        self.assertEqual(receipt["source_sha256"], hashlib.sha256(source.read_bytes()).hexdigest())
        self.assertEqual(receipt["job_status"], "succeeded")
        for name, digest in receipt["files"].items():
            self.assertEqual(hashlib.sha256((case / name).read_bytes()).hexdigest(), digest)

    def test_unknown_outcome_stays_unknown_and_has_no_substitute_answer(self):
        source, _ = self.record("outcome_unknown", candidate=False)
        result = self.run_cli(source)
        self.assertEqual(result.returncode, 0, result.stderr)
        answer = (self.output / "Case-A" / "ANSWER.md").read_text()
        self.assertIn('"job_status": "outcome_unknown"', answer)
        self.assertIn("incomplete_response", answer)
        self.assertIn('"candidate": null', answer)
        self.assertIn("No accepted model answer is present", answer)
        reasoning = (self.output / "Case-A" / "REASONING.md").read_text()
        self.assertIn("No public rationale was retained", reasoning)

    def test_supplemental_raw_response_is_retained_byte_for_byte(self):
        source, _ = self.record()
        attachment = self.root / "provider-response.txt"
        attachment.write_bytes(b'{"state":"wrong"}\n\n')
        result = self.run_cli(source, "--attachment", str(attachment))
        self.assertEqual(result.returncode, 0, result.stderr)
        case = self.output / "Case-A"
        self.assertEqual((case / "ARTIFACT-001-provider-response.txt").read_bytes(), b'{"state":"wrong"}\n\n')
        receipt = json.loads((case / "EXPORT.json").read_text())
        self.assertEqual(receipt["files"]["ARTIFACT-001-provider-response.txt"],
                         hashlib.sha256(b'{"state":"wrong"}\n\n').hexdigest())

    def test_existing_case_is_not_overwritten(self):
        source, _ = self.record()
        self.assertEqual(self.run_cli(source).returncode, 0)
        answer = self.output / "Case-A" / "ANSWER.md"
        original = answer.read_bytes()
        result = self.run_cli(source)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FileExistsError", result.stderr)
        self.assertEqual(answer.read_bytes(), original)

    def test_unsafe_case_id_is_rejected(self):
        source, value = self.record()
        value["job"]["case_id"] = "../escape"
        source.write_text(json.dumps(value))
        result = self.run_cli(source)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsafe_case_id", result.stderr)
        self.assertFalse(self.output.exists())

    def test_job_and_input_identity_mismatch_is_rejected(self):
        source, value = self.record()
        value["job"]["input"]["case_id"] = "Other-case"
        source.write_text(json.dumps(value))
        result = self.run_cli(source)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("input_identity_mismatch", result.stderr)
        self.assertFalse(self.output.exists())

    def test_official_claim_is_not_available_for_development_records(self):
        source, _ = self.record()
        result = self.run_cli(source, "--evidence-class", "official_reality_test")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid choice", result.stderr)
        self.assertFalse(self.output.exists())

    def test_missing_job_does_not_create_replacement_output(self):
        source = self.root / "record.json"
        source.write_text('{"status":"failed","error":"not_dispatched"}')
        result = self.run_cli(source)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("retained_job_required", result.stderr)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
