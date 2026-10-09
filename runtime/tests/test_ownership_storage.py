"""Real local journal checks with explicitly synthetic unit source data.

These records exercise storage integrity only, never producer authentication.
"""
from pathlib import Path
import tempfile
import unittest
from uuid import uuid4
import os
import subprocess
import sys
import threading
import sqlite3

from proofkey.contracts import TransferIntent, AuthorityObservation, RevisionVector
from proofkey.identity import fingerprint, stable_action_id
from proofkey.journal import CaseStore, JournalFailure
from support import DEADLINE, NOW, make_binding, make_checkpoint, make_intent, make_request
from test_ownership_contracts import packet_data, grant_data


def synthetic_registry():
    from proofkey.profiles import load_profile
    from proofkey.ownership_contracts import OwnershipProcessRegistryV1
    parent = load_profile("flat-v1.3")
    return OwnershipProcessRegistryV1(profile_id="synthetic-storage-unit", profile_version="v1.4",
        profile_hash="8" * 64, process_hash=parent.process_hash, policy_hash=parent.policy_hash,
        processes=parent.processes)


def synthetic_source(store, *, current=False, packet=None, ownership=None, purpose="transfer"):
    from proofkey.ownership_contracts import (OwnershipSourceReadV1, OwnershipCurrentReadV1,
        OwnershipPacketV1, OwnershipGrantV1, TRANSFER_FIELDS_V1)
    registry = synthetic_registry()
    packet = packet or OwnershipPacketV1(**packet_data())
    grant = OwnershipGrantV1(**grant_data())
    fields = TRANSFER_FIELDS_V1 if not current and purpose == "transfer" else frozenset({"case.binding", "case.request_revision", "case.authorization",
        "case.generation", "customer.consent_revision", "policy.version", "ownership.owner", "ownership.state",
        "ownership.state_revision", "ownership.epoch", "operator.ownership_packet"})
    if not current:
        fields |= {"operator.ownership_grant"}
    values = {field: "synthetic-unit-value" for field in fields}
    values.update({"case.binding": {"case_id": "C1", "object_id": "O1", "principal_id": "U1", "request_id": "REQ1"},
        "case.request_revision": "v1", "case.authorization": "verified", "case.generation": "current",
        "customer.consent_revision": "v1", "policy.version": "v1", "ownership.owner": "OP1",
        "ownership.state": "accepted", "ownership.state_revision": "owner-r1", "ownership.epoch": 1,
        "operator.packet_hash": packet.packet_hash, "operator.packet_revision": packet.packet_revision,
        "operator.ownership_packet": packet.model_dump(mode="json"), "operator.ownership_grant": grant.model_dump(mode="json")})
    if ownership:
        values.update({"ownership.owner": ownership.owner, "ownership.state": ownership.state,
                       "ownership.state_revision": ownership.state_revision, "ownership.epoch": ownership.epoch})
    ids = []
    for authority in sorted({field.partition(".")[0] for field in fields}):
        lease = store.begin_read("C1", NOW)
        store.finish_entry(lease.entry_id, 0.0)
        ids.append(lease.entry_id)
    observations = [AuthorityObservation(authority=field.partition(".")[0], fact=field.partition(".")[2],
        object_id="O1", value=values[field], revision="r1", provider_at=NOW, observed_at=NOW,
        evidence_ref="synthetic-unit:" + field) for field in sorted(fields)]
    common = dict(binding=make_binding(), checkpoint=store.checkpoint("C1"), packet=packet,
        observations=observations, read_entry_ids=ids, as_of=NOW, profile_hash=registry.profile_hash,
        process_hash=registry.process_hash, policy_hash=registry.policy_hash)
    return OwnershipCurrentReadV1(**common, ownership=ownership) if current else OwnershipSourceReadV1(**common, grant=grant)


def synthetic_transfer(source):
    from proofkey.ownership_contracts import TransferArgumentsV1, TransferPostconditionV1, OriginalTransferIdentityV1
    key = stable_action_id(source.binding, "transfer_owner", "request")
    intent = TransferIntent(transfer_id=key, binding=source.binding, case_id="C1", packet_id="P1", packet_hash="2" * 64,
        packet_revision="packet-r1", expected_owner="OP1", expected_state_revision="owner-r1", expected_epoch=1,
        target_owner="OP2", expires_at=DEADLINE)
    arguments = TransferArgumentsV1(intent=intent, content_hash="3" * 64, grant_id="grant-1", grant_revision="r1").model_dump(mode="json")
    original = OriginalTransferIdentityV1(binding=source.binding, transfer_id=key, action_id=key, provider_key=key,
                                         argument_fingerprint=fingerprint(arguments))
    post = TransferPostconditionV1(original=original, packet=source.packet, target_owner="OP2", accepted_epoch=2)
    effect = make_intent(operation="transfer_owner", stage="request", arguments=arguments,
        postcondition=post.model_dump(mode="json"), profile_version="v1.4", process_version=source.checkpoint.process_version,
        expected_revisions=RevisionVector(revisions={item.authority + "." + item.fact: item.revision for item in source.observations}),
        ownership_state_revision="owner-r1", ownership_epoch=1)
    return intent, effect


