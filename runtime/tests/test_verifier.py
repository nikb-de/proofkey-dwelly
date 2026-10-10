"""Independent effect identity and operation-specific completion evidence."""
import unittest

from proofkey.contracts import AuthorityObservation, AuthorityReadback
from proofkey.verifier import verify
from support import NOW, make_intent


def readback(intent, values, stage="committed", **changes):
    observations = [AuthorityObservation(authority=key.split(".", 1)[0], fact=key.split(".", 1)[1],
        object_id="O1", value=value, revision="v1", provider_at=NOW, observed_at=NOW,
        evidence_ref="synthetic:" + key) for key, value in values.items()]
    data = dict(operation=intent.operation, object_id="O1", observations=observations,
        provider_request_id="provider:original", action_id=intent.action_id,
        fingerprint=intent.argument_fingerprint, stage=stage, as_of=NOW,
        evidence_refs=["synthetic:original"])
    return AuthorityReadback.model_validate({**data, **changes})


class VerifierTests(unittest.TestCase):
    def test_matched_schedule_requires_authoritative_original_and_slot(self):
        intent = make_intent()
        result = verify(intent, readback(intent, {"scheduling.slot": "S1"}))
        self.assertEqual(result.status, "verified")
        self.assertEqual(result.postcondition, {"slot": "S1"})
        self.assertEqual(result.evidence_refs, ["synthetic:original"])

    def test_missing_identity_or_evidence_never_promotes_an_acknowledgement(self):
        intent = make_intent()
        for changes in ({"action_id": None}, {"fingerprint": None},
                        {"evidence_refs": []}, {"observations": []}, {"stage": "observed"}):
            with self.subTest(changes=changes):
                self.assertNotEqual(verify(intent, readback(intent, {"scheduling.slot": "S1"}, **changes)).status,
                                    "verified")

    def test_optional_opaque_provider_id_does_not_discard_complete_original_evidence(self):
        intent = make_intent()
        reply = readback(intent, {"scheduling.slot": "S1"}, provider_request_id=None)
        self.assertEqual(verify(intent, reply).status, "verified")

    def test_wrong_identity_or_postcondition_conflicts_without_foreign_disclosure(self):
        intent = make_intent()
        for changes in ({"action_id": "foreign"}, {"fingerprint": "0" * 64},
                        {"object_id": "foreign"}, {"operation": "create_return"}):
            with self.subTest(changes=changes):
                result = verify(intent, readback(intent, {"scheduling.slot": "S1"}, **changes))
                self.assertEqual(result.status, "conflict")
                self.assertNotEqual(result.object_id, "foreign")
        self.assertEqual(verify(intent, readback(intent, {"scheduling.slot": "S2"})).status, "conflict")

    def test_return_initiation_does_not_claim_physical_receipt(self):
        intent = make_intent(operation="create_return", stage="initiate",
            arguments={"inventory": {"item-1": 1}, "destination": "D1"},
            postcondition={"returns.status": "initiated", "inventory": {"item-1": 1}, "quantity": 1, "destination": "D1"})
        values = {"returns.status": "initiated", "goods.inventory": {"item-1": 1},
                  "goods.quantity": 1, "returns.destination": "D1"}
        self.assertEqual(verify(intent, readback(intent, values, stage="initiated")).status, "verified")
        receipt = make_intent(operation="create_return", stage="initiate", arguments=intent.arguments,
            postcondition={**intent.postcondition, "returns.status": "received"})
        self.assertEqual(verify(receipt, readback(receipt, values, stage="initiated")).status, "pending")

    def test_queued_handoff_and_pending_transfer_remain_distinct(self):
        handoff = make_intent(operation="enqueue_handoff", stage="enqueue",
            arguments={"packet_id": "P1", "packet_revision": "v1", "packet_hash": "packet-hash", "recipient": "OP1"},
            postcondition={"operator.handoff_disposition": "pending", "packet_id": "P1",
                           "packet_revision": "v1", "packet_hash": "packet-hash"})
        values = {"operator.handoff_disposition": "pending", "operator.packet_id": "P1",
                  "operator.packet_revision": "v1", "operator.packet_hash": "packet-hash"}
        self.assertEqual(verify(handoff, readback(handoff, values, stage="queued")).status, "verified")
        transfer = make_intent(operation="transfer_owner", stage="request",
            arguments={"transfer_id": "T1", "packet_id": "P1", "packet_revision": "v1",
                       "packet_hash": "packet-hash", "target_owner": "OP2"},
            postcondition={"ownership.state": "accepted", "target_owner": "OP2", "transfer_id": "T1",
                           "packet_id": "P1", "packet_revision": "v1", "epoch": 1}, ownership_epoch=0)
        values = {"ownership.state": "pending", "ownership.owner": "U1", "ownership.epoch": 0,
                  "ownership.state_revision": "v2", "operator.transfer_id": "T1",
                  "operator.packet_id": "P1", "operator.packet_revision": "v1"}
        self.assertEqual(verify(transfer, readback(transfer, values, stage="pending")).status, "pending")

    def test_absence_is_unknown_and_terminal_proof_needs_full_original_identity(self):
        intent = make_intent()
        absent = readback(intent, {}, stage="unknown", action_id=None, fingerprint=None, provider_request_id=None)
        self.assertEqual(verify(intent, absent).status, "outcome_unknown")
        terminal = readback(intent, {}, stage="terminally_rejected",
            nonexecution={"status": "proven", "basis": "fenced", "evidence_ref": "synthetic:fence"},
            evidence_refs=["synthetic:fence"])
        self.assertEqual(verify(intent, terminal).status, "rejected")
        self.assertEqual(verify(intent, AuthorityReadback.model_validate({**terminal.model_dump(),
                         "action_id": None})).status, "outcome_unknown")

    def test_duplicate_conflicting_observations_and_unknown_postcondition_fail_closed(self):
        intent = make_intent()
        reply = readback(intent, {"scheduling.slot": "S1"})
        contradictory = AuthorityObservation.model_validate({**reply.observations[0].model_dump(), "value": "S2"})
        reply = AuthorityReadback.model_validate({**reply.model_dump(), "observations": [*reply.observations, contradictory]})
        self.assertEqual(verify(intent, reply).status, "conflict")
        unknown = make_intent(postcondition={"delivery_complete": True})
        self.assertNotEqual(verify(unknown, readback(unknown, {"scheduling.slot": "S1"})).status, "verified")

    def test_weak_postcondition_subset_cannot_hide_missing_whole_order_or_recipient(self):
        for operation, args, post, values, stage in (
            ("register_goods_refusal", {"inventory": {"item-1": 1}}, {"goods.refusal": "verified"},
             {"goods.refusal": "verified", "goods.inventory": {"item-1": 1}, "goods.quantity": 1}, "committed"),
            ("send_status", {"recipient": "U1", "text": "Saved"}, {"messaging.status": "sent"},
             {"messaging.status": "sent", "messaging.recipient": "U1"}, "sent")):
            intent = make_intent(operation=operation, stage="send" if operation == "send_status" else "commit",
                                 arguments=args, postcondition=post)
            self.assertEqual(verify(intent, readback(intent, values, stage=stage)).status, "conflict")

    def test_claimed_delivered_stage_cannot_verify_a_merely_sent_message(self):
        intent = make_intent(operation="send_status", stage="send", arguments={"recipient": "U1", "text": "Saved"},
                             postcondition={"messaging.status": "sent", "recipient": "U1"})
        reply = readback(intent, {"messaging.status": "sent", "messaging.recipient": "U1"}, stage="delivered")
        self.assertEqual(verify(intent, reply).status, "conflict")

    def test_pending_progress_must_not_hide_wrong_inventory_or_quantity(self):
        intent = make_intent(operation="create_return", stage="initiate",
            arguments={"inventory": {"item-1": 1}, "destination": "D1"},
            postcondition={"returns.status": "received", "inventory": {"item-1": 1}, "quantity": 1, "destination": "D1"})
        values = {"returns.status": "initiated", "goods.inventory": {"item-1": 2}, "goods.quantity": 2, "returns.destination": "D1"}
        self.assertEqual(verify(intent, readback(intent, values, stage="initiated")).status, "conflict")
