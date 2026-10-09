"""Real executable/library positives with public post-exit custody checks."""
from contextlib import redirect_stdout
from datetime import timedelta
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import unittest

from proofkey.batch import run_command
from proofkey.batch_files import read_run_inventory
from proofkey.bootstrap import CliReceiptV1
from proofkey.clock import SyntheticReplayClock
from proofkey.contracts import AuthContext
from proofkey.execution import ExecutionContext
from proofkey.host import AuthResolver, HostDispatcher, ProfileRegistry
from proofkey.host_contracts import HostLimitsV1, InterfaceLimitsV1
from proofkey.host_files import read_inventory
from proofkey.adapters.world import SimulatedWorld
from proofkey.journal import CaseStore
from test_cli import ObservedFactory, request

ROOT = Path(__file__).resolve().parents[1]
OPERATIONS = {"reschedule_window": ("reschedule",), "goods_refusal": ("register_goods_refusal", "create_return")}


def semantics(result):
    return {"status": result.status, "binding": result.binding.model_dump(mode="json"),
        "fingerprint": result.fingerprint, "version": result.result_version,
        "wait": result.wait_status, "handoff": result.handoff_status,
        "effects": {op: {"status": value.status, "action_id": value.action_id,
            "object_id": value.object_id, "fingerprint": value.fingerprint,
            "postcondition": value.postcondition} for op, value in result.effects.items()}}


class CliParityTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.base = Path(folder.name).resolve()
        self.env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(ROOT / "src") + os.pathsep + str(ROOT / "tests")}

    def subprocess(self, parent, args):
        completed = subprocess.run([sys.executable, "-m", "proofkey.cli", *args],
            cwd=parent, env=self.env, capture_output=True, text=True, timeout=15)
        self.assertEqual(completed.stderr, "")
        self.assertEqual(len(completed.stdout.splitlines()), 1)
        receipt = CliReceiptV1.model_validate_json(completed.stdout)
        self.assertTrue(receipt.shutdown.owner_closed if receipt.shutdown else True)
        return completed.returncode, receipt

    def readback(self, parent, receipt, kind):
        release_id = "host-window-replay-v1" if kind == "reschedule_window" else "host-goods-replay-v1"
        launch = parent / ".proofkey"
        runs = sorted((launch / "runs").iterdir())
        run_root = next(root for root in runs if read_run_inventory(root, limits=InterfaceLimitsV1()).run_id == receipt.run.run_id)
        read = read_run_inventory(run_root, limits=InterfaceLimitsV1())
        self.assertEqual(read.status, "committed_snapshot")
        self.assertIn(receipt.run.command.command_id, read.joined_command_ids)
        host_root = next(root for root in (launch / "inventories").iterdir()
                         if any(row.command_id == receipt.run.command.command_id for row in read_inventory(root)))
        rows = read_inventory(host_root)
        self.assertEqual([row.phase for row in rows], ["queued", "started", "finished"])
        self.assertEqual(rows[0].execution, rows[-1].execution)
        clock = SyntheticReplayClock()
        release = ProfileRegistry.builtin(launch / "resources").resolve(release_id)
        world = SimulatedWorld(release.resource_root / "world.sqlite", release.fixture_path,
            profile=release.validate(), clock=clock)
        store = CaseStore(release.resource_root / "journal.sqlite")
        try:
            checkpoint = store.checkpoint("C1")
            originals = store.original_request("C1", "G1")
            intents = store.intents("C1")
            self.assertEqual(originals.model_dump(mode="json"), request(kind))
            self.assertEqual(checkpoint.binding, receipt.run.command.result.binding)
            self.assertEqual(checkpoint.budget.planner_calls, 0)
            self.assertGreater(checkpoint.budget.active_seconds, 0.0)
            self.assertLess(checkpoint.budget.active_seconds, 120.0)
            self.assertEqual(len(intents), len(OPERATIONS[kind]))
            self.assertEqual(checkpoint.budget.effects, len(OPERATIONS[kind]))
            for record in intents:
                self.assertEqual(record.state, "verified")
                self.assertEqual(record.verification, receipt.run.command.result.effects[record.intent.operation])
                self.assertEqual(world.effect_count(record.intent.operation), 1)
            hashes = {}
            for filename, digest in receipt.run.export.actual_file_hashes:
                actual = sha256((run_root / "ANSWERS/C1" / filename).read_bytes()).hexdigest()
                self.assertEqual(actual, digest)
                hashes[filename] = actual
            self.assertEqual(tuple(hashes), ("ANSWER.md", "REASONING.md"))
            self.assertEqual(world.calls, (), "Source-call memory is not falsely reconstructed after exit")
            return checkpoint, originals, intents, hashes
        finally:
            store.close()

    def library(self, parent, kind):
        parent.mkdir(mode=0o700)
        clock = SyntheticReplayClock()
        factory = ObservedFactory()
        resolver = AuthResolver({"synthetic-user": AuthContext(caller_id="U1", proof_reference="synthetic-proof")})
        release = "host-window-replay-v1" if kind == "reschedule_window" else "host-goods-replay-v1"
        execution = ExecutionContext.capture(clock.now() + timedelta(seconds=110), clock)
        dispatcher = HostDispatcher(factory, resolver, ProfileRegistry.builtin(parent / "resources"), clock,
            parent / "inventory", HostLimitsV1(), release_id=release)
        try:
            actual = run_command({"tag": "run", "release_id": release, "request": request(kind)}, dispatcher,
                resolver.handle("synthetic-user"), execution, publication_deadline=execution.deadline + timedelta(seconds=10),
                publication_reserve_seconds=10.0, output_root=parent / "run", limits=InterfaceLimitsV1(), clock=clock)
        finally:
            shutdown = dispatcher.close(clock.now() + timedelta(seconds=2))
        self.assertTrue(shutdown.owner_closed)
        self.assertEqual(actual.command.result.status, "authorized")
        self.assertEqual(actual.export_outcome, "written")
        return actual, factory.snapshots[-1]

    def test_real_module_window_and_goods_positive_match_library_and_public_persisted_facts(self):
        for kind in OPERATIONS:
            with self.subTest(kind=kind):
                parent = self.base / kind
                parent.mkdir(mode=0o700)
                source = parent / "input.json"
                source.write_text(json.dumps(request(kind)), encoding="utf-8")
                release = "host-window-replay-v1" if kind == "reschedule_window" else "host-goods-replay-v1"
                code, cli = self.subprocess(parent, ["run", "--input", str(source), "--release", release])
                self.assertEqual(code, 0)
                self.assertIsNone(cli.failure)
                cp, original, intents, hashes = self.readback(parent, cli, kind)
                library, (lcp, lintents, calls, loriginal) = self.library(self.base / (kind + "-library"), kind)
                self.assertEqual(semantics(cli.run.command.result), semantics(library.command.result))
                self.assertEqual((cp.phase, cp.next_gate, cp.processing_status), (lcp.phase, lcp.next_gate, lcp.processing_status))
                self.assertEqual(original, loriginal)
                self.assertEqual(cp.budget.tool_calls, lcp.budget.tool_calls)
                self.assertEqual(lcp.budget.tool_calls, len(calls))
                self.assertEqual([i.intent.action_id for i in intents], [i.intent.action_id for i in lintents])
                print("CLI-POSITIVE " + json.dumps({"kind": kind, "module_exit": code, "operations": list(OPERATIONS[kind]),
                    "phase": cp.phase, "tool_calls": cp.budget.tool_calls, "source_calls_library": len(calls),
                    "postexit_calls_available": False, "active_seconds_cli": cp.budget.active_seconds,
                    "active_seconds_library": lcp.budget.active_seconds, "planner_calls": cp.budget.planner_calls,
                    "export_hashes_cli": hashes, "export_hashes_library": dict(library.export.actual_file_hashes),
                    "owner_closed": cli.shutdown.owner_closed, "shutdown_seconds": cli.shutdown.elapsed_seconds}, sort_keys=True))

    def test_injected_child_retains_actual_source_call_sequence_without_sql_and_matches_library(self):
        code = '''
from contextlib import redirect_stdout
import io,json,sys
from pathlib import Path
from proofkey.cli import main
from proofkey.bootstrap import CliConfiguration
from proofkey.clock import SyntheticReplayClock
from proofkey.contracts import AuthContext
from proofkey.host import AuthResolver,ProfileRegistry
from proofkey.host_contracts import HostLimitsV1,InterfaceLimitsV1
from test_cli import ObservedFactory,request
parent=Path(sys.argv[1]); kind=sys.argv[2]
factory=ObservedFactory(); clock=SyntheticReplayClock()
configuration=CliConfiguration(factory=factory,auth_resolver=AuthResolver({'synthetic-user':AuthContext(caller_id='U1',proof_reference='synthetic-proof')}),
    profile_registry=ProfileRegistry.builtin(parent/'resources'),clock=clock,host_limits=HostLimitsV1(),interface_limits=InterfaceLimitsV1(),
    output_parent=parent,inventory_parent=parent)
source=parent/'input.json'; source.write_text(json.dumps(request(kind)))
release='host-window-replay-v1' if kind=='reschedule_window' else 'host-goods-replay-v1'
result=main(['run','--input',str(source),'--release',release],configuration=configuration)
cp,intents,calls,original=factory.snapshots[-1]
observation={'calls':[(c.operation,c.purpose) for c in calls],'active_seconds':cp.budget.active_seconds,
    'tool_calls':cp.budget.tool_calls,'phase':cp.phase,'original':original.model_dump(mode='json'),
    'imports': sorted(set(str(Path(m.__file__).resolve()) for n,m in sys.modules.copy().items()
        if getattr(m,'__file__',None) and (n.startswith('proofkey') or n=='test_cli')))}
(parent/'OBSERVATION.json').write_text(json.dumps(observation,sort_keys=True))
sys.exit(result)
'''
        for kind in OPERATIONS:
            parent = self.base / (kind + "-observed")
            parent.mkdir(mode=0o700)
            completed = subprocess.run([sys.executable, "-c", code, str(parent), kind], cwd=parent,
                env=self.env, capture_output=True, text=True, timeout=15)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            receipt = CliReceiptV1.model_validate_json(completed.stdout)
            self.assertEqual(receipt.run.command.result.status, "authorized")
            observed = json.loads((parent / "OBSERVATION.json").read_text())
            library, (cp, _, calls, original) = self.library(self.base / (kind + "-sequence-library"), kind)
            self.assertEqual(observed["calls"], [[call.operation, call.purpose] for call in calls])
            self.assertEqual(observed["tool_calls"], len(calls))
            self.assertEqual(observed["phase"], cp.phase)
            self.assertEqual(observed["original"], original.model_dump(mode="json"))
            print("CLI-CHILD-IMPORTS " + json.dumps(observed["imports"]))
            print("CLI-SOURCE-PARITY " + json.dumps({"kind": kind, "calls": observed["calls"],
                "active_seconds_child": observed["active_seconds"], "active_seconds_library": cp.budget.active_seconds}, sort_keys=True))

    def test_default_completed_recovery_and_restarted_clock_controls_preserve_actual_denials(self):
        parent = self.base / "recovery"
        parent.mkdir(mode=0o700)
        source = parent / "input.json"
        source.write_text(json.dumps(request()))
        code, first = self.subprocess(parent, ["run", "--input", str(source)])
        self.assertEqual(code, 0)
        code, recovery = self.subprocess(parent, ["recover", "--case-id", "C1"])
        self.assertEqual(code, 2)
        self.assertEqual(recovery.run.command.result.status, "denied")
        self.assertIsNone(recovery.run.command.result.binding)
        print("CLI-RESTART-CLOCK " + json.dumps({"run_exit": 0, "recover_exit": code,
            "recovery_status": recovery.run.command.result.status, "clock": "restarted_synthetic_epoch",
            "first_as_of": first.run.command.result.as_of.isoformat(),
            "second_captured_at": recovery.run.window.execution.captured_at.isoformat()}))
        code, stopped = self.subprocess(parent, ["stop", "--case-id", "C1", "--generation", "G1"])
        self.assertEqual(code, 2)
        self.assertEqual(stopped.run.command.result.status, "denied")
        print("CLI-RESTART-STOP " + json.dumps({"exit": code, "status": stopped.run.command.result.status,
            "reason": stopped.run.command.result.reason, "new_epoch": True}))
        # The fixed fixtures have no positive customer/operator wait question.
        reply = dict(question_id="absent", binding=first.run.command.result.binding.model_dump(mode="json"),
            actor_id="U1", proof_reference="synthetic-proof", request_revision="v1", consent_revision="v1",
            owner_state_revision="v1", fields={}, received_at="2026-10-08T10:00:00+00:00", simulated=True)
        source.write_text(json.dumps(reply))
        code, denied = self.subprocess(parent, ["reply", "--input", str(source)])
        self.assertEqual(code, 2)
        self.assertEqual(denied.run.command.result.status, "denied")
        code, transfer = self.subprocess(parent, ["transfer"])
        self.assertEqual(code, 2)
        self.assertEqual(transfer.run.command.outcome, "unavailable")

    def test_package_script_resolves_same_main_and_default_launch_rejects_permissive_existing_root(self):
        project = tomllib.loads((ROOT / "pyproject.toml").read_text())
        module, function = project["project"]["scripts"]["proofkey"].split(":")
        parent = self.base / "entrypoint"
        parent.mkdir(mode=0o700)
        code = "import importlib,sys; sys.exit(getattr(importlib.import_module(sys.argv[1]),sys.argv[2])(['inspect-profile']))"
        completed = subprocess.run([sys.executable, "-c", code, module, function], cwd=parent,
            env=self.env, capture_output=True, text=True, timeout=5)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(CliReceiptV1.model_validate_json(completed.stdout).run.command.outcome, "inspection")
        (parent / ".proofkey").chmod(0o755)
        status, receipt = self.subprocess(parent, ["inspect-profile"])
        self.assertEqual((status, receipt.failure), (4, "bootstrap_unavailable"))
        self.assertIsNone(receipt.shutdown)


if __name__ == "__main__":
    unittest.main()
