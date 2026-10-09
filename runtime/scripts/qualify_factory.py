#!/usr/bin/env python3
"""One fixed, local synthetic factory lane; never a production qualification."""
import argparse
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


INNER_MODULES = ("test_adaptation_factory", "test_factory_registration")
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


def preflight(root):
    """Check only the selected root and its fixed independent registration fixture."""
    if sys.flags.optimize != 0:
        raise ValueError("optimized interpreter is not permitted")
    if any(name in sys.modules for name in PIN_MODULES):
        raise ValueError("preloaded pinned module cannot establish current-source execution")
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


def import_snapshot(root, sources, retained=None):
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
    required = set(PIN_MODULES) | set(INNER_MODULES) | {"proofkey.factory", "proofkey.contracts", "support"}
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
        if relative not in sources or sources[relative] != sha256(path.read_bytes()).hexdigest():
            raise ValueError("module origin is not inventoried source: " + name)
        expected = PIN_MODULES.get(name)
        if expected and relative != "runtime/src/proofkey/" + expected:
            raise ValueError("pinned module origin mismatch: " + name)
        spec_origin = getattr(getattr(module, "__spec__", None), "origin", None)
        if spec_origin and Path(spec_origin).absolute() != path:
            raise ValueError("module spec origin mismatch: " + name)
        bindings = {key: value for key, value in vars(module).items() if not key.startswith("__")} if expected else {}
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
    if "test_factory_qualification" in objects:
        raise ValueError("recursive qualification module loaded")
    return dict(sorted(observed.items())), objects


class RecordedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.executed_ids = []

    def startTest(self, test):
        self.executed_ids.append(test.id())
        super().startTest(test)


def run_inner(modules, report, output):
    # Deliberately do not invoke discovery or module load_tests hooks.
    loader, tests = unittest.TestLoader(), []
    for module in modules:
        for value in vars(module).values():
            if isinstance(value, type) and issubclass(value, unittest.TestCase) and value.__module__ == module.__name__:
                tests.extend(loader.loadTestsFromTestCase(value))
    planned = [test.id() for test in tests]
    report["planned_ids"] = planned
    if not planned or len(planned) != len(set(planned)):
        raise ValueError("empty or duplicate test identity inventory")
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=RecordedResult).run(unittest.TestSuite(tests))
    (output / "tests.log").write_text(stream.getvalue())
    report.update(executed_ids=result.executed_ids,
                  skipped=[(test.id(), reason) for test, reason in result.skipped],
                  expected_failures=[test.id() for test, _ in result.expectedFailures],
                  unexpected_successes=[test.id() for test in result.unexpectedSuccesses],
                  errors=[(test.id(), trace) for test, trace in result.errors],
                  failures=[(test.id(), trace) for test, trace in result.failures])
    if (Counter(planned) != Counter(result.executed_ids) or planned != result.executed_ids or
            result.testsRun != len(planned) or any(report[key] for key in
                ("skipped", "expected_failures", "unexpected_successes", "errors", "failures"))):
        raise ValueError("test accounting failed: every planned test must execute exactly once and pass")


