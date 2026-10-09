"""Synthetic host evidence; no actual agent, human, activation or HTTP receipt."""
import copy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from proofkey.contracts import (AdaptationProposal, EnvironmentProfile, HumanReviewApproval,
                               ReviewPacket, ReadRequest, ReadTarget)
from proofkey.factory import (AdaptationFactory, FactoryContext, FactoryDenied, ProposalMaterial,
    RegressionEvidence, RunnerIdentity, HumanReviewEvent, OriginalInventory, ReleaseDenied,
    prepare_proposal, check_proposal, release_profile)
from proofkey.identity import fingerprint
from proofkey.profiles import load_profile
from proofkey.process import ProcessController
from proofkey.verifier import verify
from proofkey.adapters.world import SimulatedWorld
from proofkey.journal import CaseStore
from support import NOW, DEADLINE, FakeClock, make_intent, make_request, make_binding, make_checkpoint
from test_packet_source import content_for

ROOT = Path(__file__).resolve().parents[1]


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode()


def candidate_profile():
    value = load_profile("flat-v1.3").model_dump(mode="json")
    value["profile_id"] = "synthetic-adaptation-content-readiness"
    for kind, spec in value["processes"].items():
        if kind in {"reschedule_window", "reschedule_exact"}:
            spec["process_id"] += "-adaptation"
            spec["version"] = "v1-adaptation-readiness"
            origin = next(edge["origin"] for edge in spec["edges"] if edge["operation"] == "reschedule")
            spec["prerequisites"].append({"phase": origin, "authority": "scheduling", "fact": "slot", "expected": "S0"})
        spec["release_hash"] = fingerprint({k: v for k, v in spec.items() if k != "release_hash"})
    value["process_hash"] = fingerprint(value["processes"])
    value["release_hash"] = fingerprint({k: v for k, v in value.items() if k != "release_hash"})
    return EnvironmentProfile.model_validate(value)


def supported_candidate():
    value = load_profile("flat-v1.3").model_dump(mode="json")
    value["profile_id"] = "synthetic-content-supported-control"
    value["release_hash"] = fingerprint({k: v for k, v in value.items() if k != "release_hash"})
    return EnvironmentProfile.model_validate(value)


def changed_contracts(baseline, candidate):
    # Hand-selected expected affected IDs for this fixture, independent of factory.
    return sorted(["capability:enqueue_handoff:" + baseline.capabilities["enqueue_handoff"].version,
                   *["process:" + kind + ":" + spec.version for kind, spec in baseline.processes.items()
                     if spec != candidate.processes[kind]]])


def material(candidate=None, **changes):
    baseline, candidate = load_profile("flat-v1.2"), candidate or candidate_profile()
    before, after = baseline.model_dump(mode="json"), candidate.model_dump(mode="json")
    diff = [{"path": key, "before": before[key], "after": after[key]} for key in before
            if key not in {"profile_id", "version", "release_hash", "process_hash"} and before[key] != after[key]]
    tests = {"suite": "synthetic-adaptation-v1", "required_cases": ["business_rejection", "queue_only",
        "content_stored", "identity_digest_weaker"]}
    if candidate.processes["reschedule_window"].version != "v1":
        tests["required_cases"] += ["readiness_false_missing", "readiness_current_true", "candidate_dispatch"]
    data = dict(proposal_id="synthetic-proposal-1", source=encoded({"source_id": "synthetic-owned-source",
        "rights": "synthetic_rehearsal_only", "http_status_reference": 200,
        "http_transport_execution": "unavailable", "readiness": "existing authoritative scheduling.slot must equal S0 before reschedule"}),
        baseline=encoded(baseline.model_dump(mode="json")), candidate=encoded(candidate.model_dump(mode="json")),
        tests=encoded(tests), agent=encoded({"agent_id": "synthetic-coding-agent", "mode": "synthetic",
        "authorship": "unestablished"}), diff=encoded(diff), migration=encoded({"strategy": "preserve",
        "affected_contracts": changed_contracts(baseline, candidate)}),
        adapter_sources=tuple((name, (ROOT / "src/proofkey" / name).read_bytes()) for name in
            ("adapters/operator.py", "adapters/world.py", "verifier.py", "packet_contracts.py", "process.py", "profiles.py")),
        reviewed_supplement=encoded(load_profile("flat-v1.3").model_dump(mode="json")))
    return ProposalMaterial(**{**data, **changes})


