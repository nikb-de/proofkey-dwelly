"""External acceptance regressions using real denial state and controlled faults."""
import importlib.util
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from proofkey.clock import SyntheticReplayClock

RUNTIME = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


driver = load("j06_acceptance_driver", RUNTIME / "scripts/verify_synthetic_provisioning.py")
example = load("j06_acceptance_example", RUNTIME / "examples/registered_case_bootstrap.py")
DATA = RUNTIME / "examples/registered-cases"
REQUEST = DATA / "window-request.json"


class AcceptanceFailureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        parent = Path(cls.temp.name).resolve()
        clock = SyntheticReplayClock()
        cls.prepared, cls.request = example.prepare_case(REQUEST, DATA / "window-fixture.json", parent, clock)
        cls.receipt = example.execute_case(cls.prepared, cls.request, REQUEST, clock, "cli", negative="wrong-proof")
        assert cls.receipt["code"] != 0
        assert cls.receipt["shutdown"].owner_closed

    def copy_prepared(self, *, rollback=True):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        parent = Path(folder.name).resolve()
        root = parent / "copy"
        self.assertFalse(list(self.prepared.root.rglob("*-wal")))
        shutil.copytree(self.prepared.root, root, ignore=shutil.ignore_patterns("*-shm"))
        # Test-owned copies use rollback journals so SQLite read-only attachment
        # does not allocate WAL coordination sidecars during the immutability check.
        for path in root.rglob("*.sqlite"):
            if not rollback:
                continue
            db = sqlite3.connect(path)
            try:
                db.execute("PRAGMA journal_mode=DELETE")
            finally:
                db.close()
        return SimpleNamespace(root=root, control_parent=root / "control",
            host_release=SimpleNamespace(resource_root=root / "resources"),
            binding=self.prepared.binding, registry=self.prepared.registry)

    def test_actual_wrong_proof_state_is_accepted_read_only(self):
        prepared = self.copy_prepared()
        before = driver.snapshot(prepared.root)
        driver.check_wrong_proof(prepared, self.request, self.receipt)
        self.assertEqual(driver.snapshot(prepared.root), before)

    def test_native_wal_format_denial_needs_only_one_read_per_database(self):
        prepared = self.copy_prepared(rollback=False)
        before = {str(path): driver.digest(path) for path in prepared.root.rglob("*.sqlite")}
        driver.check_wrong_proof(prepared, self.request, self.receipt)
        self.assertEqual({str(path): driver.digest(path) for path in prepared.root.rglob("*.sqlite")}, before)

    def test_missing_or_pending_shutdown_is_rejected(self):
        pending = self.receipt["shutdown"].model_copy(update={"owner_closed": False,
            "pending_command_ids": ("0" * 32,)})
        for shutdown in (None, pending):
            with self.subTest(shutdown=shutdown):
                with self.assertRaises(AssertionError):
                    driver.check_wrong_proof(self.copy_prepared(), self.request,
                                             {**self.receipt, "shutdown": shutdown})

    def test_wrong_proof_rejects_each_retained_state_mutation(self):
        mutations = (
            ("claim-state", "control/host-claims.sqlite", "UPDATE claims SET state='binding_sealed'"),
            ("claim-wire", "control/host-claims.sqlite", "UPDATE claims SET wire='{}'"),
            ("attempt-state", "resources/journal.sqlite", "UPDATE admission_attempts SET state='transferred'"),
            ("attempt-wire", "resources/journal.sqlite", "UPDATE admission_attempts SET attempt_json='{}'"),
            ("active-lease", "resources/journal.sqlite", "UPDATE admission_entries SET state='active'"),
            ("lease-wire", "resources/journal.sqlite", "UPDATE admission_entries SET lease_json='{}'"),
            ("route", "control/routes.sqlite", "INSERT INTO routes VALUES('extra','extra','J06-R','J06-CASE-WINDOW','G1','J06-L','reserved','{}')"),
            ("case", "resources/journal.sqlite", "INSERT INTO cases VALUES('EXTRA','{}',1)"),
            ("intent", "resources/journal.sqlite", "INSERT INTO intents VALUES('extra','EXTRA','G1','hash','{}','prepared',NULL)"),
            ("effect", "resources/world.sqlite", "INSERT INTO effects(account_id,provider_key) VALUES('extra','extra')"),
            ("reservation", "resources/world.sqlite", "INSERT INTO reservations VALUES('extra','extra',1)"),
            ("pressure", "resources/world.sqlite", "UPDATE pressure SET active=1"),
        )
        for name, path, sql in mutations:
            with self.subTest(mutation=name):
                prepared = self.copy_prepared()
                with sqlite3.connect(prepared.root / path) as db:
                    db.execute(sql)
                db.close()
                before = driver.snapshot(prepared.root)
                with self.assertRaises((AssertionError, ValueError)):
                    driver.check_wrong_proof(prepared, self.request, self.receipt)
                self.assertEqual(driver.snapshot(prepared.root), before)

    def fresh(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        parent = Path(folder.name).resolve()
        clock = SyntheticReplayClock()
        prepared, request = example.prepare_case(REQUEST, DATA / "window-fixture.json", parent, clock)
        return parent, clock, prepared, request

    def test_raised_library_command_retains_original_and_actual_closed_receipt(self):
        parent, clock, prepared, request = self.fresh()
        original = RuntimeError("injected command failure")
        closes = []
        mapping_before_command = []
        actual_close = example.HostDispatcher.close
        def fail_command(*args, **kwargs):
            mapping_before_command.append((parent / "private-preparation.json").is_file())
            raise original
        def close(dispatcher, deadline):
            receipt = actual_close(dispatcher, deadline)
            closes.append(receipt)
            return receipt
        with patch.object(example, "run_command", side_effect=fail_command), patch.object(example.HostDispatcher, "close", close):
            with self.assertRaises(RuntimeError) as caught:
                driver.execute_recorded(example, prepared, request, REQUEST, clock, "library", parent)
        self.assertIs(caught.exception, original)
        self.assertEqual(len(closes), 1)
        self.assertTrue(closes[0].owner_closed)
        self.assertEqual(mapping_before_command, [True])
        self.assertTrue((parent / "private-preparation.json").exists(), "preparation mapping lost on exception")
        mapping = json.loads((parent / "private-preparation.json").read_text())
        self.assertEqual(mapping["root"], str(prepared.root))
        self.assertEqual(mapping["resource"], str(prepared.host_release.resource_root))
        retained = json.loads((parent / "exception-lifecycle.json").read_text())
        self.assertEqual(retained["shutdown"], closes[0].model_dump(mode="json"))
        self.assertTrue(retained["owner_closed"])
        self.assertIn("injected command failure", retained["error"])

    def test_raised_library_command_records_pending_close_without_hiding_original(self):
        parent, clock, prepared, request = self.fresh()
        original = RuntimeError("original command failure with pending close")
        actual_close = example.HostDispatcher.close
        def close(dispatcher, deadline):
            actual = actual_close(dispatcher, deadline)
            return actual.model_copy(update={"owner_closed": False, "pending_command_ids": ("0" * 32,)})
        with patch.object(example, "run_command", side_effect=original), patch.object(example.HostDispatcher, "close", close):
            with self.assertRaises(RuntimeError) as caught:
                driver.execute_recorded(example, prepared, request, REQUEST, clock, "library", parent)
        self.assertIs(caught.exception, original)
        self.assertTrue((parent / "exception-lifecycle.json").exists(), "pending close evidence lost")
        retained = json.loads((parent / "exception-lifecycle.json").read_text())
        self.assertFalse(retained["owner_closed"])
        self.assertEqual(retained["shutdown"]["pending_command_ids"], ["0" * 32])

    def test_close_error_does_not_replace_original_command_error(self):
        parent, clock, prepared, request = self.fresh()
        original = RuntimeError("original command failure with close error")
        close_error = ValueError("injected close evidence failure")
        actual_close = example.HostDispatcher.close
        def close(dispatcher, deadline):
            actual_close(dispatcher, deadline)
            raise close_error
        with patch.object(example, "run_command", side_effect=original), patch.object(example.HostDispatcher, "close", close):
            with self.assertRaises(Exception) as caught:
                driver.execute_recorded(example, prepared, request, REQUEST, clock, "library", parent)
        self.assertIs(caught.exception, original)
        self.assertTrue((parent / "exception-lifecycle.json").exists(), "close error evidence lost")
        retained = json.loads((parent / "exception-lifecycle.json").read_text())
        self.assertIsNone(retained["shutdown"])
        self.assertFalse(retained["owner_closed"])
        self.assertIn("injected close evidence failure", retained["close_error"])


if __name__ == "__main__":
    unittest.main()
