"""Durable storage boundaries, using real private directories and SQLite."""
import copy
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from tools.dwelly_bridge.store import ShadowStore


class ShadowStoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.root = self.base / "shadow"
        self.identity = {"service": "fixture", "job_id": "job-a", "case_id": "case-a",
                         "target": {"case_id": "runtime-a", "request_id": "request-a"}}
        self.content = {"status": "shadow_recorded", "source": {"proposal_hash": "a" * 64},
                        "target": {"checkpoint_hash": "b" * 64,
                                   "checked_at": "2026-10-10T12:00:00+00:00"},
                        "effects": [], "authorization": False}

    def assert_code(self, expected, action):
        with self.assertRaises(ValueError) as raised:
            action()
        self.assertEqual(str(raised.exception), expected)
        self.assertEqual(raised.exception.code, expected)

    def test_repeat_preserves_first_observation(self):
        store = ShadowStore(self.root)
        first = store.record(self.identity, self.content)
        changed = copy.deepcopy(self.content)
        changed["target"]["checked_at"] = "2026-10-10T12:01:00+00:00"
        self.assertEqual(store.record(self.identity, changed), first)
        self.assertEqual(first["target"]["checked_at"], "2026-10-10T12:00:00+00:00")
        self.assertRegex(first["import_id"], r"^[a-f0-9]{64}$")
        self.assertNotIn("import_id", self.content)

    def test_changed_checkpoint_conflicts_without_replacing_record(self):
        store = ShadowStore(self.root)
        first = store.record(self.identity, self.content)
        changed = copy.deepcopy(self.content)
        changed["target"]["checkpoint_hash"] = "c" * 64
        self.assert_code("idempotency_conflict", lambda: store.record(self.identity, changed))
        self.assertEqual(store.record(self.identity, self.content), first)

    def test_only_target_observation_time_is_excluded(self):
        store = ShadowStore(self.root)
        store.record(self.identity, self.content)
        changed = copy.deepcopy(self.content)
        changed["source"]["checked_at"] = "different"
        self.assert_code("idempotency_conflict", lambda: store.record(self.identity, changed))

    def test_reopen_and_independent_instance_return_original_record(self):
        first = ShadowStore(self.root).record(self.identity, self.content)
        first["target"]["checkpoint_hash"] = "mutated-caller-copy"
        second = ShadowStore(self.root).record(self.identity, self.content)
        self.assertEqual(second["target"]["checkpoint_hash"], "b" * 64)
        with sqlite3.connect(self.root / "shadow.sqlite3") as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM records").fetchone()[0], 1)

    def test_logical_identity_has_stable_id_but_distinct_target_is_distinct(self):
        first = ShadowStore(self.root).record(self.identity, self.content)
        other_root = self.base / "other"
        changed = copy.deepcopy(self.content)
        changed["source"]["proposal_hash"] = "c" * 64
        same_id = ShadowStore(other_root).record(self.identity, changed)
        self.assertEqual(first["import_id"], same_id["import_id"])
        other_identity = copy.deepcopy(self.identity)
        other_identity["target"]["request_id"] = "request-b"
        other = ShadowStore(self.root).record(other_identity, self.content)
        self.assertNotEqual(first["import_id"], other["import_id"])

    def test_concurrent_processes_and_restart_without_network(self):
        script = """
import json, socket, sys
from tools.dwelly_bridge.store import ShadowStore
def forbidden(*args, **kwargs):
    raise AssertionError('network forbidden')
socket.socket = forbidden
data = json.load(sys.stdin)
print(json.dumps(ShadowStore(data['root']).record(data['identity'], data['content']), sort_keys=True))
"""
        payload = json.dumps({"root": str(self.root), "identity": self.identity, "content": self.content})
        processes = [subprocess.Popen([sys.executable, "-B", "-c", script], stdin=subprocess.PIPE,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                     for _ in range(8)]
        payloads = []
        for index in range(8):
            content = copy.deepcopy(self.content)
            content["target"]["checked_at"] = f"2026-10-10T12:00:0{index}+00:00"
            payloads.append(json.dumps({"root": str(self.root), "identity": self.identity, "content": content}))
        with ThreadPoolExecutor(max_workers=8) as executor:
            outputs = list(executor.map(lambda pair: pair[0].communicate(pair[1], timeout=30),
                                        zip(processes, payloads)))
        results = []
        for process, (stdout, stderr) in zip(processes, outputs):
            self.assertEqual(process.returncode, 0, stderr)
            results.append(json.loads(stdout))
        self.assertTrue(all(result == results[0] for result in results))
        restarted = subprocess.run([sys.executable, "-B", "-c", script], input=payload,
                                   capture_output=True, text=True, timeout=30)
        self.assertEqual(restarted.returncode, 0, restarted.stderr)
        self.assertEqual(json.loads(restarted.stdout), results[0])
        with sqlite3.connect(self.root / "shadow.sqlite3") as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM records").fetchone()[0], 1)

    def test_malformed_nonfinite_and_non_json_values_are_bounded_errors(self):
        store = ShadowStore(self.root)
        cases = [[], {}, {1: "secret"}, {"value": float("nan")}, {"value": float("inf")},
                 {"value": (1, 2)}, {"value": object()}, {"target": []}, {"import_id": "forged"}]
        recursive = {}
        recursive["value"] = recursive
        cases.append(recursive)
        for value in cases:
            with self.subTest(value_type=type(value).__name__):
                self.assert_code("invalid_shadow_content", lambda: store.record(self.identity, value))
        for value in ([], {}, {False: "secret"}, {"value": float("nan")}):
            self.assert_code("invalid_shadow_identity", lambda: store.record(value, self.content))

    def test_size_and_depth_are_bounded(self):
        store = ShadowStore(self.root)
        self.assert_code("invalid_shadow_content", lambda: store.record(self.identity, {"secret": "x" * 65536}))
        self.assert_code("invalid_shadow_identity", lambda: store.record({"id": "x" * 65536}, self.content))
        nested = {"value": "leaf"}
        for _ in range(100):
            nested = {"nested": nested}
        self.assert_code("invalid_shadow_content", lambda: store.record(self.identity, nested))

    def test_exact_size_limit_accepts_valid_content(self):
        content = {"x": "a" * 65528}  # Canonical JSON is exactly 65536 ASCII bytes.
        self.assertEqual(ShadowStore(self.root).record(self.identity, content)["x"], content["x"])

    def test_corrupt_persisted_record_is_not_returned(self):
        store = ShadowStore(self.root)
        store.record(self.identity, self.content)
        with sqlite3.connect(store.database) as connection:
            connection.execute("UPDATE records SET record = ?", ('{"import_id":NaN}',))
        self.assert_code("shadow_storage_error", lambda: store.record(self.identity, self.content))

    def test_changed_persisted_content_is_not_returned_under_old_fingerprint(self):
        store = ShadowStore(self.root)
        first = store.record(self.identity, self.content)
        first["authorization"] = True
        with sqlite3.connect(store.database) as connection:
            connection.execute("UPDATE records SET record = ?", (json.dumps(first),))
        self.assert_code("shadow_storage_error", lambda: store.record(self.identity, self.content))

    def test_nonfinite_persisted_observation_is_rejected(self):
        store = ShadowStore(self.root)
        first = store.record(self.identity, self.content)
        for invalid in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(invalid=invalid):
                first["target"]["checked_at"] = invalid
                with sqlite3.connect(store.database) as connection:
                    connection.execute("UPDATE records SET record = ?", (json.dumps(first),))
                self.assert_code("shadow_storage_error", lambda: store.record(self.identity, self.content))

    def test_overdeep_persisted_observation_is_rejected(self):
        store = ShadowStore(self.root)
        first = store.record(self.identity, self.content)
        for depth in (65, 1500, 10000):
            with self.subTest(depth=depth):
                serialized = json.dumps(first).replace(
                    '"2026-10-10T12:00:00+00:00"', "[" * depth + "0" + "]" * depth)
                with sqlite3.connect(store.database) as connection:
                    connection.execute("UPDATE records SET record = ?", (serialized,))
                self.assert_code("shadow_storage_error", lambda: store.record(self.identity, self.content))

    def test_duplicate_persisted_observation_key_is_rejected(self):
        store = ShadowStore(self.root)
        first = store.record(self.identity, self.content)
        serialized = json.dumps(first).replace(
            '"checked_at":', '"checked_at": "duplicate", "checked_at":')
        with sqlite3.connect(store.database) as connection:
            connection.execute("UPDATE records SET record = ?", (serialized,))
        self.assert_code("shadow_storage_error", lambda: store.record(self.identity, self.content))

    def test_private_directory_and_database_modes(self):
        ShadowStore(self.root).record(self.identity, self.content)
        self.assertEqual(self.root.stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.root / "shadow.sqlite3").stat().st_mode & 0o777, 0o600)

    def test_accessible_existing_directory_is_rejected_without_chmod(self):
        self.root.mkdir(mode=0o755)
        self.assert_code("unsafe_shadow_directory", lambda: ShadowStore(self.root))
        self.assertEqual(self.root.stat().st_mode & 0o777, 0o755)

    def test_symlink_root_and_symlink_ancestor_are_rejected(self):
        actual = self.base / "actual"
        actual.mkdir(mode=0o700)
        self.root.symlink_to(actual, target_is_directory=True)
        self.assert_code("unsafe_shadow_directory", lambda: ShadowStore(self.root))
        self.assert_code("unsafe_shadow_directory", lambda: ShadowStore(self.root / "child"))

    def test_symlink_database_and_sidecars_are_rejected_without_touching_target(self):
        for name in ("shadow.sqlite3", "shadow.sqlite3-journal", "shadow.sqlite3-wal", "shadow.sqlite3-shm"):
            with self.subTest(name=name):
                root = self.base / name
                root.mkdir(mode=0o700)
                target = self.base / (name + "-target")
                target.write_text("secret")
                (root / name).symlink_to(target)
                self.assert_code("unsafe_shadow_database", lambda: ShadowStore(root))
                self.assertEqual(target.read_text(), "secret")

    def test_hardlinked_database_is_rejected(self):
        ShadowStore(self.root).record(self.identity, self.content)
        os.link(self.root / "shadow.sqlite3", self.base / "alias")
        self.assert_code("unsafe_shadow_database", lambda: ShadowStore(self.root))

    def test_hardlinked_sidecar_is_rejected(self):
        ShadowStore(self.root)
        target = self.base / "foreign-data"
        target.write_text("secret")
        target.chmod(0o600)
        os.link(target, self.root / "shadow.sqlite3-wal")
        self.assert_code("unsafe_shadow_database", lambda: ShadowStore(self.root))
        self.assertEqual(target.read_text(), "secret")

    def test_special_database_and_accessible_database_are_rejected(self):
        self.root.mkdir(mode=0o700)
        database = self.root / "shadow.sqlite3"
        os.mkfifo(database, 0o600)
        self.assert_code("unsafe_shadow_database", lambda: ShadowStore(self.root))
        database.unlink()
        database.write_text("secret")
        database.chmod(0o644)
        self.assert_code("unsafe_shadow_database", lambda: ShadowStore(self.root))
        self.assertEqual(database.read_text(), "secret")

    def test_revalidates_path_after_store_construction(self):
        store = ShadowStore(self.root)
        store.record(self.identity, self.content)
        database = self.root / "shadow.sqlite3"
        database.rename(self.root / "saved.sqlite3")
        database.symlink_to(self.root / "saved.sqlite3")
        self.assert_code("unsafe_shadow_database", lambda: store.record(self.identity, self.content))

    def test_corrupt_database_error_does_not_disclose_contents(self):
        self.root.mkdir(mode=0o700)
        database = self.root / "shadow.sqlite3"
        database.write_text("private secret body")
        database.chmod(0o600)
        self.assert_code("shadow_storage_error", lambda: ShadowStore(self.root))


if __name__ == "__main__":
    unittest.main()
