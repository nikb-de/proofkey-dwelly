"""Independent synthetic provider controls and original outcome assertions."""
import copy
import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from proofkey.adapters.world import SimulatedWorld
from proofkey.contracts import ReadRequest, ReadTarget
from proofkey.identity import fingerprint
from proofkey.profiles import load_profile
from proofkey.verifier import verify
from support import NOW, DEADLINE, FakeClock, make_binding, make_intent

ROOT = Path(__file__).resolve().parents[1]


def content_for(fixture, profile):
    facts = fixture["facts"]
    values = {key: item["value"] for key, item in facts.items()}
    return {"version": "packet-content-v1", "source": {
        "binding": make_binding().model_dump(mode="json"), "packet_id": "P1",
        "packet_revision": values["operator.packet_revision"], "packet_hash": values["operator.packet_hash"],
        "observations": [{"identity": key, "revision": facts[key]["revision"],
                          "evidence_ref": facts[key]["evidence_ref"]} for key in
                         ["operator.packet_hash", "operator.packet_revision", "operator.recipient",
                          "operator.packet_catalog", "operator.packet_access", "ownership.owner",
                          "ownership.state", "ownership.state_revision", "ownership.epoch"]],
        "recipient": "OP1", "owner": "U1", "owner_state": "accepted", "state_revision": "v1", "epoch": 0},
        "catalog": copy.deepcopy(values["operator.packet_catalog"]),
        "access": copy.deepcopy(values["operator.packet_access"]), "as_of": NOW.isoformat(),
        "history": [{"binding": make_binding(generation="G0").model_dump(mode="json"),
                     "action_id": "prior-action", "provider_key": "prior-key", "argument_fingerprint": "a" * 64,
                     "operation": "send_status", "stage": "send", "profile_version": "v1.2",
                     "process_version": "v1", "policy_version": "v1", "dispatch_state": "acknowledged",
                     "verification_state": "outcome_unknown", "as_of": NOW.isoformat(),
                     "evidence_refs": ["synthetic:prior"], "unresolved": True}],
        "generation_stops": [], "policy": {"profile_id": profile.profile_id,
        "profile_version": profile.version, "profile_hash": profile.release_hash, "process_version": "v1",
        "process_hash": profile.process_hash, "policy_id": "synthetic-test-policy-v1",
        "policy_hash": profile.policy_hash, "observed_version": "v1", "references": ["synthetic-test-policy-v1"]},
        "conflicts": [], "unknowns": [], "disposition": "review_facts", "expires_at": DEADLINE.isoformat()}


