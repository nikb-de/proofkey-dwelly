"""Registered synthetic ownership only; future versions/body aliases never activate."""
import copy
import hashlib
from pathlib import Path
import unittest

from proofkey.contracts import EnvironmentProfile
from proofkey.identity import fingerprint
from proofkey.ownership_contracts import ownership_enabled, TRANSFER_FIELDS_V1
from proofkey.packet_contracts import packet_enabled
from proofkey.profiles import load_profile, validate_profile

ROOT = Path(__file__).resolve().parents[1]
BASES = {
    "permission_basis": "ownership-v1: source actor and target grant",
    "acknowledgement": "ownership-v1: acknowledgement is not acceptance",
    "readback": "ownership-v1: exact original typed receipt",
    "conditional_coverage": "ownership-v1: atomic case packet owner grant comparison",
    "idempotency_scope": "ownership-v1: binding operation stage original identity",
    "terminal_nonexecution_basis": "ownership-v1: durable original terminal rejection",
}


def declared_profile(variant="flat"):
    """Explicit host unit registration, not inbound authority or a runtime setter."""
    data = load_profile(variant + "-v1.3").model_dump(mode="json")
    data.update(profile_id=variant + "-v1.4", version="v1.4")
    data["authorities"].update({"operator.ownership_grant": "operator",
        "operator.ownership_packet": "operator", "operator.transfer_receipt": "operator"})
    for operation, version in (("transfer_owner", "ownership-transfer-v1"),
            ("record_operator_decision", "ownership-decision-v1"),
            ("record_operator_disposition", "ownership-disposition-v1")):
        cap = copy.deepcopy(data["capabilities"]["transfer_owner"])
        cap.update(operation=operation, version=version, evidence_mode="synthetic", authority="operator")
        for field, basis in BASES.items():
            supported = operation == "transfer_owner" or field in {"permission_basis", "readback", "conditional_coverage"}
            cap[field] = {"status": "supported" if supported else "unsupported", "basis": basis if supported else None,
                "evidence_ref": "synthetic-ownership-manifest-v1" if supported else None, "covered_fields": []}
        cap["conditional_coverage"]["covered_fields"] = sorted(TRANSFER_FIELDS_V1)
        data["capabilities"][operation] = cap
    data["release_hash"] = fingerprint({k: v for k, v in data.items() if k != "release_hash"})
    return EnvironmentProfile.model_validate(data)


class OwnershipProfileTests(unittest.TestCase):
    def test_exact_v14_registration_keeps_packet_and_ownership_contracts(self):
        # A numeric/future allowlist or v1.4 packet rejection breaks this boundary.
        profile = declared_profile()
        try:
            registered_packet = packet_enabled(profile)
        except ValueError as exc:
            self.fail("Exact registered v1.4 packet semantics were rejected: " + str(exc))
        self.assertTrue(registered_packet)
        self.assertTrue(ownership_enabled(profile))
        self.assertEqual(validate_profile(profile), profile)
        future = profile.model_dump(mode="json")
        future["version"] = "v1.5"
        future["release_hash"] = fingerprint({k: v for k, v in future.items() if k != "release_hash"})
        with self.assertRaises(ValueError):
            validate_profile(EnvironmentProfile.model_validate(future))

    def test_builtin_v14_preserves_parent_graph_policy_limits_and_packet(self):
        for variant in ("flat", "nested"):
            parent = load_profile(variant + "-v1.3")
            try:
                profile = load_profile(variant + "-v1.4")
            except ValueError as exc:
                self.fail("Built-in v1.4 registered family is missing: " + str(exc))
            self.assertEqual(profile.processes, parent.processes)
            self.assertEqual(profile.process_hash, parent.process_hash)
            self.assertEqual(profile.policy_hash, parent.policy_hash)
            self.assertEqual(profile.mappings, parent.mappings)
            for name, cap in parent.capabilities.items():
                if name != "transfer_owner":
                    self.assertEqual(profile.capabilities[name], cap)
            self.assertEqual(profile.capabilities["transfer_owner"].shared_limits,
                             parent.capabilities["transfer_owner"].shared_limits)
            for name in ("record_operator_decision", "record_operator_disposition"):
                cap = profile.capabilities[name]
                self.assertEqual(cap.acknowledgement.status, "unsupported")
                self.assertEqual(cap.idempotency_scope.status, "unsupported")
                self.assertEqual(cap.terminal_nonexecution_basis.status, "unsupported")
            self.assertTrue(packet_enabled(profile))
            self.assertTrue(ownership_enabled(profile))
        self.assertEqual(load_profile("flat-v1.4").capabilities,
                         load_profile("nested-v1.4").capabilities)

    def test_legacy_v13_artifact_bytes_and_runtime_semantics_remain_unchanged(self):
        # Old release bytes are an explicit compatibility obligation, not activation.
        receipts = {"flat-v1.3": "8fcd07924f5518ffa6e8b7cfcb3d773e8ba9f10d48458031132f8749c177a940",
            "nested-v1.3": "089334eef9dd0818f02539b84ed4846870de90493e31ceea31263737b3d6ca15"}
        for name, expected in receipts.items():
            self.assertEqual(hashlib.sha256((ROOT / "profiles" / (name + ".json")).read_bytes()).hexdigest(), expected)
            profile = load_profile(name)
            self.assertTrue(packet_enabled(profile))
            self.assertFalse(ownership_enabled(profile))

    def test_v14_missing_ownership_registration_is_not_a_packet_only_profile(self):
        data = declared_profile().model_dump(mode="json")
        for name in ("record_operator_decision", "record_operator_disposition"):
            del data["capabilities"][name]
        data["capabilities"]["transfer_owner"] = load_profile("flat-v1.3").capabilities["transfer_owner"].model_dump(mode="json")
        data["release_hash"] = fingerprint({k: v for k, v in data.items() if k != "release_hash"})
        with self.assertRaises(ValueError):
            validate_profile(EnvironmentProfile.model_validate(data))
