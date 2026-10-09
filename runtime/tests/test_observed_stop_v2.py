"""Closed v2 provisioning contract; control behavior is tested separately."""
import base64
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import proofkey
from proofkey import host_admission
from proofkey.host import RuntimeFactory
from proofkey.host_admission import FIXED_IMPLEMENTATION_PATHS
from proofkey.synthetic_provisioning import (
    SyntheticCaseReleaseSpecV1, SyntheticPreparationFailureV1, prepare_synthetic_release)
from support_observed_stop_v2 import prepared_case
from support_synthetic_provisioning import case_data, cj, context
from test_host_admission import paced_clock


class ObservedStopV2InventoryTests(unittest.TestCase):
    def test_new_factory_uses_exact_existing_schema(self):
        with prepared_case() as fx:
            value = json.loads(fx.prepared.registry.resolve('J07-L').wire_bytes)
            dependency = json.loads(base64.b64decode(value['blobs']['dependency']['base64']))
            self.assertEqual(value['version'], 1)
            self.assertEqual(value['factory']['factory_id'], 'fixed-synthetic-observed-stop-v2')
            self.assertEqual(fx.prepared.binding.host_factory_key, 'fixed-synthetic-observed-stop-v2')
            self.assertEqual(dependency['completeness'], 'unestablished')
            observed = tuple(item['name'] for item in dependency['entries'])
            self.assertEqual(observed, host_admission.OBSERVED_STOP_V2_IMPLEMENTATION_PATHS)
            self.assertIn('clock.py', observed)
            self.assertIn('waits.py', observed)
            self.assertIn('execution_trace.py', observed)
            self.assertEqual([(e['name'], e['sha256']) for e in dependency['entries']],
                [(e['name'], e['sha256']) for e in value['implementations']])
            self.assertEqual({e['name']: e['role'] for e in dependency['entries']},
                {name: 'data' if name == 'schema.sql' else 'code' for name in observed})
            for item in value['implementations']:
                self.assertEqual(sha256(base64.b64decode(item['base64'])).hexdigest(), item['sha256'])

    def test_factory_and_inventory_cannot_be_mixed(self):
        with prepared_case() as fx:
            binding = fx.prepared.binding
            pins = binding.implementation_pins
            old_pins = tuple(pair for pair in pins if pair[0] in FIXED_IMPLEMENTATION_PATHS)
            for update in (
                {'implementation_pins': old_pins},
                {'implementation_pins': tuple(reversed(pins))},
                {'implementation_pins': pins[:-1]},
                {'implementation_pins': pins + (pins[-1],)},
                {'factory_id': 'unknown', 'host_factory_key': 'unknown'},
                {'host_factory_key': 'fixed-synthetic-v1'},
            ):
                with self.subTest(update=update), self.assertRaises(ValueError):
                    replace(binding, **update)

    def test_default_preparation_preserves_v1_factory_and_inventory(self):
        with TemporaryDirectory() as folder, paced_clock() as (clock, _):
            parent = Path(folder).resolve()
            parent.chmod(0o700)
            request, source = case_data()
            prepared = prepare_synthetic_release(
                SyntheticCaseReleaseSpecV1('J07-H', 'J07-L', 'J07-R', request, cj(source)),
                parent=parent, clock=clock, execution=context(clock))
            self.assertEqual(prepared.binding.factory_id, 'fixed-synthetic-v1')
            self.assertEqual(prepared.binding.host_factory_key, 'fixed-synthetic-v1')
            self.assertEqual(tuple(name for name, _ in prepared.binding.implementation_pins),
                             FIXED_IMPLEMENTATION_PATHS)

    def test_binding_rejects_nonexact_factory_key_types(self):
        class EqualKey:
            def __eq__(self, other):
                return other == 'fixed-synthetic-observed-stop-v2'

        class StringKey(str):
            def __eq__(self, other):
                return str(self) == other

        with prepared_case() as fx:
            for key in (EqualKey(), StringKey('fixed-synthetic-observed-stop-v2')):
                with self.subTest(key_type=type(key).__name__):
                    with self.assertRaises(host_admission.AdmissionCompositionFailure) as caught:
                        replace(fx.prepared.binding, host_factory_key=key)
                    self.assertEqual(caught.exception.code, 'unsupported_release')

    def test_unknown_factory_rejected_before_child_allocation(self):
        with TemporaryDirectory() as folder, paced_clock() as (clock, _):
            parent = Path(folder).resolve()
            parent.chmod(0o700)
            request, source = case_data()
            spec = SyntheticCaseReleaseSpecV1('J07-H', 'J07-L', 'J07-R', request, cj(source))
            with self.assertRaises(SyntheticPreparationFailureV1) as caught:
                prepare_synthetic_release(spec, parent=parent, clock=clock,
                    execution=context(clock), factory_key='unknown')
            self.assertEqual(caught.exception.code, 'invalid_input')
            self.assertEqual(tuple(parent.iterdir()), ())

    def test_reviewed_v2_inventory_covers_all_first_party_source(self):
        package = Path(proofkey.__file__).parent
        installed = {path.relative_to(package).as_posix()
                     for path in package.rglob('*.py')}
        installed.add('schema.sql')
        names = host_admission.OBSERVED_STOP_V2_IMPLEMENTATION_PATHS
        self.assertEqual(set(names), installed)
        self.assertEqual(names, tuple(sorted(set(names))))

    def test_v2_preparation_opens_with_its_exact_pins(self):
        with prepared_case() as fx:
            resources = RuntimeFactory().create_registered(fx.prepared.host_release,
                fx.clock, composition=fx.composition, execution=context(fx.clock))
            try:
                self.assertFalse(resources.closed)
            finally:
                resources.close()
            self.assertTrue(resources.closed)


if __name__ == '__main__':
    unittest.main()
