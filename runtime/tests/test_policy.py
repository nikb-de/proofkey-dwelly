"""Scope grants come from designated sources, never caller arguments alone."""
import json
import unittest
from pathlib import Path

from proofkey.contracts import ActionProposal, AuthorityObservation, EnvironmentProfile, PhaseCheckpoint
from proofkey.identity import request_fingerprint
from proofkey.policy import GateDenied, PolicyGate
from support import NOW, make_auth, make_binding, make_checkpoint, make_request, load_test_profile

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/development/world.json"
STAGES = {"reschedule": "commit", "register_goods_refusal": "commit", "register_service_refusal": "commit",
          "create_return": "initiate", "send_clarification": "send", "send_status": "send",
          "enqueue_handoff": "enqueue", "transfer_owner": "request"}
ARGS = {
    "reschedule": {"slot": "S1"}, "register_goods_refusal": {"inventory": {"item-1": 1}},
    "register_service_refusal": {"scope": "service"}, "create_return": {"inventory": {"item-1": 1}, "destination": "D1"},
    "send_clarification": {"recipient": "U1", "text": "Which slot?", "question_id": "Q1"},
    "send_status": {"recipient": "U1", "text": "Saved"},
    "enqueue_handoff": {"packet_id": "P1", "packet_revision": "v1", "packet_hash": "packet-hash", "recipient": "OP1"},
    "transfer_owner": {"packet_id": "P1", "packet_revision": "v1", "packet_hash": "packet-hash",
                       "transfer_id": "T1", "target_owner": "OP2"},
}
PHASES = {"reschedule": "window_gate", "register_goods_refusal": "refusal_gate", "register_service_refusal": "refusal_gate",
          "create_return": "return_gate", "send_clarification": "completeness", "send_status": "intake",
          "enqueue_handoff": "intake", "transfer_owner": "wait_operator"}


def observations(**overrides):
    raw = json.loads(FIXTURE.read_text())["facts"]
    return [AuthorityObservation(authority=key.partition(".")[0], fact=key.partition(".")[2],
        object_id="O1", value=overrides.get(key, value["value"]), revision=value["revision"],
        provider_at=NOW, observed_at=NOW, evidence_ref=value["evidence_ref"]) for key, value in raw.items()]


