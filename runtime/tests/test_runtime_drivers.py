"""Public synthetic runtime pilot; controls are not calibrated reference gold."""
from dataclasses import asdict, replace
from hashlib import sha256
from pathlib import Path
import tempfile
import unittest

from proofkey.assessment.driver_contracts import (DriverManifest, DriverCapture,
    RunnerReceipt, canonical_bytes, strict_loads, digest_bytes)
from proofkey.assessment.drivers import (RegisteredDriver, DriverRegistry, run_driver,
    assess_driver)
from proofkey.adapters.world import SimulatedWorld
from proofkey.contracts import CanonicalRequest, AuthContext
from proofkey.engine import WorkflowEngine
from proofkey.journal import CaseStore
from proofkey.profiles import load_profile
from proofkey.identity import request_fingerprint
from proofkey.ports import AdapterBundle
from support import FakeClock, NOW, DEADLINE

ROOT = Path(__file__).resolve().parents[1]
# Concrete runtime closure, including lazily constructed ports and journal services.
# Pilot implementation and test recipe bytes join the concrete candidate too.
SOURCE_FILES = tuple("src/proofkey/" + name for name in (
    "__init__.py", "contracts.py", "identity.py", "profiles.py", "process.py",
    "policy.py", "ports.py", "verifier.py", "budget.py", "journal.py", "admission.py", "execution.py",
    "execution_consumer.py", "engine.py", "gateway.py", "replay.py", "waits.py",
    "wait_contracts.py", "packets.py", "packet_contracts.py", "ownership.py",
    "ownership_contracts.py", "ownership_store.py", "ownership_gateway.py", "processing.py",
    "adapters/__init__.py", "adapters/world.py", "adapters/ownership.py", "adapters/case.py",
    "adapters/delivery.py", "adapters/scheduling.py", "adapters/returns.py",
    "adapters/messaging.py", "adapters/operator.py",
    "assessment/__init__.py", "assessment/contracts.py", "assessment/driver_contracts.py", "assessment/drivers.py")) + (
    "profiles/flat-v1.2.json", "fixtures/development/world.json", "tests/support.py",
    "tests/test_runtime_drivers.py", "tests/test_runtime_driver_contracts.py")


def snapshot():
    return canonical_bytes({"version": "candidate-source-v1", "kind": "filesystem",
        "files": {name: sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCE_FILES}})


def expectation(*predicates):
    return canonical_bytes({"version": "driver-expectation-v1", "expectation_version": "pilot-v1",
                            "predicates": list(predicates)})


def equals(identifier, tag, path, wanted):
    return {"id": identifier, "event_tag": tag, "field_path": path, "operation": "equals", "expected": wanted}


def request_bytes(kind="reschedule_window", mode="window", arguments=None):
    if arguments is None:
        arguments = {"window_start": NOW.isoformat(), "window_end": DEADLINE.isoformat()}
    request = {"case_id": "C1", "object_id": "O1", "principal_id": "U1", "request_id": "REQ1",
        "request_revision": "v1", "consent_revision": "v1", "kind": kind,
        "consent_mode": mode, "arguments": arguments, "evidence_ids": []}
    return canonical_bytes({"request": request, "auth": {"caller_id": "U1", "proof_reference": "synthetic-proof"}})


class ForwardPort:
    """Record exact public transport inputs/readbacks while delegating every call."""
    def __init__(self, real, sink):
        self.real, self.sink = real, sink

    def __getattr__(self, name):
        method = getattr(self.real, name)
        def call(argument, **kwargs):
            returned = method(argument, **kwargs)
            self.sink.emit(canonical_bytes({"event_tag": "port", "operation": name,
                "input": argument.model_dump(mode="json"), "output": returned.model_dump(mode="json")}))
            return returned
        return call


