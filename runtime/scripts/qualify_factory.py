#!/usr/bin/env python3
"""One fixed, local synthetic factory lane; never a production qualification."""
import argparse
import ast
from contextlib import redirect_stdout
from collections import Counter
import importlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import sysconfig
import tempfile
import unittest
import uuid
from hashlib import sha256


LEGACY_INNER_MODULES = ('test_adaptation_factory', 'test_factory_registration')
CURRENT_V1_INNER_MODULES = (
    'test_adaptation_factory', 'test_factory_registration', 'test_factory_current_v1')
J05_INNER_MODULES = (
    'test_window_readiness_registration', 'test_window_readiness_envelopes',
    'test_window_readiness_engine', 'test_window_readiness_composition',
    'test_adaptation_factory', 'test_factory_registration', 'test_factory_current_v1',
    'test_observed_stop_v2')
INNER_MODULES = LEGACY_INNER_MODULES
FORBIDDEN_INNER_MODULES = frozenset({
    'test_window_readiness_evidence', 'test_factory_qualification',
    'test_observed_stop_v2_acceptance', 'test_synthetic_provisioning_acceptance'})
CURRENT_LANE = 'current-source-v1-comparison-v1'
_CHILD_ACTIVE = False
CHILD_TIMEOUT_SECONDS = 300  # Execution cutoff only; not an adaptation/drill timing claim.
PIN_MODULES = {
    "proofkey.adapters.operator": "adapters/operator.py",
    "proofkey.adapters.world": "adapters/world.py",
    "proofkey.verifier": "verifier.py",
    "proofkey.packet_contracts": "packet_contracts.py",
    "proofkey.process": "process.py",
    "proofkey.profiles": "profiles.py",
}
ARTIFACT_KINDS = {"proposal", "regression", "simulated_approval", "review_packet",
                  "staged_manifest", "staged_receipt", "non_v1_proposal", "non_v1_regression"}
LIMITATIONS = [
    "Local controlled synthetic evidence only; approval is simulated.",
    "Source and module identity checks cover trusted fixed tests, not hostile-code isolation or invisible transient mutation.",
    "Observed project-local imports and installed distributions are not a complete transitive runtime closure.",
    "No activation, migration, authenticated human review, live agent/provider, new-process dispatch or 600-second drill is established.",
]


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def inventory(root):
    """Include all runtime files, tracked or not, excluding interpreter caches."""
    files, identities = {}, set()
    runtime = root / "runtime"
    for folder, directories, names in os.walk(runtime, followlinks=False):
        for name in directories[:]:
            path = Path(folder) / name
            if path.is_symlink():
                raise ValueError("source alias: " + str(path))
            if name in {"__pycache__", ".pytest_cache"}:
                directories.remove(name)
        for name in sorted(names):
            path = Path(folder) / name
            if path.is_symlink() or path.resolve() != path:
                raise ValueError("source alias: " + str(path))
            if path.suffix in {".pyc", ".pyo"}:
                continue
            info = path.stat()
            identity = (info.st_dev, info.st_ino)
            if not path.is_file() or info.st_nlink > 1 or identity in identities:
                raise ValueError("source alias or non-file: " + str(path))
            identities.add(identity)
            files[path.relative_to(root).as_posix()] = sha256(path.read_bytes()).hexdigest()
    if not files:
        raise ValueError("empty source inventory")
    return dict(sorted(files.items()))


def preflight(root, *, lane='legacy-v1'):
    """Check only the selected root and its fixed independent registration fixture."""
    if sys.flags.optimize != 0:
        raise ValueError("optimized interpreter is not permitted")
    if any(name in sys.modules for name in PIN_MODULES):
        raise ValueError("preloaded pinned module cannot establish current-source execution")
    if lane not in ('legacy-v1', CURRENT_LANE):
        raise ValueError('unknown fixed lane')
    if lane == CURRENT_LANE:
        return current_preflight(root)
    before = inventory(root)
    registration = json.loads((root / "runtime/tests/fixtures/factory-current-registration-v1.json").read_bytes())
    if (registration.get("registration_id") != "synthetic-factory-installed-resources-v1" or
            registration.get("provenance") != "local_controlled_synthetic" or
            set(registration.get("implementations", {})) != set(PIN_MODULES.values())):
        raise ValueError("invalid fixed registration fixture")
    for path, expected in registration["implementations"].items():
        if before.get("runtime/src/proofkey/" + path) != expected:
            raise ValueError("pinned source mismatch: " + path)
    return registration, before



