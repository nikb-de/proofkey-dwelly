"""Ownership consumer boundaries over actual synthetic source/journal entries."""
import tempfile
import unittest
from proofkey.contracts import AuthorityReadback, ReadTarget, ReadRequest
from proofkey.policy import GateDenied
from ownership_support import Harness, make_binding
from ownership_support import ROOT, FakeClock, DEADLINE, make_auth
from pathlib import Path


class OwnershipGatewayTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.h = Harness(self.folder.name)
        self.addCleanup(self.h.store.close)

    def test_old_read_malformed_registered_packet_retains_reservation(self):
        actual = self.h.bundle.operator.read_owner
        def malformed(request):
            reply = actual(request)
            data = reply.model_dump()
            data["observations"][0]["value"]["packet_hash"] = "not-a-digest"
            return AuthorityReadback.model_validate(data)
        self.h.bundle.operator.read_owner = malformed
        with self.assertRaises(GateDenied):
            self.h.gateway._read(make_binding(), ReadTarget(kind="authority_facts", authority="operator",
                facts=["ownership_packet"]), "operator", "read_owner", purpose="transfer")
        budget = self.h.store.checkpoint("C1").budget
        self.assertEqual(budget.tool_calls, 1)
        self.assertEqual(budget.active_seconds, 10.0)
        self.assertEqual(self.h.store.intents("C1"), ())

    def test_source_read_has_actual_settled_entries_and_different_actor(self):
        source = self.h.gateway.read_ownership_sources(make_binding(), self.h.auth, "decision")
        self.assertEqual(source.packet.accepted_owner, "OP1")
        self.assertNotEqual(source.grant.actor_id, source.binding.principal_id)
        self.assertEqual(len(source.read_entry_ids), 5)
        self.assertEqual(source.checkpoint, self.h.store.checkpoint("C1"))
        self.assertEqual(source.checkpoint.budget.tool_calls, 5)
        for identifier in source.read_entry_ids:
            self.assertEqual(self.h.store.entry(identifier).state, "settled")

    def test_registered_verifier_uses_typed_pending_not_flat_aliases(self):
        from proofkey.verifier import verify
        effect = self.h.effect()
        self.assertEqual(self.h.bundle.operator.transfer_owner(effect, auth=self.h.auth).status, "acknowledged")
        read = self.h.bundle.operator.read_owner(ReadRequest(case_id="C1", object_id="O1",
            caller_id=self.h.auth.caller_id, proof_reference=self.h.auth.proof_reference,
            purpose="reconcile", deadline=effect.deadline, target=ReadTarget(kind="original_effect",
            operation="transfer_owner", generation="G1", action_id=effect.action_id,
            provider_key=effect.provider_key, fingerprint=effect.argument_fingerprint)))
        result = verify(effect, read, profile=self.h.profile)
        self.assertEqual(result.status, "pending")

    def test_registered_absent_original_evidence_is_unknown_not_conflict(self):
        from proofkey.verifier import verify
        from ownership_support import NOW
        read = AuthorityReadback(operation="read_owner", object_id="O1", observations=[],
            stage="unknown", as_of=NOW, evidence_refs=[])
        self.assertEqual(verify(self.h.effect(), read, profile=self.h.profile).status, "outcome_unknown")

    def test_typed_original_receipt_cannot_substitute_evidence_or_revision_vector(self):
        from proofkey.verifier import verify
        effect = self.h.effect()
        self.h.bundle.operator.transfer_owner(effect, auth=self.h.auth)
        read = self.h.bundle.operator.read_owner(ReadRequest(case_id="C1", object_id="O1",
            caller_id=self.h.auth.caller_id, proof_reference=self.h.auth.proof_reference,
            purpose="reconcile", deadline=effect.deadline, target=ReadTarget(kind="original_effect",
            operation=effect.operation, generation="G1", action_id=effect.action_id,
            provider_key=effect.provider_key, fingerprint=effect.argument_fingerprint)))
        self.assertEqual(verify(effect, read, profile=self.h.profile).status, "pending")
        for mutation in ("receipt_evidence", "revision_vector"):
            with self.subTest(mutation=mutation):
                data = read.model_dump()
                if mutation == "receipt_evidence":
                    next(o for o in data["observations"] if o["fact"] == "transfer_receipt")["value"]["evidence_ref"] = "foreign-evidence"
                else:
                    next(o for o in data["observations"] if o["fact"] == "transfer_receipt")["value"]["expected_revisions"]["revisions"]["customer.consent"] = "foreign-revision"
                self.assertEqual(verify(effect, AuthorityReadback.model_validate(data), profile=self.h.profile).status,
                    "conflict")

    def test_transfer_source_is_six_actual_settled_reads(self):
        source = self.h.gateway.read_ownership_sources(make_binding(), self.h.auth, "transfer")
        self.assertEqual(len(source.read_entry_ids), 6)
        self.assertEqual(source.checkpoint.budget.tool_calls, 6)
        self.assertEqual(source.checkpoint.budget.active_seconds, 0)
        self.assertEqual(source.packet.packet_hash, "b"*64)

    def test_forwarded_malformed_metadata_never_refunds_operator_read(self):
        actual = self.h.bundle.operator.read_owner
        def malformed(request):
            reply = actual(request)
            if request.target.authority == "operator":
                data = reply.model_dump()
                for obs in data["observations"]:
                    if obs["fact"] == "packet_hash":
                        obs["value"] = "not-a-digest"
                return AuthorityReadback.model_validate(data)
            return reply
        self.h.bundle.operator.read_owner = malformed
        with self.assertRaises(GateDenied):
            self.h.gateway.read_ownership_sources(make_binding(), self.h.auth, "transfer")
        self.assertEqual(self.h.store.checkpoint("C1").budget.active_seconds, 10)

    def test_registered_operator_batch_does_not_widen_legacy_or_proof(self):
        from proofkey.adapters.world import SimulatedWorld
        from proofkey.profiles import load_profile
        target = ReadTarget(kind="authority_facts", authority="operator",
            facts=["packet_hash", "packet_revision", "ownership_packet", "ownership_grant"])
        request = ReadRequest(case_id="C1", object_id="O1", caller_id="OP1",
            proof_reference="synthetic-operator-proof", purpose="transfer", deadline=DEADLINE, target=target)
        self.assertEqual(self.h.bundle.operator.read_owner(request).stage, "observed")
        self.assertEqual(self.h.bundle.operator.read_owner(request.model_copy(update={"proof_reference":"wrong"})).stage,
            "scope_rejected")
        self.assertEqual(self.h.bundle.operator.read_owner(request.model_copy(update={"object_id":"foreign"})).stage,
            "scope_rejected")
        legacy = SimulatedWorld(Path(self.folder.name)/"legacy.sqlite", ROOT/"fixtures/development/packet-world-v1.json",
            profile=load_profile("flat-v1.3"), clock=FakeClock())
        self.assertEqual(legacy.bundle().operator.read_owner(request).stage, "scope_rejected")

    def test_wrong_proof_or_reader_is_not_action_grant(self):
        for auth in (make_auth(caller_id="OP1", proof_reference="wrong"),
                     make_auth(caller_id="U1"), make_auth(caller_id="OP2", proof_reference="synthetic-target-proof")):
            with self.subTest(actor=auth.caller_id, proof=auth.proof_reference), self.assertRaises(GateDenied):
                self.h.gateway.read_ownership_sources(make_binding(), auth, "decision")
        self.assertEqual(self.h.store.checkpoint("C1").budget.effects, 0)

    def test_ordinary_bind_still_rejects_actual_operator_not_customer(self):
        from ownership_support import make_request
        observations = self.h.gateway.read_ownership_sources(make_binding(), self.h.auth, "decision").observations
        with self.assertRaises(GateDenied):
            self.h.gateway.gate.bind_request(make_request(), self.h.auth, observations)

    def test_generic_gateway_never_dispatches_registered_transfer(self):
        effect = self.h.effect()
        self.assertEqual(self.h.gateway.execute(effect).status, "rejected")
        self.assertEqual(self.h.store.checkpoint("C1").budget.tool_calls, 0)
        self.assertEqual(self.h.world.effect_count("transfer_owner"), 0)