def current_registration():
    """Load independent fixed pins; submitted material never selects authority."""
    from proofkey.factory import SyntheticImplementationRegistration
    data = json.loads((ROOT / "tests/fixtures/factory-current-registration-v1.json").read_text())
    return SyntheticImplementationRegistration(data["registration_id"], data["provenance"],
                                             tuple(data["implementations"].items()))


_DEFAULT_REGISTRATION = object()


def factory_for(mat=None, regressions=(), reviews=(), pending=(), inventory=True,
                implementation_registration=_DEFAULT_REGISTRATION):
    mat = mat or material()
    base = EnvironmentProfile.model_validate_json(mat.baseline)
    context = FactoryContext(materials=(mat,), regressions=tuple(regressions),
        runners=(RunnerIdentity("controlled-local-tests", "local_controlled_synthetic", fingerprint(json.loads(mat.tests))),),
        reviews=tuple(reviews), inventory=OriginalInventory("synthetic-complete-1", "controlled_fixture",
        base.release_hash, tuple(encoded(i.model_dump(mode="json")) for i in pending)) if inventory else None, now=NOW,
        implementation_registration=(current_registration() if implementation_registration is _DEFAULT_REGISTRATION
                                     else implementation_registration))
    return AdaptationFactory(context)


def prepared(factory, mat):
    return factory.prepare_proposal(mat.source, EnvironmentProfile.model_validate_json(mat.baseline), mat.agent)


def executed_cases(candidate):
    """Execute existing public provider/verifier/graph locally, no fake interpreter."""
    outputs = {}
    with tempfile.TemporaryDirectory() as directory:
        clock = FakeClock()
        path = ROOT / "fixtures/development/packet-world-v1.json"
        fixture = json.loads(path.read_text())
        world = SimulatedWorld(Path(directory) / "provider.sqlite", path, profile=candidate, clock=clock)
        content = content_for(fixture, candidate)
        content["policy"]["process_version"] = candidate.processes["goods_refusal"].version
        from proofkey.packet_contracts import packet_postcondition, PacketContentV1
        content = PacketContentV1.model_validate(content).model_dump(mode="json")
        args = dict(packet_id="P1", packet_revision="v1", packet_hash="b" * 64,
                    recipient="OP1", packet_contract="packet-content-v1", content_hash=fingerprint(content), content=content)
        intent = make_intent(operation="enqueue_handoff", stage="enqueue", arguments=args,
            profile_version=candidate.version, process_version=content["policy"]["process_version"],
            postcondition=packet_postcondition(args), expected_revisions=world.material_revisions(),
            ownership_state_revision="v1", ownership_epoch=0)
        def read():
            return world.bundle().operator.read_receipt(ReadRequest(case_id="C1", object_id="O1", caller_id="U1",
                proof_reference="synthetic-proof", purpose="reconcile", deadline=DEADLINE,
                target=ReadTarget(kind="original_effect", operation=intent.operation, generation="G1",
                    action_id=intent.action_id, provider_key=intent.provider_key, fingerprint=intent.argument_fingerprint)))
        world.set_fault("enqueue_handoff", "business_rejection")
        rejection = world.bundle().operator.enqueue_handoff(intent)
        world.set_fault("read_receipt", "terminal_not_executed")
        rejected = verify(intent, read(), profile=candidate)
        assert rejection.status == "rejected" and rejected.status == "rejected" and world.effect_count("enqueue_handoff") == 0, (rejection, rejected)
        outputs["business_rejection"] = rejection.model_dump(mode="json")
    with tempfile.TemporaryDirectory() as directory:
        clock = FakeClock()
        world = SimulatedWorld(Path(directory) / "provider.sqlite", path, profile=candidate, clock=clock)
        self_ack = world.bundle().operator.enqueue_handoff(intent)
        assert self_ack.status == "acknowledged"
        reply = read()
        queue = reply.model_copy(update={"observations": [o for o in reply.observations if o.fact != "packet_content_receipt"]})
        assert verify(intent, queue, profile=candidate).status == "outcome_unknown"
        outputs["queue_only"] = verify(intent, queue, profile=candidate).model_dump(mode="json")
        result = verify(intent, reply, profile=candidate)
        assert result.status == "verified" and result.reason == "authoritative_content_stored_owner_pending"
        outputs["content_stored"] = result.model_dump(mode="json")
        wrong = reply.model_copy(update={"action_id": "wrong"})
        wrong_fingerprint = reply.model_copy(update={"fingerprint": "0" * 64})
        altered = reply.model_copy(update={"observations": [o.model_copy(update={"value": {**o.value,
            "content_hash": "0" * 64}}) if o.fact == "packet_content_receipt" else o for o in reply.observations]})
        weaker = intent.model_copy(update={"postcondition": {"packet_id": "P1"}})
        statuses = [verify(intent, wrong, profile=candidate).status, verify(intent, wrong_fingerprint, profile=candidate).status,
                    verify(intent, altered, profile=candidate).status, verify(weaker, reply, profile=candidate).status]
        assert statuses == ["conflict"] * 4
        outputs["identity_digest_weaker"] = {"statuses": statuses}
    if candidate.processes["reschedule_window"].version == "v1":
        return tuple({"case_id": name, "result": "passed", "output_hash": fingerprint(output)} for name, output in sorted(outputs.items()))
    controller = ProcessController(candidate, "reschedule_window")
    process = candidate.processes["reschedule_window"]
    edge = next(e for e in process.edges if e.operation == "reschedule")
    current = {r.authority + "." + r.fact: r.expected for r in process.prerequisites if r.phase == edge.origin and r.fact != "slot"}
    assert controller.next_phase(edge.origin, "reschedule", current) is None
    assert controller.next_phase(edge.origin, "reschedule", {**current, "scheduling.slot": "other"}) is None
    assert controller.next_phase(edge.origin, "reschedule", {**current, "scheduling.slot": "S0"}) == edge.target
    assert controller.next_phase("stopped", "reschedule", {**current, "scheduling.slot": "S0"}) is None
    outputs["readiness_false_missing"] = {"missing": "blocked", "false": "blocked"}
    outputs["readiness_current_true"] = {"next_phase": edge.target, "stopped": "blocked"}
    return tuple({"case_id": name, "result": "passed", "output_hash": fingerprint(output)} for name, output in sorted(outputs.items()))