FIXTURE_PATH = 'runtime/tests/fixtures/window-readiness-current-registration-v1.json'
PACKAGE_PATHS = ('__init__.py', 'adapters/__init__.py', 'adapters/case.py', 'adapters/delivery.py', 'adapters/messaging.py', 'adapters/operator.py', 'adapters/ownership.py', 'adapters/returns.py', 'adapters/scheduling.py', 'adapters/world.py', 'admission.py', 'admission_routes.py', 'api.py', 'assessment/__init__.py', 'assessment/audit.py', 'assessment/cache.py', 'assessment/contracts.py', 'assessment/coverage.py', 'assessment/drills.py', 'assessment/driver_contracts.py', 'assessment/drivers.py', 'assessment/isolation.py', 'assessment/labels.py', 'assessment/ledger.py', 'assessment/readiness.py', 'batch.py', 'batch_files.py', 'bootstrap.py', 'budget.py', 'cli.py', 'clock.py', 'contracts.py', 'engine.py', 'evidence/__init__.py', 'evidence/catalog.py', 'evidence/intake.py', 'evidence/processing_contracts.py', 'evidence/redaction.py', 'execution.py', 'execution_consumer.py', 'execution_trace.py', 'exporter.py', 'factory/__init__.py', 'factory/proposal.py', 'factory/release.py', 'factory/views.py', 'gateway.py', 'host.py', 'host_admission.py', 'host_contracts.py', 'host_files.py', 'host_writer.py', 'identity.py', 'journal.py', 'ownership.py', 'ownership_contracts.py', 'ownership_gateway.py', 'ownership_store.py', 'packet_contracts.py', 'packets.py', 'planner.py', 'policy.py', 'ports.py', 'process.py', 'processing.py', 'processing_orchestration.py', 'processing_summary.py', 'profiles.py', 'providers/__init__.py', 'providers/anthropic.py', 'providers/elevenlabs.py', 'providers/invocations.py', 'providers/protocols.py', 'providers/replay.py', 'providers/unavailable.py', 'registered_releases.py', 'release.py', 'replay.py', 'retained_state.py', 'schema.sql', 'source_retained_state.py', 'synthetic_provisioning.py', 'trace.py', 'verifier.py', 'wait_contracts.py', 'waits.py')


def fixed_fixture(root):
    try:
        value = json.loads((root / FIXTURE_PATH).read_bytes())
    except FileNotFoundError as error:
        raise ValueError('fixed fixture unavailable: final J05 freeze pending') from error
    keys = {'registration', 'candidate_file_sha256', 'current_v1_inventory_sha256',
            'current_v1_test_ids', 'j05_test_ids'}
    if type(value) is not dict or set(value) != keys:
        raise ValueError('invalid fixed J05 fixture')
    row = value['registration']
    if (type(row) is not dict or set(row) != {'registration_id', 'provenance', 'host_factory_key',
            'baseline_hash', 'candidate_hash', 'process_hash', 'policy_hash', 'implementations'}
            or row['registration_id'] != 'synthetic-window-readiness-delta-v1'
            or row['provenance'] != 'local_controlled_synthetic'
            or row['host_factory_key'] != 'fixed-synthetic-window-readiness-v3'
            or row['baseline_hash'] != '5bb712b13efaace655ee7180f3d913d93cbd637e3d1685331c6a1eecbade7bf4'):
        raise ValueError('invalid fixed J05 registration')
    pins = row['implementations']
    if (type(pins) is not list or any(type(pair) is not list or len(pair) != 2 for pair in pins)
            or tuple(pair[0] for pair in pins) != PACKAGE_PATHS):
        raise ValueError('invalid fixed package inventory')
    hashes = [pair[1] for pair in pins] + [row[key] for key in
        ('baseline_hash', 'candidate_hash', 'process_hash', 'policy_hash')] + [
        value['candidate_file_sha256'], value['current_v1_inventory_sha256']]
    if any(type(digest) is not str or len(digest) != 64 or
           any(c not in '0123456789abcdef' for c in digest) for digest in hashes):
        raise ValueError('invalid fixed source hash')
    six = [{'path': path, 'sha256': digest} for path, digest in pins if path in PIN_MODULES.values()]
    if len(six) != 6 or sha256(canonical(six)).hexdigest() != value['current_v1_inventory_sha256']:
        raise ValueError('invalid current comparison inventory commitment')
    for key in ('current_v1_test_ids', 'j05_test_ids'):
        ids = value[key]
        allowed = CURRENT_V1_INNER_MODULES if key == 'current_v1_test_ids' else (
            'test_window_readiness_registration', 'test_window_readiness_envelopes',
            'test_window_readiness_engine', 'test_window_readiness_composition',
            *CURRENT_V1_INNER_MODULES, 'test_observed_stop_v2')
        if (type(ids) is not list or not ids or any(type(name) is not str for name in ids)
                or ids != sorted(set(ids)) or any(name.split('.')[0] not in allowed for name in ids)
                or {name.split('.')[0] for name in ids} != set(allowed)):
            raise ValueError('invalid fixed planned test identities')
    return value


