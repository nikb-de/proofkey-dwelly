import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.dwelly_cases.tests.fixtures import make_source


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "source"
        make_source(self.source)
        self.bundle = self.root / "bundle"

    def call(self, *arguments):
        return subprocess.run([sys.executable, "-B", "-m", "tools.dwelly_cases", *map(str, arguments)],
                              capture_output=True, text=True, timeout=15)

    def import_bundle(self):
        result = self.call("import", "--source", self.source, "--output", self.bundle, "--expected-cases", 1)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def test_import_and_run_actual_cli(self):
        imported = self.import_bundle()
        self.assertEqual(json.loads(imported.stdout)["case_count"], 1)
        output = self.root / "results"
        result = self.call("run", "--bundle", self.bundle, "--output", output)
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(result.stdout)
        self.assertEqual(summary["case_count"], 1)
        self.assertEqual(summary["semantic_assessed_count"], 0)
        proposal = json.loads((output / "proposals/delivery-logistics-001.json").read_text())
        self.assertEqual(proposal["effects"], [])
        self.assertEqual(proposal["status"], "proposed_unsent")
        self.assertNotIn("SECRET_FUTURE", json.dumps(proposal))

    def test_repeated_runs_have_same_proposals(self):
        self.import_bundle()
        one, two = self.root / "one", self.root / "two"
        self.assertEqual(self.call("run", "--bundle", self.bundle, "--output", one).returncode, 0)
        self.assertEqual(self.call("run", "--bundle", self.bundle, "--output", two).returncode, 0)
        self.assertEqual((one / "proposals/delivery-logistics-001.json").read_bytes(),
                         (two / "proposals/delivery-logistics-001.json").read_bytes())

    def test_existing_output_is_never_replaced(self):
        self.import_bundle()
        result = self.call("import", "--source", self.source, "--output", self.bundle, "--expected-cases", 1)
        self.assertEqual(result.returncode, 2)
        self.assertTrue((self.bundle / "manifest.json").exists())

    def test_snapshot_tampering_fails_before_output(self):
        self.import_bundle()
        path = self.bundle / "agent/delivery-logistics-001.json"
        value = json.loads(path.read_text())
        value["events"][0]["body"] = "Tampered"
        path.write_text(json.dumps(value))
        output = self.root / "results"
        result = self.call("run", "--bundle", self.bundle, "--output", output)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(output.exists())

    def test_reference_mismatch_is_not_scored(self):
        self.import_bundle()
        path = self.bundle / "evaluation/delivery-logistics-001.json"
        value = json.loads(path.read_text())
        value["input_hash"] = "0" * 64
        path.write_text(json.dumps(value))
        output = self.root / "results"
        result = self.call("run", "--bundle", self.bundle, "--output", output)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(output.exists())

    def test_path_traversal_case_id_is_rejected(self):
        self.import_bundle()
        path = self.bundle / "manifest.json"
        value = json.loads(path.read_text())
        value["case_ids"] = ["../../outside"]
        path.write_text(json.dumps(value))
        output = self.root / "results"
        result = self.call("run", "--bundle", self.bundle, "--output", output)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(output.exists())

    def test_duplicate_json_keys_are_rejected(self):
        self.import_bundle()
        path = self.bundle / "manifest.json"
        path.write_text('{"case_ids":[],"case_ids":["delivery-logistics-001"]}')
        result = self.call("run", "--bundle", self.bundle, "--output", self.root / "out")
        self.assertEqual(result.returncode, 2)

    def test_nonzero_import_failure_does_not_print_raw_text(self):
        (self.source / "Delivery & Logistics/001/history.md").write_text("SECRET_CUSTOMER_TEXT")
        result = self.call("import", "--source", self.source, "--output", self.bundle, "--expected-cases", 1)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("SECRET_CUSTOMER_TEXT", result.stdout + result.stderr)
        self.assertFalse(self.bundle.exists())


if __name__ == "__main__":
    unittest.main()
