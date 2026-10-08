import unittest
from pathlib import Path

from proofkey.contracts import EnvironmentProfile, ProcessSpec
from proofkey.process import ProcessController
from support import load_test_profile


class ProcessTests(unittest.TestCase):
    def test_original_process_files_match_typed_profile_bundle(self):
        profile = load_test_profile()
        root = Path(__file__).resolve().parents[1] / "processes"
        for kind, process in profile.processes.items():
            source = root / (kind.replace("_", "-") + ".json")
            self.assertEqual(ProcessSpec.model_validate_json(source.read_text()), process)

    def test_return_requires_verified_refusal(self):
        controller = ProcessController(load_test_profile())
        self.assertFalse(controller.permits("return_gate", "create_return", {"refusal": "acknowledged"}))
        self.assertTrue(controller.permits("return_gate", "create_return", {"refusal": "verified"}))

    def test_unknown_conditional_and_readback_capabilities_fail_closed(self):
        for field in ("conditional_coverage", "readback", "permission_basis", "idempotency_scope"):
            data = load_test_profile().model_dump(mode="json")
            data["capabilities"]["create_return"][field] = {"status": "unknown"}
            profile = EnvironmentProfile.model_validate(data)
            with self.subTest(field=field):
                self.assertFalse(ProcessController(profile).permits("return_gate", "create_return", {"refusal": "verified"}))

    def test_exact_slot_never_uses_window_commit(self):
        controller = ProcessController(load_test_profile(), kind="reschedule_exact")
        self.assertFalse(controller.permits("window_gate", "reschedule", {"consent": "window"}))
        self.assertFalse(controller.permits("exact_gate", "reschedule", {"consent": "exact_slot", "confirmation": "acknowledged"}))
        self.assertTrue(controller.permits("exact_gate", "reschedule", {"consent": "exact_slot", "confirmation": "verified"}))

    def test_graphs_cover_saved_wait_stop_and_independent_refusal_states(self):
        profile = load_test_profile()
        for kind, spec in profile.processes.items():
            with self.subTest(kind=kind):
                self.assertEqual(ProcessSpec.model_validate_json(spec.model_dump_json()), spec)
                self.assertTrue({"intake", "extraction", "completeness", "auth_gate", "wait_customer",
                                 "wait_operator", "expired", "operator_facts", "dispatch", "verification",
                                 "outcome_unknown", "stop", "stopped", "complete"}.issubset(spec.phases))
                self.assertFalse(ProcessController(profile, kind=kind).permits("complete", "create_return", {"refusal": "verified"}))
        goods = profile.processes["goods_refusal"]
        self.assertIn("refusal_complete", goods.phases)
        self.assertIn("verify_return", goods.phases)
        self.assertEqual(goods.completion.required_operations, ["register_goods_refusal"])
        self.assertEqual(profile.processes["service_refusal"].completion.required_operations, ["register_service_refusal"])

    def test_unknown_phase_operation_kind_and_native_contracts_denied(self):
        controller = ProcessController(load_test_profile())
        for phase, operation in (("diagram_permission", "create_return"), ("return_gate", "create_internal_case"),
                                 ("stop", "create_return"), ("return_gate", "remind")):
            self.assertFalse(controller.permits(phase, operation, {"refusal": "verified"}))
        with self.assertRaises(ValueError):
            ProcessController(load_test_profile(), kind="unknown")
        data = load_test_profile().model_dump(mode="json")
        data["capabilities"]["create_return"]["evidence_mode"] = "actual"
        self.assertFalse(ProcessController(EnvironmentProfile.model_validate(data)).permits("return_gate", "create_return", {"refusal": "verified"}))

    def test_incomplete_material_coverage_and_unknown_graph_readback_denied(self):
        for mutate in (lambda d: d["capabilities"]["create_return"]["conditional_coverage"].update(covered_fields=["goods.refusal"]),
                       lambda d: d["processes"]["goods_refusal"]["readbacks"].update(create_return={"status": "unknown"})):
            data = load_test_profile().model_dump(mode="json")
            mutate(data)
            profile = EnvironmentProfile.model_validate(data)
            self.assertFalse(ProcessController(profile, kind="goods_refusal").permits("return_gate", "create_return", {"refusal": "verified"}))

    def test_return_material_snapshot_must_cover_refusal_revision(self):
        data = load_test_profile().model_dump(mode="json")
        coverage = data["capabilities"]["create_return"]["conditional_coverage"]["covered_fields"]
        data["capabilities"]["create_return"]["conditional_coverage"]["covered_fields"] = [x for x in coverage if x != "goods.refusal"]
        self.assertFalse(ProcessController(EnvironmentProfile.model_validate(data), kind="goods_refusal").permits("return_gate", "create_return", {"goods.refusal": "verified"}))

    def test_ambiguous_graph_requires_explicit_kind(self):
        profile = load_test_profile()
        self.assertFalse(ProcessController(profile).permits("intake", "extract_input", {}))
        self.assertTrue(ProcessController(profile, kind="goods_refusal").permits("intake", "extract_input", {}))

    def test_waits_expiry_and_operator_facts_return_to_validation(self):
        for kind in ("reschedule_window", "reschedule_exact", "goods_refusal", "service_refusal"):
            controller = ProcessController(load_test_profile(), kind=kind)
            self.assertEqual(controller.next_phase("wait_operator", "accept_operator_facts", {}), "operator_facts")
            self.assertEqual(controller.next_phase("operator_facts", "reenter_facts", {}), "completeness")
            self.assertEqual(controller.next_phase("wait_customer", "expire_wait", {}), "expired")
            self.assertIsNone(controller.next_phase("wait_operator", "create_return", {"refusal": "verified"}))

    def test_verification_and_unknown_outcome_cannot_finish_unverified(self):
        controller = ProcessController(load_test_profile(), kind="goods_refusal")
        self.assertFalse(controller.permits("verify_refusal", "verify_refusal", {"refusal": "acknowledged"}))
        self.assertTrue(controller.permits("verify_refusal", "verify_refusal", {"goods.refusal": "verified"}))
        self.assertFalse(controller.permits("outcome_unknown", "finish", {"refusal": "verified"}))
        self.assertFalse(controller.permits("return_gate", "create_return", {"refusal": "verified", "goods.refusal": "acknowledged"}))

    def test_malformed_graph_rejected(self):
        for mutate in (lambda d: d["processes"]["goods_refusal"]["edges"][0].update(target="missing"),
                       lambda d: d["processes"]["goods_refusal"]["waits"][0].update(next_gate="dispatch")):
            data = load_test_profile().model_dump(mode="json")
            mutate(data)
            with self.assertRaises(ValueError):
                ProcessController(EnvironmentProfile.model_validate(data), kind="goods_refusal")

    def test_missing_consent_and_authorization_do_not_block_stop_or_handoff(self):
        for kind, phase in (("reschedule_exact", "exact_gate"), ("goods_refusal", "return_gate"),
                            ("reschedule_window", "auth_gate")):
            controller = ProcessController(load_test_profile(), kind=kind)
            self.assertEqual(controller.next_phase(phase, "request_stop", {}), "stop")
            self.assertEqual(controller.next_phase(phase, "ask_operator", {}), "wait_operator")

    def test_incomplete_intake_can_ask_for_missing_facts_and_expire(self):
        controller = ProcessController(load_test_profile(), kind="reschedule_exact")
        self.assertFalse(controller.permits("completeness", "authenticate", {}))
        self.assertTrue(controller.permits("completeness", "authenticate", {"case.completeness": "complete"}))
        self.assertTrue(controller.permits("completeness", "ask_customer", {}))
        self.assertTrue(controller.permits("wait_confirmation", "expire_wait", {}))
        self.assertFalse(controller.permits("auth_gate", "read_authority", {}))
        self.assertTrue(controller.permits("auth_gate", "read_authority", {"case.authorization": "verified"}))
