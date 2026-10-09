"""Outer subprocess checks. This module is never part of the inner factory lane."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from hashlib import sha256


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "runtime/scripts/qualify_factory.py"


class FactoryQualificationTests(unittest.TestCase):
    @property
    def happy_result(self):
        cls = type(self)
        if "_happy_result" not in cls.__dict__:
            directory = tempfile.TemporaryDirectory(prefix="factory-shared-capture-")
            cls.addClassCleanup(directory.cleanup)
            base = Path(directory.name)
            cls._happy_result = cls.launch(ROOT, (), base / "result", base, {})
        return cls._happy_result

    def setUp(self):
        self.assertTrue(SCRIPT.is_file(), "fresh-process factory qualifier is absent")
        self.directory = tempfile.TemporaryDirectory(prefix="factory-qualification-test-")
        self.addCleanup(self.directory.cleanup)
        self.base = Path(self.directory.name)

    def run_lane(self, root=ROOT, extra_python_args=(), output=None, env_changes=None):
        return self.launch(root, extra_python_args, output or self.base / "result", self.base, env_changes or {})

    @staticmethod
    def launch(root, extra_python_args, output, cwd, env_changes):
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"}
        env.update(env_changes)
        result = subprocess.run([sys.executable, *extra_python_args, str(root / "runtime/scripts/qualify_factory.py"),
                                 "--output", str(output)], capture_output=True, text=True,
                                env=env, cwd=cwd, timeout=90)
        result.output = output
        return result

    def read_manifest(self, result):
        path = result.output / "manifest.json"
        self.assertTrue(path.is_file(), result.stdout + result.stderr)
        return json.loads(path.read_text())

    def copy_root(self):
        root = self.base / "checkout"
        shutil.copytree(ROOT / "runtime", root / "runtime",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"))
        return root

    def inject(self, root, code):
        with (root / "runtime/tests/test_adaptation_factory.py").open("a") as stream:
            stream.write("\n" + code + "\n")

    def assert_invalid(self, result, reason):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        manifest = self.read_manifest(result)
        self.assertIn(manifest["status"], ("invalid", "failed"))
        self.assertIn(reason, manifest["error"])
        return manifest

    def test_inner_suite_is_non_recursive_and_complete(self):
        result = self.happy_result
        manifest = self.read_manifest(result)
        self.assertEqual(result.returncode, 0, str(manifest.get("error")) + result.stdout + result.stderr)
        self.assertEqual(manifest["status"], "passed")
        tests = manifest["tests"]
        self.assertEqual(tests["planned_ids"], tests["executed_ids"])
        self.assertEqual(len(tests["executed_ids"]), 37)
        self.assertEqual(len(tests["executed_ids"]), len(set(tests["executed_ids"])))
        self.assertEqual({name.split(".")[0] for name in tests["executed_ids"]},
                         {"test_adaptation_factory", "test_factory_registration"})
        for name in ("skipped", "expected_failures", "unexpected_successes", "failures", "errors"):
            self.assertEqual(tests[name], [])
        self.assertEqual(manifest["python"]["optimize"], 0)
        self.assertTrue(manifest["python"]["dont_write_bytecode"])
        self.assertTrue(manifest["python"]["private_cache_initially_empty"])
        self.assertFalse(manifest["python"]["pythonoptimize_present"])
        self.assertEqual(manifest["source_before"], manifest["source_after"])
        self.assertTrue(manifest["source_stable"])
        self.assertIn("runtime/scripts/qualify_factory.py", manifest["source_before"])
        self.assertIn("runtime/tests/test_factory_qualification.py", manifest["source_before"])
        self.assertIn("runtime/tests/fixtures/factory-legacy-vectors-v1.json", manifest["source_before"])
        origins = manifest["imports"]["after"]
        for name in ("proofkey.factory", "proofkey.contracts", "support", "test_packet_source",
                     "proofkey.adapters.operator", "proofkey.adapters.world", "proofkey.verifier",
                     "proofkey.packet_contracts", "proofkey.process", "proofkey.profiles"):
            self.assertIn(name, origins)
            self.assertIn(origins[name]["path"], manifest["source_before"])
            self.assertTrue(origins[name]["identity"])
        self.assertNotIn("test_factory_qualification", origins)
        self.assertTrue(any(row["name"].lower() == "pydantic" for row in manifest["distributions"]))

    def test_artifact_bytes_have_exact_hashes_and_cross_artifact_bindings(self):
        result = self.happy_result
        manifest = self.read_manifest(result)
        self.assertEqual(result.returncode, 0, str(manifest.get("error")) + result.stderr)
        values = {}
        for row in manifest["artifacts"]:
            raw = (result.output / row["path"]).read_bytes()
            self.assertEqual(row["sha256"], sha256(raw).hexdigest())
            value = json.loads(raw)
            self.assertEqual(raw, json.dumps(value, sort_keys=True, separators=(",", ":"),
                                            ensure_ascii=False, allow_nan=False).encode())
            values[row["kind"]] = value
        self.assertEqual(set(values), {"proposal", "regression", "simulated_approval", "review_packet",
                                       "staged_manifest", "staged_receipt", "non_v1_proposal", "non_v1_regression"})
        proposal = values["proposal"]["proposal_hash"]
        regression = next(row for row in manifest["artifacts"] if row["kind"] == "regression")
        for kind in ("regression", "simulated_approval", "review_packet", "staged_manifest", "staged_receipt"):
            self.assertEqual(values[kind]["proposal_hash"], proposal)
        for kind in ("simulated_approval", "review_packet", "staged_manifest", "staged_receipt"):
            self.assertEqual(values[kind]["regression_hash"], regression["sha256"])
        self.assertEqual(values["regression"]["execution_id"], manifest["execution_id"])
        self.assertEqual(values["simulated_approval"]["mode"], "simulated")
        self.assertEqual(values["staged_manifest"]["status"], "staged_simulation")
        self.assertEqual(values["staged_receipt"]["release_hash"],
                         next(row["sha256"] for row in manifest["artifacts"] if row["kind"] == "staged_manifest"))
        self.assertEqual(values["non_v1_regression"]["result"], "unavailable")
        self.assertEqual(manifest["non_v1"]["denial_reason"], "regression_unavailable")

    def test_separate_runs_have_unique_execution_identity(self):
        first = self.read_manifest(self.happy_result)
        second = self.read_manifest(self.run_lane(output=self.base / "second"))
        self.assertEqual(first["status"], "passed", first.get("error"))
        self.assertEqual(second["status"], "passed", second.get("error"))
        self.assertNotEqual(first["execution_id"], second["execution_id"])

    def test_optimized_child_cannot_emit_pass(self):
        self.assert_invalid(self.run_lane(extra_python_args=("-O",)), "optimized")

    def test_inherited_optimization_cannot_emit_pass(self):
        self.assert_invalid(self.run_lane(env_changes={"PYTHONOPTIMIZE": "1"}), "optimized")

    def test_existing_output_directory_is_never_overwritten(self):
        output = self.base / "result"
        output.mkdir()
        marker = output / "manifest.json"
        marker.write_bytes(b"existing result")
        result = self.run_lane(output=output)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(marker.read_bytes(), b"existing result")

    def test_child_timeout_emits_invalid_manifest_and_retains_output(self):
        from unittest.mock import patch
        spec = importlib.util.spec_from_file_location("qualifier", SCRIPT)
        qualifier = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(qualifier)
        self.assertIsNotNone(getattr(qualifier, "CHILD_TIMEOUT_SECONDS", None),
                             "fresh-process child has no declared timeout")
        output = self.base / "timeout-result"
        with patch.object(qualifier, "CHILD_TIMEOUT_SECONDS", 0.001), patch.object(
                sys, "argv", [str(SCRIPT), "--output", str(output)]):
            result = qualifier.main()
        self.assertNotEqual(result, 0)
        manifest = json.loads((output / "manifest.json").read_text())
        self.assertEqual(manifest["status"], "invalid")
        self.assertIn("timeout", manifest["error"])
        self.assertTrue((output / "child.stdout.log").is_file())
        self.assertTrue((output / "child.stderr.log").is_file())
        # Separately exercise preservation of bytes supplied by the subprocess boundary.
        partial = self.base / "partial-output"
        expired = subprocess.TimeoutExpired("fixed child", 300, output=b"partial stdout\n", stderr=b"partial stderr\n")
        with patch.object(qualifier.subprocess, "run", side_effect=expired), patch.object(
                sys, "argv", [str(SCRIPT), "--output", str(partial)]):
            self.assertNotEqual(qualifier.main(), 0)
        self.assertEqual((partial / "child.stdout.log").read_bytes(), b"partial stdout\n")
        self.assertEqual((partial / "child.stderr.log").read_bytes(), b"partial stderr\n")
        self.assertEqual(json.loads((partial / "manifest.json").read_text())["status"], "invalid")

    def test_preloaded_pinned_module_is_rejected_even_with_correct_file(self):
        fixed = json.loads((ROOT / "runtime/tests/fixtures/factory-current-registration-v1.json").read_text())
        self.assertEqual(sha256((ROOT / "runtime/src/proofkey/process.py").read_bytes()).hexdigest(),
                         fixed["implementations"]["process.py"])
        code = """import importlib.util, sys, types
