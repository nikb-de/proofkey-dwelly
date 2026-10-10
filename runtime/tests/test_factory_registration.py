"""Opt-in synthetic source identity; legacy vectors are serialization only."""
import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import datetime
from hashlib import sha256
import json
import proofkey.factory as factory_api
from proofkey.factory import (AdaptationFactory, FactoryContext, FactoryDenied, ProposalMaterial,
    RegressionEvidence, RunnerIdentity, HumanReviewEvent, OriginalInventory, ReleaseDenied)
from proofkey.factory.proposal import _material_proposal, REGISTERED_IMPLEMENTATIONS
from proofkey.contracts import HumanReviewApproval
from proofkey.identity import fingerprint
from test_adaptation_factory import (ROOT, current_registration, factory_for, material, prepared,
    supported_candidate, reviewed, encoded)


class FactoryRegistrationTests(unittest.TestCase):
    @property
    def comparison_registration(self):
        from support_factory_lanes import current_v1_registration
        return current_v1_registration()

    def setUp(self):
        self.registration_type = getattr(factory_api, "SyntheticImplementationRegistration", None)
        self.assertIsNotNone(self.registration_type)

    def test_explicit_current_registration_accepts_material(self):
        self.assertIsNotNone(getattr(factory_api, "SyntheticImplementationRegistration", None))
        mat = material(supported_candidate())
        factory = factory_for(mat, implementation_registration=self.comparison_registration)
        self.assertEqual(prepared(factory, mat).proposal_id, mat.proposal_id)

    def assert_registration_denied(self, registration):
        # Invalid host registration must fail before malformed material is decoded.
        mat = material(supported_candidate(), source=b"not-json")
        with self.assertRaises(FactoryDenied) as denied:
            factory_for(mat, implementation_registration=registration)
        self.assertEqual(denied.exception.reason, "invalid_implementation_registration")

    def assert_material_denied(self, mat, reason="unsupported_adapter_implementation"):
        with self.assertRaises(FactoryDenied) as denied:
            factory_for(mat, implementation_registration=self.comparison_registration)
        self.assertEqual(denied.exception.reason, reason)

    def test_current_comparison_pins_match_selected_source_bytes(self):
        self.assertEqual(self.comparison_registration.registration_id, 'synthetic-factory-j05-current-v1')
        expected = dict(self.comparison_registration.implementations)
        self.assertEqual({path: sha256(raw).hexdigest() for path, raw in material().adapter_sources}, expected)

    def test_none_keeps_historical_admission_and_rejects_current_bytes(self):
        with self.assertRaises(FactoryDenied) as denied:
            factory_for(material(supported_candidate()), implementation_registration=None)
        self.assertEqual(denied.exception.reason, "unsupported_adapter_implementation")

    def test_registration_is_frozen_slotted_and_detached_from_caller(self):
        supplied = self.comparison_registration
        factory = factory_for(material(supported_candidate()), implementation_registration=supplied)
        retained = factory.context.implementation_registration
        self.assertIsNot(retained, supplied)
        self.assertIsNot(retained.implementations, supplied.implementations)
        self.assertFalse(hasattr(retained, "__dict__"))
        with self.assertRaises(FrozenInstanceError):
            retained.registration_id = "edited"
        # Even explicit bypass of the caller's frozen wrapper cannot edit retained authority.
        object.__setattr__(supplied, "registration_id", "caller-replaced")
        self.assertEqual(retained.registration_id, "synthetic-factory-j05-current-v1")
        mat = factory.context.materials[0]
        proposal = prepared(factory, mat)
        with self.assertRaises(TypeError):
            proposal.diff[0].after.clear()
        self.assertEqual(prepared(factory, mat), proposal)

    def test_reordered_pins_and_sources_keep_canonical_binding(self):
        registration = self.comparison_registration
        mat = material(supported_candidate())
        forward = factory_for(mat, implementation_registration=registration)
        reverse_mat = replace(mat, adapter_sources=tuple(reversed(mat.adapter_sources)))
        reverse = factory_for(reverse_mat, implementation_registration=replace(
            registration, implementations=tuple(reversed(registration.implementations))))
        self.assertEqual(prepared(forward, mat), prepared(reverse, reverse_mat))
        self.assertEqual(forward.context.implementation_registration.implementations,
                         tuple(sorted(registration.implementations)))

    def test_registration_identity_requires_bounded_exact_ascii_value(self):
        registration = self.comparison_registration
        class StringSubclass(str):
            pass
        for value in ("", "a" * 129, "Uppercase", "a b", "../a", "/a", "-a", "é", "a\n", 1,
                      StringSubclass("synthetic")):
            with self.subTest(value=value):
                self.assert_registration_denied(replace(registration, registration_id=value))
        for value in ("a", "a" * 128, "a._-0"):
            with self.subTest(valid=value):
                factory_for(material(supported_candidate()), implementation_registration=replace(
                    registration, registration_id=value))

    def test_registration_provenance_is_exact_synthetic_literal(self):
        registration = self.comparison_registration
        class StringSubclass(str):
            pass
        for value in (None, "actual", "synthetic_rehearsal", "", StringSubclass(registration.provenance)):
            with self.subTest(value=value):
                self.assert_registration_denied(replace(registration, provenance=value))

    def test_registration_rejects_subclasses_and_mutable_container_aliases(self):
        registration = self.comparison_registration
        class RegistrationSubclass(self.registration_type):
            pass
        class TupleSubclass(tuple):
            pass
        pins = registration.implementations
        values = (RegistrationSubclass(registration.registration_id, registration.provenance, pins),
                  {"registration_id": registration.registration_id, "provenance": registration.provenance,
                   "implementations": pins},
                  replace(registration, implementations=list(pins)),
                  replace(registration, implementations=dict(pins)),
                  replace(registration, implementations=TupleSubclass(pins)),
                  replace(registration, implementations=(list(pins[0]), *pins[1:])),
                  replace(registration, implementations=(TupleSubclass(pins[0]), *pins[1:])),
                  replace(registration, implementations=((pins[0][0], [pins[0][1]]), *pins[1:])))
        for value in values:
            with self.subTest(value_type=type(value), pins_type=type(getattr(value, "implementations", None))):
                self.assert_registration_denied(value)

    def test_registration_inventory_requires_each_exact_path_once(self):
        registration = self.comparison_registration
        pins = registration.implementations
        class StringSubclass(str):
            pass
        invalid = (pins[:-1], (*pins, ("extra.py", "0" * 64)), (*pins[:-1], pins[0]), (),
                   ((), *pins[1:]), ((pins[0][0], pins[0][1], "extra"), *pins[1:]))
        invalid += tuple(((alias, pins[0][1]), *pins[1:]) for alias in (
            "./adapters/operator.py", "adapters/../adapters/operator.py", "/adapters/operator.py",
            "adapters//operator.py", "adapters\\operator.py", StringSubclass(pins[0][0])))
        for value in invalid:
            with self.subTest(pins=value):
                self.assert_registration_denied(replace(registration, implementations=value))

    def test_registration_hashes_require_exact_lowercase_sha256(self):
        registration = self.comparison_registration
        pins = registration.implementations
        class StringSubclass(str):
            pass
        for value in ("", "a" * 63, "a" * 65, "A" * 64, "g" * 64, "0" * 63 + "\n", None,
                      StringSubclass(pins[0][1])):
            with self.subTest(value=value):
                self.assert_registration_denied(replace(registration,
                    implementations=((pins[0][0], value), *pins[1:])))

    def test_source_drift_missing_extra_duplicate_and_aliases_are_rejected(self):
        mat = material(supported_candidate())
        sources = mat.adapter_sources
        changed = ((sources[0][0], sources[0][1] + b"\n"), *sources[1:])
        variants = (changed, sources[:-1], (*sources, ("extra.py", b"extra")),
                    (*sources[:-1], sources[0]), (),
                    (("./" + sources[0][0], sources[0][1]), *sources[1:]))
        for value in variants:
            with self.subTest(paths=[pair[0] for pair in value]):
                self.assert_material_denied(replace(mat, adapter_sources=value))

    def test_source_types_are_exact_immutable_primitives(self):
        mat = material(supported_candidate())
        sources = mat.adapter_sources
        class BytesSubclass(bytes):
            pass
        for value, reason in ((list(sources), "invalid_material"),
                              ((list(sources[0]), *sources[1:]), "invalid_adapter_sources"),
                              (((sources[0][0], bytearray(sources[0][1])), *sources[1:]), "invalid_adapter_sources"),
                              (((sources[0][0], BytesSubclass(sources[0][1])), *sources[1:]), "invalid_adapter_sources")):
            with self.subTest(value_type=type(value)):
                self.assert_material_denied(replace(mat, adapter_sources=value), reason)

    def test_explicit_source_size_ceilings_precede_hash_admission(self):
        mat = material(supported_candidate())
        limit = 2 * 1024 * 1024
        self.assert_material_denied(replace(mat, adapter_sources=(
            (mat.adapter_sources[0][0], b"x" * (limit + 1)), *mat.adapter_sources[1:])),
            "material_limit_exceeded")
        # Seven individually bounded sources exceed the aggregate cap before inventory matching.
        self.assert_material_denied(replace(mat, adapter_sources=tuple(
            (str(i), b"x" * limit) for i in range(7))), "material_limit_exceeded")
        # Exactly-at-limit bytes reach hash admission rather than being rejected as oversized.
        self.assert_material_denied(replace(mat, adapter_sources=tuple(
            (path, b"x" * limit) for path, _ in mat.adapter_sources)))

    def test_historical_fixture_serialization_digest(self):
        historical = current_registration()
        expected = {"registration_id": "synthetic-factory-installed-resources-v1",
                    "provenance": "local_controlled_synthetic",
                    "inventory_sha256": "93959331816f018f3d13f1071cd4298468b428e7c79f253c81542893f6ce0b85"}
        self.assertEqual(historical.registration_id, expected["registration_id"])
        self.assertEqual(historical.provenance, expected["provenance"])
        self.assertEqual(sha256(encoded([{"path": path, "sha256": digest}
            for path, digest in sorted(historical.implementations)])).hexdigest(), expected["inventory_sha256"])

    def test_current_comparison_digest_and_all_resolution_paths_agree(self):
        from support_factory_lanes import fixed_current_fixture
        factory, proposal, regression, approval, packet = reviewed(implementation_registration=self.comparison_registration)
        mat = factory.context.materials[0]
        _, _, _, body = _material_proposal(mat, factory.context.implementation_registration)
        expected = {"registration_id": "synthetic-factory-j05-current-v1",
                    "provenance": "local_controlled_synthetic",
                    "inventory_sha256": fixed_current_fixture()["current_v1_inventory_sha256"]}
        self.assertEqual(body["implementation_registration"], expected)
        self.assertEqual(factory._resolve(proposal)[4]["implementation_registration"], expected)
        self.assertEqual(factory._proposal_hash(proposal.proposal_hash), prepared(factory, mat))
        self.assertEqual(factory.check_proposal(proposal, fingerprint(json.loads(regression.receipt))), packet)
        stage = factory.release_profile(packet, approval, [])
        self.assertEqual(json.loads(stage.manifest)["implementation_registration"], expected)
        self.assertEqual(stage.status, "staged_simulation")
        body["implementation_registration"]["registration_id"] = "external-edit"
        self.assertEqual(json.loads(factory.release_profile(packet, approval, []).manifest)[
            "implementation_registration"], expected)

    def test_different_registration_ids_separate_proposals_regressions_reviews_and_stages(self):
        a = self.comparison_registration
        b = replace(a, registration_id="synthetic-factory-second-id")
        first, second = reviewed(implementation_registration=a), reviewed(implementation_registration=b)
        self.assertNotEqual(first[1].proposal_hash, second[1].proposal_hash)
        self.assertNotEqual(first[0].release_profile(first[4], first[3], []).receipt.release_hash,
                            second[0].release_profile(second[4], second[3], []).receipt.release_hash)
        for target, foreign in ((first, second), (second, first)):
            factory, proposal, regression, approval, packet = target
            other, other_proposal, other_regression, other_approval, other_packet = foreign
            with self.assertRaises(FactoryDenied) as denied:
                factory.check_proposal(other_proposal, fingerprint(json.loads(other_regression.receipt)))
            self.assertEqual(denied.exception.reason, "proposal_unregistered")
            with self.assertRaises(ReleaseDenied) as denied:
                factory.release_profile(other_packet, other_approval, [])
            self.assertEqual(denied.exception.reason, "proposal_unregistered")
            wrong_regression = AdaptationFactory(replace(factory.context, regressions=(other_regression,)))
            with self.assertRaises(FactoryDenied) as denied:
                wrong_regression.check_proposal(proposal, fingerprint(json.loads(other_regression.receipt)))
            self.assertEqual(denied.exception.reason, "regression_binding_mismatch")
            wrong_review = AdaptationFactory(replace(factory.context, reviews=other.context.reviews))
            with self.assertRaises(ReleaseDenied) as denied:
                wrong_review.release_profile(packet, other_approval, [])
            self.assertEqual(denied.exception.reason, "approval_binding_mismatch")
            with self.assertRaises(ReleaseDenied) as denied:
                wrong_review.release_profile(packet, approval, [])
            self.assertEqual(denied.exception.reason, "approval_untrusted")

    def test_legacy_serialization_matches_prechange_literal_vectors(self):
        vector = json.loads((ROOT / "tests/fixtures/factory-legacy-vectors-v1.json").read_text())
        self.assertEqual(vector["scope"], "serialization_only")
        self.assertEqual(vector["source_commit"], "336b0bb0f9b9e2b6118c34de825200c80764fd2e")
        self.assertEqual(dict(REGISTERED_IMPLEMENTATIONS), vector["historical_pins"])
        fields = dict(vector["material"])
        fields["adapter_sources"] = tuple((path, raw.encode()) for path, raw in fields["adapter_sources"])
        for name in set(fields) - {"proposal_id", "adapter_sources"}:
            fields[name] = fields[name].encode()
        mat = ProposalMaterial(**fields)
        regression = RegressionEvidence(vector["regression"].encode())
        approval = HumanReviewApproval.model_validate_json(vector["approval"])
        event = HumanReviewEvent(approval.proof_reference, vector["approval"].encode(), "human", "synthetic_rehearsal")
        context = FactoryContext((mat,), (regression,),
            (RunnerIdentity("controlled-local-tests", "local_controlled_synthetic", json.loads(vector["proposal"])["test_hash"]),),
            (event,), OriginalInventory("synthetic-complete-1", "controlled_fixture",
                json.loads(mat.baseline)["release_hash"], ()), datetime.fromisoformat(vector["now"]))
        factory = AdaptationFactory(context)
        proposal = prepared(factory, mat)
        self.assertEqual(encoded(proposal.model_dump(mode="json")), vector["proposal"].encode())
        self.assertEqual(proposal.proposal_hash, vector["proposal_hash"])
        self.assertEqual(encoded(factory._resolve(proposal)[4]), vector["proposal_body"].encode())
        packet = factory.check_proposal(proposal, fingerprint(json.loads(regression.receipt)))
        self.assertEqual(encoded(packet.model_dump(mode="json")), vector["review_packet"].encode())
        stage = factory.release_profile(packet, approval, [])
        self.assertEqual(stage.manifest, vector["staged_manifest"].encode())
        self.assertEqual(stage.receipt_bytes, vector["staged_receipt"].encode())
        self.assertEqual(stage.receipt.release_hash, vector["stage_hash"])
        self.assertNotIn("implementation_registration", json.loads(stage.manifest))


if __name__ == "__main__":
    unittest.main()
