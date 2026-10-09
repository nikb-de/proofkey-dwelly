"""Observable real-world/journal workflows; labels and prose do not prove outcomes."""
from dataclasses import replace
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest

from proofkey.contracts import ActionProposal, AuthorityObservation, AuthorityReadback, PhaseCheckpoint, ReadRequest
from proofkey.engine import WorkflowEngine
from proofkey.journal import CaseStore, JournalFailure
from support import build_test_runtime, make_auth, make_request


def goods_request(**changes):
    return make_request(**{"kind": "goods_refusal", "consent_mode": "unknown",
        "arguments": {"inventory": {"item-1": 1}}, **changes})


def service_request():
    return make_request(kind="service_refusal", consent_mode="unknown", arguments={"scope": "service"})


class ProcessCrash(BaseException):
    """Host interruption, not provider timeout or a business response."""


class CrashOnPhase(WorkflowEngine):
    def __init__(self, fx, phase):
        super().__init__(fx.profile, fx.world.bundle(), fx.store, fx.clock)
        self.crash_phase = phase

    def run_one_approved_phase(self, checkpoint, request, auth, **flags):
        if checkpoint.phase == self.crash_phase:
            raise ProcessCrash()
        return super().run_one_approved_phase(checkpoint, request, auth, **flags)


class ForwardPort:
    """Instrument the external boundary without swallowing journal/provider effects."""
    def __init__(self, real, **overrides):
        self.real, self.overrides = real, overrides

    def __getattr__(self, name):
        return self.overrides.get(name, getattr(self.real, name))