class PacketSourceTests(unittest.TestCase):
    def setUp(self):
        try:
            self.profile = load_profile("flat-v1.3")
        except ValueError:
            self.fail("Registered v1.3 packet source capability is missing")
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.db = Path(self.folder.name) / "world.sqlite"
        self.fixture_path = ROOT / "fixtures/development/packet-world-v1.json"
        self.fixture = json.loads(self.fixture_path.read_text())
        self.clock = FakeClock()
        self.world = SimulatedWorld(self.db, self.fixture_path, profile=self.profile, clock=self.clock)
        self.port = self.world.bundle().operator
        self.content = content_for(self.fixture, self.profile)

    def intent(self, content=None, **overrides):
        from proofkey.packet_contracts import PacketContentV1, packet_postcondition
        data = PacketContentV1.model_validate(content or self.content).model_dump(mode="json")
        args = {"packet_id": "P1", "packet_revision": "v1", "packet_hash": "b" * 64,
                "recipient": "OP1", "packet_contract": "packet-content-v1", "content_hash": fingerprint(data), "content": data}
        intent = make_intent(operation="enqueue_handoff", stage="enqueue", arguments=args,
            profile_version="v1.3", expected_revisions=self.world.material_revisions(),
            postcondition=packet_postcondition(args), ownership_state_revision="v1", ownership_epoch=0)
        return intent.model_copy(update=overrides)

    def read(self, intent=None, *, caller="U1", proof="synthetic-proof", facts=None):
        target = (ReadTarget(kind="authority_facts", authority="operator", facts=facts) if facts else
                  ReadTarget(kind="original_effect", operation=intent.operation, generation=intent.binding.generation,
                             action_id=intent.action_id, provider_key=intent.provider_key, fingerprint=intent.argument_fingerprint))
        return self.port.read_receipt(ReadRequest(case_id="C1", object_id="O1", caller_id=caller,
            proof_reference=proof, purpose="operator_packet" if facts else "reconcile", deadline=DEADLINE, target=target))

    def test_real_store_receipt_proves_digest_and_keeps_owner_pending(self):
        intent = self.intent()
        self.assertEqual(self.port.enqueue_handoff(intent).status, "acknowledged")
        with sqlite3.connect(self.db) as connection:
            stored = json.loads(connection.execute("SELECT observations FROM effects").fetchone()[0])
        contents = next(item["value"] for item in stored if item["fact"] == "packet_content")
        digest = hashlib.sha256(json.dumps(contents, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
        self.assertEqual(digest, intent.arguments["content_hash"])
        self.assertEqual(contents["history"][0]["binding"]["generation"], "G0")
        read = self.read(intent)
        self.assertNotIn("packet_content", [obs.fact for obs in read.observations])
        receipt = next(obs.value for obs in read.observations if obs.fact == "packet_content_receipt")
        self.assertEqual(receipt["owner_status"], "pending")
        self.assertEqual(receipt["argument_fingerprint"], intent.argument_fingerprint)
        self.assertEqual(verify(intent, read, profile=self.profile).status, "verified")

    def test_current_authenticated_sources_require_explicit_scope(self):
        self.assertEqual(len(self.read(facts=["packet_catalog", "packet_access"]).observations), 2)
        for caller, proof in [("OP1", "synthetic-operator-proof"), ("OTHER", "synthetic-proof"), ("U1", "bad")]:
            self.assertEqual(self.read(caller=caller, proof=proof, facts=["packet_catalog"]).observations, [])

    def test_rehashed_missing_original_or_forged_access_cannot_mint_permission(self):
        for edit in [lambda c: c["catalog"]["originals"].clear(),
                     lambda c: c["access"].update(decision_id="forged-grant"),
                     lambda c: c["access"].update(sender="OP1"),
                     lambda c: c["catalog"]["originals"][0].update(source_handle="file:/private"),
                     lambda c: c["source"].update(recipient="OP2"),
                     lambda c: c["policy"].update(policy_id="caller-granted")]:
            data = copy.deepcopy(self.content)
            edit(data)
            try:
                intent = self.intent(data)
            except ValueError:
                continue
            self.assertEqual(self.port.enqueue_handoff(intent).status, "rejected")
        self.assertEqual(self.world.effect_count("enqueue_handoff"), 0)

    def test_current_catalog_recipient_access_and_owner_races_store_nothing(self):
        for key, value in [("operator.packet_catalog", {**self.content["catalog"], "revision": "v2"}),
                           ("operator.packet_access", {**self.content["access"], "revision": "v2"}),
                           ("operator.recipient", "OP2"), ("ownership.state", "transfer_pending"),
                           ("ownership.owner", "OP2")]:
            with self.subTest(key=key):
                intent = self.intent()
                old = self.fixture["facts"][key]["value"]
                self.world.mutate(key, value)
                self.assertEqual(self.port.enqueue_handoff(intent).status, "rejected")
                self.assertEqual(self.world.effect_count("enqueue_handoff"), 0)
                self.world.mutate(key, old)

    def test_expired_revoked_and_incomplete_sources_disclose_nothing(self):
        for edit in [{"expires_at": NOW.isoformat()}, {"permitted_originals": []}]:
            self.world.mutate("operator.packet_access", {**self.content["access"], **edit})
            self.assertEqual(self.read(facts=["packet_catalog", "packet_access"]).observations, [])
        self.world.mutate("operator.packet_access", self.content["access"])
        self.world.mutate("operator.packet_catalog", {**self.content["catalog"], "complete": False})
        self.assertEqual(self.read(facts=["packet_catalog"]).observations, [])

    def test_same_key_changed_content_conflicts_and_timeout_reconciles_original(self):
        intent = self.intent()
        self.world.set_fault("enqueue_handoff", "timeout_after")
        self.assertEqual(self.port.enqueue_handoff(intent).status, "outcome_unknown")
        changed = copy.deepcopy(self.content)
        changed["disposition"] = "refund_review"
        self.assertEqual(self.port.enqueue_handoff(self.intent(changed)).reason, "idempotency_conflict")
        restored = SimulatedWorld(self.db, self.fixture_path, profile=self.profile, clock=self.clock)
        self.port = restored.bundle().operator
        self.assertEqual(verify(intent, self.read(intent), profile=self.profile).status, "verified")
        self.assertEqual(restored.effect_count("enqueue_handoff"), 1)

    def test_queue_only_readback_is_unknown_and_digest_conflict_is_conflict(self):
        intent = self.intent()
        self.port.enqueue_handoff(intent)
        read = self.read(intent)
        queue = read.model_copy(update={"observations": [obs for obs in read.observations if obs.fact != "packet_content_receipt"]})
        self.assertEqual(verify(intent, queue, profile=self.profile).status, "outcome_unknown")
        observations = [obs.model_copy(update={"value": {**obs.value, "content_hash": "0" * 64}})
                        if obs.fact == "packet_content_receipt" else obs for obs in read.observations]
        self.assertEqual(verify(intent, read.model_copy(update={"observations": observations}), profile=self.profile).status, "conflict")

    def test_revoked_current_access_denies_original_receipt(self):
        intent = self.intent()
        self.port.enqueue_handoff(intent)
        self.world.mutate("operator.packet_access", {**self.content["access"], "permitted_originals": []})
        self.assertEqual(self.read(intent).observations, [])

    def test_restored_current_source_grant_is_readable_with_new_observation_revision(self):
        self.world.mutate("operator.packet_access", {**self.content["access"], "permitted_originals": []})
        self.world.mutate("operator.packet_access", self.content["access"])
        read = self.read(facts=["packet_catalog", "packet_access"])
        self.assertEqual(len(read.observations), 2)
        self.assertEqual(next(obs.revision for obs in read.observations if obs.fact == "packet_access"), "v3")

    def test_missing_source_observation_refs_cannot_pass_policy_gate(self):
        from proofkey.policy import PolicyGate
        from proofkey.contracts import ActionProposal, AuthorityObservation
        from support import make_request, make_checkpoint
        content = copy.deepcopy(self.content)
        content["source"]["observations"] = []
        intent = self.intent(content)
        observations = [AuthorityObservation(authority=key.partition(".")[0], fact=key.partition(".")[2],
            object_id="O1", value=item["value"], revision=item["revision"], observed_at=NOW,
            provider_at=NOW, evidence_ref=item["evidence_ref"]) for key, item in self.fixture["facts"].items()]
        checkpoint = make_checkpoint(phase="intake", profile_version="v1.3", ownership_state="accepted",
            ownership_state_revision="v1", ownership_epoch=0)
        allowed = PolicyGate(self.profile).evaluate(make_request(), ActionProposal(operation="enqueue_handoff",
            stage="enqueue", arguments=self.intent().arguments, evidence_refs=[]), observations, checkpoint)
        self.assertTrue(allowed.allowed)
        decision = PolicyGate(self.profile).evaluate(make_request(), ActionProposal(operation="enqueue_handoff",
            stage="enqueue", arguments=intent.arguments, evidence_refs=[]), observations, checkpoint)
        self.assertFalse(decision.allowed)

    def test_plain_body_marker_does_not_upgrade_legacy_verifier(self):
        intent = self.intent()
        self.port.enqueue_handoff(intent)
        self.assertNotEqual(verify(intent, self.read(intent)).status, "verified")

    def test_provider_requires_exact_original_postcondition(self):
        intent = self.intent(postcondition={"packet_id": "P1"})
        self.assertEqual(self.port.enqueue_handoff(intent).status, "rejected")
        self.assertEqual(self.world.effect_count("enqueue_handoff"), 0)

    def test_malformed_missing_extra_or_edited_argument_commitments_store_nothing(self):
        intent = self.intent()
        for edit in [lambda a: a.update(content_hash="0" * 64),
                     lambda a: a.update(packet_hash="0" * 64),
                     lambda a: a.update(authorized=True),
                     lambda a: a.pop("content"),
                     lambda a: a["content"].update(disposition="refund_review"),
                     lambda a: a["content"]["access"].update(role="reader"),
                     lambda a: a["content"]["access"].pop("expires_at"),
                     lambda a: a["content"]["catalog"]["originals"].append(
                         {**a["content"]["catalog"]["originals"][0], "artifact_id": "foreign"})]:
            args = intent.model_dump(mode="json")["arguments"]
            edit(args)
            changed = intent.model_copy(update={"arguments": args, "argument_fingerprint": fingerprint(args)})
            self.assertEqual(self.port.enqueue_handoff(changed).status, "rejected")
        self.assertEqual(self.world.effect_count("enqueue_handoff"), 0)

    def test_empty_certified_source_inventory_is_valid_but_missing_grant_is_denied(self):
        raw = copy.deepcopy(self.fixture)
        catalog = raw["facts"]["operator.packet_catalog"]["value"]
        catalog["originals"] = []
        catalog["extracts"] = []
        access = raw["facts"]["operator.packet_access"]["value"]
        access["permitted_originals"] = []
        access["permitted_extracts"] = []
        access["catalog_hash"] = fingerprint(catalog)
        fixture = Path(self.folder.name) / "empty-world.json"
        fixture.write_text(json.dumps(raw))
        world = SimulatedWorld(Path(self.folder.name) / "empty.sqlite", fixture, profile=self.profile, clock=self.clock)
        self.world, self.port, self.content = world, world.bundle().operator, content_for(raw, self.profile)
        self.assertEqual(self.port.enqueue_handoff(self.intent()).status, "acknowledged")
        missing = SimulatedWorld(Path(self.folder.name) / "missing.sqlite", ROOT / "fixtures/development/world.json",
                                 profile=self.profile, clock=self.clock)
        self.port = missing.bundle().operator
        self.assertEqual(self.read(facts=["packet_catalog", "packet_access"]).observations, [])

    def test_queue_owner_fault_never_becomes_content_acceptance(self):
        self.world.set_fault("enqueue_handoff", "owner_accepted")
        intent = self.intent()
        self.assertEqual(self.port.enqueue_handoff(intent).status, "acknowledged")
        read = self.read(intent)
        receipt = next(obs.value for obs in read.observations if obs.fact == "packet_content_receipt")
        self.assertEqual(receipt["owner_status"], "pending")
        claimed = [obs.model_copy(update={"value": {**obs.value, "owner_status": "accepted"}})
                   if obs.fact == "packet_content_receipt" else obs for obs in read.observations]
        self.assertEqual(verify(intent, read.model_copy(update={"observations": claimed}), profile=self.profile).status, "conflict")

    def test_saved_frozen_profile_mismatch_cannot_verify_original_digest(self):
        intent = self.intent()
        self.port.enqueue_handoff(intent)
        mismatched = intent.model_copy(update={"profile_version": "v1.2"})
        self.assertEqual(verify(mismatched, self.read(intent), profile=self.profile).status, "conflict")

    def test_policy_uses_current_observation_time_for_expiry(self):
        from proofkey.policy import PolicyGate
        from proofkey.contracts import ActionProposal, AuthorityObservation
        from support import make_request, make_checkpoint
        intent = self.intent()
        checkpoint = make_checkpoint(phase="intake", profile_version="v1.3", ownership_state="accepted",
            ownership_state_revision="v1", ownership_epoch=0)
        observations = [AuthorityObservation(authority=key.partition(".")[0], fact=key.partition(".")[2],
            object_id="O1", value=item["value"], revision=item["revision"], observed_at=DEADLINE,
            provider_at=DEADLINE, evidence_ref=item["evidence_ref"]) for key, item in self.fixture["facts"].items()]
        result = PolicyGate(self.profile).evaluate(make_request(), ActionProposal(operation="enqueue_handoff",
            stage="enqueue", arguments=intent.arguments, evidence_refs=[]), observations, checkpoint)
        self.assertFalse(result.allowed)

    def test_legacy_profile_reopen_cannot_disclose_content_bearing_original(self):
        intent = self.intent()
        self.assertEqual(self.port.enqueue_handoff(intent).status, "acknowledged")
        self.assertEqual(self.read(intent, caller="OP1", proof="synthetic-operator-proof").observations, [])
        for name in ["flat-v1", "flat-v1.1", "flat-v1.2", "nested-v1.2"]:
            with self.subTest(profile=name):
                self.clock.advance(1)  # Respect the shared synthetic read-rate budget.
                reopened = SimulatedWorld(self.db, self.fixture_path, profile=load_profile(name), clock=self.clock)
                self.port = reopened.bundle().operator
                denied = self.read(intent, caller="OP1", proof="synthetic-operator-proof")
                self.assertEqual(denied.observations, [])
                allowed = self.read(intent)
                self.assertNotIn("packet_content", [obs.fact for obs in allowed.observations])
                self.assertIn("packet_content_receipt", [obs.fact for obs in allowed.observations])
                packet_target = ReadTarget(kind="operator_packet", packet_id="P1", packet_revision="v1")
                for method in [self.port.read_receipt, self.port.read_resume]:
                    read = method(ReadRequest(case_id="C1", object_id="O1", caller_id="OP1",
                        proof_reference="synthetic-operator-proof", purpose="reconcile", deadline=DEADLINE, target=packet_target))
                    self.assertEqual(read.observations, [])

    def test_legacy_reopen_keeps_revoked_content_receipt_private(self):
        intent = self.intent()
        self.assertEqual(self.port.enqueue_handoff(intent).status, "acknowledged")
        self.world.mutate("operator.packet_access", {**self.content["access"], "permitted_originals": []})
        reopened = SimulatedWorld(self.db, self.fixture_path, profile=load_profile("flat-v1.2"), clock=self.clock)
        self.port = reopened.bundle().operator
        self.assertEqual(self.read(intent).observations, [])

    def test_genuine_legacy_metadata_only_original_keeps_legacy_read_semantics(self):
        legacy = load_profile("flat-v1.2")
        world = SimulatedWorld(Path(self.folder.name) / "legacy.sqlite", ROOT / "fixtures/development/world.json",
                               profile=legacy, clock=self.clock)
        self.port = world.bundle().operator
        args = {"packet_id": "P1", "packet_revision": "v1", "packet_hash": "packet-hash", "recipient": "OP1"}
        intent = make_intent(operation="enqueue_handoff", stage="enqueue", arguments=args, profile_version="v1.2",
            expected_revisions=world.material_revisions(), postcondition={"packet_id": "P1", "packet_revision": "v1",
                "packet_hash": "packet-hash", "operator.handoff_disposition": "pending"})
        self.assertEqual(self.port.enqueue_handoff(intent).status, "acknowledged")
        read = self.read(intent, caller="OP1", proof="synthetic-operator-proof")
        self.assertEqual(len(read.observations), 4)
        self.assertEqual(verify(intent, read).status, "verified")

    def test_advancing_clock_uses_one_original_receipt_observation_timestamp(self):
        class AdvancingClock(FakeClock):
            def now(self):
                current = super().now()
                self.advance(0.000001)
                return current

        self.clock = AdvancingClock()
        self.db = Path(self.folder.name) / "advancing.sqlite"
        self.world = SimulatedWorld(self.db, self.fixture_path,
                                    profile=self.profile, clock=self.clock)
        self.port = self.world.bundle().operator
        intent = self.intent()
        self.assertEqual(self.port.enqueue_handoff(intent).status, "acknowledged")
        with sqlite3.connect(self.db) as connection:
            stored = json.loads(connection.execute("SELECT observations FROM effects").fetchone()[0])
        observation = next(item for item in stored if item["fact"] == "packet_content_receipt")
        self.assertEqual(observation["value"]["stored_at"], observation["provider_at"])
        self.assertEqual(observation["observed_at"], observation["provider_at"])
        read = self.read(intent)
        self.assertEqual(verify(intent, read, profile=self.profile).status, "verified")
        receipt = next(obs for obs in read.observations if obs.fact == "packet_content_receipt")
        self.assertLess(receipt.provider_at, read.as_of)
