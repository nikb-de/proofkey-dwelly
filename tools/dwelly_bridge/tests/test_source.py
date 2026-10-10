"""Real service artifacts; all apparent live output below is a saved test fixture."""
from dataclasses import FrozenInstanceError
from hashlib import sha256
import importlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

from tools.dwelly_cases.importer import canonical_bytes, digest, import_cases
from tools.dwelly_cases.tests.fixtures import make_source
from tools.dwelly_model import runner
from tools.dwelly_model.tests.test_runner import config
from tools.dwelly_service.store import JobStore

try:
    source = importlib.import_module("tools.dwelly_bridge.source")
except ModuleNotFoundError:
    source = None


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(source, "source validator must be implemented")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.service = self.root / "service"
        self.case = "delivery-logistics-001"
        raw = self.root / "raw"
        make_source(raw)
        make_source(raw, "002")
        self.bundle = self.root / "bundle"
        import_cases(raw, self.bundle, expected_cases=2)
        store = JobStore(self.service)
        spec = {"mode": "dry_run", "limit": 2, "evaluate": False,
                "max_parallel_requests": 1, "per_provider_limit": 1}
        job, _ = store.submit("source-test", spec)
        self.job = job["job_id"]
        store.claim_next()
        self.output = store.output_path(self.job)
        runner.run_experiment(self.bundle, self.output, config(), limit=2, proposals_only=True)
        store.finish(self.job, "completed")
        store.close()

    def read(self, name):
        return json.loads((self.output / name).read_bytes())

    def write(self, name, value):
        path = self.output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(canonical_bytes(value) + b"\n")

    def db(self, query, args=()):
        with sqlite3.connect(self.service / "queue.sqlite3") as connection:
            connection.execute(query, args)

    def load(self):
        return source.load_source(self.service, self.job, self.case)

    def rejected(self, code=None):
        with self.assertRaises(source.ShadowError) as raised:
            self.load()
        if code:
            self.assertEqual(raised.exception.code, code)
        self.assertRegex(raised.exception.code, r"^source_[a-z_]{1,48}$")
        self.assertEqual(str(raised.exception), raised.exception.code)

    def file_hashes(self):
        return {str(p.relative_to(self.service)): sha256(p.read_bytes()).hexdigest()
                for p in self.service.rglob("*") if p.is_file()}

    def freeze(self):
        ids = sorted(p.stem for p in (self.output / "snapshots").iterdir())
        proposals = {c: self.read(f"proposals/{c}.json") for c in ids}
        baselines = {c: self.read(f"baseline_proposals/{c}.json") for c in ids}
        self.write("proposals-frozen.json", {
            "proposal_set_hash": digest(proposals), "baseline_set_hash": digest(baselines),
            "input_set_hash": digest({c: self.read(f"snapshots/{c}.json")["input_hash"] for c in ids})})
        summary = self.read("summary.json")
        summary["proposal_set_hash"] = digest(proposals)
        self.write("summary.json", summary)

    def live_fixture(self):
        """Convert saved offline output into a coherent, explicitly synthetic live fixture."""
        with sqlite3.connect(self.service / "queue.sqlite3") as connection:
            spec = json.loads(connection.execute("SELECT body FROM jobs").fetchone()[0])
            spec["mode"] = "live"
            body = json.dumps(spec, sort_keys=True, separators=(",", ":"))
            connection.execute("UPDATE jobs SET body=?, fingerprint=?", (body, sha256(body.encode()).hexdigest()))
        for name in ("manifest.json", "summary.json"):
            value = self.read(name)
            value["mode"] = "live_api"
            if name == "summary.json":
                value["live_calls"] = 2
            self.write(name, value)
        for snapshot_path in (self.output / "snapshots").iterdir():
            c = snapshot_path.stem
            snapshot = self.read(f"snapshots/{c}.json")
            baseline = self.read(f"baseline_proposals/{c}.json")
            candidate = runner._baseline_candidate(baseline)
            candidate["rationale"] = "Synthetic saved response fixture for " + c
            system, prompt = runner.semantic.proposal_prompt(snapshot)
            key = c + "-proposer"
            # Exercise the actual saved reservation contract without any transport.
            with runner.BudgetLedger(self.root / (c + "-fixture-budget.jsonl"), 25) as ledger:
                reservation = ledger.reserve(config()["proposer"], system, prompt, 256, key)
            self.write(f"requests/{key}.json", {"request_key": key, "provider": "openai",
                       "requested_model": "offline-model", "system": system, "prompt": prompt,
                       "reservation": reservation})
            response = {"text": json.dumps(candidate), "provider": "openai", "requested_model": "offline-model",
                        "observed_model": "synthetic-fixture-model", "input_tokens": 1, "output_tokens": 1,
                        "request_id": "test-fixture-" + c, "latency_ms": 1.0,
                        "raw_response": {"fixture": True}}
            self.write(f"receipts/{key}.json", {"request_key": key, "provider": "openai",
                       "requested_model": "offline-model", "status": "received", "response": response})
            self.write(f"proposals/{c}.json", runner._envelope(snapshot, candidate, "live_api"))
        self.freeze()

    def test_baseline_preserves_source_and_has_current_verifier_identity(self):
        before = self.file_hashes()
        value = self.load()
        self.assertEqual(before, self.file_hashes())
        self.assertEqual(value.provenance, "baseline")
        self.assertEqual(value.source_mode, "offline_dry_run")
        self.assertIsNone(value.receipt_hash)
        self.assertRegex(value.verifier_version, r"^[a-f0-9]{64}$")
        self.assertEqual(value.snapshot_hash, self.read(f"snapshots/{self.case}.json")["input_hash"])
        self.assertEqual(value.proposal_hash, digest(self.read(f"proposals/{self.case}.json")))
        self.assertEqual(value, self.load())

    def test_source_record_is_frozen_and_summary_contains_no_payloads(self):
        value = self.load()
        with self.assertRaises(FrozenInstanceError):
            value.case_id = "changed"
        summary = value.summary()
        self.assertEqual(set(summary), {"job_id", "case_id", "snapshot_hash", "proposal_hash", "receipt_hash",
                                       "source_hash", "provenance", "source_mode", "verifier_version"})
        summary["case_id"] = "changed"
        self.assertEqual(value.case_id, self.case)
        self.assertNotIn("message", json.dumps(summary))

    def test_live_fixture_links_exact_request_response_and_proposal(self):
        self.live_fixture()
        before = self.file_hashes()
        value = self.load()
        self.assertEqual(before, self.file_hashes())
        self.assertEqual(value.provenance, "historical_live_api")
        self.assertEqual(value.source_mode, "live_api")
        self.assertEqual(value.receipt_hash, digest(self.read(f"receipts/{self.case}-proposer.json")))

    def test_source_does_not_accept_a_different_attempt(self):
        self.live_fixture()
        self.write(f"receipts/{self.case}-proposer.json", self.read("receipts/delivery-logistics-002-proposer.json"))
        self.rejected("source_linkage_invalid")

    def test_valid_but_different_response_candidate_is_rejected(self):
        self.live_fixture()
        receipt = self.read(f"receipts/{self.case}-proposer.json")
        candidate = json.loads(receipt["response"]["text"])
        candidate["rationale"] = "A different attempt with the same snapshot"
        receipt["response"]["text"] = json.dumps(candidate)
        self.write(f"receipts/{self.case}-proposer.json", receipt)
        self.rejected("source_linkage_invalid")

    def test_changed_prompt_is_rejected(self):
        self.live_fixture()
        request = self.read(f"requests/{self.case}-proposer.json")
        request["prompt"] += "changed"
        self.write(f"requests/{self.case}-proposer.json", request)
        self.rejected("source_linkage_invalid")

    def test_changed_request_model_is_rejected(self):
        self.live_fixture()
        request = self.read(f"requests/{self.case}-proposer.json")
        request["requested_model"] = "different-model"
        self.write(f"requests/{self.case}-proposer.json", request)
        self.rejected("source_linkage_invalid")

    def test_changed_response_provider_is_rejected(self):
        self.live_fixture()
        receipt = self.read(f"receipts/{self.case}-proposer.json")
        receipt["response"]["provider"] = "gemini"
        self.write(f"receipts/{self.case}-proposer.json", receipt)
        self.rejected("source_linkage_invalid")

    def test_missing_receipt_is_rejected(self):
        self.live_fixture()
        (self.output / f"receipts/{self.case}-proposer.json").unlink()
        self.rejected()

    def test_changed_baseline_cannot_pass_by_refreezing_hashes(self):
        proposal = self.read(f"proposals/{self.case}.json")
        proposal["action"]["message"] = "Tampered but structurally valid draft"
        self.write(f"proposals/{self.case}.json", proposal)
        self.freeze()
        self.rejected("source_linkage_invalid")

    def test_changed_second_proposal_invalidates_whole_frozen_set(self):
        proposal = self.read("proposals/delivery-logistics-002.json")
        proposal["action"]["message"] += "changed"
        self.write("proposals/delivery-logistics-002.json", proposal)
        self.rejected()

    def test_missing_snapshot_is_rejected(self):
        (self.output / "snapshots/delivery-logistics-002.json").unlink()
        self.rejected()

    def test_extra_proposal_is_rejected(self):
        self.write("proposals/unrelated.json", {})
        self.rejected()

    def test_summary_hash_mismatch_is_rejected(self):
        summary = self.read("summary.json")
        summary["proposal_set_hash"] = "0" * 64
        self.write("summary.json", summary)
        self.rejected()

    def test_incomplete_job_is_rejected(self):
        self.db("UPDATE jobs SET status='running'")
        self.rejected("source_incomplete")

    def test_mode_mismatch_is_rejected(self):
        manifest = self.read("manifest.json")
        manifest["mode"] = "live_api"
        self.write("manifest.json", manifest)
        self.rejected()

    def test_case_count_mismatch_is_rejected(self):
        summary = self.read("summary.json")
        summary["case_count"] = 1
        self.write("summary.json", summary)
        self.rejected()

    def test_foreign_case_is_rejected(self):
        self.case = "delivery-logistics-003"
        self.rejected("source_case_missing")

    def test_traversal_id_is_rejected(self):
        self.case = "../summary"
        self.rejected("source_identity_invalid")

    def test_duplicate_json_keys_are_rejected(self):
        (self.output / "proposals-frozen.json").write_text('{"proposal_set_hash":"a","proposal_set_hash":"b"}')
        self.rejected()

    def test_nonfinite_json_is_rejected(self):
        (self.output / "proposals-frozen.json").write_text('{"proposal_set_hash":1e999}')
        self.rejected()

    def test_malformed_json_is_rejected(self):
        (self.output / "summary.json").write_text('{"status":')
        self.rejected()

    def test_unknown_closed_fields_are_rejected(self):
        frozen = self.read("proposals-frozen.json")
        frozen["invented"] = True
        self.write("proposals-frozen.json", frozen)
        self.rejected()

    def test_unsupported_version_is_rejected(self):
        manifest = self.read("manifest.json")
        manifest["schema_version"] = "dwelly-model-experiment-v99"
        self.write("manifest.json", manifest)
        self.rejected("source_version_unsupported")

    def test_symlink_file_is_rejected(self):
        path = self.output / "summary.json"
        original = self.root / "summary.json"
        path.rename(original)
        path.symlink_to(original)
        self.rejected("source_path_unsafe")

    def test_symlink_directory_is_rejected(self):
        path = self.output / "snapshots"
        original = self.root / "snapshots"
        path.rename(original)
        path.symlink_to(original, target_is_directory=True)
        self.rejected("source_path_unsafe")

    def test_world_writable_root_is_rejected(self):
        self.service.chmod(0o777)
        self.rejected("source_path_unsafe")

    def test_oversized_json_is_rejected(self):
        (self.output / "summary.json").write_bytes(b" " * (4 * 1024 * 1024 + 1))
        self.rejected("source_too_large")

    def test_invalid_job_spec_is_rejected_even_with_matching_fingerprint(self):
        body = '{"mode":"dry_run","limit":false}'
        self.db("UPDATE jobs SET body=?, fingerprint=?", (body, sha256(body.encode()).hexdigest()))
        self.rejected()

    def test_raw_byte_changes_are_retained_in_source_hash(self):
        first = self.load()
        with (self.output / f"proposals/{self.case}.json").open("ab") as stream:
            stream.write(b" \n")
        second = self.load()
        self.assertEqual(first.proposal_hash, second.proposal_hash)
        self.assertNotEqual(first.source_hash, second.source_hash)

    def test_database_symlink_is_rejected(self):
        path = self.service / "queue.sqlite3"
        original = self.root / "queue.sqlite3"
        path.rename(original)
        path.symlink_to(original)
        self.rejected("source_path_unsafe")

    def test_writable_job_directory_is_rejected(self):
        self.output.chmod(0o777)
        self.rejected("source_path_unsafe")

    def test_symlink_service_root_is_rejected(self):
        link = self.root / "linked-service"
        link.symlink_to(self.service, target_is_directory=True)
        with self.assertRaises(source.ShadowError) as raised:
            source.load_source(link, self.job, self.case)
        self.assertEqual(raised.exception.code, "source_path_unsafe")

    def test_traversal_job_is_rejected(self):
        self.job = "../queue.sqlite3"
        self.rejected("source_identity_invalid")

    def test_more_than_fifty_cases_is_rejected(self):
        for number in range(3, 52):
            self.write(f"snapshots/delivery-logistics-{number:03d}.json", {})
        self.rejected("source_too_large")

    def test_untrusted_error_code_is_sanitized(self):
        error = source.ShadowError("secret/raw/provider/payload")
        self.assertEqual(error.code, "source_invalid")
        self.assertEqual(str(error), "source_invalid")

    def test_conflicting_failure_terminal_is_rejected(self):
        self.write("failure.json", {"status": "failed", "error": "request_failed",
                                    "live_calls": 0, "resumable": False})
        self.rejected("source_incomplete")


if __name__ == "__main__":
    unittest.main()
