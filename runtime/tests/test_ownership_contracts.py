"""Closed synthetic ownership data; fixtures are not source authorization."""
from datetime import timedelta
import unittest

from proofkey.identity import stable_action_id
from support import NOW, DEADLINE, make_binding


class OwnershipContractTests(unittest.TestCase):
    def test_host_registry_rejects_changed_process_release_or_bundle(self):
        from test_ownership_storage import synthetic_registry
        from proofkey.ownership_contracts import OwnershipProcessRegistryV1
        from proofkey.identity import fingerprint
        registry = synthetic_registry()
        data = registry.model_dump(mode="json")
        with self.assertRaises(ValueError):
            OwnershipProcessRegistryV1.model_validate({**data, "process_hash": "0" * 64})
        kind = next(iter(data["processes"]))
        data["processes"][kind]["release_hash"] = "0" * 64
        data["process_hash"] = fingerprint(data["processes"])
        with self.assertRaises(ValueError):
            OwnershipProcessRegistryV1.model_validate(data)

    def test_source_grant_and_packet_require_strict_boolean_simulation(self):
        from proofkey.ownership_contracts import OwnershipPacketV1, OwnershipGrantV1
        for cls, data in ((OwnershipPacketV1, packet_data()), (OwnershipGrantV1, grant_data())):
            with self.subTest(model=cls.__name__):
                with self.assertRaises(ValueError):
                    cls(**{**data, "simulated": 1})

    def test_original_identity_rejects_a_different_transfer_key(self):
        from proofkey.ownership_contracts import OriginalTransferIdentityV1
        binding = make_binding()
        key = stable_action_id(binding, "transfer_owner", "request")
        original = dict(binding=binding, transfer_id=key, action_id=key,
                        provider_key=key, argument_fingerprint="1" * 64)
        self.assertEqual(OriginalTransferIdentityV1(**original).provider_key, key)
        for field in ("transfer_id", "action_id", "provider_key"):
            with self.assertRaises(ValueError):
                OriginalTransferIdentityV1(**{**original, field: "replacement"})

    def test_packet_rejects_duplicate_keys_and_unbounded_identifiers(self):
        from proofkey.ownership_contracts import OwnershipPacketV1
        data = packet_data()
        value = OwnershipPacketV1(**data)
        with self.assertRaises(ValueError):
            OwnershipPacketV1.model_validate_json(value.model_dump_json()[:-1] + ',"simulated":true}')
        with self.assertRaises(ValueError):
            OwnershipPacketV1(**{**data, "packet_id": "x" * 4097})
        with self.assertRaises(ValueError):
            OwnershipPacketV1(**{**data, "accepted_at": NOW.replace(tzinfo=None)})
        with self.assertRaises(ValueError):
            OwnershipPacketV1(**{**data, "simulated": False})

    def test_grant_requires_human_role_and_closed_sorted_unique_scope(self):
        from proofkey.ownership_contracts import OwnershipGrantV1
        data = grant_data()
        grant = OwnershipGrantV1(**{**data, "target_owners": ["OP3", "OP2"]})
        self.assertEqual(grant.target_owners, ["OP2", "OP3"])
        for patch in ({"actor_type": "machine"}, {"target_owners": ["OP2", "OP2"]},
                      {"expires_at": data["issued_at"]}, {"decision_operations": ["refund"]},
                      {"target_owners": [str(i) for i in range(17)]}):
            with self.assertRaises(ValueError):
                OwnershipGrantV1(**{**data, **patch})

    def test_acceptance_requires_next_epoch_and_new_revision(self):
        from proofkey.ownership_contracts import TransferAcceptedV1
        binding = make_binding()
        key = stable_action_id(binding, "transfer_owner", "request")
        data = dict(original=dict(binding=binding, transfer_id=key, action_id=key, provider_key=key,
                                  argument_fingerprint="1" * 64), packet=packet_data(), target_owner="OP2",
                    expected_revisions={"revisions": {"operator.packet_hash": "r1"}},
                    pending_state_revision=None, accepted_state_revision="owner-r2", accepted_epoch=2,
                    accepted_at=NOW, acceptance_evidence="accepted-2", target_instruction_hash="7" * 64,
                    simulated=True)
        self.assertEqual(TransferAcceptedV1(**data).accepted_epoch, 2)
        for patch in ({"accepted_epoch": 1}, {"accepted_state_revision": "owner-r1"},
                      {"target_owner": "OP1"}):
            with self.assertRaises(ValueError):
                TransferAcceptedV1(**{**data, **patch})

    def test_approve_requires_exact_closed_effect_scope(self):
        from proofkey.ownership_contracts import OperatorDecisionSubmissionV1
        from proofkey.contracts import OperatorDecision
        binding = make_binding()
        decision = OperatorDecision(decision_id="d1", packet_id="P1", packet_hash="2" * 64,
            packet_revision="packet-r1", binding=binding, owner="OP1", epoch=1,
            state_revision="owner-r1", actor_id="OP1", proof_reference="synthetic", decision="approve",
            scope=["reschedule"], expires_at=DEADLINE, replay_id="replay-d1", simulated=True)
        with self.assertRaises(ValueError):
            OperatorDecisionSubmissionV1(decision=decision, content_hash="3" * 64, effect_scope=None)
        scope = dict(operation="reschedule", stage="commit", action_id=stable_action_id(binding, "reschedule", "commit"),
                     argument_fingerprint="4" * 64)
        self.assertEqual(OperatorDecisionSubmissionV1(decision=decision, content_hash="3" * 64,
                         effect_scope=scope).effect_scope.operation, "reschedule")
        with self.assertRaises(ValueError):
            OperatorDecisionSubmissionV1(decision=decision, content_hash="3" * 64,
                effect_scope={**scope, "stage": "initiate", "action_id": stable_action_id(binding, "reschedule", "initiate")})


def packet_data():
    return dict(binding=make_binding(), packet_id="P1", packet_hash="2" * 64,
        packet_revision="packet-r1", content_hash="3" * 64, accepted_owner="OP1", accepted_epoch=1,
        accepted_state_revision="owner-r1", acceptance_evidence="accepted-1", accepted_at=NOW,
        simulated=True)


def grant_data():
    return dict(grant_id="grant-1", binding=make_binding(), actor_id="OP1", actor_type="human",
        packet_id="P1", packet_hash="2" * 64, packet_revision="packet-r1", content_hash="3" * 64,
        owner="OP1", epoch=1, state_revision="owner-r1", may_initiate_transfer=True,
        target_owners=["OP2"], decision_operations=["reschedule"], may_record_nonaction_decision=True,
        dispositions=["refund_review"], issued_at=NOW - timedelta(minutes=1), expires_at=DEADLINE,
        evidence_ref="synthetic-grant", fixture_hash="6" * 64, simulated=True)
