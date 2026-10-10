"""The optional bridge preserves the runtime's registered source closure."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[3]


class RuntimePackagingTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec("proofkey"),
                         "Requires runtime environment and PYTHONPATH=runtime/src:runtime/tests")
    def test_standalone_runtime_discovery_needs_no_companion_package(self):
        code = '''import sys, unittest
def leaves(suite):
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from leaves(test)
        else:
            yield test
collected = list(leaves(unittest.defaultTestLoader.discover("tests")))
if not collected:
    raise RuntimeError("No standalone runtime tests discovered")
selected = [test for test in collected if type(test).__name__ == "_FailedTest"
            or test.id().endswith(".ShadowBindingTests.test_exact_admitted_binding_and_versions_are_returned_without_writes")]
result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(selected))
print("Standalone runtime test cases discovered:", len(collected))
sys.exit(not result.wasSuccessful())
'''
        result = subprocess.run([sys.executable, "-B", "-c", code], cwd=ROOT / "runtime",
                                env={**os.environ, "PYTHONPATH": "src:tests", "PYTHONDONTWRITEBYTECODE": "1"},
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_optional_bridge_preserves_registered_runtime_source(self):
        spec = importlib.util.spec_from_file_location(
            "bridge_runtime_qualification", ROOT / "runtime/scripts/qualify_factory.py")
        qualification = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(qualification)

        try:
            registration, _ = qualification.current_preflight(ROOT)
        except ValueError as error:
            self.fail("Optional bridge invalidates registered runtime source: " + str(error))

        self.assertEqual(registration["registration_id"], "synthetic-factory-j05-current-v1")


if __name__ == "__main__":
    unittest.main()
