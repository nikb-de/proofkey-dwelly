"""Outer-only J05 qualification rejection tests; never selected by either child."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import types
import unittest

ROOT = Path(__file__).resolve().parents[2]


def runner(name='qualify_factory'):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'runtime/scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WindowReadinessEvidenceTests(unittest.TestCase):
    def capture_unit_timing_records(self, timings):
        # Fabricated unit records exercise capture validation, not qualification.
        from hashlib import sha256
        target = runner('qualify_window_readiness')
        fixture = json.loads((ROOT / 'runtime/tests/fixtures/window-readiness-current-registration-v1.json').read_bytes())
        ids = fixture['j05_test_ids']
        records = []
        for index, test_id in enumerate(ids):
            stdout = ('J05_TIMING ' + json.dumps(timings[index]) + '\n') if index < len(timings) else ''
            raw = target.common.canonical({'test_id': test_id, 'outcome': 'passed', 'stdout': stdout})
            records.append({'case_id': test_id, 'raw_utf8': raw.decode(), 'output_hash': sha256(raw).hexdigest()})
        manifest = {'execution_id': 'unit-timing-validation-only',
            'tests': {'planned_ids': ids, 'executed_ids': ids, 'case_outputs': records}}
        with tempfile.TemporaryDirectory() as directory:
            artifacts = target.capture_artifacts(ROOT, fixture, Path(directory), manifest)
        return artifacts, manifest

    def test_capture_accepts_actual_library_and_configured_cli_timing_emitters(self):
        timings = [{'lane': lane, 'calls': [{'elapsed_seconds': 10}] * 15,
                    'active_seconds': 120, 'host_remaining_seconds': 0.001}
                   for lane in ('library', 'configured_cli')]
        try:
            artifacts, manifest = self.capture_unit_timing_records(timings)
        except ValueError as error:
            self.fail('actual timing emitter identities must pass capture validation: ' + str(error))
        self.assertEqual(len(artifacts), 6)
        self.assertEqual(manifest['measured_fit'], timings)
        self.assertEqual(manifest['executed_test_count'], 156)
        self.assertEqual(manifest['receipt_group_count'], 8)
        self.assertIn('identifier/revision/reason fields <=1024 Unicode code points',
                      manifest['evidence_scope']['raw_domain'])

    def test_capture_rejects_missing_unknown_timing_lanes_and_invalid_fit(self):
        from copy import deepcopy
        valid = [{'lane': lane, 'calls': [{'elapsed_seconds': 10}] * 15,
                  'active_seconds': 120, 'host_remaining_seconds': 0.001}
                 for lane in ('library', 'configured_cli')]
        invalid = [[], valid[:1], valid[1:]]
        for lane in ('cli', 'unknown'):
            changed = deepcopy(valid)
            changed[1]['lane'] = lane
            invalid.append(changed)
        for field, value in (('active_seconds', 120.001), ('host_remaining_seconds', 0)):
            changed = deepcopy(valid)
            changed[0][field] = value
            invalid.append(changed)
        changed = deepcopy(valid)
        changed[1]['calls'][0]['elapsed_seconds'] = 10.001
        invalid.append(changed)
        for count in (14, 16):
            changed = deepcopy(valid)
            changed[1]['calls'] = [{'elapsed_seconds': 10}] * count
            invalid.append(changed)
        for timings in invalid:
            with self.subTest(timings=timings), self.assertRaisesRegex(ValueError, 'unmeasured_or_failed_fit_blocker'):
                self.capture_unit_timing_records(timings)

    def test_factory_body_injection_preserves_test_id_and_executes_valid_code(self):
        import ast
        from test_factory_qualification import FactoryQualificationTests

        source = (ROOT / 'runtime/tests/test_adaptation_factory.py').read_text()
        method = 'test_truthful_capability_leaf_cannot_omit_changed_semantic_siblings'
        def test_ids(raw):
            tree = ast.parse(raw)
            return [f'test_adaptation_factory.{node.name}.{member.name}'
                    for node in tree.body if isinstance(node, ast.ClassDef)
                    for member in node.body if isinstance(member, ast.FunctionDef)
                    and member.name.startswith('test_')]
        before = test_ids(source)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'runtime/tests/test_adaptation_factory.py'
            path.parent.mkdir(parents=True)
            path.write_text(source)
            helper = FactoryQualificationTests('test_default_lane_rejects_changed_current_source')
            helper.inject_body(root, "self.i1_probe = 'injected-body'\nraise RuntimeError(self.i1_probe)")
            changed = path.read_text()
            self.assertEqual(test_ids(changed), before)
            namespace = {'__name__': 'test_adaptation_factory', '__file__': str(path)}
            exec(compile(changed, str(path), 'exec'), namespace)
            case = namespace['AdaptationFactoryTests'](method)
            self.assertEqual(case.id(), 'test_adaptation_factory.AdaptationFactoryTests.' + method)
            with self.assertRaisesRegex(RuntimeError, '^injected-body$'):
                getattr(case, method)()
            self.assertEqual(case.i1_probe, 'injected-body')

    def test_receipt_groups_bind_all_records_without_changing_test_denominator(self):
        from hashlib import sha256
        common = runner()
        records = []
        for module in common.J05_INNER_MODULES:
            for i in range(20):
                test_id = module + '.Probe.test_' + str(i).zfill(3)
                raw = common.canonical({'test_id': test_id, 'outcome': 'passed', 'stdout': ''})
                records.append({'case_id': test_id, 'raw_utf8': raw.decode(), 'output_hash': sha256(raw).hexdigest()})
        records.sort(key=lambda row: row['case_id'])
        expected = [row['case_id'] for row in records]
        report = {'planned_ids': expected, 'executed_ids': expected, 'case_outputs': records}
        grouped = common.group_case_records(report, expected)
        self.assertEqual(len(expected), 160)
        self.assertEqual([row['case_id'] for row in grouped], ['module:' + name for name in common.J05_INNER_MODULES])
        self.assertEqual(report['case_outputs'], records)
        first_group = [row for row in records if row['case_id'].startswith(common.J05_INNER_MODULES[0] + '.')]
        self.assertEqual(grouped[0]['output_hash'], sha256(json.dumps(first_group,
            sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest())
        mutations = [records[:-1], records + [records[-1]], list(reversed(records)),
                     [records[1], records[1], *records[2:]],
                     [{**records[0], 'raw_utf8': '{}'}, *records[1:]]]
        failed_raw = common.canonical({'test_id': expected[0], 'outcome': 'failed', 'stdout': ''})
        mutations.append([{**records[0], 'raw_utf8': failed_raw.decode(),
                           'output_hash': sha256(failed_raw).hexdigest()}, *records[1:]])
        for mutated in mutations:
            with self.subTest(mutated_ids=[row['case_id'] for row in mutated[:2]]):
                with self.assertRaises(ValueError):
                    common.group_case_records({**report, 'case_outputs': mutated}, expected)
        for invalid_expected in (expected[20:], [*expected[:-1], 'unknown.Probe.test_x']):
            with self.assertRaises(ValueError):
                common.group_case_records(report, invalid_expected)
        remaining = [row for row in records if not row['case_id'].startswith(common.J05_INNER_MODULES[0] + '.')]
        ids = [row['case_id'] for row in remaining]
        with self.assertRaisesRegex(ValueError, 'empty receipt group'):
            common.group_case_records({'planned_ids': ids, 'executed_ids': ids, 'case_outputs': remaining}, ids)

    def test_one_launcher_starts_exactly_one_bounded_child(self):
        # Observe real Popen audit events in a separate process; no monkeypatch.
        code = """import importlib.util, json, sys
