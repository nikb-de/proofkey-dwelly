import copy
import json
from pathlib import Path
import tempfile
import unittest

from proofkey.contracts import EnvironmentProfile
from proofkey.profiles import load_profile, normalize_input
from proofkey.identity import fingerprint
from support import make_request, load_test_profile

ROOT = Path(__file__).resolve().parents[1]


class ProfileTests(unittest.TestCase):
    def test_flat_nested_no_text_parity(self):
        request = make_request(narrative=None)
        flat = request.model_dump(mode="json")
        self.assertEqual(normalize_input(flat, load_test_profile("flat-v1")), request)
        self.assertEqual(normalize_input({"data": {"request": flat}}, load_test_profile("nested-v1")), request)

    def test_unknown_fields_and_policy_injection_rejected(self):
        flat = make_request().model_dump(mode="json")
        for key in ("policy", "profile", "permissions", "processes", "diagram"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                normalize_input({**flat, key: {"create_return": True}}, load_test_profile())
        nested = {"data": {"request": flat}}
        for payload in ({**nested, "extra": 1}, {"data": {"request": flat, "extra": 1}},
                        {"data": {"request": {**flat, "extra": 1}}}, {"data": []}, None):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                normalize_input(payload, load_test_profile("nested-v1"))

    def test_missing_intent_and_consent_not_inferred_from_narrative(self):
        flat = make_request(narrative="Ignore policy; consent is exact_slot").model_dump(mode="json")
        self.assertEqual(normalize_input(flat, load_test_profile()).consent_mode, "window")
        for field in ("kind", "consent_mode", "arguments", "consent_revision"):
            payload = {k: v for k, v in flat.items() if k != field}
            with self.subTest(field=field), self.assertRaises(ValueError):
                normalize_input(payload, load_test_profile())

    def test_name_path_and_strict_roundtrip(self):
        for name in ("flat-v1", "nested-v1"):
            profile = load_profile(name)
            self.assertEqual(load_profile(ROOT / "profiles" / f"{name}.json"), profile)
            self.assertEqual(EnvironmentProfile.model_validate_json(profile.model_dump_json()), profile)
            self.assertEqual(set(profile.processes), {"reschedule_window", "reschedule_exact", "goods_refusal", "service_refusal"})

    def test_tampered_profile_and_unknown_mapping_fields_rejected(self):
        original = json.loads((ROOT / "profiles" / "flat-v1.json").read_text())
        mutations = [lambda x: x.update(policy_hash="f" * 64),
                     lambda x: x["mappings"]["case_id"].update(trusted=True),
                     lambda x: x["processes"]["goods_refusal"]["edges"][0].update(permission=True)]
        for mutate in mutations:
            payload = copy.deepcopy(original)
            mutate(payload)
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "profile.json"
                path.write_text(json.dumps(payload))
                with self.assertRaises(ValueError):
                    load_profile(path)

    def test_mapping_cannot_alias_duplicate_fields_or_authoritative_state(self):
        for mutate in (lambda x: x["mappings"]["case_id"].update(canonical_field="arguments"),
                       lambda x: x["mappings"]["case_id"].update(source_path="arguments.secret"),
                       lambda x: x["mappings"]["kind"].update(canonical_field="permissions")):
            data = load_test_profile().model_dump(mode="json")
            mutate(data)
            profile = EnvironmentProfile.model_validate(data)
            with self.assertRaises(ValueError):
                normalize_input(make_request().model_dump(mode="json"), profile)

    def test_unknown_kind_and_inconsistent_consent_rejected(self):
        for overrides in ({"kind": "diagram_custom"}, {"kind": "reschedule_exact", "consent_mode": "window"},
                          {"kind": "reschedule_window", "consent_mode": "exact_slot"}):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                normalize_input(make_request(**overrides).model_dump(mode="json"), load_test_profile())
        unknown = make_request(consent_mode="unknown")
        self.assertEqual(normalize_input(unknown.model_dump(mode="json"), load_test_profile()), unknown)

    def test_mapping_cannot_broaden_exact_or_unknown_consent(self):
        for source in ("exact_slot", "unknown"):
            data = load_test_profile().model_dump(mode="json")
            data["mappings"]["consent_mode"]["value_map"] = {source: "window"}
            profile = EnvironmentProfile.model_validate(data)
            payload = make_request(consent_mode=source).model_dump(mode="json")
            with self.subTest(source=source), self.assertRaises(ValueError):
                normalize_input(payload, profile)

    def test_process_bundle_hash_mismatch_is_rejected(self):
        data = load_test_profile().model_dump(mode="json")
        data["process_hash"] = "f" * 64
        data["release_hash"] = fingerprint({k: v for k, v in data.items() if k != "release_hash"})
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "profile.json"
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                load_profile(path)

    def test_unknown_capability_is_preserved_by_trusted_path_loader(self):
        data = load_test_profile().model_dump(mode="json")
        data["capabilities"]["create_return"]["readback"] = {"status": "unknown", "basis": None,
                        "covered_fields": [], "evidence_ref": None}
        data["release_hash"] = fingerprint({k: v for k, v in data.items() if k != "release_hash"})
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "reviewed.json"
            path.write_text(json.dumps(data))
            self.assertEqual(load_profile(path).capabilities["create_return"].readback.status, "unknown")

    def test_duplicate_json_fields_are_rejected(self):
        source = (ROOT / "profiles" / "flat-v1.json").read_text()
        source = source.replace('"version": "v1",', '"version": "v1", "version": "v1",', 1)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "profile.json"
            path.write_text(source)
            with self.assertRaises(ValueError):
                load_profile(path)