def current_preflight(root):
    fixture = fixed_fixture(root)
    before = inventory(root)
    actual = tuple(sorted(path.removeprefix('runtime/src/proofkey/') for path in before
        if path.startswith('runtime/src/proofkey/') and (path.endswith('.py') or path.endswith('/schema.sql'))))
    if actual != PACKAGE_PATHS:
        raise ValueError('package source closure mismatch')
    for path, digest in fixture['registration']['implementations']:
        if before.get('runtime/src/proofkey/' + path) != digest:
            raise ValueError('pinned source mismatch: ' + path)
    for prefix in ('runtime/profiles/', 'runtime/src/proofkey/resources/profiles/'):
        if before.get(prefix + 'flat-window-readiness-v1.json') != fixture['candidate_file_sha256']:
            raise ValueError('candidate resource mismatch')
    for relative, name in (('profiles.py', 'WINDOW_READINESS_IMPLEMENTATION_PATHS'),
                            ('host_admission.py', 'OBSERVED_STOP_V2_IMPLEMENTATION_PATHS')):
        tree = ast.parse((root / 'runtime/src/proofkey' / relative).read_bytes())
        assignment = next((n for n in tree.body if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == name for t in n.targets)), None)
        if (assignment is None or not isinstance(assignment.value, ast.Tuple)
                or not all(isinstance(n, ast.Constant) and type(n.value) is str for n in assignment.value.elts)
                or tuple(n.value for n in assignment.value.elts) != PACKAGE_PATHS):
            raise ValueError('nonliteral package inventory: ' + name)
    registration = {'registration_id': 'synthetic-factory-j05-current-v1',
        'provenance': 'local_controlled_synthetic', 'implementations': {
            path: digest for path, digest in fixture['registration']['implementations']
            if path in PIN_MODULES.values()}}
    return registration, before


