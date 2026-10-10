"""Breaks caught: forged probe flags, same UID protection and canary leakage."""
import os
import unittest
from test_label_reference_versions import module


class IsolationTests(unittest.TestCase):
    def test_actual_local_probe_reads_policy_and_same_identity_canary_is_rehearsal(self):
        isolation = module(self, "isolation")
        configuration = isolation.RehearsalBoundary(candidate_hash="1" * 64, workload_hash="2" * 64, public_policy=b"public-synthetic-policy")
        probes = isolation.run_local_probes(configuration)
        receipt = isolation.verify_isolation(configuration, probes, custodian=None)
        self.assertEqual(receipt.status, "rehearsal")
        self.assertEqual(probes.runtime_uid, os.geteuid())
        self.assertEqual(probes.public_policy, b"public-synthetic-policy")
        self.assertTrue(probes.hidden_accessible)
        self.assertFalse(any(p.enforced for p in receipt.probes))
        self.assertNotEqual(receipt.status, "protected")

    def test_public_error_debug_canary_leaks_fail_without_echoing_canary(self):
        isolation = module(self, "isolation")
        for channel in ("public", "error", "debug"):
            boundary = isolation.RehearsalBoundary(candidate_hash="1" * 64, workload_hash="2" * 64, public_policy=b"public-synthetic-policy")
            probes = isolation.run_local_probes(boundary, presenter=lambda policy, canary: {channel: canary})
            receipt = isolation.verify_isolation(boundary, probes, custodian=None)
            self.assertEqual(receipt.status, "failed")
            self.assertNotIn("PROOFKEY_SYNTHETIC_CANARY", receipt.model_dump_json())

    def test_claimed_denials_custodian_strings_and_wrong_join_cannot_grant_protection(self):
        isolation = module(self, "isolation")
        boundary = isolation.RehearsalBoundary(candidate_hash="1" * 64, workload_hash="2" * 64, public_policy=b"public")
        probes = isolation.run_local_probes(boundary)
        self.assertEqual(isolation.verify_isolation(boundary, probes, custodian="approved").status, "rehearsal")
        with self.assertRaises(TypeError):
            isolation.verify_isolation({"runtime_uid": 1, "evaluator_uid": 2, "protected": True}, [{"enforced": True}], "approved")
        other = isolation.RehearsalBoundary(candidate_hash="3" * 64, workload_hash="2" * 64, public_policy=b"public")
        with self.assertRaises(ValueError):
            isolation.verify_isolation(other, probes, None)
