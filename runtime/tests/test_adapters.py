"""Real provider SQLite tests; driver controls are not runtime tools."""
import json
import sqlite3
import os
import subprocess
import sys
import textwrap
from contextlib import contextmanager
from datetime import timedelta
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from pydantic import ValidationError

from proofkey.contracts import ReadRequest, ReadTarget, RevisionVector
from support import DEADLINE, FakeClock, make_binding, make_intent, load_test_profile

try:
    from proofkey.adapters.world import SimulatedWorld
except ModuleNotFoundError:
    SimulatedWorld = None

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/development/world.json"


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(SimulatedWorld, "six scoped provider adapters are missing")
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.clock = FakeClock()
        self.world = SimulatedWorld(Path(self.folder.name) / "world.sqlite", FIXTURE, clock=self.clock)
        self.bundle = self.world.bundle()
        self._fresh_count = 0

    def fresh_world(self):
        self._fresh_count += 1
        self.clock = FakeClock()
        self.world = SimulatedWorld(Path(self.folder.name) / f"world-{self._fresh_count}.sqlite", FIXTURE, clock=self.clock)
        self.bundle = self.world.bundle()

    def intent(self, operation="reschedule", **overrides):
        arguments = {
            "reschedule": {"slot": "S1"},
            "register_goods_refusal": {"inventory": {"item-1": 1}},
            "register_service_refusal": {"scope": "service"},
            "create_return": {"inventory": {"item-1": 1}, "destination": "D1"},
            "send_clarification": {"question_id": "Q1", "recipient": "U1", "text": "Which slot?"},
            "send_status": {"recipient": "U1", "text": "Saved"},
            "enqueue_handoff": {"packet_id": "P1", "packet_revision": "v1", "packet_hash": "packet-hash", "recipient": "OP1"},
            "transfer_owner": {"transfer_id": "T1", "packet_id": "P1", "packet_revision": "v1", "packet_hash": "packet-hash", "target_owner": "OP2"},
        }[operation]
        return make_intent(operation=operation, arguments=arguments,
                           expected_revisions=self.world.material_revisions(), **overrides)

    def dispatch(self, intent):
        port = {"reschedule": "scheduling", "register_goods_refusal": "delivery",
                "register_service_refusal": "delivery", "create_return": "returns",
                "send_clarification": "messaging", "send_status": "messaging",
                "enqueue_handoff": "operator", "transfer_owner": "operator"}[intent.operation]
        return getattr(getattr(self.bundle, port), intent.operation)(intent)

    def read(self, method, target, **overrides):
        port = {"read_case": "case", "read_principal": "case", "read_delivery": "delivery",
                "read_refusal": "delivery", "list_permitted_slots": "scheduling", "read_schedule": "scheduling",
                "read_return_policy": "returns", "read_return": "returns", "read_message": "messaging",
                "read_receipt": "operator", "read_resume": "operator", "read_owner": "operator"}[method]
        request = ReadRequest(case_id="C1", object_id="O1", caller_id="U1", proof_reference="synthetic-proof",
                              purpose="reconcile", deadline=DEADLINE, target=target, **overrides)
        return getattr(getattr(self.bundle, port), method)(request)

    @staticmethod
    def original(intent):
        return ReadTarget(kind="original_effect", operation=intent.operation, generation=intent.binding.generation,
                          action_id=intent.action_id, provider_key=intent.provider_key, fingerprint=intent.argument_fingerprint)

    def test_material_races_fence_effect_atomically(self):
        for fact in ["case.binding", "case.request_revision", "case.authorization", "case.generation",
                     "customer.consent", "customer.consent_revision", "delivery.risk", "delivery.stage",
                     "scheduling.capacity", "scheduling.slot", "delivery.status", "policy.version",
                     "ownership.state_revision"]:
            with self.subTest(fact=fact):
                self.fresh_world()
                intent = self.intent()
                self.world.mutate(fact, "changed")
                result = self.dispatch(intent)
                self.assertEqual(result.status, "rejected")
                self.assertIn(result.reason, {"stale_material_revision", "identity_scope_rejected"})
                self.assertEqual(self.world.effect_count("reschedule"), 0)

    def test_missing_and_wrong_authority_revisions_cannot_select_protection(self):
        for key in ["customer.consent", "delivery.risk", "ownership.state_revision"]:
            vector = dict(self.world.material_revisions().revisions)
            value = vector.pop(key)
            vector["forged." + key.partition(".")[2]] = value
            intent = make_intent(expected_revisions=RevisionVector(revisions=vector))
            self.assertEqual(self.dispatch(intent).status, "rejected")
        self.assertEqual(self.world.effect_count("reschedule"), 0)

    def test_goods_quantity_inventory_destination_and_pending_ownership_races(self):
        for operation, fact in [("register_goods_refusal", "goods.inventory"), ("register_goods_refusal", "goods.quantity"),
                                ("create_return", "returns.destination"), ("transfer_owner", "ownership.state"),
                                ("transfer_owner", "ownership.epoch"), ("transfer_owner", "ownership.owner")]:
            with self.subTest(operation=operation, fact=fact):
                self.fresh_world()
                intent = self.intent(operation)
                self.world.mutate(fact, "changed")
                result = self.dispatch(intent)
                self.assertEqual(result.status, "rejected")
                self.assertEqual(result.reason, "stale_material_revision")
                self.assertEqual(self.world.effect_count(operation), 0)

    def test_all_six_ports_return_typed_scoped_facts(self):
        for method, authority, fact in [("read_case", "case", "binding"), ("read_principal", "customer", "consent"),
                                        ("read_delivery", "delivery", "status"), ("list_permitted_slots", "scheduling", "capacity"),
                                        ("read_return_policy", "returns", "destination"), ("read_owner", "ownership", "owner")]:
            reply = self.read(method, ReadTarget(kind="authority_facts", authority=authority, facts=[fact]))
            self.assertEqual(reply.object_id, "O1")
            self.assertEqual(len(reply.observations), 1)
            self.assertEqual(reply.observations[0].authority, authority)
            self.assertEqual(reply.observations[0].revision, "v1")

    def test_acl_wrong_object_wrong_proof_and_cross_port_scope_leak_no_facts(self):
        target = ReadTarget(kind="authority_facts", authority="case", facts=["binding"])
        for change in [{"object_id": "OTHER"}, {"case_id": "OTHER"}, {"caller_id": "OTHER"}, {"proof_reference": "bad"}]:
            data = dict(case_id="C1", object_id="O1", caller_id="U1", proof_reference="synthetic-proof",
                        purpose="inspect", deadline=DEADLINE, target=target)
            reply = self.bundle.case.read_case(ReadRequest(**{**data, **change}))
            self.assertEqual(reply.observations, [])
            self.assertIsNone(reply.provider_request_id)
        self.assertEqual(self.read("read_message", target).observations, [])

    def test_provider_business_rejection_does_not_register_effect(self):
        self.world.set_fault("reschedule", "business_rejection")
        reply = self.dispatch(self.intent())
        self.assertEqual(reply.status, "rejected")
        self.assertEqual(self.world.effect_count("reschedule"), 0)

    def legacy_world_with_packet_revision(self, revision):
        self._fresh_count += 1
        root = Path(self.folder.name) / f"optional-revision-{self._fresh_count}"
        root.mkdir()
        fixture = json.loads(FIXTURE.read_text())
        fixture["facts"]["operator.packet_id"] = {
            "case_id": "C1", "object_id": "O1", "value": "P1", "revision": revision,
            "evidence_ref": "synthetic-provider:operator.packet_id",
        }
        fixture_path = root / "fixture.json"
        fixture_path.write_text(json.dumps(fixture))
        self.clock = FakeClock()
        database = root / "world.sqlite"
        self.world = SimulatedWorld(database, fixture_path, clock=self.clock)
        self.bundle = self.world.bundle()
        return database

    @staticmethod
    def legacy_dispatch_snapshot(database):
        with sqlite3.connect(database) as connection:
            return (
                connection.execute("SELECT * FROM facts ORDER BY case_id,object_id,identity").fetchall(),
                connection.execute("SELECT COUNT(*) FROM effects").fetchone()[0],
                connection.execute("SELECT COUNT(*) FROM final_rejections").fetchone()[0],
            )

    def test_invalid_optional_observation_revision_rolls_back_legacy_dispatch(self):
        for operation in ("enqueue_handoff", "transfer_owner"):
            for revision in ("", " \t "):
                with self.subTest(operation=operation, revision=revision):
                    database = self.legacy_world_with_packet_revision(revision)
                    self.world.set_fault("transfer_owner", "owner_accepted")
                    intent = self.intent(operation)
                    self.assertNotIn("operator.packet_id", intent.expected_revisions.revisions)
                    before, effects, rejections = self.legacy_dispatch_snapshot(database)
                    self.assertEqual((effects, rejections), (0, 0))
                    with self.assertRaises(ValidationError) as raised:
                        self.dispatch(intent)
                    self.assertEqual([error["loc"] for error in raised.exception.errors()], [("revision",)])
                    after, effects, rejections = self.legacy_dispatch_snapshot(database)
                    self.assertEqual(after, before)
                    self.assertEqual((effects, rejections), (0, 0))

    def test_valid_optional_observation_revision_preserves_legacy_original(self):
        for operation, read_method, stage in (
                ("enqueue_handoff", "read_receipt", "queued"),
                ("transfer_owner", "read_owner", "accepted")):
            with self.subTest(operation=operation):
                database = self.legacy_world_with_packet_revision("v1")
                self.world.set_fault("transfer_owner", "owner_accepted")
                intent = self.intent(operation)
                self.assertNotIn("operator.packet_id", intent.expected_revisions.revisions)
                before, effects, rejections = self.legacy_dispatch_snapshot(database)
                self.assertEqual((effects, rejections), (0, 0))
                self.assertEqual(self.dispatch(intent).status, "acknowledged")
                after, effects, rejections = self.legacy_dispatch_snapshot(database)
                self.assertEqual((effects, rejections), (1, 0))
                original = self.read(read_method, self.original(intent))
                self.assertEqual(original.action_id, intent.action_id)
                self.assertEqual(original.stage, stage)
                packet = next(item for item in original.observations
                              if item.authority == "operator" and item.fact == "packet_id")
                self.assertEqual((packet.value, packet.revision), ("P1", "v1"))
                if operation == "enqueue_handoff":
                    self.assertEqual(after, before)
                else:
                    before_by_fact = {row[2]: (json.loads(row[3]), row[4]) for row in before}
                    after_by_fact = {row[2]: (json.loads(row[3]), row[4]) for row in after}
                    for fact, old, new in (
                            ("ownership.state", ("accepted", "v1"), ("accepted", "v2")),
                            ("ownership.state_revision", ("v1", "v1"), ("v2", "v2")),
                            ("ownership.owner", ("U1", "v1"), ("OP2", "v2")),
                            ("ownership.epoch", (0, "v1"), (1, "v2"))):
                        self.assertEqual(before_by_fact[fact], old)
                        self.assertEqual(after_by_fact[fact], new)

    def test_timeout_after_commit_preserves_original_readback_without_resend(self):
        intent = self.intent()
        self.world.set_fault("reschedule", "timeout_after")
        self.assertEqual(self.dispatch(intent).status, "outcome_unknown")
        reply = self.read("read_schedule", self.original(intent))
        self.assertEqual(reply.action_id, intent.action_id)
        self.assertEqual(reply.fingerprint, intent.argument_fingerprint)
        self.assertEqual(reply.stage, "committed")
        self.assertEqual(self.world.effect_count("reschedule"), 1)

    def test_original_read_requires_all_identity_fields_and_never_latest(self):
        first = self.intent()
        self.assertEqual(self.dispatch(first).status, "acknowledged")
        second = self.intent(binding=make_binding(generation="G2"))
        self.world.mutate("case.generation", "G2")
        second = self.intent(binding=second.binding)
        self.assertEqual(self.dispatch(second).status, "acknowledged")
        for intent in [first, second]:
            self.assertEqual(self.read("read_schedule", self.original(intent)).action_id, intent.action_id)
        target = self.original(first).model_dump()
        for field, value in [("generation", "G9"), ("action_id", "wrong"), ("provider_key", "wrong"), ("fingerprint", "0" * 64)]:
            reply = self.read("read_schedule", ReadTarget(**{**target, field: value}))
            self.assertEqual(reply.observations, [])
            self.assertIsNone(reply.action_id)
        self.assertEqual(self.read("read_schedule", ReadTarget(kind="authority_facts", authority="scheduling", facts=["slot"])).action_id, None)

    def test_same_key_different_arguments_conflicts_and_same_intent_deduplicates(self):
        first = self.intent()
        self.assertEqual(self.dispatch(first).status, "acknowledged")
        self.assertEqual(self.dispatch(first).status, "acknowledged")
        conflict = make_intent(arguments={"slot": "S2"}, expected_revisions=self.world.material_revisions())
        self.assertEqual(self.dispatch(conflict).status, "rejected")
        self.assertEqual(self.world.effect_count("reschedule"), 1)

    def test_refusal_and_return_are_separate_without_private_compensation(self):
        refusal = self.intent("register_goods_refusal")
        self.assertEqual(self.dispatch(refusal).status, "acknowledged")
        self.world.set_fault("create_return", "business_rejection")
        self.assertEqual(self.dispatch(self.intent("create_return")).status, "rejected")
        self.assertEqual(self.world.effect_count("register_goods_refusal"), 1)
        self.assertEqual(self.world.effect_count("create_return"), 0)
        self.assertEqual([call.operation for call in self.world.calls], ["register_goods_refusal", "create_return"])
        self.assertEqual(self.read("read_refusal", self.original(refusal)).stage, "committed")

    def test_message_sent_and_queue_ack_are_not_delivery_or_owner_acceptance(self):
        message = self.intent("send_status")
        handoff = self.intent("enqueue_handoff")
        self.assertEqual(self.dispatch(message).status, "acknowledged")
        self.assertEqual(self.dispatch(handoff).status, "acknowledged")
        values = {obs.fact: obs.value for obs in self.read("read_message", self.original(message)).observations}
        self.assertEqual(values["status"], "sent")
        queue = {obs.fact: obs.value for obs in self.read("read_receipt", self.original(handoff)).observations}
        self.assertEqual(queue["handoff_disposition"], "pending")
        self.assertNotIn("accepted", queue.values())

    def test_question_packet_and_transfer_selectors_preserve_multiple_records(self):
        q1 = self.intent("send_clarification")
        self.dispatch(q1)
        q2 = self.intent("send_clarification", binding=make_binding(generation="G2"))
        self.world.mutate("case.generation", "G2")
        q2 = make_intent(binding=q2.binding, operation="send_clarification", arguments={"question_id": "Q2", "recipient": "U1", "text": "Other?"}, expected_revisions=self.world.material_revisions())
        self.dispatch(q2)
        for question in ["Q1", "Q2"]:
            reply = self.read("read_message", ReadTarget(kind="question", question_id=question))
            self.assertEqual({o.fact: o.value for o in reply.observations}["question_id"], question)
        self.assertEqual(self.read("read_message", ReadTarget(kind="question", question_id="absent")).observations, [])

    def test_shared_rate_pressure_and_cooldown_span_ports(self):
        self.world.set_fault("reschedule", "429")
        self.assertEqual(self.dispatch(self.intent()).status, "rejected")
        self.assertEqual(self.dispatch(self.intent("send_status")).status, "rejected")
        self.assertEqual(self.world.effect_count("send_status"), 0)
        self.clock.advance(1)
        self.world.set_fault("reschedule", "none")
        self.assertEqual(self.dispatch(self.intent("send_status")).status, "acknowledged")

    def test_deadline_and_unknown_capability_fail_closed(self):
        self.clock.advance(7201)
        self.assertEqual(self.dispatch(self.intent()).status, "rejected")
        self.assertEqual(self.world.effect_count("reschedule"), 0)

    def test_unknown_read_contract_cannot_expose_authority_data(self):
        data = load_test_profile().model_dump()
        data["capabilities"]["read_authority"]["readback"]["status"] = "unknown"
        from proofkey.contracts import EnvironmentProfile
        world = SimulatedWorld(Path(self.folder.name) / "unknown.sqlite", FIXTURE,
                               profile=EnvironmentProfile.model_validate(data), clock=self.clock)
        request = ReadRequest(case_id="C1", object_id="O1", caller_id="U1", proof_reference="synthetic-proof",
                              purpose="inspect", deadline=DEADLINE,
                              target=ReadTarget(kind="authority_facts", authority="case", facts=["binding"]))
        self.assertEqual(world.bundle().case.read_case(request).observations, [])

    def test_unknown_physical_readback_guarantee_prevents_dispatch(self):
        data = load_test_profile().model_dump()
        data["capabilities"]["reschedule"]["readback"]["status"] = "unknown"
        from proofkey.contracts import EnvironmentProfile
        world = SimulatedWorld(Path(self.folder.name) / "unsupported.sqlite", FIXTURE,
                               profile=EnvironmentProfile.model_validate(data), clock=self.clock)
        self.assertEqual(world.bundle().scheduling.reschedule(self.intent()).status, "rejected")
        self.assertEqual(world.effect_count("reschedule"), 0)

    def test_transfer_selector_cannot_read_handoff_through_owner_read(self):
        handoff = self.intent("enqueue_handoff")
        self.assertEqual(self.dispatch(handoff).status, "acknowledged")
        packet = ReadTarget(kind="operator_packet", packet_id="P1", packet_revision="v1")
        self.assertEqual(self.read("read_owner", packet).observations, [])

    def test_delivery_service_and_return_have_independent_exact_readbacks(self):
        service = self.intent("register_service_refusal")
        self.assertEqual(self.dispatch(service).status, "acknowledged")
        self.assertEqual({o.authority + "." + o.fact: o.value for o in self.read("read_refusal", self.original(service)).observations},
                         {"service.refusal": "verified"})
        goods = self.intent("register_goods_refusal")
        self.assertEqual(self.dispatch(goods).status, "acknowledged")
        returned = self.intent("create_return")
        self.assertEqual(self.dispatch(returned).status, "acknowledged")
        reply = self.read("read_return", self.original(returned))
        self.assertEqual(reply.stage, "initiated")
        self.assertEqual({o.fact: o.value for o in reply.observations}["status"], "initiated")
        self.assertEqual(self.world.effect_count("register_service_refusal"), 1)
        self.assertEqual(self.world.effect_count("register_goods_refusal"), 1)
        self.assertEqual(self.world.effect_count("create_return"), 1)

    def test_wrong_object_readback_keeps_provider_conflict_visible(self):
        intent = self.intent()
        self.dispatch(intent)
        self.world.set_fault("read_schedule", "wrong_object")
        reply = self.read("read_schedule", self.original(intent))
        self.assertEqual(reply.object_id, "provider-other-object")
        self.assertTrue(all(o.object_id == "provider-other-object" for o in reply.observations))
        self.assertEqual(reply.action_id, intent.action_id)

    def test_pending_transfer_does_not_accept_target_or_increment_epoch(self):
        intent = self.intent("transfer_owner")
        self.assertEqual(self.dispatch(intent).status, "acknowledged")
        target = ReadTarget(kind="transfer", transfer_id="T1", packet_id="P1", packet_revision="v1")
        reply = self.read("read_resume", target)
        values = {o.authority + "." + o.fact: o.value for o in reply.observations}
        self.assertEqual(reply.stage, "pending")
        self.assertEqual(values["ownership.owner"], "U1")
        self.assertEqual(values["ownership.epoch"], 0)
        self.assertEqual(values["ownership.state_revision"], "v2")
        self.assertEqual(self.read("read_owner", self.original(intent)).action_id, intent.action_id)
        self.assertEqual(self.dispatch(self.intent("send_status")).status, "rejected")

    def test_account_quota_and_rate_are_shared_across_reads_and_writes(self):
        target = ReadTarget(kind="authority_facts", authority="case", facts=["binding"])
        for _ in range(10):
            self.assertEqual(len(self.read("read_case", target).observations), 1)
        self.assertEqual(self.dispatch(self.intent("send_status")).status, "rejected")
        self.clock.advance(1)
        for _ in range(90):
            self.assertEqual(len(self.read("read_case", target).observations), 1)
            self.clock.advance(0.11)
        self.assertEqual(self.dispatch(self.intent("send_status")).status, "rejected")
        self.clock.advance(20)
        self.assertEqual(self.read("read_case", target).observations, [])
        self.assertEqual(self.world.effect_count("send_status"), 0)

    def test_shared_concurrency_slot_blocks_other_ports(self):
        # A real outstanding provider reservation in the shared SQLite ledger.
        with sqlite3.connect(Path(self.folder.name) / "world.sqlite") as connection:
            connection.execute("INSERT INTO pressure VALUES('synthetic-local-world',1,1,'[]',0)")
            connection.execute("INSERT INTO reservations VALUES('outstanding-provider-call','synthetic-local-world',?)",
                               (self.clock.now().timestamp() + 10,))
        self.assertEqual(self.dispatch(self.intent("send_status")).status, "rejected")
        target = ReadTarget(kind="authority_facts", authority="case", facts=["binding"])
        self.assertEqual(self.read("read_case", target).observations, [])
        self.assertEqual(self.world.effect_count("send_status"), 0)

    def test_reopen_preserves_effect_and_provider_deduplication(self):
        intent = self.intent()
        first = self.dispatch(intent)
        other = SimulatedWorld(Path(self.folder.name) / "world.sqlite", FIXTURE, clock=self.clock)
        second = other.bundle().scheduling.reschedule(intent)
        self.assertEqual(second.provider_request_id, first.provider_request_id)
        self.assertEqual(other.effect_count("reschedule"), 1)

    def test_original_transfer_records_survive_other_transfer_and_packet_reuse(self):
        self.world.set_fault("transfer_owner", "owner_accepted")
        first = self.intent("transfer_owner")
        self.assertEqual(self.dispatch(first).status, "acknowledged")
        self.world.mutate("case.generation", "G2")
        arguments = {"transfer_id": "T2", "packet_id": "P1", "packet_revision": "v1", "packet_hash": "packet-hash", "target_owner": "OP1"}
        second = make_intent(binding=make_binding(generation="G2"), operation="transfer_owner", arguments=arguments,
                             expected_revisions=self.world.material_revisions())
        self.assertEqual(self.dispatch(second).status, "acknowledged")
        for intent, owner, epoch in [(first, "OP2", 1), (second, "OP1", 2)]:
            original = self.read("read_owner", self.original(intent))
            self.assertEqual(original.action_id, intent.action_id)
            values = {o.authority + "." + o.fact: o.value for o in original.observations}
            self.assertEqual(values["ownership.owner"], owner)
            self.assertEqual(values["ownership.epoch"], epoch)
            transfer = ReadTarget(kind="transfer", transfer_id=intent.arguments["transfer_id"], packet_id="P1", packet_revision="v1")
            self.assertEqual(self.read("read_resume", transfer).action_id, intent.action_id)
        self.assertEqual(self.read("read_resume", ReadTarget(kind="transfer", transfer_id="T1", packet_id="P1", packet_revision="v9")).observations, [])

    def test_reused_question_and_packet_are_ambiguous_not_latest(self):
        first_message = self.intent("send_clarification")
        first_packet = self.intent("enqueue_handoff")
        self.dispatch(first_message)
        self.dispatch(first_packet)
        self.world.mutate("case.generation", "G2")
        binding = make_binding(generation="G2")
        second_message = self.intent("send_clarification", binding=binding)
        second_packet = self.intent("enqueue_handoff", binding=binding)
        self.dispatch(second_message)
        self.dispatch(second_packet)
        self.assertEqual(self.read("read_message", ReadTarget(kind="question", question_id="Q1")).observations, [])
        packet = ReadTarget(kind="operator_packet", packet_id="P1", packet_revision="v1")
        self.assertEqual(self.read("read_receipt", packet).observations, [])
        for intent in [first_message, second_message]:
            self.assertEqual(self.read("read_message", self.original(intent)).action_id, intent.action_id)
        self.clock.advance(1)
        for intent in [first_packet, second_packet]:
            self.assertEqual(self.read("read_receipt", self.original(intent)).action_id, intent.action_id)

    def test_current_owner_state_and_binding_preconditions_reject_even_fresh_vector(self):
        for key, value in [("ownership.state", "pending"), ("customer.consent", "revoked"),
                           ("delivery.risk", "unsafe"), ("delivery.stage", "completed"),
                           ("case.authorization", "denied"), ("case.binding", {"case_id": "C1", "object_id": "O1", "principal_id": "OTHER", "request_id": "REQ1"})]:
            with self.subTest(key=key):
                self.fresh_world()
                self.world.mutate(key, value)
                reply = self.dispatch(self.intent())
                self.assertEqual(reply.status, "rejected")
                self.assertIn(reply.reason, {"identity_scope_rejected", "provider_precondition_rejected"})
                self.assertEqual(self.world.effect_count("reschedule"), 0)

    def test_read_and_effect_deadline_deny_without_identity_or_write(self):
        target = ReadTarget(kind="authority_facts", authority="case", facts=["binding"])
        self.clock.advance(7200)
        self.assertEqual(self.read("read_case", target).observations, [])
        self.assertEqual(self.dispatch(self.intent()).status, "rejected")
        self.assertEqual(self.world.effect_count("reschedule"), 0)

    def test_port_method_never_dispatches_other_declared_operation(self):
        intent = self.intent("send_status")
        self.assertEqual(self.bundle.scheduling.reschedule(intent).status, "rejected")
        self.assertEqual(self.world.effect_count("reschedule"), 0)
        self.assertEqual(self.world.effect_count("send_status"), 0)

    def test_delivered_message_is_distinct_explicit_provider_readback(self):
        self.world.set_fault("send_status", "delivered")
        intent = self.intent("send_status")
        self.assertEqual(self.dispatch(intent).status, "acknowledged")
        self.assertEqual(self.read("read_message", self.original(intent)).stage, "delivered")

    def test_terminal_proof_requires_durable_final_rejection_and_fences_late_dispatch(self):
        intent = self.intent()
        self.world.set_fault("reschedule", "business_rejection")
        self.assertEqual(self.dispatch(intent).status, "rejected")
        try:
            self.world.set_fault("read_schedule", "terminal_not_executed")
        except ValueError:
            self.fail("provider cannot expose its durable terminal rejection proof")
        reply = self.read("read_schedule", self.original(intent))
        self.assertEqual(reply.nonexecution.status, "proven")
        self.assertEqual(reply.action_id, intent.action_id)
        self.assertEqual(reply.fingerprint, intent.argument_fingerprint)
        self.world.set_fault("reschedule", "none")
        self.assertEqual(self.dispatch(intent).status, "rejected")
        self.assertEqual(self.world.effect_count("reschedule"), 0)
        wrong = self.original(intent).model_dump()
        wrong["fingerprint"] = "0" * 64
        self.assertEqual(self.read("read_schedule", ReadTarget(**wrong)).nonexecution.status, "unknown")

    def test_terminal_flag_cannot_prove_absence_timeout_or_executed_effect(self):
        try:
            self.world.set_fault("read_schedule", "terminal_not_executed")
        except ValueError:
            self.fail("terminal provider scenario is missing")
        intent = self.intent()
        self.assertEqual(self.read("read_schedule", self.original(intent)).nonexecution.status, "unknown")
        self.world.set_fault("reschedule", "timeout_before")
        self.dispatch(intent)
        self.assertEqual(self.read("read_schedule", self.original(intent)).nonexecution.status, "unknown")
        self.world.set_fault("reschedule", "none")
        self.assertEqual(self.dispatch(intent).status, "acknowledged")
        self.assertEqual(self.read("read_schedule", self.original(intent)).nonexecution.status, "unknown")

    def test_lost_final_rejection_can_be_proven_but_never_late_executed(self):
        intent = self.intent()
        try:
            self.world.set_fault("reschedule", "final_rejection_unknown")
        except ValueError:
            self.fail("final-rejection response-loss scenario is missing")
        self.assertEqual(self.dispatch(intent).status, "outcome_unknown")
        self.world.set_fault("read_schedule", "terminal_not_executed")
        self.assertEqual(self.read("read_schedule", self.original(intent)).nonexecution.status, "proven")
        self.world.set_fault("reschedule", "none")
        self.assertEqual(self.dispatch(intent).status, "rejected")
        self.assertEqual(self.world.effect_count("reschedule"), 0)

    def test_terminal_proof_deadline_expiry_during_fence_lookup_exposes_no_identity(self):
        for advance, request_seconds in [(11, 7200), (2, 1)]:
            with self.subTest(advance=advance, request_seconds=request_seconds):
                clock = FakeClock()
                initial_now = clock.now()
                expired = []
                phase = "setup"

                class ExpiringFenceWorld(SimulatedWorld):
                    @contextmanager
                    def _connect(self):
                        with super()._connect() as connection:
                            def trace(statement):
                                if phase == "read" and statement.startswith("SELECT * FROM final_rejections") and not expired:
                                    expired.append(phase)
                                    clock.advance(advance)

                            connection.set_trace_callback(trace)
                            yield connection

                world = ExpiringFenceWorld(Path(self.folder.name) / f"fence-expiry-{advance}.sqlite", FIXTURE, clock=clock)
                intent = make_intent(expected_revisions=world.material_revisions())
                world.set_fault("reschedule", "business_rejection")
                dispatch = world.bundle().scheduling.reschedule(intent)
                self.assertEqual(expired, [], "read expiry fault fired during setup dispatch")
                self.assertEqual(clock.now(), initial_now)
                self.assertEqual(dispatch.status, "rejected")
                self.assertEqual(dispatch.reason, "business_rejected")
                world.set_fault("read_schedule", "terminal_not_executed")
                request = ReadRequest(case_id="C1", object_id="O1", caller_id="U1", proof_reference="synthetic-proof",
                                      purpose="reconcile", deadline=clock.now() + timedelta(seconds=request_seconds),
                                      target=self.original(intent))
                phase = "read"
                reply = world.bundle().scheduling.read_schedule(request)
                self.assertTrue(expired, "real provider rejection-fence lookup did not run")
                self.assertEqual(expired, ["read"])
                self.assertEqual(reply.nonexecution.status, "unknown")
                self.assertEqual(reply.observations, [])
                self.assertIsNone(reply.action_id)
                self.assertIsNone(reply.fingerprint)
                self.assertIsNone(reply.provider_request_id)
                self.assertEqual(reply.evidence_refs, [])
                # Expiry must suppress the response, not delete the durable fence.
                fresh = ReadRequest(**{**request.model_dump(), "deadline": clock.now() + timedelta(seconds=5)})
                self.assertEqual(world.bundle().scheduling.read_schedule(fresh).nonexecution.status, "proven")
                self.assertEqual(world.effect_count("reschedule"), 0)

    def test_trusted_manifest_extra_material_fact_is_in_snapshot_and_enforced(self):
        from proofkey.contracts import EnvironmentProfile
        data = load_test_profile().model_dump()
        data["authorities"]["customer.consent_mode"] = "customer"
        data["capabilities"]["reschedule"]["conditional_coverage"]["covered_fields"].append("customer.consent_mode")
        world = SimulatedWorld(Path(self.folder.name) / "extra.sqlite", FIXTURE,
                               profile=EnvironmentProfile.model_validate(data), clock=self.clock)
        vector = dict(world.material_revisions().revisions)
        self.assertIn("customer.consent_mode", vector)
        del vector["customer.consent_mode"]
        intent = make_intent(expected_revisions=RevisionVector(revisions=vector))
        self.assertEqual(world.bundle().scheduling.reschedule(intent).reason, "missing_material_revision")
        intent = make_intent(expected_revisions=world.material_revisions())
        world.mutate("customer.consent_mode", "exact_slot")
        self.assertEqual(world.bundle().scheduling.reschedule(intent).reason, "stale_material_revision")
        self.assertEqual(world.effect_count("reschedule"), 0)

    def test_terminal_rejection_survives_reopen_and_unknown_basis_cannot_prove(self):
        intent = self.intent()
        self.world.set_fault("reschedule", "business_rejection")
        self.dispatch(intent)
        other = SimulatedWorld(Path(self.folder.name) / "world.sqlite", FIXTURE, clock=self.clock)
        self.assertEqual(other.bundle().scheduling.reschedule(intent).status, "rejected")
        from proofkey.contracts import EnvironmentProfile
        data = load_test_profile().model_dump()
        data["capabilities"]["reschedule"]["terminal_nonexecution_basis"]["status"] = "unknown"
        other = SimulatedWorld(Path(self.folder.name) / "world.sqlite", FIXTURE,
                               profile=EnvironmentProfile.model_validate(data), clock=self.clock)
        other.set_fault("read_schedule", "terminal_not_executed")
        request = ReadRequest(case_id="C1", object_id="O1", caller_id="U1", proof_reference="synthetic-proof",
                              purpose="reconcile", deadline=DEADLINE, target=self.original(intent))
        self.assertEqual(other.bundle().scheduling.read_schedule(request).nonexecution.status, "unknown")

    def test_deadline_rechecked_after_account_reservation_before_effect_write(self):
        path = Path(self.folder.name) / "deadline.sqlite"

        class AdvancingClock:
            def __init__(self):
                self.clock = FakeClock()
                self.expired = False

            def now(self):
                if path.exists() and not self.expired:
                    with sqlite3.connect(path) as connection:
                        active = connection.execute("SELECT COUNT(*) FROM pressure WHERE active>0").fetchone()[0]
                    if active:
                        self.expired = True
                        self.clock.advance(7200)
                return self.clock.now()

        world = SimulatedWorld(path, FIXTURE, clock=AdvancingClock())
        result = world.bundle().scheduling.reschedule(make_intent(expected_revisions=world.material_revisions()))
        self.assertEqual(result.status, "rejected")
        self.assertEqual(world.effect_count("reschedule"), 0)

    def test_tool_timeout_is_bounded_even_when_case_deadline_is_later(self):
        path = Path(self.folder.name) / "tool-timeout.sqlite"

        class SlowProviderClock:
            def __init__(self):
                self.clock = FakeClock()
                self.advanced = False

            def now(self):
                if path.exists() and not self.advanced:
                    with sqlite3.connect(path) as connection:
                        active = connection.execute("SELECT COUNT(*) FROM pressure WHERE active>0").fetchone()[0]
                    if active:
                        self.advanced = True
                        self.clock.advance(11)
                return self.clock.now()

        world = SimulatedWorld(path, FIXTURE, clock=SlowProviderClock())
        reply = world.bundle().scheduling.reschedule(make_intent(expected_revisions=world.material_revisions()))
        self.assertEqual(reply.status, "rejected")
        self.assertEqual(world.effect_count("reschedule"), 0)

    def test_read_deadline_rechecked_after_reservation_does_not_expose_facts(self):
        path = Path(self.folder.name) / "read-expired.sqlite"

        class ExpiringClock:
            def __init__(self):
                self.clock = FakeClock()
                self.expired = False

            def now(self):
                if path.exists() and not self.expired:
                    with sqlite3.connect(path) as connection:
                        active = connection.execute("SELECT COUNT(*) FROM pressure WHERE active>0").fetchone()[0]
                    if active:
                        self.expired = True
                        self.clock.advance(7200)
                return self.clock.now()

        world = SimulatedWorld(path, FIXTURE, clock=ExpiringClock())
        request = ReadRequest(case_id="C1", object_id="O1", caller_id="U1", proof_reference="synthetic-proof",
                              purpose="inspect", deadline=DEADLINE,
                              target=ReadTarget(kind="authority_facts", authority="case", facts=["binding"]))
        self.assertEqual(world.bundle().case.read_case(request).observations, [])

    def test_two_provider_instances_cannot_both_commit_same_material_snapshot(self):
        import threading
        other = SimulatedWorld(Path(self.folder.name) / "world.sqlite", FIXTURE, clock=self.clock)
        first = make_intent(provider_key="first-key", expected_revisions=self.world.material_revisions())
        second = make_intent(arguments={"slot": "S2"}, provider_key="second-key", expected_revisions=other.material_revisions())
        barrier = threading.Barrier(2)

        def invoke(world, intent):
            barrier.wait(timeout=2)
            return world.bundle().scheduling.reschedule(intent)

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda pair: invoke(*pair), [(self.world, first), (other, second)]))
        self.assertEqual(sorted(reply.status for reply in results), ["acknowledged", "rejected"])
        self.assertEqual(self.world.effect_count("reschedule"), 1)

    def test_timeout_driver_aliases_preserve_before_and_after_execution(self):
        for behavior, count in [("timeout_before_execute", 0), ("timeout_after_execute", 1)]:
            with self.subTest(behavior=behavior):
                self.fresh_world()
                self.world.set_fault("reschedule", behavior)
                self.assertEqual(self.dispatch(self.intent()).status, "outcome_unknown")
                self.assertEqual(self.world.effect_count("reschedule"), count)

    def test_crashed_provider_reservation_expires_without_refund_or_nonexecution_proof(self):
        path = Path(self.folder.name) / "world.sqlite"
        code = textwrap.dedent("""
            import os
            from proofkey.adapters.world import SimulatedWorld
            from support import make_intent
            class CrashWorld(SimulatedWorld):
                def _write_identity_allowed(self, connection, intent):
                    os._exit(73)
            world = CrashWorld(os.environ['PROOFKEY_TEST_WORLD'], os.environ['PROOFKEY_TEST_FIXTURE'])
            world.bundle().scheduling.reschedule(make_intent(expected_revisions=world.material_revisions()))
        """)
        result = subprocess.run([sys.executable, "-c", code], env={**os.environ,
                                "PROOFKEY_TEST_WORLD": str(path), "PROOFKEY_TEST_FIXTURE": str(FIXTURE)}, timeout=5)
        self.assertEqual(result.returncode, 73)
        other = SimulatedWorld(path, FIXTURE, clock=self.clock)
        self.world, self.bundle = other, other.bundle()
        original = self.intent()
        self.assertEqual(self.dispatch(original).status, "rejected")
        self.assertEqual(self.read("read_schedule", self.original(original)).nonexecution.status, "unknown")
        with sqlite3.connect(path) as connection:
            self.assertEqual(connection.execute("SELECT used FROM pressure").fetchone()[0], 1)
        self.clock.advance(11)
        reply = self.read("read_schedule", self.original(original))
        self.assertEqual(reply.nonexecution.status, "unknown")
        with sqlite3.connect(path) as connection:
            self.assertEqual(connection.execute("SELECT used FROM pressure").fetchone()[0], 2)
        self.assertEqual(self.dispatch(original).status, "acknowledged")
        self.assertEqual(self.dispatch(original).status, "acknowledged")
        self.assertEqual(self.world.effect_count("reschedule"), 1)
        with sqlite3.connect(path) as connection:
            self.assertEqual(connection.execute("SELECT used FROM pressure").fetchone()[0], 4)

    def test_crash_after_commit_keeps_original_history_after_lease_expiry(self):
        path = Path(self.folder.name) / "world.sqlite"
        original = self.intent()
        code = textwrap.dedent("""
            import os
            from proofkey.adapters.world import SimulatedWorld
            from support import make_intent
            class CrashWorld(SimulatedWorld):
                def _release(self, account, token):
                    os._exit(74)
            world = CrashWorld(os.environ['PROOFKEY_TEST_WORLD'], os.environ['PROOFKEY_TEST_FIXTURE'])
            world.bundle().scheduling.reschedule(make_intent(expected_revisions=world.material_revisions()))
        """)
        result = subprocess.run([sys.executable, "-c", code], env={**os.environ,
                                "PROOFKEY_TEST_WORLD": str(path), "PROOFKEY_TEST_FIXTURE": str(FIXTURE)}, timeout=5)
        self.assertEqual(result.returncode, 74)
        self.world = SimulatedWorld(path, FIXTURE, clock=self.clock)
        self.bundle = self.world.bundle()
        self.assertEqual(self.world.effect_count("reschedule"), 1)
        self.assertEqual(self.dispatch(original).status, "rejected")
        self.clock.advance(11)
        reply = self.read("read_schedule", self.original(original))
        self.assertEqual(reply.stage, "committed")
        self.assertEqual(reply.action_id, original.action_id)
        self.assertEqual(reply.nonexecution.status, "unknown")
        self.assertEqual(self.dispatch(original).status, "acknowledged")
        self.assertEqual(self.world.effect_count("reschedule"), 1)
        with sqlite3.connect(path) as connection:
            self.assertEqual(connection.execute("SELECT used FROM pressure").fetchone()[0], 3)

    def test_bad_inventory_destination_and_return_without_refusal_reject(self):
        self.assertEqual(self.dispatch(self.intent("create_return")).status, "rejected")
        for args in [{"inventory": {"item-1": 2}}, {"inventory": {"item-1": True}}, {"inventory": {}}]:
            intent = make_intent(operation="register_goods_refusal", arguments=args,
                                 expected_revisions=self.world.material_revisions())
            self.assertEqual(self.dispatch(intent).status, "rejected")
        self.assertEqual(self.world.effect_count("register_goods_refusal"), 0)

    def test_fault_canary_and_driver_keys_never_appear_in_wire_responses(self):
        self.world.set_fault("reschedule", "timeout_before")
        intent = self.intent()
        result = self.dispatch(intent)
        reply = self.read("read_schedule", self.original(intent))
        serialized = json.dumps([result.model_dump(mode="json"), reply.model_dump(mode="json")])
        for secret in ["timeout_before", "fault", "expected_label", "oracle", "world_selector"]:
            self.assertNotIn(secret, serialized)


if __name__ == "__main__":
    unittest.main()
