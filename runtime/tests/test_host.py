"""Real owner threads/public synthetic runtime; no native or packaging claims."""
from datetime import timedelta
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import threading
import subprocess
import sys
import unittest
from unittest.mock import patch

from proofkey.clock import SyntheticReplayClock
from proofkey.contracts import AuthContext, ScopedReply
from proofkey.execution import ExecutionContext
from proofkey.host import AuthResolver, HostDispatcher, ProfileRegistry, RuntimeFactory, RuntimeResources
from proofkey.host_contracts import HostLimitsV1
from proofkey.host_files import read_inventory
import proofkey.host_files as host_files
from proofkey.adapters.world import SimulatedWorld
from proofkey.journal import CaseStore
from test_host_contracts import request


ROOT = Path(__file__).resolve().parents[1]


class ObservedFactory(RuntimeFactory):
    def __init__(self):
        self.events, self.snapshots, self.created, self.auth_snapshots = [], [], [], []

    def create(self, release, clock):
        self.events.append(("create", threading.get_ident()))
        resource = super().create(release, clock)
        self.created.append(resource)
        actual = resource.engine
        observer = self

        class EngineObserver:
            def __getattr__(self, name):
                target = getattr(actual, name)
                if not callable(target):
                    return target
                def forward(*args, **kwargs):
                    observer.events.append((name, threading.get_ident()))
                    result = target(*args, **kwargs)
                    observer.auth_snapshots.append(actual.gateway.auth)
                    if resource.store.has_case("C1"):
                        cp = resource.store.checkpoint("C1")
                        observer.snapshots.append((cp, resource.store.intents("C1"), tuple(resource.world.calls),
                            {op: resource.world.effect_count(op) for op in ("reschedule", "register_goods_refusal", "create_return")}))
                    return result
                return forward

        resource.engine = EngineObserver()
        close = resource.close
        def observed_close():
            observer.events.append(("close", threading.get_ident()))
            close()
        resource.close = observed_close
        return resource


class HostTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.clock = SyntheticReplayClock()
        self.registry = ProfileRegistry.builtin(self.base / "resources")
        self.resolver = AuthResolver({"synthetic-user": AuthContext(caller_id="U1", proof_reference="synthetic-proof"),
            "wrong-proof": AuthContext(caller_id="U1", proof_reference="wrong-documentary-proof")})
        self.handle = self.resolver.handle("synthetic-user")

    def context(self, seconds=20):
        return ExecutionContext.capture(self.clock.now() + timedelta(seconds=seconds), self.clock)

    def dispatcher(self, *, release_id="host-window-replay-v1", factory=None, limits=None):
        dispatcher = HostDispatcher(factory or ObservedFactory(), self.resolver, self.registry, self.clock,
            self.base / ("inventory-" + release_id), limits or HostLimitsV1(), release_id=release_id)
        self.addCleanup(lambda: dispatcher.close(self.clock.now() + timedelta(seconds=2)))
        return dispatcher

    def test_goods_fixture_has_exact_three_semantic_differences_and_old_pin(self):
        original = ROOT / "fixtures/development/packet-world-v1.json"
        goods = ROOT / "fixtures/development/host-goods-world-v1.json"
        self.assertEqual(sha256(original.read_bytes()).hexdigest(),
                         "cb9a2c3b8bcf77ee1f400cac7921b52b52f2468180c0b043b8f35f01058a0c59")
        before, after = json.loads(original.read_bytes()), json.loads(goods.read_bytes())
        changed = {key for key in before["facts"] if before["facts"][key] != after["facts"][key]}
        self.assertEqual(changed, {"customer.request_fingerprint", "customer.consent_mode", "delivery.status"})
        for key, value in (("customer.request_fingerprint", "f1a95a447f2a6726a3459f37790557326b3361a15894a7b4a2baa28451321ce2"),
                           ("customer.consent_mode", "unknown"), ("delivery.status", "delivered")):
            before["facts"][key]["value"] = value
        self.assertEqual(before, after)

    def test_complete_factory_runs_both_real_positive_families_on_creator_and_closes_there(self):
        for release_id, kind in (("host-window-replay-v1", "reschedule_window"),
                                 ("host-goods-replay-v1", "goods_refusal")):
            with self.subTest(release_id=release_id):
                factory = ObservedFactory()
                dispatcher = self.dispatcher(release_id=release_id, factory=factory)
                canonical = request()
                if kind == "goods_refusal":
                    canonical = canonical.model_copy(update={"kind": kind, "consent_mode": "unknown",
                        "arguments": {"inventory": {"item-1": 1}}})
                execution = self.context()
                receipt = dispatcher.submit({"tag": "run", "release_id": release_id,
                    "request": canonical.model_dump(mode="json")}, self.handle, execution)
                self.assertEqual(receipt.outcome, "result")
                self.assertEqual(receipt.result.status, "authorized")
                required = ("reschedule",) if kind == "reschedule_window" else ("register_goods_refusal", "create_return")
                for operation in required:
                    self.assertEqual(receipt.result.effects[operation].status, "verified")
                    self.assertEqual(factory.snapshots[-1][3][operation], 1)
                checkpoint, intents, calls, _ = factory.snapshots[-1]
                self.assertLessEqual(checkpoint.deadline, execution.deadline)
                self.assertEqual(checkpoint.budget.tool_calls, len(calls))
                self.assertGreater(checkpoint.budget.tool_calls, 0)
                self.assertGreater(checkpoint.budget.active_seconds, 0)
                self.assertTrue(intents)
                self.assertTrue(checkpoint.observations)
                for record in intents:
                    self.assertEqual(record.intent.binding, receipt.result.binding)
                    self.assertEqual(record.state, "verified")
                    self.assertEqual(record.verification, receipt.result.effects[record.intent.operation])
                    self.assertEqual(record.intent.binding.object_id, "O1")
                self.assertEqual(receipt.execution.deadline, execution.deadline)
                self.assertEqual(receipt.inventory_status, "committed")
                print("HOST-POSITIVE", json.dumps({"release_id": release_id, "mode": receipt.mode,
                    "status": receipt.result.status, "operations": {op: receipt.result.effects[op].status for op in required},
                    "tool_calls": checkpoint.budget.tool_calls, "active_seconds": checkpoint.budget.active_seconds,
                    "source_calls": len(calls), "intents": len(intents), "physical_effects": factory.snapshots[-1][3]}, sort_keys=True))
                states = read_inventory(dispatcher.inventory_root)
                self.assertEqual([state.phase for state in states], ["queued", "started", "finished"])
                self.assertEqual(states[-1].outcome, "result")
                raw = b"".join(path.read_bytes() for path in dispatcher.inventory_root.iterdir())
                self.assertNotIn(b"synthetic-proof", raw)
                self.assertNotIn(b'"request":', raw)
                shutdown = dispatcher.close(self.clock.now() + timedelta(seconds=2))
                self.assertTrue(shutdown.owner_closed)
                threads = {thread for _, thread in factory.events}
                self.assertEqual(len(threads), 1)
                self.assertNotIn(threading.get_ident(), threads)

    def test_wrong_business_family_cannot_reconfigure_registered_world(self):
        factory = ObservedFactory()
        dispatcher = self.dispatcher(factory=factory)
        canonical = request().model_copy(update={"kind": "goods_refusal", "consent_mode": "unknown",
            "arguments": {"inventory": {"item-1": 1}}})
        receipt = dispatcher.submit({"tag": "run", "release_id": "host-window-replay-v1",
            "request": canonical.model_dump(mode="json")}, self.handle, self.context())
        self.assertEqual(receipt.outcome, "denied")
        self.assertEqual(receipt.failure, "scope_denied")
        self.assertIsNone(receipt.result)
        self.assertEqual(factory.created, [])
        self.assertEqual(read_inventory(dispatcher.inventory_root), ())
        changed = request().model_copy(update={"arguments": {"inventory": {"item-1": 2}}})
        with patch.object(self.resolver, "resolve", wraps=self.resolver.resolve) as resolve:
            receipt = dispatcher.submit({"tag": "run", "release_id": "host-window-replay-v1",
                "request": changed.model_dump(mode="json")}, self.handle, self.context())
            self.assertEqual(receipt.outcome, "denied")
            self.assertEqual(receipt.failure, "scope_denied")
            self.assertEqual(resolve.call_count, 0)
        self.assertEqual(factory.created, [])

    def test_fixed_demo_commitments_are_mandatory_immutable_closed_config_not_body_grants(self):
        entry = self.registry.resolve("host-window-replay-v1")
        for update in ({"admitted_request_kind": "enqueue_handoff"}, {"admitted_request_kind": True},
                       {"admitted_request_fingerprint": "A" * 64}, {"admitted_request_fingerprint": "a" * 63},
                       {"admitted_request_fingerprint": None}):
            with self.assertRaises(ValueError):
                replace(entry, **update)
        with self.assertRaises(AttributeError):
            entry.admitted_request_kind = "goods_refusal"
        self.assertEqual(entry.admitted_request_kind, "reschedule_window")

    def test_invalid_or_expired_context_denies_before_resolver_and_factory(self):
        factory = ObservedFactory()
        dispatcher = self.dispatcher(factory=factory)
        command = {"tag": "inspect-profile", "release_id": "host-window-replay-v1"}
        with patch.object(self.resolver, "resolve", wraps=self.resolver.resolve) as resolve:
            for context in (None, self.context(-1), {"deadline": "body-cannot-supply-this"}):
                receipt = dispatcher.submit(command, self.handle, context)
                self.assertIn(receipt.outcome, {"denied", "expired"})
            self.assertEqual(resolve.call_count, 0)
        self.assertEqual(factory.created, [])

    def test_owner_reentry_denies_before_nested_admission_or_shutdown_mutation(self):
        observer, attempted = {}, []
        class RecursiveFactory(ObservedFactory):
            def create(inner, entry, clock):
                dispatcher = observer["dispatcher"]
                for callback in (
                    lambda: dispatcher.enqueue({"tag": "inspect-profile", "release_id": entry.release_id},
                        self.handle, self.context()),
                    lambda: dispatcher.close(clock.now() + timedelta(seconds=1)),
                ):
                    with self.assertRaises(ValueError):
                        callback()
                    attempted.append("rejected")
                return super().create(entry, clock)
        factory = RecursiveFactory()
        dispatcher = self.dispatcher(factory=factory)
        observer["dispatcher"] = dispatcher
        command = {"tag": "run", "release_id": "host-window-replay-v1", "request": request().model_dump(mode="json")}
        receipt = dispatcher.submit(command, self.handle, self.context())
        self.assertEqual(receipt.outcome, "result")
        self.assertEqual(receipt.result.status, "authorized")
        self.assertEqual(attempted, ["rejected", "rejected"])
        inspected = dispatcher.submit({"tag": "inspect-profile", "release_id": command["release_id"]},
            self.handle, self.context())
        self.assertEqual(inspected.outcome, "inspection")
        self.assertEqual(len(read_inventory(dispatcher.inventory_root)), 6)

    def test_resolver_elapsed_window_and_long_configured_global_window_are_not_recaptured(self):
        factory = ObservedFactory()
        dispatcher = self.dispatcher(factory=factory, limits=HostLimitsV1(max_execution_seconds=2000.0))
        command = {"tag": "inspect-profile", "release_id": "host-window-replay-v1"}
        original = self.context(1800)
        receipt = dispatcher.submit(command, self.handle, original)
        self.assertEqual(receipt.outcome, "inspection")
        self.assertEqual(receipt.execution.deadline, original.deadline)
        self.assertEqual(receipt.execution.monotonic_deadline, original.monotonic_deadline)
        resolve = self.resolver.resolve
        def slow_resolve(*args):
            auth = resolve(*args)
            self.clock.wait(0.025)
            return auth
        original = self.context(0.01)
        with patch.object(self.resolver, "resolve", side_effect=slow_resolve):
            receipt = dispatcher.submit(command, self.handle, original)
            self.assertIn(receipt.outcome, {"started_pending", "expired"})
        self.assertTrue(dispatcher.close(self.clock.now() + timedelta(seconds=1)).owner_closed)
        finished = read_inventory(dispatcher.inventory_root)[-1]
        self.assertEqual(finished.outcome, "expired")
        self.assertEqual(finished.execution.deadline, original.deadline)
        self.assertEqual(factory.created, [])

    def test_pinned_fixture_and_nofollow_database_targets_fail_before_engine(self):
        entry = self.registry.resolve("host-window-replay-v1")
        bad = replace(entry, fixture_hash="0" * 64)
        with self.assertRaises(ValueError):
            RuntimeFactory().create(bad, self.clock)
        self.assertFalse(entry.resource_root.exists())
        entry.resource_root.mkdir(parents=True)
        untouched = self.base / "unrelated-file"
        untouched.write_bytes(b"not an owned database")
        (entry.resource_root / "journal.sqlite").symlink_to(untouched)
        with self.assertRaises(ValueError):
            RuntimeFactory().create(entry, self.clock)
        self.assertEqual(untouched.read_bytes(), b"not an owned database")
        self.assertFalse((entry.resource_root / "world.sqlite").exists())

    def test_inventory_nofollow_bounds_and_actual_readback_mismatch_prevent_callback(self):
        factory = ObservedFactory()
        dispatcher = self.dispatcher(factory=factory)
        command = {"tag": "inspect-profile", "release_id": "host-window-replay-v1"}
        actual_write = host_files._write
        def changed_write(root, name, data):
            if name.endswith("-0.json"):
                data = data.replace(b'"phase":"queued"', b'"phase":"changed"')
            actual_write(root, name, data)
        with patch.object(host_files, "_write", side_effect=changed_write), \
                patch.object(self.resolver, "resolve", wraps=self.resolver.resolve) as resolve:
            receipt = dispatcher.submit(command, self.handle, self.context())
            self.assertEqual(receipt.outcome, "infrastructure_error")
            self.assertEqual(receipt.failure, "no_durable_inventory")
            self.assertEqual(resolve.call_count, 0)
        with self.assertRaises(host_files.InventoryFailure):
            read_inventory(dispatcher.inventory_root)
        alias = self.base / "inventory-alias"
        alias.symlink_to(dispatcher.inventory_root, target_is_directory=True)
        with self.assertRaises(host_files.InventoryFailure):
            read_inventory(alias)
        with self.assertRaises(host_files.InventoryFailure):
            read_inventory(dispatcher.inventory_root, max_bytes=1)
        self.assertEqual(factory.created, [])

    def test_enqueue_clock_failure_does_not_leave_an_admitting_owner_stranded(self):
        factory = ObservedFactory()
        dispatcher = self.dispatcher(factory=factory)
        execution = self.context()
        command = {"tag": "inspect-profile", "release_id": "host-window-replay-v1"}
        actual = dispatcher._now
        failed = False
        def fail_once():
            nonlocal failed
            if not failed:
                failed = True
                raise ValueError("task-owned queued timestamp failure")
            return actual()
        with patch.object(dispatcher, "_now", side_effect=fail_once):
            receipt = dispatcher.submit(command, self.handle, execution)
        self.assertEqual(receipt.outcome, "denied")
        self.assertEqual(receipt.failure, "scope_denied")
        shutdown = dispatcher.close(self.clock.now() + timedelta(seconds=0.2))
        self.assertTrue(shutdown.owner_closed)
        self.assertEqual(shutdown.pending_command_ids, ())
        self.assertEqual(factory.created, [])

    def test_real_blocked_owner_queue_full_cancel_started_pending_and_bounded_shutdown(self):
        entered, release = threading.Event(), threading.Event()
        class BlockingFactory(ObservedFactory):
            def create(self, entry, clock):
                entered.set()
                if not release.wait(2):
                    raise RuntimeError("task-owned test gate did not release")
                return super().create(entry, clock)
        factory = BlockingFactory()
        dispatcher = self.dispatcher(factory=factory, limits=HostLimitsV1(queue_capacity=1))
        command = {"tag": "run", "release_id": "host-window-replay-v1", "request": request().model_dump(mode="json")}
        first = dispatcher.enqueue(command, self.handle, self.context(0.1))
        try:
            self.assertTrue(entered.wait(1))
            second = dispatcher.enqueue(command, self.handle, self.context())
            overflow = dispatcher.submit(command, self.handle, self.context())
            self.assertEqual(overflow.outcome, "queue_full")
            self.assertTrue(dispatcher.cancel_queued(second))
            self.assertEqual(dispatcher.wait(second).outcome, "cancelled_before_start")
            self.assertFalse(dispatcher.cancel_queued(first))
            pending = dispatcher.wait(first)
            self.assertEqual(pending.outcome, "started_pending")
            self.assertIsNone(pending.result)
            rows = read_inventory(dispatcher.inventory_root)
            self.assertEqual([row.phase for row in rows if row.command_id == pending.command_id], ["queued", "started"])
            shutdown = dispatcher.close(self.clock.now() + timedelta(seconds=0.01))
            self.assertFalse(shutdown.owner_closed)
            self.assertIn(pending.command_id, shutdown.pending_command_ids)
        finally:
            release.set()
        shutdown = dispatcher.close(self.clock.now() + timedelta(seconds=2))
        self.assertTrue(shutdown.owner_closed)
        self.assertEqual(dispatcher.wait(first).outcome, "expired")
        self.assertFalse(any(name == "run" for name, _ in factory.events))
        self.assertEqual(factory.created[0].world.calls, ())

    def test_missing_queued_or_started_inventory_denies_before_resolver_and_runtime(self):
        command = {"tag": "run", "release_id": "host-window-replay-v1", "request": request().model_dump(mode="json")}
        for phase in ("queued", "started"):
            factory = ObservedFactory()
            root = self.base / ("fault-" + phase)
            dispatcher = HostDispatcher(factory, self.resolver, self.registry, self.clock, root, HostLimitsV1(),
                                        release_id="host-window-replay-v1")
            self.addCleanup(lambda dispatcher=dispatcher: dispatcher.close(self.clock.now() + timedelta(seconds=2)))
            real = host_files._write
            def forward(descriptor, name, data):
                if b'"phase":"' + phase.encode() + b'"' in data:
                    if phase == "started":
                        real(descriptor, name, data)
                    raise OSError("synthetic private-like exception must not leak")
                return real(descriptor, name, data)
            with patch.object(host_files, "_write", side_effect=forward), patch.object(
                    self.resolver, "resolve", wraps=self.resolver.resolve) as resolver:
                receipt = dispatcher.submit(command, self.handle, self.context())
                self.assertEqual(receipt.outcome, "infrastructure_error")
                self.assertEqual(resolver.call_count, 0)
            self.assertEqual(factory.created, [])
            self.assertNotIn("private-like", receipt.model_dump_json())

    def test_final_inventory_failure_preserves_actual_scoped_result_and_journal_effect(self):
        factory = ObservedFactory()
        dispatcher = self.dispatcher(factory=factory)
        real = host_files._write
        def forward(descriptor, name, data):
            if b'"phase":"finished"' in data:
                raise OSError("task-owned finalization fault")
            return real(descriptor, name, data)
        with patch.object(host_files, "_write", side_effect=forward):
            receipt = dispatcher.submit({"tag": "run", "release_id": "host-window-replay-v1",
                "request": request().model_dump(mode="json")}, self.handle, self.context())
        self.assertEqual(receipt.outcome, "result")
        self.assertEqual(receipt.result.effects["reschedule"].status, "verified")
        self.assertEqual(factory.snapshots[-1][3]["reschedule"], 1)
        self.assertEqual(receipt.inventory_status, "partial")
        self.assertEqual(receipt.failure, "inventory_failed")
        self.assertEqual([row.phase for row in read_inventory(dispatcher.inventory_root)], ["queued", "started"])

    def test_preexisting_inventory_and_foreign_submission_never_reuse_or_disclose(self):
        root = self.base / "taken-inventory"
        root.mkdir()
        marker = root / "user-owned.txt"
        marker.write_bytes(b"keep exact preexisting bytes")
        factory = ObservedFactory()
        dispatcher = HostDispatcher(factory, self.resolver, self.registry, self.clock, root, HostLimitsV1(),
                                    release_id="host-window-replay-v1")
        self.addCleanup(lambda: dispatcher.close(self.clock.now() + timedelta(seconds=2)))
        command = {"tag": "inspect-profile", "release_id": "host-window-replay-v1"}
        receipt = dispatcher.submit(command, self.handle, self.context())
        self.assertEqual(receipt.failure, "no_durable_inventory")
        self.assertEqual(marker.read_bytes(), b"keep exact preexisting bytes")
        self.assertEqual(list(root.iterdir()), [marker])
        other = self.dispatcher()
        foreign = other.enqueue(command, self.handle, self.context())
        with self.assertRaises(ValueError):
            dispatcher.wait(foreign)
        with self.assertRaises(ValueError):
            dispatcher.cancel_queued(receipt.command_id)
        self.assertEqual(factory.created, [])

    def test_close_commits_queued_cancellation_before_owner_inventory_close(self):
        owner_continue = threading.Event()
        class PausedDispatcher(HostDispatcher):
            def _owner(self):
                owner_continue.wait(2)
                super()._owner()
        factory = ObservedFactory()
        dispatcher = PausedDispatcher(factory, self.resolver, self.registry, self.clock,
            self.base / "close-inventory", HostLimitsV1(), release_id="host-window-replay-v1")
        submission = dispatcher.enqueue({"tag": "inspect-profile", "release_id": "host-window-replay-v1"},
                                        self.handle, self.context())
        owner_closed = threading.Event()
        close = dispatcher._inventory.close
        finish = dispatcher._finish
        def observed_close():
            close()
            owner_closed.set()
        def forwarded_finish(state):
            owner_continue.set()
            owner_closed.wait(0.03)
            return finish(state)
        try:
            with patch.object(dispatcher._inventory, "close", side_effect=observed_close), patch.object(
                    dispatcher, "_finish", side_effect=forwarded_finish):
                shutdown = dispatcher.close(self.clock.now() + timedelta(seconds=1))
            self.assertTrue(shutdown.owner_closed)
            self.assertFalse(shutdown.inventory_failure)
            self.assertEqual(dispatcher.wait(submission).outcome, "cancelled_before_start")
            self.assertEqual([row.phase for row in read_inventory(dispatcher.inventory_root)], ["queued", "finished"])
            self.assertEqual(factory.created, [])
        finally:
            owner_continue.set()
            dispatcher.close(self.clock.now() + timedelta(seconds=1))

    def test_failed_clock_at_dequeue_is_contained_without_resolver_or_runtime(self):
        owner_continue = threading.Event()
        class FailingClock(SyntheticReplayClock):
            fail = False
            def now(self):
                if self.fail:
                    raise ValueError("task-owned invalid clock observation")
                return super().now()
        clock = FailingClock()
        class PausedDispatcher(HostDispatcher):
            def _owner(self):
                owner_continue.wait(2)
                super()._owner()
        factory = ObservedFactory()
        dispatcher = PausedDispatcher(factory, self.resolver, self.registry, clock,
            self.base / "clock-failure-inventory", HostLimitsV1(), release_id="host-window-replay-v1")
        execution = ExecutionContext.capture(clock.now() + timedelta(seconds=2), clock)
        submission = dispatcher.enqueue({"tag": "inspect-profile", "release_id": "host-window-replay-v1"},
                                        self.handle, execution)
        try:
            with patch.object(self.resolver, "resolve", wraps=self.resolver.resolve) as resolve:
                clock.fail = True
                owner_continue.set()
                self.assertTrue(dispatcher._state(submission).done.wait(0.1))
                clock.fail = False
                receipt = dispatcher.wait(submission)
                self.assertEqual(receipt.outcome, "denied")
                self.assertEqual(receipt.inventory_status, "partial")
                self.assertEqual(resolve.call_count, 0)
                self.assertEqual(factory.created, [])
        finally:
            clock.fail = False
            owner_continue.set()
            dispatcher.close(clock.now() + timedelta(seconds=1))

    def test_queued_expiry_uses_original_capture_without_second_resolver(self):
        entered, release = threading.Event(), threading.Event()
        class BlockingFactory(ObservedFactory):
            def create(self, entry, clock):
                entered.set()
                if not release.wait(2):
                    raise RuntimeError("task-owned gate timed out")
                return super().create(entry, clock)
        dispatcher = self.dispatcher(factory=BlockingFactory())
        command = {"tag": "run", "release_id": "host-window-replay-v1", "request": request().model_dump(mode="json")}
        try:
            with patch.object(self.resolver, "resolve", wraps=self.resolver.resolve) as resolve:
                first = dispatcher.enqueue(command, self.handle, self.context(5))
                self.assertTrue(entered.wait(1))
                original = self.context(0.03)
                queued = dispatcher.enqueue(command, self.handle, original)
                receipt = dispatcher.wait(queued)
                self.assertEqual(receipt.outcome, "expired")
                self.assertIsNone(receipt.started_at)
                self.assertEqual(receipt.execution.deadline, original.deadline)
                self.assertEqual(resolve.call_count, 1)
        finally:
            release.set()
        self.assertTrue(dispatcher.close(self.clock.now() + timedelta(seconds=2)).owner_closed)
        self.assertEqual(dispatcher.wait(first).outcome, "result")

    def test_concurrent_callers_proofs_and_actual_recover_stop_share_one_owner(self):
        entered, release, second_queued = threading.Event(), threading.Event(), threading.Event()
        class BlockingFactory(ObservedFactory):
            def create(self, entry, clock):
                entered.set()
                if not release.wait(2):
                    raise RuntimeError("task-owned gate timed out")
                return super().create(entry, clock)
        factory = BlockingFactory()
        dispatcher = self.dispatcher(factory=factory)
        command = {"tag": "run", "release_id": "host-window-replay-v1", "request": request().model_dump(mode="json")}
        receipts, errors = [], []
        def caller(handle, queued=None):
            try:
                execution = self.context()
                submission = dispatcher.enqueue(command, handle, execution)
                if queued is not None:
                    queued.set()
                receipts.append(dispatcher.wait(submission))
            except Exception as error:
                errors.append(type(error).__name__)
        callers = [threading.Thread(target=caller, args=(self.handle,)),
            threading.Thread(target=caller, args=(self.resolver.handle("wrong-proof"), second_queued))]
        try:
            callers[0].start()
            self.assertTrue(entered.wait(1))
            callers[1].start()
            self.assertTrue(second_queued.wait(1))
        finally:
            release.set()
        for thread in callers:
            thread.join(5)
            self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual([receipt.outcome for receipt in receipts], ["result", "result"])
        self.assertEqual(sorted(receipt.result.status for receipt in receipts), ["authorized", "denied"])
        denied = next(receipt.result for receipt in receipts if receipt.result.status == "denied")
        self.assertIsNone(denied.binding)
        self.assertEqual(dict(denied.effects), {})
        self.assertTrue(all(auth is None for auth in factory.auth_snapshots))
        self.assertEqual(factory.snapshots[-1][3]["reschedule"], 1)
        resource = factory.created[0]
        with self.assertRaises(ValueError):
            RuntimeResources.close(resource)
        self.assertFalse(resource.closed)
        recovered = dispatcher.submit({"tag": "recover", "release_id": command["release_id"], "case_id": "C1"},
            self.handle, self.context())
        # Completed recovery intentionally returns unavailable; the host must
        # forward that factual engine result rather than fabricate success.
        self.assertEqual(recovered.result.status, "denied")
        self.assertEqual(recovered.result.reason, "unavailable")
        generation = factory.snapshots[-1][0].binding.generation
        stopped = dispatcher.submit({"tag": "stop", "release_id": command["release_id"], "case_id": "C1", "generation": generation},
            self.handle, self.context())
        self.assertEqual(stopped.result.status, "authorized")
        self.assertTrue(stopped.result.stop.requested)
        self.assertEqual(factory.snapshots[-1][3]["reschedule"], 1)
        checkpoint = factory.snapshots[-1][0]
        reply = ScopedReply(question_id="not-a-created-wait", binding=checkpoint.binding, actor_id="U1",
            proof_reference="synthetic-proof", request_revision="v1", consent_revision="v1",
            owner_state_revision="v1", fields={}, received_at=self.clock.now(), simulated=True)
        answered = dispatcher.submit({"tag": "reply", "release_id": command["release_id"],
            "reply": reply.model_dump(mode="json")}, self.handle, self.context())
        self.assertEqual(answered.outcome, "result")
        self.assertEqual(answered.result.status, "denied")
        self.assertIn("reply", [name for name, _ in factory.events])
        self.assertEqual(factory.snapshots[-1][3]["reschedule"], 1)

    def test_actual_process_exit_after_public_source_effect_keeps_started_inventory_and_original_debt(self):
        base = self.base / "crash"
        base.mkdir()
        code = '''
from dataclasses import replace
from datetime import timedelta
import os
from pathlib import Path
import sys
from proofkey.clock import SyntheticReplayClock
from proofkey.contracts import AuthContext, CanonicalRequest
from proofkey.engine import WorkflowEngine
from proofkey.execution import ExecutionContext
from proofkey.host import AuthResolver, HostDispatcher, ProfileRegistry, RuntimeFactory
from proofkey.host_contracts import HostLimitsV1
class ExitFactory(RuntimeFactory):
    def create(self, release, clock):
        resource = super().create(release, clock)
        bundle = resource.world.bundle()
        actual = bundle.scheduling
        class ExitPort:
            def __getattr__(self, name):
                return getattr(actual, name)
            def reschedule(self, intent, *, deadline):
                actual.reschedule(intent, deadline=deadline)
                os._exit(91)
        resource.engine = WorkflowEngine(resource.profile, replace(bundle, scheduling=ExitPort()), resource.store, clock)
        return resource
base=Path(sys.argv[1])
clock=SyntheticReplayClock()
registry=ProfileRegistry.builtin(base/'resources')
resolver=AuthResolver({'documentary':AuthContext(caller_id='U1',proof_reference='synthetic-proof')})
execution=ExecutionContext.capture(clock.now()+timedelta(seconds=20),clock)
dispatcher=HostDispatcher(ExitFactory(),resolver,registry,clock,base/'inventory',HostLimitsV1(),release_id='host-window-replay-v1')
request=CanonicalRequest(case_id='C1',object_id='O1',principal_id='U1',request_id='REQ1',request_revision='v1',consent_revision='v1',
    kind='reschedule_window',consent_mode='window',arguments={'window_start':'2026-10-08T10:00:00+00:00','window_end':'2026-10-08T12:00:00+00:00',
    'inventory':{'item-1':1}},evidence_ids=[])
dispatcher.submit({'tag':'run','release_id':'host-window-replay-v1','request':request.model_dump(mode='json')},resolver.handle('documentary'),execution)
os._exit(92)
'''
        process = subprocess.run([sys.executable, "-c", code, str(base)],
            env={"PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(ROOT / "src")}, capture_output=True, timeout=10)
        self.assertEqual(process.returncode, 91, process.stderr.decode())
        with patch("proofkey.host.WorkflowEngine.run", side_effect=AssertionError("readback must not invoke engine")):
            rows = read_inventory(base / "inventory")
        self.assertEqual([row.phase for row in rows], ["queued", "started"])
        self.assertEqual(rows[0].execution, rows[1].execution)
        release = self.registry.resolve("host-window-replay-v1")
        world = SimulatedWorld(base / "resources/host-window-replay-v1/world.sqlite", release.fixture_path,
                               profile=release.validate(), clock=self.clock)
        store = CaseStore(base / "resources/host-window-replay-v1/journal.sqlite")
        try:
            intents = store.intents("C1")
            self.assertEqual(len(intents), 1)
            self.assertEqual(intents[0].state, "dispatching")
            self.assertIsNone(intents[0].verification)
            self.assertGreaterEqual(store.checkpoint("C1").budget.active_seconds, 10)
            self.assertEqual(world.effect_count("reschedule"), 1)
            print("HOST-CRASH", json.dumps({"exit": process.returncode, "inventory_phases": [row.phase for row in rows],
                "intent_state": intents[0].state, "tool_calls": store.checkpoint("C1").budget.tool_calls,
                "active_seconds": store.checkpoint("C1").budget.active_seconds, "reschedule_effects": world.effect_count("reschedule")}, sort_keys=True))
        finally:
            store.close()

    def test_foreign_proof_body_release_and_unavailable_do_not_enter_engine(self):
        factory = ObservedFactory()
        dispatcher = self.dispatcher(factory=factory)
        command = {"tag": "inspect-profile", "release_id": "host-window-replay-v1"}
        foreign = AuthResolver({"other": AuthContext(caller_id="U1", proof_reference="synthetic-proof")}).handle("other")
        for handle in (None, "synthetic-user", foreign):
            self.assertEqual(dispatcher.submit(command, handle, self.context()).outcome, "denied")
        self.assertEqual(dispatcher.submit({**command, "auth": {"proof_reference": "body"}},
                                           self.handle, self.context()).failure, "invalid_command")
        self.assertEqual(dispatcher.submit({**command, "release_id": "host-goods-replay-v1"},
                                           self.handle, self.context()).outcome, "denied")
        inspection = dispatcher.submit(command, self.handle, self.context())
        self.assertEqual(inspection.outcome, "inspection")
        self.assertEqual(inspection.inspection.profile_hash,
                         "5bb712b13efaace655ee7180f3d913d93cbd637e3d1685331c6a1eecbade7bf4")
        for tag in ("batch", "transfer"):
            self.assertEqual(dispatcher.submit({"tag": tag, "release_id": command["release_id"]},
                self.handle, self.context()).outcome, "unavailable")
        self.assertEqual(factory.created, [])
