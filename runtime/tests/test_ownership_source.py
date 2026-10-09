"""Independent public-port source tests; synthetic setup is not native authority."""
import copy
from datetime import timedelta
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest

from proofkey.adapters.world import SimulatedWorld
from proofkey.contracts import ReadRequest, ReadTarget, RevisionVector, TransferIntent
from proofkey.identity import fingerprint, stable_action_id
from proofkey.ownership_contracts import (OriginalTransferIdentityV1, OwnershipPacketV1,
    SyntheticTargetAcceptanceV1, TransferArgumentsV1, TransferPostconditionV1)
from proofkey.profiles import load_profile
from support import NOW, DEADLINE, FakeClock, make_auth, make_binding, make_intent, make_request

ROOT = Path(__file__).resolve().parents[1]


def fixture_authority_hash(authority):
    payload = copy.deepcopy(authority)
    payload.pop("fixture_hash", None)
    payload["grant"].pop("fixture_hash", None)
    for instruction in payload["target_acceptances"]:
        instruction.pop("fixture_hash", None)
    return fingerprint(payload)


def synthetic_fixture(profile, *, direct_accept=False):
    """Host-only initial accepted packet, independent from inbound transfer arguments."""
    raw = json.loads((ROOT / "fixtures/development/packet-world-v1.json").read_text())
    raw["facts"]["ownership.owner"]["value"] = "OP1"
    packet = OwnershipPacketV1(binding=make_binding(), packet_id="P1", packet_hash="b" * 64,
        packet_revision="v1", content_hash="c" * 64, accepted_owner="OP1", accepted_epoch=0,
        accepted_state_revision="v1", acceptance_evidence="synthetic-initial-packet-acceptance",
        accepted_at=NOW, simulated=True).model_dump(mode="json")
    authority = {"kind": "synthetic_ownership_fixture_v1", "profile_id": profile.profile_id,
        "profile_version": profile.version, "profile_hash": profile.release_hash,
        "process_hash": profile.process_hash, "policy_hash": profile.policy_hash,
        "request": make_request().model_dump(mode="json"), "case_deadline": DEADLINE.isoformat().replace("+00:00", "Z"),
        "packet": packet, "grant_revision": "v1", "grant": {"kind": "ownership_grant_v1",
            "grant_id": "synthetic-owner-grant", "binding": make_binding().model_dump(mode="json"),
            "actor_id": "OP1", "actor_type": "human", "packet_id": "P1", "packet_hash": "b" * 64,
            "packet_revision": "v1", "content_hash": "c" * 64, "owner": "OP1", "epoch": 0,
            "state_revision": "v1", "may_initiate_transfer": True, "target_owners": ["OP2"],
            "decision_operations": ["reschedule"], "may_record_nonaction_decision": True,
            "dispositions": ["refund_review"], "issued_at": (NOW - timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
            "expires_at": DEADLINE.isoformat().replace("+00:00", "Z"), "evidence_ref": "synthetic-owner-grant-evidence",
            "fixture_hash": "0" * 64, "simulated": True}, "target_acceptances": [],
        "fixture_hash": "0" * 64, "simulated": True}
    raw["ownership_authority"] = authority
    if direct_accept:
        authority["target_acceptances"] = [target_instruction(raw, profile).model_dump(mode="json")]
    value = fixture_authority_hash(authority)
    authority["fixture_hash"] = authority["grant"]["fixture_hash"] = value
    for instruction in authority["target_acceptances"]:
        instruction["fixture_hash"] = value
    return raw


def effect_for(raw, profile, revisions=None):
    authority = raw["ownership_authority"]
    packet = OwnershipPacketV1.model_validate(authority["packet"])
    key = stable_action_id(packet.binding, "transfer_owner", "request")
    transfer = TransferIntent(transfer_id=key, binding=packet.binding, case_id=packet.binding.case_id,
        packet_id=packet.packet_id, packet_hash=packet.packet_hash, packet_revision=packet.packet_revision,
        expected_owner=packet.accepted_owner, expected_state_revision=packet.accepted_state_revision,
        expected_epoch=packet.accepted_epoch, target_owner="OP2", expires_at=DEADLINE)
    arguments = TransferArgumentsV1(intent=transfer, content_hash=packet.content_hash,
        grant_id=authority["grant"]["grant_id"], grant_revision=authority["grant_revision"]).model_dump(mode="json")
    original = OriginalTransferIdentityV1(binding=packet.binding, transfer_id=key, action_id=key,
        provider_key=key, argument_fingerprint=fingerprint(arguments))
    material = set().union(*(set(profile.capabilities[name].conditional_coverage.covered_fields)
        for name in ("reschedule", "register_goods_refusal", "register_service_refusal", "create_return",
                     "send_clarification", "send_status", "enqueue_handoff", "transfer_owner")))
    fixture_revisions = {key: fact["revision"] for key, fact in raw["facts"].items() if key in material}
    fixture_revisions.update({"operator.ownership_grant": authority["grant_revision"], "operator.ownership_packet": "v1"})
    expected = revisions or RevisionVector(revisions=fixture_revisions)
    return make_intent(operation="transfer_owner", stage="request", arguments=arguments,
        profile_version=profile.version, expected_revisions=expected, ownership_state_revision="v1",
        ownership_epoch=0, postcondition=TransferPostconditionV1(original=original, packet=packet,
            target_owner="OP2", accepted_epoch=1).model_dump(mode="json"))


def target_instruction(raw, profile, revisions=None):
    effect = effect_for(raw, profile, revisions)
    condition = TransferPostconditionV1.model_validate(effect.postcondition)
    return SyntheticTargetAcceptanceV1(original=condition.original, packet=condition.packet,
        target_owner="OP2", expected_revisions=effect.expected_revisions, expires_at=DEADLINE,
        fixture_hash=raw["ownership_authority"]["fixture_hash"],
        evidence_ref="synthetic-exact-target-acceptance", simulated=True)


class OwnershipSourceTests(unittest.TestCase):
    def setUp(self):
        try:
            self.profile = load_profile("flat-v1.4")
        except ValueError as exc:
            self.fail("Registered ownership source profile is missing: " + str(exc))
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.db = Path(self.folder.name) / "source.sqlite"
        self.fixture_path = Path(self.folder.name) / "source.json"
        self.clock = FakeClock()
        self.owner = make_auth(caller_id="OP1", proof_reference="synthetic-operator-proof")

    def source(self, *, direct=False, patch=None):
        self.fixture = synthetic_fixture(self.profile, direct_accept=direct)
        if patch:
            patch(self.fixture)
        self.fixture_path.write_text(json.dumps(self.fixture))
        self.world = SimulatedWorld(self.db, self.fixture_path, profile=self.profile, clock=self.clock)
        self.port = self.world.bundle().operator
        return effect_for(self.fixture, self.profile, self.world.material_revisions())

    def read(self, effect=None, *, caller="OP1", proof="synthetic-operator-proof", facts=None, deadline=DEADLINE):
        target = (ReadTarget(kind="authority_facts", authority="operator", facts=facts) if facts else
            ReadTarget(kind="original_effect", operation="transfer_owner", generation=effect.binding.generation,
                action_id=effect.action_id, provider_key=effect.provider_key, fingerprint=effect.argument_fingerprint))
        return self.port.read_owner(ReadRequest(case_id="C1", object_id="O1", caller_id=caller,
            proof_reference=proof, purpose="transfer" if facts else "reconcile", deadline=deadline, target=target))

    def receipt(self, effect):
        read = self.read(effect)
        found = [obs for obs in read.observations if obs.authority == "operator" and obs.fact == "transfer_receipt"]
        self.assertEqual(len(found), 1, "Exact original source read must contain one typed receipt")
        return read, found[0]

    def test_current_owner_grant_is_source_owned_not_reader_membership(self):
        self.source()
        read = self.read(facts=["ownership_grant", "ownership_packet"])
        self.assertEqual({o.fact for o in read.observations}, {"ownership_grant", "ownership_packet"})
        grant = next(o.value for o in read.observations if o.fact == "ownership_grant")
        self.assertEqual(grant["actor_id"], "OP1")
        self.assertEqual(grant["fixture_hash"], self.fixture["ownership_authority"]["fixture_hash"])
        for caller, proof in (("U1", "synthetic-proof"), ("OP2", "synthetic-target-proof"), ("OP1", "wrong")):
            with self.subTest(caller=caller):
                self.assertEqual(self.read(caller=caller, proof=proof, facts=["ownership_grant"]).observations, [])

    def test_current_owner_grant_supports_exact_record_only_purposes(self):
        self.source()
        for purpose in ("decision", "disposition"):
            request = ReadRequest(case_id="C1", object_id="O1", caller_id="OP1",
                proof_reference="synthetic-operator-proof", purpose=purpose, deadline=DEADLINE,
                target=ReadTarget(kind="authority_facts", authority="operator", facts=["ownership_grant", "ownership_packet"]))
            self.assertEqual(len(self.port.read_owner(request).observations), 2)
        self.assertEqual(self.world.effect_count("transfer_owner"), 0)

    def test_source_rejects_shorter_effect_deadline_than_transfer_expiry(self):
        effect = self.source()
        changed = effect.model_copy(update={"deadline": DEADLINE - timedelta(seconds=1)})
        self.assertEqual(self.port.transfer_owner(changed, auth=self.owner).status, "rejected")
        self.assertEqual(self.world.effect_count("transfer_owner"), 0)

    def test_registered_initial_packet_requires_content_digest(self):
        raw = synthetic_fixture(self.profile)
        authority = raw["ownership_authority"]
        authority["packet"]["content_hash"] = authority["grant"]["content_hash"] = None
        value = fixture_authority_hash(authority)
        authority["fixture_hash"] = authority["grant"]["fixture_hash"] = value
        self.fixture_path.write_text(json.dumps(raw))
        with self.assertRaises(ValueError):
            SimulatedWorld(self.db, self.fixture_path, profile=self.profile, clock=self.clock)

    def test_missing_target_instruction_and_owner_accepted_fault_still_yield_pending(self):
        effect = self.source()
        self.world.set_fault("transfer_owner", "owner_accepted")
        self.assertEqual(self.port.transfer_owner(effect, auth=self.owner).status, "acknowledged")
        read, observation = self.receipt(effect)
        self.assertEqual(observation.value["kind"], "transfer_pending_v1")
        self.assertEqual(observation.value["packet"]["accepted_owner"], "OP1")
        self.assertEqual(observation.value["packet"]["accepted_epoch"], 0)
        self.assertEqual(read.fingerprint, effect.argument_fingerprint)
        self.assertEqual(self.world.effect_count("transfer_owner"), 1)

    def test_direct_exact_source_acceptance_reopens_original_identity_and_time(self):
        effect = self.source(direct=True)
        self.assertEqual(self.port.transfer_owner(effect, auth=self.owner).status, "acknowledged")
        first_read, observation = self.receipt(effect)
        self.assertEqual(observation.value["kind"], "transfer_accepted_v1")
        self.assertEqual(observation.value["accepted_epoch"], 1)
        self.assertEqual(observation.value["original"]["provider_key"], effect.provider_key)
        accepted_at = observation.value["accepted_at"]
        self.clock.advance(1)
        reopened = SimulatedWorld(self.db, self.fixture_path, profile=self.profile, clock=self.clock)
        self.world, self.port = reopened, reopened.bundle().operator
        later_read, later = self.receipt(effect)
        self.assertEqual(later.value["accepted_at"], accepted_at)
        self.assertGreater(later.observed_at, first_read.as_of)
        self.assertEqual(later_read.action_id, effect.action_id)
        self.assertEqual(later_read.fingerprint, effect.argument_fingerprint)
        self.assertEqual(reopened.effect_count("transfer_owner"), 1)

    def test_absent_wrong_and_readers_only_transport_auth_cannot_enter(self):
        effect = self.source()
        for auth in (None, make_auth(caller_id="OP1", proof_reference="wrong"),
                     make_auth(caller_id="OP2", proof_reference="synthetic-target-proof"), make_auth()):
            with self.subTest(auth=auth):
                self.assertEqual(self.port.transfer_owner(effect, auth=auth).status, "rejected")
        self.assertEqual(self.world.effect_count("transfer_owner"), 0)

    def test_hostile_body_grant_and_legacy_transfer_alias_cannot_activate(self):
        effect = self.source()
        hostile = effect.arguments.copy()
        hostile["auth"] = self.owner.model_dump(mode="json")
        body = make_intent(operation="transfer_owner", stage="request", arguments=hostile,
            profile_version="v1.4", expected_revisions=effect.expected_revisions, postcondition=effect.postcondition)
        self.assertEqual(self.port.transfer_owner(body, auth=self.owner).status, "rejected")
        legacy = make_intent(operation="transfer_owner", stage="request", profile_version="v1.4",
            expected_revisions=effect.expected_revisions, arguments={"transfer_id": effect.action_id,
                "packet_id": "P1", "packet_revision": "v1", "packet_hash": "b" * 64, "target_owner": "OP2"})
        self.assertEqual(self.port.transfer_owner(legacy, auth=self.owner).status, "rejected")
        self.assertEqual(self.world.effect_count("transfer_owner"), 0)

    def test_changed_fixture_provenance_is_rejected_on_construction(self):
        self.fixture = synthetic_fixture(self.profile)
        self.fixture["ownership_authority"]["grant"]["target_owners"].append("READER")
        self.fixture_path.write_text(json.dumps(self.fixture))
        with self.assertRaises(ValueError):
            SimulatedWorld(self.db, self.fixture_path, profile=self.profile, clock=self.clock)

    def test_later_exact_target_instruction_accepts_pending_original_once(self):
        effect = self.source()
        self.assertEqual(self.port.transfer_owner(effect, auth=self.owner).status, "acknowledged")
        _, pending = self.receipt(effect)
        self.assertEqual(pending.value["kind"], "transfer_pending_v1")
        self.assertTrue(hasattr(self.world, "deliver_target_acceptance"), "Trusted synthetic driver delivery is absent")
        instruction = target_instruction(self.fixture, self.profile, effect.expected_revisions)
        self.assertTrue(self.world.deliver_target_acceptance(instruction))
        self.assertTrue(self.world.deliver_target_acceptance(instruction))
        _, accepted = self.receipt(effect)
        self.assertEqual(accepted.value["kind"], "transfer_accepted_v1")
        self.assertEqual(accepted.value["pending_state_revision"], pending.value["pending_state_revision"])
        self.assertEqual(accepted.value["target_instruction_hash"], fingerprint(instruction.model_dump(mode="json")))
        self.assertEqual(self.world.effect_count("transfer_owner"), 1)
        self.assertFalse(hasattr(self.port, "deliver_target_acceptance"))

    def test_exact_original_only_short_selector_and_wrong_fingerprint_return_no_receipt(self):
        effect = self.source()
        self.assertEqual(self.read(effect).observations, [])
        self.assertEqual(self.port.transfer_owner(effect, auth=self.owner).status, "acknowledged")
        wrong = ReadRequest(case_id="C1", object_id="O1", caller_id="OP1", proof_reference="synthetic-operator-proof",
            purpose="reconcile", deadline=DEADLINE, target=ReadTarget(kind="original_effect", operation="transfer_owner",
                generation="G1", action_id=effect.action_id, provider_key=effect.provider_key, fingerprint="0" * 64))
        self.assertEqual(self.port.read_owner(wrong).observations, [])
        short = self.port.read_owner(ReadRequest(case_id="C1", object_id="O1", caller_id="OP1",
            proof_reference="synthetic-operator-proof", purpose="reconcile", deadline=DEADLINE,
            target=ReadTarget(kind="transfer", transfer_id=effect.action_id, packet_id="P1", packet_revision="v1")))
        self.assertEqual(short.observations, [])

    def test_same_key_changed_payload_never_replaces_pending_original(self):
        effect = self.source()
        self.assertEqual(self.port.transfer_owner(effect, auth=self.owner).status, "acknowledged")
        self.assertEqual(self.port.transfer_owner(effect, auth=self.owner).status, "acknowledged")
        arguments = json.loads(json.dumps(effect.model_dump(mode="json")["arguments"]))
        arguments["intent"]["target_owner"] = "OP3"
        changed = make_intent(operation="transfer_owner", stage="request", arguments=arguments,
            profile_version="v1.4", expected_revisions=effect.expected_revisions,
            ownership_state_revision="v1", ownership_epoch=0, postcondition=effect.postcondition)
        self.assertEqual(self.port.transfer_owner(changed, auth=self.owner).status, "rejected")
        _, receipt = self.receipt(effect)
        self.assertEqual(receipt.value["target_owner"], "OP2")
        self.assertEqual(self.world.effect_count("transfer_owner"), 1)

    def test_terminal_nonexecution_is_typed_but_timeout_before_is_unknown(self):
        effect = self.source()
        self.world.set_fault("transfer_owner", "timeout_before")
        self.assertEqual(self.port.transfer_owner(effect, auth=self.owner).status, "outcome_unknown")
        self.assertEqual(self.read(effect).observations, [])
        self.world.set_fault("transfer_owner", "business_rejection")
        self.assertEqual(self.port.transfer_owner(effect, auth=self.owner).status, "rejected")
        self.world.set_fault("read_owner", "terminal_not_executed")
        read, receipt = self.receipt(effect)
        self.assertEqual(receipt.value["kind"], "transfer_rejected_v1")
        self.assertEqual(receipt.value["nonexecution"]["status"], "proven")
        self.assertEqual(receipt.value["original"]["argument_fingerprint"], effect.argument_fingerprint)
        self.assertEqual(read.stage, "terminally_rejected")
        self.assertEqual(self.world.effect_count("transfer_owner"), 0)

    def test_pending_grant_read_does_not_claim_current_initiation_permission(self):
        effect = self.source()
        self.assertEqual(self.port.transfer_owner(effect, auth=self.owner).status, "acknowledged")
        self.assertEqual(self.read(facts=["ownership_grant"]).observations, [])

    def test_registered_source_database_cannot_reopen_under_legacy_semantics(self):
        self.source()
        with self.assertRaises(ValueError):
            SimulatedWorld(self.db, self.fixture_path, profile=load_profile("flat-v1.3"), clock=self.clock)

    def test_registered_fixture_rejects_duplicate_fields_before_hashing(self):
        raw = synthetic_fixture(self.profile)
        text = json.dumps(raw).replace('"may_initiate_transfer": true',
            '"may_initiate_transfer": false, "may_initiate_transfer": true')
        self.fixture_path.write_text(text)
        with self.assertRaises(ValueError):
            SimulatedWorld(self.db, self.fixture_path, profile=self.profile, clock=self.clock)

    def test_missing_source_grant_or_body_only_proof_fails_closed(self):
        raw = synthetic_fixture(self.profile)
        raw.pop("ownership_authority")
        self.fixture_path.write_text(json.dumps(raw))
        with self.assertRaises(ValueError):
            SimulatedWorld(self.db, self.fixture_path, profile=self.profile, clock=self.clock)
        effect = self.source()
        args = effect.model_dump(mode="json")["arguments"]
        args["auth"] = self.owner.model_dump(mode="json")
        body = make_intent(operation="transfer_owner", stage="request", arguments=args,
            profile_version="v1.4", expected_revisions=effect.expected_revisions,
            ownership_state_revision="v1", ownership_epoch=0, postcondition=effect.postcondition)
        self.assertEqual(self.port.transfer_owner(body).status, "rejected")
        self.assertEqual(self.world.effect_count("transfer_owner"), 0)

    def test_source_unknown_after_execution_reconciles_without_replacement(self):
        effect = self.source(direct=True)
        self.world.set_fault("transfer_owner", "timeout_after")
        result = self.port.transfer_owner(effect, auth=self.owner)
        self.assertEqual(result.status, "outcome_unknown")
        self.assertIsNone(result.provider_request_id)
        self.assertEqual(self.receipt(effect)[1].value["kind"], "transfer_accepted_v1")
        self.assertEqual(self.port.transfer_owner(effect, auth=self.owner).status, "acknowledged")
        self.assertEqual(self.world.effect_count("transfer_owner"), 1)

    def test_scope_without_transfer_permission_is_not_reader_based_activation(self):
        def remove_permission(raw):
            authority = raw["ownership_authority"]
            authority["grant"]["may_initiate_transfer"] = False
            value = fixture_authority_hash(authority)
            authority["fixture_hash"] = authority["grant"]["fixture_hash"] = value
        effect = self.source(patch=remove_permission)
        self.assertEqual(self.port.transfer_owner(effect, auth=self.owner).status, "rejected")
        self.assertEqual(self.world.effect_count("transfer_owner"), 0)

    def test_acceptance_crossing_original_deadline_rolls_back_all_source_changes(self):
        effect = self.source()
        self.assertEqual(self.port.transfer_owner(effect, auth=self.owner).status, "acknowledged")
        instruction = target_instruction(self.fixture, self.profile, effect.expected_revisions)
        update = self.world._update
        def expire_inside_transaction(connection, case, obj, identity, value):
            result = update(connection, case, obj, identity, value)
            if identity == "ownership.state" and value == "accepted":
                self.clock.advance(7200)
            return result
        self.world._update = expire_inside_transaction
        self.assertFalse(self.world.deliver_target_acceptance(instruction))
        read = self.read(effect, deadline=DEADLINE + timedelta(hours=1))
        self.assertEqual(read.observations[0].value["kind"], "transfer_pending_v1")
        with sqlite3.connect(self.db) as connection:
            owner = json.loads(connection.execute("SELECT value FROM facts WHERE identity='ownership.owner'").fetchone()[0])
            record = json.loads(connection.execute("SELECT value FROM metadata WHERE key LIKE 'ownership_original:%'").fetchone()[0])
        self.assertEqual(owner, "OP1")
        self.assertEqual(len(record["history"]), 1)

    def test_exact_content_and_source_revision_are_checked_not_metadata_alone(self):
        effect = self.source()
        args = effect.model_dump(mode="json")["arguments"]
        args["content_hash"] = "d" * 64
        changed = make_intent(operation="transfer_owner", stage="request", arguments=args,
            profile_version="v1.4", expected_revisions=effect.expected_revisions,
            ownership_state_revision="v1", ownership_epoch=0, postcondition=effect.postcondition)
        self.assertEqual(self.port.transfer_owner(changed, auth=self.owner).status, "rejected")
        self.world.mutate("operator.ownership_grant", self.fixture["ownership_authority"]["grant"])
        self.assertEqual(self.port.transfer_owner(effect, auth=self.owner).status, "rejected")
        self.assertEqual(self.world.effect_count("transfer_owner"), 0)

    def test_actual_generation_and_consent_fence_entry(self):
        effect = self.source()
        self.world.mutate("case.generation", "G2")
        self.assertEqual(self.port.transfer_owner(effect, auth=self.owner).status, "rejected")
        self.world.mutate("case.generation", "G1")
        self.world.mutate("customer.consent", "revoked")
        self.assertEqual(self.port.transfer_owner(effect, auth=self.owner).status, "rejected")
        self.assertEqual(self.world.effect_count("transfer_owner"), 0)

    def test_expired_or_mismatched_instruction_cannot_accept_pending(self):
        effect = self.source()
        self.assertEqual(self.port.transfer_owner(effect, auth=self.owner).status, "acknowledged")
        instruction = target_instruction(self.fixture, self.profile, effect.expected_revisions)
        for update in ({"fixture_hash": "0" * 64}, {"target_owner": "OP3"},
                {"packet": instruction.packet.model_copy(update={"content_hash": "d" * 64})},
                {"expected_revisions": RevisionVector(revisions={"case.generation": "v2"})}):
            with self.subTest(update=update):
                self.assertFalse(self.world.deliver_target_acceptance(instruction.model_copy(update=update)))
        self.clock.advance(7200)
        self.assertFalse(self.world.deliver_target_acceptance(instruction))
        self.world = SimulatedWorld(self.db, self.fixture_path, profile=self.profile, clock=self.clock)
        self.port = self.world.bundle().operator
        later = self.read(effect, deadline=DEADLINE + timedelta(hours=1))
        self.assertEqual(later.observations[0].value["kind"], "transfer_pending_v1")

    def test_changed_source_case_or_packet_facts_prevent_late_acceptance(self):
        for field, value in (("case.generation", "G2"), ("operator.packet_hash", "d" * 64),
                ("customer.consent", "revoked"), ("scheduling.slot", "S2")):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as folder:
                self.db = Path(folder) / "source.sqlite"
                effect = self.source()
                self.assertEqual(self.port.transfer_owner(effect, auth=self.owner).status, "acknowledged")
                self.world.mutate(field, value)
                instruction = target_instruction(self.fixture, self.profile, effect.expected_revisions)
                self.assertFalse(self.world.deliver_target_acceptance(instruction))
                self.assertEqual(self.receipt(effect)[1].value["kind"], "transfer_pending_v1")

    def test_transfer_never_changes_artifact_acl_consent_or_wait_stop_facts(self):
        effect = self.source(direct=True)
        identities = ("operator.packet_access", "customer.consent", "customer.consent_revision",
                      "case.question_revision", "case.result_revision", "case.authorization")
        def snapshot():
            with sqlite3.connect(self.db) as connection:
                return {key: connection.execute("SELECT value,revision FROM facts WHERE identity=?", (key,)).fetchone()
                        for key in identities}
        before = snapshot()
        self.assertEqual(self.port.transfer_owner(effect, auth=self.owner).status, "acknowledged")
        self.assertEqual(snapshot(), before)
        denied = self.port.read_receipt(ReadRequest(case_id="C1", object_id="O1", caller_id="OP2",
            proof_reference="synthetic-target-proof", purpose="operator_packet", deadline=DEADLINE,
            target=ReadTarget(kind="authority_facts", authority="operator", facts=["packet_access"])))
        self.assertEqual(denied.observations, [])

    def test_rejected_auth_still_charges_each_physical_dispatch_but_no_effect(self):
        effect = self.source()
        for _ in range(3):
            self.assertEqual(self.port.transfer_owner(effect, auth=None).status, "rejected")
        with sqlite3.connect(self.db) as connection:
            used, active = connection.execute("SELECT used,active FROM pressure").fetchone()
        self.assertEqual((used, active), (3, 0))
        self.assertEqual(len(self.world.calls), 3)
        self.assertEqual(self.world.effect_count("transfer_owner"), 0)

    def test_real_hard_exit_after_provider_acceptance_reopens_exact_receipt(self):
        self.fixture = synthetic_fixture(self.profile, direct_accept=True)
        self.fixture_path.write_text(json.dumps(self.fixture))
        code = """import json, os, sys
from pathlib import Path
from proofkey.adapters.world import SimulatedWorld
from proofkey.profiles import load_profile
from support import FakeClock, make_auth
from test_ownership_source import effect_for
p = load_profile('flat-v1.4')
w = SimulatedWorld(sys.argv[1], sys.argv[2], profile=p, clock=FakeClock())
e = effect_for(json.loads(Path(sys.argv[2]).read_text()), p, w.material_revisions())
assert w.bundle().operator.transfer_owner(e, auth=make_auth(caller_id='OP1', proof_reference='synthetic-operator-proof')).status == 'acknowledged'
os._exit(73)
"""
        result = subprocess.run([sys.executable, "-c", code, str(self.db), str(self.fixture_path)],
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 73, result.stderr)
        self.world = SimulatedWorld(self.db, self.fixture_path, profile=self.profile, clock=self.clock)
        self.port = self.world.bundle().operator
        effect = effect_for(self.fixture, self.profile)
        receipt = self.receipt(effect)[1].value
        self.assertEqual(receipt["kind"], "transfer_accepted_v1")
        self.assertEqual(receipt["original"]["argument_fingerprint"], effect.argument_fingerprint)
        self.assertEqual(self.world.effect_count("transfer_owner"), 1)

    def test_barrier_ordered_old_business_entry_vs_pending_transfer_both_orders(self):
        for winner in ("business", "transfer"):
            with self.subTest(winner=winner), tempfile.TemporaryDirectory() as folder:
                self.db = Path(folder) / "source.sqlite"
                effect = self.source()
                other = SimulatedWorld(self.db, self.fixture_path, profile=self.profile, clock=self.clock)
                business = make_intent(profile_version="v1.4", expected_revisions=effect.expected_revisions,
                    ownership_state_revision="v1", ownership_epoch=0)
                ready, completed = threading.Barrier(2), threading.Event()
                results, errors = {}, []
                def run(name):
                    try:
                        ready.wait(timeout=3)
                        if name != winner:
                            self.assertTrue(completed.wait(timeout=3))
                        results[name] = (other.bundle().scheduling.reschedule(business) if name == "business"
                            else self.port.transfer_owner(effect, auth=self.owner))
                    except BaseException as error:
                        errors.append(error)
                    finally:
                        if name == winner:
                            completed.set()
                threads = [threading.Thread(target=run, args=(name,)) for name in ("business", "transfer")]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join(timeout=5)
                    self.assertFalse(thread.is_alive())
                self.assertEqual(errors, [])
                self.assertEqual(results[winner].status, "acknowledged")
                self.assertEqual(results["transfer" if winner == "business" else "business"].status, "rejected")
                instruction = target_instruction(self.fixture, self.profile, effect.expected_revisions)
                self.assertEqual(self.world.deliver_target_acceptance(instruction), winner == "transfer")
                self.assertEqual(self.world.effect_count("reschedule"), winner == "business")
                self.assertEqual(self.world.effect_count("transfer_owner"), winner == "transfer")

    def test_pending_and_accepted_history_are_durable_without_new_effect(self):
        effect = self.source()
        self.assertEqual(self.port.transfer_owner(effect, auth=self.owner).status, "acknowledged")
        instruction = target_instruction(self.fixture, self.profile, effect.expected_revisions)
        self.clock.advance(2)
        self.assertTrue(self.world.deliver_target_acceptance(instruction))
        self.clock.advance(3)
        self.world = SimulatedWorld(self.db, self.fixture_path, profile=self.profile, clock=self.clock)
        self.port = self.world.bundle().operator
        with sqlite3.connect(self.db) as connection:
            record = json.loads(connection.execute("SELECT value FROM metadata WHERE key LIKE 'ownership_original:%'").fetchone()[0])
        self.assertEqual([item["kind"] for item in record["history"]], ["transfer_pending_v1", "transfer_accepted_v1"])
        self.assertEqual(record["receipt"], record["history"][-1])
        self.assertEqual(record["history"][0]["pending_state_revision"], record["receipt"]["pending_state_revision"])
        self.assertEqual(self.receipt(effect)[1].provider_at, NOW + timedelta(seconds=2))
        self.assertEqual(self.world.effect_count("transfer_owner"), 1)
        self.assertEqual(self.read(caller="OP2", proof="synthetic-target-proof", facts=["ownership_grant"]).observations, [])
        self.assertEqual(self.read(facts=["ownership_grant"]).observations, [])

    def test_builtin_fixture_is_exact_typed_source_setup_not_native_authority(self):
        path = ROOT / "fixtures/development/ownership-world-v1.json"
        self.assertTrue(path.is_file(), "Explicit immutable source fixture is missing")
        raw = json.loads(path.read_text())
        self.assertEqual(raw, synthetic_fixture(self.profile))
        world = SimulatedWorld(self.db, path, profile=self.profile, clock=self.clock)
        effect = effect_for(raw, self.profile, world.material_revisions())
        self.assertEqual(world.bundle().operator.transfer_owner(effect, auth=self.owner).status, "acknowledged")
        self.assertEqual(world.effect_count("transfer_owner"), 1)
