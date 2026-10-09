"""Synthetic v1.2 release and independent provider lifecycle contracts."""
import hashlib
import tempfile
import unittest
from pathlib import Path

from proofkey.adapters.world import SimulatedWorld
from proofkey.contracts import EnvironmentProfile, ReadRequest, ReadTarget, RevisionVector
from proofkey.identity import request_fingerprint
from proofkey.profiles import load_profile, normalize_input
from support import DEADLINE, FakeClock, make_binding, make_intent, make_request

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures/development/world.json"
LEGACY_HASHES = {
    "flat-v1": "cab4df81d0f37ca74a7e952db22dd185c0eb9092154564e1f199e39cd1b7a9b2",
    "nested-v1": "ea8451fe41fb2549a22904f7c11cfdd8f96306a95dbd8ba3ded93a3ff19b8cef",
    "flat-v1.1": "6a555d7a9c1b00e5c8c176c1e8a74c6fb2317aa1d0f7dfc2dbe3d84d62e03b04",
    "nested-v1.1": "cec02aae538b9139526e89fecdd57887a47bb1cb44640ec29ec5edeb46c4cd82",
}


def candidate_profile():
    """Trusted candidate makes behavioral RED independent of absent files."""
    data = load_profile("flat-v1.1").model_dump()
    data.update(profile_id="flat-v1.2", version="v1.2")
    data["authorities"]["case.completeness"] = "case"
    capability = data["capabilities"]["register_service_refusal"]
    capability["version"] = "v1.2"
    capability["conditional_coverage"]["covered_fields"].append("delivery.status")
    return EnvironmentProfile.model_validate(data)