def evidence(mat, proposal, result=None, cases=None, **changes):
    candidate = EnvironmentProfile.model_validate_json(mat.candidate)
    result = result or ("unavailable" if candidate.processes["reschedule_window"].version != "v1" else "passed")
    data = dict(proposal_hash=proposal.proposal_hash, candidate_hash=candidate.release_hash,
        baseline_hash=proposal.baseline_hash, test_hash=proposal.test_hash, runner_id="controlled-local-tests",
        provenance="local_controlled_synthetic", execution_id="synthetic-local-execution-1", executed_at=NOW.isoformat(),
        result=result, cases=list(executed_cases(candidate) if cases is None else cases))
    return RegressionEvidence(encoded({**data, **changes}))


def approval_for(proposal, regression):
    return HumanReviewApproval(proposal_hash=proposal.proposal_hash, regression_hash=fingerprint(json.loads(regression.receipt)),
        reviewer_id="synthetic-human-reviewer", proof_reference="synthetic-review-event", scope=["review_profile", "review_process"],
        decision="approved", reviewed_at=NOW, mode="simulated")


def reviewed(mat=None, pending=(), **context_changes):
    mat = mat or material(supported_candidate())
    proposal = prepared(factory_for(mat, implementation_registration=context_changes.get(
        "implementation_registration", _DEFAULT_REGISTRATION)), mat)
    regression = evidence(mat, proposal)
    approval = approval_for(proposal, regression)
    event = HumanReviewEvent(approval.proof_reference, encoded(approval.model_dump(mode="json")), "human", "synthetic_rehearsal")
    factory = factory_for(mat, regressions=(regression,), reviews=(event,), pending=pending, **context_changes)
    packet = factory.check_proposal(proposal, fingerprint(json.loads(regression.receipt)))
    return factory, proposal, regression, approval, packet


