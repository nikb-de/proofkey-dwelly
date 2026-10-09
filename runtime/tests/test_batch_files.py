"""Real private file custody, independently of engine/source authorization."""
from datetime import timedelta
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
from unittest.mock import patch

from proofkey.batch_files import PublicationFailure, RunPublisher, read_run_inventory
from proofkey.contracts import CaseResult
from proofkey.exporter import ExportFailure, export_case
from proofkey.host_contracts import (BatchInputV1, BatchManifestV1, BatchPositionInventoryV1,
                                    BatchPositionReceiptV1, InterfaceLimitsV1, _OrdinalAdmissionV1)
from test_batch_contracts import START, window

ROOT = Path(__file__).resolve().parents[1]
CHILD_MODULE_PATHS = set()
CHILD_RUNTIME_READS = set()


def runtime_module_paths():
    return sorted({str(Path(module.__file__).resolve()) for module in tuple(sys.modules.values())
        if getattr(module, "__file__", None) and str(module.__file__).endswith(".py")
        and Path(module.__file__).resolve().is_relative_to(ROOT)})


def child_prefix():
    # Exact child runtime audit installed before checkout imports. This is
    # test-owned observation, not an engine/host callback or custody grant.
    return '''
import sys,json,os
from pathlib import Path
_runtime_root=Path(%r)
_runtime_reads=set()
def _audit(event,args):
 if event=='open' and args and isinstance(args[0],(str,bytes)):
  path=Path(os.fsdecode(args[0])).resolve()
  if path.is_relative_to(_runtime_root) and path.suffix!='.pyc':
   flags=args[2] if len(args)>2 else None
   if not (type(flags) is int and flags & os.O_DIRECTORY and path.is_dir()):
    _runtime_reads.add(str(path))
sys.addaudithook(_audit)
def _child_receipt():
 from test_batch_files import runtime_module_paths
 modules=runtime_module_paths()
 assert all(Path(path).is_relative_to(_runtime_root) for path in modules)
 print('CHILD-CONTAINMENT '+json.dumps({'modules':modules,'reads':sorted(_runtime_reads)}),flush=True)
''' % str(ROOT)


def retain_child(completed):
    line = next(line for line in completed.stdout.splitlines() if line.startswith("CHILD-CONTAINMENT "))
    actual = json.loads(line[len("CHILD-CONTAINMENT "):])
    CHILD_MODULE_PATHS.update(actual["modules"])
    CHILD_RUNTIME_READS.update(actual["reads"])


class Clock:
    mode = "synthetic_replay"
    def __init__(self):
        self.seconds = 0.0
    def now(self):
        return START + timedelta(seconds=self.seconds)
    def monotonic(self):
        return -100.0 + self.seconds
    def wait(self, seconds):
        self.seconds += seconds


def manifest(count=1):
    rows = tuple(BatchPositionInventoryV1(ordinal=i, supplied_id_shape="string", supplied_case_id="C1")
                 for i in range(count))
    return BatchManifestV1(run_id="a" * 32,
        input=BatchInputV1(input_hash="b" * 64, input_bytes=2, position_count=count,
                          encoding="canonical_json_array_v1"),
        release_id="registered", mode="synthetic_replay", clock_mode="synthetic_replay", window=window(),
        inventories=rows, positions=tuple(BatchPositionReceiptV1(inventory=r) for r in rows), as_of=START)


class BatchFileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / "run"
        self.clock = Clock()
        self.limits = InterfaceLimitsV1()

    def publisher(self, **kwargs):
        publisher = RunPublisher(self.root, window=window(), clock=self.clock,
                                 limits=kwargs.get("limits", self.limits))
        self.addCleanup(publisher.close)
        return publisher

    def test_new_root_and_fixed_inventory_are_actual_private_readback(self):
        publisher = self.publisher()
        self.assertTrue(self.root.is_dir())
        reference = publisher.publish_input(manifest(3))
        data = (self.root / reference.name).read_bytes()
        self.assertEqual(reference.file_hash, sha256(data).hexdigest())
        self.assertEqual(self.root.stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.root / reference.name).stat().st_mode & 0o777, 0o600)
        readback = read_run_inventory(self.root, limits=self.limits)
        self.assertEqual(readback.status, "partial")
        self.assertEqual(tuple(r.ordinal for r in readback.position_inventories), (0, 1, 2))
        self.assertEqual(readback.joined_command_ids, ())

    def test_actual_admission_gap_readback_is_unresolved_not_guessed_or_complete(self):
        publisher = self.publisher()
        initial = manifest()
        publisher.publish_input(initial)
        admission = _OrdinalAdmissionV1(run_id=initial.run_id, ordinal=0, inventory=initial.inventories[0],
            input_hash=initial.input.input_hash, window=initial.window, as_of=START)
        publisher.publish_admission(0, admission)
        readback = read_run_inventory(self.root, limits=self.limits)
        self.assertEqual(readback.status, "partial")
        self.assertEqual(readback.unresolved_admission_ordinals, (0,))
        self.assertEqual(readback.joined_command_ids, ())
        self.assertIsNone(readback.final_manifest)

    def test_no_overwrite_or_symlink_root_and_full_parent_substitution_denies(self):
        publisher = self.publisher()
        publisher.publish_input(manifest())
        before = (self.root / "INPUT-INVENTORY.json").read_bytes()
        with self.assertRaises(PublicationFailure):
            publisher.publish_input(manifest())
        self.assertEqual((self.root / "INPUT-INVENTORY.json").read_bytes(), before)
        with self.assertRaises(PublicationFailure):
            self.publisher()
        moved = self.base / "moved"
        self.root.rename(moved)
        self.root.mkdir()
        with self.assertRaises(PublicationFailure):
            publisher.publish_final(manifest())
        self.assertFalse((self.root / "FINAL-MANIFEST.json").exists())
        link = self.base / "link"
        link.symlink_to(moved, target_is_directory=True)
        with self.assertRaises(PublicationFailure):
            RunPublisher(link, window=window(), clock=self.clock, limits=self.limits)

    def test_deadline_and_cumulative_ledger_limit_prevent_new_write(self):
        publisher = self.publisher(limits=InterfaceLimitsV1(max_run_bytes=10))
        with self.assertRaises(PublicationFailure) as observed:
            publisher.publish_input(manifest())
        self.assertEqual(observed.exception.reason, "publication_limit_exceeded")
        self.assertFalse((self.root / "INPUT-INVENTORY.json").exists())
        self.clock.seconds = 202.0
        with self.assertRaises(PublicationFailure):
            publisher.publish_final(manifest())
        self.assertFalse((self.root / "FINAL-MANIFEST.json").exists())

    def test_current_file_substitution_and_unknown_inventory_are_invalid(self):
        publisher = self.publisher()
        reference = publisher.publish_input(manifest())
        publisher.publish_final(manifest().model_copy(update={"references": (reference,)}))
        readback = read_run_inventory(self.root, limits=self.limits)
        self.assertEqual(readback.status, "committed_snapshot")
        os.chmod(self.root / "INPUT-INVENTORY.json", 0o600)
        with (self.root / "INPUT-INVENTORY.json").open("wb") as output:
            output.write(b'{}')
        self.assertEqual(read_run_inventory(self.root, limits=self.limits).status, "invalid")

    def test_public_export_actual_bytes_are_verified_and_changed_bytes_denied(self):
        publisher = self.publisher()
        publisher.publish_input(manifest())
        result = CaseResult(status="denied", correlation_id="C1", reason="denied")
        actual = export_case(result, self.root / "ANSWERS")
        consumed = publisher.verify_export(actual, result)
        self.assertEqual(tuple(name for name, _ in consumed.actual_file_hashes), ("ANSWER.md", "REASONING.md"))
        with (self.root / "ANSWERS/C1/ANSWER.md").open("ab") as output:
            output.write(b'changed')
        with self.assertRaises(PublicationFailure):
            publisher.verify_export(actual, result)

    def test_actual_safe_id_casefold_unicode_collisions_never_substitute_identity(self):
        publisher = self.publisher()
        publisher.publish_input(manifest())
        for unsafe in ("../C1", "C/1", "C\\1"):
            with self.subTest(unsafe=unsafe):
                result = CaseResult(status="denied", correlation_id=unsafe, reason="denied")
                with self.assertRaises(ExportFailure) as observed:
                    export_case(result, self.root / "ANSWERS")
                self.assertEqual(observed.exception.reason, "unsafe_case_id")
                self.assertEqual(observed.exception.supplied_case_id, unsafe)
        for original, collision in (("Case", "case"), ("é", "e\u0301")):
            result = CaseResult(status="denied", correlation_id=original, reason="denied")
            actual = export_case(result, self.root / "ANSWERS")
            self.assertEqual(publisher.verify_export(actual, result).actual_receipt.output_name, original)
            with self.assertRaises(ExportFailure) as observed:
                export_case(CaseResult(status="denied", correlation_id=collision, reason="denied"),
                            self.root / "ANSWERS")
            self.assertEqual(observed.exception.reason, "output_conflict")
            self.assertEqual(observed.exception.supplied_case_id, collision)
        self.assertEqual({path.name for path in (self.root / "ANSWERS").iterdir()}, {"Case", "é"})

    def test_genuine_exit_after_admission_keeps_all_n_and_unresolved_without_join(self):
        code = '''
import os,sys
from pathlib import Path
from test_batch_files import Clock,manifest
from test_batch_contracts import START,window
from proofkey.batch_files import RunPublisher
from proofkey.host_contracts import InterfaceLimitsV1,_OrdinalAdmissionV1
root=Path(sys.argv[1]); initial=manifest(2)
p=RunPublisher(root,window=window(),clock=Clock(),limits=InterfaceLimitsV1())
p.publish_input(initial)
reference=p.publish_admission(0,_OrdinalAdmissionV1(run_id=initial.run_id,ordinal=0,
 inventory=initial.inventories[0],input_hash=initial.input.input_hash,window=initial.window,as_of=START))
print("ACTUAL-ADMISSION "+reference.file_hash,flush=True)
_child_receipt()
os._exit(74)
'''
        completed = subprocess.run([sys.executable, "-c", child_prefix() + code, str(self.root)], capture_output=True, text=True, timeout=8)
        self.assertEqual(completed.returncode, 74, completed.stderr)
        self.assertIn("ACTUAL-ADMISSION ", completed.stdout)
        retain_child(completed)
        reader = read_run_inventory(self.root, limits=self.limits)
        self.assertEqual(reader.status, "partial")
        self.assertEqual(len(reader.position_inventories), 2)
        self.assertEqual(reader.unresolved_admission_ordinals, (0,))
        self.assertEqual(reader.joined_command_ids, ())
        self.assertIsNone(reader.final_manifest)
        print(completed.stdout.strip())

    def test_genuine_exit_after_real_public_progress_keeps_actual_original_debt(self):
        code = '''
import os,sys,json
from pathlib import Path
from datetime import timedelta
from unittest.mock import patch
from test_batch import canonical
from proofkey.batch import run_batch
from proofkey.batch_files import RunPublisher
from proofkey.clock import SyntheticReplayClock
from proofkey.contracts import AuthContext
from proofkey.execution import ExecutionContext
from proofkey.host import HostDispatcher,RuntimeFactory,ProfileRegistry,AuthResolver
from proofkey.host_contracts import HostLimitsV1,InterfaceLimitsV1
root=Path(sys.argv[1]);clock=SyntheticReplayClock()
registry=ProfileRegistry.builtin(root.parent/'resources')
resolver=AuthResolver({'user':AuthContext(caller_id='U1',proof_reference='synthetic-proof')})
dispatcher=HostDispatcher(RuntimeFactory(),resolver,registry,clock,root.parent/'host',HostLimitsV1(),release_id='host-window-replay-v1')
execution=ExecutionContext.capture(clock.now()+timedelta(seconds=20),clock)
actual=RunPublisher.publish_progress
def crash(self,ordinal,position):
 reference=actual(self,ordinal,position)
 print('ACTUAL-PROGRESS '+json.dumps({'ordinal':ordinal,'id':position.command.command_id,
  'status':position.command.result.status,'file_hash':reference.file_hash}),flush=True)
 _child_receipt()
 os._exit(75)
with patch.object(RunPublisher,'publish_progress',crash):
 run_batch([canonical(),canonical()],dispatcher,resolver.handle('user'),execution,
  publication_deadline=execution.deadline+timedelta(seconds=2),publication_reserve_seconds=2.0,
  output_root=root,limits=InterfaceLimitsV1(),clock=clock)
'''
        completed = subprocess.run([sys.executable, "-c", child_prefix() + code, str(self.root)], capture_output=True, text=True, timeout=12)
        self.assertEqual(completed.returncode, 75, completed.stderr)
        retain_child(completed)
        actual = json.loads(next(line[len("ACTUAL-PROGRESS "):] for line in completed.stdout.splitlines()
                                 if line.startswith("ACTUAL-PROGRESS ")))
        reader = read_run_inventory(self.root, limits=self.limits)
        self.assertEqual(reader.status, "partial")
        self.assertEqual(tuple(r.ordinal for r in reader.position_inventories), (0, 1))
        self.assertEqual(reader.joined_command_ids, (actual["id"],))
        self.assertEqual(reader.unresolved_admission_ordinals, ())
        self.assertFalse((self.root / "POSITION-00000001-ADMISSION.json").exists())
        self.assertIsNone(reader.final_manifest)
        from proofkey.journal import CaseStore
        store = CaseStore(self.base / "resources/host-window-replay-v1/journal.sqlite")
        try:
            cp, intents = store.checkpoint("C1"), store.intents("C1")
            self.assertEqual(len(intents), 1)
            self.assertEqual(intents[0].verification.status, "verified")
            self.assertGreater(cp.budget.active_seconds, 0.0)
            self.assertGreater(cp.budget.tool_calls, 0)
            print("ACTUAL-PROGRESS-DEBT " + json.dumps({"tool_calls": cp.budget.tool_calls,
                  "active_seconds": cp.budget.active_seconds, "verification": intents[0].verification.status}))
        finally:
            store.close()
        print(completed.stdout.strip())

    def test_final_header_mismatch_and_invalid_ordinals_allocate_no_new_marker(self):
        publisher = self.publisher()
        initial = manifest()
        publisher.publish_input(initial)
        with self.assertRaises(PublicationFailure):
            publisher.publish_final(initial.model_copy(update={"release_id": "another-release"}))
        self.assertFalse((self.root / "FINAL-MANIFEST.json").exists())
        admission = _OrdinalAdmissionV1(run_id=initial.run_id, ordinal=0, inventory=initial.inventories[0],
            input_hash=initial.input.input_hash, window=initial.window, as_of=START)
        for ordinal in (-1, True, 9, "0", []):
            with self.subTest(ordinal=ordinal), self.assertRaises(PublicationFailure):
                publisher.publish_admission(ordinal, admission)
            with self.subTest(ordinal=ordinal), self.assertRaises(PublicationFailure):
                publisher.publish_progress(ordinal, initial.positions[0])

    def test_real_fsync_returning_after_d_retains_pending_no_false_reference(self):
        publisher = self.publisher()
        actual_fsync = os.fsync
        def forward(descriptor):
            actual_fsync(descriptor)
            self.clock.seconds = 202.0
        with patch("proofkey.batch_files.os.fsync", side_effect=forward), self.assertRaises(PublicationFailure):
            publisher.publish_input(manifest())
        self.assertFalse((self.root / "INPUT-INVENTORY.json").exists())
        names = list(self.root.iterdir())
        self.assertEqual(len(names), 1)
        self.assertTrue(names[0].name.startswith("INPUT-INVENTORY.json.pending-"))
        self.assertGreater(names[0].stat().st_size, 0)

    def test_complete_parent_substitution_cannot_keep_old_output_inode_as_authority(self):
        parent = self.base / "registered"
        parent.mkdir()
        self.root = parent / "run"
        publisher = self.publisher()
        publisher.publish_input(manifest())
        original = self.base / "original-parent"
        parent.rename(original)
        parent.mkdir()
        (original / "run").rename(parent / "run")
        with self.assertRaises(PublicationFailure):
            publisher.publish_final(manifest())
        self.assertFalse((parent / "run/FINAL-MANIFEST.json").exists())

    def test_readback_rejects_final_labels_changed_after_actual_publication(self):
        publisher = self.publisher()
        initial = manifest(0)
        reference = publisher.publish_input(initial)
        publisher.publish_final(initial.model_copy(update={"references": (reference,)}))
        payload = json.loads((self.root / "FINAL-MANIFEST.json").read_bytes())
        payload["release_id"] = "different-registered-release"
        with (self.root / "FINAL-MANIFEST.json").open("w") as output:
            json.dump(payload, output)
        self.assertEqual(read_run_inventory(self.root, limits=self.limits).status, "invalid")

    def test_backwards_clock_between_actual_publications_never_reopens_allowance(self):
        publisher = self.publisher()
        self.clock.seconds = 1.0
        reference = publisher.publish_input(manifest())
        self.clock.seconds = 0.5
        with self.assertRaises(PublicationFailure):
            publisher.publish_final(manifest().model_copy(update={"references": (reference,)}))
        self.assertFalse((self.root / "FINAL-MANIFEST.json").exists())
