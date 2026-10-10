"""The public command only imports local completed artifacts in unmapped mode."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.dwelly_bridge.tests.test_bridge import completed_source, hashes


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.service, self.job, self.case, _ = completed_source(self.root)
        self.shadow = self.root / "shadow"

    def command(self, *extra):
        return subprocess.run([sys.executable, "-B", "-m", "tools.dwelly_bridge",
            "--service-state", str(self.service), "--job-id", self.job, "--case-id", self.case,
            "--shadow-state", str(self.shadow), *extra], capture_output=True, text=True, timeout=30)

    def test_real_cli_is_unmapped_and_restart_is_identical(self):
        before = hashes(self.service)
        first, second = self.command(), self.command()
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stderr, "")
        self.assertEqual(first.stdout, second.stdout)
        record = json.loads(first.stdout)
        self.assertEqual(record["status"], "unmapped")
        self.assertIsNone(record["target"])
        self.assertFalse(record["authorization"])
        self.assertEqual(record["effects"], [])
        self.assertEqual(before, hashes(self.service))

    def test_bad_source_has_nonzero_machine_readable_sanitized_result(self):
        self.case = "../SECRET"
        result = self.command()
        self.assertNotEqual(result.returncode, 0)
        value = json.loads(result.stdout)
        self.assertEqual(value["status"], "rejected")
        self.assertEqual(value["reason"], "source_identity_invalid")
        self.assertNotIn("SECRET", result.stdout + result.stderr)
        self.assertFalse(self.shadow.exists())

    def test_unknown_plugin_or_binding_options_are_rejected(self):
        for option in ("--resolver", "--binding"):
            result = self.command(option, "SECRET")
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)["reason"], "cli_arguments_invalid")
            self.assertNotIn("SECRET", result.stdout + result.stderr)
            self.assertFalse(self.shadow.exists())


if __name__ == "__main__":
    unittest.main()