class AdaptationFactoryTests(unittest.TestCase):
    def test_truthful_capability_leaf_cannot_omit_changed_semantic_siblings(self):
        mat = material(supported_candidate())
        diffs = json.loads(mat.diff)
        capability = next(item for item in diffs if item["path"] == "capabilities")
        partial = {"path": "capabilities.enqueue_handoff.version",
                   "before": capability["before"]["enqueue_handoff"]["version"],
                   "after": capability["after"]["enqueue_handoff"]["version"]}
        # This leaf is truthful but omits changed permission/ack/readback/coverage.
        changed = replace(mat, diff=encoded([item if item["path"] != "capabilities" else partial for item in diffs]))
        with self.assertRaises(FactoryDenied) as denied:
            prepared(factory_for(changed), changed)
        self.assertEqual(denied.exception.reason, "incomplete_diff")

    def test_diff_paths_must_be_unique_complete_semantic_top_level_fields(self):
        mat = material(supported_candidate())
        diffs = json.loads(mat.diff)
        capability = next(item for item in diffs if item["path"] == "capabilities")
        leaf = {"path": "capabilities.enqueue_handoff.version",
                "before": capability["before"]["enqueue_handoff"]["version"],
                "after": capability["after"]["enqueue_handoff"]["version"]}
        for label, declared, reason in (("duplicate", [*diffs, capability], "invalid_diff"),
            ("overlapping", [*diffs, leaf], "incomplete_diff"),
            ("foreign", [*diffs, {"path": "foreign", "before": None, "after": "claim"}], "incomplete_diff"),
            ("missing", [item for item in diffs if item["path"] != "capabilities"], "incomplete_diff")):
            changed = replace(mat, diff=encoded(declared))
            with self.subTest(label=label):
                with self.assertRaises(FactoryDenied) as denied:
                    prepared(factory_for(changed), changed)
                self.assertEqual(denied.exception.reason, reason)

    def test_proposal_is_deterministic_and_detached(self):
        mat = material()
        factory = factory_for(mat)
        proposal = prepared(factory, mat)
        self.assertIsInstance(proposal, AdaptationProposal)
        self.assertEqual(proposal, prepared(factory, mat))
        source = json.loads(mat.source)
        reordered = encoded(dict(reversed(list(source.items()))))
        self.assertEqual(proposal, factory.prepare_proposal(reordered, load_profile("flat-v1.2"), mat.agent))
        self.assertEqual(proposal.baseline_hash, load_profile("flat-v1.2").release_hash)
        self.assertEqual(proposal.source_hash, fingerprint(source))
        self.assertEqual(proposal.migration.affected_contracts, changed_contracts(load_profile("flat-v1.2"), candidate_profile()))
        reverse = replace(mat, diff=encoded(list(reversed(json.loads(mat.diff)))),
                          adapter_sources=tuple(reversed(mat.adapter_sources)))
        self.assertEqual(proposal, prepared(factory_for(reverse), reverse))

    def test_rehashed_unregistered_supplement_cannot_mint_new_authority(self):
        raw = supported_candidate().model_dump(mode="json")
        supplement = load_profile("flat-v1.3").model_dump(mode="json")
        for value in (raw, supplement):
            value["authorities"]["secret.access"] = "secret"
            value["release_hash"] = fingerprint({key: item for key, item in value.items() if key != "release_hash"})
        mat = material(EnvironmentProfile.model_validate(raw), reviewed_supplement=encoded(supplement))
        with self.assertRaises(FactoryDenied):
            prepared(factory_for(mat), mat)

    def test_forged_complete_pass_cannot_overrule_known_candidate_dispatch_gap(self):
        mat = material()
        proposal = prepared(factory_for(mat), mat)
        cases = (*executed_cases(candidate_profile()), {"case_id": "candidate_dispatch", "result": "passed", "output_hash": "0" * 64})
        reg = evidence(mat, proposal, result="passed", cases=cases)
        with self.assertRaises(FactoryDenied) as denied:
            factory_for(mat, regressions=(reg,)).check_proposal(proposal, fingerprint(json.loads(reg.receipt)))
        self.assertEqual(denied.exception.reason, "regression_unavailable")

    def test_unknown_adapter_and_omitted_migration_declaration_denied(self):
        mat = material()
        for changed in (replace(mat, adapter_sources=(("adapters/operator.py", b"forged adapter"), *mat.adapter_sources[1:])),
                        replace(mat, migration=encoded({"strategy": "compatible", "affected_contracts": []}))):
            with self.assertRaises(FactoryDenied):
                prepared(factory_for(changed), changed)

    def test_mutable_host_inventory_or_runner_bags_are_not_authority(self):
        context = factory_for(material(supported_candidate())).context
        for altered in (replace(context, inventory=replace(context.inventory, pending=[])),
                        replace(context, runners=(replace(context.runners[0], runner_id=[]),)),
                        replace(context, regressions=(RegressionEvidence(b"[]"),))):
            with self.assertRaises(FactoryDenied):
                AdaptationFactory(altered)

    def test_owned_fixture_snapshots_and_diff_references_are_exact(self):
        folder = ROOT / "fixtures/development/adaptation"
        self.assertEqual(EnvironmentProfile.model_validate_json((folder / "baseline.json").read_bytes()), load_profile("flat-v1.2"))
        self.assertEqual(EnvironmentProfile.model_validate_json((folder / "candidate.json").read_bytes()), candidate_profile())
        self.assertEqual(EnvironmentProfile.model_validate_json((folder / "supported-control.json").read_bytes()), supported_candidate())
        index = json.loads((folder / "diff-index.json").read_bytes())
        before, after = json.loads((folder / "baseline.json").read_bytes()), json.loads((folder / "candidate.json").read_bytes())
        diffs = [{"path": entry["path"], "before": before[entry["path"]], "after": after[entry["path"]]} for entry in index["entries"]]
        self.assertEqual(index["diff_hash"], fingerprint({"diff": diffs}))
        self.assertEqual(index["canonical_diff_bytes"], len(encoded(diffs)))

    def test_registered_rejected_stale_scope_events_and_failed_regression_remain_distinct(self):
        factory, proposal, reg, approval, packet = reviewed()
        for changes, reason in (({"decision": "rejected"}, "approval_rejected"), ({"scope": ["review_profile"]}, "approval_scope_inadequate"),
                                ({"reviewed_at": "2026-10-01T10:00:00Z"}, "approval_stale")):
            changed = HumanReviewApproval.model_validate({**approval.model_dump(), **changes})
            event = HumanReviewEvent(changed.proof_reference, encoded(changed.model_dump(mode="json")), "human", "synthetic_rehearsal")
            updated = AdaptationFactory(replace(factory.context, reviews=(event,)))
            with self.assertRaises(ReleaseDenied) as denied:
                updated.release_profile(packet, changed, [])
            self.assertEqual(denied.exception.reason, reason)
        mat = factory.context.materials[0]
        failed = evidence(mat, proposal, result="failed", cases=json.loads(reg.receipt)["cases"])
        changed = packet.model_copy(update={"regression_hash": fingerprint(json.loads(failed.receipt))})
        updated = factory_for(mat, regressions=(failed,))
        with self.assertRaises(ReleaseDenied) as denied:
            updated.release_profile(changed, approval, [])
        self.assertEqual(denied.exception.reason, "failed_regression")

    def test_unregistered_source_baseline_agent_and_context_fail_closed(self):
        mat = material()
        factory = factory_for(mat)
        for args in [(encoded({"source_id": "forged"}), load_profile("flat-v1.2"), mat.agent),
                     (mat.source, load_profile("nested-v1.2"), mat.agent), (mat.source, load_profile("flat-v1.2"), encoded({"agent": "actual"}))]:
            with self.subTest(args=args[0][:20]), self.assertRaises(FactoryDenied):
                factory.prepare_proposal(*args)
        for method, args in [(prepare_proposal, (mat.source, load_profile("flat-v1.2"), mat.agent)),
                             (check_proposal, (None, "0" * 64)), (release_profile, (None, None, []))]:
            with self.assertRaises(FactoryDenied) as denied:
                method(*args)
            self.assertEqual(denied.exception.reason, "trusted_context_unavailable")

    def test_validator_has_same_loader_checks_in_memory(self):
        from proofkey.profiles import validate_profile
        profile = candidate_profile()
        self.assertEqual(validate_profile(profile), profile)
        for name in ("flat-v1", "nested-v1", "flat-v1.2", "flat-v1.3"):
            self.assertEqual(validate_profile(load_profile(name)), load_profile(name))
        with self.assertRaises(ValueError):
            validate_profile(profile.model_copy(update={"release_hash": "0" * 64}))

    def test_fabricated_failed_incomplete_and_wrong_runner_evidence_denied(self):
        mat = material(supported_candidate())
        proposal = prepared(factory_for(mat), mat)
        with self.assertRaises(FactoryDenied):
            factory_for(mat).check_proposal(proposal, "a" * 64)
        valid_cases = executed_cases(supported_candidate())
        for changes in ({"result": "failed"}, {"result": "unavailable"}, {"cases": valid_cases[:-1]},
                        {"candidate_hash": "0" * 64}, {"baseline_hash": "0" * 64}, {"test_hash": "0" * 64},
                        {"runner_id": "forged"}, {"provenance": "actual"}):
            reg = evidence(mat, proposal, **{"cases": valid_cases, **changes})
            with self.subTest(changes=changes), self.assertRaises(FactoryDenied):
                factory_for(mat, regressions=(reg,)).check_proposal(proposal, fingerprint(json.loads(reg.receipt)))

    def test_nested_candidate_and_proposal_tamper_is_rejected(self):
        factory, proposal, regression, approval, packet = reviewed()
        raw = proposal.model_dump(mode="json")
        raw["diff"][0]["after"]["ownership.epoch"] = "tampered"
        proposal = AdaptationProposal.model_validate(raw)
        with self.assertRaises(FactoryDenied):
            factory.check_proposal(proposal, packet.regression_hash)
        raw = packet.model_dump(mode="json")
        raw["proposed_profile"]["authorities"]["ownership.epoch"] = "forged"
        packet = ReviewPacket.model_validate(raw)
        with self.assertRaises(ReleaseDenied):
            factory.release_profile(packet, approval, [])

    def test_lead_candidate_semantics_graph_execute_but_new_dispatch_is_unavailable(self):
        candidate, baseline = candidate_profile(), load_profile("flat-v1.2")
        self.assertNotEqual(candidate.capabilities["enqueue_handoff"].acknowledgement, baseline.capabilities["enqueue_handoff"].acknowledgement)
        self.assertNotEqual(candidate.capabilities["enqueue_handoff"].readback, baseline.capabilities["enqueue_handoff"].readback)
        cases = executed_cases(candidate)
        self.assertEqual({case["case_id"] for case in cases}, {"business_rejection", "queue_only", "content_stored",
            "identity_digest_weaker", "readiness_false_missing", "readiness_current_true"})
        with tempfile.TemporaryDirectory() as directory:
            world = SimulatedWorld(Path(directory) / "provider.sqlite", ROOT / "fixtures/development/world.json",
                                   profile=candidate, clock=FakeClock())
            intent = make_intent(profile_version="v1.3", process_version=candidate.processes["reschedule_window"].version,
                                 expected_revisions=world.material_revisions())
            self.assertEqual(world.bundle().scheduling.reschedule(intent).status, "rejected")
            self.assertEqual(world.effect_count("reschedule"), 0)
        mat = material(candidate)
        proposal = prepared(factory_for(mat), mat)
        reg = evidence(mat, proposal, cases=cases)
        with self.assertRaises(FactoryDenied) as denied:
            factory_for(mat, regressions=(reg,)).check_proposal(proposal, fingerprint(json.loads(reg.receipt)))
        self.assertEqual(denied.exception.reason, "regression_unavailable")

    def test_permission_policy_and_authority_changes_rejected(self):
        for mutate in (lambda p: p["authorities"].update({"new.secret": "new"}),
                       lambda p: p["capabilities"]["send_status"]["permission_basis"].update(basis="broader grant"),
                       lambda p: p.update(policy_hash="0" * 64),
                       lambda p: p["authorities"].update({"ownership.epoch": "new"})):
            raw = candidate_profile().model_dump(mode="json")
            mutate(raw)
            raw["release_hash"] = fingerprint({k: v for k, v in raw.items() if k != "release_hash"})
            mat = material(EnvironmentProfile.model_validate(raw))
            with self.subTest(mutate=mutate), self.assertRaises(FactoryDenied):
                prepared(factory_for(mat), mat)

    def test_missing_approval_and_untrusted_inventory_have_distinct_denials(self):
        factory, _, _, approval, packet = reviewed()
        with self.assertRaises(ReleaseDenied) as denied:
            factory.release_profile(packet, None, [])
        self.assertEqual(denied.exception.reason, "missing_approval")
        factory, _, _, approval, packet = reviewed(inventory=False)
        with self.assertRaises(ReleaseDenied) as denied:
            factory.release_profile(packet, approval, [])
        self.assertEqual(denied.exception.reason, "pending_inventory_unavailable")

    def test_review_event_must_match_actor_scope_time_decision_and_content(self):
        factory, _, _, approval, packet = reviewed()
        for changes in ({"reviewer_id": "agent-consensus"}, {"mode": "actual"}, {"proof_reference": "forged"},
                        {"scope": []}, {"decision": "rejected"}, {"regression_hash": "0" * 64},
                        {"reviewed_at": DEADLINE}):
            changed = HumanReviewApproval.model_validate({**approval.model_dump(), **changes})
            with self.subTest(changes=changes), self.assertRaises(ReleaseDenied):
                factory.release_profile(packet, changed, [])
        altered = replace(factory.context, reviews=(replace(factory.context.reviews[0], actor_type="agent"),))
        with self.assertRaises(ReleaseDenied):
            AdaptationFactory(altered).release_profile(packet, approval, [])

    def test_attached_approval_and_process_bundle_mismatch_denied(self):
        factory, _, _, approval, packet = reviewed()
        for changed in (packet.model_copy(update={"proposed_processes": {}}),
                        packet.model_copy(update={"approval": approval.model_copy(update={"proof_reference": "other"})})):
            with self.assertRaises(ReleaseDenied):
                factory.release_profile(changed, approval, [])

    def test_no_pending_simulated_stage_has_canonical_manifest_and_no_activation(self):
        factory, _, _, approval, packet = reviewed()
        stage = factory.release_profile(packet, approval, [])
        self.assertEqual(stage.status, "staged_simulation")
        self.assertEqual(stage.receipt.approval.mode, "simulated")
        self.assertEqual(stage.receipt.release_hash, fingerprint(json.loads(stage.manifest)))
        self.assertEqual(stage.manifest, factory.release_profile(packet, approval, []).manifest)
        self.assertIn("atomic_activation_unavailable", stage.unmet_requirements)
        self.assertNotIn("current_profile", json.loads(stage.manifest))
        self.assertEqual(json.loads(stage.manifest)["migration_proof"], "unavailable")

    def test_omitted_or_changed_pending_inventory_cannot_stage(self):
        old = make_intent(profile_version="v1.2")
        factory, _, _, approval, packet = reviewed(pending=(old,))
        for pending in ([], [old], [make_intent(binding=make_binding(generation="foreign"))]):
            with self.subTest(pending=len(pending)), self.assertRaises(ReleaseDenied):
                factory.release_profile(packet, approval, pending)
        with self.assertRaises(ReleaseDenied) as denied:
            factory.release_profile(packet, approval, [old])
        self.assertEqual(denied.exception.reason, "incompatible_pending_contract")

    def test_denied_stage_preserves_disk_intent_stop_budget_wait_and_owner(self):
        from test_wait_storage import make_record
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "case.sqlite"
            store = CaseStore(path)
            origin = make_checkpoint(phase="completeness", next_gate="send_clarification", ownership_state="accepted",
                ownership_state_revision="owner-1", ownership_epoch=2)
            store.admit(make_binding(), make_request(), origin)
            record = make_record(origin)
            store.create_wait_atomic(record, NOW)
            old = make_intent(operation="send_clarification", stage="send", arguments={"recipient": "U1", "question_id": "Q1", "text": "synthetic"},
                postcondition={"recipient": "U1", "question_id": "Q1", "status": "sent"}, ownership_epoch=2,
                ownership_state_revision="owner-1")
            store.prepare(old)
            store.begin_dispatch(old, NOW)
            store.stop_waits_atomic(make_binding(), store.checkpoint("C1"))
            checkpoint, wait = store.checkpoint("C1"), store.load_wait_record("Q1")
            factory, _, _, approval, packet = reviewed(pending=(old,))
            with self.assertRaises(ReleaseDenied) as denied:
                factory.release_profile(packet, approval, [old])
            self.assertEqual(denied.exception.reason, "incompatible_pending_contract")
            store.close()
            reopened = CaseStore(path)
            try:
                self.assertEqual(reopened.intent(old.action_id).intent, old)
                self.assertEqual(reopened.checkpoint("C1"), checkpoint)
                self.assertTrue(reopened.checkpoint("C1").stop.requested)
                self.assertEqual(reopened.load_wait_record("Q1"), wait)
                self.assertEqual(reopened.checkpoint("C1").ownership_epoch, 2)
                self.assertEqual(reopened.checkpoint("C1").deadline, DEADLINE)
                self.assertGreater(reopened.checkpoint("C1").budget.tool_calls, 0)
            finally:
                reopened.close()


if __name__ == "__main__":
    unittest.main()
