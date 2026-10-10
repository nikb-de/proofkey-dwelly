"""Bridge acceptance against actual completed offline service jobs."""
import copy
from hashlib import sha256
import importlib
import json
import multiprocessing
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from tools.dwelly_cases.importer import import_cases
from tools.dwelly_cases.tests.fixtures import make_source
from tools.dwelly_model import runner
from tools.dwelly_model import providers
from tools.dwelly_model.tests.test_runner import config
from tools.dwelly_service.store import JobStore


def completed_source(root):
    raw, bundle, service = root / "raw", root / "bundle", root / "service"
    make_source(raw)
    import_cases(raw, bundle, expected_cases=1)
    store = JobStore(service)
    try:
        job, _ = store.submit("bridge-test", {"mode": "dry_run", "limit": 1, "evaluate": False,
                             "max_parallel_requests": 1, "per_provider_limit": 1})
        store.claim_next()
        output = store.output_path(job["job_id"])
        runner.run_experiment(bundle, output, config(), limit=1, proposals_only=True)
        store.finish(job["job_id"], "completed")
        return service, job["job_id"], "delivery-logistics-001", output
    finally:
        store.close()


def hashes(root):
    return {str(p.relative_to(root)): sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


def bound_target():
    return {"binding": {"case_id": "C1", "object_id": "O1", "principal_id": "U1", "request_id": "REQ1",
                        "request_revision": "v1", "consent_revision": "v1", "generation": "G1",
                        "fingerprint": "a" * 64, "supersedes_generation": None},
            "profile_version": "v1", "process_version": "v1", "policy_version": "v1",
            "checkpoint_hash": "b" * 64, "checked_at": "2026-10-10T12:00:00+00:00"}


class HostResolver:
    def __init__(self, result=None, roots=()):
        self.result = result if result is not None else {"status": "bound", "reason": None, "target": bound_target()}
        self.shadow_protected_roots = roots

    def __call__(self, case, snapshot):
        if case != "delivery-logistics-001" or len(snapshot) != 64:
            raise AssertionError("Incorrect source passed to host")
        return copy.deepcopy(self.result)


def child_import(source, job, case, output, queue):
    from tools.dwelly_bridge.bridge import import_shadow
    queue.put(import_shadow(source, job, case, output))


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.service, self.job, self.case, self.artifacts = completed_source(self.root)
        self.output = self.root / "shadow"

    def run_bridge(self, *, resolver=None, output=None):
        try:
            api = importlib.import_module("tools.dwelly_bridge.bridge")
        except ImportError:
            self.fail("Shadow bridge API must be implemented")
        return api.import_shadow(self.service, self.job, self.case,
                                 self.output if output is None else output, resolver=resolver)

    def test_default_import_is_unmapped_and_repeatable(self):
        before = hashes(self.service)
        first = self.run_bridge()
        self.assertEqual(first, self.run_bridge())
        self.assertEqual(first["schema_version"], "dwelly-shadow-record-v1")
        self.assertEqual(first["status"], "unmapped")
        self.assertEqual(first["reason"], "resolver_absent")
        self.assertFalse(first["authorization"])
        self.assertEqual(first["effects"], [])
        self.assertIsNone(first["target"])
        self.assertRegex(first["import_id"], "^[a-f0-9]{64}$")
        self.assertEqual(len(first["source"]), 9)
        self.assertNotIn("message", json.dumps(first))
        self.assertEqual(before, hashes(self.service))

    def test_bound_import_retains_complete_binding_and_first_check_time(self):
        resolver = HostResolver()
        first = self.run_bridge(resolver=resolver)
        self.assertEqual(first["status"], "shadow_recorded")
        self.assertEqual(first["target"], bound_target())
        resolver.result["target"]["checked_at"] = "2026-10-10T12:01:00+00:00"
        self.assertEqual(first, self.run_bridge(resolver=resolver))
        self.assertFalse(first["authorization"])

    def test_changed_checkpoint_or_revision_conflicts_under_stable_target_identity(self):
        for field in ("checkpoint_hash", "request_revision", "generation"):
            with self.subTest(field=field):
                resolver = HostResolver()
                output = self.root / field
                self.run_bridge(resolver=resolver, output=output)
                container = resolver.result["target"] if field == "checkpoint_hash" else resolver.result["target"]["binding"]
                container[field] = "c" * 64 if field == "checkpoint_hash" else "changed"
                result = self.run_bridge(resolver=resolver, output=output)
                self.assertEqual(result["status"], "rejected")
                self.assertEqual(result["reason"], "idempotency_conflict")
                self.assertIsNone(result["target"])

    def test_changed_source_bytes_conflict(self):
        self.run_bridge()
        with (self.artifacts / "summary.json").open("ab") as stream:
            stream.write(b" \n")
        self.assertEqual(self.run_bridge()["reason"], "idempotency_conflict")

    def test_different_target_has_a_separate_logical_identity(self):
        first = self.run_bridge(resolver=HostResolver())
        resolver = HostResolver()
        resolver.result["target"]["binding"]["request_id"] = "REQ2"
        second = self.run_bridge(resolver=resolver)
        self.assertNotEqual(first["import_id"], second["import_id"])

    def test_denied_and_absent_mapping_disclose_no_target(self):
        for status, reason in (("rejected", "scope_denied"), ("unmapped", "mapping_absent")):
            result = self.run_bridge(resolver=HostResolver({"status": status, "reason": reason}))
            self.assertEqual(result["status"], status)
            self.assertEqual(result["reason"], reason)
            self.assertIsNone(result["target"])

    def test_invalid_source_is_sanitized_and_never_creates_output(self):
        self.case = "../SECRET"
        result = self.run_bridge()
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason"], "source_identity_invalid")
        self.assertIsNone(result["source"])
        self.assertNotIn("SECRET", json.dumps(result))
        self.assertFalse(self.output.exists())

    def test_malformed_resolver_results_cannot_disclose_or_persist(self):
        bad = [None, [], {"status": "execute", "reason": None},
               {"status": "rejected", "reason": "SECRET"},
               {"status": "unmapped", "reason": "mapping_absent", "target": bound_target()}]
        for mutation in (lambda t: t.update(extra="SECRET"), lambda t: t.update(checkpoint_hash="bad"),
                         lambda t: t.update(checked_at="2026-10-10T12:00:00"),
                         lambda t: t.update(checked_at=float("nan")),
                         lambda t: t["binding"].update(fingerprint="bad"),
                         lambda t: t["binding"].update(principal_id="\nSECRET"),
                         lambda t: t["binding"].update(extra="SECRET")):
            target = bound_target()
            mutation(target)
            bad.append({"status": "bound", "reason": None, "target": target})
        for value in bad:
            with self.subTest(value=value):
                resolver = HostResolver()
                resolver.result = value
                result = self.run_bridge(resolver=resolver)
                self.assertEqual(result["status"], "rejected")
                self.assertEqual(result["reason"], "resolver_invalid")
                self.assertIsNone(result["target"])
                self.assertNotIn("SECRET", json.dumps(result))
                self.assertFalse(self.output.exists())

    def test_resolver_exception_is_sanitized(self):
        class Broken(HostResolver):
            def __call__(self, *_):
                raise RuntimeError("SECRET")
        result = self.run_bridge(resolver=Broken())
        self.assertEqual(result["reason"], "resolver_unavailable")
        self.assertNotIn("SECRET", json.dumps(result))
        self.assertFalse(self.output.exists())

    def test_storage_readback_rejects_nonboolean_authorization_and_invalid_time(self):
        from tools.dwelly_bridge.bridge import _record, _validate_readback
        content = _record("shadow_recorded", None, {"source_hash": "d" * 64}, bound_target())
        for field in ("authorization", "checked_at"):
            stored = copy.deepcopy(content)
            stored["import_id"] = "c" * 64
            if field == "authorization":
                stored["authorization"] = 0
            else:
                stored["target"][field] = float("nan")
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "^shadow_storage_error$"):
                _validate_readback(stored, content)

    def test_source_and_runtime_output_overlap_rejected_before_mutation(self):
        before = hashes(self.service)
        runtime = self.root / "runtime"
        runtime.mkdir()
        for output, resolver in ((self.service, None), (self.service / "new", None), (self.root, None),
                                 (runtime, HostResolver(roots=(runtime,))),
                                 (runtime / "new", HostResolver(roots=(runtime,))),
                                 (self.root, HostResolver(roots=(runtime,)))):
            with self.subTest(output=output):
                self.assertEqual(self.run_bridge(output=output, resolver=resolver)["reason"], "shadow_root_overlap")
        self.assertEqual(before, hashes(self.service))
        self.assertEqual(list(runtime.iterdir()), [])

    def test_missing_or_malformed_runtime_protection_fails_closed(self):
        for roots in (None, [], ("relative",), (self.root / "absent",), (self.root / "..",)):
            resolver = HostResolver(roots=roots)
            self.assertEqual(self.run_bridge(resolver=resolver)["reason"], "resolver_invalid")
            self.assertFalse(self.output.exists())
        self.assertEqual(self.run_bridge(resolver=lambda *_: {})["reason"], "resolver_invalid")

    def test_symlink_output_is_rejected(self):
        real = self.root / "real"
        real.mkdir(mode=0o700)
        self.output.symlink_to(real, target_is_directory=True)
        result = self.run_bridge()
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(list(real.iterdir()), [])

    def test_output_traversal_has_a_bounded_output_error(self):
        result = self.run_bridge(output=self.root / "unused" / ".." / "shadow")
        self.assertEqual(result["reason"], "unsafe_shadow_directory")
        self.assertFalse(self.output.exists())

    def test_concurrent_process_imports_and_reopen_return_one_record(self):
        context = multiprocessing.get_context("spawn")
        queue = context.Queue()
        workers = [context.Process(target=child_import, args=(self.service, self.job, self.case, self.output, queue))
                   for _ in range(3)]
        for worker in workers:
            worker.start()
        results = [queue.get(timeout=30) for _ in workers]
        for worker in workers:
            worker.join(30)
            self.assertEqual(worker.exitcode, 0)
        self.assertEqual(results, [results[0]] * 3)
        self.assertEqual(results[0], self.run_bridge())
        import sqlite3
        with sqlite3.connect(self.output / "shadow.sqlite3") as db:
            self.assertEqual(db.execute("SELECT count(*) FROM records").fetchone()[0], 1)

    def test_offline_import_never_calls_network_or_provider(self):
        before = hashes(self.service)
        with patch.object(socket, "create_connection", side_effect=AssertionError("network forbidden")), \
             patch.object(socket.socket, "connect", side_effect=AssertionError("network forbidden")), \
             patch.object(providers, "complete", side_effect=AssertionError("provider forbidden")), \
             patch.object(runner, "run_experiment", side_effect=AssertionError("experiment forbidden")):
            self.assertEqual(self.run_bridge()["status"], "unmapped")
        self.assertEqual(before, hashes(self.service))

    @unittest.skipUnless(importlib.util.find_spec("proofkey"), "Run with runtime environment and PYTHONPATH=runtime/src:runtime/tests")
    def test_actual_runtime_resolver_observes_without_network_or_runtime_effects(self):
        from proofkey.gateway import ActionGateway
        from proofkey.identity import fingerprint
        from proofkey.journal import CaseStore
        from tools.dwelly_bridge.runtime_binding import RuntimeShadowResolver, RuntimeShadowTarget
        from tools.dwelly_bridge.source import load_source
        from support import NOW, make_auth, make_binding, make_checkpoint, make_request

        runtime = self.root / "runtime"
        runtime.mkdir()
        store = CaseStore(runtime / "journal.sqlite")
        self.addCleanup(store.close)
        store.admit(make_binding(), make_request(), make_checkpoint())
        source = load_source(self.service, self.job, self.case)
        target = RuntimeShadowTarget(source_case_id=self.case, source_snapshot_hash=source.snapshot_hash,
            binding=make_binding(), checkpoint_hash=fingerprint(store.checkpoint("C1").model_dump(mode="json")),
            profile_version="v1", process_version="v1", policy_version="v1", allowed_caller_ids=("U1",))
        resolver = RuntimeShadowResolver(store, (target,), auth=make_auth(), clock=lambda: NOW,
            authorize=lambda registered, auth: auth.proof_reference == "synthetic-proof")
        before_source, before_runtime = hashes(self.service), hashes(runtime)
        before_rows, total_changes = list(store._db.iterdump()), store._db.total_changes
        with patch.object(socket, "create_connection", side_effect=AssertionError("network forbidden")), \
             patch.object(socket.socket, "connect", side_effect=AssertionError("network forbidden")), \
             patch.object(providers, "complete", side_effect=AssertionError("provider forbidden")), \
             patch.object(ActionGateway, "execute", side_effect=AssertionError("effect forbidden")), \
             patch.object(ActionGateway, "execute_proposal", side_effect=AssertionError("workflow forbidden")):
            record = self.run_bridge(resolver=resolver)
            self.assertEqual(record["status"], "shadow_recorded")
            self.assertEqual(record["target"]["binding"]["principal_id"], "U1")
            self.assertEqual(record["target"]["checkpoint_hash"], target.checkpoint_hash)
            self.assertEqual(self.run_bridge(resolver=resolver), record)
            denied = RuntimeShadowResolver(store, (target,), auth=make_auth(), clock=lambda: NOW,
                                          authorize=lambda *_: False)
            rejected = self.run_bridge(resolver=denied)
            self.assertEqual(rejected["reason"], "scope_denied")
            self.assertIsNone(rejected["target"])
            self.assertEqual(self.run_bridge(resolver=resolver, output=runtime / "shadow")["reason"], "shadow_root_overlap")
        self.assertEqual(before_source, hashes(self.service))
        self.assertEqual(before_runtime, hashes(runtime))
        self.assertEqual(before_rows, list(store._db.iterdump()))
        self.assertEqual(total_changes, store._db.total_changes)
        self.assertFalse(store._db.in_transaction)


if __name__ == "__main__":
    unittest.main()
