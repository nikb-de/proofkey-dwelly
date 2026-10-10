"""The optional bridge preserves the runtime's registered source closure."""
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]


class RuntimePackagingTests(unittest.TestCase):
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
