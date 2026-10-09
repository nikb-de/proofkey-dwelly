"""Synthetic host operator waits over real public packet ports and durable storage."""
from datetime import timedelta
from pathlib import Path
import copy
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from proofkey.adapters.world import SimulatedWorld
from proofkey.contracts import ActionProposal, WaitState
from proofkey.gateway import ActionGateway
from proofkey.identity import fingerprint, stable_action_id
from proofkey.journal import CaseStore
from proofkey.profiles import load_profile
from proofkey.wait_contracts import WaitRecordV1
from support import FakeClock, make_auth, make_binding, make_checkpoint, make_request

ROOT = Path(__file__).resolve().parents[1]


class HostWaitFixture:
    """No runtime activation shim: host persists the declared graph envelope."""
    def __init__(self, folder, *, reopen=False):
        root = Path(folder)
        self.clock, self.profile = FakeClock(), load_profile("flat-v1.3")
        self.fixture = json.loads((ROOT / "fixtures/development/packet-world-v1.json").read_text())
        self.world = SimulatedWorld(root / "world.sqlite", ROOT / "fixtures/development/packet-world-v1.json",
            profile=self.profile, clock=self.clock)
        self.store = CaseStore(root / "journal.sqlite")
        self.binding = make_binding()
        if not reopen:
            self.store.admit(self.binding, make_request(), make_checkpoint(profile_version="v1.3",
                phase="intake", next_gate="enqueue_handoff", ownership_state="accepted", ownership_state_revision="v1"))
        else:
            self.clock.advance(2)
        self.gateway = ActionGateway(self.profile, self.world.bundle(), self.store, self.clock, make_auth())
        self.question_id = "question:" + stable_action_id(self.binding, "enqueue_handoff", "enqueue")

    def persist(self, intent, sources, checkpoint, *, retain=True, expiry_seconds=None):
        origin = checkpoint.model_copy(update={"observations": list(sources.observations)})
        self.store.save_checkpoint(origin)
        process = self.profile.processes["reschedule_window"]
        edge = next(e for e in process.edges if e.origin == origin.phase and e.operation == "enqueue_handoff")
        contract = next(w for w in process.waits if w.phase == edge.target)
        now = self.clock.now()
        wait = WaitState(question_id=self.question_id, binding=origin.binding, origin=origin.phase,
            next_gate=contract.next_gate, recipient=intent.arguments["recipient"],
            owner_state_revision=origin.ownership_state_revision, awaited_fields=contract.awaited_fields,
            expires_at=min(origin.deadline, now + timedelta(seconds=contract.expiry_seconds if expiry_seconds is None else expiry_seconds)),
            budget=origin.budget)
        data = dict(wait=wait, origin_checkpoint=origin, origin_hash=fingerprint(origin.model_dump(mode="json")),
            process=process, profile_hash=self.profile.release_hash, policy_hash=self.profile.policy_hash,
            owner_id="U1", owner_state=origin.ownership_state, owner_revision=origin.ownership_state_revision,
            owner_epoch=origin.ownership_epoch, recipient_role=contract.recipient_role, wait_phase=edge.target,
            communication_edge=edge, communication_stage="enqueue", communication_action_id=intent.action_id,
            accept_edge=next(e for e in process.edges if e.origin == edge.target and e.target == contract.next_gate),
            expiry_edge=next(e for e in process.edges if e.origin == edge.target and e.operation == "expire_wait"), created_at=now)
        if retain:
            data["communication_intent"] = intent
        record = WaitRecordV1.model_validate(data)
        self.store.create_wait_atomic(record, now)
        return record


class OperatorWaitGatewayTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.fx = HostWaitFixture(self.folder.name)
        self.addCleanup(lambda: self.fx.store.close())

    def enqueue(self, hook=None, disposition="review_facts"):
        try:
            return self.fx.gateway.enqueue_operator_packet("C1", disposition, before_prepare=hook)
        except TypeError as error:
            self.fail("Owned operator-wait preprepare callback is missing: " + str(error))

    def saved_only(self, *, retain=True):
        def hook(intent, sources, checkpoint):
            self.fx.persist(intent, sources, checkpoint, retain=retain)
            raise RuntimeError("Synthetic interruption after durable wait, before prepare")
        self.assertEqual(self.enqueue(hook).status, "rejected")
        self.assertEqual(self.fx.store.intents("C1"), ())
        return self.fx.store.load_wait_record(self.fx.question_id)

    def test_default_nonwait_still_eight_tools_and_no_question(self):
        self.assertEqual(self.fx.gateway.enqueue_operator_packet("C1", "review_facts").status, "verified")
        self.assertEqual(self.fx.store.checkpoint("C1").budget.tool_calls, 8)
        self.assertIsNone(self.fx.store.wait(self.fx.question_id))

    def test_hook_runs_after_six_sources_before_prepare_and_transport(self):
        captured = []
        def hook(intent, sources, checkpoint):
            self.assertEqual(checkpoint, self.fx.store.checkpoint("C1"))
            self.assertEqual(checkpoint.budget.tool_calls, 6)
            self.assertEqual(self.fx.store.intents("C1"), ())
            self.assertEqual(self.fx.world.effect_count("enqueue_handoff"), 0)
            self.assertIn("case.question_revision", {o.authority + "." + o.fact for o in sources.observations})
            captured.append(intent)
            self.fx.persist(intent, sources, checkpoint)
            return {"arguments": "ignored", "budget": "ignored"}
        self.assertEqual(self.enqueue(hook).status, "verified")
        record = self.fx.store.load_wait_record(self.fx.question_id)
        self.assertEqual(record.communication_intent, captured[0])
        self.assertEqual(self.fx.store.intents("C1")[0].intent, captured[0])
        self.assertEqual(self.fx.store.checkpoint("C1").budget.tool_calls, 8)
        self.assertEqual(self.fx.store.checkpoint("C1").budget.clarifications, 0)
        self.assertEqual(self.fx.world.effect_count("enqueue_handoff"), 1)

    def test_nested_mutation_denies_without_preparing(self):
        def mutate(intent, sources, checkpoint):
            intent.arguments["content"]["disposition"] = "coverage_review"
        self.assertEqual(self.enqueue(mutate).status, "rejected")
        self.assertEqual(self.fx.store.intents("C1"), ())
        self.assertEqual(self.fx.store.checkpoint("C1").budget.tool_calls, 6)

    def test_bypassed_detached_mutation_is_detected(self):
        def mutate(intent, sources, checkpoint):
            dict.__setitem__(intent.arguments["content"], "disposition", "coverage_review")
        self.assertEqual(self.enqueue(mutate).status, "rejected")
        self.assertEqual(self.fx.store.intents("C1"), ())

    def test_detached_source_mutation_is_detected(self):
        def mutate(intent, sources, checkpoint):
            object.__setattr__(sources.observations[0], "revision", "host-invented")
        self.assertEqual(self.enqueue(mutate).status, "rejected")
        self.assertEqual(self.fx.store.intents("C1"), ())

    def test_callback_cannot_mutate_checkpoint_control_or_accounting(self):
        def mutate(intent, sources, checkpoint):
            self.fx.store.save_checkpoint(checkpoint.model_copy(update={"phase": "completeness"}))
        self.assertEqual(self.enqueue(mutate).status, "rejected")
        self.assertEqual(self.fx.store.intents("C1"), ())
        self.assertEqual(self.fx.store.checkpoint("C1").budget.tool_calls, 6)

    def test_callback_cannot_replace_observations_with_an_invented_batch(self):
        def mutate(intent, sources, checkpoint):
            observation = sources.observations[0].model_copy(update={"revision": "invented"})
            self.fx.store.save_checkpoint(checkpoint.model_copy(update={"observations": [observation]}))
        self.assertEqual(self.enqueue(mutate).status, "rejected")
        self.assertEqual(self.fx.store.intents("C1"), ())

    def test_callback_extra_accounting_is_not_an_allowed_checkpoint_change(self):
        def charge(intent, sources, checkpoint):
            self.fx.store.consume("C1", "tool_calls", 1, self.fx.clock.now())
        self.assertEqual(self.enqueue(charge).status, "rejected")
        self.assertEqual(self.fx.store.checkpoint("C1").budget.tool_calls, 7)
        self.assertEqual(self.fx.store.intents("C1"), ())

    def test_source_read_control_race_denies_before_callback(self):
        from dataclasses import replace
        original, store = self.fx.gateway.bundle.operator, self.fx.store
        class ChangeControl:
            def __getattr__(self, name):
                return getattr(original, name)
            def read_receipt(self, request):
                read = original.read_receipt(request)
                if request.target.kind == "authority_facts":
                    store.save_checkpoint(store.checkpoint("C1").model_copy(update={"phase": "completeness"}))
                return read
        self.fx.gateway.bundle = replace(self.fx.gateway.bundle, operator=ChangeControl())
        calls = []
        self.assertEqual(self.enqueue(lambda *args: calls.append(True)).status, "rejected")
        self.assertEqual(calls, [])
        self.assertEqual(self.fx.store.checkpoint("C1").budget.tool_calls, 6)
        self.assertEqual(self.fx.store.intents("C1"), ())

    def test_malformed_question_keeps_full_case_reservation(self):
        self.fx.world.mutate("case.question_revision", 7)
        calls = []
        self.assertEqual(self.enqueue(lambda *args: calls.append(args)).status, "rejected")
        cp = self.fx.store.checkpoint("C1")
        self.assertEqual((cp.budget.tool_calls, cp.budget.active_seconds), (1, 10.0))
        self.assertEqual(calls, [])
        self.assertEqual(self.fx.store.intents("C1"), ())

    def test_saved_envelope_recovers_exact_payload_without_rebuild(self):
        saved = self.saved_only()
        self.assertEqual(self.enqueue(disposition="coverage_review").status, "verified")
        self.assertEqual(self.fx.store.intents("C1")[0].intent, saved.communication_intent)
        self.assertEqual(self.fx.store.load_wait_record(self.fx.question_id), saved)
        self.assertEqual(self.fx.store.checkpoint("C1").budget.tool_calls, 14)

    def test_changed_saved_content_denies_before_recovery_hook(self):
        self.saved_only()
        self.fx.world.mutate("operator.packet_hash", "e" * 64)
        calls = []
        self.assertEqual(self.enqueue(lambda *args: calls.append(True)).status, "rejected")
        self.assertEqual(calls, [], "A retained payload must pass fresh original scope before the hook")

    def test_question_expiring_during_dispatch_pacing_never_enters_transport(self):
        def short_wait(intent, sources, checkpoint):
            self.fx.persist(intent, sources, checkpoint, expiry_seconds=0.05)
        self.assertEqual(self.enqueue(short_wait).status, "rejected")
        records = self.fx.store.intents("C1")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].state, "prepared")
        self.assertEqual(self.fx.store.checkpoint("C1").budget.tool_calls, 6)
        self.assertEqual(self.fx.world.effect_count("enqueue_handoff"), 0)

    def test_noop_hook_cannot_enter_after_packet_access_expires(self):
        access = copy.deepcopy(self.fx.fixture["facts"]["operator.packet_access"]["value"])
        access["expires_at"] = (self.fx.clock.now() + timedelta(seconds=1)).isoformat()
        self.fx.world.mutate("operator.packet_access", access)
        def slow_noop(intent, sources, checkpoint):
            self.fx.clock.advance(1)
        self.assertEqual(self.enqueue(slow_noop).status, "rejected")
        self.assertEqual(self.fx.world.effect_count("enqueue_handoff"), 0)
        self.assertEqual(self.fx.store.intents("C1"), (), "Expired callback scope must deny before durable prepare/entry")
        self.assertEqual(self.fx.store.checkpoint("C1").budget.tool_calls, 6)

    def test_wait_control_phase_change_during_pacing_denies_transport(self):
        def install_race(intent, sources, checkpoint):
            self.fx.persist(intent, sources, checkpoint)
            wait = self.fx.clock.wait
            def change_phase(seconds):
                wait(seconds)
                current = self.fx.store.checkpoint("C1")
                self.fx.store.save_checkpoint(current.model_copy(update={"phase": "completeness"}))
            self.fx.clock.wait = change_phase
        self.assertEqual(self.enqueue(install_race).status, "rejected")
        self.assertEqual(self.fx.world.effect_count("enqueue_handoff"), 0)
        self.assertEqual(self.fx.store.intents("C1")[0].state, "prepared")

    def test_physical_wait_deadline_is_clamped_without_changing_intent(self):
        deadlines = []
        original = self.fx.gateway.bundle.operator
        class CaptureDeadline:
            def __getattr__(self, name):
                return getattr(original, name)
            def enqueue_handoff(self, intent, *, deadline):
                deadlines.append((intent.deadline, deadline))
                return original.enqueue_handoff(intent, deadline=deadline)
        from dataclasses import replace
        self.fx.gateway.bundle = replace(self.fx.gateway.bundle, operator=CaptureDeadline())
        def short_wait(intent, sources, checkpoint):
            self.fx.persist(intent, sources, checkpoint, expiry_seconds=2)
        self.assertEqual(self.enqueue(short_wait).status, "verified")
        wait = self.fx.store.load_wait_record(self.fx.question_id)
        self.assertEqual(deadlines, [(wait.communication_intent.deadline, wait.wait.expires_at)])
        self.assertEqual(self.fx.store.checkpoint("C1").deadline, wait.communication_intent.deadline)
        self.fx.clock.advance(3)
        before = self.fx.world.effect_count("enqueue_handoff")
        self.assertEqual(self.enqueue().status, "verified", "Expired wait does not erase entered-original readback")
        self.assertEqual(self.fx.world.effect_count("enqueue_handoff"), before)

    def test_customer_tagged_question_also_expires_during_dispatch_pacing(self):
        store, profile = self.fx.store, self.fx.profile
        store.save_checkpoint(store.checkpoint("C1").model_copy(update={"phase": "completeness",
            "next_gate": "send_clarification"}))
        def builder(request, observations):
            current = store.checkpoint("C1")
            origin = current.model_copy(update={"observations": list(observations)})
            store.save_checkpoint(origin)
            process = profile.processes[request.kind]
            edge = next(e for e in process.edges if e.origin == origin.phase and e.operation == "send_clarification")
            contract = next(w for w in process.waits if w.phase == edge.target)
            action_id = stable_action_id(origin.binding, "send_clarification", "send")
            question_id = "question:" + action_id
            now = self.fx.clock.now()
            wait = WaitState(question_id=question_id, binding=origin.binding, origin=origin.phase,
                next_gate=contract.next_gate, recipient="U1", owner_state_revision=origin.ownership_state_revision,
                awaited_fields=contract.awaited_fields, expires_at=now + timedelta(seconds=0.05), budget=origin.budget)
            record = WaitRecordV1(wait=wait, origin_checkpoint=origin, origin_hash=fingerprint(origin.model_dump(mode="json")),
                process=process, profile_hash=profile.release_hash, policy_hash=profile.policy_hash, owner_id="U1",
                owner_state=origin.ownership_state, owner_revision=origin.ownership_state_revision, owner_epoch=origin.ownership_epoch,
                recipient_role=contract.recipient_role, wait_phase=edge.target, communication_edge=edge,
                communication_stage="send", communication_action_id=action_id,
                accept_edge=next(e for e in process.edges if e.origin == edge.target and e.target == contract.next_gate),
                expiry_edge=next(e for e in process.edges if e.origin == edge.target and e.operation == "expire_wait"), created_at=now)
            store.create_wait_atomic(record, now)
            args = {"question_id": question_id, "recipient": "U1", "text": "Synthetic host question"}
            return ActionProposal(operation="send_clarification", stage="send", arguments=args, evidence_refs=[]), {
                "question_id": question_id, "recipient": "U1", "status": "sent"}
        result = self.fx.gateway.execute_proposal("C1", "send_clarification", builder)
        self.assertEqual(result.status, "rejected")
        self.assertEqual(store.intents("C1")[0].state, "prepared")
        self.assertEqual(store.checkpoint("C1").budget.clarifications, 1)
        self.assertEqual(store.checkpoint("C1").budget.tool_calls, 6)
        self.assertEqual(self.fx.world.effect_count("send_clarification"), 0)

    def test_generic_dynamic_builder_remains_closed(self):
        calls = []
        result = self.fx.gateway.execute_proposal("C1", "enqueue_handoff", lambda *args: calls.append(True))
        self.assertEqual(result.status, "rejected")
        self.assertEqual(calls, [])
        self.assertEqual(self.fx.world.calls, ())

    def test_prepared_nonwait_original_cannot_acquire_a_wait_retroactively(self):
        def persist_only(intent, observations, **kwargs):
            self.fx.store.prepare(intent)
            raise RuntimeError("Synthetic interruption at prepared nonwait original")
        self.fx.gateway._run = persist_only
        self.assertEqual(self.fx.gateway.enqueue_operator_packet("C1", "review_facts").status, "rejected")
        calls = []
        self.assertEqual(self.enqueue(lambda *args: calls.append(args)).status, "rejected")
        self.assertEqual(calls, [])
        self.assertIsNone(self.fx.store.wait(self.fx.question_id))
        self.assertEqual(self.fx.world.effect_count("enqueue_handoff"), 0)

    def test_legacy_incomplete_saved_payload_denies_without_rebuild(self):
        self.saved_only(retain=False)
        self.assertEqual(self.enqueue().status, "rejected")
        self.assertEqual(self.fx.store.intents("C1"), ())
        self.assertEqual(self.fx.world.effect_count("enqueue_handoff"), 0)

    def test_prepared_original_retries_without_hook_and_entered_only_reconciles(self):
        def persist_then_stop(intent, sources, checkpoint):
            self.fx.persist(intent, sources, checkpoint)
            self.fx.store.prepare(intent)
            raise RuntimeError("Synthetic interruption after prepare")
        self.assertEqual(self.enqueue(persist_then_stop).status, "rejected")
        saved = self.fx.store.intents("C1")[0].intent
        calls = []
        self.assertEqual(self.enqueue(lambda *args: calls.append(args), "coverage_review").status, "verified")
        self.assertEqual(calls, [])
        self.assertEqual(self.fx.store.intents("C1")[0].intent, saved)
        before = len(self.fx.world.calls)
        self.assertEqual(self.enqueue(lambda *args: calls.append(args)).status, "verified")
        self.assertEqual(calls, [])
        self.assertEqual([c.operation for c in self.fx.world.calls[before:]], ["read_receipt"])

    def test_saved_scope_changes_deny_without_replacing_original(self):
        for field, value in (("case.question_revision", "changed"), ("operator.packet_hash", "e" * 64),
                             ("operator.packet_revision", "changed"), ("operator.recipient", "OP2"),
                             ("ownership.owner", "other"), ("ownership.epoch", 1), ("policy.version", "other")):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as folder:
                old = self.fx
                self.fx = HostWaitFixture(folder)
                try:
                    saved = self.saved_only()
                    self.fx.world.mutate(field, value)
                    self.assertEqual(self.enqueue().status, "rejected")
                    self.assertEqual(self.fx.store.intents("C1"), ())
                    self.assertEqual(self.fx.store.load_wait_record(self.fx.question_id), saved)
                    self.assertEqual(self.fx.world.effect_count("enqueue_handoff"), 0)
                finally:
                    self.fx.store.close()
                    self.fx = old

    def test_saved_expiry_and_config_change_deny(self):
        saved = self.saved_only()
        self.fx.clock.advance(301)
        self.assertEqual(self.enqueue().status, "rejected")
        self.assertEqual(self.fx.store.load_wait_record(self.fx.question_id), saved)
        self.assertEqual(self.fx.world.effect_count("enqueue_handoff"), 0)

    def test_saved_configured_release_change_denies_without_read_or_hook(self):
        saved = self.saved_only()
        self.fx.gateway.profile = load_profile("flat-v1.2")
        calls = []
        before = len(self.fx.world.calls)
        self.assertEqual(self.enqueue(lambda *args: calls.append(args)).status, "rejected")
        self.assertEqual(calls, [])
        self.assertEqual(len(self.fx.world.calls), before)
        self.assertEqual(self.fx.store.load_wait_record(self.fx.question_id), saved)

    def test_callback_stop_race_keeps_durable_envelope_and_debt(self):
        def stop(intent, sources, checkpoint):
            self.fx.persist(intent, sources, checkpoint)
            self.fx.store.stop_waits_atomic(checkpoint.binding, self.fx.store.checkpoint("C1"))
        self.assertEqual(self.enqueue(stop).status, "rejected")
        self.assertEqual(self.fx.store.intents("C1"), ())
        self.assertEqual(self.fx.store.load_wait_record(self.fx.question_id).lifecycle, "stopped")
        self.assertEqual(self.fx.store.checkpoint("C1").budget.tool_calls, 6)
        self.assertEqual(self.fx.world.effect_count("enqueue_handoff"), 0)

    def test_record_rejects_retained_intent_scope_changes(self):
        saved = self.saved_only()
        raw = saved.model_dump()
        for key, value in (("provider_key", "foreign"), ("deadline", saved.communication_intent.deadline + timedelta(seconds=1)),
                           ("ownership_epoch", 9), ("policy_version", "other"), ("postcondition", {})):
            with self.subTest(key=key):
                changed = copy.deepcopy(raw)
                changed["communication_intent"][key] = value
                with self.assertRaises(ValueError):
                    WaitRecordV1.model_validate(changed)

    def test_public_save_rejects_incomplete_or_mismatching_retained_revision_pins(self):
        for mutation in ("empty", "partial", "mismatch"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as folder:
                fx = HostWaitFixture(folder)
                self.addCleanup(fx.store.close)
                admitted = []
                def hook(intent, sources, checkpoint):
                    pins = dict(intent.expected_revisions.revisions)
                    if mutation == "empty":
                        pins.clear()
                    elif mutation == "partial":
                        del pins["customer.consent"]
                    else:
                        pins["customer.consent"] = "valid-looking-but-wrong"
                    changed = intent.model_copy(update={"expected_revisions":
                        intent.expected_revisions.model_copy(update={"revisions": pins})})
                    try:
                        fx.persist(changed, sources, checkpoint)
                    except ValueError:
                        admitted.append(False)
                    else:
                        admitted.append(True)
                    raise RuntimeError("Bounded host interruption after rejected save")
                self.assertEqual(fx.gateway.enqueue_operator_packet("C1", "review_facts", before_prepare=hook).status, "rejected")
                self.assertEqual(admitted, [False], "Incomplete original must not be publicly persisted")
                self.assertIsNone(fx.store.wait(fx.question_id))
                self.assertEqual(fx.store.intents("C1"), ())
                self.assertEqual(fx.store.checkpoint("C1").budget.tool_calls, 6)
                self.assertEqual(fx.world.effect_count("enqueue_handoff"), 0)

    def test_corrupt_retained_revision_pins_deny_before_recovery_hook(self):
        for mutation in ("empty", "partial", "mismatch"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as folder:
                old = self.fx
                self.fx = HostWaitFixture(folder)
                try:
                    saved = self.saved_only()
                    raw = saved.model_dump(mode="json")
                    pins = raw["communication_intent"]["expected_revisions"]["revisions"]
                    if mutation == "empty":
                        pins.clear()
                    elif mutation == "partial":
                        del pins["customer.consent"]
                    else:
                        pins["customer.consent"] = "valid-looking-but-wrong"
                    encoded = json.dumps(raw)
                    path = Path(folder) / "journal.sqlite"
                    # Hostile stored-row setup, not a valid public save or source grant.
                    with sqlite3.connect(path) as db:
                        db.execute("UPDATE waits SET wait_json=? WHERE question_id=?", (encoded, self.fx.question_id))
                    calls = []
                    debt = self.fx.store.checkpoint("C1").budget
                    self.assertEqual(self.enqueue(lambda intent, *_: calls.append(intent.action_id)).status, "rejected")
                    self.assertEqual(calls, [], "Malformed original cannot reach the consumer hook")
                    self.assertEqual(self.fx.store.intents("C1"), ())
                    self.assertEqual(self.fx.store.checkpoint("C1").budget, debt)
                    self.assertEqual(self.fx.world.effect_count("enqueue_handoff"), 0)
                    with sqlite3.connect(path) as db:
                        retained = db.execute("SELECT wait_json FROM waits WHERE question_id=?", (self.fx.question_id,)).fetchone()[0]
                    self.assertEqual(retained, encoded)
                finally:
                    self.fx.store.close()
                    self.fx = old

    def test_valid_saved_revision_pins_reach_recovery_hook_and_dispatch(self):
        saved = self.saved_only()
        calls = []
        def hook(intent, sources, checkpoint):
            self.assertEqual(intent, saved.communication_intent)
            self.assertEqual(checkpoint.budget.tool_calls, 12)
            self.assertEqual(self.fx.store.intents("C1"), ())
            self.assertNotIn("case.question_revision", intent.expected_revisions.revisions)
            calls.append(intent)
        self.assertEqual(self.enqueue(hook).status, "verified")
        self.assertEqual(calls, [saved.communication_intent])
        self.assertEqual(self.fx.store.load_wait_record(self.fx.question_id), saved)
        self.assertEqual(self.fx.store.checkpoint("C1").budget.tool_calls, 14)
        self.assertEqual(self.fx.world.effect_count("enqueue_handoff"), 1)

    def test_valid_saved_original_with_changed_fresh_revision_denies_before_hook(self):
        saved = self.saved_only()
        self.fx.world.mutate("customer.consent", "granted")
        calls = []
        self.assertEqual(self.enqueue(lambda intent, *_: calls.append(intent.action_id)).status, "rejected")
        self.assertEqual(calls, [])
        self.assertEqual(self.fx.store.intents("C1"), ())
        self.assertEqual(self.fx.world.effect_count("enqueue_handoff"), 0)
        self.assertEqual(self.fx.store.load_wait_record(self.fx.question_id), saved)
        self.assertEqual(self.fx.store.checkpoint("C1").budget.tool_calls, 12)

    def test_record_requires_typed_original_question_revision(self):
        saved = self.saved_only()
        raw = saved.model_dump(mode="json")
        observation = next(o for o in raw["origin_checkpoint"]["observations"]
                           if (o["authority"], o["fact"]) == ("case", "question_revision"))
        observation["value"] = 9
        raw["origin_hash"] = fingerprint(raw["origin_checkpoint"])
        with self.assertRaises(ValueError):
            WaitRecordV1.model_validate_json(json.dumps(raw))

    def test_record_packet_metadata_must_match_designated_origin_observations(self):
        saved = self.saved_only()
        for key, value in (("operator.packet_hash", "e" * 64), ("operator.recipient", "OP2"),
                           ("ownership.owner", "OTHER"), ("policy.version", "other"),
                           ("case.request_revision", "other")):
            with self.subTest(key=key):
                raw = saved.model_dump(mode="json")
                observation = next(o for o in raw["origin_checkpoint"]["observations"]
                                   if o["authority"] + "." + o["fact"] == key)
                observation["value"] = value
                raw["origin_hash"] = fingerprint(raw["origin_checkpoint"])
                with self.assertRaises(ValueError):
                    WaitRecordV1.model_validate_json(json.dumps(raw))

    def test_real_exit_after_envelope_before_prepare_retains_original(self):
        self.fx.store.close()
        # Child owns initial admission in a separate durable fixture directory.
        with tempfile.TemporaryDirectory() as folder:
            script = """import os, sys
from test_operator_wait_gateway import HostWaitFixture
fx = HostWaitFixture(sys.argv[1])
def hook(intent, sources, checkpoint):
    fx.persist(intent, sources, checkpoint)
    os._exit(73)
fx.gateway.enqueue_operator_packet('C1', 'review_facts', before_prepare=hook)
os._exit(74)
"""
            result = subprocess.run([sys.executable, "-c", script, folder], capture_output=True, text=True)
            self.assertEqual(result.returncode, 73, result.stderr)
            reopened = HostWaitFixture(folder, reopen=True)
            self.addCleanup(reopened.store.close)
            saved = reopened.store.load_wait_record(reopened.question_id)
            self.assertEqual(reopened.store.intents("C1"), ())
            self.assertEqual(reopened.world.effect_count("enqueue_handoff"), 0)
            self.assertEqual(reopened.gateway.enqueue_operator_packet("C1", "coverage_review").status, "verified")
            self.assertEqual(reopened.store.intents("C1")[0].intent, saved.communication_intent)
            self.assertEqual(reopened.world.effect_count("enqueue_handoff"), 1)


if __name__ == "__main__":
    unittest.main()
