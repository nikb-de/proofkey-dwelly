"""Host-owned packet assembly against real public adapters and journal storage."""
from dataclasses import replace
from pathlib import Path
import copy
import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from proofkey.adapters.world import SimulatedWorld
from proofkey.contracts import ActionProposal
from proofkey.gateway import ActionGateway
from proofkey.identity import fingerprint
from proofkey.journal import CaseStore, JournalFailure
from proofkey.policy import GateDenied
from proofkey.profiles import load_profile
from support import FakeClock, make_auth, make_binding, make_checkpoint, make_intent, make_request

ROOT = Path(__file__).resolve().parents[1]


class PacketGatewayTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.clock, self.profile = FakeClock(), load_profile("flat-v1.3")
        self.db, self.path = Path(self.folder.name) / "world.sqlite", Path(self.folder.name) / "journal.sqlite"
        self.fixture = json.loads((ROOT / "fixtures/development/packet-world-v1.json").read_text())
        self.world = SimulatedWorld(self.db, ROOT / "fixtures/development/packet-world-v1.json", profile=self.profile, clock=self.clock)
        self.store = CaseStore(self.path)
        self.addCleanup(lambda: self.store.close())
        self.binding = make_binding()
        self.store.admit(self.binding, make_request(), make_checkpoint(profile_version="v1.3",
            phase="intake", next_gate="enqueue_handoff", ownership_state="accepted", ownership_state_revision="v1"))
        self.gateway = ActionGateway(self.profile, self.world.bundle(), self.store, self.clock, make_auth())

    def enqueue(self, disposition="review_facts"):
        method = getattr(self.gateway, "enqueue_operator_packet", None)
        self.assertTrue(callable(method), "Dynamic packet must use the owned gateway service")
        return method("C1", disposition)

    def prepare(self, disposition="review_facts"):
        reader = getattr(self.gateway, "read_packet_sources", None)
        self.assertTrue(callable(reader), "Packet service needs an owned typed current source reader")
        from proofkey.packets import PacketService
        return PacketService(self.profile, self.store, reader, self.clock).prepare("C1", make_auth(), disposition)

    def test_owned_packet_stores_full_exact_content_and_owner_pending_with_one_batch(self):
        result = self.enqueue("refund_review")
        self.assertEqual(result.status, "verified")
        records = self.store.intents("C1")
        self.assertEqual(len(records), 1)
        intent = records[0].intent
        self.assertEqual(set(intent.arguments), {"packet_id", "packet_revision", "packet_hash", "recipient", "packet_contract", "content_hash", "content"})
        self.assertEqual(intent.arguments["content"]["disposition"], "refund_review")
        self.assertEqual(intent.arguments["content"]["history"], [])
        self.assertNotEqual(intent.arguments["content_hash"], intent.arguments["packet_hash"])
        with sqlite3.connect(self.db) as connection:
            outcome = json.loads(connection.execute("SELECT observations FROM effects").fetchone()[0])
        content = next(item["value"] for item in outcome if item["fact"] == "packet_content")
        receipt = next(item["value"] for item in outcome if item["fact"] == "packet_content_receipt")
        digest = hashlib.sha256(json.dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
        self.assertEqual(digest, intent.arguments["content_hash"])
        self.assertEqual(receipt["owner_status"], "pending")
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 8)
        self.assertEqual(self.world.effect_count("enqueue_handoff"), 1)

    def test_generic_dynamic_builder_is_rejected_before_callback_or_source_reads(self):
        calls = []
        def builder(*args):
            calls.append(args)
            return ActionProposal(operation="enqueue_handoff", stage="enqueue", arguments={}, evidence_refs=[]), {}
        result = self.gateway.execute_proposal("C1", "enqueue_handoff", builder)
        self.assertEqual(result.status, "rejected")
        self.assertEqual(calls, [], "Caller/model callback must never construct a dynamic packet")
        self.assertEqual(self.world.calls, ())

    def test_generic_execute_cannot_admit_a_new_caller_built_packet(self):
        from proofkey.packet_contracts import packet_postcondition
        prepared = self.prepare()
        arguments = {"packet_id": prepared.packet.packet_id, "packet_revision": prepared.packet.packet_revision,
            "packet_hash": prepared.packet.packet_hash, "recipient": "OP1", "packet_contract": "packet-content-v1",
            "content_hash": prepared.content_hash, "content": prepared.content.model_dump(mode="json")}
        intent = make_intent(operation="enqueue_handoff", stage="enqueue", arguments=arguments,
            profile_version="v1.3", expected_revisions=self.world.material_revisions(), postcondition=packet_postcondition(arguments),
            ownership_state_revision="v1", ownership_epoch=0)
        result = self.gateway.execute(intent)
        self.assertEqual(result.status, "rejected")
        self.assertEqual(self.world.effect_count("enqueue_handoff"), 0)
        self.assertEqual(self.store.intents("C1"), ())

    def test_complete_empty_catalog_is_allowed_but_missing_or_incomplete_is_denied(self):
        catalog = copy.deepcopy(self.fixture["facts"]["operator.packet_catalog"]["value"])
        access = copy.deepcopy(self.fixture["facts"]["operator.packet_access"]["value"])
        catalog["originals"], catalog["extracts"] = [], []
        access["permitted_originals"], access["permitted_extracts"] = [], []
        access["catalog_hash"] = fingerprint(catalog)
        self.world.mutate("operator.packet_catalog", catalog)
        self.world.mutate("operator.packet_access", access)
        packet = self.prepare()
        self.assertEqual(packet.content.catalog.originals, [])
        catalog["complete"] = False
        self.world.mutate("operator.packet_catalog", catalog)
        with self.assertRaises(GateDenied):
            self.prepare()
        self.assertEqual(self.store.intents("C1"), ())

    def test_all_detached_generations_and_stops_appear_without_invented_timestamp(self):
        original = make_request(request_id="REQ-Z")
        stopped = make_binding(original, generation="G-Z", supersedes_generation="G1")
        self.store.bind(stopped)
        self.store.save_request(stopped, original)
        self.store.set_stop("C1", "G-Z")
        missing = make_binding(make_request(request_id="REQ-M"), generation="G-M", supersedes_generation="G1")
        self.store.bind(missing)
        packet = self.prepare()
        self.assertEqual([(item.generation, item.requested_at) for item in packet.content.generation_stops], [("G-Z", None)])
        self.assertTrue(any("G-M" in item.record_id and "original" in item.description for item in packet.content.unknowns))
        self.assertTrue(all(any(ref.startswith("local:") for ref in item.source_refs)
            for item in packet.content.unknowns if "G-M" in item.record_id or "G-Z" in item.record_id))

    def test_prepared_original_reopens_and_uses_exact_original_payload(self):
        def persist_only(intent, observations, **kwargs):
            self.store.prepare(intent)
            raise JournalFailure("simulated host interruption after prepare")
        self.gateway._run = persist_only
        self.assertEqual(self.enqueue().status, "rejected")
        saved = self.store.intents("C1")[0].intent
        self.store.close()
        self.store = CaseStore(self.path)
        self.gateway = ActionGateway(self.profile, self.world.bundle(), self.store, self.clock, make_auth())
        # A different requested disposition must not replace the saved snapshot.
        self.assertEqual(self.enqueue("coverage_review").status, "verified")
        self.assertEqual(self.store.intents("C1")[0].intent, saved)
        self.assertEqual(self.world.effect_count("enqueue_handoff"), 1)

    def test_entered_original_recovers_without_rebuilding_or_rekeying(self):
        self.world.set_fault("enqueue_handoff", "timeout_after_execute")
        original, world = self.gateway.bundle.operator, self.world
        class UnknownOriginal:
            def __getattr__(self, name):
                return getattr(original, name)
            def read_receipt(self, request):
                if request.target.kind == "original_effect":
                    world.set_fault("read_receipt", "timeout_before")
                return original.read_receipt(request)
        self.gateway.bundle = replace(self.gateway.bundle, operator=UnknownOriginal())
        self.assertEqual(self.enqueue().status, "outcome_unknown")
        saved = self.store.intents("C1")[0].intent
        self.store.close()
        self.store = CaseStore(self.path)
        self.gateway = ActionGateway(self.profile, self.world.bundle(), self.store, self.clock, make_auth())
        self.world.set_fault("read_receipt", "none")
        before = len(self.world.calls)
        self.assertEqual(self.enqueue("internal_case_review").status, "verified")
        self.assertEqual(self.store.intents("C1")[0].intent, saved)
        self.assertEqual([call.operation for call in self.world.calls[before:]], ["read_receipt"])
        self.assertEqual(self.world.effect_count("enqueue_handoff"), 1)

    def test_current_access_revocation_never_exposes_saved_private_content(self):
        self.assertEqual(self.enqueue().status, "verified")
        access = copy.deepcopy(self.fixture["facts"]["operator.packet_access"]["value"])
        access["sender"] = "OTHER"
        self.world.mutate("operator.packet_access", access)
        result = self.enqueue()
        self.assertEqual(result.status, "rejected")
        self.assertNotIn("content", result.model_dump_json())
        self.assertEqual(self.world.effect_count("enqueue_handoff"), 1)

    def test_malformed_observed_catalog_keeps_its_physical_read_reservation(self):
        original = self.gateway.bundle.operator
        class AlteredCatalog:
            def __getattr__(self, name):
                return getattr(original, name)
            def read_receipt(self, request):
                read = original.read_receipt(request)
                altered = []
                for observation in read.observations:
                    if observation.fact == "packet_catalog":
                        value = observation.model_dump()["value"]
                        value["complete"] = False
                        observation = observation.model_copy(update={"value": value})
                    altered.append(observation)
                return read.model_copy(update={"observations": altered})
        self.gateway.bundle = replace(self.gateway.bundle, operator=AlteredCatalog())
        self.assertEqual(self.enqueue().status, "rejected")
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 10,
            "Structurally observed but invalid catalog must not refund reserved work")

    def test_conflicting_extract_retains_source_linked_conflict(self):
        catalog = copy.deepcopy(self.fixture["facts"]["operator.packet_catalog"]["value"])
        access = copy.deepcopy(self.fixture["facts"]["operator.packet_access"]["value"])
        catalog["extracts"][0]["assertion"]["uncertainty"] = "conflicting"
        access["catalog_hash"] = fingerprint(catalog)
        self.world.mutate("operator.packet_catalog", catalog)
        self.world.mutate("operator.packet_access", access)
        packet = self.prepare()
        self.assertTrue(packet.content.conflicts, "Source extract contradiction must remain visible")
        self.assertIn("synthetic-provider:operator.packet_catalog", packet.content.conflicts[0].source_refs)

    def test_all_prior_intents_keep_unknown_dispatch_separate_from_verified_evidence(self):
        old_request = make_request(request_id="REQ0")
        old = make_binding(old_request, generation="G0")
        folder = Path(self.folder.name) / "history.sqlite"
        history_store = CaseStore(folder)
        try:
            history_store.admit(old, old_request, make_checkpoint(binding=old, profile_version="v1.3",
                phase="intake", ownership_state="accepted", ownership_state_revision="v1"))
            self.world.mutate("case.binding", {"case_id": "C1", "object_id": "O1", "principal_id": "U1", "request_id": "REQ0"})
            self.world.mutate("case.generation", "G0")
            old_gateway = ActionGateway(self.profile, self.world.bundle(), history_store, self.clock, make_auth())
            result = old_gateway.execute_proposal("C1", "send_status", lambda *args:
                (ActionProposal(operation="send_status", stage="send", arguments={"recipient": "U1", "text": "old"}, evidence_refs=[]),
                 {"messaging.status": "sent", "recipient": "U1"}))
            self.assertEqual(result.status, "verified")
            self.world.mutate("case.binding", {"case_id": "C1", "object_id": "O1", "principal_id": "U1", "request_id": "REQ1"})
            self.world.mutate("case.generation", "G1")
            current = make_binding(supersedes_generation="G0")
            history_store.admit(current, make_request(), make_checkpoint(binding=current, profile_version="v1.3",
                phase="intake", ownership_state="accepted", ownership_state_revision="v1"))
            gateway = ActionGateway(self.profile, self.world.bundle(), history_store, self.clock, make_auth())
            from proofkey.packets import PacketService
            packet = PacketService(self.profile, history_store, gateway.read_packet_sources, self.clock).prepare("C1", make_auth(), "review_facts")
            self.assertEqual(len(packet.content.history), 1)
            self.assertEqual((packet.content.history[0].binding.generation, packet.content.history[0].dispatch_state,
                packet.content.history[0].verification_state), ("G0", "unknown", "verified"))
            self.assertFalse(packet.content.history[0].unresolved)
        finally:
            history_store.close()

    def test_real_process_crash_after_prepare_and_after_provider_commit_keep_original(self):
        # Actual os._exit in a child, separate from simulated Python phase faults.
        for phase, exit_code in (("prepared", 71), ("provider_committed", 72)):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as folder:
                path = Path(folder)
                script = '''
import os, sys
from dataclasses import replace
from pathlib import Path
from proofkey.adapters.world import SimulatedWorld
from proofkey.gateway import ActionGateway
from proofkey.journal import CaseStore
from proofkey.profiles import load_profile
from support import FakeClock, make_auth, make_binding, make_checkpoint, make_request
folder, fixture, phase = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
clock, profile = FakeClock(), load_profile("flat-v1.3")
world = SimulatedWorld(folder / "world.sqlite", fixture, profile=profile, clock=clock)
store = CaseStore(folder / "journal.sqlite")
store.admit(make_binding(), make_request(), make_checkpoint(profile_version="v1.3", phase="intake",
    next_gate="enqueue_handoff", ownership_state="accepted", ownership_state_revision="v1"))
gateway = ActionGateway(profile, world.bundle(), store, clock, make_auth())
if phase == "prepared":
    prepare = store.prepare
    def crash_after_prepare(intent):
        prepare(intent)
        os._exit(71)
    store.prepare = crash_after_prepare
else:
    operator = gateway.bundle.operator
    class CrashOperator:
        def __getattr__(self, name):
            return getattr(operator, name)
        def enqueue_handoff(self, intent, *, deadline=None):
            result = operator.enqueue_handoff(intent, deadline=deadline)
            assert result.status == "acknowledged"
            os._exit(72)
    gateway.bundle = replace(gateway.bundle, operator=CrashOperator())
gateway.enqueue_operator_packet("C1", "review_facts")
raise RuntimeError("Crash boundary was not reached")
'''
                child = subprocess.run([sys.executable, "-c", script, folder,
                    str(ROOT / "fixtures/development/packet-world-v1.json"), phase],
                    capture_output=True, text=True, timeout=20)
                self.assertEqual(child.returncode, exit_code, child.stderr)
                recovered = CaseStore(path / "journal.sqlite")
                try:
                    saved = recovered.intents("C1")[0].intent
                    self.assertEqual(recovered.intents("C1")[0].state,
                        "prepared" if phase == "prepared" else "dispatching")
                    clock = FakeClock()
                    clock.advance(2)  # Recovery clock follows the crashed entry's source time.
                    world = SimulatedWorld(path / "world.sqlite", ROOT / "fixtures/development/packet-world-v1.json",
                        profile=self.profile, clock=clock)
                    gateway = ActionGateway(self.profile, world.bundle(), recovered, clock, make_auth())
                    self.assertEqual(gateway.enqueue_operator_packet("C1", "coverage_review").status, "verified")
                    self.assertEqual(recovered.intents("C1")[0].intent, saved)
                    self.assertEqual(world.effect_count("enqueue_handoff"), 1)
                    if phase == "provider_committed":
                        self.assertEqual([call.operation for call in world.calls], ["read_receipt"])
                finally:
                    recovered.close()

    def test_prepared_stop_fence_does_not_read_or_send_saved_packet(self):
        def persist_only(intent, observations, **kwargs):
            self.store.prepare(intent)
            raise JournalFailure("simulated interruption")
        self.gateway._run = persist_only
        self.assertEqual(self.enqueue().status, "rejected")
        saved = self.store.intents("C1")[0].intent
        self.store.set_stop("C1", "G1")
        gateway = ActionGateway(self.profile, self.world.bundle(), self.store, self.clock, make_auth())
        before = len(self.world.calls)
        self.assertEqual(gateway.enqueue_operator_packet("C1", "review_facts").status, "rejected")
        self.assertEqual(len(self.world.calls), before)
        self.assertEqual(self.store.intent(saved.action_id).state, "prepared")

    def test_provider_races_current_catalog_access_recipient_and_owner_deny_storage(self):
        catalog = copy.deepcopy(self.fixture["facts"]["operator.packet_catalog"]["value"])
        access = copy.deepcopy(self.fixture["facts"]["operator.packet_access"]["value"])
        catalog["revision"], access["revision"] = "v2", "v2"
        for fact, value in (("operator.recipient", "OP2"), ("ownership.owner", "OP1"),
                            ("ownership.epoch", 1), ("operator.packet_hash", "a" * 64),
                            ("operator.packet_catalog", catalog), ("operator.packet_access", access)):
            with self.subTest(fact=fact):
                fixture = PacketGatewayTests()
                fixture.setUp()
                try:
                    original, world = fixture.gateway.bundle.operator, fixture.world
                    class RacingOperator:
                        def __getattr__(self, name):
                            return getattr(original, name)
                        def enqueue_handoff(self, intent, *, deadline=None):
                            world.mutate(fact, value)
                            return original.enqueue_handoff(intent, deadline=deadline)
                    fixture.gateway.bundle = replace(fixture.gateway.bundle, operator=RacingOperator())
                    self.assertEqual(fixture.enqueue().status, "rejected")
                    self.assertEqual(fixture.world.effect_count("enqueue_handoff"), 0)
                finally:
                    fixture.doCleanups()

    def test_packet_rejects_oversize_extract_without_truncation(self):
        catalog = copy.deepcopy(self.fixture["facts"]["operator.packet_catalog"]["value"])
        access = copy.deepcopy(self.fixture["facts"]["operator.packet_access"]["value"])
        catalog["extracts"][0]["content"] = "x" * 16385
        access["catalog_hash"] = fingerprint(catalog)
        self.world.mutate("operator.packet_catalog", catalog)
        self.world.mutate("operator.packet_access", access)
        self.assertEqual(self.enqueue().status, "rejected")
        self.assertEqual(self.store.intents("C1"), ())

    def test_packet_rejects_oversize_local_history_without_truncation(self):
        for index in range(65):
            self.store.prepare(make_intent(operation="send_status", stage="local-history-" + str(index), profile_version="v1.3"))
        self.assertEqual(self.enqueue().status, "rejected")
        self.assertEqual(len(self.store.intents("C1")), 65)
        self.assertEqual(self.world.effect_count("enqueue_handoff"), 0)

    def test_packet_snapshot_checkpoint_changed_after_read_cannot_prepare(self):
        source_reader = self.gateway.read_packet_sources
        def changed_checkpoint(binding, auth):
            sources = source_reader(binding, auth)
            checkpoint = self.store.checkpoint("C1")
            self.store.save_checkpoint(checkpoint.model_copy(update={"phase": "completeness"}))
            return sources
        self.gateway.read_packet_sources = changed_checkpoint
        self.assertEqual(self.enqueue().status, "rejected")
        self.assertEqual(self.store.intents("C1"), ())

    def test_later_dynamic_material_read_validates_catalog_before_settlement(self):
        def persist_only(intent, observations, **kwargs):
            self.store.prepare(intent)
            raise JournalFailure("simulated interruption")
        self.gateway._run = persist_only
        self.assertEqual(self.enqueue().status, "rejected")
        intent = self.store.intents("C1")[0].intent
        original = self.gateway.bundle.operator
        class BadAccess:
            def __getattr__(self, name):
                return getattr(original, name)
            def read_receipt(self, request):
                reply = original.read_receipt(request)
                altered = []
                for observation in reply.observations:
                    if observation.fact == "packet_access":
                        access = observation.model_dump()["value"]
                        access["catalog_hash"] = "0" * 64
                        observation = observation.model_copy(update={"value": access})
                    altered.append(observation)
                return reply.model_copy(update={"observations": altered})
        self.gateway.bundle = replace(self.gateway.bundle, operator=BadAccess())
        with self.assertRaises(GateDenied):
            self.gateway.read_material_authorities(intent)
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 10)


if __name__ == "__main__":
    unittest.main()