from pathlib import Path
spec = importlib.util.spec_from_file_location('qualifier', sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
stale = types.ModuleType('proofkey.process')
stale.__file__ = str(Path(sys.argv[2]) / 'runtime/src/proofkey/process.py')
sys.modules['proofkey.process'] = stale
try:
    module.preflight(Path(sys.argv[2]))
except Exception as error:
    print(error)
    sys.exit(7)
sys.exit(0)
"""
        result = subprocess.run([sys.executable, "-B", "-c", code, str(SCRIPT), str(ROOT)],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertIn("preloaded", result.stdout)

    def test_pinned_disk_drift_is_rejected_before_imports(self):
        root = self.copy_root()
        path = root / "runtime/src/proofkey/process.py"
        path.write_bytes(path.read_bytes() + b"\n# controlled drift\n")
        manifest = self.assert_invalid(self.run_lane(root), "pinned source")
        self.assertEqual(manifest["imports"], {})

    def test_wrong_pinned_module_origin_is_rejected(self):
        root = self.copy_root()
        self.inject(root, "import proofkey.process as bad_origin\nbad_origin.__file__ = '/tmp/foreign-process.py'")
        self.assert_invalid(self.run_lane(root), "origin")

    def test_wrong_selected_helper_origin_is_not_an_external_dependency(self):
        root = self.copy_root()
        self.inject(root, "import test_packet_source as foreign_helper\nforeign_helper.__file__ = '/tmp/foreign-helper.py'")
        self.assert_invalid(self.run_lane(root), "origin")

    def test_replaced_local_helper_module_is_rejected(self):
        root = self.copy_root()
        self.inject(root, """class ReplacementProbe(unittest.TestCase):
    def test_replacement(self):
        import sys, types
        stale = sys.modules['support']
        replacement = types.ModuleType('support')
        replacement.__file__ = stale.__file__
        sys.modules['support'] = replacement
""")
        self.assert_invalid(self.run_lane(root), "identity")

    def test_monkeypatched_pinned_binding_is_rejected(self):
        root = self.copy_root()
        self.inject(root, """class BindingProbe(unittest.TestCase):
    def test_binding(self):
        import proofkey.process as process_module
        process_module.ProcessController = object()
""")
        self.assert_invalid(self.run_lane(root), "binding")

    def test_untracked_local_module_is_in_inventory_and_import_report(self):
        root = self.copy_root()
        helper = root / "runtime/tests/untracked_probe.py"
        helper.write_text("VALUE = 7\n")
        self.inject(root, "import untracked_probe")
        result = self.run_lane(root)
        manifest = self.read_manifest(result)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(manifest["imports"]["after"]["untracked_probe"]["path"],
                         "runtime/tests/untracked_probe.py")
        self.assertIn("runtime/tests/untracked_probe.py", manifest["source_before"])

    def test_file_added_during_execution_invalidates_inventory(self):
        root = self.copy_root()
        self.inject(root, """class AdditionProbe(unittest.TestCase):
    def test_addition(self):
        (ROOT / 'tests/added_during_run.py').write_text('VALUE = 1\\n')
        import importlib
        importlib.import_module('added_during_run')
""")
        self.assert_invalid(self.run_lane(root), "source inventory")

    def test_broader_source_drift_during_execution_invalidates_inventory(self):
        root = self.copy_root()
        self.inject(root, """class DriftProbe(unittest.TestCase):
    def test_drift(self):
        path = ROOT / 'tests/support.py'
        path.write_bytes(path.read_bytes() + b'\\n# drift\\n')
""")
        self.assert_invalid(self.run_lane(root), "source inventory")

    def test_symlink_and_hardlink_aliases_are_rejected(self):
        for alias_kind in ("symlink", "hardlink"):
            with self.subTest(alias_kind=alias_kind):
                root = self.base / alias_kind
                shutil.copytree(ROOT / "runtime", root / "runtime", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
                original = root / "runtime/tests/support.py"
                alias = original.with_name("alias.py")
                if alias_kind == "symlink":
                    alias.symlink_to(original)
                else:
                    os.link(original, alias)
                self.assert_invalid(self.run_lane(root, output=self.base / (alias_kind + "-result")), "alias")

    def test_hardlink_to_source_outside_inventory_is_rejected(self):
        root = self.copy_root()
        inside = root / "runtime/tests/support.py"
        outside = self.base / "external-source.py"
        outside.write_bytes(inside.read_bytes())
        inside.unlink()
        os.link(outside, inside)
        spec = importlib.util.spec_from_file_location("qualifier", SCRIPT)
        qualifier = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(qualifier)
        with self.assertRaisesRegex(ValueError, "alias"):
            qualifier.inventory(root.resolve())

    def test_skipped_test_invalidates_lane(self):
        root = self.copy_root()
        self.inject(root, """class SkipProbe(unittest.TestCase):
    @unittest.skip('controlled skip')
    def test_skip(self):
        pass
""")
        self.assert_invalid(self.run_lane(root), "test accounting")

    def test_omitted_execution_invalidates_lane(self):
        root = self.copy_root()
        self.inject(root, """class OmissionProbe(unittest.TestCase):
    def test_omitted(self):
        pass
    def run(self, result=None):
        return result
""")
        self.assert_invalid(self.run_lane(root), "test accounting")

    def test_duplicate_test_identity_invalidates_lane(self):
        root = self.copy_root()
        self.inject(root, "AliasOfTests = AdaptationFactoryTests")
        self.assert_invalid(self.run_lane(root), "duplicate test")

    def test_failing_test_cannot_emit_pass(self):
        root = self.copy_root()
        self.inject(root, """class FailureProbe(unittest.TestCase):
    def test_failure(self):
        self.fail('controlled failure')
""")
        manifest = self.assert_invalid(self.run_lane(root), "test accounting")
        self.assertTrue(manifest["tests"]["failures"])

    def test_missing_artifact_cannot_remain_valid(self):
        result = self.happy_result
        manifest = self.read_manifest(result)
        output = self.base / "artifact-copy"
        shutil.copytree(result.output, output)
        spec = importlib.util.spec_from_file_location("qualifier", SCRIPT)
        qualifier = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(qualifier)
        (output / manifest["artifacts"][0]["path"]).unlink()
        with self.assertRaisesRegex(Exception, "artifact"):
            qualifier.validate_artifacts(output, manifest["artifacts"])


if __name__ == "__main__":
    unittest.main()
