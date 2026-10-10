"""Exercise the shipped command rather than inspecting source strings."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[3]


class CliTests(unittest.TestCase):
    def invoke(self, *args):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY"):
            env.pop(key, None)
        return subprocess.run([sys.executable, "-B", "-m", "tools.dwelly_model", *args],
                              cwd=ROOT, env=env, text=True, capture_output=True, timeout=10)

    def test_help_explains_live_opt_in(self):
        result = self.invoke("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("dry-run", result.stdout)
        self.assertIn("preflight", result.stdout)

    def test_run_without_live_flag_is_rejected_before_input(self):
        result = self.invoke("run", "--bundle", "missing", "--output", "missing",
                             "--config", "missing")
        self.assertEqual(result.returncode, 2)
        self.assertIn("--live", result.stderr)

    def test_preflight_reports_missing_credentials_without_values(self):
        result = self.invoke("preflight", "--config", "tools/dwelly_model/config.example.json")
        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads(result.stdout)
        self.assertFalse(report["ready"])
        self.assertEqual(set(report["missing_credentials"]),
                         {"OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY"})

    def test_bad_config_is_content_free(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp) / "bad.json"
            config.write_text('{"secret":"do-not-print-secret"', encoding="utf-8")
            result = self.invoke("preflight", "--config", str(config))
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("do-not-print-secret", result.stderr + result.stdout)


if __name__ == "__main__":
    unittest.main()
