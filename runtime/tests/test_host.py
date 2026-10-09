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
from proofkey.contracts import AuthContext, ScopedReply, ReadRequest, ReadTarget
from proofkey.execution import ExecutionContext
from proofkey.host import AuthResolver, HostDispatcher, ProfileRegistry, RuntimeFactory, RuntimeResources
from proofkey.host_contracts import HostLimitsV1
from proofkey.host_files import HostInventory, read_inventory
import proofkey.host_files as host_files
import proofkey.host as host_module
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

    def test_close_cutoff_does_not_wait_for_owner_publication_and_preserves_pending_cancellation(self):
        factory_entered, factory_release = threading.Event(), threading.Event()
        publication_entered, publication_release = threading.Event(), threading.Event()
        caller_done = threading.Event()
        results, errors = [], []
        class BlockingFactory(ObservedFactory):
            def create(inner, entry, clock):
                factory_entered.set()
                if not factory_release.wait(3):
                    raise RuntimeError("task-local factory barrier timed out")
                return super().create(entry, clock)
        factory = BlockingFactory()
        actual_publish = HostInventory.publish
        def forward_publish(inventory, sequence, phase, value):
            if sequence == 1 and phase == "finished":
                publication_entered.set()
                if not publication_release.wait(3):
                    raise RuntimeError("task-local publication barrier timed out")
            return actual_publish(inventory, sequence, phase, value)
        caller = None
        with patch.object(HostInventory, "publish", forward_publish), patch.object(
                self.resolver, "resolve", wraps=self.resolver.resolve) as resolve:
            dispatcher = self.dispatcher(factory=factory)
            try:
                first = dispatcher.enqueue({"tag": "run", "release_id": "host-window-replay-v1",
                    "request": request().model_dump(mode="json")}, self.handle, self.context())
                self.assertTrue(factory_entered.wait(1))
                second = dispatcher.enqueue({"tag": "inspect-profile", "release_id": "host-window-replay-v1"},
                    self.handle, self.context())
                factory_release.set()
                self.assertTrue(publication_entered.wait(5))
                cutoff = self.clock.now() + timedelta(seconds=0.03)
                def close_caller():
                    try:
                        results.append(dispatcher.close(cutoff))
                    except Exception as error:
                        errors.append(type(error).__name__)
                    finally:
                        caller_done.set()
                caller = threading.Thread(target=close_caller, name="task-local-close-observer")
                caller.start()
                returned_bounded = caller_done.wait(0.15)
                held_rows = read_inventory(dispatcher.inventory_root)
                self.assertFalse(any(row.phase == "finished" for row in held_rows))
                if returned_bounded:
                    shutdown = results[0]
                    self.assertFalse(shutdown.owner_closed)
                    self.assertEqual(set(shutdown.pending_command_ids), {row.command_id for row in held_rows})
                    prevented = dispatcher.wait(second)
                    self.assertEqual(prevented.outcome, "cancelled_before_start")
                    self.assertIsNone(prevented.started_at)
                    self.assertIsNone(prevented.finished_at)
                    self.assertEqual(prevented.inventory_status, "partial")
                    self.assertEqual(len(prevented.inventory_references), 1)
            finally:
                factory_release.set()
                publication_release.set()
                if caller is not None:
                    caller.join(5)
                    self.assertFalse(caller.is_alive())
                shutdown = dispatcher.close(self.clock.now() + timedelta(seconds=2))
                self.assertTrue(shutdown.owner_closed)
            self.assertEqual(errors, [])
            self.assertEqual(resolve.call_count, 1)
            self.assertEqual(dispatcher.wait(first).result.status, "authorized")
            cancelled = dispatcher.wait(second)
            self.assertEqual(cancelled.outcome, "cancelled_before_start")
            self.assertIsNone(cancelled.started_at)
            self.assertIsNotNone(cancelled.finished_at)
            self.assertEqual(cancelled.inventory_status, "committed")
            self.assertEqual([row.phase for row in read_inventory(dispatcher.inventory_root)
                if row.command_id == cancelled.command_id], ["queued", "finished"])
            cp, intents, calls, effects = factory.snapshots[-1]
            self.assertEqual(cp.budget.tool_calls, len(calls))
            self.assertEqual(effects["reschedule"], 1)
            self.assertEqual(len(intents), 1)
            self.assertEqual({thread for _, thread in factory.events}, {dispatcher._thread.ident})
            print("HOST-FIX-I1", json.dumps({"returned_bounded": returned_bounded,
                "close_elapsed": results[0].elapsed_seconds, "close_overrun": results[0].overrun_seconds,
                "tool_calls": cp.budget.tool_calls, "active_seconds": cp.budget.active_seconds,
                "source_calls": len(calls), "effects": effects, "intents": len(intents)}, sort_keys=True))
            self.assertTrue(returned_bounded, "close waited for owner publication beyond its cutoff")

    def test_factory_consumes_pinned_fixture_bytes_despite_constructor_path_substitution(self):
        entry = self.registry.resolve("host-window-replay-v1")
        original = entry.fixture_path.read_bytes()
        private_fixture = self.base / "private-fixture.json"
        private_fixture.write_bytes(original)
        altered = json.loads(original)
        altered["facts"]["delivery.status"]["value"] = "delivered"
        substituted = json.dumps(altered, sort_keys=True).encode("utf-8")
        entry = replace(entry, fixture_path=private_fixture)
        actual_world = SimulatedWorld
        forwarded = []
        def forward_world(path, fixture, **kwargs):
            private_fixture.write_bytes(substituted)
            try:
                world = actual_world(path, fixture, **kwargs)
                forwarded.append(type(world))
                return world
            finally:
                private_fixture.write_bytes(original)
        with patch.object(host_module, "SimulatedWorld", forward_world):
            resources = RuntimeFactory().create(entry, self.clock)
        try:
            reply = resources.world.bundle().delivery.read_delivery(ReadRequest(case_id="C1", object_id="O1",
                caller_id="U1", proof_reference="synthetic-proof", purpose="reconcile",
                deadline=self.clock.now() + timedelta(seconds=5),
                target=ReadTarget(kind="authority_facts", authority="delivery", facts=["status"])))
            values = {observation.fact: observation.value for observation in reply.observations}
            self.assertEqual(forwarded, [SimulatedWorld])
            self.assertEqual(sha256(private_fixture.read_bytes()).hexdigest(), entry.fixture_hash)
            self.assertEqual(len(resources.world.calls), 1)
            print("HOST-FIX-I2", json.dumps({"observed": values, "source_calls": len(resources.world.calls),
                "effects": resources.world.effect_count("reschedule"), "restored_hash": entry.fixture_hash}, sort_keys=True))
            self.assertEqual(values, {"status": "scheduled"}, "accepted source consumed substituted pathname bytes")
        finally:
            resources.close()

    def test_queued_prevention_wakes_waiter_without_caller_finalization(self):
        owner_continue, waiting, waiter_done = threading.Event(), threading.Event(), threading.Event()
        class PausedDispatcher(HostDispatcher):
            def _owner(inner):
                owner_continue.wait(3)
                super()._owner()
        dispatcher = PausedDispatcher(ObservedFactory(), self.resolver, self.registry, self.clock,
            self.base / "cancel-waiter", HostLimitsV1(), release_id="host-window-replay-v1")
        submission = dispatcher.enqueue({"tag": "inspect-profile", "release_id": "host-window-replay-v1"},
            self.handle, self.context())
        receipts = []
        def waiter():
            waiting.set()
            receipts.append(dispatcher.wait(submission))
            waiter_done.set()
        thread = threading.Thread(target=waiter, name="task-local-waiter")
        try:
            thread.start()
            self.assertTrue(waiting.wait(1))
            self.assertTrue(dispatcher.cancel_queued(submission))
            self.assertFalse(dispatcher.cancel_queued(submission))
            self.assertTrue(waiter_done.wait(0.2))
            self.assertIsNone(receipts[0].finished_at)
            self.assertIsNone(receipts[0].started_at)
            self.assertEqual(receipts[0].inventory_status, "partial")
            self.assertEqual([row.phase for row in read_inventory(dispatcher.inventory_root)], ["queued"])
            owner_continue.set()
            self.assertTrue(dispatcher.close(self.clock.now() + timedelta(seconds=2)).owner_closed)
            self.assertEqual([row.phase for row in read_inventory(dispatcher.inventory_root)], ["queued", "finished"])
        finally:
            owner_continue.set()
            dispatcher.close(self.clock.now() + timedelta(seconds=2))
            thread.join(2)
            self.assertFalse(thread.is_alive())

    def test_admission_racing_close_retains_one_owner_cancellation_marker(self):
        committed, release_admission = threading.Event(), threading.Event()
        actual_publish = HostInventory.publish
        submissions, errors = [], []
        publish_threads = []
        def forward_publish(inventory, sequence, phase, value):
            reference = actual_publish(inventory, sequence, phase, value)
            publish_threads.append((phase, threading.get_ident()))
            if phase == "queued":
                committed.set()
                if not release_admission.wait(3):
                    raise RuntimeError("task-local admission gate timed out")
            return reference
        with patch.object(HostInventory, "publish", forward_publish), patch.object(
                self.resolver, "resolve", wraps=self.resolver.resolve) as resolve:
            factory = ObservedFactory()
            dispatcher = self.dispatcher(factory=factory)
            def admit():
                try:
                    submissions.append(dispatcher.enqueue({"tag": "inspect-profile", "release_id": "host-window-replay-v1"},
                        self.handle, self.context()))
                except Exception as error:
                    errors.append(type(error).__name__)
            thread = threading.Thread(target=admit, name="task-local-admission")
            try:
                thread.start()
                self.assertTrue(committed.wait(1))
                pending_close = dispatcher.close(self.clock.now() + timedelta(seconds=0.01))
                self.assertFalse(pending_close.owner_closed)
                self.assertEqual([row.phase for row in read_inventory(dispatcher.inventory_root)], ["queued"])
            finally:
                release_admission.set()
                thread.join(3)
                self.assertFalse(thread.is_alive())
                self.assertTrue(dispatcher.close(self.clock.now() + timedelta(seconds=2)).owner_closed)
            self.assertEqual(errors, [])
            self.assertEqual(resolve.call_count, 0)
            self.assertEqual(factory.created, [])
            receipt = dispatcher.wait(submissions[0])
            self.assertEqual(receipt.outcome, "cancelled_before_start")
            self.assertIsNone(receipt.started_at)
            self.assertEqual([row.phase for row in read_inventory(dispatcher.inventory_root)], ["queued", "finished"])
            self.assertEqual([owner for phase, owner in publish_threads if phase == "finished"], [dispatcher._thread.ident])

    def test_owner_cancellation_publication_failure_keeps_original_partial_evidence(self):
        owner_continue = threading.Event()
        class PausedDispatcher(HostDispatcher):
            def _owner(inner):
                owner_continue.wait(3)
                super()._owner()
        dispatcher = PausedDispatcher(ObservedFactory(), self.resolver, self.registry, self.clock,
            self.base / "cancel-publication-failure", HostLimitsV1(), release_id="host-window-replay-v1")
        actual_publish = HostInventory.publish
        def failed_finish(inventory, sequence, phase, value):
            if phase == "finished":
                raise OSError("task-local publication failure")
            return actual_publish(inventory, sequence, phase, value)
        try:
            submission = dispatcher.enqueue({"tag": "inspect-profile", "release_id": "host-window-replay-v1"},
                self.handle, self.context())
            self.assertTrue(dispatcher.cancel_queued(submission))
            with patch.object(HostInventory, "publish", failed_finish):
                owner_continue.set()
                shutdown = dispatcher.close(self.clock.now() + timedelta(seconds=2))
                self.assertTrue(shutdown.owner_closed)
                self.assertTrue(shutdown.inventory_failure)
            receipt = dispatcher.wait(submission)
            self.assertEqual(receipt.outcome, "cancelled_before_start")
            self.assertEqual(receipt.failure, "inventory_failed")
            self.assertEqual(receipt.inventory_status, "partial")
            self.assertIsNone(receipt.started_at)
            self.assertEqual(len(receipt.inventory_references), 1)
            self.assertEqual([row.phase for row in read_inventory(dispatcher.inventory_root)], ["queued"])
        finally:
            owner_continue.set()
            dispatcher.close(self.clock.now() + timedelta(seconds=2))

    def test_factory_profile_snapshot_never_reopens_path_and_keeps_validation(self):
        entry = self.registry.resolve("host-window-replay-v1")
        private_profile = self.base / "private-profile.json"
        original = entry.profile_path.read_bytes()
        private_profile.write_bytes(original)
        entry = replace(entry, profile_path=private_profile)
        actual_read = Path.read_text
        def guarded_read(path, *args, **kwargs):
            if path == private_profile:
                raise AssertionError("verified profile must not be reopened for semantic parsing")
            return actual_read(path, *args, **kwargs)
        with patch.object(Path, "read_text", guarded_read):
            resources = RuntimeFactory().create(entry, self.clock)
        resources.close()
        self.assertEqual(resources.profile.release_hash, entry.profile_hash)
        invalid_profiles = [b'{}', b'\xff', original.replace(b'{', b'{"profile_id":"duplicate",', 1)]
        malformed = json.loads(original)
        malformed["process_hash"] = "0" * 64
        invalid_profiles.append(json.dumps(malformed).encode("utf-8"))
        for raw in invalid_profiles:
            with self.subTest(raw_hash=sha256(raw).hexdigest()):
                private_profile.write_bytes(raw)
                invalid = replace(entry, profile_file_hash=sha256(raw).hexdigest())
                with self.assertRaises(ValueError):
                    invalid.validate()

    def test_fixture_bytes_are_exact_bounded_utf8_and_keep_legacy_default(self):
        entry = self.registry.resolve("host-window-replay-v1")
        profile = entry.validate()
        raw = entry.fixture_path.read_bytes()
        class BytesSubclass(bytes):
            pass
        invalid = (b"", b"x" * 1048577, bytearray(raw), BytesSubclass(raw), raw.decode("utf-8"), b"\xff", b"{", b"{}")
        for index, value in enumerate(invalid):
            with self.subTest(index=index):
                path = self.base / f"invalid-bytes-{index}.sqlite"
                with self.assertRaises((ValueError, KeyError)):
                    SimulatedWorld(path, entry.fixture_path, profile=profile, clock=self.clock, fixture_bytes=value)
                self.assertFalse(path.exists())
        missing_path = self.base / "not-a-fixture.json"
        for index, kwargs in enumerate(({"fixture_bytes": raw}, {})):
            world = SimulatedWorld(self.base / f"valid-bytes-{index}.sqlite",
                missing_path if kwargs else entry.fixture_path, profile=profile, clock=self.clock, **kwargs)
            observed = world.bundle().delivery.read_delivery(ReadRequest(case_id="C1", object_id="O1",
                caller_id="U1", proof_reference="synthetic-proof", purpose="reconcile",
                deadline=self.clock.now() + timedelta(seconds=5),
                target=ReadTarget(kind="authority_facts", authority="delivery", facts=["status"])))
            self.assertEqual({row.fact: row.value for row in observed.observations}, {"status": "scheduled"})
        changed = json.loads(raw)
        changed["facts"]["delivery.status"]["value"] = "delivered"
        with self.assertRaisesRegex(ValueError, "different fixture"):
            SimulatedWorld(self.base / "valid-bytes-0.sqlite", missing_path, profile=profile, clock=self.clock,
                fixture_bytes=json.dumps(changed).encode("utf-8"))

    def test_fixture_snapshot_preserves_v14_duplicate_and_ownership_validation(self):
        from proofkey.profiles import load_profile
        profile = load_profile("flat-v1.4")
        raw = (ROOT / "fixtures/development/ownership-world-v1.json").read_bytes()
        absent = self.base / "absent-ownership-fixture.json"
        world = SimulatedWorld(self.base / "owned-byte-source.sqlite", absent,
            profile=profile, clock=self.clock, fixture_bytes=raw)
        self.assertIsNotNone(world.bundle().operator)
        duplicate = raw.replace(b"{", b'{"version":"synthetic-provider-v1",', 1)
        no_authority = json.loads(raw)
        no_authority.pop("ownership_authority")
        for index, invalid in enumerate((duplicate, json.dumps(no_authority).encode("utf-8"))):
            with self.subTest(index=index):
                path = self.base / f"invalid-ownership-bytes-{index}.sqlite"
                with self.assertRaises(ValueError):
                    SimulatedWorld(path, absent, profile=profile, clock=self.clock, fixture_bytes=invalid)
                self.assertFalse(path.exists())

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
        def observed_close():
            close()
            owner_closed.set()
        try:
            with patch.object(dispatcher._inventory, "close", side_effect=observed_close):
                bounded = dispatcher.close(self.clock.now() + timedelta(seconds=0.01))
                self.assertFalse(bounded.owner_closed)
                pending = dispatcher.wait(submission)
                self.assertIsNone(pending.finished_at)
                self.assertEqual(pending.inventory_status, "partial")
                self.assertFalse(owner_closed.is_set())
                owner_continue.set()
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
                self.assertIsNone(receipt.finished_at)
                self.assertEqual(receipt.inventory_status, "partial")
                self.assertEqual(len(receipt.inventory_references), 1)
                self.assertEqual(receipt.execution.deadline, original.deadline)
                self.assertEqual(resolve.call_count, 1)
        finally:
            release.set()
        self.assertTrue(dispatcher.close(self.clock.now() + timedelta(seconds=2)).owner_closed)
        self.assertEqual(dispatcher.wait(first).outcome, "result")
        completed = dispatcher.wait(queued)
        self.assertEqual(completed.outcome, "expired")
        self.assertIsNotNone(completed.finished_at)
        self.assertEqual(completed.inventory_status, "committed")
        self.assertEqual([row.phase for row in read_inventory(dispatcher.inventory_root)
            if row.command_id == completed.command_id], ["queued", "finished"])

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
