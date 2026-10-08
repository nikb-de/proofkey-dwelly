import unittest
from pathlib import Path

from proofkey.contracts import EnvironmentProfile, ProcessSpec, ReadTarget
from proofkey.process import ProcessController
from support import load_test_profile


def original_scope(operation):
    return {"journal.original_effect": ReadTarget(kind="original_effect", operation=operation,
                generation="G1", action_id="original-action", provider_key="original-provider-key",
                fingerprint="a" * 64)}


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
                                 "wait_operator", "expired", "operator_facts", "dispatch",
                                 "stop", "stopped", "complete"}.issubset(spec.phases))
                expected_verify = "verification" if kind.startswith("reschedule") else "verify_refusal"
                expected_unknown = "outcome_unknown" if kind.startswith("reschedule") else "outcome_unknown_refusal"
                self.assertIn(expected_verify, spec.phases)
                self.assertIn(expected_unknown, spec.phases)
                self.assertFalse(ProcessController(profile, kind=kind).permits("complete", "create_return", {"refusal": "verified"}))
        goods = profile.processes["goods_refusal"]
        self.assertIn("refusal_complete", goods.phases)
        self.assertIn("verify_return", goods.phases)
        self.assertEqual(goods.completion.required_operations, ["register_goods_refusal"])
        self.assertEqual(profile.processes["service_refusal"].completion.required_operations, ["register_service_refusal", "enqueue_handoff"])

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

    def test_unknown_reconciliation_resumes_original_refusal_or_return(self):
        for kind, dispatch, unknown, verify, operation in (
            ("goods_refusal", "dispatch", "outcome_unknown_refusal", "verify_refusal", "register_goods_refusal"),
            ("service_refusal", "dispatch", "outcome_unknown_refusal", "verify_refusal", "register_service_refusal"),
            ("goods_refusal", "return_dispatch", "outcome_unknown_return", "verify_return", "create_return"),
            ("reschedule_window", "dispatch", "outcome_unknown", "verification", "reschedule"),
            ("reschedule_exact", "dispatch", "outcome_unknown", "verification", "reschedule")):
            with self.subTest(kind=kind, operation=operation):
                controller = ProcessController(load_test_profile(), kind=kind)
                self.assertEqual(controller.next_phase(dispatch, "mark_unknown", {}), unknown)
                self.assertEqual(controller.next_phase(unknown, "read_effect", original_scope(operation)), verify)
                self.assertIsNone(controller.next_phase(unknown, operation, original_scope(operation)))
                self.assertIsNone(controller.next_phase(unknown, "extract_input", original_scope(operation)))

    def test_pending_verification_allows_repeat_reads_and_mark_unknown(self):
        for kind, verify, unknown, operation in (
            ("goods_refusal", "verify_refusal", "outcome_unknown_refusal", "register_goods_refusal"),
            ("service_refusal", "verify_refusal", "outcome_unknown_refusal", "register_service_refusal"),
            ("goods_refusal", "verify_return", "outcome_unknown_return", "create_return"),
            ("reschedule_window", "verification", "outcome_unknown", "reschedule"),
            ("reschedule_exact", "verification", "outcome_unknown", "reschedule")):
            with self.subTest(kind=kind, operation=operation):
                controller = ProcessController(load_test_profile(), kind=kind)
                self.assertEqual(controller.next_phase(verify, "read_effect", original_scope(operation)), verify)
                self.assertEqual(controller.next_phase(verify, "mark_unknown", {}), unknown)
                self.assertIsNone(controller.next_phase(verify, "read_effect", original_scope("different_effect")))

    def test_operator_reconciliation_preserves_original_verification_gate(self):
        for kind, verify, wait, unknown, operation in (
            ("goods_refusal", "verify_refusal", "wait_refusal_operator", "outcome_unknown_refusal", "register_goods_refusal"),
            ("service_refusal", "verify_refusal", "wait_refusal_operator", "outcome_unknown_refusal", "register_service_refusal"),
            ("goods_refusal", "verify_return", "wait_return_operator", "outcome_unknown_return", "create_return"),
            ("reschedule_window", "verification", "wait_reschedule_operator", "outcome_unknown", "reschedule"),
            ("reschedule_exact", "verification", "wait_reschedule_operator", "outcome_unknown", "reschedule")):
            with self.subTest(kind=kind, operation=operation):
                controller = ProcessController(load_test_profile(), kind=kind)
                self.assertEqual(controller.next_phase(verify, "ask_operator", {}), wait)
                self.assertEqual(controller.next_phase(wait, "accept_operator_facts", {}), verify)
                self.assertEqual(controller.next_phase(wait, "expire_wait", {}), unknown)
                self.assertIsNone(controller.next_phase(wait, "reenter_facts", {}))

    def test_stopped_recovery_is_scoped_readonly_and_retains_stop(self):
        for kind, operation in (("goods_refusal", "create_return"), ("service_refusal", "register_service_refusal"),
                                ("reschedule_window", "reschedule"), ("reschedule_exact", "reschedule")):
            controller = ProcessController(load_test_profile(), kind=kind)
            for phase in ("stop", "stopped"):
                with self.subTest(kind=kind, phase=phase):
                    self.assertEqual(controller.next_phase(phase, "read_effect", original_scope(operation)), phase)
                    self.assertIsNone(controller.next_phase(phase, "read_effect", {}))
                    self.assertIsNone(controller.next_phase(phase, "read_effect", original_scope("different_effect")))
                    for forbidden in (operation, "authenticate", "extract_input", "ask_operator", "reenter_facts", "finish"):
                        self.assertIsNone(controller.next_phase(phase, forbidden, original_scope(operation)))

    def test_stopped_terminal_exception_cannot_reenter_business_phase(self):
        for phase in ("stop", "stopped"):
            data = load_test_profile().model_dump(mode="json")
            for edge in data["processes"]["goods_refusal"]["edges"]:
                if edge["origin"] == phase and edge["operation"] == "read_effect":
                    edge["target"] = "verify_return"
            with self.subTest(phase=phase), self.assertRaises(ValueError):
                ProcessController(EnvironmentProfile.model_validate(data), kind="goods_refusal")

    def test_service_requires_handoff_attempt_and_preserves_partial_disposition(self):
        controller = ProcessController(load_test_profile(), kind="service_refusal")
        self.assertIsNone(controller.next_phase("refusal_complete", "finish", {"service.refusal": "verified"}))
        self.assertEqual(controller.next_phase("refusal_complete", "enqueue_handoff", {"service.refusal": "verified",
                         "case.authorization": "verified", "case.generation": "current", "case.authority": "fresh",
                         "operator.packet": "current"}), "handoff_attempted")
        for disposition in ("pending", "blocked", "outcome_unknown", "accepted"):
            with self.subTest(disposition=disposition):
                saved_phase = "handoff_" + disposition
                observations = {"operator.handoff_attempt": "recorded", "operator.handoff_disposition": disposition}
                self.assertEqual(controller.next_phase("handoff_attempted", "record_handoff_" + disposition, observations), saved_phase)
                self.assertEqual(controller.next_phase(saved_phase, "finish", observations), "complete")
                self.assertIsNone(controller.next_phase(saved_phase, "finish", {"operator.handoff_disposition": "unverified"}))
                self.assertIsNone(controller.next_phase(saved_phase, "create_return", observations))
        self.assertIn("enqueue_handoff", controller.profile.processes["service_refusal"].completion.required_operations)

    def test_unknown_effect_can_finish_its_original_verified_path(self):
        goods = ProcessController(load_test_profile(), kind="goods_refusal")
        self.assertEqual(goods.next_phase("outcome_unknown_refusal", "read_effect", original_scope("register_goods_refusal")), "verify_refusal")
        self.assertEqual(goods.next_phase("verify_refusal", "verify_refusal", {"goods.refusal": "verified"}), "refusal_complete")
        self.assertEqual(goods.next_phase("refusal_complete", "finish", {}), "complete")
        self.assertEqual(goods.next_phase("outcome_unknown_return", "read_effect", original_scope("create_return")), "verify_return")
        self.assertEqual(goods.next_phase("verify_return", "verify_return", {"returns.return": "verified"}), "complete")
        self.assertIsNone(goods.next_phase("verify_return", "verify_return", {"returns.return": "acknowledged"}))

    def test_physical_message_handoff_transfer_edges_are_explicit(self):
        profile = load_test_profile()
        current = {"case.authorization": "verified", "case.generation": "current", "case.authority": "fresh",
                   "messaging.permission": "granted", "operator.packet": "current", "ownership.state": "accepted"}
        for kind in profile.processes:
            controller = ProcessController(profile, kind=kind)
            self.assertEqual(controller.next_phase("completeness", "send_clarification", current), "wait_customer")
            self.assertEqual(controller.next_phase("wait_operator", "send_status", current), "wait_operator")
            self.assertEqual(controller.next_phase("auth_gate", "enqueue_handoff", current), "wait_operator")
            self.assertEqual(controller.next_phase("wait_operator", "transfer_owner", current), "wait_operator")
            for operation in ("send_clarification", "send_status", "enqueue_handoff", "transfer_owner"):
                self.assertIn(operation, profile.capabilities)
                self.assertEqual(profile.capabilities[operation].operation, operation)
                self.assertIsNone(controller.next_phase("stopped", operation, {}))
            for observations in ({}, {"case.authorization": "verified"},
                                 {"case.authorization": "verified", "case.generation": "stale"}):
                self.assertIsNone(controller.next_phase("wait_operator", "send_status", observations))
            for missing in ("case.authority", "messaging.permission"):
                self.assertIsNone(controller.next_phase("wait_operator", "send_status", {k: v for k, v in current.items() if k != missing}))
            for state in ("unowned", "pending", "transfer_pending", "stopped"):
                self.assertIsNone(controller.next_phase("wait_operator", "transfer_owner", {**current, "ownership.state": state}))
            self.assertIsNone(controller.next_phase("wait_operator", "transfer_owner", {**current, "operator.packet": "stale"}))

    def test_physical_capabilities_cover_recipient_question_packet_and_owner(self):
        required = {
            "send_clarification": {"case.authorization", "case.generation", "messaging.permission", "messaging.recipient", "case.question_revision"},
            "send_status": {"case.authorization", "case.generation", "messaging.permission", "messaging.recipient", "case.result_revision"},
            "enqueue_handoff": {"case.authorization", "case.generation", "operator.recipient", "operator.packet_revision", "operator.packet_hash"},
            "transfer_owner": {"case.authorization", "case.generation", "ownership.state", "ownership.owner", "ownership.epoch", "operator.packet_revision", "operator.packet_hash"},
        }
        for operation, fields in required.items():
            for missing in fields:
                data = load_test_profile().model_dump(mode="json")
                capability = data["capabilities"].get(operation)
                self.assertIsNotNone(capability, operation)
                capability["conditional_coverage"]["covered_fields"] = [x for x in capability["conditional_coverage"]["covered_fields"] if x != missing]
                phase = "completeness" if operation == "send_clarification" else "auth_gate" if operation == "enqueue_handoff" else "wait_operator"
                with self.subTest(operation=operation, missing=missing):
                    self.assertFalse(ProcessController(EnvironmentProfile.model_validate(data), kind="goods_refusal").permits(
                        phase, operation, {"case.authorization": "verified", "case.generation": "current", "case.authority": "fresh",
                                           "messaging.permission": "granted", "operator.packet": "current", "ownership.state": "accepted"}))

    def test_saved_communications_have_original_scoped_readonly_recovery(self):
        for kind in ("reschedule_window", "reschedule_exact", "goods_refusal", "service_refusal"):
            controller = ProcessController(load_test_profile(), kind=kind)
            for phase, operation in (("wait_customer", "send_clarification"), ("completeness", "send_status"),
                                     ("wait_operator", "enqueue_handoff"), ("wait_operator", "transfer_owner")):
                with self.subTest(kind=kind, phase=phase, operation=operation):
                    scope = {**original_scope(operation), "ownership.state": "transfer_pending"}
                    self.assertEqual(controller.next_phase(phase, "read_communication", scope), phase)
                    self.assertIsNone(controller.next_phase(phase, "read_communication", {}))
                    self.assertIsNone(controller.next_phase(phase, "read_communication", original_scope("create_return")))
                    self.assertIsNone(controller.next_phase(phase, "read_effect", scope))
            for phase in ("stop", "stopped"):
                for operation in ("send_clarification", "send_status", "enqueue_handoff", "transfer_owner"):
                    with self.subTest(kind=kind, phase=phase, operation=operation):
                        self.assertEqual(controller.next_phase(phase, "read_communication", original_scope(operation)), phase)
                        self.assertIsNone(controller.next_phase(phase, operation, original_scope(operation)))
            self.assertIsNone(controller.next_phase("complete", "read_communication", original_scope("send_status")))

    def test_confirmation_and_service_dispositions_keep_message_receipt_scope(self):
        exact = ProcessController(load_test_profile(), kind="reschedule_exact")
        self.assertEqual(exact.next_phase("wait_confirmation", "read_communication", original_scope("send_clarification")), "wait_confirmation")
        self.assertIsNone(exact.next_phase("wait_confirmation", "read_communication", original_scope("transfer_owner")))
        service = ProcessController(load_test_profile(), kind="service_refusal")
        for phase in ("handoff_attempted", "handoff_pending", "handoff_blocked", "handoff_outcome_unknown", "handoff_accepted"):
            with self.subTest(phase=phase):
                self.assertEqual(service.next_phase(phase, "read_communication", original_scope("enqueue_handoff")), phase)
        self.assertEqual(service.next_phase("handoff_accepted", "read_communication", original_scope("transfer_owner")), "handoff_accepted")
        self.assertIsNone(service.next_phase("handoff_pending", "read_communication", original_scope("transfer_owner")))

    def test_every_physical_effect_saved_destination_can_read_its_receipt(self):
        profile = load_test_profile()
        physical = {"send_clarification", "send_status", "enqueue_handoff", "transfer_owner"}
        for kind, spec in profile.processes.items():
            controller = ProcessController(profile, kind=kind)
            for edge in spec.edges:
                if edge.operation not in physical:
                    continue
                with self.subTest(kind=kind, destination=edge.target, operation=edge.operation):
                    self.assertEqual(controller.next_phase(edge.target, "read_communication",
                                     original_scope(edge.operation)), edge.target)

    def test_handoff_record_requires_exact_qualified_disposition_cross_product(self):
        controller = ProcessController(load_test_profile(), kind="service_refusal")
        dispositions = ("pending", "blocked", "outcome_unknown", "accepted")
        for recorded in dispositions:
            for observed in dispositions:
                with self.subTest(recorded=recorded, observed=observed):
                    actual = controller.next_phase("handoff_attempted", "record_handoff_" + recorded,
                        {"operator.handoff_attempt": "recorded", "operator.handoff_disposition": observed})
                    self.assertEqual(actual, "handoff_" + recorded if recorded == observed else None)
        for recorded in dispositions:
            for observations in ({"operator.handoff_attempt": "recorded"},
                                 {"operator.handoff_attempt": "recorded", "handoff_disposition": recorded}):
                with self.subTest(recorded=recorded, observations=observations):
                    self.assertIsNone(controller.next_phase("handoff_attempted", "record_handoff_" + recorded, observations))

    def test_communication_read_control_cannot_change_phase_or_infer_receipts(self):
        for phase in ("wait_operator", "stop", "stopped"):
            data = load_test_profile().model_dump(mode="json")
            spec = data["processes"]["goods_refusal"]
            existing = next((e for e in spec["edges"] if e["origin"] == phase and e["operation"] == "read_communication"), None)
            if existing:
                existing["target"] = "return_gate"
            else:
                spec["edges"].append({"origin": phase, "operation": "read_communication", "target": "return_gate"})
                spec["operations"].append("read_communication")
            with self.subTest(phase=phase), self.assertRaises(ValueError):
                ProcessController(EnvironmentProfile.model_validate(data), kind="goods_refusal")
        controller = ProcessController(load_test_profile(), kind="goods_refusal")
        malformed = {"journal.original_effect": {"kind": "original_effect", "operation": "send_status"}}
        self.assertIsNone(controller.next_phase("wait_operator", "read_communication", malformed))