def context(operation="reschedule", request=None, **facts):
    kind = {"register_goods_refusal": "goods_refusal", "create_return": "goods_refusal",
            "register_service_refusal": "service_refusal"}.get(operation, "reschedule_window")
    request = request or make_request(kind=kind, consent_mode="unknown" if "refusal" in kind else "window",
        **({"arguments": {"inventory": {"item-1": 1}}} if kind == "goods_refusal" else
           {"arguments": {"scope": "service"}} if kind == "service_refusal" else {}))
    source = {"customer.request_fingerprint": request_fingerprint(request), "customer.consent_mode": request.consent_mode}
    if operation == "create_return":
        source["goods.refusal"] = "verified"
    source.update(facts)
    checkpoint = make_checkpoint(binding=make_binding(request), phase=PHASES[operation], next_gate=PHASES[operation],
        profile_version="v1.1", ownership_state="accepted", ownership_state_revision="v1")
    proposal = ActionProposal(operation=operation, stage=STAGES[operation], arguments=ARGS[operation], evidence_refs=[])
    return request, proposal, observations(**source), checkpoint


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.profile = load_test_profile("flat-v1.1")
        self.gate = PolicyGate(self.profile)

    def test_binding_uses_designated_identity_and_historical_generation(self):
        binding = self.gate.bind_request(make_request(), make_auth(), observations())
        self.assertEqual(binding, make_binding())

    def test_body_identity_wrong_source_and_foreign_caller_cannot_bind(self):
        for request, auth, obs in ((make_request(object_id="foreign"), make_auth(), observations()),
                (make_request(request_revision="v2"), make_auth(), observations()),
                (make_request(), make_auth(caller_id="OP1"), observations()),
                (make_request(), make_auth(), observations(**{"case.authorization": "unknown"})),
                (make_request(), make_auth(), [])):
            with self.subTest(request=request, auth=auth):
                with self.assertRaises(GateDenied):
                    self.gate.bind_request(request, auth, obs)

    def test_eight_physical_operations_have_positive_scope_paths(self):
        for operation in STAGES:
            with self.subTest(operation=operation):
                self.assertTrue(self.gate.evaluate(*context(operation)).allowed)

    def test_request_kind_commitment_and_effect_arguments_cannot_expand_scope(self):
        request, proposal, obs, checkpoint = context()
        for changes in ({"slot": "S9"}, {"slot": "S1", "permission": True}):
            candidate = ActionProposal.model_validate({**proposal.model_dump(), "arguments": changes})
            self.assertFalse(self.gate.evaluate(request, candidate, obs, checkpoint).allowed)
        for facts in ({"customer.request_fingerprint": "0" * 64}, {"customer.consent_mode": "exact_slot"},
                      {"customer.consent": "unknown"}):
            self.assertFalse(self.gate.evaluate(*context(**facts)).allowed)
        request = make_request(kind="service_refusal", consent_mode="unknown")
        _, _, obs, checkpoint = context(request=request)
        self.assertFalse(self.gate.evaluate(request, proposal, obs, checkpoint).allowed)

    def test_window_dates_and_exact_selection_require_original_scope(self):
        for args in ({"window_start": "2026-10-08T11:00:00+00:00", "window_end": "2026-10-08T12:00:00+00:00"},
                     {"window_start": "2026-10-08T10:00:00", "window_end": "2026-10-08T12:00:00"},
                     {"window_start": "2026-10-08T12:00:00+00:00", "window_end": "2026-10-08T10:00:00+00:00"}):
            with self.subTest(args=args):
                self.assertFalse(self.gate.evaluate(*context(request=make_request(arguments=args))).allowed)
        exact = make_request(kind="reschedule_exact", consent_mode="exact_slot", arguments={"slot": "S1"})
        request, proposal, obs, checkpoint = context(request=exact)
        checkpoint = make_checkpoint(binding=checkpoint.binding, profile_version="v1.1", phase="exact_gate", next_gate="exact_gate",
                                     ownership_state="accepted", ownership_state_revision="v1")
        self.assertTrue(self.gate.evaluate(request, proposal, obs, checkpoint).allowed)
        proposal = ActionProposal.model_validate({**proposal.model_dump(), "arguments": {"slot": "S2"}})
        self.assertFalse(self.gate.evaluate(request, proposal, obs, checkpoint).allowed)

    def test_whole_goods_inventory_and_service_scope_are_separate(self):
        for operation in ("register_goods_refusal", "create_return"):
            request, proposal, obs, checkpoint = context(operation)
            for inventory in ({}, {"item-1": 2}, {"item-1": True}, {"foreign": 1}):
                candidate = ActionProposal.model_validate({**proposal.model_dump(),
                    "arguments": {**proposal.arguments, "inventory": inventory}})
                self.assertFalse(self.gate.evaluate(request, candidate, obs, checkpoint).allowed)
            self.assertFalse(self.gate.evaluate(*context(operation, **{"goods.quantity": 2})).allowed)
        self.assertFalse(self.gate.evaluate(*context("create_return", **{"goods.refusal": "none"})).allowed)

    def test_source_commitment_to_invalid_boolean_inventory_does_not_become_whole_goods_consent(self):
        request = make_request(kind="goods_refusal", consent_mode="unknown", arguments={"inventory": {"item-1": True}})
        self.assertFalse(self.gate.evaluate(*context("register_goods_refusal", request=request)).allowed)

    def test_confirmed_unknown_constraints_address_or_leftover_window_cannot_be_ignored(self):
        cases = [make_request(arguments={**make_request().arguments, "constraints": {"weekend_only": True}}),
                 make_request(arguments={**make_request().arguments, "address_change": "elsewhere"}),
                 make_request(kind="goods_refusal", consent_mode="unknown"),
                 make_request(kind="service_refusal", consent_mode="unknown"),
                 make_request(kind="service_refusal", consent_mode="unknown", arguments={"scope": "goods"})]
        for request in cases:
            operation = {"goods_refusal": "register_goods_refusal", "service_refusal": "register_service_refusal"}.get(request.kind, "reschedule")
            with self.subTest(request=request):
                self.assertFalse(self.gate.evaluate(*context(operation, request=request)).allowed)

    def test_unknown_business_consent_does_not_block_separately_permitted_assistance(self):
        for operation in ("send_clarification", "send_status", "enqueue_handoff", "transfer_owner"):
            request = make_request(consent_mode="unknown")
            args = context(operation, request=request, **{"customer.consent": "unknown", "customer.request_fingerprint": None})
            self.assertTrue(self.gate.evaluate(*args).allowed)
        self.assertFalse(self.gate.evaluate(*context("send_status", **{"messaging.permission": "unknown"})).allowed)

    def test_missing_material_unknown_guarantees_stop_and_ownership_fence(self):
        request, proposal, obs, checkpoint = context()
        missing = [o for o in obs if (o.authority, o.fact) != ("delivery", "risk")]
        self.assertFalse(self.gate.evaluate(request, proposal, missing, checkpoint).allowed)
        for changes in ({"stop": {"requested": True}}, {"ownership_state": "pending"},
                        {"ownership_state_revision": "v2"}, {"profile_version": "v1"}, {"phase": "complete"}):
            cp = PhaseCheckpoint.model_validate({**checkpoint.model_dump(), **changes})
            self.assertFalse(self.gate.evaluate(request, proposal, obs, cp).allowed)
        data = self.profile.model_dump()
        data["capabilities"]["reschedule"]["conditional_coverage"] = {"status": "unknown"}
        self.assertFalse(PolicyGate(EnvironmentProfile.model_validate(data)).evaluate(request, proposal, obs, checkpoint).allowed)
        legacy = PolicyGate(load_test_profile("flat-v1"))
        self.assertFalse(legacy.evaluate(request, proposal, obs, make_checkpoint(phase="window_gate")).allowed)

    def test_arbitrary_proposal_stage_unqualified_or_duplicate_sources_deny(self):
        request, proposal, obs, checkpoint = context()
        wrong = ActionProposal.model_validate({**proposal.model_dump(), "stage": "receive"})
        self.assertFalse(self.gate.evaluate(request, wrong, obs, checkpoint).allowed)
        self.assertFalse(self.gate.evaluate(request, proposal, [*obs, obs[0]], checkpoint).allowed)
        foreign = AuthorityObservation.model_validate({**obs[0].model_dump(), "object_id": "foreign"})
        self.assertFalse(self.gate.evaluate(request, proposal, [foreign, *obs[1:]], checkpoint).allowed)
