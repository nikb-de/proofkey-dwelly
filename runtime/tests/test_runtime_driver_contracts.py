"""Closed driver identities and captured evidence, independent of legacy rows."""
from dataclasses import FrozenInstanceError, replace
from hashlib import sha256
import json
import unittest

from proofkey.assessment.driver_contracts import (DriverManifest, RunnerReceipt,
    canonical_bytes, digest_bytes, strict_loads)


def manifest_values():
    return dict(version="runtime-driver-v1", driver_id="window", obligation="R01",
        variant="positive", case_id="C1", independence_group="pilot-window",
        case_bytes_hash="a" * 64, scenario_hash="b" * 64, driver_code_hash="c" * 64,
        candidate_manifest_hash="d" * 64, profile_name="flat-v1.2", profile_hash="e" * 64,
        process_hash="f" * 64, policy_hash="0" * 64, expectation_version="pilot-v1",
        expectation_hash="1" * 64, execution_kind="public_sequence", dependency_ids=("engine",))


class DriverManifestTests(unittest.TestCase):
    def test_invalid_identities_cannot_be_registered_as_manifest(self):
        # Removing validation would admit unbound/unknown recipes.
        for field, value in [("obligation", "R00"), ("case_bytes_hash", "A" * 64),
                             ("driver_id", ""), ("dependency_ids", ["engine"]),
                             ("dependency_ids", ("engine", "engine")),
                             ("execution_kind", "shell"), ("version", "v2")]:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                DriverManifest(**{**manifest_values(), field: value})

    def test_wire_rejects_duplicate_noncanonical_and_extra_fields(self):
        data = DriverManifest(**manifest_values()).to_wire()
        raw = canonical_bytes(data)
        malformed = [json.dumps(data).encode(), raw[:-1] + b',"version":"runtime-driver-v1"}',
            canonical_bytes({**data, "unexpected": True}), canonical_bytes({k: v for k, v in data.items() if k != "obligation"})]
        for value in malformed:
            with self.subTest(raw=value), self.assertRaises(ValueError):
                DriverManifest.from_bytes(value)

    def test_canonical_json_rejects_nonfinite_overflow_deep_and_invalid_utf8(self):
        for raw in [b'{"x":NaN}', b'{"x":1e999}', b'\xff', b'[' * 40 + b'0' + b']' * 40,
                    b'{"x":1,"x":2}', b'{"x": 1}', b'{"x":9223372036854775808}']:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                strict_loads(raw)
        for value in [float("inf"), {"x": (1, 2)}, {1: "key"}, b"bytes"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                canonical_bytes(value)
        with self.assertRaises(ValueError):
            digest_bytes(bytearray(b"mutable"))

    def test_detached_access_does_not_change_manifest_or_frozen_identity(self):
        manifest = DriverManifest(**manifest_values())
        raw = manifest.to_bytes()
        detached = manifest.to_wire()
        detached["dependency_ids"].append("other")
        self.assertEqual(manifest.dependency_ids, ("engine",))
        self.assertEqual(manifest.to_bytes(), raw)
        self.assertEqual(DriverManifest.from_bytes(raw), manifest)
        with self.assertRaises(FrozenInstanceError):
            manifest.case_id = "other"


def receipt_values():
    raw = DriverManifest(**manifest_values()).to_bytes()
    return dict(manifest_bytes=raw, manifest_hash=sha256(raw).hexdigest(), ordinal=0,
                repetition=0, status="no_output")


class RunnerReceiptTests(unittest.TestCase):
    def test_absence_or_failure_cannot_claim_success_hash_or_projection(self):
        cases = [dict(status="completed"), dict(raw_output_hash="a" * 64),
                 dict(score_projection_bytes=b'{}'), dict(manifest_hash="a" * 64),
                 dict(status="success"), dict(ordinal=True), dict(ordinal=256),
                 dict(repetition=16), dict(elapsed_seconds=float("nan")),
                 dict(elapsed_seconds=-1.0), dict(process_exit=True),
                 dict(raw_event_bytes=[b'{"event_tag":"counter"}']),
                 dict(raw_event_bytes=(b'{"x":0}',))]
        for change in cases:
            with self.subTest(change=change), self.assertRaises(ValueError):
                RunnerReceipt(**{**receipt_values(), **change})

    def test_events_and_aggregate_are_bounded_without_truncation(self):
        event = b'{"event_tag":"counter","x":0}'
        for changes in [dict(raw_event_bytes=(event,) * 65),
                        dict(error_bytes=b'x' * (1048576 + 1)),
                        dict(raw_event_bytes=(canonical_bytes({"event_tag":"big", "x":"x" * 1048500}),) * 9)]:
            with self.subTest(changes=tuple(changes)), self.assertRaises(ValueError):
                RunnerReceipt(**{**receipt_values(), **changes})

    def test_completed_source_snapshot_must_explicitly_name_real_or_fixture_evidence(self):
        source = b'{"data":"unlabeled"}'
        manifest = replace(DriverManifest(**manifest_values()), candidate_manifest_hash=digest_bytes(source))
        raw = manifest.to_bytes()
        with self.assertRaises(ValueError):
            RunnerReceipt(raw, digest_bytes(raw), 0, 0, "completed", raw_output_bytes=b'{}',
                raw_output_hash=digest_bytes(b'{}'), elapsed_seconds=0.0,
                source_pre_manifest_bytes=source, source_post_manifest_bytes=source)

    def test_numeric_receipt_overflow_is_a_closed_validation_error(self):
        with self.assertRaises(ValueError):
            RunnerReceipt(**{**receipt_values(), "elapsed_seconds": 10**1000})


if __name__ == "__main__":
    unittest.main()
