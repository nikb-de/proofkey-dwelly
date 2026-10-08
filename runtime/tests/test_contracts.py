"""Boundary tests: losing strictness, identity inputs or snapshots is a bug."""
import json
import unittest
from datetime import datetime, timezone

from proofkey import contracts as c
from proofkey.identity import fingerprint, stable_action_id
from support import (FakeClock, make_auth, make_binding, make_checkpoint,
                     make_intent, make_request, make_result)


def wire_examples():
    """Small independent public JSON records for every planned boundary."""
    when = "2026-10-08T10:00:00Z"
    digest = "1" * 64
    binding = make_binding().model_dump(mode="json")
    vector = {"revisions": {"delivery.status": "v1"}}
    observation = {"authority": "delivery", "fact": "status", "object_id": "O1",
                   "value": "scheduled", "revision": "v1", "observed_at": when,
                   "provider_at": when, "evidence_ref": "E1"}
    verification = {"status": "pending"}
    budget = {"case_id": "C1", "deadline": when}
    locator = {"kind": "unknown", "reason": "coordinates unavailable"}
    assertion = {"artifact_id": "A1", "content_hash": digest, "lineage_hash": digest,
                 "locator": locator, "uncertainty": "unverified", "processing_receipt_id": "P1",
                 "claim": "customer supplied requested slot"}
    proposal = {"operation": "reschedule", "stage": "commit", "arguments": {"slot": "S1"},
                "evidence_refs": ["E1"]}
    capability = {"operation": "reschedule", "authority": "scheduling"}
    process = {"process_id": "reschedule-window", "version": "v1", "release_hash": digest,
               "phases": ["start", "done"], "edges": [{"origin": "start", "target": "done"}],
               "operations": ["reschedule"], "completion": {"phase": "done", "required_operations": ["reschedule"]}}
    profile = {"profile_id": "flat-v1", "version": "v1", "release_hash": digest,
               "mappings": {"status": {"source_path": "status", "canonical_field": "status"}},
               "authorities": {"status": "delivery"}, "capabilities": {"reschedule": capability},
               "policy_hash": digest, "process_hash": digest}
    processor = {"case_id": "C1", "generation": "G1", "role": "planning", "campaign_id": "CAM1",
                 "permit_hash": digest, "input_hashes": [digest], "provider": "replay", "model": "fixture-v1",
                 "endpoint": "offline", "prompt_hash": digest, "version": "v1", "profile_version": "v1",
                 "process_version": "v1", "deadline": when}
    human = {"binding": binding, "owner": "OP1", "epoch": 1, "state_revision": "v1",
             "packet_id": "PK1", "packet_hash": digest, "packet_revision": "v1", "state": "pending"}
    approval = {"proposal_hash": digest, "regression_hash": digest, "reviewer_id": "H1", "proof_reference": "proof",
                "scope": ["flat-v1"], "decision": "approved", "reviewed_at": when, "mode": "simulated"}
    command = {"command": ["python3", "-m", "unittest"], "exit_code": 0, "artifact_hashes": {"report": digest}}
    evidence = {"reference_hash": digest, "source_hash": digest, "label_hash": digest,
                "rubric_hash": digest, "lineage_hash": digest}
    return {
        "CanonicalRequest": make_request().model_dump(mode="json"),
        "AuthContext": {"caller_id": "U1", "proof_reference": "synthetic-proof"},
        "ReadTarget": {"kind": "authority_facts", "authority": "delivery", "facts": ["status"]},
        "ReadRequest": {"case_id": "C1", "object_id": "O1", "caller_id": "U1", "proof_reference": "proof",
                        "purpose": "verify", "deadline": when,
                        "target": {"kind": "original_effect", "operation": "reschedule", "generation": "G1",
                                   "action_id": digest, "provider_key": "key", "fingerprint": digest}},
        "RequestBinding": binding,
        "AuthorityObservation": observation,
        "AuthorityReadback": {"operation": "reschedule", "object_id": "O1", "observations": [observation],
                              "stage": "commit", "nonexecution": {"status": "unknown"}, "as_of": when,
                              "evidence_refs": ["E1"]},
        "RevisionVector": vector,
        "OperationCapability": capability,
        "EffectIntent": make_intent().model_dump(mode="json"),
        "DispatchResult": {"status": "acknowledged", "provider_request_id": "P1", "evidence_refs": ["E1"]},
        "VerificationResult": verification,
        "PhaseCheckpoint": make_checkpoint().model_dump(mode="json"),
        "BudgetLedger": budget,
        "WaitState": {"question_id": "Q1", "binding": binding, "origin": "select", "next_gate": "commit",
                      "recipient": "U1", "owner_state_revision": "v1", "awaited_fields": ["slot"],
                      "expires_at": when, "budget": budget},
        "ScopedReply": {"question_id": "Q1", "binding": binding, "actor_id": "U1", "proof_reference": "proof",
                        "request_revision": "v1", "consent_revision": "v1", "owner_state_revision": "v1",
                        "fields": {"slot": "S1"}, "received_at": when, "simulated": True},
        "OperatorPacket": {"packet_id": "PK1", "case_id": "C1", "object_id": "O1", "binding": binding,
                           "packet_hash": digest, "packet_revision": "v1", "owner": "OP1", "owner_state": "pending",
                           "epoch": 1, "state_revision": "v1", "source_scope": ["E1"], "expires_at": when,
                           "replay_id": "RP1"},
        "OperatorReceipt": {"packet_id": "PK1", "packet_hash": digest, "packet_revision": "v1", "binding": binding,
                            "owner": "OP1", "epoch": 1, "state_revision": "v1", "status": "accepted",
                            "evidence_ref": "E1", "received_at": when, "replay_id": "RP1", "simulated": True},
        "OperatorDecision": {"decision_id": "D1", "packet_id": "PK1", "packet_hash": digest, "packet_revision": "v1",
                             "binding": binding, "owner": "OP1", "epoch": 1, "state_revision": "v1",
                             "actor_id": "OP1", "proof_reference": "proof", "decision": "approve",
                             "scope": ["reschedule"], "expires_at": when, "replay_id": "RP1", "simulated": True},
        "TransferIntent": {"transfer_id": "T1", "binding": binding, "case_id": "C1", "packet_id": "PK1",
                           "packet_hash": digest, "packet_revision": "v1", "expected_owner": "OP1",
                           "expected_state_revision": "v1", "expected_epoch": 1, "target_owner": "OP2", "expires_at": when},
        "HumanOwnership": human,
        "ArtifactRecord": {"artifact_id": "A1", "original_hash": digest, "mime_type": "text/plain", "source": "synthetic",
                           "case_id": "C1", "access": "synthetic", "created_at": when, "lineage_hash": digest},
        "ProcessingReceipt": {"invocation_id": "I1", "role": "planning", "provider": "replay", "requested_model": "fixture-v1",
                              "observed_model": "fixture-v1", "prompt_hash": digest, "version": "v1", "input_hashes": [digest],
                              "mode": "replay", "status": "completed", "latency_seconds": 0.1,
                              "usage": {"input_tokens": 1}, "output": {"kind": "proposal", "proposal": proposal},
                              "output_hashes": [digest], "output_refs": ["E1"], "processed_at": when},
        "EvidenceAssertion": assertion,
        "CampaignPermit": {"campaign_id": "CAM1", "permit_hash": digest, "input_hashes": [digest], "role": "planning",
                           "provider": "replay", "model": "fixture-v1", "endpoint": "offline", "privacy_approval": "reviewed",
                           "rights_approval": "reviewed", "max_cost": 0.0, "max_usage": {"tokens": 5}, "max_invocations": 1,
                           "expires_at": when, "approval_receipt": "H1", "mode": "simulated"},
        "ProcessorIdentity": processor,
        "InvocationRequest": {"identity": processor, "invocation_id": "I1", "requested_usage": {"tokens": 5}, "worst_case_cost": 0.0},
        "InvocationReservation": {"identity": processor, "invocation_id": "I1", "reserved_usage": {"tokens": 5},
                                  "worst_case_cost": 0.0, "status": "consumed", "case_debit": 1, "role_debit": 1,
                                  "campaign_debit": 1, "reserved_at": when},
        "ActionProposal": proposal,
        "GateDecision": {"allowed": False, "reason": "missing authority", "verification": {"status": "rejected"}},
        "SavedResult": make_result().model_dump(mode="json"),
        "CaseResult": {"status": "error", "correlation_id": "original", "reason": "unavailable"},
        "ProcessSpec": process,
        "EnvironmentProfile": profile,
        "AdaptationProposal": {"proposal_id": "PR1", "source_hash": digest, "baseline_hash": digest, "proposal_hash": digest,
                               "diff": [{"path": "mappings/status", "before": "status", "after": "delivery.status"}],
                               "test_hash": digest, "migration": {"strategy": "preserve", "affected_contracts": []}, "agent_hash": digest},
        "ReviewPacket": {"proposal_hash": digest, "regression_hash": digest, "affected_pending_contracts": ["I1"],
                         "approval": approval},
        "ReleaseReceipt": {"version": "v2", "release_hash": digest, "proposal_hash": digest, "regression_hash": digest,
                           "profile_hash": digest, "process_hash": digest, "policy_hash": digest,
                           "preserved_contract_hashes": [digest], "approval": approval, "released_at": when},
        "HumanReviewApproval": approval,
        "ExportReceipt": {"supplied_case_id": "C1", "output_name": "C1.json", "output_hash": digest, "status": "written", "as_of": when},
        "BatchReceipt": {"supplied_case_ids": ["C1"], "exports": [{"supplied_case_id": "C1", "output_name": "C1.json",
                         "output_hash": digest, "status": "written", "as_of": when}], "deadline": when,
                         "active_seconds": 1.0, "as_of": when, "measured_reserve_seconds": 2.0},
        "LedgerAudit": {**evidence, "total_cases": 1, "included_cases": 1, "ambiguous_cases": 0,
                        "excluded_cases": 0, "findings": []},
        "CaseAssessment": {**evidence, "case_id": "C1", "effect_verdicts": {"reschedule": {"verdict": "correct", "evidence_refs": ["E1"]}},
                           "repeatability": {"runs": 2, "agreements": 2}, "sensitivity": {"trials": 1, "detected": 1},
                           "noise": {"trials": 1, "disagreements": 0}, "qualification_limits": ["synthetic only"]},
        "QualificationReceipt": {**evidence, "candidate_hash": digest, "assessment_hashes": [digest],
                                 "total_cases": 1, "included_cases": 1, "ambiguous_cases": 0, "excluded_cases": 0,
                                 "status": "rehearsal", "qualification_limits": ["synthetic only"], "as_of": when},
        "DrillReceipt": {"workload_hash": digest, "candidate_hash": digest, "baseline_hash": digest, "result_hash": digest,
                         "started_at": when, "ended_at": when, "active_seconds": 0.0, "wall_seconds": 0.0,
                         "waits": [], "partial_case_ids": [], "mode": "rehearsal"},
        "IsolationReceipt": {"candidate_hash": digest, "workload_hash": digest, "result_hash": digest,
                             "identity_hash": digest, "custody_hash": digest, "probes": [{"name": "canary", "enforced": True,
                             "evidence_ref": "probe1"}], "status": "rehearsal", "observed_at": when},
        "SourceReleaseReceipt": {"candidate_hash": digest, "file_hashes": {"contracts.py": digest}, "rights_hash": digest,
                                 "dependency_hash": digest, "release_hash": digest, "created_at": when},
        "ReproductionReceipt": {"candidate_hash": digest, "commands": [command], "observed_artifact_hashes": {"report": digest},
                                "started_at": when, "ended_at": when},
        "ImplementationAudit": {"candidate_hash": digest, "requirements": [{"requirement_id": "R1", "status": "missing",
                                "evidence_refs": [], "reason": "provider assessment absent"}], "missing_evidence": ["provider"],
                                "invalid_evidence": [], "audited_at": when},
    }