class EngineProviderContracts(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.count = 0
        self.request = make_request(kind="service_refusal", consent_mode="unknown", arguments={"scope": "service"})

    def world(self, status="completed", profile=None):
        self.count += 1
        world = SimulatedWorld(Path(self.folder.name) / f"world-{self.count}.sqlite", FIXTURE,
                               profile=profile or candidate_profile(), clock=FakeClock())
        # Only the trusted local driver sets source state before execution.
        world.mutate("customer.request_fingerprint", request_fingerprint(self.request))
        world.mutate("customer.consent_mode", "unknown")
        world.mutate("delivery.status", status)
        return world

    def intent(self, world, **overrides):
        data = dict(binding=make_binding(request=self.request), operation="register_service_refusal",
                    arguments={"scope": "service"}, profile_version="v1.2",
                    expected_revisions=world.material_revisions(), postcondition={"service.refusal": "verified"})
        return make_intent(**{**data, **overrides})

    @staticmethod
    def read(world, method, authority, fact, **overrides):
        request = ReadRequest(case_id="C1", object_id="O1", caller_id="U1", proof_reference="synthetic-proof",
                              purpose="inspect", deadline=DEADLINE,
                              target=ReadTarget(kind="authority_facts", authority=authority, facts=[fact]), **overrides)
        port = world.bundle().case if method == "read_case" else world.bundle().delivery
        return getattr(port, method)(request)

    def test_completed_service_refusal_commits_and_reads_back_original_effect(self):
        world = self.world()
        self.assertEqual(self.read(world, "read_delivery", "delivery", "status").observations[0].value, "completed")
        intent = self.intent(world)
        result = world.bundle().delivery.register_service_refusal(intent)
        self.assertEqual(result.status, "acknowledged")
        self.assertEqual(world.effect_count("register_service_refusal"), 1)
        reply = world.bundle().delivery.read_refusal(ReadRequest(
            case_id="C1", object_id="O1", caller_id="U1", proof_reference="synthetic-proof",
            purpose="reconcile", deadline=DEADLINE, target=ReadTarget(
                kind="original_effect", operation=intent.operation, generation=intent.binding.generation,
                action_id=intent.action_id, provider_key=intent.provider_key, fingerprint=intent.argument_fingerprint)))
        self.assertEqual([(o.authority, o.fact, o.value) for o in reply.observations], [("service", "refusal", "verified")])

    def test_released_flat_and_nested_profiles_enforce_provider_completed_status(self):
        for name in ("flat-v1.2", "nested-v1.2"):
            for status, expected in (("completed", "acknowledged"), ("out_for_delivery", "rejected")):
                with self.subTest(profile=name, status=status):
                    world = self.world(status, profile=load_profile(name))
                    self.assertEqual(world.bundle().delivery.register_service_refusal(self.intent(world)).status, expected)
                    self.assertEqual(world.effect_count("register_service_refusal"), int(expected == "acknowledged"))

    def test_wrong_or_malformed_current_status_rejects_even_with_matching_revisions(self):
        for status in ("scheduled", "out_for_delivery", "unknown", "Completed", "", None, True, 1,
                       {"status": "completed"}, ["completed"]):
            with self.subTest(status=status):
                world = self.world(status)
                result = world.bundle().delivery.register_service_refusal(self.intent(world))
                self.assertEqual(result.status, "rejected")
                self.assertEqual(world.effect_count("register_service_refusal"), 0)

    def test_service_kind_body_cannot_supply_completed_source_status(self):
        world = self.world("out_for_delivery")
        intent = self.intent(world, arguments={"scope": "service", "delivery.status": "completed",
                                               "kind": "service_refusal", "status": "completed"})
        self.assertEqual(world.bundle().delivery.register_service_refusal(intent).status, "rejected")
        self.assertEqual(world.effect_count("register_service_refusal"), 0)

    def test_source_change_after_fresh_read_rejects_stale_and_new_matching_vectors(self):
        for fresh_vector in (False, True):
            with self.subTest(fresh_vector=fresh_vector):
                world = self.world()
                self.assertEqual(self.read(world, "read_delivery", "delivery", "status").observations[0].value, "completed")
                intent = self.intent(world)
                world.mutate("delivery.status", "out_for_delivery")
                if fresh_vector:
                    intent = self.intent(world)
                result = world.bundle().delivery.register_service_refusal(intent)
                self.assertEqual(result.status, "rejected")
                self.assertEqual(world.effect_count("register_service_refusal"), 0)

    def test_missing_unknown_or_wrongly_designated_service_status_coverage_rejects(self):
        for change in ("omit", "unknown", "wrong_authority"):
            with self.subTest(change=change):
                data = candidate_profile().model_dump()
                coverage = data["capabilities"]["register_service_refusal"]["conditional_coverage"]
                if change == "omit":
                    coverage["covered_fields"].remove("delivery.status")
                elif change == "unknown":
                    coverage["status"] = "unknown"
                else:
                    data["authorities"]["delivery.status"] = "model"
                world = self.world(profile=EnvironmentProfile.model_validate(data))
                self.assertEqual(world.bundle().delivery.register_service_refusal(self.intent(world)).status, "rejected")
                self.assertEqual(world.effect_count("register_service_refusal"), 0)

    def test_status_revision_is_mandatory_and_completed_to_completed_revision_race_rejects(self):
        for change in ("missing_revision", "same_value_new_revision"):
            with self.subTest(change=change):
                world = self.world()
                intent = self.intent(world)
                if change == "missing_revision":
                    revisions = dict(intent.expected_revisions.revisions)
                    del revisions["delivery.status"]
                    intent = self.intent(world, expected_revisions=RevisionVector(revisions=revisions))
                else:
                    world.mutate("delivery.status", "completed")
                self.assertEqual(world.bundle().delivery.register_service_refusal(intent).status, "rejected")
                self.assertEqual(world.effect_count("register_service_refusal"), 0)

    def test_explicit_status_coverage_activates_guard_on_legacy_version_candidate(self):
        for version in ("v1", "v1.1"):
            with self.subTest(version=version):
                data = candidate_profile().model_dump()
                data["version"] = version
                world = self.world("scheduled", profile=EnvironmentProfile.model_validate(data))
                intent = self.intent(world, profile_version=version)
                self.assertEqual(world.bundle().delivery.register_service_refusal(intent).status, "rejected")
                self.assertEqual(world.effect_count("register_service_refusal"), 0)

    def test_frozen_legacy_service_semantics_still_accept_scheduled_source(self):
        for name in ("flat-v1", "flat-v1.1"):
            with self.subTest(profile=name):
                profile = load_profile(name)
                self.assertNotIn("delivery.status", profile.capabilities["register_service_refusal"].conditional_coverage.covered_fields)
                world = self.world("scheduled", profile=profile)
                intent = self.intent(world, profile_version=profile.version)
                self.assertEqual(world.bundle().delivery.register_service_refusal(intent).status, "acknowledged")
                self.assertEqual(world.effect_count("register_service_refusal"), 1)


class EngineProfileArtifacts(unittest.TestCase):
    def test_new_releases_designate_completeness_and_cover_service_status_without_other_contract_changes(self):
        for prefix in ("flat", "nested"):
            with self.subTest(profile=prefix):
                old = load_profile(prefix + "-v1.1")
                new = load_profile(prefix + "-v1.2")
                self.assertEqual(new.profile_id, prefix + "-v1.2")
                self.assertEqual(new.version, "v1.2")
                self.assertEqual(new.authorities, {**old.authorities, "case.completeness": "case"})
                self.assertEqual(new.processes, old.processes)
                self.assertEqual(new.process_hash, old.process_hash)
                self.assertEqual(new.policy_hash, old.policy_hash)
                self.assertEqual(new.mappings, old.mappings)
                self.assertNotEqual(new.release_hash, old.release_hash)
                self.assertEqual(load_profile(ROOT / "profiles" / (new.profile_id + ".json")), new)
                old_cap = old.capabilities["register_service_refusal"].model_dump()
                new_cap = new.capabilities["register_service_refusal"].model_dump()
                self.assertEqual(new_cap["conditional_coverage"]["covered_fields"],
                                 old_cap["conditional_coverage"]["covered_fields"] + ["delivery.status"])
                for key in ("permission_basis", "acknowledgement", "readback", "idempotency_scope",
                            "timeout_seconds", "terminal_nonexecution_basis", "shared_limits", "evidence_mode"):
                    self.assertEqual(new_cap[key], old_cap[key])
                for operation in old.capabilities.keys() - {"register_service_refusal"}:
                    self.assertEqual(new.capabilities[operation], old.capabilities[operation])
                request = make_request(narrative=None)
                payload = request.model_dump(mode="json")
                if prefix == "nested":
                    payload = {"data": {"request": payload}}
                self.assertEqual(normalize_input(payload, new), request)

    def test_builtin_designation_drives_existing_scoped_completeness_read(self):
        for prefix in ("flat", "nested"):
            with self.subTest(profile=prefix), tempfile.TemporaryDirectory() as folder:
                profile = load_profile(prefix + "-v1.2")
                # This designation is consumed by initialize_process; the scoped
                # provider read already existed and is regression coverage here.
                self.assertEqual(profile.authorities.get("case.completeness"), "case")
                world = SimulatedWorld(Path(folder) / "world.sqlite", FIXTURE, profile=profile, clock=FakeClock())
                reply = EngineProviderContracts.read(world, "read_case", "case", "completeness")
                self.assertEqual([(o.authority, o.fact, o.value, o.revision) for o in reply.observations],
                                 [("case", "completeness", "complete", "v1")])

    def test_frozen_legacy_files_keep_original_bytes(self):
        for name, expected in LEGACY_HASHES.items():
            with self.subTest(profile=name):
                self.assertEqual(hashlib.sha256((ROOT / "profiles" / (name + ".json")).read_bytes()).hexdigest(), expected)