class CountingPlanner:
    def __init__(self):
        self.calls = 0

    def propose(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError("Historical replay entered planning")


def public_callback(view, sink):
    # No manifest/reference/rubric is available to this public-runtime composition.
    raw, scenario = strict_loads(view.input_sequence_bytes), strict_loads(view.scenario_bytes)
    request, auth = CanonicalRequest.model_validate(raw["request"]), AuthContext.model_validate(raw["auth"])
    clock, profile = FakeClock(), load_profile("flat-v1.2")
    operations = ("reschedule", "register_goods_refusal", "create_return", "register_service_refusal",
                  "send_clarification", "send_status", "enqueue_handoff", "transfer_owner")
    with tempfile.TemporaryDirectory() as folder:
        world = SimulatedWorld(Path(folder) / "world.sqlite", ROOT / "fixtures/development/world.json",
                               profile=profile, clock=clock)
        # Source instructions are independently declared and hash-bound before entry.
        world.mutate("customer.request_fingerprint", request_fingerprint(request))
        world.mutate("customer.consent_mode", request.consent_mode)
        for fact, value in scenario["mutations"]:
            world.mutate(fact, value)
        for operation, behavior in scenario["faults"]:
            world.set_fault(operation, behavior)
        real = world.bundle()
        bundle = AdapterBundle(**{name: ForwardPort(getattr(real, name), sink)
                                  for name in ("case", "delivery", "scheduling", "returns", "messaging", "operator")})
        store = CaseStore(Path(folder) / "journal.sqlite")
        try:
            engine = WorkflowEngine(profile, bundle, store, clock)
            original = engine.run(request, auth)
            sink.emit(canonical_bytes({"event_tag": "result", "output": original.model_dump(mode="json")}))
            sink.emit(canonical_bytes({"event_tag": "physical", "counts": {operation: world.effect_count(operation)
                                                                               for operation in operations}}))
            if store.has_case(request.case_id):
                checkpoint = store.checkpoint(request.case_id)
                sink.emit(canonical_bytes({"event_tag": "journal", "checkpoint": checkpoint.model_dump(mode="json"),
                    "original_request": store.original_request(request.case_id, checkpoint.binding.generation).model_dump(mode="json"),
                    "intents": [record.model_dump(mode="json") for record in store.intents(request.case_id)],
                    "source_revisions": world.material_revisions().model_dump(mode="json")}))
            if scenario["replay"]:
                saved = store.saved_result(request.case_id, "G1")
                before = store.checkpoint(request.case_id)
                before_calls, before_effects = len(world.calls), {op: world.effect_count(op) for op in operations}
                for fact, value in scenario["replay_mutations"]:
                    world.mutate(fact, value)
                planner = CountingPlanner()
                replay = WorkflowEngine(profile, bundle, store, clock, planner=planner).run(request, auth)
                after = store.checkpoint(request.case_id)
                sink.emit(canonical_bytes({"event_tag": "replay", "output": replay.model_dump(mode="json"),
                    "saved_before": saved.model_dump(mode="json"),
                    "saved_after": store.saved_result(request.case_id, "G1").model_dump(mode="json"),
                    "checkpoint_before": before.model_dump(mode="json"), "checkpoint_after": after.model_dump(mode="json"),
                    "original": store.original_request(request.case_id, "G1").model_dump(mode="json"),
                    "intents": [record.model_dump(mode="json") for record in store.intents(request.case_id)],
                    "planner_calls": planner.calls, "effect_delta": {op: world.effect_count(op) - before_effects[op] for op in operations},
                    "calls": [asdict(call) for call in world.calls[before_calls:]],
                    "source_instructions": scenario["replay_mutations"],
                    "source_revisions": world.material_revisions().model_dump(mode="json"),
                    "bindings": [binding.model_dump(mode="json") for binding in store.request_bindings(request.case_id)]}))
            return DriverCapture(sink.events, canonical_bytes(original.model_dump(mode="json")))
        finally:
            store.close()


def registration(callback=public_callback, *, inputs=None, scenario=None, expect=None,
                 variant="positive", obligation="R01", group="pilot-window", fixture_only=False, **changes):
    inputs = request_bytes() if inputs is None else inputs
    scenario = canonical_bytes({"mutations": [], "faults": [], "replay": False}) if scenario is None else scenario
    expect = expectation(equals("physical-once", "physical", ["counts", "reschedule"], 1)) if expect is None else expect
    candidate = (canonical_bytes({"version": "candidate-source-v1", "kind": "fixture-only", "files": {"synthetic": "a" * 64}})
                 if fixture_only else snapshot())
    profile = canonical_bytes(load_profile("flat-v1.2").model_dump(mode="json"))
    profile_data = strict_loads(profile)
    process = canonical_bytes(profile_data["processes"])
    policy = canonical_bytes({"policy_id": "synthetic-test-policy-v1", "version": "v1", "evidence_mode": "synthetic",
        "native_routes_enabled": False, "live_roles": {"extraction": False, "transcription": False, "planning": False},
        "wait_expiry_seconds": 300, "internal_case_creation": False, "automatic_reminders": False})
    code = canonical_bytes({"files": {name: sha256((ROOT / name).read_bytes()).hexdigest() for name in (
        "src/proofkey/assessment/driver_contracts.py", "src/proofkey/assessment/drivers.py",
        "tests/test_runtime_driver_contracts.py", "tests/test_runtime_drivers.py")}})
    values = dict(driver_id="public-pilot", obligation=obligation, variant=variant, case_id="C1", independence_group=group,
        profile_name="flat-v1.2", input_sequence_bytes=inputs, scenario_bytes=scenario,
        candidate_manifest_bytes=candidate, profile_bytes=profile, process_bytes=process, policy_bytes=policy,
        driver_code_bytes=code, dependency_evidence=(("public-runtime", b'{"status":"available"}'),),
        callback=callback, source_snapshot=None if fixture_only else snapshot, max_seconds=60.0)
    reg = RegisteredDriver(**{**values, **changes})
    manifest = DriverManifest(version="runtime-driver-v1", driver_id=reg.driver_id, obligation=reg.obligation,
        variant=reg.variant, case_id=reg.case_id, independence_group=reg.independence_group,
        case_bytes_hash=digest_bytes(inputs), scenario_hash=digest_bytes(scenario), driver_code_hash=digest_bytes(code),
        candidate_manifest_hash=digest_bytes(candidate), profile_name="flat-v1.2", profile_hash=digest_bytes(profile),
        process_hash=digest_bytes(process), policy_hash=digest_bytes(policy), expectation_version="pilot-v1",
        expectation_hash=digest_bytes(expect), execution_kind="public_sequence", dependency_ids=("public-runtime",))
    return reg, manifest, expect


class PublicDriverTests(unittest.TestCase):
    def test_actual_window_capture_includes_transport_intent_counter_and_source(self):
        reg, manifest, expect = registration()
        receipt = run_driver(DriverRegistry((reg,)), manifest, reg.input_sequence_bytes, ordinal=3, repetition=2)
        self.assertEqual(receipt.status, "completed")
        self.assertEqual((receipt.ordinal, receipt.repetition), (3, 2))
        self.assertEqual(assess_driver(receipt, expect).status, "passed")
        events = receipt.events()
        journal = next(event for event in events if event["event_tag"] == "journal")
        self.assertEqual(journal["checkpoint"]["phase"], "complete")
        self.assertEqual(journal["intents"][0]["intent"]["arguments"], {"slot": "S1"})
        self.assertEqual(journal["intents"][0]["state"], "verified")
        self.assertEqual(receipt.source_pre_manifest_bytes, receipt.source_post_manifest_bytes)
        self.assertEqual(strict_loads(receipt.source_pre_manifest_bytes)["kind"], "filesystem")
        self.assertTrue(any(event["event_tag"] == "port" and event["operation"] == "reschedule" for event in events))

    def test_goods_positive_and_declared_inventory_mismatch_are_distinct(self):
        inputs = request_bytes("goods_refusal", "unknown", {"inventory": {"item-1": 1}})
        cases = [("positive", [["delivery.status", "delivered"]], 1, "passed"),
                 ("inventory-mismatch", [["delivery.status", "delivered"],
                                         ["goods.inventory", {"item-1": 1, "item-2": 1}]], 0, "failed")]
        positive_expect = expectation(equals("refusal-once", "physical", ["counts", "register_goods_refusal"], 1),
                                     equals("return-once", "physical", ["counts", "create_return"], 1))
        for variant, mutations, wanted, grade in cases:
            with self.subTest(variant=variant):
                scenario = canonical_bytes({"mutations": mutations, "faults": [], "replay": False})
                reg, manifest, expect = registration(inputs=inputs, scenario=scenario, variant=variant,
                    expect=positive_expect, obligation="R05", group="pilot-whole-goods")
                receipt = run_driver(DriverRegistry((reg,)), manifest, inputs, ordinal=1, repetition=0)
                self.assertEqual(receipt.status, "completed")
                physical = next(event for event in receipt.events() if event["event_tag"] == "physical")
                self.assertEqual(physical["counts"]["register_goods_refusal"], wanted)
                self.assertEqual(physical["counts"]["create_return"], wanted)
                self.assertEqual(assess_driver(receipt, expect).status, grade)

    def test_revoked_consent_and_missing_window_capture_explicit_zero(self):
        cases = [("revoked", request_bytes(), [["customer.consent", "revoked"]]),
                 ("missing-window", request_bytes(mode="unknown", arguments={}), [])]
        expect = expectation(equals("zero-reschedule", "physical", ["counts", "reschedule"], 0))
        for ordinal, (variant, inputs, mutations) in enumerate(cases):
            with self.subTest(variant=variant):
                reg, manifest, _ = registration(inputs=inputs, variant=variant, expect=expect,
                    scenario=canonical_bytes({"mutations": mutations, "faults": [], "replay": False}))
                receipt = run_driver(DriverRegistry((reg,)), manifest, inputs, ordinal=ordinal, repetition=0)
                self.assertEqual(receipt.status, "completed")
                self.assertEqual(assess_driver(receipt, expect).status, "passed")
                self.assertFalse(any(event["event_tag"] == "port" and event["operation"] == "reschedule"
                                     for event in receipt.events()))

    def test_saved_original_replay_retains_bytes_counters_debt_and_generation(self):
        expect = expectation(equals("zero-model", "replay", ["planner_calls"], 0),
                             equals("zero-new-effect", "replay", ["effect_delta", "reschedule"], 0))
        reg, manifest, _ = registration(obligation="R15", variant="saved-original", expect=expect,
            scenario=canonical_bytes({"mutations": [], "faults": [], "replay": True,
                                     "replay_mutations": [["delivery.status", "completed"]]}))
        receipt = run_driver(DriverRegistry((reg,)), manifest, reg.input_sequence_bytes, ordinal=5, repetition=0)
        self.assertEqual(receipt.status, "completed")
        self.assertEqual(assess_driver(receipt, expect).status, "passed")
        replay = next(event for event in receipt.events() if event["event_tag"] == "replay")
        saved = replay["saved_before"]
        journal = next(event for event in receipt.events() if event["event_tag"] == "journal")
        self.assertEqual(replay["intents"], journal["intents"])
        self.assertEqual(replay["source_instructions"], [["delivery.status", "completed"]])
        self.assertNotEqual(replay["source_revisions"]["revisions"]["delivery.status"],
                            journal["source_revisions"]["revisions"]["delivery.status"])
        self.assertEqual(canonical_bytes({**replay["output"], "historical": False}), canonical_bytes(saved))
        self.assertEqual(replay["saved_after"], saved)
        self.assertEqual(replay["original"], CanonicalRequest.model_validate(
            strict_loads(reg.input_sequence_bytes)["request"]).model_dump(mode="json"))
        self.assertEqual(replay["calls"], [{"operation": "read_case", "purpose": "disclosure"}])
        self.assertTrue(all(value == 0 for value in replay["effect_delta"].values()))
        before, after = replay["checkpoint_before"], replay["checkpoint_after"]
        for field in ("binding", "phase", "next_gate", "stop", "deadline", "processing_status"):
            self.assertEqual(after[field], before[field])
        self.assertEqual(after["budget"]["tool_calls"], before["budget"]["tool_calls"] + 1)
        for field in ("planner_calls", "max_tool_calls", "max_planner_calls", "reconciliation_reads"):
            self.assertEqual(after["budget"][field], before["budget"][field])
        self.assertEqual(len(replay["bindings"]), 1)

    def test_changed_expectation_cannot_change_runtime_view_or_public_port_inputs(self):
        reg, manifest, expect = registration()
        changed = expectation(equals("sentinel", "physical", ["counts", "reschedule"], "SECRET-EXPECTED-VALUE"))
        other = replace(manifest, expectation_hash=digest_bytes(changed))
        first = run_driver(DriverRegistry((reg,)), manifest, reg.input_sequence_bytes, ordinal=0, repetition=0)
        second = run_driver(DriverRegistry((reg,)), other, reg.input_sequence_bytes, ordinal=0, repetition=1)
        self.assertEqual(first.raw_event_bytes, second.raw_event_bytes)
        self.assertEqual(first.raw_output_bytes, second.raw_output_bytes)
        self.assertEqual(assess_driver(first, expect).status, "passed")
        self.assertEqual(assess_driver(second, changed).status, "failed")
        self.assertNotIn(b"SECRET-EXPECTED-VALUE", b"".join(second.raw_event_bytes))


class RegisteredExecutionTests(unittest.TestCase):
    def test_callback_view_is_frozen_reference_free_and_sink_retains_order(self):
        seen = []
        def callback(view, sink):
            seen.append(asdict(view))
            sink.emit(b'{"event_tag":"counter","physical":0}')
            sink.emit(b'{"event_tag":"done","ok":true}')
            return DriverCapture(sink.events, b'{"ok":true}')
        reg, manifest, _ = registration(callback, fixture_only=True)
        result = run_driver(DriverRegistry((reg,)), manifest, reg.input_sequence_bytes, ordinal=255, repetition=15)
        self.assertEqual(result.status, "completed")
        self.assertEqual(tuple(event["event_tag"] for event in result.events()), ("counter", "done"))
        self.assertEqual(set(seen[0]), {"input_sequence_bytes", "scenario_bytes", "case_id", "obligation", "variant",
            "candidate_manifest_hash", "profile_name", "profile_hash", "process_hash", "policy_hash"})
        self.assertEqual(strict_loads(result.source_pre_manifest_bytes)["kind"], "fixture-only")
        detached = result.events()[0]
        detached["physical"] = 999
        self.assertEqual(result.events()[0]["physical"], 0)

    def test_unknown_mismatch_dependencies_and_unsupported_kind_enter_nothing(self):
        entered = []
        def callback(view, sink):
            entered.append("callback")
            return DriverCapture((), b'{}')
        def source():
            entered.append("source")
            return snapshot()
        reg, manifest, _ = registration(callback, source_snapshot=source)
        variants = [replace(manifest, driver_id="missing"), replace(manifest, scenario_hash="a" * 64),
            replace(manifest, dependency_ids=("missing",)), replace(manifest, execution_kind="subprocess_barrier"),
            replace(manifest, execution_kind="controlled_order")]
        results = [run_driver(DriverRegistry((reg,)), value, reg.input_sequence_bytes, ordinal=i, repetition=0)
                   for i, value in enumerate(variants)]
        self.assertEqual([r.status for r in results], ["not_started"] * 5)
        self.assertEqual([r.ordinal for r in results], list(range(5)))
        self.assertTrue(all(r.dependency_limits for r in results))
        self.assertEqual(entered, [])
        result = run_driver(DriverRegistry((reg,)), manifest, b'{}', ordinal=10, repetition=0)
        self.assertEqual(result.status, "not_started")
        self.assertEqual(entered, [])

    def test_callback_error_absence_invalid_output_are_separate_positions(self):
        def failure(view, sink):
            sink.emit(b'{"entered":true,"event_tag":"before-error"}')
            raise RuntimeError("actual callback error")
        def no_output(view, sink):
            return None
        def invalid(view, sink):
            return DriverCapture((), b'not-json')
        for i, (callback, wanted) in enumerate([(failure, "failed"), (no_output, "no_output"), (invalid, "invalid_output")]):
            with self.subTest(wanted=wanted):
                reg, manifest, expect = registration(callback, fixture_only=True)
                receipt = run_driver(DriverRegistry((reg,)), manifest, reg.input_sequence_bytes, ordinal=i, repetition=1)
                self.assertEqual((receipt.status, receipt.ordinal, receipt.repetition), (wanted, i, 1))
                self.assertEqual(assess_driver(receipt, expect).status, "ungraded")
                if wanted == "failed":
                    self.assertIn(b"actual callback error", receipt.error_bytes)
                    self.assertEqual(len(receipt.raw_event_bytes), 1)
                if wanted == "invalid_output":
                    self.assertEqual(receipt.raw_output_bytes, b"not-json")
                    self.assertEqual(receipt.raw_output_hash, sha256(b"not-json").hexdigest())

    def test_actual_snapshot_drift_fails_without_presumed_clean_hash(self):
        snapshots, entered = [], []
        original = snapshot()
        changed = strict_loads(original)
        changed["files"]["src/proofkey/engine.py"] = "a" * 64
        # Trusted observed-snapshot control, separately from real PRE/POST source tests.
        for order, count in [((canonical_bytes(changed),), 0), ((original, canonical_bytes(changed)), 1)]:
            snapshots[:] = order
            def source():
                return snapshots.pop(0)
            def callback(view, sink):
                entered.append(1)
                return DriverCapture((), b'{}')
            reg, manifest, expect = registration(callback, source_snapshot=source)
            before = len(entered)
            receipt = run_driver(DriverRegistry((reg,)), manifest, reg.input_sequence_bytes, ordinal=0, repetition=0)
            self.assertEqual(receipt.status, "failed")
            self.assertEqual(len(entered) - before, count)
            self.assertEqual(assess_driver(receipt, expect).status, "ungraded")

    def test_event_overflow_and_forged_capture_are_invalid_not_complete(self):
        def overflow(view, sink):
            for _ in range(65):
                sink.emit(b'{"event_tag":"counter","physical":0}')
            return DriverCapture(sink.events, b'{}')
        def forged(view, sink):
            return DriverCapture((b'{"event_tag":"counter","physical":0}',), b'{}')
        for callback in (overflow, forged):
            reg, manifest, _ = registration(callback, fixture_only=True)
            result = run_driver(DriverRegistry((reg,)), manifest, reg.input_sequence_bytes, ordinal=0, repetition=0)
            self.assertEqual(result.status, "invalid_output")
            self.assertLessEqual(len(result.raw_event_bytes), 64)

    def test_caught_sink_overflow_cannot_relabel_truncated_capture_complete(self):
        def callback(view, sink):
            for _ in range(65):
                try:
                    sink.emit(b'{"event_tag":"counter","physical":0}')
                except ValueError:
                    pass
            return DriverCapture(sink.events, b'{}')
        reg, manifest, _ = registration(callback, fixture_only=True)
        receipt = run_driver(DriverRegistry((reg,)), manifest, reg.input_sequence_bytes, ordinal=0, repetition=0)
        self.assertEqual(receipt.status, "invalid_output")
        self.assertEqual(len(receipt.raw_event_bytes), 64)

    def test_caught_invalid_event_cannot_become_missing_trace_success(self):
        def callback(view, sink):
            try:
                sink.emit(b'{"physical":0}')
            except ValueError:
                pass
            return DriverCapture(sink.events, b'{}')
        reg, manifest, _ = registration(callback, fixture_only=True)
        receipt = run_driver(DriverRegistry((reg,)), manifest, reg.input_sequence_bytes, ordinal=0, repetition=0)
        self.assertEqual(receipt.status, "invalid_output")
        self.assertEqual(receipt.raw_event_bytes, ())

    def test_registry_rejects_mutable_duplicate_or_unbound_registration(self):
        reg, manifest, _ = registration(fixture_only=True)
        for value in ([reg], (reg, reg)):
            with self.assertRaises(ValueError):
                DriverRegistry(value)
        for changes in (dict(input_sequence_bytes=bytearray(b'{}')), dict(max_seconds=float("inf")),
                        dict(max_seconds=61), dict(max_seconds=10**1000), dict(callback=None),
                        dict(dependency_evidence=(("public-runtime", b'{"status":[]}'),)),
                        dict(dependency_evidence=(("public-runtime", b'{"status":"available"}'),) * 2)):
            with self.subTest(changes=tuple(changes)), self.assertRaises(ValueError):
                replace(reg, **changes)

    def test_malformed_source_snapshots_fail_as_evidence_without_callback_entry(self):
        entered = []
        for invalid in (b'{"files":{},"kind":[],"version":"candidate-source-v1"}',
                        b'{"files":{},"kind":"filesystem","version":"candidate-source-v1"}',
                        bytearray(b'{}'), None):
            with self.subTest(invalid=invalid):
                reg, manifest, _ = registration(lambda *_: entered.append(1), source_snapshot=lambda: invalid)
                receipt = run_driver(DriverRegistry((reg,)), manifest, reg.input_sequence_bytes, ordinal=0, repetition=0)
                self.assertEqual(receipt.status, "failed")
                self.assertIsNone(receipt.source_pre_manifest_bytes)
        self.assertEqual(entered, [])

    def test_filesystem_drift_captures_real_changed_bytes_from_task_owned_source(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "candidate-input.json"
            path.write_bytes(b'{"input":1}')
            def source():
                return canonical_bytes({"version": "candidate-source-v1", "kind": "filesystem",
                    "files": {"candidate-input.json": sha256(path.read_bytes()).hexdigest()}})
            def callback(view, sink):
                path.write_bytes(b'{"input":2}')
                return DriverCapture((), b'{}')
            original = source()
            reg, manifest, _ = registration(callback, candidate_manifest_bytes=original, source_snapshot=source)
            manifest = replace(manifest, candidate_manifest_hash=digest_bytes(original))
            receipt = run_driver(DriverRegistry((reg,)), manifest, reg.input_sequence_bytes, ordinal=0, repetition=0)
            self.assertEqual(receipt.status, "failed")
            self.assertEqual(receipt.source_pre_manifest_bytes, original)
            self.assertEqual(receipt.source_post_manifest_bytes, source())
            self.assertNotEqual(receipt.source_pre_manifest_bytes, receipt.source_post_manifest_bytes)

    def test_interrupt_is_not_swallowed_and_post_source_snapshot_is_attempted(self):
        entries = []
        original = snapshot()
        def source():
            entries.append("source")
            return original
        def callback(view, sink):
            raise KeyboardInterrupt("host interrupted")
        reg, manifest, _ = registration(callback, source_snapshot=source)
        with self.assertRaises(KeyboardInterrupt):
            run_driver(DriverRegistry((reg,)), manifest, reg.input_sequence_bytes, ordinal=0, repetition=0)
        self.assertEqual(entries, ["source", "source"])

    def test_cooperative_cutoff_fails_before_entering_callback(self):
        entered = []
        reg, manifest, _ = registration(lambda *_: entered.append(1), fixture_only=True, max_seconds=1e-12)
        receipt = run_driver(DriverRegistry((reg,)), manifest, reg.input_sequence_bytes, ordinal=0, repetition=0)
        self.assertEqual(receipt.status, "failed")
        self.assertEqual(entered, [])
        self.assertIn(b"limit", receipt.error_bytes)

    def test_source_error_and_unavailable_dependency_preserve_position_without_entry(self):
        entered = []
        def source():
            raise OSError("source unavailable")
        reg, manifest, _ = registration(lambda *_: entered.append(1), source_snapshot=source)
        result = run_driver(DriverRegistry((reg,)), manifest, reg.input_sequence_bytes, ordinal=8, repetition=4)
        self.assertEqual(result.status, "failed")
        self.assertIsNone(result.source_pre_manifest_bytes)
        self.assertIn(b"source unavailable", result.error_bytes)
        unavailable = replace(reg, dependency_evidence=(("public-runtime", b'{"status":"unavailable"}'),))
        result = run_driver(DriverRegistry((unavailable,)), manifest, reg.input_sequence_bytes, ordinal=8, repetition=4)
        self.assertEqual((result.status, result.ordinal, result.repetition), ("not_started", 8, 4))
        self.assertEqual(entered, [])

    def test_unvalidated_manifest_container_is_rejected_before_host_entry(self):
        reg, manifest, _ = registration(fixture_only=True)
        object.__setattr__(manifest, "dependency_ids", ["public-runtime"])
        with self.assertRaises(ValueError):
            run_driver(DriverRegistry((reg,)), manifest, reg.input_sequence_bytes, ordinal=0, repetition=0)

    def test_all_bounded_ordinals_and_repetitions_are_preserved_for_missing_driver(self):
        reg, manifest, _ = registration(fixture_only=True)
        missing = replace(manifest, driver_id="unregistered")
        positions = [run_driver(DriverRegistry(()), missing, reg.input_sequence_bytes,
            ordinal=ordinal, repetition=ordinal % 16) for ordinal in range(256)]
        self.assertEqual([(r.ordinal, r.repetition) for r in positions], [(i, i % 16) for i in range(256)])
        self.assertTrue(all(result.status == "not_started" for result in positions))


def control_receipt(events, expect):
    reg, manifest, _ = registration(lambda *_: None, fixture_only=True, expect=expect)
    raw = manifest.to_bytes()
    return RunnerReceipt(raw, digest_bytes(raw), 7, 2, "completed", raw_event_bytes=tuple(canonical_bytes(event) for event in events),
        raw_output_bytes=b'{}', raw_output_hash=digest_bytes(b'{}'), elapsed_seconds=0.0,
        source_pre_manifest_bytes=reg.candidate_manifest_bytes, source_post_manifest_bytes=reg.candidate_manifest_bytes)


class DeclarativeGraderTests(unittest.TestCase):
    def test_good_bad_missing_and_ambiguous_controls_separate(self):
        expect = expectation(equals("physical-zero", "counter", ["value"], 0))
        cases = [([{"event_tag": "counter", "value": 0}], "passed"),
                 ([{"event_tag": "counter", "value": 1}], "failed"), ([], "insufficient"),
                 ([{"event_tag": "counter"}], "insufficient"),
                 ([{"event_tag": "counter", "value": 0}] * 2, "insufficient")]
        for events, wanted in cases:
            with self.subTest(wanted=wanted):
                result = assess_driver(control_receipt(events, expect), expect)
                self.assertEqual(result.status, wanted)
                self.assertEqual(result.outcomes[0].status, wanted)
                self.assertEqual((result.ordinal, result.repetition), (7, 2))

    def test_positive_effect_expectation_rejects_handcrafted_deny_all_control(self):
        expect = expectation(equals("one-effect", "counter", ["physical"], 1))
        for physical, wanted in ((1, "passed"), (0, "failed")):
            # Fixture-only grader controls, not a disabled runtime candidate.
            receipt = control_receipt([{"event_tag": "counter", "physical": physical}], expect)
            self.assertEqual(assess_driver(receipt, expect).status, wanted)

    def test_missing_logs_cannot_prove_count_zero(self):
        expect = expectation({"id": "count", "event_tag": "effect", "field_path": [],
                              "operation": "count_equals", "expected": 0})
        receipt = control_receipt([], expect)
        self.assertEqual(assess_driver(receipt, expect).status, "insufficient")
        nonzero = control_receipt([{"event_tag": "effect"}], expect)
        self.assertEqual(assess_driver(nonzero, expect).status, "failed")

    def test_repeated_and_swapped_predicates_preserve_ids_and_raw_references(self):
        good = equals("good", "counter", ["value"], 0)
        bad = equals("bad", "counter", ["value"], 1)
        for predicates in ((good, bad), (bad, good)):
            expect = expectation(*predicates)
            receipt = control_receipt([{"event_tag": "counter", "value": 0}], expect)
            for _ in range(3):
                result = assess_driver(receipt, expect)
                self.assertEqual({outcome.predicate_id: outcome.status for outcome in result.outcomes},
                                 {"good": "passed", "bad": "failed"})
                self.assertTrue(all(outcome.event_ordinals == (0,) and outcome.raw_event_bytes == receipt.raw_event_bytes
                                    for outcome in result.outcomes))

    def test_invalid_reference_schema_hash_and_path_stay_ungraded(self):
        good = equals("counter", "counter", ["value"], 0)
        valid = expectation(good)
        receipt = control_receipt([{"event_tag": "counter", "value": 0}], valid)
        wrong_hash = expectation({**good, "expected": 1})
        self.assertEqual(assess_driver(receipt, wrong_hash).status, "ungraded")
        for predicates in [(good, good), ({**good, "operation": "python"},),
                           ({**good, "field_path": [True]},), ({**good, "field_path": ["value"] * 17},),
                           ({**good, "operation": "count_equals", "expected": False},),
                           ({**good, "operation": "count_equals", "field_path": ["value"]},),
                           ({**good, "unexpected": "extra"},)]:
            expect = expectation(*predicates)
            result = assess_driver(control_receipt([], expect), expect)
            self.assertEqual(result.status, "ungraded")

    def test_json_equality_keeps_bool_integer_and_list_path_types_distinct(self):
        expect = expectation(equals("typed", "counter", ["value", 0], 0))
        receipt = control_receipt([{"event_tag": "counter", "value": [False]}], expect)
        self.assertEqual(assess_driver(receipt, expect).status, "failed")



if __name__ == "__main__":
    unittest.main()
