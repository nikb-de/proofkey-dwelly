"""Public consumer composition; synthetic owner fixtures do not activate handoff."""
import tempfile
import unittest
from proofkey.contracts import OperatorDecision
from proofkey.ownership_contracts import OperatorDecisionSubmissionV1, OperatorDispositionV1
from ownership_support import Harness, make_binding, DEADLINE


class OwnershipTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.h = Harness(self.folder.name)
        self.addCleanup(self.h.store.close)

    def service(self):
        from proofkey.ownership import OwnershipService
        return OwnershipService(self.h.profile, self.h.bundle, self.h.store, self.h.clock, gateway=self.h.gateway)

    def decision(self, **changes):
        data = dict(decision_id="D1", replay_id="R1", packet_id="P1", packet_hash="b"*64,
            packet_revision="v1", binding=make_binding(), owner="OP1", epoch=0, state_revision="v1",
            actor_id="OP1", proof_reference="synthetic-operator-proof", decision="clarify", scope=[],
            expires_at=DEADLINE, simulated=True)
        return OperatorDecisionSubmissionV1(decision=OperatorDecision.model_validate({**data, **changes}),
            content_hash="c"*64, effect_scope=None)

    def test_recorded_nonaction_is_not_stop_reply_or_effect(self):
        before = self.h.store.checkpoint("C1")
        submission = self.decision(decision="stop")
        result = self.service().validate_decision(submission, self.h.auth)
        self.assertTrue(result.allowed)
        self.assertEqual(self.h.store.decision_record(make_binding(), "D1"), submission)
        after = self.h.store.checkpoint("C1")
        self.assertEqual(after.phase, before.phase)
        self.assertEqual(after.stop, before.stop)
        self.assertEqual(after.budget.effects, 0)
        self.assertEqual(after.budget.tool_calls, 5)

    def test_disposition_is_immutable_record_only(self):
        record = OperatorDispositionV1(record_id="disp1", replay_id="disp-replay", binding=make_binding(),
            packet_id="P1", packet_hash="b"*64, packet_revision="v1", content_hash="c"*64,
            owner="OP1", epoch=0, state_revision="v1", actor_id="OP1", proof_reference="synthetic-operator-proof",
            disposition="refund_review", rationale="synthetic review only", evidence_refs=[], expires_at=DEADLINE, simulated=True)
        actual = self.service().record_disposition(record, self.h.auth)
        self.assertEqual(actual, record)
        self.assertEqual(self.h.store.checkpoint("C1").budget.effects, 0)
        self.assertEqual(self.h.store.checkpoint("C1").phase, "wait_operator")

    def test_transfer_pending_original_has_one_effect_and_fence(self):
        current_reads = []
        current = self.h.gateway.read_current_ownership
        def observe_current(*args, **kwargs):
            result = current(*args, **kwargs)
            current_reads.append(result)
            return result
        self.h.gateway.read_current_ownership = observe_current
        result = self.service().transfer_result(self.h.transfer(), self.h.auth)
        self.assertTrue(result.simulated)
        self.assertEqual(result.ownership.owner, "OP1")
        self.assertEqual(result.ownership.state, "transfer_pending")
        cp = self.h.store.checkpoint("C1")
        self.assertEqual(cp.ownership_state, "transfer_pending")
        self.assertEqual(cp.budget.effects, 1)
        self.assertEqual(self.h.world.effect_count("transfer_owner"), 1)
        self.assertEqual(cp.budget.tool_calls, 19)
        record = self.h.store.transfer_record(self.h.transfer().transfer_id)
        self.assertEqual(record.lifecycle, "pending")
        self.assertEqual(record.source_receipt.kind, "transfer_pending_v1")
        self.assertEqual(current_reads[0].ownership.state, "transfer_pending")
        self.assertEqual(next(o.value for o in current_reads[0].observations if o.authority+"."+o.fact=="ownership.state"), "pending")
        self.assertEqual(current_reads[0].ownership.transfer_id, record.intent.transfer_id)

    def test_actual_target_acceptance_needs_current_confirmation_and_advances_once(self):
        self.h.store.close()
        self.folder.cleanup()
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.h = Harness(self.folder.name, direct=True)
        self.addCleanup(self.h.store.close)
        before = self.h.store.checkpoint("C1")
        actual = self.service().transfer_result(self.h.transfer(), self.h.auth)
        self.assertEqual(actual.ownership.owner, "OP2")
        self.assertEqual(actual.ownership.epoch, 1)
        self.assertEqual(actual.ownership.state, "accepted")
        cp = self.h.store.checkpoint("C1")
        self.assertEqual(cp.phase, before.phase)
        self.assertEqual(cp.stop, before.stop)
        self.assertEqual(cp.budget.effects, 1)
        self.assertEqual(self.h.world.effect_count("transfer_owner"), 1)

    def test_separate_synthetic_packet_change_cannot_accept_pending_original(self):
        from proofkey.ownership_contracts import SyntheticTargetAcceptanceV1
        self.assertEqual(self.service().transfer_result(self.h.transfer(), self.h.auth).ownership.state,
            "transfer_pending")
        record = self.h.store.transfer_record(self.h.transfer().transfer_id)
        instruction = SyntheticTargetAcceptanceV1(original=record.source_receipt.original,
            packet=record.registration_source.packet, target_owner=record.intent.target_owner,
            expected_revisions=record.effect.expected_revisions, expires_at=record.intent.expires_at,
            fixture_hash=record.registration_source.grant.fixture_hash,
            evidence_ref="synthetic-separate-stale-packet-control", simulated=True)
        # This explicit trusted synthetic driver mutation is NOT an automatic
        # reschedule side effect, consumer authority, or a new grant producer.
        self.h.world.mutate("operator.packet_hash", "d"*64)
        self.assertFalse(self.h.world.deliver_target_acceptance(instruction))
        self.assertEqual(self.h.store.transfer_record(record.intent.transfer_id), record)
        self.assertEqual(self.h.store.checkpoint("C1").ownership_state, "transfer_pending")
        self.assertEqual(self.h.world.effect_count("transfer_owner"), 1)
        self.assertEqual(self.h.store.checkpoint("C1").budget.tool_calls, 19)

    def test_pending_source_without_complete_local_original_cannot_infer_transfer_id(self):
        from proofkey.journal import JournalFailure
        from proofkey.policy import GateDenied
        # Trusted synthetic setup invokes the real public source; it does not
        # fabricate a local registration or grant the consumer a missing ID.
        effect = self.h.effect()
        self.h.bundle.operator.transfer_owner(effect, auth=self.h.auth)
        with self.assertRaises((JournalFailure, GateDenied)):
            self.h.gateway.read_current_ownership(make_binding(), self.h.auth)
        self.assertEqual(self.h.store.checkpoint("C1").budget.tool_calls, 5)
        self.assertEqual(self.h.store.checkpoint("C1").budget.effects, 0)
        self.assertEqual(self.h.store.checkpoint("C1").ownership_state, "accepted")
        self.assertEqual(self.h.world.effect_count("transfer_owner"), 1)

    def test_engine_guarded_decision_entry_uses_same_gateway(self):
        from proofkey.engine import WorkflowEngine
        engine = WorkflowEngine(self.h.profile, self.h.bundle, self.h.store, self.h.clock, gateway=self.h.gateway)
        self.assertTrue(engine.validate_operator_decision(self.decision(), self.h.auth).allowed)
        self.assertEqual(self.h.store.checkpoint("C1").budget.tool_calls, 5)

    def test_approved_decision_dispatch_is_one_use_actual_business(self):
        from proofkey.contracts import RevisionVector
        from proofkey.ownership_contracts import DecisionEffectScopeV1
        from proofkey.policy import required_fields, OWNER_FIELDS
        from ownership_support import make_intent
        from proofkey.identity import fingerprint
        cp = self.h.store.checkpoint("C1")
        self.h.store.save_checkpoint(cp.model_copy(update={"phase":"window_gate", "next_gate":"window_gate"}))
        revisions = self.h.world.material_revisions().revisions
        fields = required_fields(self.h.profile, "reschedule") | OWNER_FIELDS
        effect = make_intent(profile_version=self.h.profile.version,
            process_version=self.h.profile.processes["reschedule_window"].version,
            ownership_state_revision="v1", ownership_epoch=0, decision_id="D1",
            expected_revisions=RevisionVector(revisions={k: revisions[k] for k in fields}))
        data = self.decision().decision.model_dump()
        data.update(decision="approve", scope=["reschedule"])
        submission = OperatorDecisionSubmissionV1(decision=OperatorDecision.model_validate(data), content_hash="c"*64,
            effect_scope=DecisionEffectScopeV1(operation="reschedule", stage="commit", action_id=effect.action_id,
                argument_fingerprint=fingerprint(effect.arguments)))
        service = self.service()
        self.assertTrue(service.validate_decision(submission, self.h.auth).allowed)
        result = service.execute_decision("D1", effect, self.h.auth)
        self.assertEqual(result.status, "verified")
        self.assertEqual(self.h.world.effect_count("reschedule"), 1)
        self.assertEqual(self.h.store.checkpoint("C1").budget.effects, 1)
        # Entered originals only reread; no second business entry or consumption.
        self.assertEqual(service.execute_decision("D1", effect, self.h.auth).status, "verified")
        self.assertEqual(self.h.world.effect_count("reschedule"), 1)
        self.assertEqual(self.h.store.checkpoint("C1").budget.effects, 1)

    def test_transfer_changed_body_and_material_are_denied_without_entry(self):
        from proofkey.policy import GateDenied
        for field, value in (("customer.consent", "revoked"), ("delivery.risk", "unsafe"),
                              ("operator.packet_hash", "d"*64), ("ownership.epoch", 7),
                              ("policy.version", "v9")):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as folder:
                h = Harness(folder)
                try:
                    h.world.mutate(field, value)
                    service = type(self.service())(h.profile, h.bundle, h.store, h.clock, gateway=h.gateway)
                    with self.assertRaises(GateDenied):
                        service.transfer_result(h.transfer(), h.auth)
                    self.assertEqual(h.store.checkpoint("C1").budget.effects, 0)
                    self.assertEqual(h.world.effect_count("transfer_owner"), 0)
                finally:
                    h.store.close()

    def test_missing_registry_cannot_be_installed_by_consumer(self):
        from proofkey.policy import GateDenied
        with tempfile.TemporaryDirectory() as folder:
            h = Harness(folder, registry=False)
            try:
                service = type(self.service())(h.profile, h.bundle, h.store, h.clock, gateway=h.gateway)
                with self.assertRaisesRegex(GateDenied, "configuration_unavailable"):
                    service.transfer_result(h.transfer(), h.auth)
                self.assertEqual(h.store.checkpoint("C1").budget.effects, 0)
                self.assertEqual(h.store.checkpoint("C1").budget.tool_calls, 6)
            finally:
                h.store.close()

    def test_prepared_original_reuses_exact_effect_after_reopen(self):
        from proofkey.policy import GateDenied
        from proofkey.journal import CaseStore
        # Real committed public registration is forwarded; deterministic interrupt
        # before public entry here is not represented as a process crash.
        actual = self.h.gateway.execute_registered_transfer
        def interrupt(*args, **kwargs):
            raise GateDenied("synthetic-before-entry")
        self.h.gateway.execute_registered_transfer = interrupt
        with self.assertRaises(GateDenied):
            self.service().transfer_result(self.h.transfer(), self.h.auth)
        original = self.h.store.transfer_record(self.h.transfer().transfer_id)
        self.h.store.close()
        self.h.store = CaseStore(self.h.journal_path, ownership_processes=self.h.registry)
        from proofkey.gateway import ActionGateway
        self.h.gateway = ActionGateway(self.h.profile, self.h.bundle, self.h.store, self.h.clock, self.h.auth)
        self.addCleanup(self.h.store.close)
        self.assertEqual(self.service().transfer_result(self.h.transfer(), self.h.auth).ownership.owner, "OP1")
        self.assertEqual(self.h.store.transfer_record(original.intent.transfer_id).effect, original.effect)
        self.assertEqual(self.h.world.effect_count("transfer_owner"), 1)
        self.assertEqual(self.h.store.checkpoint("C1").budget.tool_calls, 19)

    def test_wrong_target_or_changed_expiry_never_creates_replacement_original(self):
        from proofkey.policy import GateDenied
        from datetime import timedelta
        with tempfile.TemporaryDirectory() as folder:
            h = Harness(folder)
            try:
                service = type(self.service())(h.profile, h.bundle, h.store, h.clock, gateway=h.gateway)
                with self.assertRaises(GateDenied):
                    service.transfer_result(h.transfer(target_owner="OP3"), h.auth)
                self.assertEqual(h.store.intents("C1"), ())
            finally:
                h.store.close()
        self.service().transfer_result(self.h.transfer(), self.h.auth)
        original = self.h.store.transfer_record(self.h.transfer().transfer_id)
        with self.assertRaisesRegex(GateDenied, "immutable_intent_conflict"):
            self.service().transfer_result(self.h.transfer(expires_at=DEADLINE-timedelta(seconds=1)), self.h.auth)
        self.assertEqual(self.h.store.transfer_record(original.intent.transfer_id), original)

    def test_genuine_exit_boundaries_preserve_original_debt_and_fence(self):
        import subprocess
        import sys
        from pathlib import Path
        from proofkey.journal import CaseStore
        from proofkey.adapters.world import SimulatedWorld
        from ownership_support import FakeClock, NOW
        from datetime import timedelta
        for boundary, code, tools, effects, source_count, lifecycle in (
            ("registration",81,6,0,0,"prepared"), ("debit",82,13,1,0,"prepared"),
            ("source_acceptance",83,13,1,1,"prepared"), ("terminal",84,19,1,1,"accepted")):
            with self.subTest(boundary=boundary), tempfile.TemporaryDirectory() as folder:
                child = subprocess.run([sys.executable, str(Path(__file__).with_name("ownership_support.py")), folder, boundary],
                    capture_output=True, text=True, timeout=20)
                self.assertEqual(child.returncode, code, child.stdout+child.stderr)
                import json
                receipt = json.loads(child.stdout)
                self.assertEqual(receipt["exit_code"], code)
                self.assertEqual(receipt["tool_calls"], tools)
                self.assertEqual(receipt["effects"], effects)
                print(child.stdout.strip(), flush=True)
                store = CaseStore(Path(folder)/"journal.sqlite", ownership_processes=self.h.registry)
                try:
                    cp = store.checkpoint("C1")
                    record = store.transfer_record(self.h.transfer().transfer_id)
                    self.assertEqual(record.lifecycle, lifecycle)
                    self.assertEqual(cp.budget.tool_calls, tools)
                    self.assertEqual(cp.budget.effects, effects)
                    self.assertEqual(cp.ownership_state, "accepted" if boundary=="terminal" else "transfer_pending")
                    self.assertEqual(store.intent(record.effect.action_id).intent, record.effect)
                    world = SimulatedWorld(Path(folder)/"source.sqlite", Path(folder)/"source.json",
                        profile=self.h.profile, clock=FakeClock(NOW+timedelta(seconds=30)))
                    self.assertEqual(world.effect_count("transfer_owner"), source_count)
                    if boundary in {"debit", "source_acceptance"}:
                        self.assertEqual(store.entry("effect:"+record.effect.action_id+":1").state, "active")
                        self.assertEqual(cp.budget.active_seconds, 10)
                finally:
                    store.close()

    def test_monotonic_slice_expiry_after_actual_transfer_debit_never_calls_port(self):
        from proofkey.execution import ExecutionContext
        from proofkey.engine import WorkflowEngine
        from proofkey.policy import GateDenied
        from ownership_support import MonotonicClock
        from datetime import timedelta
        clock = MonotonicClock()
        self.h.store.close()
        self.folder.cleanup()
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        # Constructor-installed same trusted clock, never private source mutation.
        self.h = Harness(self.folder.name, clock=clock)
        self.addCleanup(self.h.store.close)
        actual = self.h.store.begin_registered_transfer
        def reserve(*args, **kwargs):
            lease = actual(*args, **kwargs)
            clock.advance(lease.reserved_seconds+0.1, utc=False)
            return lease
        self.h.store.begin_registered_transfer = reserve
        engine = WorkflowEngine(self.h.profile, self.h.bundle, self.h.store, clock, gateway=self.h.gateway)
        context = ExecutionContext.capture(clock.now()+timedelta(seconds=40), clock)
        with self.assertRaises(GateDenied):
            engine.transfer(self.h.transfer(), self.h.auth, execution=context)
        cp = self.h.store.checkpoint("C1")
        self.assertEqual(cp.budget.effects, 1)
        self.assertEqual(cp.budget.tool_calls, 13)
        self.assertEqual(cp.budget.active_seconds, 10)
        self.assertEqual(self.h.world.effect_count("transfer_owner"), 0)
        self.assertEqual(self.h.store.transfer_record(self.h.transfer().transfer_id).lifecycle, "outcome_unknown")

    def test_all_engine_entries_guard_creator_and_nonreentrancy_before_debt(self):
        import threading
        from proofkey.engine import WorkflowEngine
        from proofkey.policy import GateDenied
        engine = WorkflowEngine(self.h.profile, self.h.bundle, self.h.store, self.h.clock, gateway=self.h.gateway)
        entries = [lambda: engine.transfer(self.h.transfer(), self.h.auth),
            lambda: engine.reconcile_transfer(self.h.transfer().transfer_id, self.h.auth),
            lambda: engine.validate_operator_decision(self.decision(), self.h.auth),
            lambda: engine.record_operator_disposition(None, self.h.auth),
            lambda: engine.execute_operator_decision("D1", None, self.h.auth)]
        outcomes = []
        def foreign():
            for entry in entries:
                try:
                    entry()
                    outcomes.append("unexpected")
                except GateDenied:
                    outcomes.append("denied")
        thread = threading.Thread(target=foreign)
        thread.start()
        thread.join(5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(outcomes, ["denied"]*5)
        with engine._execution_scope(None):
            for entry in entries:
                with self.assertRaises(GateDenied):
                    entry()
        self.assertEqual(self.h.store.checkpoint("C1").budget.tool_calls, 0)
        self.assertEqual(self.h.world.calls, ())

    def test_monotonic_slice_expiry_during_actual_port_resolution_is_fenced(self):
        from dataclasses import replace
        from datetime import timedelta
        from proofkey.execution import ExecutionContext
        from proofkey.engine import WorkflowEngine
        from proofkey.gateway import ActionGateway
        from proofkey.policy import GateDenied
        from ownership_support import MonotonicClock
        clock = MonotonicClock()
        with tempfile.TemporaryDirectory() as folder:
            h = Harness(folder, clock=clock)
            try:
                port = h.bundle.operator
                class Port:
                    def __getattr__(self, name):
                        target = getattr(port, name)
                        if name == "transfer_owner":
                            clock.advance(10.1, utc=False)
                        return target
                bundle = replace(h.bundle, operator=Port())
                gateway = ActionGateway(h.profile, bundle, h.store, clock, h.auth)
                engine = WorkflowEngine(h.profile, bundle, h.store, clock, gateway=gateway)
                ctx = ExecutionContext.capture(clock.now()+timedelta(seconds=40), clock)
                with self.assertRaises(GateDenied):
                    engine.transfer(h.transfer(), h.auth, execution=ctx)
                self.assertEqual(h.world.effect_count("transfer_owner"), 0)
                self.assertEqual(h.store.checkpoint("C1").budget.effects, 1)
                self.assertEqual(h.store.checkpoint("C1").budget.active_seconds, 10)
                self.assertEqual(h.store.transfer_record(h.transfer().transfer_id).lifecycle, "outcome_unknown")
                self.assertFalse(gateway._execution_active)
                self.assertIsNone(gateway._timing)
            finally:
                h.store.close()

    def test_source_fault_after_entered_transfer_never_resends_or_proves_nonexecution(self):
        from proofkey.policy import GateDenied
        actual = self.h.bundle.operator.transfer_owner
        def dispatch_then_fault(*args, **kwargs):
            result = actual(*args, **kwargs)
            self.h.world.set_fault("read_owner", "timeout_before")
            return result
        self.h.bundle.operator.transfer_owner = dispatch_then_fault
        owner = self.service().transfer_result(self.h.transfer(), self.h.auth).ownership
        self.assertEqual(owner.owner, "OP1")
        record = self.h.store.transfer_record(self.h.transfer().transfer_id)
        self.assertEqual(record.lifecycle, "outcome_unknown")
        self.assertIsNone(record.source_receipt)
        before = self.h.world.effect_count("transfer_owner")
        self.service().reconcile_result(record.intent.transfer_id, self.h.auth)
        self.assertEqual(self.h.world.effect_count("transfer_owner"), before)
        self.assertEqual(self.h.store.checkpoint("C1").ownership_state, "transfer_pending")

    def test_terminal_rejection_requires_typed_original_and_current_predecessor(self):
        self.h.world.set_fault("transfer_owner", "business_rejection")
        self.h.world.set_fault("read_owner", "terminal_not_executed")
        result = self.service().transfer_result(self.h.transfer(), self.h.auth)
        record = self.h.store.transfer_record(self.h.transfer().transfer_id)
        self.assertEqual(record.lifecycle, "rejected", self.h.store.intent(record.effect.action_id).verification)
        self.assertEqual(record.source_receipt.nonexecution.status, "proven")
        self.assertEqual(result.ownership.owner, "OP1")
        self.assertEqual(result.ownership.state, "accepted")
        self.assertEqual(self.h.world.effect_count("transfer_owner"), 0)
        self.assertEqual(self.h.store.checkpoint("C1").budget.effects, 1)

    def test_sticky_stop_between_acceptance_and_confirmation_retains_unknown_fence(self):
        with tempfile.TemporaryDirectory() as folder:
            h = Harness(folder, direct=True)
            try:
                actual = h.bundle.operator.transfer_owner
                def accept_then_stop(*args, **kwargs):
                    result = actual(*args, **kwargs)
                    h.store.set_stop("C1", "G1")
                    return result
                h.bundle.operator.transfer_owner = accept_then_stop
                service = type(self.service())(h.profile, h.bundle, h.store, h.clock, gateway=h.gateway)
                result = service.transfer_result(h.transfer(), h.auth)
                self.assertEqual(result.ownership.owner, "OP1")
                self.assertEqual(h.store.transfer_record(h.transfer().transfer_id).lifecycle, "outcome_unknown")
                self.assertTrue(h.store.checkpoint("C1").stop.requested)
                self.assertEqual(h.store.checkpoint("C1").ownership_state, "transfer_pending")
                self.assertEqual(h.world.effect_count("transfer_owner"), 1)
                self.assertEqual(h.store.checkpoint("C1").budget.tool_calls, 14)
            finally:
                h.store.close()

    def test_foreign_pending_original_cannot_be_confirmed_by_correct_tuple(self):
        current = self.h.gateway.read_current_ownership
        def foreign(*args, **kwargs):
            result = current(*args, **kwargs)
            return result.model_copy(update={"ownership": result.ownership.model_copy(update={"transfer_id":"foreign"})})
        self.h.gateway.read_current_ownership = foreign
        self.service().transfer_result(self.h.transfer(), self.h.auth)
        record = self.h.store.transfer_record(self.h.transfer().transfer_id)
        self.assertEqual(record.lifecycle, "outcome_unknown")
        self.assertIsNone(record.source_receipt)
        self.assertEqual(self.h.store.checkpoint("C1").budget.effects, 1)

    def test_unknown_current_wire_state_retains_full_read_reservation(self):
        from proofkey.contracts import AuthorityReadback
        actual = self.h.bundle.operator.read_owner
        def unknown(request):
            result = actual(request)
            if request.purpose == "current_owner" and request.target.authority == "ownership":
                data = result.model_dump()
                for obs in data["observations"]:
                    if obs["fact"] == "state":
                        obs["value"] = "unknown-new-state"
                return AuthorityReadback.model_validate(data)
            return result
        self.h.bundle.operator.read_owner = unknown
        self.service().transfer_result(self.h.transfer(), self.h.auth)
        record = self.h.store.transfer_record(self.h.transfer().transfer_id)
        self.assertEqual(record.lifecycle, "outcome_unknown")
        self.assertIsNone(record.source_receipt)
        self.assertEqual(self.h.store.checkpoint("C1").budget.active_seconds, 10)

    def test_prior_canonical_pending_current_snapshot_remains_compatible(self):
        from proofkey.ownership_contracts import OwnershipCurrentReadV1
        current = self.h.gateway.read_current_ownership
        def canonical_fixture(*args, **kwargs):
            actual = current(*args, **kwargs)
            # Explicit synthetic prior canonical wire compatibility, not a claim
            # that this adapter returns canonical text or a runtime source rewrite.
            observations = [o.model_copy(update={"value":"transfer_pending"})
                if o.authority+"."+o.fact == "ownership.state" else o for o in actual.observations]
            return OwnershipCurrentReadV1.model_validate({**actual.model_dump(), "observations": observations})
        self.h.gateway.read_current_ownership = canonical_fixture
        self.service().transfer_result(self.h.transfer(), self.h.auth)
        self.assertEqual(self.h.store.transfer_record(self.h.transfer().transfer_id).lifecycle, "pending")

    def test_decision_reserved_slice_expiry_default_none_never_calls_port(self):
        from ownership_support import approval
        with tempfile.TemporaryDirectory() as folder:
            h = Harness(folder, phase="window_gate")
            try:
                service = type(self.service())(h.profile, h.bundle, h.store, h.clock, gateway=h.gateway)
                submission, effect = approval(h)
                self.assertTrue(service.validate_decision(submission, h.auth).allowed)
                actual = h.store.begin_dispatch
                def reserve(*args, **kwargs):
                    lease = actual(*args, **kwargs)
                    h.clock.advance(lease.reserved_seconds+0.1)
                    return lease
                h.store.begin_dispatch = reserve
                result = service.execute_decision("D1", effect, h.auth)
                self.assertEqual(result.status, "outcome_unknown")
                self.assertEqual(sum(c.operation=="reschedule" and c.purpose=="dispatch" for c in h.world.calls), 0)
                self.assertEqual(h.store.checkpoint("C1").budget.effects, 1)
                self.assertEqual(h.store.checkpoint("C1").budget.active_seconds, 10)
            finally:
                h.store.close()

    def test_terminal_inventory_cannot_substitute_missing_fresh_current_confirmation(self):
        from proofkey.policy import GateDenied
        with tempfile.TemporaryDirectory() as folder:
            h = Harness(folder, direct=True)
            try:
                service = type(self.service())(h.profile, h.bundle, h.store, h.clock, gateway=h.gateway)
                self.assertEqual(service.transfer_result(h.transfer(), h.auth).ownership.owner, "OP2")
                # Exact original read can complete within cap, but all five fresh
                # current reads cannot fit after nineteen prior calls. Never claim
                # fresh current accepted ownership from the saved terminal record.
                with self.assertRaises(GateDenied):
                    service.reconcile_result(h.transfer().transfer_id, h.auth)
                self.assertEqual(h.store.transfer_record(h.transfer().transfer_id).lifecycle, "accepted")
                self.assertEqual(h.world.effect_count("transfer_owner"), 1)
                self.assertEqual(h.store.checkpoint("C1").budget.tool_calls, 24)
            finally:
                h.store.close()

    def test_terminal_current_scope_rejection_is_not_replaced_by_saved_acceptance(self):
        from proofkey.policy import GateDenied
        with tempfile.TemporaryDirectory() as folder:
            h = Harness(folder, direct=True)
            try:
                service = type(self.service())(h.profile, h.bundle, h.store, h.clock, gateway=h.gateway)
                service.transfer_result(h.transfer(), h.auth)
                actual = h.bundle.case.read_case
                def rejected_current(request):
                    # Actual public source call with deliberately invalid forwarded
                    # current-read proof; original-read proof remains unchanged.
                    if request.purpose == "current_owner":
                        request = request.model_copy(update={"proof_reference":"wrong"})
                    return actual(request)
                h.bundle.case.read_case = rejected_current
                with self.assertRaises(GateDenied):
                    service.reconcile_result(h.transfer().transfer_id, h.auth)
                self.assertEqual(h.store.transfer_record(h.transfer().transfer_id).lifecycle, "accepted")
                self.assertEqual(h.world.effect_count("transfer_owner"), 1)
            finally:
                h.store.close()

    def test_accepted_target_reader_has_no_fresh_action_grant(self):
        from ownership_support import make_auth
        with tempfile.TemporaryDirectory() as folder:
            h = Harness(folder, direct=True)
            try:
                service = type(self.service())(h.profile, h.bundle, h.store, h.clock, gateway=h.gateway)
                owner = service.transfer_result(h.transfer(), h.auth).ownership
                target = make_auth(caller_id="OP2", proof_reference="synthetic-target-proof")
                d = self.decision().decision.model_dump()
                d.update(decision_id="D2", replay_id="R2", owner="OP2", actor_id="OP2", epoch=owner.epoch,
                    state_revision=owner.state_revision, proof_reference=target.proof_reference)
                submission = OperatorDecisionSubmissionV1(decision=OperatorDecision.model_validate(d), content_hash="c"*64,
                    effect_scope=None)
                self.assertFalse(service.validate_decision(submission, target).allowed)
                self.assertEqual(h.store.checkpoint("C1").budget.tool_calls, 24)
                self.assertEqual(h.store.checkpoint("C1").budget.effects, 1)
                self.assertEqual(h.world.effect_count("transfer_owner"), 1)
                self.assertEqual(h.store.checkpoint("C1").binding.principal_id, "U1")
            finally:
                h.store.close()

    def test_decision_cannot_replace_current_customer_consent_or_recorded_scope(self):
        from ownership_support import approval
        for mutation in ("consent", "scope", "content", "expiry"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as folder:
                h = Harness(folder, phase="window_gate")
                try:
                    service = type(self.service())(h.profile, h.bundle, h.store, h.clock, gateway=h.gateway)
                    submission, effect = approval(h)
                    if mutation=="content":
                        bad = submission.model_copy(update={"content_hash":"d"*64})
                        self.assertFalse(service.validate_decision(bad, h.auth).allowed)
                    else:
                        self.assertTrue(service.validate_decision(submission, h.auth).allowed)
                        if mutation=="consent":
                            h.world.mutate("customer.consent", "revoked")
                        elif mutation=="scope":
                            from proofkey.identity import fingerprint
                            arguments = {"slot":"S2"}
                            effect = effect.model_copy(update={"arguments":arguments,"argument_fingerprint":fingerprint(arguments)})
                        else:
                            h.clock.advance((DEADLINE-h.clock.now()).total_seconds())
                        self.assertEqual(service.execute_decision("D1", effect, h.auth).status, "rejected")
                    self.assertEqual(h.world.effect_count("reschedule"), 0)
                    self.assertEqual(h.store.checkpoint("C1").budget.effects, 0)
                finally:
                    h.store.close()

    def test_foreign_or_wrong_current_pending_tuple_packet_keeps_unknown(self):
        from proofkey.ownership_contracts import OwnershipCurrentReadV1
        for mutation in ("revision", "packet"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as folder:
                h = Harness(folder)
                try:
                    current = h.gateway.read_current_ownership
                    def wrong(*args, **kwargs):
                        result = current(*args, **kwargs)
                        if mutation=="revision":
                            owner = result.ownership.model_copy(update={"state_revision":"wrong-revision"})
                            return result.model_copy(update={"ownership":owner})
                        packet = result.packet.model_copy(update={"packet_hash":"d"*64})
                        owner = result.ownership.model_copy(update={"packet_hash":"d"*64})
                        return result.model_copy(update={"packet":packet,"ownership":owner})
                    h.gateway.read_current_ownership = wrong
                    service = type(self.service())(h.profile,h.bundle,h.store,h.clock,gateway=h.gateway)
                    self.assertEqual(service.transfer_result(h.transfer(),h.auth).ownership.owner,"OP1")
                    self.assertEqual(h.store.transfer_record(h.transfer().transfer_id).lifecycle,"outcome_unknown")
                    self.assertEqual(h.store.checkpoint("C1").ownership_state,"transfer_pending")
                    self.assertEqual(h.world.effect_count("transfer_owner"),1)
                finally:
                    h.store.close()

    def test_transfer_registration_first_fences_recorded_decision_without_consumption(self):
        from ownership_support import approval
        submission, effect = approval(self.h)
        self.assertTrue(self.service().validate_decision(submission,self.h.auth).allowed)
        # Forward real atomic registration, stop orchestration before entry. This
        # deterministic public boundary ordering is not a simultaneous host race.
        from proofkey.policy import GateDenied
        def pause(*args,**kwargs):
            raise GateDenied("synthetic-registration-barrier")
        self.h.gateway.execute_registered_transfer = pause
        with self.assertRaises(GateDenied):
            self.service().transfer_result(self.h.transfer(),self.h.auth)
        self.assertEqual(self.service().execute_decision("D1",effect,self.h.auth).status,"rejected")
        self.assertEqual(self.h.world.effect_count("reschedule"),0)
        self.assertEqual(self.h.store.checkpoint("C1").budget.effects,0)
        self.assertEqual(self.h.store.decision_record(make_binding(),"D1"),submission)
        self.assertEqual(self.h.store.transfer_record(self.h.transfer().transfer_id).lifecycle,"prepared")

    def test_decision_first_then_declared_transfer_phase_does_not_undo_business(self):
        from ownership_support import approval
        from proofkey.policy import GateDenied
        with tempfile.TemporaryDirectory() as folder:
            h = Harness(folder,phase="window_gate")
            try:
                service = type(self.service())(h.profile,h.bundle,h.store,h.clock,gateway=h.gateway)
                submission,effect = approval(h)
                self.assertTrue(service.validate_decision(submission,h.auth).allowed)
                captured = []
                read_material = h.gateway.read_material_authorities
                def observe_material(*args,**kwargs):
                    observations = read_material(*args,**kwargs)
                    captured.extend(observations)
                    return observations
                h.gateway.read_material_authorities = observe_material
                self.assertEqual(service.execute_decision("D1",effect,h.auth).status,"verified")
                # Declared graph walk using public host checkpoints, never adding
                # a simultaneous transfer self-edge to the reschedule phase.
                from proofkey.process import ProcessController
                controller = ProcessController(h.profile,"reschedule_window")
                cp = h.store.checkpoint("C1")
                graph = {o.authority+"."+o.fact:o.value for o in captured}
                graph.update({"case.generation":"current","case.authority":"fresh","operator.packet":"current",
                    "customer.consent":"window"})
                for operation, facts in (("reschedule",graph),("read_effect",{"journal.original_effect":
                        __import__("proofkey.contracts",fromlist=["ReadTarget"]).ReadTarget(kind="original_effect",
                            operation=effect.operation,generation="G1",action_id=effect.action_id,
                            provider_key=effect.provider_key,fingerprint=effect.argument_fingerprint)}),
                        ("ask_operator",{})):
                    target = controller.next_phase(cp.phase,operation,facts)
                    self.assertIsNotNone(target,(cp.phase,operation))
                    cp = cp.model_copy(update={"phase":target,"next_gate":target})
                    h.store.save_checkpoint(cp)
                    cp = h.store.checkpoint("C1")
                self.assertEqual(cp.phase,"wait_reschedule_operator")
                def pause(*args,**kwargs):
                    raise GateDenied("synthetic-registration-barrier")
                h.gateway.execute_registered_transfer = pause
                with self.assertRaises(GateDenied):
                    service.transfer_result(h.transfer(),h.auth)
                self.assertEqual(h.world.effect_count("reschedule"),1)
                self.assertEqual(h.world.effect_count("transfer_owner"),0)
                self.assertEqual(h.store.intent(effect.action_id).state,"verified")
                self.assertEqual(h.store.checkpoint("C1").budget.tool_calls,24)
                self.assertEqual(h.store.checkpoint("C1").ownership_state,"transfer_pending")
            finally:
                h.store.close()