class WorkflowTests(unittest.TestCase):
    def fixture(self, folder, **changes):
        fx = build_test_runtime(folder, **changes)
        self.addCleanup(fx.store.close)
        return fx

    def test_window_selection_verifies_with_original_caps_and_no_unnecessary_handoff(self):
        # Catches wrong selected slot, an ungated/no-op write or duplicated entry.
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder)
            result = fx.engine.run(fx.request, fx.auth)
            self.assertEqual(result.status, "authorized")
            self.assertEqual(result.effects["reschedule"].status, "verified")
            self.assertEqual(result.effects["reschedule"].postcondition, {"slot": "S1"})
            self.assertEqual(fx.world.effect_count("reschedule"), 1)
            self.assertEqual(fx.world.effect_count("enqueue_handoff"), 0)
            budget = fx.store.checkpoint("C1").budget
            self.assertEqual(budget.planner_calls, 0)
            self.assertEqual(budget.effects, 1)
            self.assertLessEqual(budget.tool_calls, 24)
            self.assertEqual(budget.tool_calls, len(fx.world.calls))

    def test_exact_slot_never_selects_other_slot(self):
        with tempfile.TemporaryDirectory() as folder:
            request = make_request(kind="reschedule_exact", consent_mode="exact_slot", arguments={"slot": "S2"})
            fx = self.fixture(folder, request=request)
            result = fx.engine.run(request, fx.auth)
            self.assertEqual(result.status, "authorized")
            self.assertEqual(result.effects["reschedule"].status, "verified")
            self.assertEqual(result.effects["reschedule"].postcondition, {"slot": "S2"})
            self.assertEqual(fx.world.effect_count("reschedule"), 1)

    def test_whole_goods_refusal_and_return_have_independent_verified_receipts(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder, request=goods_request())
            result = fx.engine.run(fx.request, fx.auth)
            self.assertEqual(result.status, "authorized")
            self.assertEqual(set(result.effects), {"register_goods_refusal", "create_return"})
            self.assertEqual(result.effects["register_goods_refusal"].status, "verified")
            self.assertEqual(result.effects["create_return"].status, "verified")
            self.assertEqual(result.effects["create_return"].postcondition["returns.status"], "initiated")
            self.assertNotEqual(result.effects["register_goods_refusal"].action_id,
                                result.effects["create_return"].action_id)
            self.assertEqual(fx.world.effect_count("register_goods_refusal"), 1)
            self.assertEqual(fx.world.effect_count("create_return"), 1)
            self.assertEqual(fx.world.effect_count("enqueue_handoff"), 0)
            self.assertLessEqual(fx.store.checkpoint("C1").budget.tool_calls, 24)

    def test_refusal_survives_unknown_return(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder, request=goods_request())
            fx.world.set_fault("create_return", "timeout_after_execute")
            fx.world.set_fault("read_return", "timeout_before")
            result = fx.engine.run(fx.request, fx.auth)
            self.assertEqual(result.status, "authorized")
            self.assertEqual(result.effects["register_goods_refusal"].status, "verified")
            self.assertEqual(result.effects["create_return"].status, "outcome_unknown")
            self.assertEqual(fx.world.effect_count("register_goods_refusal"), 1)
            self.assertEqual(fx.world.effect_count("create_return"), 1)
            self.assertNotIn("refund", result.effects)

    def test_return_timeout_with_authoritative_readback_is_verified(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder, request=goods_request())
            fx.world.set_fault("create_return", "timeout_after_execute")
            result = fx.engine.run(fx.request, fx.auth)
            self.assertEqual(result.status, "authorized")
            self.assertEqual(result.effects["create_return"].status, "verified")
            self.assertEqual(fx.world.effect_count("register_goods_refusal"), 1)
            self.assertEqual(fx.world.effect_count("create_return"), 1)

    def test_return_business_rejection_retains_refusal(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder, request=goods_request())
            fx.world.set_fault("create_return", "business_rejection")
            result = fx.engine.run(fx.request, fx.auth)
            self.assertEqual(result.status, "authorized")
            self.assertEqual(result.effects["register_goods_refusal"].status, "verified")
            self.assertEqual(result.effects["create_return"].status, "rejected")
            self.assertEqual(fx.world.effect_count("create_return"), 0)

    def test_completed_service_registers_refusal_and_records_queue_only(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder, request=service_request())
            result = fx.engine.run(fx.request, fx.auth)
            self.assertEqual(result.status, "authorized")
            self.assertEqual(result.effects["register_service_refusal"].status, "verified")
            self.assertEqual(result.effects["enqueue_handoff"].status, "verified")
            self.assertEqual(result.handoff_status, "pending")
            self.assertEqual(fx.world.effect_count("register_service_refusal"), 1)
            self.assertEqual(fx.world.effect_count("enqueue_handoff"), 1)
            self.assertNotIn("refund", result.effects)
            self.assertNotIn("create_internal_case", result.effects)

    def test_service_handoff_rejection_does_not_erase_registration(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder, request=service_request())
            fx.world.set_fault("enqueue_handoff", "business_rejection")
            result = fx.engine.run(fx.request, fx.auth)
            self.assertEqual(result.status, "authorized")
            self.assertEqual(result.effects["register_service_refusal"].status, "verified")
            self.assertEqual(result.effects["enqueue_handoff"].status, "rejected")
            self.assertEqual(result.handoff_status, "rejected")
            self.assertEqual(fx.world.effect_count("enqueue_handoff"), 0)

    def test_wrong_proof_returns_generic_denial_without_case_history(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder)
            result = fx.engine.run(fx.request, make_auth(proof_reference="foreign-proof"))
            self.assertEqual(result.status, "denied")
            self.assertEqual(result.effects, {})
            self.assertIsNone(result.binding)
            self.assertEqual(fx.world.effect_count("reschedule"), 0)

    def test_window_uses_earliest_interval_even_when_provider_order_is_reversed(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder)
            fx.world.mutate("scheduling.capacity", ["S2", "S1"])
            result = fx.engine.run(fx.request, fx.auth)
            self.assertEqual(result.effects["reschedule"].postcondition, {"slot": "S1"})
            self.assertEqual(fx.world.effect_count("reschedule"), 1)

    def test_window_excludes_an_earlier_slot_outside_customer_window(self):
        with tempfile.TemporaryDirectory() as folder:
            request = make_request(arguments={"window_start": "2026-10-08T11:00:00+00:00",
                                             "window_end": "2026-10-08T12:00:00+00:00"})
            fx = self.fixture(folder, request=request)
            result = fx.engine.run(request, fx.auth)
            self.assertEqual(result.effects["reschedule"].postcondition, {"slot": "S2"})
            self.assertEqual(fx.world.effect_count("reschedule"), 1)

    def test_unavailable_exact_slot_does_not_switch_consent_mode(self):
        with tempfile.TemporaryDirectory() as folder:
            request = make_request(kind="reschedule_exact", consent_mode="exact_slot", arguments={"slot": "S2"})
            fx = self.fixture(folder, request=request)
            fx.world.mutate("scheduling.capacity", ["S1"])
            result = fx.engine.run(request, fx.auth)
            self.assertEqual(result.wait_status, "pending")
            self.assertEqual(fx.world.effect_count("reschedule"), 0)
            self.assertEqual(fx.store.original_request("C1", "G1").arguments, {"slot": "S2"})

    def test_partial_goods_never_expand_to_whole_order(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder, request=goods_request())
            fx.world.mutate("goods.inventory", {"item-1": 1, "item-2": 2})
            fx.world.mutate("goods.quantity", 3)
            result = fx.engine.run(fx.request, fx.auth)
            self.assertEqual(result.wait_status, "pending")
            self.assertEqual(fx.world.effect_count("register_goods_refusal"), 0)
            self.assertEqual(fx.world.effect_count("create_return"), 0)
            self.assertEqual(fx.store.original_request("C1", "G1").arguments, {"inventory": {"item-1": 1}})

    def test_unrequested_address_or_leftover_window_is_not_dropped(self):
        for request in (make_request(arguments={"window_start": "2026-10-08T10:00:00+00:00",
                                               "window_end": "2026-10-08T12:00:00+00:00", "address": "Elsewhere"}),
                        goods_request(arguments={"inventory": {"item-1": 1}, "window_start": "ignored"})):
            with self.subTest(kind=request.kind), tempfile.TemporaryDirectory() as folder:
                fx = self.fixture(folder, request=request)
                result = fx.engine.run(request, fx.auth)
                self.assertEqual(result.wait_status, "pending")
                self.assertEqual(fx.world.effect_count("reschedule"), 0)
                self.assertEqual(fx.world.effect_count("register_goods_refusal"), 0)

    def test_return_readback_wrong_object_inventory_quantity_or_destination_is_independent_conflict(self):
        for field, value in (("object_id", "O-foreign"), ("goods.inventory", {"other-item": 1}),
                             ("goods.quantity", 9), ("returns.destination", "D-other")):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as folder:
                fx = self.fixture(folder, request=goods_request())
                original = fx.engine.gateway.bundle.returns
                def corrupt(request, field=field, value=value):
                    read = original.read_return(request)
                    if field == "object_id":
                        return AuthorityReadback.model_validate({**read.model_dump(), "object_id": value})
                    observations = [AuthorityObservation.model_validate({**obs.model_dump(), "value": value})
                                    if obs.authority + "." + obs.fact == field else obs for obs in read.observations]
                    return AuthorityReadback.model_validate({**read.model_dump(), "observations": observations})
                fx.engine.gateway.bundle = replace(fx.engine.gateway.bundle,
                    returns=ForwardPort(original, read_return=corrupt))
                result = fx.engine.run(fx.request, fx.auth)
                self.assertEqual(result.effects["register_goods_refusal"].status, "verified")
                self.assertEqual(result.effects["create_return"].status, "conflict")
                self.assertEqual(fx.world.effect_count("register_goods_refusal"), 1)
                self.assertEqual(fx.world.effect_count("create_return"), 1)

    def test_refusal_rejection_or_unknown_never_authorizes_return(self):
        for fault in ("business_rejection", "timeout_before_execute"):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as folder:
                fx = self.fixture(folder, request=goods_request())
                fx.world.set_fault("register_goods_refusal", fault)
                result = fx.engine.run(fx.request, fx.auth)
                self.assertEqual(result.effects["register_goods_refusal"].status,
                                 "rejected" if fault == "business_rejection" else "outcome_unknown")
                self.assertEqual(fx.world.effect_count("create_return"), 0)
                self.assertNotIn("create_return", result.effects)

    def test_structured_execution_does_not_invoke_attached_planner(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder)
            class ForbiddenPlanner:
                def propose(self, *args):
                    raise AssertionError("Structured workflow entered a planner")
            engine = WorkflowEngine(fx.profile, fx.world.bundle(), fx.store, fx.clock, planner=ForbiddenPlanner())
            result = engine.run(fx.request, fx.auth)
            self.assertEqual(result.effects["reschedule"].status, "verified")
            self.assertEqual(fx.store.checkpoint("C1").budget.planner_calls, 0)

    def test_media_without_scoped_processor_waits_without_fabrication(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder, request=make_request(narrative="Please inspect attached context"))
            result = fx.engine.run(fx.request, fx.auth)
            self.assertEqual(result.media_status, "unavailable")
            self.assertEqual(result.wait_status, "pending")
            self.assertEqual(fx.world.effect_count("reschedule"), 0)
            self.assertEqual(fx.store.checkpoint("C1").budget.planner_calls, 0)

    def test_phase_and_exact_external_gate_are_committed_before_every_write(self):
        for request, operations in ((make_request(), {"reschedule": ("window_gate", "scheduling")}),
                                   (goods_request(), {"register_goods_refusal": ("refusal_gate", "delivery"),
                                                      "create_return": ("return_gate", "returns")}),
                                   (service_request(), {"register_service_refusal": ("refusal_gate", "delivery"),
                                                       "enqueue_handoff": ("refusal_complete", "operator")})):
            with self.subTest(kind=request.kind), tempfile.TemporaryDirectory() as folder:
                fx = self.fixture(folder, request=request)
                for operation, (phase, port) in operations.items():
                    original = getattr(fx.engine.gateway.bundle, port)
                    def checked(intent, *, deadline=None, operation=operation, phase=phase, original=original):
                        observer = CaseStore(Path(folder) / "journal.sqlite")
                        try:
                            saved = observer.checkpoint("C1")
                            self.assertEqual((saved.phase, saved.next_gate), (phase, operation))
                            self.assertEqual(observer.original_request("C1", "G1"), request)
                            self.assertEqual(observer.intent(intent.action_id).state, "dispatching")
                            self.assertEqual(intent.ownership_state_revision, "v1")
                            self.assertEqual(set(intent.expected_revisions.revisions),
                                             set(fx.profile.capabilities[operation].conditional_coverage.covered_fields))
                            self.assertEqual(fx.world.effect_count(operation), 0)
                        finally:
                            observer.close()
                        return getattr(original, operation)(intent, deadline=deadline)
                    fx.engine.gateway.bundle = replace(fx.engine.gateway.bundle,
                        **{port: ForwardPort(original, **{operation: checked})})
                result = fx.engine.run(request, fx.auth)
                self.assertEqual(result.status, "authorized")
                for operation in operations:
                    self.assertEqual(fx.world.effect_count(operation), 1)

    def test_checkpoint_commit_failure_prevents_any_external_effect(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder)
            def fail_external_gate_commit():
                row = fx.store._db.execute("SELECT checkpoint_json FROM cases WHERE case_id='C1'").fetchone()
                if row and row[0] and '"next_gate":"reschedule"' in row[0]:
                    raise JournalFailure("private-host-canary")
            fx.store._before_commit = fail_external_gate_commit
            result = fx.engine.run(fx.request, fx.auth)
            self.assertEqual(fx.world.effect_count("reschedule"), 0)
            self.assertFalse(any(c.operation == "reschedule" for c in fx.world.calls))
            self.assertNotIn("canary", result.model_dump_json())

    def test_saved_pre_effect_phases_reopen_at_exact_original_without_planner(self):
        phases = ("intake", "extraction", "completeness", "auth_gate", "read_authority", "window_gate")
        for phase in phases:
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as folder:
                fx = self.fixture(folder)
                with self.assertRaises(ProcessCrash):
                    CrashOnPhase(fx, phase).run(fx.request, fx.auth)
                before = fx.store.checkpoint("C1")
                self.assertEqual(before.phase, phase)
                fx.store.close()
                reopened = CaseStore(Path(folder) / "journal.sqlite")
                self.addCleanup(reopened.close)
                engine = WorkflowEngine(fx.profile, fx.world.bundle(), reopened, fx.clock)
                result = engine.recover("C1", fx.auth)
                self.assertEqual(result.status, "authorized")
                self.assertEqual(result.effects["reschedule"].status, "verified")
                self.assertEqual(reopened.original_request("C1", "G1"), fx.request)
                self.assertEqual(reopened.checkpoint("C1").deadline, before.deadline)
                self.assertEqual(reopened.checkpoint("C1").budget.planner_calls, 0)
                self.assertEqual(fx.world.effect_count("reschedule"), 1)

    def test_crash_after_write_reconciles_exact_original_without_second_transport(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder)
            original = fx.engine.gateway.bundle.scheduling
            def crash(intent, *, deadline=None):
                original.reschedule(intent, deadline=deadline)
                raise ProcessCrash()
            fx.engine.gateway.bundle = replace(fx.engine.gateway.bundle,
                scheduling=ForwardPort(original, reschedule=crash))
            with self.assertRaises(ProcessCrash):
                fx.engine.run(fx.request, fx.auth)
            before = fx.store.checkpoint("C1")
            self.assertEqual((before.phase, before.next_gate), ("window_gate", "reschedule"))
            intent = fx.store.intents("C1")[0].intent
            fx.store.close()
            reopened = CaseStore(Path(folder) / "journal.sqlite")
            self.addCleanup(reopened.close)
            result = WorkflowEngine(fx.profile, fx.world.bundle(), reopened, fx.clock).recover("C1", fx.auth)
            self.assertEqual(result.status, "authorized")
            self.assertEqual(result.effects["reschedule"].status, "verified")
            self.assertEqual(reopened.intent(intent.action_id).intent, intent)
            self.assertEqual(fx.world.effect_count("reschedule"), 1)
            self.assertEqual(sum(c.operation == "reschedule" for c in fx.world.calls), 1)
            self.assertGreaterEqual(reopened.checkpoint("C1").budget.active_seconds, before.budget.active_seconds)

    def test_unknown_return_recovery_reads_only_unfinished_original(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder, request=goods_request())
            fx.world.set_fault("create_return", "timeout_after_execute")
            fx.world.set_fault("read_return", "timeout_before")
            initial = fx.engine.run(fx.request, fx.auth)
            self.assertEqual(initial.effects["create_return"].status, "outcome_unknown")
            before = len(fx.world.calls)
            checkpoint = fx.store.checkpoint("C1")
            fx.world.set_fault("read_return", "none")
            result = WorkflowEngine(fx.profile, fx.world.bundle(), fx.store, fx.clock).recover("C1", fx.auth)
            self.assertEqual(result.status, "authorized")
            self.assertEqual(result.effects["create_return"].status, "verified")
            self.assertEqual(result.effects["register_goods_refusal"], initial.effects["register_goods_refusal"])
            tail = fx.world.calls[before:]
            self.assertEqual(sum(c.operation == "read_return" for c in tail), 1)
            self.assertFalse(any(c.operation in {"register_goods_refusal", "create_return", "read_refusal"} for c in tail))
            self.assertEqual(fx.store.checkpoint("C1").deadline, checkpoint.deadline)
            self.assertEqual(fx.store.checkpoint("C1").budget.tool_calls, 24)

    def test_foreign_or_missing_recovery_auth_cannot_disclose_saved_effect(self):
        for auth in (None, make_auth(proof_reference="foreign-proof"), make_auth(caller_id="OP1", proof_reference="synthetic-operator-proof")):
            with self.subTest(auth=auth), tempfile.TemporaryDirectory() as folder:
                fx = self.fixture(folder)
                with self.assertRaises(ProcessCrash):
                    CrashOnPhase(fx, "verification").run(fx.request, fx.auth)
                result = WorkflowEngine(fx.profile, fx.world.bundle(), fx.store, fx.clock).recover("C1", auth)
                self.assertEqual(result.status, "denied")
                self.assertEqual(result.effects, {})
                self.assertIsNone(result.binding)
                self.assertEqual(fx.world.effect_count("reschedule"), 1)

    def test_stopped_checkpoint_does_not_resume_or_resend(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder)
            with self.assertRaises(ProcessCrash):
                CrashOnPhase(fx, "window_gate").run(fx.request, fx.auth)
            fx.store.set_stop("C1", "G1")
            before = fx.store.checkpoint("C1")
            result = WorkflowEngine(fx.profile, fx.world.bundle(), fx.store, fx.clock).recover("C1", fx.auth)
            self.assertTrue(fx.store.checkpoint("C1").stop.requested)
            self.assertEqual(result.status, "denied")
            self.assertEqual(fx.store.checkpoint("C1").phase, before.phase)
            self.assertEqual(fx.world.effect_count("reschedule"), 0)

    def test_legacy_profile_cannot_silently_activate_business_scope(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder, profile_name="flat-v1")
            result = fx.engine.run(fx.request, fx.auth)
            self.assertNotEqual(result.effects.get("reschedule", None), "verified")
            self.assertEqual(fx.world.effect_count("reschedule"), 0)

    def test_pending_stronger_saved_return_is_preserved_without_receive_dispatch(self):
        # Recovery contract only: original initiation requested later physical
        # receipt; initiated readback is pending against that stronger original.
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder, request=goods_request())
            engine = CrashOnPhase(fx, "return_gate")
            with self.assertRaises(ProcessCrash):
                engine.run(fx.request, fx.auth)
            def stronger(request, observations):
                return ActionProposal(operation="create_return", stage="initiate",
                    arguments={"inventory": {"item-1": 1}, "destination": "D1"}, evidence_refs=[]), {
                    "returns.status": "received", "inventory": {"item-1": 1}, "quantity": 1, "destination": "D1"}
            pending = engine.gateway.execute_proposal("C1", "create_return", stronger)
            self.assertEqual(pending.status, "pending")
            checkpoint = fx.store.checkpoint("C1")
            fx.store.save_checkpoint(PhaseCheckpoint.model_validate({**checkpoint.model_dump(),
                "phase": "verify_return", "next_gate": "read_effect"}))
            original = next(r.intent for r in fx.store.intents("C1") if r.intent.operation == "create_return")
            result = WorkflowEngine(fx.profile, fx.world.bundle(), fx.store, fx.clock).recover("C1", fx.auth)
            self.assertEqual(result.effects["register_goods_refusal"].status, "verified")
            self.assertEqual(result.effects["create_return"].status, "pending")
            self.assertEqual(fx.store.intent(original.action_id).intent, original)
            self.assertEqual(original.stage, "initiate")
            self.assertEqual(fx.world.effect_count("create_return"), 1)
            self.assertEqual(sum(c.operation == "create_return" for c in fx.world.calls), 1)

    def test_recovery_cannot_replace_unsupported_saved_next_gate_with_business_dispatch(self):
        for next_gate in ("undeclared_gate", "send_status"):
            with self.subTest(next_gate=next_gate), tempfile.TemporaryDirectory() as folder:
                fx = self.fixture(folder)
                with self.assertRaises(ProcessCrash):
                    CrashOnPhase(fx, "window_gate").run(fx.request, fx.auth)
                checkpoint = fx.store.checkpoint("C1")
                fx.store.save_checkpoint(PhaseCheckpoint.model_validate({**checkpoint.model_dump(), "next_gate": next_gate}))
                result = WorkflowEngine(fx.profile, fx.world.bundle(), fx.store, fx.clock).recover("C1", fx.auth)
                self.assertEqual(result.status, "denied")
                self.assertEqual(fx.store.checkpoint("C1").next_gate, next_gate)
                self.assertEqual(fx.world.effect_count("reschedule"), 0)

    def test_recovery_cannot_silently_discard_saved_gate_during_local_verification(self):
        for phase in ("dispatch", "verification"):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as folder:
                fx = self.fixture(folder)
                with self.assertRaises(ProcessCrash):
                    CrashOnPhase(fx, phase).run(fx.request, fx.auth)
                checkpoint = fx.store.checkpoint("C1")
                fx.store.save_checkpoint(PhaseCheckpoint.model_validate({**checkpoint.model_dump(), "next_gate": "send_status"}))
                result = WorkflowEngine(fx.profile, fx.world.bundle(), fx.store, fx.clock).recover("C1", fx.auth)
                self.assertEqual(result.status, "denied")
                self.assertEqual(fx.store.checkpoint("C1").next_gate, "send_status")
                self.assertEqual(fx.world.effect_count("reschedule"), 1)

    def test_saved_explicit_original_read_gate_is_entered_before_finish(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder)
            with self.assertRaises(ProcessCrash):
                CrashOnPhase(fx, "verification").run(fx.request, fx.auth)
            checkpoint = fx.store.checkpoint("C1")
            fx.store.save_checkpoint(PhaseCheckpoint.model_validate({**checkpoint.model_dump(), "next_gate": "read_effect"}))
            before = len(fx.world.calls)
            result = WorkflowEngine(fx.profile, fx.world.bundle(), fx.store, fx.clock).recover("C1", fx.auth)
            self.assertEqual(result.effects["reschedule"].status, "verified")
            self.assertEqual(sum(c.operation == "read_schedule" for c in fx.world.calls[before:]), 1)
            self.assertEqual(sum(c.operation == "reschedule" for c in fx.world.calls[before:]), 0)

    def test_failed_verification_commit_retains_possible_return_execution(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder, request=goods_request())
            failed = False
            def fail_return_verification_once():
                nonlocal failed
                if not failed and any(state == "verified" and '"operation":"create_return"' in intent
                        for state, intent in fx.store._db.execute("SELECT dispatch_state,intent_json FROM intents")):
                    failed = True
                    raise JournalFailure("private-verification-fault")
            fx.store._before_commit = fail_return_verification_once
            result = fx.engine.run(fx.request, fx.auth)
            self.assertEqual(result.status, "authorized")
            self.assertEqual(result.effects["register_goods_refusal"].status, "verified")
            self.assertIn("create_return", result.effects)
            self.assertEqual(result.effects["create_return"].status, "outcome_unknown")
            self.assertEqual(result.effects["create_return"].evidence_refs, [])
            self.assertEqual(fx.world.effect_count("create_return"), 1)
            self.assertNotIn("private", result.model_dump_json())

    def test_original_read_acl_denial_after_entry_withholds_saved_effect_details(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder)
            original = fx.engine.gateway.bundle.scheduling
            def revoked(request):
                return original.read_schedule(ReadRequest.model_validate({**request.model_dump(),
                    "proof_reference": "revoked-original-read-proof"}))
            fx.engine.gateway.bundle = replace(fx.engine.gateway.bundle,
                scheduling=ForwardPort(original, read_schedule=revoked))
            result = fx.engine.run(fx.request, fx.auth)
            self.assertEqual(result.status, "denied")
            self.assertEqual(result.effects, {})
            self.assertIsNone(result.binding)
            self.assertEqual(fx.world.effect_count("reschedule"), 1)

    def test_handoff_recovery_commits_its_declared_communication_read_gate(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder, request=service_request())
            with self.assertRaises(ProcessCrash):
                CrashOnPhase(fx, "handoff_attempted").run(fx.request, fx.auth)
            checkpoint = fx.store.checkpoint("C1")
            fx.store.save_checkpoint(PhaseCheckpoint.model_validate({**checkpoint.model_dump(), "next_gate": "read_communication"}))
            engine = WorkflowEngine(fx.profile, fx.world.bundle(), fx.store, fx.clock)
            original, observed = engine.gateway.bundle.operator, []
            def checked(request):
                observer = CaseStore(Path(folder) / "journal.sqlite")
                saved = observer.checkpoint("C1")
                observed.append((saved.phase, saved.next_gate))
                observer.close()
                return original.read_receipt(request)
            engine.gateway.bundle = replace(engine.gateway.bundle, operator=ForwardPort(original, read_receipt=checked))
            result = engine.recover("C1", fx.auth)
            self.assertEqual(result.effects["enqueue_handoff"].status, "verified")
            self.assertEqual(observed, [("handoff_attempted", "read_communication")])
            self.assertEqual(fx.world.effect_count("enqueue_handoff"), 1)

    def test_cross_thread_and_reentrant_entry_cannot_replace_current_auth_or_enter_ports(self):
        for mode in ("thread", "reentrant"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as folder:
                fx = self.fixture(folder)
                original = fx.engine.gateway.bundle.case
                records, active = [], False
                def checked(request):
                    nonlocal active
                    if not active:
                        active = True
                        before = len(fx.world.calls)
                        output = []
                        def competing_entry():
                            try:
                                output.append(fx.engine.run(fx.request, make_auth(proof_reference="foreign-proof")))
                            except Exception:
                                output.append(None)
                        if mode == "thread":
                            thread = threading.Thread(target=competing_entry)
                            thread.start()
                            thread.join(timeout=1)
                            self.assertFalse(thread.is_alive())
                        else:
                            competing_entry()
                        records.append((fx.engine.gateway.auth, len(fx.world.calls) - before, output))
                    return original.read_case(request)
                fx.engine.gateway.bundle = replace(fx.engine.gateway.bundle,
                    case=ForwardPort(original, read_case=checked))
                result = fx.engine.run(fx.request, fx.auth)
                self.assertEqual(result.status, "authorized")
                self.assertEqual(result.effects["reschedule"].status, "verified")
                self.assertEqual(records[0][0], fx.auth)
                self.assertEqual(records[0][1], 0)
                self.assertIsNotNone(records[0][2][0])
                self.assertEqual(records[0][2][0].status, "denied")
                self.assertEqual(records[0][2][0].effects, {})
                self.assertEqual(fx.world.effect_count("reschedule"), 1)

    def test_current_material_denials_each_use_an_independent_world(self):
        for fact, value in (("customer.request_fingerprint", "0" * 64), ("customer.consent", "revoked"),
                            ("delivery.risk", "unsafe"), ("delivery.stage", "ineligible"),
                            ("delivery.status", "completed"), ("policy.version", "unknown-version"),
                            ("ownership.state", "pending")):
            with self.subTest(fact=fact), tempfile.TemporaryDirectory() as folder:
                fx = self.fixture(folder)
                fx.world.mutate(fact, value)
                result = fx.engine.run(fx.request, fx.auth)
                self.assertEqual(result.wait_status, "pending")
                self.assertEqual(fx.world.effect_count("reschedule"), 0)
                self.assertFalse(any(c.operation == "reschedule" for c in fx.world.calls))

    def test_incomplete_source_is_waiting_even_with_complete_caller_body(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder)
            fx.world.mutate("case.completeness", "missing")
            result = fx.engine.run(fx.request, fx.auth)
            self.assertEqual(result.wait_status, "pending")
            self.assertEqual(fx.store.checkpoint("C1").phase, "wait_operator")
            self.assertEqual(fx.world.effect_count("reschedule"), 0)

    def test_service_requires_completed_authoritative_lifecycle(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder, request=service_request())
            fx.world.mutate("delivery.status", "scheduled")
            result = fx.engine.run(fx.request, fx.auth)
            self.assertEqual(result.wait_status, "pending")
            self.assertEqual(fx.world.effect_count("register_service_refusal"), 0)
            self.assertEqual(fx.world.effect_count("enqueue_handoff"), 0)

    def test_conditional_provider_race_rejects_freshly_planned_effect(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder)
            original = fx.engine.gateway.bundle.scheduling
            def changed_after_read(request):
                read = original.list_permitted_slots(request)
                fx.world.mutate("scheduling.capacity", [])
                return read
            fx.engine.gateway.bundle = replace(fx.engine.gateway.bundle,
                scheduling=ForwardPort(original, list_permitted_slots=changed_after_read))
            result = fx.engine.run(fx.request, fx.auth)
            self.assertEqual(result.effects["reschedule"].status, "rejected")
            self.assertEqual(fx.world.effect_count("reschedule"), 0)
            self.assertEqual(sum(c.operation == "reschedule" for c in fx.world.calls), 1)

    def test_recovery_refreshes_source_scope_without_reconstructing_original_request(self):
        with tempfile.TemporaryDirectory() as folder:
            request = make_request(kind="reschedule_exact", consent_mode="exact_slot", arguments={"slot": "S2"})
            fx = self.fixture(folder, request=request)
            with self.assertRaises(ProcessCrash):
                CrashOnPhase(fx, "exact_gate").run(request, fx.auth)
            fx.world.mutate("scheduling.capacity", ["S1"])
            result = WorkflowEngine(fx.profile, fx.world.bundle(), fx.store, fx.clock).recover("C1", fx.auth)
            self.assertEqual(result.wait_status, "pending")
            self.assertEqual(fx.world.effect_count("reschedule"), 0)
            self.assertEqual(fx.store.original_request("C1", "G1"), request)

    def test_no_dispatch_when_finite_case_calls_are_exhausted_after_refusal(self):
        with tempfile.TemporaryDirectory() as folder:
            fx = self.fixture(folder, request=goods_request())
            with self.assertRaises(ProcessCrash):
                CrashOnPhase(fx, "refusal_complete").run(fx.request, fx.auth)
            checkpoint = fx.store.checkpoint("C1")
            fx.store.consume("C1", "tool_calls", checkpoint.budget.max_tool_calls - checkpoint.budget.tool_calls, fx.clock.now())
            before = len(fx.world.calls)
            result = WorkflowEngine(fx.profile, fx.world.bundle(), fx.store, fx.clock).recover("C1", fx.auth)
            self.assertEqual(result.status, "denied")
            self.assertEqual(len(fx.world.calls), before)
            self.assertEqual(fx.world.effect_count("register_goods_refusal"), 1)
            self.assertEqual(fx.world.effect_count("create_return"), 0)
            self.assertEqual(fx.store.checkpoint("C1").budget.tool_calls, 24)

    def test_all_positive_saved_phases_recover_in_a_fresh_python_process(self):
        common = ("intake", "extraction", "completeness", "auth_gate", "read_authority")
        scenarios = ((make_request(), common + ("window_gate", "dispatch", "verification")),
            (make_request(kind="reschedule_exact", consent_mode="exact_slot", arguments={"slot": "S2"}),
             common + ("slot_selection", "wait_confirmation", "exact_gate", "dispatch", "verification")),
            (goods_request(), common + ("refusal_gate", "dispatch", "verify_refusal", "refusal_complete",
                                       "return_gate", "return_dispatch", "verify_return")),
            (service_request(), common + ("refusal_gate", "dispatch", "verify_refusal", "refusal_complete",
                                         "handoff_attempted", "handoff_pending")))
        crash_script = """
import os,sys
from proofkey.contracts import CanonicalRequest
from support import build_test_runtime
from test_workflows import CrashOnPhase,ProcessCrash
fx=build_test_runtime(sys.argv[1],request=CanonicalRequest.model_validate_json(sys.argv[2]))
try:
    CrashOnPhase(fx,sys.argv[3]).run(fx.request,fx.auth)
except ProcessCrash:
    os._exit(41)
os._exit(42)
"""
        recover_script = """
import sys
from pathlib import Path
from datetime import timedelta
from proofkey.adapters.world import SimulatedWorld
from proofkey.engine import WorkflowEngine
from proofkey.journal import CaseStore
from support import FakeClock,NOW,load_test_profile,make_auth
profile=load_test_profile('flat-v1.2')
clock=FakeClock(NOW+timedelta(seconds=5))
world=SimulatedWorld(Path(sys.argv[1])/'world.sqlite',Path('runtime/fixtures/development/world.json'),profile=profile,clock=clock)
store=CaseStore(Path(sys.argv[1])/'journal.sqlite')
result=WorkflowEngine(profile,world.bundle(),store,clock).recover('C1',make_auth())
print(result.model_dump_json())
store.close()
"""
        for request, phases in scenarios:
            for phase in phases:
                with self.subTest(kind=request.kind, phase=phase), tempfile.TemporaryDirectory() as folder:
                    crash = subprocess.run([sys.executable, "-c", crash_script, folder, request.model_dump_json(), phase],
                        capture_output=True, text=True, timeout=10, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
                    self.assertEqual(crash.returncode, 41, crash.stderr)
                    observer = CaseStore(Path(folder) / "journal.sqlite")
                    before = observer.checkpoint("C1")
                    self.assertEqual(before.phase, phase)
                    observer.close()
                    recovered = subprocess.run([sys.executable, "-c", recover_script, folder],
                        capture_output=True, text=True, timeout=10, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
                    self.assertEqual(recovered.returncode, 0, recovered.stderr)
                    result = json.loads(recovered.stdout)
                    self.assertEqual(result["status"], "authorized")
                    self.assertTrue(all(v["status"] == "verified" for v in result["effects"].values()))
                    observer = CaseStore(Path(folder) / "journal.sqlite")
                    self.assertEqual(observer.original_request("C1", "G1"), request)
                    self.assertEqual(observer.checkpoint("C1").phase, "complete")
                    self.assertEqual(observer.checkpoint("C1").deadline, before.deadline)
                    self.assertLessEqual(observer.checkpoint("C1").budget.tool_calls, 24)
                    self.assertEqual(observer.checkpoint("C1").budget.planner_calls, 0)
                    observer.close()


if __name__ == "__main__":
    unittest.main()