class ContractTests(unittest.TestCase):
    def test_denied_and_error_reason_reject_private_account_canary(self):
        for status in ("denied", "error"):
            payload = {"status": status, "correlation_id": "public-id",
                       "reason": "private-account-canary-secret-detail"}
            for validate in (c.CaseResult.model_validate,
                             lambda value: c.CaseResult.model_validate_json(json.dumps(value))):
                with self.subTest(status=status, validate=validate):
                    with self.assertRaises(ValueError):
                        validate(payload)

    def test_denied_and_error_json_roundtrip_has_closed_generic_reason(self):
        for status in ("denied", "error"):
            for reason in ("denied", "unavailable", "invalid_request", "runtime_error", "deadline_exceeded"):
                with self.subTest(status=status, reason=reason):
                    result = c.CaseResult(status=status, correlation_id="public-id", reason=reason)
                    expected = {"status": status, "correlation_id": "public-id", "reason": reason}
                    self.assertEqual(json.loads(result.model_dump_json()), expected)
                    self.assertEqual(c.CaseResult.model_validate_json(result.model_dump_json()).model_dump(mode="json"), expected)
        with self.assertRaises(ValueError):
            c.CaseResult(status="error", correlation_id="public-id", reason="unavailable: private-account-canary").model_dump_json()

    def test_synthetic_return_builder_accepts_all_verification_statuses(self):
        for status in ("verified", "rejected", "pending", "outcome_unknown", "conflict"):
            with self.subTest(status=status):
                result = make_result(return_status=status)
                self.assertEqual(result.effects["create_return"].status, status)
                self.assertEqual(c.SavedResult.model_validate_json(result.model_dump_json()).effects["create_return"].status, status)

    def test_synthetic_verified_return_builder_binds_complete_record(self):
        binding = make_binding(case_id="C9", generation="G2")
        when = datetime(2026, 10, 8, 11, tzinfo=timezone.utc)
        result = make_result(binding=binding, return_status="verified", as_of=when)
        effect = result.effects["create_return"]
        self.assertEqual(effect.object_id, "O1")
        # Independently hashed canonical create_return/initiate identity and inventory.
        self.assertEqual(effect.action_id, "94074a32586ce8b8999efe0527e9c23dc2683e543d05f8a973bf32762584ba2a")
        self.assertEqual(effect.fingerprint, "34f96779d7ba2c0d523ff38019669cb33b5765ee5755f06fc94b8f8bddff599c")
        self.assertEqual(effect.postcondition, {"return_status": "created", "inventory": {"item-1": 1}})
        self.assertEqual(effect.evidence_refs, ["synthetic-return-verification"])
        self.assertEqual(effect.as_of, when)
        self.assertEqual(result.binding.case_id, "C9")
        self.assertIn("Synthetic", result.rationale)

    def test_binding_fingerprint_captures_business_kind_and_consent_not_transport_noise(self):
        first = make_binding(request=make_request(arguments={"slot": "S1"}, consent_mode="window"))
        consent = make_binding(request=make_request(arguments={"slot": "S1"}, consent_mode="exact_slot"))
        kind = make_binding(request=make_request(arguments={"slot": "S1"}, kind="goods_refusal"))
        narrative = make_binding(request=make_request(arguments={"slot": "S1"}, narrative="Please change this"))
        self.assertNotEqual(first.fingerprint, consent.fingerprint)
        self.assertNotEqual(first.fingerprint, kind.fingerprint)
        self.assertEqual(first.fingerprint, narrative.fingerprint)
        self.assertNotEqual(first.fingerprint, fingerprint({"slot": "S1"}))

    def test_related_records_cannot_mix_cases_or_objects(self):
        examples = wire_examples()
        for name, field, wrong in (("OperatorPacket", "case_id", "C2"),
                                   ("OperatorPacket", "object_id", "O2"),
                                   ("TransferIntent", "case_id", "C2")):
            with self.subTest(model=name, field=field):
                with self.assertRaises(ValueError):
                    getattr(c, name).model_validate({**examples[name], field: wrong})
        with self.assertRaises(ValueError):
            make_checkpoint(budget=c.BudgetLedger(case_id="C2", deadline="2026-10-08T12:00:00Z"))
        with self.assertRaises(ValueError):
            c.WaitState.model_validate({**examples["WaitState"], "budget": {"case_id": "C2", "deadline": "2026-10-08T12:00:00Z"}})

    def test_revision_keys_identify_authority_and_fact(self):
        for key in ("status", "delivery.", ".status"):
            with self.assertRaises(ValueError):
                c.RevisionVector(revisions={key: "v1"})
        c.RevisionVector(revisions={"delivery.status": "v1", "scheduling.slot": "v2"})

    def test_conditional_coverage_qualifies_material_fact_identities(self):
        with self.assertRaises(ValueError):
            c.OperationCapability(operation="reschedule", authority="scheduling",
                conditional_coverage={"status": "supported", "basis": "provider-contract", "covered_fields": ["status"]})
        c.OperationCapability(operation="reschedule", authority="scheduling",
            conditional_coverage={"status": "supported", "basis": "provider-contract",
                                  "covered_fields": ["delivery.status", "scheduling.slot"]})

    def test_consent_is_business_scope_and_narrative_is_independent(self):
        request = make_request(consent_mode="window", narrative=None)
        self.assertIsNone(request.narrative)
        self.assertEqual(make_request(consent_mode="exact_slot").consent_mode, "exact_slot")
        for mode in ("structured_only", "text", "audio", "multimodal"):
            with self.assertRaises(ValueError):
                make_request(consent_mode=mode)

    def test_processor_roles_have_shared_canonical_names(self):
        for name in ("ProcessorIdentity", "ProcessingReceipt", "CampaignPermit"):
            payload = wire_examples()[name]
            for role in ("extraction", "transcription", "planning"):
                with self.subTest(model=name, role=role):
                    getattr(c, name).model_validate({**payload, "role": role})
            for role in ("extractor", "transcriber", "planner"):
                with self.assertRaises(ValueError):
                    getattr(c, name).model_validate({**payload, "role": role})

    def test_profile_carries_typed_versioned_processes(self):
        payload = wire_examples()["EnvironmentProfile"]
        process = wire_examples()["ProcessSpec"]
        profile = c.EnvironmentProfile.model_validate({**payload, "processes": {"reschedule_window": process}})
        self.assertIsInstance(profile.processes["reschedule_window"], c.ProcessSpec)
        self.assertEqual(profile.processes["reschedule_window"].version, "v1")
        with self.assertRaises(ValueError):
            c.EnvironmentProfile.model_validate({**payload, "processes": {"reschedule_window": {"phases": []}}})

    def test_review_packet_preserves_proposed_material_and_compatibility(self):
        examples = wire_examples()
        packet = c.ReviewPacket.model_validate({**examples["ReviewPacket"], "proposed_profile": examples["EnvironmentProfile"],
                  "proposed_processes": {"reschedule_window": examples["ProcessSpec"]},
                  "compatibility": {"strategy": "preserve", "affected_contracts": ["I1"]}})
        self.assertEqual(packet.compatibility.affected_contracts, ["I1"])
        self.assertIsInstance(packet.proposed_profile, c.EnvironmentProfile)
        with self.assertRaises(ValueError):
            c.ReviewPacket.model_validate({**examples["ReviewPacket"], "compatibility": {"safe": True}})

    def test_denied_wire_exposes_only_correlation_and_generic_reason(self):
        result = c.CaseResult(status="denied", correlation_id="public-id", reason="denied")
        self.assertEqual(json.loads(result.model_dump_json()),
                         {"status": "denied", "correlation_id": "public-id", "reason": "denied"})
        self.assertEqual(result.model_dump(mode="json"),
                         {"status": "denied", "correlation_id": "public-id", "reason": "denied"})

    def test_terminal_nonexecution_proof_cannot_be_fabricated_from_status(self):
        with self.assertRaises(ValueError):
            c.NonexecutionProof(status="proven")
        self.assertEqual(c.NonexecutionProof(status="proven", basis="provider_terminal_contract",
                                             evidence_ref="E1").status, "proven")

    def test_supported_capability_requires_designated_basis(self):
        with self.assertRaises(ValueError):
            c.CapabilityContract(status="supported")
        c.CapabilityContract(status="supported", basis="provider_idempotency_contract")

    def test_typed_budget_rejects_negative_bool_and_nonfinite_counts(self):
        for field, values in (("tool_calls", [-1, True, "2", 1.1]),
                              ("active_seconds", [-1.0, True, "2", float("nan"), float("inf")])):
            for value in values:
                with self.subTest(field=field, value=value):
                    with self.assertRaises(ValueError):
                        c.BudgetLedger.model_validate({"case_id": "C1", "deadline": "2026-10-08T12:00:00Z", field: value})

    def test_frozen_copy_revalidates_and_does_not_mutate_original(self):
        intent = make_intent()
        with self.assertRaises(ValueError):
            intent.model_copy(update={"arguments": {"slot": "S2"}})
        with self.assertRaises(ValueError):
            intent.deadline = datetime.now(timezone.utc)
        self.assertEqual(intent.arguments["slot"], "S1")

    def test_every_planned_wire_model_has_strict_json_roundtrip(self):
        for name, payload in wire_examples().items():
            with self.subTest(model=name):
                model = getattr(c, name)
                value = model.model_validate(payload)
                wire = value.model_dump(mode="json")
                self.assertEqual(model.model_validate_json(value.model_dump_json()).model_dump(mode="json"), wire)
                self.assertEqual(model.model_validate(wire).model_dump(mode="json"), wire)
                with self.assertRaises(ValueError):
                    model.model_validate({**wire, "permission_granted": True})

    def test_capability_defaults_are_explicit_unknown_not_permission(self):
        capability = c.OperationCapability(operation="reschedule", authority="scheduling")
        wire = capability.model_dump(mode="json")
        for field in ("permission_basis", "acknowledgement", "readback", "idempotency_scope",
                      "conditional_coverage", "terminal_nonexecution_basis"):
            self.assertEqual(wire[field]["status"], "unknown")
        self.assertIsNone(capability.timeout_seconds)
        self.assertIsNone(capability.shared_limits.quota)
        with self.assertRaises(ValueError):
            c.OperationCapability(operation="reschedule", authority="scheduling", permission_basis=True)

    def test_tagged_read_target_forbids_hidden_world_and_cross_variant_fields(self):
        for target in ({"kind": "hidden_world"}, {"kind": "authority_facts", "authority": "delivery", "facts": ["status"], "action_id": "A1"},
                       {"kind": "original_effect", "operation": "reschedule"}):
            with self.subTest(target=target):
                with self.assertRaises(ValueError):
                    c.ReadTarget.model_validate(target)

    def test_locator_does_not_invent_coordinates_or_allow_invalid_bounds(self):
        payload = wire_examples()["EvidenceAssertion"]
        for locator in ({"kind": "text_span", "start": -1, "end": 4},
                        {"kind": "text_span", "start": 5, "end": 4},
                        {"kind": "audio_time", "start_seconds": 5.0, "end_seconds": 4.0},
                        {"kind": "unknown", "reason": "absent", "page": 1}):
            with self.subTest(locator=locator):
                with self.assertRaises(ValueError):
                    c.EvidenceAssertion.model_validate({**payload, "locator": locator})

    def test_verified_result_requires_effect_identity_and_evidence(self):
        with self.assertRaises(ValueError):
            c.VerificationResult(status="verified")
        valid = c.VerificationResult(status="verified", object_id="O1", action_id="A1",
                                     fingerprint="1" * 64, postcondition={"slot": "S1"},
                                     evidence_refs=["E1"], as_of="2026-10-08T10:00:00Z")
        self.assertEqual(valid.status, "verified")

    def test_gate_denial_requires_rejected_verification(self):
        for verification in (None, {"status": "pending"}, {"status": "outcome_unknown"}):
            with self.assertRaises(ValueError):
                c.GateDecision(allowed=False, reason="denied", verification=verification)

    def test_body_cannot_grant_permission(self):
        payload = make_request().model_dump(mode="json")
        payload["permission_granted"] = True
        with self.assertRaises(ValueError):
            c.CanonicalRequest.model_validate(payload)

    def test_required_identity_cannot_be_absent_empty_or_coerced(self):
        for field in ("case_id", "object_id", "principal_id", "request_id",
                      "request_revision", "consent_revision"):
            for value in (None, "", 1, True, [], {}):
                with self.subTest(field=field, value=value):
                    payload = make_request().model_dump(mode="json")
                    payload[field] = value
                    with self.assertRaises(ValueError):
                        c.CanonicalRequest.model_validate(payload)
            payload = make_request().model_dump(mode="json")
            del payload[field]
            with self.assertRaises(ValueError):
                c.CanonicalRequest.model_validate(payload)

    def test_nonfinite_arguments_rejected_at_any_depth(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    make_request(arguments={"nested": [{"quantity": value}]})
                with self.assertRaises(ValueError):
                    fingerprint({"quantity": value})

    def test_wire_statuses_reject_unknown_values_and_coercion(self):
        for model, valid in ((c.DispatchResult, {"status": "acknowledged"}),
                             (c.VerificationResult, {"status": "pending"})):
            for status in ("success", "", 1, True):
                with self.subTest(model=model.__name__, status=status):
                    with self.assertRaises(ValueError):
                        model.model_validate({**valid, "status": status})
        with self.assertRaises(ValueError):
            make_checkpoint(processing_status="finished")

    def test_naive_deadline_rejected(self):
        for deadline in (datetime(2026, 10, 8, 12), "2026-10-08T12:00:00"):
            with self.subTest(deadline=deadline):
                with self.assertRaises(ValueError):
                    make_intent(deadline=deadline)

    def test_same_generation_identity_is_stable_and_arguments_separate(self):
        binding = make_binding()
        first = stable_action_id(binding, "reschedule", "commit")
        self.assertEqual(len(first), 64)
        self.assertEqual(first, stable_action_id(binding, "reschedule", "commit"))
        for other, operation, stage in ((make_binding(generation="G2"), "reschedule", "commit"),
                                        (binding, "create_return", "initiate"),
                                        (binding, "reschedule", "prepare"),
                                        (make_binding(case_id="C2"), "reschedule", "commit")):
            self.assertNotEqual(first, stable_action_id(other, operation, stage))
        changed = make_binding(fingerprint=fingerprint({"slot": "S2"}))
        self.assertEqual(first, stable_action_id(changed, "reschedule", "commit"))
        self.assertNotEqual(fingerprint({"slot": "S1"}), fingerprint({"slot": "S2"}))

    def test_fingerprint_has_hand_checked_canonical_bytes(self):
        # SHA-256 of UTF-8 b'{"a":1,"b":2}', independently checked.
        self.assertEqual(fingerprint({"b": 2, "a": 1}),
                         "43258cff783fe7036d8a43033f830adfc60ec037382473548ac742b888292777")
        for value in ({1: "bad"}, {"object": object()}, {"set": {1}}, [1]):
            with self.subTest(value=value):
                with self.assertRaises((TypeError, ValueError)):
                    fingerprint(value)

    def test_prepared_arguments_and_vector_are_defensive_immutable_snapshots(self):
        args = {"inventory": {"item-1": 1}, "slots": ["S1"]}
        revisions = {"delivery.status": "v1"}
        intent = make_intent(arguments=args,
                             argument_fingerprint=fingerprint(args),
                             expected_revisions=c.RevisionVector(revisions=revisions))
        before = intent.model_dump_json()
        args["inventory"]["item-1"] = 8
        args["slots"].append("S2")
        revisions["delivery.status"] = "v2"
        self.assertEqual(intent.model_dump_json(), before)
        for mutation in (lambda: intent.arguments["inventory"].update({"item-1": 9}),
                         lambda: intent.arguments["slots"].append("S3"),
                         lambda: intent.expected_revisions.revisions.update({"delivery.status": "v3"})):
            with self.assertRaises(TypeError):
                mutation()

    def test_mismatched_prepared_fingerprint_rejected(self):
        with self.assertRaises(ValueError):
            make_intent(argument_fingerprint="0" * 64)

    def test_builders_revalidate_overrides_and_derive_binding(self):
        request = make_request(case_id="C9", request_revision="v8", consent_revision="v7")
        binding = make_binding(request=request)
        self.assertEqual((binding.case_id, binding.request_revision, binding.consent_revision),
                         ("C9", "v8", "v7"))
        self.assertEqual(binding.fingerprint, fingerprint({"kind": request.kind, "consent_mode": request.consent_mode,
                                                          "arguments": request.arguments}))
        with self.assertRaises(ValueError):
            make_auth(caller_id=1)
        result = make_result(case_id="C9", return_status="outcome_unknown")
        self.assertEqual(result.case_id, "C9")
        self.assertEqual(result.effects["create_return"].status, "outcome_unknown")
        self.assertIsInstance(result, c.CaseResult)

    def test_denied_result_cannot_contain_authorized_material(self):
        denied = c.CaseResult(status="denied", correlation_id="caller-correlation", reason="denied")
        self.assertEqual(denied.case_id, "caller-correlation")
        self.assertTrue(denied.exportable)
        for extra in ({"binding": make_binding()}, {"effects": {"return": c.VerificationResult(status="pending")}},
                      {"evidence_refs": ["internal"]}):
            with self.assertRaises(ValueError):
                c.CaseResult.model_validate({**denied.model_dump(), **extra})

    def test_fake_clock_has_aware_deterministic_time(self):
        clock = FakeClock()
        start = clock.now()
        clock.advance(3.5)
        self.assertEqual((clock.now() - start).total_seconds(), 3.5)
        self.assertEqual(clock.now().tzinfo, timezone.utc)


if __name__ == "__main__":
    unittest.main()
