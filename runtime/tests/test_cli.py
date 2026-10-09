"""Closed CLI launch boundaries and actual owner lifetime."""
from contextlib import redirect_stdout
from dataclasses import FrozenInstanceError
from datetime import timedelta
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from proofkey.cli import main
from proofkey.bootstrap import CliConfiguration, CliReceiptV1
from proofkey.clock import SyntheticReplayClock
from proofkey.contracts import AuthContext, CaseResult
from proofkey.host import AuthResolver, ProfileRegistry, RuntimeFactory
from proofkey.host_contracts import HostLimitsV1, InterfaceLimitsV1


def request(kind="reschedule_window"):
    return dict(case_id="C1", object_id="O1", principal_id="U1", request_id="REQ1",
        request_revision="v1", consent_revision="v1", kind=kind,
        consent_mode="window" if kind == "reschedule_window" else "unknown",
        arguments={"window_start": "2026-10-08T10:00:00+00:00", "window_end": "2026-10-08T12:00:00+00:00",
                   "inventory": {"item-1": 1}} if kind == "reschedule_window" else {"inventory": {"item-1": 1}},
        evidence_ids=[], narrative=None)


class ObservedFactory(RuntimeFactory):
    def __init__(self):
        self.resources = []
        self.contexts = []
        self.snapshots = []
        self.release = threading.Event()
        self.block_close = False

    def create(self, release, clock):
        resource = super().create(release, clock)
        self.resources.append(resource)
        actual = resource.engine
        observer = self
        class Engine:
            def __getattr__(self, name):
                method = getattr(actual, name)
                def invoke(*args, **kwargs):
                    observer.contexts.append(kwargs["execution"])
                    result = method(*args, **kwargs)
                    if resource.store.has_case("C1"):
                        observer.snapshots.append((resource.store.checkpoint("C1"), resource.store.intents("C1"),
                            resource.world.calls, resource.store.original_request("C1", "G1")))
                    return result
                return invoke
        resource.engine = Engine()
        close = resource.close
        def closing():
            if observer.block_close:
                observer.release.wait(2)
            close()
        resource.close = closing
        return resource


class CliTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.base = Path(folder.name).resolve()
        self.factory = ObservedFactory()
        self.clock = SyntheticReplayClock()
        self.options = dict(factory=self.factory,
            auth_resolver=AuthResolver({"synthetic-user": AuthContext(caller_id="U1", proof_reference="synthetic-proof"),
                "wrong": AuthContext(caller_id="U1", proof_reference="wrong-proof")}),
            profile_registry=ProfileRegistry.builtin(self.base / "resources"), clock=self.clock,
            host_limits=HostLimitsV1(), interface_limits=InterfaceLimitsV1(),
            output_parent=self.base, inventory_parent=self.base, total_seconds=20.0,
            publication_reserve_seconds=2.0, shutdown_seconds=1.0)

    def invoke(self, args, configuration=None):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = main(args, configuration=configuration or CliConfiguration(**self.options))
        wire = stdout.getvalue()
        self.assertTrue(wire.strip(), "CLI must emit its factual receipt even for usage failure")
        receipt = CliReceiptV1.model_validate_json(wire)
        self.assertEqual(len(wire.splitlines()), 1)
        return code, receipt

    def body(self, value):
        path = self.base / "input.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return str(path)

    def test_unknown_inline_authority_flags_are_closed_usage_without_bootstrap(self):
        for args in ([], ["run"], ["run", "--input", "SECRET", "--proof", "SECRET"],
                     ["run", "--input", "SECRET", "--deadline", "SECRET"], ["--help"],
                     ["run", "--input", "SECRET", "extra"]):
            code, receipt = self.invoke(args)
            self.assertEqual(code, 64)
            self.assertEqual(receipt.failure, "invalid_usage")
            self.assertIsNone(receipt.run)
            self.assertIsNone(receipt.shutdown)
            self.assertNotIn("SECRET", receipt.model_dump_json())
        self.assertEqual(self.factory.resources, [])
        self.assertEqual(list(self.base.iterdir()), [])

    def test_configuration_bounds_are_exact_finite_frozen_and_detached(self):
        valid = CliConfiguration(**self.options)
        with self.assertRaises(FrozenInstanceError):
            valid.total_seconds = 1.0
        for changes in ({"total_seconds": float("nan")}, {"total_seconds": True},
                        {"publication_reserve_seconds": 20.0}, {"publication_reserve_seconds": 0.0000001},
                        {"shutdown_seconds": float("inf")}, {"shutdown_seconds": 31.0},
                        {"total_seconds": 200.0}, {"output_parent": self.base / "absent"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                CliConfiguration(**{**self.options, **changes})
        self.assertIsNot(valid.host_limits, self.options["host_limits"])
        self.assertIsNot(valid.interface_limits, self.options["interface_limits"])

    def test_run_body_rejects_launch_metadata_duplicate_nonfinite_and_invalid_utf8_before_owner(self):
        for data in (b'{"proof":"SECRET"}', b'{"case_id":"C1","case_id":"C2"}',
                     b'{"a":NaN}', b'"\xff"', json.dumps({**request(), "release_id": "foreign"}).encode()):
            path = self.base / "bad.json"
            path.write_bytes(data)
            code, receipt = self.invoke(["run", "--input", str(path)])
            self.assertEqual((code, receipt.failure), (2, "invalid_input"))
            self.assertIsNone(receipt.shutdown)
        self.assertEqual(self.factory.resources, [])
        self.assertEqual(sorted(p.name for p in self.base.iterdir()), ["bad.json"])

    def test_stdin_reads_limit_plus_one_and_oversized_input_never_enters_owner(self):
        class Bounded(io.BytesIO):
            def read(self, size=-1):
                self.observed = size
                return super().read(size)
        stream = Bounded(b"x" * 65)
        options = CliConfiguration(**{**self.options, "interface_limits": InterfaceLimitsV1(max_input_bytes=64)})
        with patch("sys.stdin", type("Stdin", (), {"buffer": stream})()):
            code, receipt = self.invoke(["batch", "--input", "-"], options)
        self.assertEqual(stream.observed, 65)
        self.assertEqual((code, receipt.failure), (2, "invalid_input"))
        self.assertIsNone(receipt.shutdown)
        self.assertEqual(list(self.base.iterdir()), [])

    def test_symlink_parent_and_default_private_nodes_fail_without_source_or_alias_writes(self):
        alias = self.base / "alias"
        alias.symlink_to(self.base, target_is_directory=True)
        with self.assertRaises(ValueError):
            CliConfiguration(**{**self.options, "output_parent": alias})
        launch = self.base / "launch"
        launch.mkdir(mode=0o700)
        (launch / ".proofkey").symlink_to(self.base, target_is_directory=True)
        with patch("pathlib.Path.cwd", return_value=launch), redirect_stdout(io.StringIO()) as out:
            code = main(["inspect-profile"])
        self.assertEqual(code, 4)
        self.assertEqual(json.loads(out.getvalue())["failure"], "bootstrap_unavailable")
        self.assertFalse((self.base / "runs").exists())

    def test_one_original_context_precedes_input_and_cold_setup(self):
        path = self.body(request())
        before = self.clock.monotonic()
        actual_open = Path.open
        def delayed_open(target, *args, **kwargs):
            if target == Path(path):
                self.clock.wait(0.03)
            return actual_open(target, *args, **kwargs)
        with patch.object(Path, "open", delayed_open):
            code, receipt = self.invoke(["run", "--input", path])
        self.assertEqual(code, 0)
        execution = self.factory.contexts[0]
        self.assertLess(execution.captured_monotonic, before + 0.02)
        self.assertGreater(receipt.run.command.started_at.timestamp() - execution.captured_at.timestamp(), 0.03)
        self.assertEqual(receipt.run.window.execution.captured_monotonic, execution.captured_monotonic)
        self.assertTrue(self.factory.resources[0].closed)
        self.assertTrue(receipt.shutdown.owner_closed)

    def test_larger_trusted_global_window_is_preserved(self):
        configuration = CliConfiguration(**{**self.options, "total_seconds": 240.0,
            "host_limits": HostLimitsV1(max_execution_seconds=300.0)})
        code, receipt = self.invoke(["inspect-profile"], configuration)
        self.assertEqual(code, 0)
        window = receipt.run.window
        self.assertGreater((window.execution.deadline - window.execution.captured_at).total_seconds(), 237.0)
        self.assertEqual(window.reserve_seconds, 2.0)
        self.assertIsNone(receipt.run.export)

    def test_owner_pending_preserves_successful_run_and_finite_actual_shutdown(self):
        self.factory.block_close = True
        self.addCleanup(self.factory.release.set)
        configuration = CliConfiguration(**{**self.options, "shutdown_seconds": 0.01})
        code, receipt = self.invoke(["run", "--input", self.body(request())], configuration)
        self.assertEqual((code, receipt.failure), (4, "owner_pending"))
        self.assertEqual(receipt.run.command.result.status, "authorized")
        self.assertFalse(receipt.shutdown.owner_closed)
        self.assertLess(receipt.shutdown.elapsed_seconds, 0.3)
        self.factory.release.set()

    def test_proof_release_fingerprint_and_unavailable_are_factual_closed_denials(self):
        path = self.body(request())
        for extra in (["--credential-ref", "wrong"], ["--release", "host-goods-replay-v1"]):
            code, receipt = self.invoke(["run", "--input", path, *extra])
            self.assertEqual(code, 2)
            self.assertIsNotNone(receipt.run.command)
            self.assertIsNone(receipt.failure)
        code, receipt = self.invoke(["run", "--input", path, "--release", "unregistered"])
        self.assertEqual((code, receipt.failure), (2, "invalid_input"))
        self.assertIsNone(receipt.shutdown)
        code, receipt = self.invoke(["transfer"])
        self.assertEqual(code, 2)
        self.assertEqual(receipt.run.command.outcome, "unavailable")

    def test_batch_retains_all_n_and_collision_facts(self):
        values = [{}, {"case_id": 3}, 4, request(), request()]
        code, receipt = self.invoke(["batch", "--input", self.body(values)])
        self.assertEqual(code, 4)
        self.assertEqual(receipt.run.position_count, 5)
        self.assertEqual([p.execution_outcome for p in receipt.run.positions],
                         ["invalid_request", "invalid_request", "invalid_request", "result", "result"])
        self.assertEqual([p.export_outcome for p in receipt.run.positions],
                         ["not_attempted", "not_attempted", "not_attempted", "written", "failed"])
        self.assertEqual(receipt.run.positions[-1].export_failure, "output_conflict")
        self.assertTrue(receipt.shutdown.owner_closed)

    def test_pending_batch_cannot_hide_earlier_actual_export_failure_after_owner_closes(self):
        # Regression: an early pending exit must not suppress ordinal1's real
        # output collision. Only the third engine call is gated; host admission,
        # waits, publication, expiry and eventual owner closure remain actual.
        from proofkey.host import HostDispatcher
        from proofkey.batch_files import read_run_inventory
        released = threading.Event()
        entered = threading.Event()
        self.addCleanup(released.set)
        class GatedFactory(ObservedFactory):
            def create(self, release, clock):
                resource = super().create(release, clock)
                actual = resource.engine
                class Engine:
                    calls = 0
                    def run(self, *args, **kwargs):
                        self.calls += 1
                        if self.calls == 3:
                            entered.set()
                            if not released.wait(5):
                                raise RuntimeError("test_gate_timeout")
                        return actual.run(*args, **kwargs)
                resource.engine = Engine()
                original_close = resource.close
                def capture_effects_then_close():
                    self.physical_reschedules = resource.world.effect_count("reschedule")
                    original_close()
                resource.close = capture_effects_then_close
                return resource
        factory = GatedFactory()
        configuration = CliConfiguration(**{**self.options, "factory": factory,
            "total_seconds": 4.0, "publication_reserve_seconds": 2.0})
        original_close = HostDispatcher.close
        def eventual_close(dispatcher, cutoff):
            released.set()
            return original_close(dispatcher, cutoff)
        with patch.object(HostDispatcher, "close", eventual_close):
            code, receipt = self.invoke(["batch", "--input", self.body([request()] * 4)], configuration)
        batch = receipt.run
        self.assertTrue(entered.is_set())
        self.assertEqual(batch.publication_status, "committed")
        self.assertEqual(batch.outcome, "abandoned_pending")
        self.assertEqual(batch.position_count, 4)
        self.assertEqual([p.inventory.ordinal for p in batch.positions], [0, 1, 2, 3])
        self.assertEqual([p.execution_outcome for p in batch.positions],
                         ["result", "result", "deadline_exceeded", "not_started"])
        self.assertEqual([p.export_outcome for p in batch.positions],
                         ["written", "failed", "not_attempted", "not_attempted"])
        self.assertEqual(batch.positions[1].export_failure, "output_conflict")
        self.assertTrue(batch.positions[1].command.result.historical)
        pending = batch.positions[2].command
        self.assertEqual((pending.outcome, pending.inventory_status), ("started_pending", "committed"))
        self.assertEqual(batch.pending_command_ids, (pending.command_id,))
        self.assertIsNone(pending.result)
        self.assertIsNone(pending.finished_at)
        self.assertEqual(batch.unresolved_admission_ordinals, ())
        self.assertTrue(receipt.shutdown.owner_closed)
        self.assertEqual(receipt.shutdown.pending_command_ids, ())
        self.assertFalse(receipt.shutdown.inventory_failure)
        self.assertIsNone(receipt.failure)
        self.assertTrue(factory.resources[0].closed)
        self.assertEqual(factory.physical_reschedules, 1)
        self.assertEqual(len(factory.snapshots[-1][1]), 1)
        self.assertEqual(factory.snapshots[-1][1][0].state, "verified")
        self.assertEqual(factory.snapshots[-1][3].model_dump(mode="json"), request())
        self.assertTrue(all(context is factory.contexts[0] for context in factory.contexts))
        self.assertEqual(pending.execution.captured_monotonic,
                         batch.window.execution.captured_monotonic)
        output = next(path.parent for path in self.base.glob("*/FINAL-MANIFEST.json"))
        inventory = read_run_inventory(output, limits=configuration.interface_limits)
        self.assertEqual(inventory.status, "committed_snapshot")
        self.assertEqual(inventory.final_manifest.positions, batch.positions)
        self.assertEqual(inventory.final_manifest.pending_command_ids, batch.pending_command_ids)
        print("CLI-FIX1-MIXED " + json.dumps({"exit": code,
            "actual_receipt": receipt.model_dump(mode="json"),
            "physical_intents": len(factory.snapshots[-1][1]),
            "physical_reschedules": factory.physical_reschedules,
            "source_calls": [(call.operation, call.purpose) for call in factory.snapshots[-1][2]],
            "original_context_count":
            len({id(context) for context in factory.contexts})}))
        self.assertEqual(code, 4)

    def test_receipt_rejects_unknown_fields_and_detaches_actual_nested_values(self):
        code, receipt = self.invoke(["inspect-profile"])
        self.assertEqual(code, 0)
        data = receipt.model_dump(mode="json")
        with self.assertRaises(ValueError):
            CliReceiptV1.model_validate_json(json.dumps({**data, "body": "SECRET"}))
        copy = CliReceiptV1.model_validate_json(json.dumps(data))
        data["shutdown"]["owner_closed"] = False
        self.assertTrue(copy.shutdown.owner_closed)

    def test_strict_exit_controls_include_command_inventory_in_deadline_and_not_started_ordinals(self):
        # Supplementary strict contract controls, not invented runtime evidence.
        # Literal expectations protect pending3 and inventory failure4 even when
        # a position's coarse execution classification is deadline/not_started.
        from proofkey.cli import _run_exit
        from proofkey.host_contracts import BatchRunReceiptV1, CommandReceiptV1
        code, receipt = self.invoke(["batch", "--input", self.body([{}])])
        self.assertEqual(code, 2)
        base = receipt.run.model_dump(mode="python")
        cases = (
            ("started_pending", "committed", "deadline_exceeded", True, 3),
            ("started_pending", "partial", "deadline_exceeded", True, 4),
            ("started_pending", "unavailable", "deadline_exceeded", True, 4),
            ("expired", "committed", "deadline_exceeded", False, 3),
            ("expired", "partial", "deadline_exceeded", False, 4),
            ("cancelled_before_start", "committed", "not_started", False, 2),
            ("cancelled_before_start", "partial", "not_started", False, 4),
            ("denied", "committed", "denied", False, 2),
            ("infrastructure_error", "unavailable", "runtime_error", False, 4),
        )
        for outcome, inventory, execution, pending, expected in cases:
            with self.subTest(outcome=outcome, inventory=inventory):
                command = CommandReceiptV1(command_id="a" * 32, command_tag="run",
                    release_id=base["release_id"], mode=base["mode"], clock_mode=base["clock_mode"],
                    execution=receipt.run.window.execution, outcome=outcome,
                    started_at=receipt.run.started_at if outcome == "started_pending" else None,
                    inventory_status=inventory)
                position = {**base["positions"][0], "command": command.model_dump(mode="python"),
                    "admission_status": "joined", "execution_outcome": execution, "failure": None,
                    "publication_status": "committed"}
                run = BatchRunReceiptV1.model_validate({**base, "positions": (position,),
                    "pending_command_ids": (command.command_id,) if pending else (),
                    "outcome": "abandoned_pending" if pending else "deadline_exceeded" if outcome == "expired"
                        else "runtime_error" if outcome == "infrastructure_error" else "completed"})
                self.assertEqual(_run_exit(run), expected)

    def test_original_publication_window_expiring_during_load_is_unavailable_without_owner(self):
        class JumpClock(SyntheticReplayClock):
            offset = 0.0
            def monotonic(self):
                return super().monotonic() + self.offset
        clock = JumpClock()
        configuration = CliConfiguration(**{**self.options, "clock": clock})
        path = self.body(request())
        original = Path.open
        def expired(target, *args, **kwargs):
            if target == Path(path):
                clock.offset = 25.0
            return original(target, *args, **kwargs)
        with patch.object(Path, "open", expired):
            code, receipt = self.invoke(["run", "--input", path], configuration)
        self.assertEqual((code, receipt.failure), (4, "bootstrap_unavailable"))
        self.assertIsNone(receipt.run)
        self.assertIsNone(receipt.shutdown)
        self.assertEqual(self.factory.resources, [])
        self.assertEqual(sorted(p.name for p in self.base.iterdir()), ["input.json"])

    def test_ancestry_replaced_during_input_never_allocates_under_new_directory(self):
        parent = self.base / "output"
        parent.mkdir(mode=0o700)
        configuration = CliConfiguration(**{**self.options, "output_parent": parent})
        path = self.body(request())
        actual = Path.open
        def changed(target, *args, **kwargs):
            if target == Path(path):
                parent.rename(self.base / "original-output")
                parent.mkdir(mode=0o700)
            return actual(target, *args, **kwargs)
        with patch.object(Path, "open", changed):
            code, receipt = self.invoke(["run", "--input", path], configuration)
        self.assertEqual((code, receipt.failure), (4, "bootstrap_unavailable"))
        self.assertIsNone(receipt.shutdown)
        self.assertEqual(list(parent.iterdir()), [])
        self.assertEqual(self.factory.resources, [])

    def test_default_private_permissions_changed_during_load_are_rejected(self):
        launch = self.base / "launch"
        launch.mkdir(mode=0o700)
        path = self.body(request())
        actual = Path.open
        def changed(target, *args, **kwargs):
            if target == Path(path):
                (launch / ".proofkey/runs").chmod(0o777)
            return actual(target, *args, **kwargs)
        with patch("pathlib.Path.cwd", return_value=launch), patch.object(Path, "open", changed), redirect_stdout(io.StringIO()) as out:
            code = main(["run", "--input", path])
        receipt = CliReceiptV1.model_validate_json(out.getvalue())
        self.assertEqual((code, receipt.failure), (4, "bootstrap_unavailable"))
        self.assertIsNone(receipt.shutdown)
        self.assertEqual(list((launch / ".proofkey/runs").iterdir()), [])

    def test_same_trusted_clock_recover_stop_and_absent_reply_remain_scoped(self):
        configuration = CliConfiguration(**self.options)
        code, first = self.invoke(["run", "--input", self.body(request())], configuration)
        self.assertEqual(code, 0)
        code, recovered = self.invoke(["recover", "--case-id", "C1"], configuration)
        self.assertEqual(code, 2)
        self.assertEqual((recovered.run.command.result.status, recovered.run.command.result.reason), ("denied", "unavailable"))
        code, replayed = self.invoke(["run", "--input", self.body(request())], configuration)
        self.assertEqual(code, 0)
        self.assertTrue(replayed.run.command.result.historical)
        self.assertEqual(first.run.command.result.binding, replayed.run.command.result.binding)
        self.assertEqual(first.run.command.result.effects, replayed.run.command.result.effects)
        code, stopped = self.invoke(["stop", "--case-id", "C1", "--generation", "G1"], configuration)
        self.assertEqual(code, 0)
        self.assertTrue(stopped.run.command.result.stop.requested)
        reply = dict(question_id="absent", binding=first.run.command.result.binding.model_dump(mode="json"),
            actor_id="U1", proof_reference="synthetic-proof", request_revision="v1", consent_revision="v1",
            owner_state_revision="v1", fields={}, received_at="2026-10-08T10:00:00+00:00", simulated=True)
        code, denied = self.invoke(["reply", "--input", self.body(reply)], configuration)
        self.assertEqual(code, 2)
        self.assertEqual(denied.run.command.result.status, "denied")
        print("CLI-CONTROL " + json.dumps({"completed_recovery_exit": 2, "historical_run_replay": True,
            "stop_exit": 0, "stopped": True, "absent_reply_exit": code,
            "physical_reschedule": len(self.factory.snapshots[-1][1]), "clock": "same_trusted_synthetic_clock"}))

    def test_actual_error_result_is_preserved_with_infrastructure_exit(self):
        class ErrorFactory(RuntimeFactory):
            def create(self, release, clock):
                resource = super().create(release, clock)
                class FailedEngine:
                    def run(self, request, auth, *, execution):
                        return CaseResult(status="error", correlation_id=request.case_id, reason="unavailable")
                resource.engine = FailedEngine()
                return resource
        configuration = CliConfiguration(**{**self.options, "factory": ErrorFactory()})
        code, receipt = self.invoke(["run", "--input", self.body(request())], configuration)
        self.assertEqual(code, 4)
        self.assertEqual(receipt.run.command.result.status, "error")
        self.assertTrue(receipt.shutdown.owner_closed)

    def test_changed_request_fingerprint_and_missing_credential_never_construct_runtime(self):
        changed = request()
        changed["arguments"]["inventory"] = {"item-1": 2}
        code, receipt = self.invoke(["run", "--input", self.body(changed)])
        self.assertEqual(code, 2)
        self.assertEqual((receipt.run.command.outcome, receipt.run.command.failure), ("denied", "scope_denied"))
        self.assertEqual(self.factory.resources, [])
        code, receipt = self.invoke(["inspect-profile", "--credential-ref", "missing"])
        self.assertEqual((code, receipt.failure), (2, "invalid_input"))
        self.assertIsNone(receipt.shutdown)

    def test_expired_operational_window_retains_all_n_with_deadline_exit(self):
        class JumpClock(SyntheticReplayClock):
            offset = 0.0
            def monotonic(self):
                return super().monotonic() + self.offset
        clock = JumpClock()
        configuration = CliConfiguration(**{**self.options, "clock": clock})
        path = self.body([request(), request()])
        original = Path.open
        def expired(target, *args, **kwargs):
            if target == Path(path):
                clock.offset = 19.0
            return original(target, *args, **kwargs)
        with patch.object(Path, "open", expired):
            code, receipt = self.invoke(["batch", "--input", path], configuration)
        self.assertEqual(code, 3)
        self.assertEqual(receipt.run.position_count, 2)
        self.assertEqual([p.execution_outcome for p in receipt.run.positions], ["deadline_exceeded"] * 2)
        self.assertEqual(receipt.run.publication_status, "committed")
        self.assertTrue(receipt.shutdown.owner_closed)
        self.assertEqual(self.factory.resources, [])

    def test_publication_expiry_during_proof_selection_is_not_mislabeled_invalid_input(self):
        class JumpClock(SyntheticReplayClock):
            offset = 0.0
            def monotonic(self):
                return super().monotonic() + self.offset
        clock = JumpClock()
        class SlowResolver(AuthResolver):
            def handle(self, reference):
                handle = super().handle(reference)
                clock.offset = 25.0
                return handle
        resolver = SlowResolver({"synthetic-user": AuthContext(caller_id="U1", proof_reference="synthetic-proof")})
        configuration = CliConfiguration(**{**self.options, "clock": clock, "auth_resolver": resolver})
        code, receipt = self.invoke(["inspect-profile"], configuration)
        self.assertEqual((code, receipt.failure), (4, "bootstrap_unavailable"))
        self.assertIsNone(receipt.shutdown)
        self.assertEqual(list(self.base.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