def reject_recursive_selection(root, selected):
    # Follow local static imports, including function-local imports, through helpers.
    pending, seen = list(selected), set()
    forbidden = FORBIDDEN_INNER_MODULES | {'qualify_factory', 'qualify_window_readiness'}
    while pending:
        name = pending.pop()
        if name in forbidden:
            raise ValueError('recursive qualification module selected: ' + name)
        if name in seen:
            continue
        seen.add(name)
        path = root / 'runtime/tests' / (name + '.py')
        if not path.is_file():
            continue
        tree = ast.parse(path.read_bytes())
        if name not in selected:
            # Imported helper modules can contain unrelated, unselected TestCases.
            # Their methods are not executable members of this fixed inner suite.
            tree.body = [node for node in tree.body if not (isinstance(node, ast.ClassDef)
                and any((isinstance(base, ast.Attribute) and base.attr == 'TestCase')
                        or (isinstance(base, ast.Name) and base.id == 'TestCase') for base in node.bases))]
        cli_entry_names = {alias.asname or alias.name for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module == 'proofkey.cli'
            for alias in node.names if alias.name == 'main'}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                pending.extend(alias.name.split('.')[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                pending.append(node.module.split('.')[0])
            elif isinstance(node, ast.Call):
                function = node.func
                if ((isinstance(function, ast.Attribute) and isinstance(function.value, ast.Name)
                     and function.value.id in {'subprocess', 'runpy', 'os'}
                     and function.attr in {'run', 'Popen', 'call', 'check_call', 'check_output', 'run_path', 'system'})
                    or (isinstance(function, ast.Name) and function.id in {'main', 'launch', 'run_lane'}
                        and function.id not in cli_entry_names)):
                    raise ValueError('runner launch seam in selected helper: ' + name)


def import_snapshot(root, sources, retained=None, *, modules=LEGACY_INNER_MODULES):
    """Retain module objects, origins and pinned bindings, not just disk hashes."""
    observed, objects = {}, {}
    external_roots = {Path(sysconfig.get_path(key)).resolve() for key in ("purelib", "platlib")}
    local_names = {}
    for relative in sources:
        for prefix in ("runtime/src/", "runtime/tests/"):
            if relative.startswith(prefix) and relative.endswith(".py"):
                parts = relative[len(prefix):-3].split("/")
                if parts[-1] == "__init__":
                    parts.pop()
                local_names[".".join(parts)] = relative
    required = set(PIN_MODULES) | set(modules) | {"proofkey.factory", "proofkey.contracts", "support"}
    observed_paths = {}
    for name, module in list(sys.modules.items()):
        raw = getattr(module, "__file__", None)
        path = Path(raw).absolute() if raw else None
        local = (path is not None and (path.is_relative_to(root) or path.resolve().is_relative_to(root))
                 and not any(path.resolve().is_relative_to(folder) for folder in external_roots))
        if name not in required and name not in local_names and not name.startswith("proofkey.") and not local:
            continue
        if path is None or not path.is_relative_to(root) or path.resolve() != path:
            raise ValueError("module origin outside selected root or aliased: " + name)
        relative = path.relative_to(root).as_posix()
        if name in local_names and relative != local_names[name]:
            raise ValueError("selected local module origin mismatch: " + name)
        if relative in observed_paths and observed_paths[relative] != name:
            raise ValueError('aliased local module: ' + name)
        observed_paths[relative] = name
        if relative not in sources or sources[relative] != sha256(path.read_bytes()).hexdigest():
            raise ValueError("module origin is not inventoried source: " + name)
        expected = PIN_MODULES.get(name)
        if expected and relative != "runtime/src/proofkey/" + expected:
            raise ValueError("pinned module origin mismatch: " + name)
        spec_origin = getattr(getattr(module, "__spec__", None), "origin", None)
        if spec_origin and Path(spec_origin).absolute() != path:
            raise ValueError("module spec origin mismatch: " + name)
        pin_bindings = bool(expected) or (modules != LEGACY_INNER_MODULES and (
            name.startswith('proofkey.') or name in {'support_factory_lanes', 'qualify_factory', 'qualify_window_readiness'}))
        bindings = {key: value for key, value in vars(module).items() if not key.startswith("__")} if pin_bindings else {}
        if retained and name in retained:
            prior_module, prior_path, prior_bindings = retained[name]
            if module is not prior_module or relative != prior_path:
                raise ValueError("module identity changed: " + name)
            if bindings.keys() != prior_bindings.keys() or any(bindings[key] is not value for key, value in prior_bindings.items()):
                raise ValueError("pinned module binding changed: " + name)
        objects[name] = (module, relative, bindings)
        observed[name] = {"path": relative, "sha256": sources[relative], "identity": id(module)}
    if not required <= objects.keys():
        raise ValueError("required local module missing: " + ", ".join(sorted(required - objects.keys())))
    if retained and not retained.keys() <= objects.keys():
        raise ValueError("retained module identity missing")
    if FORBIDDEN_INNER_MODULES.intersection(objects):
        raise ValueError("recursive qualification module loaded")
    return dict(sorted(observed.items())), objects


class RecordedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.executed_ids = []
        self.case_outputs = []
        self._stdout = sys.stdout

    def startTest(self, test):
        self.executed_ids.append(test.id())
        self._output_start = self._stdout.tell()
        super().startTest(test)

    def addSuccess(self, test):
        observed = self._stdout.getvalue()[self._output_start:]
        raw = canonical({'test_id': test.id(), 'outcome': 'passed', 'stdout': observed})
        self.case_outputs.append({'case_id': test.id(), 'output_hash': sha256(raw).hexdigest(),
                                  'raw_utf8': raw.decode('utf-8')})
        super().addSuccess(test)


def require_full_run(planned, executed, result):
    if (not planned or len(planned) != len(set(planned)) or planned != executed
            or result.testsRun != len(planned) or result.skipped or result.expectedFailures
            or result.unexpectedSuccesses or result.failures or result.errors):
        raise ValueError('incomplete_current_source_execution: test accounting failed')


def run_inner(modules, report, output, *, expected_ids=None):
    # Deliberately do not invoke discovery or module load_tests hooks.
    if any(module.__name__ in FORBIDDEN_INNER_MODULES for module in modules):
        raise ValueError('forbidden inner module')
    if expected_ids is not None and any(name.split('.')[0] in FORBIDDEN_INNER_MODULES for name in expected_ids):
        raise ValueError('forbidden planned test identity')
    loader, tests = unittest.TestLoader(), []
    for module in modules:
        for value in vars(module).values():
            if isinstance(value, type) and issubclass(value, unittest.TestCase) and value.__module__ == module.__name__:
                tests.extend(loader.loadTestsFromTestCase(value))
    if expected_ids is not None:
        tests.sort(key=lambda test: test.id())
    planned = [test.id() for test in tests]
    report["planned_ids"] = planned
    if not planned or len(planned) != len(set(planned)):
        raise ValueError("empty or duplicate test identity inventory")
    if expected_ids is not None and planned != expected_ids:
        raise ValueError('planned test identity mismatch')
    stream = io.StringIO()
    observed_stdout = io.StringIO()
    with redirect_stdout(observed_stdout):
        result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=RecordedResult).run(unittest.TestSuite(tests))
    (output / "behavior.stdout.log").write_bytes(observed_stdout.getvalue().encode('utf-8'))
    report["case_outputs"] = result.case_outputs
    (output / "tests.log").write_text(stream.getvalue())
    report.update(executed_ids=result.executed_ids,
                  skipped=[(test.id(), reason) for test, reason in result.skipped],
                  expected_failures=[test.id() for test, _ in result.expectedFailures],
                  unexpected_successes=[test.id() for test in result.unexpectedSuccesses],
                  errors=[(test.id(), trace) for test, trace in result.errors],
                  failures=[(test.id(), trace) for test, trace in result.failures])
    if expected_ids is not None:
        require_full_run(planned, result.executed_ids, result)
    if (Counter(planned) != Counter(result.executed_ids) or planned != result.executed_ids or
            result.testsRun != len(planned) or any(report[key] for key in
                ("skipped", "expected_failures", "unexpected_successes", "errors", "failures"))):
        raise ValueError("test accounting failed: every planned test must execute exactly once and pass")


def capture_artifacts(helper, output, execution_id, *, registration):
    """Execute existing public helpers and preserve their actual canonical bytes."""
    mat = helper.material(helper.supported_candidate())
    proposal = helper.prepared(helper.factory_for(mat, implementation_registration=registration), mat)
    regression = helper.evidence(mat, proposal, execution_id=execution_id)
    approval = helper.approval_for(proposal, regression)
    event = helper.HumanReviewEvent(approval.proof_reference, helper.encoded(approval.model_dump(mode="json")),
                                   "human", "synthetic_rehearsal")
    factory = helper.factory_for(mat, regressions=(regression,), reviews=(event,), implementation_registration=registration)
    packet = factory.check_proposal(proposal, sha256(regression.receipt).hexdigest())
    stage = factory.release_profile(packet, approval, [])
    if stage.status != "staged_simulation":
        raise ValueError("supported control did not remain staged_simulation")
    candidate = helper.material(helper.candidate_profile())
    candidate_proposal = helper.prepared(helper.factory_for(candidate, implementation_registration=registration), candidate)
    candidate_regression = helper.evidence(candidate, candidate_proposal, execution_id=execution_id + "-non-v1")
    if json.loads(candidate_regression.receipt)["result"] != "unavailable":
        raise ValueError("non-v1 candidate did not remain unavailable")
    try:
        helper.factory_for(candidate, regressions=(candidate_regression,), implementation_registration=registration).check_proposal(
            candidate_proposal, sha256(candidate_regression.receipt).hexdigest())
    except helper.FactoryDenied as error:
        if error.reason != "regression_unavailable":
            raise
    else:
        raise ValueError("non-v1 candidate was admitted")
    raws = {"proposal": helper.encoded(proposal.model_dump(mode="json")), "regression": regression.receipt,
            "simulated_approval": helper.encoded(approval.model_dump(mode="json")),
            "review_packet": helper.encoded(packet.model_dump(mode="json")), "staged_manifest": stage.manifest,
            "staged_receipt": stage.receipt_bytes, "non_v1_proposal": helper.encoded(candidate_proposal.model_dump(mode="json")),
            "non_v1_regression": candidate_regression.receipt}
    artifacts = []
    for kind, raw in raws.items():
        value = json.loads(raw)
        if canonical(value) != raw:
            raise ValueError("noncanonical artifact: " + kind)
        path = kind + ".json"
        (output / path).write_bytes(raw)
        artifacts.append({"kind": kind, "path": path, "sha256": sha256(raw).hexdigest(),
                          "proposal_hash": value["proposal_hash"],
                          "regression_execution_id": value.get("execution_id"),
                          "stage_hash": stage.receipt.release_hash if kind.startswith("staged_") else None})
    validate_artifacts(output, artifacts)
    return artifacts, {"result": "unavailable", "denial_reason": "regression_unavailable",
                       "execution_id": execution_id + "-non-v1"}


def validate_artifacts(output, artifacts, *, j05=False):
    required = ARTIFACT_KINDS - {"non_v1_proposal", "non_v1_regression"} if j05 else ARTIFACT_KINDS
    if {row["kind"] for row in artifacts} != required or len(artifacts) != len(required):
        raise ValueError("artifact inventory incomplete or duplicated")
    values, rows = {}, {}
    for row in artifacts:
        path = output / row["path"]
        if path.parent != output or path.is_symlink() or not path.is_file():
            raise ValueError("artifact missing or aliased: " + row["kind"])
        raw = path.read_bytes()
        value = json.loads(raw)
        if sha256(raw).hexdigest() != row["sha256"] or canonical(value) != raw:
            raise ValueError("artifact byte hash mismatch: " + row["kind"])
        if row["proposal_hash"] != value["proposal_hash"] or row["regression_execution_id"] != value.get("execution_id"):
            raise ValueError("artifact metadata join mismatch: " + row["kind"])
        values[row["kind"]], rows[row["kind"]] = value, row
    for kind in required - {"non_v1_proposal", "non_v1_regression"}:
        if values[kind]["proposal_hash"] != values["proposal"]["proposal_hash"]:
            raise ValueError("artifact proposal join mismatch: " + kind)
    for kind in ("simulated_approval", "review_packet", "staged_manifest", "staged_receipt"):
        if values[kind]["regression_hash"] != rows["regression"]["sha256"]:
            raise ValueError("artifact regression join mismatch: " + kind)
    stage_hash = rows["staged_manifest"]["sha256"]
    if (values["staged_receipt"]["release_hash"] != stage_hash or
            any(rows[kind]["stage_hash"] != stage_hash for kind in ("staged_manifest", "staged_receipt")) or
            (not j05 and values["non_v1_proposal"]["proposal_hash"] != values["non_v1_regression"]["proposal_hash"])):
        raise ValueError("artifact stage or non-v1 join mismatch")


def validate_j05_artifacts(output, artifacts):
    validate_artifacts(output, artifacts, j05=True)


def group_case_records(report, expected_ids):
    """Eight receipt groups bind the complete exact per-test denominator."""
    records = report['case_outputs']
    if (not expected_ids or expected_ids != sorted(set(expected_ids))
            or report['planned_ids'] != expected_ids or report['executed_ids'] != expected_ids
            or [row['case_id'] for row in records] != expected_ids
            or any(report.get(key) for key in ('skipped', 'expected_failures', 'unexpected_successes', 'errors', 'failures'))):
        raise ValueError('regression executed output mismatch')
    grouped = {name: [] for name in J05_INNER_MODULES}
    for record in records:
        if set(record) != {'case_id', 'output_hash', 'raw_utf8'}:
            raise ValueError('invalid raw output record')
        raw = record['raw_utf8'].encode('utf-8')
        if sha256(raw).hexdigest() != record['output_hash']:
            raise ValueError('regression raw output hash mismatch')
        value = json.loads(raw)
        if (set(value) != {'test_id', 'outcome', 'stdout'} or value['test_id'] != record['case_id']
                or value['outcome'] != 'passed' or type(value['stdout']) is not str
                or canonical(value) != raw):
            raise ValueError('invalid passed raw output record')
        module = record['case_id'].split('.')[0]
        if module not in grouped:
            raise ValueError('unknown receipt group')
        grouped[module].append(record)
    if any(not rows for rows in grouped.values()):
        raise ValueError('empty receipt group')
    return [{'case_id': 'module:' + name, 'result': 'passed',
             'output_hash': sha256(canonical(rows)).hexdigest()} for name, rows in grouped.items()]


def validate_execution_artifacts(output, artifacts, manifest, *, j05):
    regression = json.loads((output / 'regression.json').read_bytes())
    if regression['execution_id'] != manifest['execution_id']:
        raise ValueError('regression execution identity mismatch')
    if j05:
        expected = group_case_records(manifest['tests'], manifest['tests']['planned_ids'])
        if regression['cases'] != expected:
            raise ValueError('regression executed output mismatch')
        tests = {'required_cases': ['module:' + name for name in J05_INNER_MODULES],
                 'planned_test_ids_sha256': sha256(canonical(manifest['tests']['planned_ids'])).hexdigest()}
        proposal = json.loads((output / 'proposal.json').read_bytes())
        if regression['test_hash'] != sha256(canonical(tests)).hexdigest() or proposal['test_hash'] != regression['test_hash']:
            raise ValueError('regression planned test digest mismatch')


def blank_manifest():
    return dict(status="invalid", registration=None, python={"executable": sys.executable, "version": sys.version,
                "optimize": sys.flags.optimize}, distributions=[], source_before={}, source_after={},
                source_stable=False, imports={}, tests={}, artifacts=[], limitations=LIMITATIONS)


def child(output, *, lane='legacy-v1'):
    selected = LEGACY_INNER_MODULES if lane == 'legacy-v1' else CURRENT_V1_INNER_MODULES
    return _execute_child(output, lane=lane, selected_modules=selected,
                          capture=None, test_ids_key='current_v1_test_ids')


def _execute_child(output, *, lane, selected_modules, capture, test_ids_key):
    global _CHILD_ACTIVE
    if _CHILD_ACTIVE or os.environ.get('_PROOFKEY_QUALIFICATION_CHILD'):
        raise ValueError('nested child entry')
    _CHILD_ACTIVE = True
    os.environ['_PROOFKEY_QUALIFICATION_CHILD'] = '1'
    manifest = blank_manifest()
    if lane == CURRENT_LANE:
        manifest.update(lane='window-readiness-current-source-v1' if capture else lane, role='child')
    root, before, retained, errors = None, None, None, []
    try:
        if sys.flags.optimize != 0:
            raise ValueError("optimized child is not permitted")
        cache = Path(sys._xoptions.get("pycache_prefix", ""))
        if not cache.is_absolute() or not cache.is_dir() or any(cache.iterdir()) or not sys.dont_write_bytecode:
            raise ValueError("empty private cache and disabled bytecode writes required")
        manifest["python"].update(dont_write_bytecode=sys.dont_write_bytecode,
            private_cache_initially_empty=True, pycache_prefix=str(cache), pythonoptimize_present="PYTHONOPTIMIZE" in os.environ)
        root = Path(__file__).resolve().parents[2]
        registration, before = preflight(root, lane=lane)
        manifest.update(registration=registration, source_before=before,
                        execution_id="synthetic-factory-" + uuid.uuid4().hex)
        if lane == CURRENT_LANE:
            fixture = fixed_fixture(root)
            manifest.update(source_registration=fixture['registration'],
                source_fixture_sha256=sha256((root / FIXTURE_PATH).read_bytes()).hexdigest())
            if capture is not None:
                manifest['registration'] = fixture['registration']
        manifest["distributions"] = sorted([{"name": dist.metadata["Name"], "version": dist.version,
                    "location": str(dist.locate_file("").resolve())} for dist in importlib.metadata.distributions()],
                    key=lambda row: (row["name"].lower(), row["version"], row["location"]))
        sys.path[:0] = [str(root / "runtime/src"), str(root / "runtime/tests")]
        reject_recursive_selection(root, selected_modules)
        modules = [importlib.import_module(name) for name in selected_modules]
        # Some adapters are lazy-loaded by SimulatedWorld; retain all six before tests.
        for name in PIN_MODULES:
            importlib.import_module(name)
        if lane == CURRENT_LANE:
            # Settle the fixed bundle's ordinary lazy imports before pinning namespaces.
            for name in ('proofkey.adapters.case', 'proofkey.adapters.delivery',
                         'proofkey.adapters.scheduling', 'proofkey.adapters.returns',
                         'proofkey.adapters.messaging', 'proofkey.adapters.operator'):
                importlib.import_module(name)
        observed, retained = import_snapshot(root, before, modules=selected_modules)
        manifest["imports"]["before"] = observed
        run_inner(modules, manifest["tests"], output,
                  expected_ids=fixture[test_ids_key] if lane == CURRENT_LANE else None)
        if capture is None:
            manifest["artifacts"], manifest["non_v1"] = capture_artifacts(modules[0], output, manifest["execution_id"],
                registration=(importlib.import_module('support_factory_lanes').current_v1_registration()
                              if lane == CURRENT_LANE else modules[0].current_registration()))
        else:
            manifest["artifacts"] = capture(root, fixture, output, manifest)
    except Exception as error:
        errors.append(type(error).__name__ + ": " + str(error))
    # Retain post-execution observations even when the tests themselves fail.
    if before is not None:
        try:
            manifest["source_after"] = inventory(root)
            manifest["source_stable"] = before == manifest["source_after"]
            if not manifest["source_stable"]:
                raise ValueError("source inventory changed during execution")
        except Exception as error:
            errors.append(type(error).__name__ + ": " + str(error))
        if retained is not None:
            try:
                manifest["imports"]["after"], _ = import_snapshot(root, before, retained, modules=selected_modules)
            except Exception as error:
                errors.append(type(error).__name__ + ": " + str(error))
    if manifest["artifacts"]:
        try:
            (validate_artifacts if capture is None else validate_j05_artifacts)(output, manifest["artifacts"])
            validate_execution_artifacts(output, manifest['artifacts'], manifest, j05=capture is not None)
        except Exception as error:
            errors.append(type(error).__name__ + ": " + str(error))
    if errors:
        manifest["error"] = "; ".join(errors)
    else:
        manifest["status"] = "passed"
    (output / "manifest.json").write_bytes(canonical(manifest))
    return 0 if manifest["status"] == "passed" else 1


def main():
    if _CHILD_ACTIVE or os.environ.get('_PROOFKEY_QUALIFICATION_CHILD'):
        raise ValueError('nested launcher entry')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument('--lane', choices=('legacy-v1', CURRENT_LANE), default='legacy-v1')
    args = parser.parse_args()
    output, lane = args.output, args.lane
    if not output.is_absolute():
        parser.error("--output must be an absolute new directory")
    if __name__ == "__factory_child__":
        return child(output, lane=lane)
    root = Path(__file__).resolve().parents[2]
    if output.resolve().is_relative_to(root / "runtime"):
        parser.error("--output must be outside the inventoried runtime")
    try:
        output.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        parser.error("--output directory already exists")
    if sys.flags.optimize != 0:
        manifest = blank_manifest()
        if lane == CURRENT_LANE:
            manifest.update(lane=lane, role="launcher")
        manifest["error"] = "optimized launcher is not permitted"
        (output / "manifest.json").write_bytes(canonical(manifest))
        return 1
    env = dict(os.environ)
    env.pop("PYTHONOPTIMIZE", None)
    env["PYTHONNOUSERSITE"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    timed_out = False
    with tempfile.TemporaryDirectory(prefix="factory-private-pycache-") as directory:
        code = "import runpy,sys; path=sys.argv.pop(1); runpy.run_path(path,run_name='__factory_child__')"
        try:
            result = subprocess.run([sys.executable, "-B", "-s", "-X", "pycache_prefix=" + directory,
                                     "-c", code, str(Path(__file__).resolve()), "--output", str(output), "--lane", lane],
                                    env=env, capture_output=True, timeout=CHILD_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired as error:
            result, timed_out = error, True
    (output / "child.stdout.log").write_bytes(result.stdout or b"")
    (output / "child.stderr.log").write_bytes(result.stderr or b"")
    if timed_out:
        manifest = blank_manifest()
        if lane == CURRENT_LANE:
            manifest.update(lane=lane, role="launcher")
        manifest["error"] = "child timeout after " + str(CHILD_TIMEOUT_SECONDS) + " seconds"
        (output / "manifest.json").write_bytes(canonical(manifest))
        return 1
    if not (output / "manifest.json").is_file():
        manifest = blank_manifest()
        if lane == CURRENT_LANE:
            manifest.update(lane=lane, role="launcher")
        manifest["error"] = "child failed without a manifest; exit=" + str(result.returncode)
        (output / "manifest.json").write_bytes(canonical(manifest))
        return 1
    if lane == CURRENT_LANE:
        manifest = json.loads((output / 'manifest.json').read_bytes())
        manifest['launcher_events'] = [{'role': 'launcher', 'event': 'child_launch', 'count': 1,
                                        'returncode': result.returncode}]
        (output / 'manifest.json').write_bytes(canonical(manifest))
    return result.returncode


if __name__ in {"__main__", "__factory_child__"}:
    sys.exit(main())