events = []
sys.addaudithook(lambda event, args: events.append(list(args[1])) if event == 'subprocess.Popen' else None)
spec = importlib.util.spec_from_file_location('qualifier', sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
sys.argv = [sys.argv[1], '--output', sys.argv[2], *sys.argv[3:]]
result = module.main()
print(json.dumps({'events': events, 'result': result}))
"""
        for name, args in (('qualify_factory', ['--lane', 'current-source-v1-comparison-v1']),
                           ('qualify_window_readiness', [])):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / 'result'
                result = subprocess.run([sys.executable, '-B', '-c', code,
                    str(ROOT / 'runtime/scripts' / (name + '.py')), str(output), *args],
                    capture_output=True, text=True, timeout=330)
                self.assertEqual(result.returncode, 0, result.stderr)
                observed = json.loads(result.stdout)
                self.assertEqual(len(observed['events']), 1)
                self.assertIn('-s', observed['events'][0])
                self.assertIn('-B', observed['events'][0])
                manifest = json.loads((output / 'manifest.json').read_bytes())
                self.assertEqual(manifest['role'], 'child')
                self.assertEqual(manifest['launcher_events'][0]['count'], 1)

    def test_child_guard_rejects_launcher_and_child_reentry(self):
        code = """import importlib.util, sys
spec = importlib.util.spec_from_file_location('qualifier', sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
common = getattr(module, 'common', module)
common._CHILD_ACTIVE = True
for call in (module.main, lambda: module.child(None)):
    try:
        call()
    except ValueError as error:
        assert 'nested' in str(error), str(error)
    else:
        raise AssertionError('nested entry accepted')
"""
        for name in ('qualify_factory', 'qualify_window_readiness'):
            result = subprocess.run([sys.executable, '-B', '-c', code,
                str(ROOT / 'runtime/scripts' / (name + '.py'))], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_selected_module_closure_has_no_launcher(self):
        common = runner()
        common.reject_recursive_selection(ROOT, common.CURRENT_V1_INNER_MODULES)
        j05_modules = runner('qualify_window_readiness').INNER_MODULES
        self.assertEqual(common.J05_INNER_MODULES, j05_modules)
        common.reject_recursive_selection(ROOT, j05_modules)

    def test_exact_accounting_rejects_every_incomplete_result(self):
        from types import SimpleNamespace
        complete = dict(testsRun=1, skipped=[], expectedFailures=[], unexpectedSuccesses=[], failures=[], errors=[])
        target = runner()
        target.require_full_run(['a'], ['a'], SimpleNamespace(**complete))
        variants = [([], [], complete), (['a', 'a'], ['a', 'a'], {**complete, 'testsRun': 2}),
                    (['a', 'b'], ['b', 'a'], {**complete, 'testsRun': 2}), (['a'], [], complete)]
        variants.extend((['a'], ['a'], {**complete, name: ['observed']}) for name in
                        ('skipped', 'expectedFailures', 'unexpectedSuccesses', 'failures', 'errors'))
        for planned, executed, result in variants:
            with self.subTest(result=result), self.assertRaisesRegex(ValueError, 'incomplete_current_source_execution'):
                target.require_full_run(planned, executed, SimpleNamespace(**result))

    def test_closed_current_lane_rejects_missing_reviewed_fixture(self):
        # A missing fixture must stop before importing any behavioral module.
        with tempfile.TemporaryDirectory() as directory:
            code = """import importlib.util, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location('qualifier', sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
try:
    module.preflight(Path(sys.argv[2]), lane='current-source-v1-comparison-v1')
except ValueError as error:
    print(error)
    sys.exit(7)
"""
            result = subprocess.run([sys.executable, '-B', '-c', code,
                str(ROOT / 'runtime/scripts/qualify_factory.py'), directory], capture_output=True, text=True)
            self.assertEqual(result.returncode, 7, result.stderr)
            self.assertIn('fixed fixture unavailable', result.stdout)

    def test_unknown_lane_rejected_before_execution(self):
        for value in ('test_factory_qualification', '../../pins.json'):
            with tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / 'result'
                result = subprocess.run([sys.executable, '-B', str(ROOT / 'runtime/scripts/qualify_factory.py'),
                    '--lane', value, '--output', str(output)], capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(output.exists())

    def test_fixed_id_selection_rejects_added_test_before_execution(self):
        module = types.ModuleType('synthetic_inner')
        class Probe(unittest.TestCase):
            def test_expected(self):
                self.fail('selection must reject before executing')
        Probe.__module__ = module.__name__
        module.Probe = Probe
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'planned test identity mismatch'):
                runner().run_inner([module], {}, Path(directory), expected_ids=['synthetic_inner.Other.test_expected'])

    def test_sorted_selection_ignores_load_tests_and_records_real_output(self):
        module = types.ModuleType('synthetic_inner')
        def alpha(self):
            print('observed alpha')
        def zeta(self):
            print('observed zeta')
        module.Probe = type('Probe', (unittest.TestCase,), {
            '__module__': module.__name__, 'test_zeta': zeta, 'test_alpha': alpha})
        module.load_tests = lambda *args: self.fail('load_tests must never be invoked')
        expected = ['synthetic_inner.Probe.test_alpha', 'synthetic_inner.Probe.test_zeta']
        report = {}
        with tempfile.TemporaryDirectory() as directory:
            runner().run_inner([module], report, Path(directory), expected_ids=expected)
        self.assertEqual(report['planned_ids'], expected)
        self.assertEqual(report['executed_ids'], expected)
        self.assertEqual(json.loads(report['case_outputs'][0]['raw_utf8'])['stdout'], 'observed alpha\n')

    def test_j05_selection_rejects_outer_modules(self):
        module = types.ModuleType('test_factory_qualification')
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'forbidden inner module'):
                runner('qualify_window_readiness').run_inner([module], {}, Path(directory), expected_ids=[])

    def test_independent_closed_literal_inventory(self):
        import ast
        import proofkey
        from proofkey.profiles import WINDOW_READINESS_IMPLEMENTATION_PATHS
        from proofkey.host_admission import OBSERVED_STOP_V2_IMPLEMENTATION_PATHS
        package = Path(proofkey.__file__).resolve().parent
        discovered = tuple(sorted(str(p.relative_to(package)) for p in package.rglob('*')
            if p.is_file() and (p.suffix == '.py' or p.name == 'schema.sql')))
        self.assertEqual(len(WINDOW_READINESS_IMPLEMENTATION_PATHS), 86)
        self.assertEqual(WINDOW_READINESS_IMPLEMENTATION_PATHS, discovered)
        self.assertEqual(OBSERVED_STOP_V2_IMPLEMENTATION_PATHS, discovered)
        tree = ast.parse((package / 'profiles.py').read_text())
        assignment = next(n for n in tree.body if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == 'WINDOW_READINESS_IMPLEMENTATION_PATHS' for t in n.targets))
        self.assertIsInstance(assignment.value, ast.Tuple)
        self.assertTrue(all(isinstance(n, ast.Constant) and type(n.value) is str for n in assignment.value.elts))


class WindowReadinessRunnerTests(unittest.TestCase):
    """Every hostile copied root is gated by one successful untouched fixed lane."""
    @classmethod
    def launch(cls, root, output, *, extra=()):
        result = subprocess.run([sys.executable, '-B', *extra,
            str(root / 'runtime/scripts/qualify_window_readiness.py'), '--output', str(output)],
            env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1'},
            capture_output=True, text=True, timeout=330)
        result.output = output
        return result

    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='j05-outer-test-')
        self.addCleanup(directory.cleanup)
        self.base = Path(directory.name)

    @property
    def happy_result(self):
        cls = type(self)
        if '_happy' not in cls.__dict__:
            directory = tempfile.TemporaryDirectory(prefix='j05-outer-control-')
            cls.addClassCleanup(directory.cleanup)
            cls._happy = cls.launch(ROOT, Path(directory.name) / 'result')
        return cls._happy

    def manifest(self, result):
        return json.loads((result.output / 'manifest.json').read_bytes())

    def copy_root(self):
        result = self.happy_result
        self.assertEqual(result.returncode, 0, self.manifest(result).get('error'))
        root = self.base / 'checkout'
        shutil.copytree(ROOT / 'runtime', root / 'runtime',
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        return root

    def inject(self, root, text, *, body=True):
        path = root / 'runtime/tests/test_window_readiness_registration.py'
        old = path.read_text()
        if body:
            marker = '    def test_exact_candidate_and_only_two_affected_contracts(self):\n'
            self.assertIn(marker, old)
            new = old.replace(marker, marker + ''.join('        ' + line + '\n' for line in text.splitlines()), 1)
        else:
            new = old + '\n' + text + '\n'
        path.write_text(new)

    def denied(self, root, reason):
        result = self.launch(root, self.base / 'result')
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        manifest = self.manifest(result)
        self.assertEqual(manifest['status'], 'invalid')
        self.assertIn(reason, manifest['error'])
        return manifest

    def test_exact_j05_execution_and_bound_artifacts(self):
        result = self.happy_result
        manifest = self.manifest(result)
        self.assertEqual(result.returncode, 0, manifest.get('error'))
        from support_factory_lanes import fixed_current_fixture
        self.assertEqual(manifest['tests']['planned_ids'], fixed_current_fixture()['j05_test_ids'])
        self.assertEqual(manifest['tests']['executed_ids'], manifest['tests']['planned_ids'])
        common = runner()
        common.validate_j05_artifacts(result.output, manifest['artifacts'])
        common.validate_execution_artifacts(result.output, manifest['artifacts'], manifest, j05=True)
        self.assertEqual(manifest['source_before'], manifest['source_after'])
        self.assertEqual(manifest['evidence_scope']['historical_pending_preservation'], 'unqualified')
        self.assertEqual(manifest['role'], 'child')
        self.assertEqual(manifest['registration']['registration_id'], 'synthetic-window-readiness-delta-v1')
        self.assertEqual(manifest['executed_test_count'], len(manifest['tests']['executed_ids']))
        self.assertEqual(manifest['receipt_group_count'], 8)

    def test_pinned_source_drift_rejected_before_import(self):
        root = self.copy_root()
        path = root / 'runtime/src/proofkey/gateway.py'
        path.write_bytes(path.read_bytes() + b'\n# controlled drift\n')
        self.assertEqual(self.denied(root, 'pinned source mismatch')['imports'], {})

    def test_added_package_module_is_rejected(self):
        root = self.copy_root()
        (root / 'runtime/src/proofkey/extra.py').write_text('VALUE = 1\n')
        self.denied(root, 'package source closure')

    def test_forbidden_helper_import_rejected_before_behavior(self):
        root = self.copy_root()
        self.inject(root, 'import test_factory_qualification', body=False)
        self.assertEqual(self.denied(root, 'recursive qualification module')['tests'], {})

    def test_wrong_import_origin(self):
        root = self.copy_root()
        self.inject(root, "import proofkey.process\nproofkey.process.__file__ = '/tmp/not-this-source.py'", body=False)
        self.denied(root, 'origin')

    def test_hash_binding_mutation_is_rejected(self):
        root = self.copy_root()
        self.inject(root, "import proofkey.identity\nproofkey.identity.fingerprint = lambda value: '0' * 64")
        self.denied(root, 'binding')

    def test_registration_helper_mutation_is_rejected(self):
        root = self.copy_root()
        self.inject(root, 'import support_factory_lanes\nsupport_factory_lanes.current_v1_registration = lambda: None')
        self.denied(root, 'binding')

    def test_skipped_required_test_is_rejected(self):
        root = self.copy_root()
        self.inject(root, "self.skipTest('controlled skip')")
        self.denied(root, 'incomplete_current_source_execution')

    def test_failing_required_test_is_rejected(self):
        root = self.copy_root()
        self.inject(root, "self.fail('controlled failure')")
        self.denied(root, 'incomplete_current_source_execution')

    def test_expected_failure_does_not_qualify(self):
        root = self.copy_root()
        self.inject(root, "self.fail('expected failure')")
        self.inject(root, 'ProfileDeltaTests.test_exact_candidate_and_only_two_affected_contracts = unittest.expectedFailure(ProfileDeltaTests.test_exact_candidate_and_only_two_affected_contracts)', body=False)
        self.denied(root, 'incomplete_current_source_execution')

    def test_reordered_selection_is_rejected(self):
        root = self.copy_root()
        path = root / 'runtime/scripts/qualify_factory.py'
        old = path.read_text()
        new = old.replace('tests.sort(key=lambda test: test.id())', 'tests.sort(key=lambda test: test.id(), reverse=True)')
        self.assertNotEqual(old, new)
        path.write_text(new)
        self.denied(root, 'planned test identity mismatch')

    def test_receipt_execution_mutation_is_rejected(self):
        root = self.copy_root()
        path = root / 'runtime/scripts/qualify_window_readiness.py'
        old = path.read_text()
        new = old.replace("execution_id=manifest['execution_id']", "execution_id='wrong-execution'")
        self.assertNotEqual(old, new)
        path.write_text(new)
        self.denied(root, 'regression execution identity mismatch')

    def test_missing_artifact_is_rejected(self):
        control = self.happy_result
        self.assertEqual(control.returncode, 0, self.manifest(control).get('error'))
        output = self.base / 'copy'
        shutil.copytree(control.output, output)
        artifacts = self.manifest(control)['artifacts']
        (output / artifacts[0]['path']).unlink()
        with self.assertRaisesRegex(ValueError, 'artifact'):
            runner().validate_j05_artifacts(output, artifacts)

    def test_omitted_required_execution_is_rejected(self):
        root = self.copy_root()
        self.inject(root, """_original_run = ProfileDeltaTests.run
def omitted(self, result=None):
    if self._testMethodName == 'test_exact_candidate_and_only_two_affected_contracts':
        return result
    return _original_run(self, result)
ProfileDeltaTests.run = omitted""", body=False)
        self.denied(root, 'incomplete_current_source_execution')

    def test_duplicate_identity_is_rejected(self):
        root = self.copy_root()
        self.inject(root, 'SecondName = ProfileDeltaTests', body=False)
        self.denied(root, 'duplicate test')

    def test_added_test_is_rejected_before_execution(self):
        root = self.copy_root()
        self.inject(root, """class AddedCase(unittest.TestCase):
    def test_extra(self):
        self.fail('must not execute')""", body=False)
        self.denied(root, 'planned test identity mismatch')

    def test_source_drift_during_execution_is_rejected(self):
        root = self.copy_root()
        self.inject(root, "from pathlib import Path\np = Path(__file__).with_name('support.py')\np.write_bytes(p.read_bytes() + b'\\n# drift\\n')")
        self.denied(root, 'source inventory changed')

    def test_untracked_executing_helper_is_inventoried(self):
        root = self.copy_root()
        (root / 'runtime/tests/j05_extra_helper.py').write_text('VALUE = 1\n')
        self.inject(root, 'import j05_extra_helper', body=False)
        result = self.launch(root, self.base / 'result')
        self.assertEqual(result.returncode, 0, self.manifest(result).get('error'))
        self.assertIn('j05_extra_helper', self.manifest(result)['imports']['after'])

    def test_optimized_launcher_rejected(self):
        control = self.happy_result
        self.assertEqual(control.returncode, 0, self.manifest(control).get('error'))
        result = self.launch(ROOT, self.base / 'result', extra=('-O',))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('optimized', self.manifest(result)['error'])

    def test_existing_output_is_not_overwritten(self):
        control = self.happy_result
        self.assertEqual(control.returncode, 0, self.manifest(control).get('error'))
        output = self.base / 'result'
        output.mkdir()
        marker = output / 'marker'
        marker.write_text('retained')
        self.assertNotEqual(self.launch(ROOT, output).returncode, 0)
        self.assertEqual(marker.read_text(), 'retained')
