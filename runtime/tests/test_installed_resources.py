"""Relocated-source regressions; these are not installed-wheel receipts."""
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src/proofkey"
# Literal canonical byte commitments, independent of the resource loader.
RESOURCES = {
    "resources/profiles/flat-v1.json": "cab4df81d0f37ca74a7e952db22dd185c0eb9092154564e1f199e39cd1b7a9b2",
    "resources/profiles/flat-v1.1.json": "6a555d7a9c1b00e5c8c176c1e8a74c6fb2317aa1d0f7dfc2dbe3d84d62e03b04",
    "resources/profiles/flat-v1.2.json": "faafa410d3e736a5e1177a9b2b9a9783271854cfad5cc358f1ef3e6705a37778",
    "resources/profiles/flat-v1.3.json": "8fcd07924f5518ffa6e8b7cfcb3d773e8ba9f10d48458031132f8749c177a940",
    "resources/profiles/flat-v1.4.json": "cc21da123bb5c2347f9e8363952541f9d7739e7c2e1b8a76ec0423133871a54a",
    "resources/profiles/nested-v1.json": "ea8451fe41fb2549a22904f7c11cfdd8f96306a95dbd8ba3ded93a3ff19b8cef",
    "resources/profiles/nested-v1.1.json": "cec02aae538b9139526e89fecdd57887a47bb1cb44640ec29ec5edeb46c4cd82",
    "resources/profiles/nested-v1.2.json": "5561191419d0fa2b85a6c354cff1a45f6e74c4a8fc2c2555bb24ba0da4e465f9",
    "resources/profiles/nested-v1.3.json": "089334eef9dd0818f02539b84ed4846870de90493e31ceea31263737b3d6ca15",
    "resources/profiles/nested-v1.4.json": "c560920a90183e3f2715def18f5819dfe6212e63ce411a6cb867f5ec00b7e5c4",
    "resources/fixtures/packet-world-v1.json": "cb9a2c3b8bcf77ee1f400cac7921b52b52f2468180c0b043b8f35f01058a0c59",
    "resources/fixtures/host-goods-world-v1.json": "e3ec67bfd42fb4e6e26394eb9e22fb0c822194768a4eb8eec2ba63b32a27973f",
    "schema.sql": "1ce7f4a5c234c9a93223f9c1f1a3c048b71f6b9958fa9c4783a0d7aecc04f4f8",
}