def synthetic_decision(source, decision_id="decision-1", replay_id="replay-1"):
    from proofkey.ownership_contracts import OperatorDecisionSubmissionV1
    from proofkey.contracts import OperatorDecision
    effect = make_intent(profile_version="v1.4", process_version=source.checkpoint.process_version,
        decision_id=decision_id, ownership_state_revision="owner-r1", ownership_epoch=1,
        expected_revisions=RevisionVector(revisions={item.authority + "." + item.fact: item.revision for item in source.observations}))
    decision = OperatorDecision(decision_id=decision_id, packet_id="P1", packet_hash="2" * 64,
        packet_revision="packet-r1", binding=make_binding(), owner="OP1", epoch=1, state_revision="owner-r1",
        actor_id="OP1", proof_reference="synthetic-proof", decision="approve", scope=["reschedule"],
        expires_at=DEADLINE, replay_id=replay_id, simulated=True)
    submission = OperatorDecisionSubmissionV1(decision=decision, content_hash="3" * 64,
        effect_scope=dict(operation="reschedule", stage="commit", action_id=effect.action_id,
                          argument_fingerprint=effect.argument_fingerprint))
    return submission, effect


def synthetic_acceptance(store, source, intent, effect, pending_revision=None):
    from proofkey.ownership_contracts import TransferAcceptedV1
    from proofkey.contracts import HumanOwnership
    receipt = TransferAcceptedV1(original=effect.postcondition["original"], packet=source.packet,
        target_owner="OP2", expected_revisions=effect.expected_revisions, pending_state_revision=pending_revision,
        accepted_state_revision="owner-r2", accepted_epoch=2, accepted_at=NOW,
        acceptance_evidence="synthetic-accepted-2", target_instruction_hash="7" * 64, simulated=True)
    packet = source.packet.model_copy(update={"accepted_owner": "OP2", "accepted_epoch": 2,
        "accepted_state_revision": "owner-r2", "acceptance_evidence": "synthetic-accepted-2", "accepted_at": NOW})
    owner = HumanOwnership(binding=make_binding(), owner="OP2", epoch=2, state_revision="owner-r2",
        packet_id="P1", packet_hash="2" * 64, packet_revision="packet-r1", state="accepted",
        acceptance_evidence="synthetic-accepted-2", transfer_id=intent.transfer_id)
    return receipt, synthetic_source(store, current=True, packet=packet, ownership=owner)


def hard_exit_driver(path, boundary):
    """Real process exit on both sides of SQLite commits; no source provider."""
    armed = False
    def before_commit():
        if armed:
            os._exit(71)
    store = CaseStore(path, before_commit=before_commit, ownership_processes=synthetic_registry())
    decision_boundary = boundary.startswith("consume")
    source = synthetic_source(store, purpose="decision" if decision_boundary else "transfer")
    if decision_boundary:
        submission, effect = synthetic_decision(source)
        store.record_decision_atomic(submission, source, NOW)
        store.prepare(effect)
        armed = boundary.endswith("before_commit")
        store.begin_dispatch(effect, NOW)
        os._exit(71)
    intent, effect = synthetic_transfer(source)
    if boundary == "pending_before_commit":
        armed = True
    store.register_transfer_atomic(intent, effect, source, NOW)
    if boundary == "pending_after_commit":
        os._exit(71)
    if boundary == "entry_before_commit":
        armed = True
    store.begin_registered_transfer(intent.transfer_id, store.checkpoint("C1"), NOW)
    if boundary == "entry_after_commit":
        os._exit(71)
    receipt, current = synthetic_acceptance(store, source, intent, effect)
    armed = boundary == "terminal_before_commit"
    store.apply_transfer_receipt_atomic(intent.transfer_id, receipt, current, current.checkpoint, NOW)
    os._exit(71)


class OwnershipStorageTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "journal.sqlite"
        self.store = CaseStore(self.path)
        self.addCleanup(lambda: self.store.close())
        self.store.admit(make_binding(), make_request(), make_checkpoint())

    def test_unknown_supplied_decision_id_denies_and_consumes_no_entry(self):
        effect = make_intent(decision_id="unrecorded", ownership_state_revision="owner-r1", ownership_epoch=1)
        self.store.save_checkpoint(make_checkpoint(ownership_state="accepted", ownership_state_revision="owner-r1", ownership_epoch=1))
        self.store.prepare(effect)
        with self.assertRaises(JournalFailure):
            self.store.begin_dispatch(effect, NOW)
        self.assertEqual(self.store.intent(effect.action_id).state, "prepared")
        self.assertEqual(self.store.checkpoint("C1").budget.effects, 0)

    def test_legacy_terminal_transfer_cannot_roll_back(self):
        intent = TransferIntent(transfer_id="legacy", binding=make_binding(), case_id="C1", packet_id="P1",
            packet_hash="2" * 64, packet_revision="p1", expected_owner="OP1", expected_state_revision="o1",
            expected_epoch=1, target_owner="OP2", expires_at=DEADLINE)
        self.store.save_transfer(intent, "accepted")
        with self.assertRaises(JournalFailure):
            self.store.save_transfer(intent, "prepared")
        self.assertEqual(self.store.transfer("legacy").state, "accepted")
        with self.assertRaises(JournalFailure):
            self.store.transfer_record("legacy")

    def configure_synthetic(self):
        self.store.close()
        self.store = CaseStore(self.path, ownership_processes=synthetic_registry())
        # Fresh admitted generation, host synthetic unit configuration only.

    def test_registration_atomically_fences_unchanged_epoch_and_preserves_budget(self):
        self.assertTrue(hasattr(self.store, "register_transfer_atomic"), "Missing atomic registered transfer storage")
        self.store.close()
        self.path = Path(self.folder.name) / ("ownership-" + uuid4().hex + ".sqlite")
        self.store = CaseStore(self.path, ownership_processes=synthetic_registry())
        spec = synthetic_registry().processes[make_request().kind]
        self.store.admit(make_binding(), make_request(), make_checkpoint(profile_version="v1.4", process_version=spec.version,
            phase="wait_operator", next_gate="wait_operator", ownership_state="accepted", ownership_state_revision="owner-r1", ownership_epoch=1))
        source = synthetic_source(self.store)
        intent, effect = synthetic_transfer(source)
        old = self.store.checkpoint("C1")
        business = make_intent(profile_version="v1.4", process_version=spec.version,
            ownership_epoch=1, ownership_state_revision="owner-r1")
        self.store.prepare(business)
        record = self.store.register_transfer_atomic(intent, effect, source, NOW)
        cp = self.store.checkpoint("C1")
        self.assertEqual(record.lifecycle, "prepared")
        self.assertEqual(cp.ownership_state, "transfer_pending")
        self.assertEqual(cp.ownership_epoch, 1)
        self.assertEqual(cp.ownership_state_revision, "owner-r1")
        self.assertEqual(cp.budget, old.budget)
        with self.assertRaises(JournalFailure):
            self.store.begin_dispatch(business, NOW)
        with self.assertRaises(JournalFailure):
            self.store.save_checkpoint(old)
        self.assertEqual(self.store.register_transfer_atomic(intent, effect, source, NOW), record)
        self.store.close()
        self.store = CaseStore(self.path, ownership_processes=synthetic_registry())
        self.assertEqual(self.store.transfer_record(intent.transfer_id), record)
        lease = self.store.begin_registered_transfer(intent.transfer_id, self.store.checkpoint("C1"), NOW)
        self.assertEqual(lease.subject_id, effect.action_id)
        self.assertEqual(self.store.checkpoint("C1").budget.effects, 1)
        with self.assertRaises(JournalFailure):
            self.store.begin_registered_transfer(intent.transfer_id, self.store.checkpoint("C1"), NOW)

    def start_ownership(self, purpose="transfer"):
        self.store.close()
        self.path = Path(self.folder.name) / ("ownership-" + uuid4().hex + ".sqlite")
        self.store = CaseStore(self.path, ownership_processes=synthetic_registry())
        spec = synthetic_registry().processes[make_request().kind]
        self.store.admit(make_binding(), make_request(), make_checkpoint(profile_version="v1.4", process_version=spec.version,
            phase="wait_operator", next_gate="wait_operator", ownership_state="accepted", ownership_state_revision="owner-r1", ownership_epoch=1))
        return synthetic_source(self.store, purpose=purpose)

    def test_unknown_expiry_keeps_original_fence_and_stopped_debt(self):
        source = self.start_ownership()
        intent, effect = synthetic_transfer(source)
        self.store.register_transfer_atomic(intent, effect, source, NOW)
        self.store.begin_registered_transfer(intent.transfer_id, self.store.checkpoint("C1"), NOW)
        self.store.set_stop("C1", "G1")
        before = self.store.checkpoint("C1")
        ownership = self.store.mark_transfer_unknown_atomic(intent.transfer_id, before)
        self.assertEqual((ownership.state, ownership.owner, ownership.epoch), ("transfer_pending", "OP1", 1))
        self.assertEqual(self.store.checkpoint("C1"), before)
        self.assertTrue(self.store.checkpoint("C1").stop.requested)
        self.store.close()
        self.store = CaseStore(self.path, ownership_processes=synthetic_registry())
        self.assertEqual(self.store.transfer_record(intent.transfer_id).lifecycle, "outcome_unknown")
        with self.assertRaises(JournalFailure):
            self.store.begin_registered_transfer(intent.transfer_id, before, DEADLINE)

    def test_entered_acceptance_advances_once_and_requires_matching_fresh_packet(self):
        from proofkey.ownership_contracts import TransferAcceptedV1
        from proofkey.contracts import HumanOwnership
        source = self.start_ownership()
        intent, effect = synthetic_transfer(source)
        record = self.store.register_transfer_atomic(intent, effect, source, NOW)
        receipt = TransferAcceptedV1(original=effect.postcondition["original"], packet=source.packet,
            target_owner="OP2", expected_revisions=effect.expected_revisions, pending_state_revision=None,
            accepted_state_revision="owner-r2", accepted_epoch=2, accepted_at=NOW,
            acceptance_evidence="synthetic-accepted-2", target_instruction_hash="7" * 64, simulated=True)
        packet = source.packet.model_copy(update={"accepted_owner": "OP2", "accepted_epoch": 2,
            "accepted_state_revision": "owner-r2", "acceptance_evidence": "synthetic-accepted-2", "accepted_at": NOW})
        owner = HumanOwnership(binding=make_binding(), owner="OP2", epoch=2, state_revision="owner-r2",
            packet_id="P1", packet_hash="2" * 64, packet_revision="packet-r1", state="accepted",
            acceptance_evidence="synthetic-accepted-2", transfer_id=intent.transfer_id)
        current = synthetic_source(self.store, current=True, packet=packet, ownership=owner)
        with self.assertRaises(JournalFailure):
            self.store.apply_transfer_receipt_atomic(intent.transfer_id, receipt, current, current.checkpoint, NOW)
        self.store.begin_registered_transfer(intent.transfer_id, self.store.checkpoint("C1"), NOW)
        current = synthetic_source(self.store, current=True, packet=packet, ownership=owner)
        result = self.store.apply_transfer_receipt_atomic(intent.transfer_id, receipt, current, current.checkpoint, NOW)
        self.assertEqual((result.owner, result.epoch, result.state), ("OP2", 2, "accepted"))
        self.assertEqual(self.store.checkpoint("C1").ownership_state_revision, "owner-r2")
        # Terminal replay is evidence-idempotent; current snapshot is freshly read.
        current = synthetic_source(self.store, current=True, packet=packet, ownership=owner)
        self.assertEqual(self.store.apply_transfer_receipt_atomic(intent.transfer_id, receipt, current, current.checkpoint, NOW), result)
        with self.assertRaises(JournalFailure):
            self.store.apply_transfer_receipt_atomic(intent.transfer_id,
                receipt.model_copy(update={"acceptance_evidence": "conflicting"}), current, current.checkpoint, NOW)
        self.store.close()
        self.store = CaseStore(self.path, ownership_processes=synthetic_registry())
        self.assertEqual(self.store.human_ownership(make_binding()), result)

    def test_decision_is_record_only_and_consumption_is_atomic_with_exact_entry(self):
        from proofkey.ownership_contracts import OperatorDecisionSubmissionV1
        from proofkey.contracts import OperatorDecision
        source = self.start_ownership(purpose="decision")
        # Transfer tests use the transfer material fields instead.
        effect = make_intent(profile_version="v1.4", process_version=source.checkpoint.process_version,
            decision_id="decision-1", ownership_state_revision="owner-r1", ownership_epoch=1)
        decision = OperatorDecision(decision_id="decision-1", packet_id="P1", packet_hash="2" * 64,
            packet_revision="packet-r1", binding=make_binding(), owner="OP1", epoch=1, state_revision="owner-r1",
            actor_id="OP1", proof_reference="synthetic-proof", decision="approve", scope=["reschedule"],
            expires_at=DEADLINE, replay_id="replay-1", simulated=True)
        submission = OperatorDecisionSubmissionV1(decision=decision, content_hash="3" * 64,
            effect_scope=dict(operation="reschedule", stage="commit", action_id=effect.action_id,
                              argument_fingerprint=effect.argument_fingerprint))
        before = self.store.checkpoint("C1")
        self.assertEqual(self.store.record_decision_atomic(submission, source, NOW), submission)
        self.assertEqual(self.store.checkpoint("C1"), before)
        self.assertEqual(self.store.intents("C1"), ())
        with self.assertRaises(JournalFailure):
            self.store.consume_decision_atomic("decision-1", effect, before, NOW)
        self.store.prepare(effect)
        self.store.begin_dispatch(effect, NOW)
        self.assertEqual(self.store.checkpoint("C1").budget.effects, 1)
        self.store.close()
        self.store = CaseStore(self.path, ownership_processes=synthetic_registry())
        with self.assertRaises(JournalFailure):
            self.store.begin_dispatch(effect, NOW)

    def test_registered_arguments_cannot_enter_through_ordinary_dispatch(self):
        source = self.start_ownership()
        intent, effect = synthetic_transfer(source)
        self.store.prepare(effect)
        with self.assertRaises(JournalFailure):
            self.store.begin_dispatch(effect, NOW)
        self.assertEqual(self.store.checkpoint("C1").budget.effects, 0)

    def test_registration_rejects_immutable_key_target_expiry_and_source_substitutions(self):
        source = self.start_ownership()
        intent, effect = synthetic_transfer(source)
        before = self.store.checkpoint("C1")
        substitutions = [source.model_copy(update={"profile_hash": "0" * 64}),
            source.model_copy(update={"policy_hash": "0" * 64}),
            source.model_copy(update={"read_entry_ids": ["nonexistent-lease"] * 1}),
            source.model_copy(update={"as_of": DEADLINE})]
        for changed in substitutions:
            with self.subTest(source=changed.profile_hash, as_of=changed.as_of):
                with self.assertRaises(JournalFailure):
                    self.store.register_transfer_atomic(intent, effect, changed, NOW)
                self.assertEqual(self.store.checkpoint("C1"), before)
                self.assertEqual(self.store.intents("C1"), ())
        record = self.store.register_transfer_atomic(intent, effect, source, NOW)
        for patch in ({"transfer_id": "fresh-key"}, {"target_owner": "OP3"}, {"expires_at": NOW}):
            with self.assertRaises((JournalFailure, ValueError)):
                self.store.register_transfer_atomic(intent.model_copy(update=patch), effect, source, NOW)
        self.assertEqual(self.store.transfer_record(intent.transfer_id), record)

    def test_registration_and_entry_commit_failure_roll_back_all_accounting(self):
        from support import CommitFault
        source = self.start_ownership()
        intent, effect = synthetic_transfer(source)
        before = self.store.checkpoint("C1")
        fault = CommitFault()
        self.store.close()
        self.store = CaseStore(self.path, before_commit=fault, ownership_processes=synthetic_registry())
        fault.arm()
        with self.assertRaises(JournalFailure):
            self.store.register_transfer_atomic(intent, effect, source, NOW)
        self.assertEqual(self.store.checkpoint("C1"), before)
        self.assertEqual(self.store.intents("C1"), ())
        self.assertIsNone(self.store.transfer(intent.transfer_id))
        self.store.register_transfer_atomic(intent, effect, source, NOW)
        before = self.store.checkpoint("C1")
        fault.arm()
        with self.assertRaises(JournalFailure):
            self.store.begin_registered_transfer(intent.transfer_id, before, NOW)
        self.assertEqual(self.store.checkpoint("C1"), before)
        self.assertEqual(self.store.intent(effect.action_id).state, "prepared")

    def test_source_observations_outside_registered_lease_cannot_register(self):
        from datetime import timedelta
        source = self.start_ownership()
        intent, effect = synthetic_transfer(source)
        # Even aware, ordered source data is invalid if its observation predates
        # every physical lease that allegedly produced the snapshot.
        observations = [item.model_copy(update={"observed_at": NOW - timedelta(seconds=1),
                                               "provider_at": NOW - timedelta(seconds=2)})
                        for item in source.observations]
        changed = source.model_copy(update={"observations": observations})
        with self.assertRaises(JournalFailure):
            self.store.register_transfer_atomic(intent, effect, changed, NOW)
        self.assertEqual(self.store.checkpoint("C1").ownership_state, "accepted")

    def test_initial_accepted_packet_cannot_claim_future_source_acceptance(self):
        source = self.start_ownership()
        packet = source.packet.model_copy(update={"accepted_at": DEADLINE})
        observations = [item.model_copy(update={"value": packet.model_dump(mode="json")})
            if item.authority + "." + item.fact == "operator.ownership_packet" else item
            for item in source.observations]
        changed = source.model_copy(update={"packet": packet, "observations": observations})
        intent, effect = synthetic_transfer(changed)
        with self.assertRaises(JournalFailure):
            self.store.register_transfer_atomic(intent, effect, changed, NOW)

    def test_disposition_replay_is_immutable_record_only_and_cross_kind_collision_denied(self):
        from proofkey.ownership_contracts import OperatorDispositionV1
        source = self.start_ownership(purpose="disposition")
        disposition = OperatorDispositionV1(record_id="record-1", replay_id="replay-1", binding=make_binding(),
            packet_id="P1", packet_hash="2" * 64, packet_revision="packet-r1", content_hash="3" * 64,
            owner="OP1", epoch=1, state_revision="owner-r1", actor_id="OP1", proof_reference="synthetic-proof",
            disposition="refund_review", rationale="Synthetic unit recommendation only", evidence_refs=["unit-evidence"],
            expires_at=DEADLINE, simulated=True)
        before = self.store.checkpoint("C1")
        self.assertEqual(self.store.record_disposition_atomic(disposition, source, NOW), disposition)
        self.assertEqual(self.store.record_disposition_atomic(disposition, source, NOW), disposition)
        self.assertEqual(self.store.checkpoint("C1"), before)
        self.assertEqual(self.store.intents("C1"), ())
        submission, _ = synthetic_decision(source, decision_id="different", replay_id="replay-1")
        with self.assertRaises(JournalFailure):
            self.store.record_decision_atomic(submission, source, NOW)
        for patch in ({"rationale": "Changed recommendation"}, {"record_id": "another"}, {"content_hash": "0" * 64}):
            with self.assertRaises(JournalFailure):
                self.store.record_disposition_atomic(disposition.model_copy(update=patch), source, NOW)
        self.store.close()
        self.store = CaseStore(self.path, ownership_processes=synthetic_registry())
        self.assertEqual(self.store.record_disposition_atomic(disposition, source, NOW), disposition)

    def test_fresh_read_ids_are_required_for_a_distinct_operator_record(self):
        source = self.start_ownership(purpose="decision")
        first, _ = synthetic_decision(source)
        self.store.record_decision_atomic(first, source, NOW)
        another, _ = synthetic_decision(source, decision_id="decision-2", replay_id="replay-2")
        with self.assertRaises(JournalFailure):
            self.store.record_decision_atomic(another, source, NOW)
        fresh = synthetic_source(self.store, purpose="decision")
        self.assertEqual(self.store.record_decision_atomic(another, fresh, NOW), another)

    def test_pending_unknown_acceptance_requires_the_saved_source_pending_revision(self):
        from proofkey.ownership_contracts import TransferPendingV1
        from proofkey.contracts import HumanOwnership
        source = self.start_ownership()
        intent, effect = synthetic_transfer(source)
        self.store.register_transfer_atomic(intent, effect, source, NOW)
        self.store.begin_registered_transfer(intent.transfer_id, self.store.checkpoint("C1"), NOW)
        pending = TransferPendingV1(original=effect.postcondition["original"], packet=source.packet, target_owner="OP2",
            expected_revisions=effect.expected_revisions, pending_state_revision="source-pending-r1", pending_at=NOW,
            evidence_ref="synthetic-pending", simulated=True)
        owner = HumanOwnership(binding=make_binding(), owner="OP1", epoch=1, state_revision="source-pending-r1",
            packet_id="P1", packet_hash="2" * 64, packet_revision="packet-r1", state="transfer_pending",
            pending_evidence="synthetic-pending", transfer_id=intent.transfer_id)
        current = synthetic_source(self.store, current=True, ownership=owner)
        result = self.store.apply_transfer_receipt_atomic(intent.transfer_id, pending, current, current.checkpoint, NOW)
        self.assertEqual(result.state_revision, "owner-r1")
        self.store.mark_transfer_unknown_atomic(intent.transfer_id, self.store.checkpoint("C1"))
        receipt, current = synthetic_acceptance(self.store, source, intent, effect)
        with self.assertRaises(JournalFailure):
            self.store.apply_transfer_receipt_atomic(intent.transfer_id, receipt, current, current.checkpoint, NOW)
        receipt = receipt.model_copy(update={"pending_state_revision": "source-pending-r1"})
        self.assertEqual(self.store.apply_transfer_receipt_atomic(intent.transfer_id, receipt, current, current.checkpoint, NOW).epoch, 2)

    def test_definite_rejection_requires_fresh_retained_owner_and_keeps_epoch(self):
        from proofkey.ownership_contracts import TransferRejectedV1, OWNERSHIP_BASES_V1
        from proofkey.contracts import HumanOwnership
        source = self.start_ownership()
        intent, effect = synthetic_transfer(source)
        self.store.register_transfer_atomic(intent, effect, source, NOW)
        self.store.begin_registered_transfer(intent.transfer_id, self.store.checkpoint("C1"), NOW)
        rejected = TransferRejectedV1(original=effect.postcondition["original"], packet=source.packet, target_owner="OP2",
            expected_revisions=effect.expected_revisions, retained_state_revision="source-retained-r2", rejected_at=NOW,
            nonexecution=dict(status="proven", basis=OWNERSHIP_BASES_V1["terminal_nonexecution_basis"], evidence_ref="synthetic-terminal"),
            evidence_ref="synthetic-rejected", simulated=True)
        owner = HumanOwnership(binding=make_binding(), owner="OP1", epoch=1, state_revision="owner-r1",
            packet_id="P1", packet_hash="2" * 64, packet_revision="packet-r1", state="accepted", acceptance_evidence="accepted-1")
        current = synthetic_source(self.store, current=True, ownership=owner)
        with self.assertRaises(JournalFailure):
            self.store.apply_transfer_receipt_atomic(intent.transfer_id, rejected, current, current.checkpoint, NOW)
        current = synthetic_source(self.store, current=True, ownership=owner.model_copy(update={"state_revision": "source-retained-r2"}))
        before = current.checkpoint
        result = self.store.apply_transfer_receipt_atomic(intent.transfer_id, rejected, current, before, NOW)
        self.assertEqual((result.owner, result.epoch, result.state_revision), ("OP1", 1, "source-retained-r2"))
        self.assertEqual(self.store.checkpoint("C1").budget, before.budget)
        self.store.close()
        self.store = CaseStore(self.path)
        self.assertEqual(self.store.transfer_record(intent.transfer_id).lifecycle, "rejected")

    def test_receipt_substitution_matrix_is_denied_without_clearing_fence(self):
        source = self.start_ownership()
        intent, effect = synthetic_transfer(source)
        self.store.register_transfer_atomic(intent, effect, source, NOW)
        self.store.begin_registered_transfer(intent.transfer_id, self.store.checkpoint("C1"), NOW)
        receipt, current = synthetic_acceptance(self.store, source, intent, effect)
        before = current.checkpoint
        patches = [dict(original=receipt.original.model_copy(update={"argument_fingerprint": "0" * 64})),
            dict(packet=receipt.packet.model_copy(update={"packet_hash": "0" * 64})),
            dict(packet=receipt.packet.model_copy(update={"content_hash": "0" * 64})),
            dict(expected_revisions=RevisionVector(revisions={"delivery.status": "substituted"})),
            dict(target_owner="OP3"), dict(accepted_at=DEADLINE), dict(accepted_state_revision="wrong-source-revision")]
        for patch in patches:
            with self.subTest(fields=list(patch)):
                with self.assertRaises((JournalFailure, ValueError)):
                    self.store.apply_transfer_receipt_atomic(intent.transfer_id, receipt.model_copy(update=patch), current, before, NOW)
                self.assertEqual(self.store.checkpoint("C1"), before)
                self.assertEqual(self.store.transfer_record(intent.transfer_id).lifecycle, "prepared")
        for field in ("profile_hash", "process_hash", "policy_hash"):
            with self.subTest(source_hash=field):
                with self.assertRaises(JournalFailure):
                    self.store.apply_transfer_receipt_atomic(intent.transfer_id, receipt,
                        current.model_copy(update={field: "0" * 64}), before, NOW)
        self.assertEqual(self.store.checkpoint("C1").ownership_state, "transfer_pending")

    def test_unknown_transfer_tag_and_terminal_current_source_corruption_fail_reopen(self):
        source = self.start_ownership()
        intent, effect = synthetic_transfer(source)
        self.store.register_transfer_atomic(intent, effect, source, NOW)
        self.store.begin_registered_transfer(intent.transfer_id, self.store.checkpoint("C1"), NOW)
        receipt, current = synthetic_acceptance(self.store, source, intent, effect)
        self.store.apply_transfer_receipt_atomic(intent.transfer_id, receipt, current, current.checkpoint, NOW)
        self.store.close()
        # Intentional hostile DB writes only; no private SQL inventory getters.
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE audit SET event_json=json_set(event_json, '$.ownership_event.source_current.packet.content_hash', ?) "
                "WHERE json_extract(event_json, '$.ownership_event.kind')='transfer_resolved_v1'", ("0" * 64,))
        with self.assertRaises(JournalFailure):
            CaseStore(self.path, ownership_processes=synthetic_registry())
        self.store = CaseStore(Path(self.folder.name) / "legacy-unknown.sqlite")
        self.store.admit(make_binding(), make_request(), make_checkpoint())
        legacy = TransferIntent(transfer_id="legacy", binding=make_binding(), case_id="C1", packet_id="P1",
            packet_hash="2" * 64, packet_revision="p1", expected_owner="OP1", expected_state_revision="o1",
            expected_epoch=1, target_owner="OP2", expires_at=DEADLINE)
        self.store.save_transfer(legacy)
        path = Path(self.folder.name) / "legacy-unknown.sqlite"
        self.store.close()
        with sqlite3.connect(path) as db:
            db.execute("UPDATE transfers SET transfer_json=json_set(transfer_json, '$.kind', 'unknown_ownership_tag')")
        with self.assertRaises(JournalFailure):
            CaseStore(path)

    def test_decision_consumption_commit_failure_preserves_unconsumed_approval(self):
        from support import CommitFault
        source = self.start_ownership(purpose="decision")
        submission, effect = synthetic_decision(source)
        self.store.record_decision_atomic(submission, source, NOW)
        self.store.prepare(effect)
        before = self.store.checkpoint("C1")
        self.store.close()
        fault = CommitFault()
        self.store = CaseStore(self.path, before_commit=fault, ownership_processes=synthetic_registry())
        fault.arm()
        with self.assertRaises(JournalFailure):
            self.store.begin_dispatch(effect, NOW)
        self.assertEqual(self.store.checkpoint("C1"), before)
        self.assertEqual(self.store.intent(effect.action_id).state, "prepared")
        self.store.close()
        self.store = CaseStore(self.path, ownership_processes=synthetic_registry())
        self.store.begin_dispatch(effect, NOW)
        self.assertEqual(self.store.checkpoint("C1").budget.effects, 1)

    def test_terminal_resolution_commit_failure_keeps_the_pending_original(self):
        from support import CommitFault
        source = self.start_ownership()
        intent, effect = synthetic_transfer(source)
        self.store.register_transfer_atomic(intent, effect, source, NOW)
        self.store.begin_registered_transfer(intent.transfer_id, self.store.checkpoint("C1"), NOW)
        receipt, current = synthetic_acceptance(self.store, source, intent, effect)
        before = current.checkpoint
        self.store.close()
        fault = CommitFault()
        self.store = CaseStore(self.path, before_commit=fault, ownership_processes=synthetic_registry())
        fault.arm()
        with self.assertRaises(JournalFailure):
            self.store.apply_transfer_receipt_atomic(intent.transfer_id, receipt, current, before, NOW)
        self.store.close()
        self.store = CaseStore(self.path, ownership_processes=synthetic_registry())
        self.assertEqual(self.store.transfer_record(intent.transfer_id).lifecycle, "prepared")
        self.assertEqual(self.store.checkpoint("C1"), before)
        self.assertEqual(self.store.apply_transfer_receipt_atomic(intent.transfer_id, receipt, current, before, NOW).epoch, 2)

    def test_real_hard_exit_before_and_after_pending_entry_terminal_and_consumption_commits(self):
        boundaries = ("pending_before_commit", "pending_after_commit", "entry_before_commit", "entry_after_commit",
                      "terminal_before_commit", "terminal_after_commit", "consume_before_commit", "consume_after_commit")
        for boundary in boundaries:
            with self.subTest(boundary=boundary):
                self.start_ownership()
                path = self.path
                self.store.close()
                result = subprocess.run([sys.executable, "-c",
                    "from test_ownership_storage import hard_exit_driver; import sys; hard_exit_driver(sys.argv[1], sys.argv[2])",
                    str(path), boundary], env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                    capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 71, result.stdout + result.stderr)
                self.store = CaseStore(path, ownership_processes=synthetic_registry())
                cp = self.store.checkpoint("C1")
                if boundary == "pending_before_commit":
                    self.assertEqual(cp.ownership_state, "accepted")
                    self.assertEqual(self.store.intents("C1"), ())
                    continue
                original = self.store.intents("C1")[0]
                entered = boundary in {"entry_after_commit", "terminal_before_commit", "terminal_after_commit", "consume_after_commit"}
                self.assertEqual(original.state, "dispatching" if entered else "prepared")
                self.assertEqual(cp.budget.effects, 1 if entered else 0)
                if boundary.startswith("consume"):
                    if not entered:
                        self.store.begin_dispatch(original.intent, NOW)
                    with self.assertRaises(JournalFailure):
                        self.store.begin_dispatch(original.intent, NOW)
                else:
                    record = self.store.transfer_record(original.intent.action_id)
                    self.assertEqual(record.lifecycle, "accepted" if boundary == "terminal_after_commit" else "prepared")
                    self.assertEqual(cp.ownership_epoch, 2 if boundary == "terminal_after_commit" else 1)
                    self.assertEqual(cp.ownership_state, "accepted" if boundary == "terminal_after_commit" else "transfer_pending")

    def test_barrier_controlled_journal_orders_fence_or_preserve_entered_original(self):
        for transfer_first in (True, False):
            with self.subTest(transfer_first=transfer_first):
                decision_source = self.start_ownership(purpose="decision")
                submission, effect = synthetic_decision(decision_source)
                self.store.record_decision_atomic(submission, decision_source, NOW)
                source = synthetic_source(self.store)
                intent, transfer_effect = synthetic_transfer(source)
                self.store.prepare(effect)
                path = self.path
                self.store.close()
                first_committed, second_ready = threading.Event(), threading.Event()
                outcomes, errors = [], []
                def worker(transfer):
                    local = CaseStore(path, ownership_processes=synthetic_registry())
                    try:
                        if transfer != transfer_first:
                            second_ready.set()
                            if not first_committed.wait(5):
                                raise AssertionError("first transaction did not commit")
                        else:
                            if not second_ready.wait(5):
                                raise AssertionError("second worker did not reach barrier")
                        if transfer:
                            fresh = source if transfer_first else synthetic_source(local)
                            local.register_transfer_atomic(intent, transfer_effect, fresh, NOW)
                            outcomes.append("registered")
                        else:
                            try:
                                local.begin_dispatch(effect, NOW)
                                outcomes.append("entered")
                            except JournalFailure:
                                outcomes.append("fenced")
                    except BaseException as error:
                        errors.append(error)
                    finally:
                        if transfer == transfer_first:
                            first_committed.set()
                        local.close()
                threads = [threading.Thread(target=worker, args=(flag,)) for flag in (True, False)]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join(10)
                self.assertFalse(any(thread.is_alive() for thread in threads))
                self.assertEqual(errors, [])
                self.assertEqual(set(outcomes), {"registered", "fenced" if transfer_first else "entered"})
                self.store = CaseStore(path, ownership_processes=synthetic_registry())
                self.assertEqual(self.store.intent(effect.action_id).state, "prepared" if transfer_first else "dispatching")
                self.assertEqual(self.store.checkpoint("C1").budget.effects, 0 if transfer_first else 1)
