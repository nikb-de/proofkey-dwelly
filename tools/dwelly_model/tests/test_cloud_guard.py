"""Managed Cloud Run cannot admit live calls using local-only reservations."""
import importlib
import os
import unittest
from unittest.mock import patch


class CloudGuardTests(unittest.TestCase):
    def guard(self):
        try:
            return importlib.import_module("tools.dwelly_model.cloud_guard").reject_live_cloud
        except ModuleNotFoundError:
            self.fail("live cloud admission guard has not been implemented")

    def test_live_calls_rejected_in_cloud_run_service_or_job(self):
        for marker in ("K_SERVICE", "CLOUD_RUN_JOB"):
            for value in ("proofkey", ""):
                with self.subTest(marker=marker, value=value):
                    with patch.dict(os.environ, {marker: value}, clear=True):
                        with self.assertRaisesRegex(ValueError, "^live_cloud_unavailable$"):
                            self.guard()(True)

    def test_offline_cloud_smoke_is_allowed(self):
        for marker in ("K_SERVICE", "CLOUD_RUN_JOB"):
            with self.subTest(marker=marker):
                with patch.dict(os.environ, {marker: "proofkey"}, clear=True):
                    self.assertIsNone(self.guard()(False))

    def test_local_execution_is_allowed(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(self.guard()(False))
            self.assertIsNone(self.guard()(True))


if __name__ == "__main__":
    unittest.main()