class InstalledResourceTests(unittest.TestCase):
    def test_packaged_inventory_preserves_canonical_bytes(self):
        # Catches missing/extra assets or changed copies, even if loading succeeds.
        actual = {str(path.relative_to(PACKAGE)) for path in (PACKAGE / "resources").rglob("*")
                  if path.is_file()}
        self.assertEqual(actual, set(RESOURCES) - {"schema.sql"})
        for relative, expected in RESOURCES.items():
            with self.subTest(resource=relative):
                packaged = (PACKAGE / relative).read_bytes()
                self.assertEqual(sha256(packaged).hexdigest(), expected)
                if relative.startswith("resources/profiles/"):
                    original = ROOT / "profiles" / Path(relative).name
                elif relative.startswith("resources/fixtures/"):
                    original = ROOT / "fixtures/development" / Path(relative).name
                else:
                    original = PACKAGE / relative
                self.assertEqual(packaged, original.read_bytes())

    def run_relocated(self, probe):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        base = Path(temporary.name).resolve()
        isolated_site = base / "site-packages"
        shutil.copytree(PACKAGE, isolated_site / "proofkey",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        unrelated = base / "unrelated"
        unrelated.mkdir()
        # Valid-looking locations with unusable bytes must never shadow built-ins.
        for relative in ("profiles", "fixtures", "fixtures/development", "resources/profiles",
                         "resources/fixtures"):
            (unrelated / relative).mkdir(parents=True, exist_ok=True)
        for relative in RESOURCES:
            if relative == "schema.sql":
                continue
            for parent in (Path(relative).parent, Path(*Path(relative).parts[1:-1])):
                (unrelated / parent / Path(relative).name).write_text('{"shadow":true}')
        for name in ("packet-world-v1.json", "host-goods-world-v1.json"):
            (unrelated / "fixtures/development" / name).write_text('{"shadow":true}')
        safe_env = {key: value for key, value in os.environ.items()
                    if key not in {"PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP"}}
        child = subprocess.run([sys.executable, "-B", "-c", probe], cwd=unrelated,
            env={**safe_env, "PYTHONPATH": str(isolated_site), "PYTHONNOUSERSITE": "1",
                 "PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, text=True, timeout=60)
        self.assertEqual(child.returncode, 0, child.stderr)
        return json.loads(child.stdout)

    def test_relocated_package_loads_builtins_hosts_and_fresh_journal(self):
        # Catches checkout/CWD resource roots and missing packaged schema.
        result = self.run_relocated('''
import json
from pathlib import Path
import sqlite3
import proofkey
from proofkey.profiles import load_profile
from proofkey.host import ProfileRegistry
from proofkey.journal import CaseStore
package = Path(proofkey.__file__).resolve().parent
assert package.parent.name == "site-packages"
before = {str(p.relative_to(package)): p.read_bytes() for p in package.rglob("*") if p.is_file()}
names = ["flat-v1", "flat-v1.1", "flat-v1.2", "flat-v1.3", "flat-v1.4",
         "nested-v1", "nested-v1.1", "nested-v1.2", "nested-v1.3", "nested-v1.4"]
for name in names:
    profile = load_profile(name)
    assert profile.profile_id == name
    assert load_profile(package / "resources/profiles" / (name + ".json")) == profile
state = Path.cwd() / "writable-state"
state.mkdir()
registry = ProfileRegistry.builtin(state)
release_ids = ["host-window-replay-v1", "host-goods-replay-v1"]
for release_id in release_ids:
    release = registry.resolve(release_id)
    assert registry.inspect(release_id).profile_hash == "5bb712b13efaace655ee7180f3d913d93cbd637e3d1685331c6a1eecbade7bf4"
    assert release.profile_path == package / "resources/profiles/flat-v1.3.json"
    assert release.fixture_path.parent == package / "resources/fixtures"
    assert release.resource_root == state / release_id
database = state / "fresh.sqlite"
store = CaseStore(database)
assert not store.has_case("absent")
store.close()
with sqlite3.connect(database) as connection:
    assert connection.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0] > 0
after = {str(p.relative_to(package)): p.read_bytes() for p in package.rglob("*") if p.is_file()}
assert before == after
print(json.dumps({"profiles": names, "releases": release_ids, "journal_created": database.is_file()}))
''')
        self.assertEqual(len(result["profiles"]), 10)
        self.assertEqual(result["releases"], ["host-window-replay-v1", "host-goods-replay-v1"])
        self.assertTrue(result["journal_created"])

    def test_relocated_host_rejects_invalid_pinned_resources(self):
        # Each variant starts valid: unrelated baseline failures cannot satisfy rejection.
        targets = {
            "resources/profiles/flat-v1.3.json": ["host-window-replay-v1", "host-goods-replay-v1"],
            "resources/fixtures/packet-world-v1.json": ["host-window-replay-v1"],
            "resources/fixtures/host-goods-world-v1.json": ["host-goods-replay-v1"],
        }
        for target, release_ids in targets.items():
            for mutation in ("missing", "tampered", "symlink", "hardlink"):
                with self.subTest(target=target, mutation=mutation):
                    result = self.run_relocated('''
import json
import os
from pathlib import Path
import proofkey
from proofkey.host import ProfileRegistry
registry = ProfileRegistry.builtin(Path.cwd() / "state")
release_ids = %r
for release_id in release_ids:
    registry.inspect(release_id)
target = Path(proofkey.__file__).resolve().parent / %r
mutation = %r
if mutation == "missing":
    target.unlink()
elif mutation == "tampered":
    target.write_bytes(target.read_bytes() + b" ")
else:
    replacement = Path.cwd() / "original-resource"
    target.rename(replacement)
    if mutation == "symlink":
        target.symlink_to(replacement)
    else:
        os.link(replacement, target)
rejected = []
for release_id in release_ids:
    try:
        registry.inspect(release_id)
    except (OSError, ValueError):
        rejected.append(release_id)
    else:
        raise AssertionError("invalid host resource accepted: " + mutation)
print(json.dumps({"rejected": rejected}))
''' % (release_ids, target, mutation))
                    self.assertEqual(result["rejected"], release_ids)


if __name__ == "__main__":
    unittest.main()