def capture_artifacts(helper, output, execution_id):
    """Execute existing public helpers and preserve their actual canonical bytes."""
    mat = helper.material(helper.supported_candidate())
    proposal = helper.prepared(helper.factory_for(mat), mat)
    regression = helper.evidence(mat, proposal, execution_id=execution_id)
    approval = helper.approval_for(proposal, regression)
    event = helper.HumanReviewEvent(approval.proof_reference, helper.encoded(approval.model_dump(mode="json")),
                                   "human", "synthetic_rehearsal")
    factory = helper.factory_for(mat, regressions=(regression,), reviews=(event,))
    packet = factory.check_proposal(proposal, sha256(regression.receipt).hexdigest())
    stage = factory.release_profile(packet, approval, [])
    if stage.status != "staged_simulation":
        raise ValueError("supported control did not remain staged_simulation")
    candidate = helper.material(helper.candidate_profile())
    candidate_proposal = helper.prepared(helper.factory_for(candidate), candidate)
    candidate_regression = helper.evidence(candidate, candidate_proposal, execution_id=execution_id + "-non-v1")
    if json.loads(candidate_regression.receipt)["result"] != "unavailable":
        raise ValueError("non-v1 candidate did not remain unavailable")
    try:
        helper.factory_for(candidate, regressions=(candidate_regression,)).check_proposal(
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


def validate_artifacts(output, artifacts):
    if {row["kind"] for row in artifacts} != ARTIFACT_KINDS or len(artifacts) != len(ARTIFACT_KINDS):
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
    for kind in ARTIFACT_KINDS - {"non_v1_proposal", "non_v1_regression"}:
        if values[kind]["proposal_hash"] != values["proposal"]["proposal_hash"]:
            raise ValueError("artifact proposal join mismatch: " + kind)
    for kind in ("simulated_approval", "review_packet", "staged_manifest", "staged_receipt"):
        if values[kind]["regression_hash"] != rows["regression"]["sha256"]:
            raise ValueError("artifact regression join mismatch: " + kind)
    stage_hash = rows["staged_manifest"]["sha256"]
    if (values["staged_receipt"]["release_hash"] != stage_hash or
            any(rows[kind]["stage_hash"] != stage_hash for kind in ("staged_manifest", "staged_receipt")) or
            values["non_v1_proposal"]["proposal_hash"] != values["non_v1_regression"]["proposal_hash"]):
        raise ValueError("artifact stage or non-v1 join mismatch")


def blank_manifest():
    return dict(status="invalid", registration=None, python={"executable": sys.executable, "version": sys.version,
                "optimize": sys.flags.optimize}, distributions=[], source_before={}, source_after={},
                source_stable=False, imports={}, tests={}, artifacts=[], limitations=LIMITATIONS)


def child(output):
    manifest = blank_manifest()
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
        registration, before = preflight(root)
        manifest.update(registration=registration, source_before=before,
                        execution_id="synthetic-factory-" + uuid.uuid4().hex)
        manifest["distributions"] = sorted([{"name": dist.metadata["Name"], "version": dist.version,
                    "location": str(dist.locate_file("").resolve())} for dist in importlib.metadata.distributions()],
                    key=lambda row: (row["name"].lower(), row["version"], row["location"]))
        sys.path[:0] = [str(root / "runtime/src"), str(root / "runtime/tests")]
        modules = [importlib.import_module(name) for name in INNER_MODULES]
        # Some adapters are lazy-loaded by SimulatedWorld; retain all six before tests.
        for name in PIN_MODULES:
            importlib.import_module(name)
        observed, retained = import_snapshot(root, before)
        manifest["imports"]["before"] = observed
        run_inner(modules, manifest["tests"], output)
        manifest["artifacts"], manifest["non_v1"] = capture_artifacts(modules[0], output, manifest["execution_id"])
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
                manifest["imports"]["after"], _ = import_snapshot(root, before, retained)
            except Exception as error:
                errors.append(type(error).__name__ + ": " + str(error))
    if manifest["artifacts"]:
        try:
            validate_artifacts(output, manifest["artifacts"])
        except Exception as error:
            errors.append(type(error).__name__ + ": " + str(error))
    if errors:
        manifest["error"] = "; ".join(errors)
    else:
        manifest["status"] = "passed"
    (output / "manifest.json").write_bytes(canonical(manifest))
    return 0 if manifest["status"] == "passed" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    output = parser.parse_args().output
    if not output.is_absolute():
        parser.error("--output must be an absolute new directory")
    if __name__ == "__factory_child__":
        return child(output)
    root = Path(__file__).resolve().parents[2]
    if output.resolve().is_relative_to(root / "runtime"):
        parser.error("--output must be outside the inventoried runtime")
    try:
        output.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        parser.error("--output directory already exists")
    if sys.flags.optimize != 0:
        manifest = blank_manifest()
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
                                     "-c", code, str(Path(__file__).resolve()), "--output", str(output)],
                                    env=env, capture_output=True, timeout=CHILD_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired as error:
            result, timed_out = error, True
    (output / "child.stdout.log").write_bytes(result.stdout or b"")
    (output / "child.stderr.log").write_bytes(result.stderr or b"")
    if timed_out:
        manifest = blank_manifest()
        manifest["error"] = "child timeout after " + str(CHILD_TIMEOUT_SECONDS) + " seconds"
        (output / "manifest.json").write_bytes(canonical(manifest))
        return 1
    if not (output / "manifest.json").is_file():
        manifest = blank_manifest()
        manifest["error"] = "child failed without a manifest; exit=" + str(result.returncode)
        (output / "manifest.json").write_bytes(canonical(manifest))
        return 1
    return result.returncode


if __name__ in {"__main__", "__factory_child__"}:
    sys.exit(main())
