"""Actual library/public-owner/source/journal integration, not native authority."""
from datetime import timedelta
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from proofkey.batch import run_batch, run_command
from proofkey.batch_files import PublicationFailure, read_run_inventory
from proofkey.clock import SyntheticReplayClock
from proofkey.contracts import AuthContext, CanonicalRequest
from proofkey.execution import ExecutionContext
from proofkey.host import AuthResolver, HostDispatcher, ProfileRegistry, RuntimeFactory
from proofkey.host_contracts import InterfaceLimitsV1, HostLimitsV1


def canonical(kind="reschedule_window"):
    return CanonicalRequest(case_id="C1", object_id="O1", principal_id="U1", request_id="REQ1",
        request_revision="v1", consent_revision="v1", kind=kind,
        consent_mode="window" if kind == "reschedule_window" else "unknown",
        arguments={"window_start": "2026-10-08T10:00:00+00:00", "window_end": "2026-10-08T12:00:00+00:00",
                   "inventory": {"item-1": 1}} if kind == "reschedule_window" else {"inventory": {"item-1": 1}},
        evidence_ids=[])


class ObservedFactory(RuntimeFactory):
    def __init__(self):
        self.snapshots = []
        self.contexts = []
        self.owners = []
        self.created = []

    def create(self, release, clock):
        resource = super().create(release, clock)
        self.created.append(resource)
        engine, observer = resource.engine, self
        class ObservedEngine:
            def __getattr__(self, name):
                actual = getattr(engine, name)
                if not callable(actual):
                    return actual
                def forward(*args, **kwargs):
                    observer.contexts.append(kwargs.get("execution"))
                    observer.owners.append(threading.get_ident())
                    result = actual(*args, **kwargs)
                    if resource.store.has_case("C1"):
                        observer.snapshots.append((resource.store.checkpoint("C1"), resource.store.intents("C1"),
                            tuple(resource.world.calls), {op: resource.world.effect_count(op) for op in
                                ("reschedule", "register_goods_refusal", "create_return")}))
                    return result
                return forward
        resource.engine = ObservedEngine()
        return resource


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.clock = SyntheticReplayClock()
        self.registry = ProfileRegistry.builtin(self.base / "resources")
        self.resolver = AuthResolver({"user": AuthContext(caller_id="U1", proof_reference="synthetic-proof"),
            "wrong": AuthContext(caller_id="U1", proof_reference="wrong-proof")})
        self.proof = self.resolver.handle("user")
        self.factory = ObservedFactory()
        self.limits = InterfaceLimitsV1()

    def dispatcher(self, release="host-window-replay-v1"):
        dispatcher = HostDispatcher(self.factory, self.resolver, self.registry, self.clock,
            self.base / ("host-" + release), HostLimitsV1(), release_id=release)
        self.addCleanup(lambda: dispatcher.close(self.clock.now() + timedelta(seconds=2)))
        return dispatcher

    def parameters(self, dispatcher, *, execution=None, name="run"):
        execution = execution or ExecutionContext.capture(self.clock.now() + timedelta(seconds=20), self.clock)
        return dict(dispatcher=dispatcher, proof_handle=self.proof, execution=execution,
            publication_deadline=execution.deadline + timedelta(seconds=2), publication_reserve_seconds=2.0,
            output_root=self.base / name, limits=self.limits, clock=self.clock)

    def assert_positive(self, receipt, operations, execution):
        self.assertEqual(receipt.outcome, "completed")
        self.assertEqual(receipt.publication_status, "committed")
        position = receipt.positions[0]
        self.assertEqual(position.execution_outcome, "result")
        self.assertEqual(position.command.result.status, "authorized")
        self.assertEqual(position.export_outcome, "written")
        cp, intents, calls, effects = self.factory.snapshots[-1]
        self.assertEqual(cp.budget.tool_calls, len(calls))
        self.assertGreater(cp.budget.active_seconds, 0.0)
        self.assertEqual(cp.budget.planner_calls, 0)
        self.assertEqual(len(intents), len(operations))
        for operation in operations:
            self.assertEqual(position.command.result.effects[operation].status, "verified")
            self.assertEqual(effects[operation], 1)
        for record in intents:
            self.assertEqual(record.verification, position.command.result.effects[record.intent.operation])
        self.assertTrue(all(value is execution for value in self.factory.contexts))
        self.assertTrue(all(owner != threading.get_ident() for owner in self.factory.owners))
        for name, digest in position.export.actual_file_hashes:
            self.assertEqual(sha256((self.base / "run/ANSWERS/C1" / name).read_bytes()).hexdigest(), digest)
        readback = read_run_inventory(self.base / "run", limits=self.limits)
        self.assertEqual(readback.status, "committed_snapshot")
        self.assertEqual(readback.joined_command_ids, (position.command.command_id,))
        print("BATCH-POSITIVE " + json.dumps({"operations": list(operations), "calls": len(calls),
            "tool_calls": cp.budget.tool_calls, "active_seconds": cp.budget.active_seconds,
            "effects": effects, "intents": len(intents)}, sort_keys=True))

    def test_actual_window_result_export_and_source_journal_joins(self):
        dispatcher = self.dispatcher()
        options = self.parameters(dispatcher)
        receipt = run_batch([canonical()], **options)
        self.assert_positive(receipt, ("reschedule",), options["execution"])

    def test_actual_goods_result_export_and_source_journal_joins(self):
        dispatcher = self.dispatcher("host-goods-replay-v1")
        options = self.parameters(dispatcher)
        receipt = run_batch([canonical("goods_refusal")], **options)
        self.assert_positive(receipt, ("register_goods_refusal", "create_return"), options["execution"])

    def test_finite_whole_document_failure_has_no_output_or_invented_denominator(self):
        dispatcher = self.dispatcher()
        cycle = []; cycle.append(cycle)
        deep = []
        for _ in range(40):
            deep = [deep]
        values = (b'{"not":"list"}', b'[{"case_id":"C1","case_id":"C2"}]', b'[NaN]', b'["\xff"]',
                  cycle, deep, [object()], [("nested",)], ["\ud800"], (row for row in []))
        for index, value in enumerate(values):
            with self.subTest(index=index):
                options = self.parameters(dispatcher, name=f"invalid-{index}")
                actual = run_batch(value, **options)
                self.assertEqual(actual.outcome, "invalid_document")
                self.assertIsNone(actual.position_count)
                self.assertEqual(actual.positions, ())
                self.assertFalse(options["output_root"].exists())
                if type(value) is bytes:
                    self.assertEqual(actual.observed_input_hash, sha256(value).hexdigest())
        self.assertEqual(self.factory.created, [])

    def test_all_n_mixed_rows_keep_original_order_and_admission_before_public_enqueue(self):
        dispatcher = self.dispatcher()
        values = [{}, {"case_id": 7}, 3, {"case_id": "../bad"}, canonical()]
        actual_enqueue = dispatcher.enqueue
        observations = []
        def forward(command, proof, execution):
            inventory = json.loads((self.base / "run/INPUT-INVENTORY.json").read_bytes())
            admission = json.loads((self.base / "run/POSITION-00000004-ADMISSION.json").read_bytes())
            observations.append((len(inventory["positions"]), admission["admission_status"], "command_id" in admission))
            return actual_enqueue(command, proof, execution)
        with patch.object(dispatcher, "enqueue", side_effect=forward):
            receipt = run_batch(values, **self.parameters(dispatcher))
        self.assertEqual(receipt.position_count, 5)
        self.assertEqual(tuple(p.inventory.supplied_id_shape for p in receipt.positions),
                         ("missing", "non_string", "non_object", "string", "string"))
        self.assertEqual(tuple(p.execution_outcome for p in receipt.positions),
                         ("invalid_request", "invalid_request", "invalid_request", "invalid_request", "result"))
        self.assertEqual(observations, [(5, "unresolved", False)])

    def test_empty_batch_and_invalid_command_create_no_fictional_entries(self):
        dispatcher = self.dispatcher()
        receipt = run_batch([], **self.parameters(dispatcher))
        self.assertEqual(receipt.position_count, 0)
        self.assertEqual(receipt.outcome, "completed")
        options = self.parameters(dispatcher, name="bad-command")
        invalid = run_command({"tag": "run", "proof": "body"}, **options)
        self.assertEqual(invalid.input_outcome, "invalid_command")
        self.assertIsNone(invalid.command)
        self.assertFalse(options["output_root"].exists())
        self.assertEqual(self.factory.created, [])

    def test_standalone_inspection_has_actual_receipt_no_export_and_does_not_close_dispatcher(self):
        dispatcher = self.dispatcher()
        command = {"tag": "inspect-profile", "release_id": "host-window-replay-v1"}
        receipt = run_command(command, **self.parameters(dispatcher))
        self.assertEqual(receipt.command.outcome, "inspection")
        self.assertEqual(receipt.export_outcome, "not_attempted")
        self.assertEqual(receipt.publication_status, "committed")
        self.assertEqual(dispatcher.submit(command, self.proof, self.parameters(dispatcher)["execution"]).outcome, "inspection")

    def test_progress_write_failure_fences_next_enqueue_and_cannot_claim_committed_position(self):
        dispatcher = self.dispatcher()
        actual_enqueue = dispatcher.enqueue
        submissions = []
        def enqueue(*args):
            submissions.append(args[0])
            return actual_enqueue(*args)
        with patch.object(dispatcher, "enqueue", side_effect=enqueue), patch(
                "proofkey.batch.RunPublisher.publish_progress", side_effect=PublicationFailure()):
            receipt = run_batch([canonical(), canonical()], **self.parameters(dispatcher))
        self.assertEqual(len(submissions), 1)
        self.assertEqual(receipt.outcome, "publication_failed")
        self.assertEqual(receipt.positions[0].publication_status, "partial")
        self.assertEqual(receipt.positions[1].execution_outcome, "not_started")
        self.assertIsNone(receipt.final_reference)
        self.assertTrue((self.base / "run/POSITION-00000000-ADMISSION.json").exists())
        self.assertFalse((self.base / "run/POSITION-00000000-PROGRESS.json").exists())

    def test_returned_wrong_scope_has_no_false_result_hash_export_or_next_entry(self):
        from proofkey.contracts import CaseResult
        dispatcher = self.dispatcher()
        actual_wait = dispatcher.wait
        def wrong(submission):
            returned = actual_wait(submission)
            return returned.model_copy(update={"result": CaseResult(status="denied", correlation_id="C2", reason="denied")})
        with patch.object(dispatcher, "wait", side_effect=wrong):
            receipt = run_batch([canonical(), canonical()], **self.parameters(dispatcher))
        self.assertEqual(receipt.positions[0].failure, "result_scope_mismatch")
        self.assertIsNone(receipt.positions[0].result_hash)
        self.assertIsNone(receipt.positions[0].command)
        self.assertEqual(receipt.positions[0].export_outcome, "not_attempted")
        self.assertEqual(receipt.unresolved_admission_ordinals, (0,))
        self.assertEqual(receipt.positions[1].execution_outcome, "not_started")
        self.assertFalse((self.base / "run/ANSWERS").exists())

    def test_actual_duplicate_original_replays_once_but_export_collision_is_factual(self):
        dispatcher = self.dispatcher()
        receipt = run_batch([canonical(), canonical()], **self.parameters(dispatcher))
        self.assertEqual(receipt.outcome, "completed")
        first, second = receipt.positions
        self.assertNotEqual(first.command.command_id, second.command.command_id)
        self.assertEqual(first.export_outcome, "written")
        self.assertEqual(second.export_outcome, "failed")
        self.assertEqual(second.export_failure, "output_conflict")
        self.assertIsNone(second.export)
        self.assertTrue(second.command.result.historical)
        self.assertEqual(self.factory.snapshots[-1][3]["reschedule"], 1)

    def test_external_wrong_proof_and_changed_business_fingerprint_never_grant(self):
        dispatcher = self.dispatcher()
        altered = canonical().model_copy(update={"arguments": {"inventory": {"item-1": 999}}})
        options = self.parameters(dispatcher)
        options["proof_handle"] = object()
        denied = run_batch([canonical()], **options)
        self.assertEqual(denied.positions[0].execution_outcome, "denied")
        self.assertIsNone(denied.positions[0].command.result)
        self.assertEqual(self.factory.created, [])
        changed = run_batch([altered], **self.parameters(dispatcher, name="changed"))
        self.assertEqual(changed.positions[0].execution_outcome, "denied")
        self.assertEqual(self.factory.created, [])
        self.assertEqual(changed.positions[0].export_outcome, "not_attempted")

    def test_trusted_pre_row_cancellation_retains_all_positions_without_host_entry(self):
        dispatcher = self.dispatcher()
        cancellation = threading.Event(); cancellation.set()
        receipt = run_batch([canonical(), canonical()], cancellation=cancellation, **self.parameters(dispatcher))
        self.assertEqual(receipt.position_count, 2)
        self.assertEqual(tuple(p.execution_outcome for p in receipt.positions), ("not_started", "not_started"))
        self.assertEqual(tuple(p.command for p in receipt.positions), (None, None))
        self.assertEqual(self.factory.created, [])
        self.assertEqual(receipt.publication_status, "committed")

    def test_config_clock_identity_and_windows_reject_before_any_root_or_entry(self):
        dispatcher = self.dispatcher()
        for update in ({"clock": SyntheticReplayClock()}, {"publication_reserve_seconds": 0.0000001},
                       {"publication_deadline": self.clock.now() + timedelta(seconds=999)},
                       {"limits": {"max_positions": 1}}, {"cancellation": lambda: False}):
            options = self.parameters(dispatcher)
            with self.assertRaises(ValueError):
                run_batch([canonical()], **{**options, **update})
            self.assertFalse(options["output_root"].exists())
        self.assertEqual(self.factory.created, [])

    def test_intake_detaches_before_enqueue_and_exact_raw_vs_canonical_hash_labels(self):
        dispatcher = self.dispatcher()
        rows = [canonical().model_dump(mode="json")]
        raw = json.dumps(rows, indent=2).encode()
        actual_enqueue = dispatcher.enqueue
        def mutate(*args):
            rows[0]["arguments"]["inventory"]["item-1"] = 999
            return actual_enqueue(*args)
        with patch.object(dispatcher, "enqueue", side_effect=mutate):
            receipt = run_batch(rows, **self.parameters(dispatcher))
        expected = sha256(json.dumps(json.loads(raw), sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
        self.assertEqual(receipt.input.input_hash, expected)
        self.assertEqual(receipt.positions[0].command.result.status, "authorized")
        exact = run_batch(raw, **self.parameters(dispatcher, name="exact"))
        self.assertEqual(exact.input.encoding, "exact_json_document_v1")
        self.assertEqual(exact.input.input_hash, sha256(raw).hexdigest())
        self.assertNotEqual(exact.input.input_hash, receipt.input.input_hash)

    def test_public_wait_exception_retains_unresolved_admission_without_private_peek(self):
        dispatcher = self.dispatcher()
        with patch.object(dispatcher, "wait", side_effect=RuntimeError("private exception must not be serialized")):
            receipt = run_batch([canonical(), canonical()], **self.parameters(dispatcher))
        self.assertEqual(receipt.outcome, "abandoned_pending")
        self.assertEqual(receipt.unresolved_admission_ordinals, (0,))
        self.assertEqual(receipt.pending_command_ids, ())
        self.assertEqual(receipt.positions[1].command, None)
        reader = read_run_inventory(self.base / "run", limits=self.limits)
        self.assertEqual(reader.unresolved_admission_ordinals, (0,))
        self.assertEqual(reader.joined_command_ids, ())
        self.assertNotIn("private exception", (self.base / "run/FINAL-MANIFEST.json").read_text())

    def test_actual_host_parse_ceiling_denial_is_joined_not_invented_unresolved(self):
        dispatcher = self.dispatcher()
        request = canonical().model_copy(update={"narrative": "x" * 70000})
        receipt = run_batch([request], **self.parameters(dispatcher))
        self.assertEqual(receipt.positions[0].execution_outcome, "denied")
        self.assertEqual(receipt.positions[0].admission_status, "joined")
        self.assertEqual(receipt.positions[0].command.failure, "invalid_command")
        self.assertEqual(receipt.unresolved_admission_ordinals, ())
        self.assertEqual(self.factory.created, [])

    def test_wrong_release_standalone_preserves_actual_host_denied_receipt(self):
        dispatcher = self.dispatcher()
        receipt = run_command({"tag": "inspect-profile", "release_id": "foreign-release"}, **self.parameters(dispatcher))
        self.assertIsNotNone(receipt.command)
        self.assertEqual(receipt.command.outcome, "denied")
        self.assertEqual(receipt.command.failure, "scope_denied")
        self.assertFalse(receipt.unresolved_admission)
        self.assertEqual(receipt.publication_status, "committed")

    def test_relative_output_and_custom_path_configuration_reject_before_publication(self):
        dispatcher = self.dispatcher()
        for root in ("relative-run", object()):
            with self.assertRaises(ValueError):
                run_batch([], **{**self.parameters(dispatcher), "output_root": root})
        self.assertEqual(self.factory.created, [])

    def test_w_expiry_preserves_denominator_without_any_host_entry(self):
        dispatcher = self.dispatcher()
        context = ExecutionContext.capture(self.clock.now() - timedelta(seconds=0.01), self.clock)
        options = self.parameters(dispatcher, execution=context)
        actual = run_batch([canonical(), canonical()], **options)
        self.assertEqual(actual.outcome, "deadline_exceeded")
        self.assertEqual(actual.position_count, 2)
        self.assertEqual(tuple(p.execution_outcome for p in actual.positions), ("deadline_exceeded", "deadline_exceeded"))
        self.assertEqual(self.factory.created, [])

    def test_only_closed_unavailable_tags_are_forwarded_no_export_or_fake_business(self):
        dispatcher = self.dispatcher()
        for tag in ("batch", "transfer"):
            receipt = run_command({"tag": tag, "release_id": "host-window-replay-v1"},
                                  **self.parameters(dispatcher, name=tag))
            self.assertEqual(receipt.command.outcome, "unavailable")
            self.assertEqual(receipt.export_outcome, "not_attempted")
            self.assertEqual(receipt.publication_status, "committed")
        self.assertEqual(self.factory.created, [])

    def test_actual_started_pending_fences_later_rows_without_claiming_nonexecution(self):
        entered, release = threading.Event(), threading.Event()
        observer = self.factory
        class BlockingFactory:
            def create(self, entry, clock):
                entered.set()
                if not release.wait(3):
                    raise RuntimeError("bounded test barrier")
                return observer.create(entry, clock)
        self.factory = BlockingFactory()
        dispatcher = self.dispatcher()
        self.factory = observer
        execution = ExecutionContext.capture(self.clock.now() + timedelta(seconds=0.15), self.clock)
        try:
            receipt = run_batch([canonical(), canonical()], **self.parameters(dispatcher, execution=execution))
            self.assertTrue(entered.is_set())
            first, second = receipt.positions
            self.assertEqual(first.command.outcome, "started_pending")
            self.assertIsNone(first.command.finished_at)
            self.assertEqual(receipt.pending_command_ids, (first.command.command_id,))
            self.assertEqual(receipt.outcome, "abandoned_pending")
            self.assertEqual(second.execution_outcome, "not_started")
            self.assertIsNone(second.command)
            self.assertIsNone(first.result_hash)
            self.assertEqual(first.export_outcome, "not_attempted")
            self.assertEqual(receipt.publication_status, "committed")
        finally:
            release.set()
            closed = dispatcher.close(self.clock.now() + timedelta(seconds=2))
            self.assertTrue(closed.owner_closed)

    def test_after_enqueue_event_uses_public_cancel_queued_with_actual_partial_pending(self):
        entered, release, cancellation = threading.Event(), threading.Event(), threading.Event()
        observer = self.factory
        class BlockingFactory:
            def create(self, entry, clock):
                entered.set()
                if not release.wait(4):
                    raise RuntimeError("bounded test barrier")
                return observer.create(entry, clock)
        self.factory = BlockingFactory()
        dispatcher = self.dispatcher()
        self.factory = observer
        options = self.parameters(dispatcher)
        first = dispatcher.enqueue({"tag": "run", "release_id": "host-window-replay-v1", "request": canonical().model_dump(mode="json")},
                                   self.proof, options["execution"])
        actual_enqueue = dispatcher.enqueue
        def cancel_after(*args):
            submission = actual_enqueue(*args)
            cancellation.set()
            return submission
        try:
            self.assertTrue(entered.wait(1))
            with patch.object(dispatcher, "enqueue", side_effect=cancel_after):
                receipt = run_batch([canonical(), canonical()], cancellation=cancellation, **options)
            position = receipt.positions[0]
            self.assertEqual(position.command.outcome, "cancelled_before_start")
            self.assertIsNone(position.command.started_at)
            self.assertIsNone(position.command.finished_at)
            self.assertEqual(position.command.inventory_status, "partial")
            self.assertEqual(receipt.pending_command_ids, (position.command.command_id,))
            self.assertEqual(receipt.outcome, "abandoned_pending")
            self.assertEqual(receipt.positions[1].execution_outcome, "not_started")
        finally:
            release.set()
            dispatcher.wait(first)
            closed = dispatcher.close(self.clock.now() + timedelta(seconds=2))
            self.assertTrue(closed.owner_closed)

    def test_current_wrong_documentary_proof_returns_only_actual_generic_result(self):
        dispatcher = self.dispatcher()
        options = self.parameters(dispatcher)
        options["proof_handle"] = self.resolver.handle("wrong")
        receipt = run_batch([canonical()], **options)
        result = receipt.positions[0].command.result
        self.assertEqual(result.status, "denied")
        self.assertIsNone(result.binding)
        self.assertEqual(result.model_dump(mode="json").keys(), {"status", "correlation_id", "reason"})
        self.assertEqual(self.factory.created[0].world.effect_count("reschedule"), 0)
        self.assertEqual(receipt.positions[0].export_outcome, "written")

    def test_actual_standalone_recover_and_stop_reuse_original_context_scoped_results(self):
        dispatcher = self.dispatcher()
        options = self.parameters(dispatcher)
        original = run_batch([canonical()], **options).positions[0].command.result
        for tag in ("recover", "stop"):
            command = {"tag": tag, "release_id": "host-window-replay-v1", "case_id": "C1"}
            if tag == "stop":
                command["generation"] = original.binding.generation
            actual = run_command(command, **{**options, "output_root": self.base / tag})
            self.assertIsNotNone(actual.command)
            if tag == "recover":
                # The fixed positive is already terminal; recovery is not a replay grant.
                self.assertEqual(actual.command.result.status, "denied")
                self.assertEqual(actual.command.result.reason, "unavailable")
                self.assertIsNone(actual.command.result.binding)
            else:
                self.assertEqual(actual.command.result.binding, original.binding)
            self.assertEqual(actual.export_outcome, "written")
            self.assertEqual(actual.publication_status, "committed")
            if tag == "stop":
                self.assertTrue(actual.command.result.stop.requested)
        self.assertTrue(all(execution is options["execution"] for execution in self.factory.contexts))
        self.assertEqual(self.factory.snapshots[-1][3]["reschedule"], 1)

    def test_whole_document_position_size_and_node_bounds_never_create_root_or_hash_fragments(self):
        dispatcher = self.dispatcher()
        for index, (inputs, limits) in enumerate(((b'[]       ', InterfaceLimitsV1(max_input_bytes=2)),
            ([{}, {}], InterfaceLimitsV1(max_positions=1)), (["a", "b", "c"], InterfaceLimitsV1(max_input_bytes=2)))):
            options = self.parameters(dispatcher, name=f"bounded-{index}")
            options["limits"] = limits
            receipt = run_batch(inputs, **options)
            self.assertEqual(receipt.input_outcome, "invalid_document")
            self.assertIsNone(receipt.position_count)
            self.assertIsNone(receipt.observed_input_hash)
            self.assertFalse(options["output_root"].exists())
        self.assertEqual(self.factory.created, [])

    def test_utc_or_monotonic_d_expiry_during_actual_intake_returns_no_fabricated_receipt(self):
        from test_batch_files import Clock
        from test_batch_contracts import START
        class SplitClock(Clock):
            utc_seconds = 0.0
            mono_seconds = 0.0
            def now(self):
                return START + timedelta(seconds=self.utc_seconds)
            def monotonic(self):
                return -100.0 + self.mono_seconds
        for axis in ("utc_seconds", "mono_seconds"):
            clock = SplitClock()
            dispatcher = HostDispatcher(self.factory, self.resolver, self.registry, clock,
                self.base / ("intake-host-" + axis), HostLimitsV1(), release_id="host-window-replay-v1")
            context = ExecutionContext.capture(clock.now() + timedelta(seconds=10), clock)
            options = dict(dispatcher=dispatcher, proof_handle=self.proof, execution=context,
                publication_deadline=context.deadline + timedelta(seconds=2), publication_reserve_seconds=2.0,
                output_root=self.base / axis, limits=self.limits, clock=clock)
            actual_loads = json.loads
            def consume_then_expire(*args, **kwargs):
                actual = actual_loads(*args, **kwargs)
                setattr(clock, axis, 12.0)
                return actual
            try:
                with patch("proofkey.batch.json.loads", side_effect=consume_then_expire), self.assertRaises(ValueError) as error:
                    run_batch(b'[{}]', **options)
                self.assertEqual(str(error.exception), "Unavailable trusted intake window")
                self.assertFalse(options["output_root"].exists())
            finally:
                self.assertTrue(dispatcher.close(clock.now() + timedelta(seconds=1)).owner_closed)
        self.assertEqual(self.factory.created, [])

    def test_already_exhausted_d_does_not_even_enter_actual_parser(self):
        from test_batch_files import Clock
        from test_batch_contracts import START
        clock = Clock()
        dispatcher = HostDispatcher(self.factory, self.resolver, self.registry, clock,
            self.base / "expired-intake-host", HostLimitsV1(), release_id="host-window-replay-v1")
        context = ExecutionContext.capture(START + timedelta(seconds=10), clock)
        clock.seconds = 12.0
        options = dict(dispatcher=dispatcher, proof_handle=self.proof, execution=context,
            publication_deadline=context.deadline + timedelta(seconds=2), publication_reserve_seconds=2.0,
            output_root=self.base / "expired-intake", limits=self.limits, clock=clock)
        calls = []
        actual_loads = json.loads
        def observed_loads(*args, **kwargs):
            calls.append(args[0])
            return actual_loads(*args, **kwargs)
        try:
            with patch("proofkey.batch.json.loads", side_effect=observed_loads), self.assertRaises(ValueError):
                run_batch(b'[]', **options)
            self.assertEqual(calls, [])
            self.assertFalse(options["output_root"].exists())
        finally:
            self.assertTrue(dispatcher.close(clock.now() + timedelta(seconds=1)).owner_closed)

    def test_actual_export_returning_after_d_is_unvalidated_failure_not_false_nonattempt(self):
        from proofkey.exporter import export_case
        class AdvancingClock(SyntheticReplayClock):
            extra = 0.0
            def monotonic(self):
                return super().monotonic() + self.extra
        self.clock = AdvancingClock()
        dispatcher = self.dispatcher()
        options = self.parameters(dispatcher)
        def consume_then_expire(result, root):
            actual = export_case(result, root)
            self.clock.extra = 22.0
            return actual
        with patch("proofkey.batch.export_case", side_effect=consume_then_expire):
            receipt = run_batch([canonical(), canonical()], **options)
        self.assertEqual(receipt.outcome, "deadline_exceeded")
        first = receipt.positions[0]
        self.assertEqual(first.execution_outcome, "result")
        self.assertEqual(first.export_outcome, "failed")
        self.assertIsNone(first.export)
        self.assertEqual(first.export_failure, "export_io_error")
        self.assertEqual(first.publication_status, "partial")
        self.assertGreater(receipt.overrun_seconds, 0.0)
        self.assertTrue((self.base / "run/ANSWERS/C1/ANSWER.md").exists())
        self.assertFalse((self.base / "run/POSITION-00000001-ADMISSION.json").exists())
        self.assertIsNone(receipt.final_reference)
