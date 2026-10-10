"""Offline configuration checks for explicit Anthropic workspace routing."""
import json
import os
import unittest
from unittest.mock import patch

from tools.dwelly_model import providers, runner
from tools.dwelly_model.tests.test_runner import config


class WorkspaceConfigTests(unittest.TestCase):
    def scoped(self):
        value = config()
        value["judges"][1]["workspace_id_env"] = "TEST_WORKSPACE_ID"
        return value

    def test_preflight_reports_missing_workspace_name_without_values(self):
        keys = {name: "private-key" for name in
                ("OPENAI_TEST_KEY", "ANTHROPIC_TEST_KEY", "GEMINI_TEST_KEY")}
        with patch.dict(os.environ, keys, clear=True):
            result = runner.preflight(self.scoped())
        self.assertFalse(result["ready"])
        self.assertEqual(result["missing_credentials"], [])
        self.assertEqual(result["missing_workspace_config"], ["TEST_WORKSPACE_ID"])
        self.assertNotIn("private-key", json.dumps(result))

    def test_preflight_only_checks_presence_and_never_exposes_workspace(self):
        env = {name: "private-key" for name in
               ("OPENAI_TEST_KEY", "ANTHROPIC_TEST_KEY", "GEMINI_TEST_KEY")}
        env["TEST_WORKSPACE_ID"] = "wrkspc_privateAccount123"
        with patch.dict(os.environ, env, clear=True):
            result = runner.preflight(self.scoped())
        self.assertTrue(result["ready"])
        self.assertEqual(result["workspace_config_presence"], {"TEST_WORKSPACE_ID": True})
        self.assertFalse(result["network_checked"])
        self.assertFalse(result["billing_checked"])
        self.assertNotIn("wrkspc_privateAccount123", json.dumps(result))

    def test_invalid_workspace_option_is_rejected_by_config_validation(self):
        invalid = []
        for name in (None, "", "BAD-NAME", "ID\nINJECT"):
            value = self.scoped()
            value["judges"][1]["workspace_id_env"] = name
            invalid.append(value)
        for index in (0, 2):
            value = config()
            value["judges"][index]["workspace_id_env"] = "TEST_WORKSPACE_ID"
            invalid.append(value)
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                runner.preflight(value)

    def test_legacy_config_requires_no_workspace_variable(self):
        env = {name: "private-key" for name in
               ("OPENAI_TEST_KEY", "ANTHROPIC_TEST_KEY", "GEMINI_TEST_KEY")}
        with patch.dict(os.environ, env, clear=True):
            result = runner.preflight(config())
        self.assertTrue(result["ready"])
        self.assertEqual(result["missing_workspace_config"], [])

    def test_workspace_errors_remain_content_free_stable_codes(self):
        for code in ("missing_workspace_id", "invalid_workspace_id"):
            with self.subTest(code=code):
                self.assertEqual(runner._error_code(providers.ProviderError(code)), code)


if __name__ == "__main__":
    unittest.main()
