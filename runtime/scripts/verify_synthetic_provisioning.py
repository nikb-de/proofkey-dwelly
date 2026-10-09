"""Offline installed J06 acceptance. Receipts and retained synthetic state are private."""
import argparse
from contextlib import contextmanager
import importlib.util
import platform
import sqlite3
import stat
import traceback
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile
import tempfile
import time
import venv
import zipfile

ROOT = Path(__file__).resolve().parents[2]
RESOURCE_MAP = {
    "proofkey/schema.sql": "src/proofkey/schema.sql",
    **{f"proofkey/resources/profiles/{family}{version}.json": f"profiles/{family}{version}.json"
       for family in ("flat-", "nested-") for version in ("v1", "v1.1", "v1.2", "v1.3", "v1.4")},
    "proofkey/resources/fixtures/packet-world-v1.json": "fixtures/development/packet-world-v1.json",
    "proofkey/resources/fixtures/host-goods-world-v1.json": "fixtures/development/host-goods-world-v1.json",
}


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def environment():
    return {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LANG": "en_US.UTF-8",
            "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
            "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_NO_INDEX": "1",
            "PIP_CONFIG_FILE": os.devnull}


def run(report, label, argv, cwd, *, expected=0, timeout=180):
    started = datetime.now(timezone.utc).isoformat()
    tick = time.monotonic()
    timed_out = False
    try:
        completed = subprocess.run([str(x) for x in argv], cwd=cwd, env=environment(),
                                   capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as error:
        timed_out = True
        completed = subprocess.CompletedProcess(argv, None, error.stdout or b"", error.stderr or b"")
    (report["output_dir"] / (label + ".stdout")).write_bytes(completed.stdout)
    (report["output_dir"] / (label + ".stderr")).write_bytes(completed.stderr)
    report["commands"].append({"label": label, "argv": [str(x) for x in argv],
        "cwd": str(cwd), "started": started, "seconds": time.monotonic() - tick,
        "returncode": completed.returncode, "expected": expected, "timed_out": timed_out,
        "stdout_sha256": sha256(completed.stdout).hexdigest(),
        "stderr_sha256": sha256(completed.stderr).hexdigest()})
    write(report["output_dir"] / "progress.json", serial(report))
    if completed.returncode != expected:
        raise RuntimeError(f"{label}: exit {completed.returncode}, wanted {expected}; "
                           + completed.stderr.decode(errors="replace")[-3000:])
    return completed


def serial(report):
    return {key: str(value) if isinstance(value, Path) else value for key, value in report.items()}


def wheel_payload(path):
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        names = [x.filename for x in infos if not x.is_dir()]
        assert len(names) == len(set(names)), "duplicate wheel member"
        for info in infos:
            parts = PurePosixPath(info.filename).parts
            assert not info.filename.startswith("/") and ".." not in parts
            assert ((info.external_attr >> 16) & 0o170000) != 0o120000, "wheel symlink"
        assert archive.testzip() is None
        return {name: archive.read(name) for name in names}


def inspect_fixed(wheel, sdist, source):
    payload = wheel_payload(wheel)
    expected = {"proofkey/" + str(path.relative_to(source / "src/proofkey")):
                path.read_bytes() for path in (source / "src/proofkey").rglob("*.py")}
    for member, canonical in RESOURCE_MAP.items():
        expected[member] = (source / canonical).read_bytes()
    actual_code = {name: data for name, data in payload.items() if name.startswith("proofkey/")}
    assert actual_code == expected, "wheel source/resource inventory or bytes mismatch"
    metadata_roots = {name.split("/", 1)[0] for name in payload if ".dist-info/" in name}
    assert len(metadata_roots) == 1
    metadata_root = next(iter(metadata_roots))
    allowed_metadata = {f"{metadata_root}/{name}" for name in
                        ("METADATA", "WHEEL", "entry_points.txt", "top_level.txt", "RECORD",
                         "licenses/LICENSE", "licenses/NOTICE")}
    assert set(payload) - set(expected) == allowed_metadata, "unexpected wheel metadata/file"
    assert payload[f"{metadata_root}/licenses/LICENSE"] == (source / "LICENSE").read_bytes()
    assert payload[f"{metadata_root}/licenses/NOTICE"] == (source / "NOTICE").read_bytes()
    with tarfile.open(sdist, "r:gz") as archive:
        members = archive.getmembers()
        names = [x.name for x in members]
        assert len(names) == len(set(names)), "duplicate sdist member"
        prefix = names[0].split("/")[0]
        assert {PurePosixPath(name).parts[0] for name in names} == {prefix}, "multiple sdist roots"
        files = {}
        for member in members:
            assert not member.name.startswith("/") and ".." not in PurePosixPath(member.name).parts
            assert member.isfile() or member.isdir(), "sdist alias/special member"
            if member.isfile():
                assert member.name.startswith(prefix + "/"), "file outside sdist root"
                relative = member.name.removeprefix(prefix + "/")
                assert relative not in files, "duplicate normalized sdist member"
                files[relative] = archive.extractfile(member).read()
    wanted = {"src/" + name: data for name, data in expected.items()}
    top_names = {"LICENSE", "NOTICE", "RIGHTS.md", "README.md", "DEMO.md", "DEPENDENCIES.json",
                 "requirements.lock", "requirements-api.lock", "pyproject.toml", "MANIFEST.in"}
    wanted.update({name: (source / name).read_bytes() for name in top_names})
    generated = {"PKG-INFO", "setup.cfg", "src/proofkey_runtime.egg-info/PKG-INFO",
                 "src/proofkey_runtime.egg-info/SOURCES.txt", "src/proofkey_runtime.egg-info/dependency_links.txt",
                 "src/proofkey_runtime.egg-info/entry_points.txt", "src/proofkey_runtime.egg-info/requires.txt",
                 "src/proofkey_runtime.egg-info/top_level.txt"}
    assert set(files) == set(wanted) | generated, "unexpected/missing sdist files: " + repr(set(files) ^ (set(wanted) | generated))
    for name, data in wanted.items():
        assert files[name] == data, name
    return {"wheel_members": {name: sha256(data).hexdigest() for name, data in payload.items()},
            "sdist_members": {name: sha256(data).hexdigest() for name, data in files.items()},
            "resource_hashes": {name: sha256(expected[name]).hexdigest() for name in RESOURCE_MAP}}



def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def h(value):
    return sha256(canonical(value)).hexdigest()


def strict(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            assert key not in result, "duplicate JSON key"
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def snapshot(root):
    return {str(p.relative_to(root)): digest(p) for p in sorted(root.rglob("*")) if p.is_file()}


@contextmanager
def readonly(path):
    info = path.lstat()
    assert stat.S_ISREG(info.st_mode) and info.st_nlink == 1
    before = (info.st_dev, info.st_ino, info.st_size, digest(path))
    # A live WAL/hot journal prevents this offline acceptance, not an invitation to repair.
    assert not any(Path(str(path) + suffix).exists() for suffix in ("-wal", "-journal"))
    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=1)
    connection.row_factory = sqlite3.Row
    end = time.monotonic() + 5
    connection.set_progress_handler(lambda: int(time.monotonic() > end), 1000)
    try:
        connection.execute("PRAGMA query_only=ON")
        connection.execute("BEGIN")
        yield connection
    finally:
        connection.close()
        after = path.lstat()
        assert before == (after.st_dev, after.st_ino, after.st_size, digest(path)), "readback changed database"


def rows(db, table):
    # Callers supply only fixed internal table names.
    return [dict(row) for row in db.execute("SELECT * FROM " + table)]


def one(db, table):
    result = rows(db, table)
    assert len(result) == 1, (table, len(result))
    return result[0]


def readback(prepared, request, run_receipt, shutdown):
    from proofkey.admission import AdmissionAttempt, AdmissionLease
    from proofkey.admission_routes import RouteRecordV1
    from proofkey.batch_files import read_run_inventory
    from proofkey.contracts import (CanonicalRequest, RequestBinding, PhaseCheckpoint,
        EffectIntent, VerificationResult, SavedResult, AuthorityObservation)
    from proofkey.host_admission import AdmissionClaimV1
    from proofkey.host_files import read_inventory
    from proofkey.host_contracts import InterfaceLimitsV1
    from proofkey.registered_releases import RegisteredReleaseV1
    body = request.model_dump(mode="json")
    assert shutdown.owner_closed and not shutdown.pending_command_ids
    assert run_receipt.command.result.status == "authorized"
    assert run_receipt.export_outcome == "written" and not run_receipt.pending_command_ids
    binding = run_receipt.command.result.binding
    business = h({key: body[key] for key in ("kind", "consent_mode", "arguments")})
    builtin = ("e51bc7df8304c4f88f09e979b60505c20610e2bd13209ac60afd8e9d47a8af34"
               if request.kind == "reschedule_window" else
               "f1a95a447f2a6726a3459f37790557326b3361a15894a7b4a2baa28451321ce2")
    assert business != builtin and binding.fingerprint == business
    assert binding.generation == "G1" and binding.supersedes_generation is None
    for key in ("case_id", "object_id", "principal_id", "request_id", "request_revision", "consent_revision"):
        assert getattr(binding, key) == body[key]
    with readonly(prepared.host_release.resource_root / "journal.sqlite") as db:
        assert one(db, "schema_meta")["version"] == 1
        original = one(db, "original_requests")
        assert (original["case_id"], original["generation"]) == (request.case_id, "G1")
        assert strict(original["request_json"]) == body
        assert CanonicalRequest.model_validate(strict(original["request_json"])) == request
        case = one(db, "cases")
        checkpoint = PhaseCheckpoint.model_validate(strict(case["checkpoint_json"]))
        assert case["case_id"] == request.case_id and checkpoint.binding == binding
        assert (checkpoint.profile_version, checkpoint.process_version, checkpoint.policy_version) == ("v1.3", "v1", "v1")
        saved_request = one(db, "requests")
        assert RequestBinding.model_validate(strict(saved_request["binding_json"])) == binding
        for key in ("case_id", "generation", "request_id", "request_revision", "consent_revision", "fingerprint"):
            assert saved_request[key] == getattr(binding, key)
        result_row = one(db, "results")
        saved = SavedResult.model_validate(strict(result_row["result_json"]))
        assert (result_row["case_id"], result_row["generation"]) == (request.case_id, "G1")
        assert saved.binding == binding and saved.fingerprint == business
        attempt_row = one(db, "admission_attempts")
        attempt = AdmissionAttempt.model_validate(strict(attempt_row["attempt_json"]))
        assert attempt.state == attempt_row["state"] == "transferred"
        assert attempt_row["attempt_id"] == attempt.attempt_id
        assert attempt_row["claimed_case_id"] == attempt.claimed_case_id == request.case_id
        for prefix, key in (("claimed_", "object_id"), ("claimed_", "principal_id"),
                            ("", "request_id"), ("", "request_revision"), ("", "consent_revision")):
            assert getattr(attempt, prefix + key) == body[key]
        assert attempt.business_fingerprint == business and attempt.request_hash == h(body)
        assert attempt_row["dedup_hash"] == attempt.dedup_hash
        for lease_row in rows(db, "admission_entries"):
            lease = AdmissionLease.model_validate(strict(lease_row["lease_json"]))
            assert lease.state == lease_row["state"] != "active"
        intent_rows = rows(db, "intents")
        decoded = {}
        for row in intent_rows:
            intent = EffectIntent.model_validate(strict(row["intent_json"]))
            verification = VerificationResult.model_validate(strict(row["verification_json"]))
            assert intent.operation not in decoded
            assert row["dispatch_state"] == verification.status == "verified"
            assert intent.binding == binding
            assert row["case_id"] == request.case_id and row["generation"] == "G1"
            assert row["action_id"] == intent.action_id == verification.action_id
            assert row["fingerprint"] == intent.argument_fingerprint == verification.fingerprint
            assert verification.object_id == request.object_id
            assert verification.postcondition == intent.postcondition
            assert verification.evidence_refs and verification.as_of is not None
            assert saved.effects[intent.operation] == run_receipt.command.result.effects[intent.operation] == verification
            decoded[intent.operation] = intent
        expected = ({"reschedule"} if request.kind == "reschedule_window"
                    else {"register_goods_refusal", "create_return"})
        assert set(decoded) == set(saved.effects) == set(run_receipt.command.result.effects) == expected
    with readonly(prepared.control_parent / "host-claims.sqlite") as db:
        assert one(db, "meta")["version"] == 1
        claim_row = one(db, "claims")
        AdmissionClaimV1(claim_row["wire"].encode())
        claim = strict(claim_row["wire"])
        for key in ("claim_id", "attempt_id", "state"):
            assert claim_row[key] == claim[key]
        assert claim_row["case_id"] == claim["request"]["case_id"] == request.case_id
        assert claim["state"] == "admission_observed"
    with readonly(prepared.control_parent / "routes.sqlite") as db:
        assert one(db, "meta")["version"] == 1
        release_row = one(db, "releases")
        release = RegisteredReleaseV1(release_row["artifact_json"].encode())
        assert release.artifact_hash == release_row["artifact_hash"] == prepared.binding.artifact_hash
        route_row = one(db, "routes")
        RouteRecordV1(route_row["record_json"].encode())
        route = strict(route_row["record_json"])
        for key in ("reservation_id", "attempt_id", "resource_id", "case_id", "generation", "release_id", "state"):
            assert route_row[key] == route[key]
        assert route["state"] == "admission_observed"
        for key in ("attempt_id", "release_id", "resource_id", "resource_hash", "artifact_hash", "binding", "request", "auth_claim"):
            assert claim[key] == route[key]
        assert route["artifact_hash"] == prepared.binding.artifact_hash
        assert release.wire_bytes == prepared.registry.resolve(prepared.binding.registered_release_id).wire_bytes
        assert route["resource_hash"] == h(strict(release.wire_bytes)["resource"])
        assert route["release_id"] == release_row["release_id"] == prepared.binding.registered_release_id
        assert route["resource_id"] == prepared.registry.resolve(prepared.binding.registered_release_id).resource.resource_id
        assert route["binding"] == binding.model_dump(mode="json") and route["request"] == body
        assert claim["route_id"] == route["reservation_id"]
        assert claim["route_reservation_hash"] == route["reservation_hash"]
        assert claim["observation_hash"] == route["observation"]["observation_hash"]
        assert claim["final_journal_hash"] == route["observation"]["content_hash"]
        assert route["binding_hash"] == h(route["binding"]) and route["request_hash"] == h(body)
        assert route["business_fingerprint"] == business and route["dedup_hash"] == attempt.dedup_hash
        assert route["attempt_id"] == attempt.attempt_id
        assert route["auth_claim"]["caller_id"] == attempt.claimed_caller_id == request.principal_id
        assert route["auth_claim"]["proof_digest"] == attempt.proof_digest == h({"proof_reference": "j06-synthetic-proof"})
    inventory = {"j06-widget": 2, "j06-cable": 1}
    wanted = ({"reschedule": ({"slot": "J06-S3"}, {"slot": "J06-S3"}, {"scheduling.slot": "J06-S3"}, "committed")}
              if request.kind == "reschedule_window" else {
        "register_goods_refusal": ({"inventory": inventory},
            {"inventory": inventory, "quantity": 3, "goods.refusal": "verified"},
            {"goods.inventory": inventory, "goods.quantity": 3, "goods.refusal": "verified"}, "committed"),
        "create_return": ({"inventory": inventory, "destination": "J06-DEPOT-B"},
            {"inventory": inventory, "quantity": 3, "destination": "J06-DEPOT-B", "returns.status": "initiated"},
            {"goods.inventory": inventory, "goods.quantity": 3, "returns.destination": "J06-DEPOT-B", "returns.status": "initiated"}, "initiated")})
    with readonly(prepared.host_release.resource_root / "world.sqlite") as db:
        scope = one(db, "scopes")
        assert all(scope[key] == body[key] for key in ("case_id", "object_id", "principal_id"))
        fact_rows = rows(db, "facts")
        assert all(row["case_id"] == request.case_id and row["object_id"] == request.object_id for row in fact_rows)
        facts = {row["identity"]: strict(row["value"]) for row in fact_rows}
        assert len(facts) == len(fact_rows)
        assert facts["case.binding"] == {key: body[key] for key in ("case_id", "object_id", "principal_id", "request_id")}
        assert facts["case.generation"] == "G1" and facts["customer.request_fingerprint"] == business
        effects = rows(db, "effects")
        assert len(effects) == len(wanted) and {row["operation"] for row in effects} == set(wanted)
        assert not rows(db, "final_rejections") and not rows(db, "reservations")
        assert all(row["active"] == 0 for row in rows(db, "pressure"))
        profile = prepared.host_release.validate()
        for effect in effects:
            intent = decoded[effect["operation"]]
            arguments, postcondition, observations, stage = wanted[intent.operation]
            assert intent.arguments == arguments and intent.postcondition == postcondition
            assert effect["stage"] == stage
            assert effect["provider_key"] == intent.provider_key
            assert effect["account_id"] == profile.capabilities[intent.operation].shared_limits.account_id
            assert effect["case_id"] == request.case_id and effect["object_id"] == request.object_id
            assert effect["generation"] == "G1" and effect["action_id"] == intent.action_id
            assert effect["fingerprint"] == intent.argument_fingerprint
            assert effect["identity_hash"] == h(intent.model_dump(mode="json"))
            assert effect["request_id"] == "provider:" + h({"account": effect["account_id"], "provider_key": effect["provider_key"]})[:24]
            observed = [AuthorityObservation.model_validate(value) for value in strict(effect["observations"])]
            assert all(item.object_id == request.object_id and item.revision and item.evidence_ref for item in observed)
            values = {item.authority + "." + item.fact: item.value for item in observed}
            for key, value in observations.items():
                assert values[key] == facts[key] == value
                if key == "goods.quantity":
                    assert type(values[key]) is type(facts[key]) is int
    run_roots = list(prepared.output_parent.iterdir())
    assert len(run_roots) == 1
    run_root = run_roots[0]
    run_inventory = read_run_inventory(run_root, limits=InterfaceLimitsV1())
    assert run_inventory.status == "committed_snapshot"
    assert run_inventory.run_id == run_receipt.run_id
    assert tuple(run_inventory.joined_command_ids) == (run_receipt.command.command_id,)
    assert not run_inventory.pending_command_ids
    host_rows = [row for folder in prepared.inventory_parent.iterdir() for row in read_inventory(folder)]
    assert [row.phase for row in host_rows] == ["queued", "started", "finished"]
    assert all(row.command_id == run_receipt.command.command_id for row in host_rows)
    assert all(row.execution == run_receipt.command.execution and row.release_id == "J06-H"
               and row.mode == "synthetic_replay" for row in host_rows)
    hashes = dict(run_receipt.export.actual_file_hashes)
    assert set(hashes) == {"ANSWER.md", "REASONING.md"}
    for name, expected_hash in hashes.items():
        assert digest(run_root / "ANSWERS" / request.case_id / name) == expected_hash
    database_inventory = {}
    for root in (prepared.host_release.resource_root, prepared.control_parent):
        for path in sorted(root.glob("*.sqlite")):
            info = path.lstat()
            database_inventory[path.name] = {"device": info.st_dev, "inode": info.st_ino,
                "size": info.st_size, "sha256": digest(path)}
    return {"business_fingerprint": business, "original_request_hash": h(body),
            "database_inventory": database_inventory,
            "effects": {key: 1 for key in wanted}, "export_hashes": hashes,
            "claim_state": claim["state"], "route_state": route["state"], "owner_closed": True,
            "phase": checkpoint.phase, "generation": "G1",
            "logical_snapshot_recomputed": False,
            "snapshot_limit": "Stored claim/route journal hash links checked; final source context was not retained for independent recomputation."}


def load_example(path):
    assert path.is_file(), "external reusable bootstrap is missing"
    spec = importlib.util.spec_from_file_location("j06_external_bootstrap", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert callable(getattr(module, "prepare_case", None)), "external preparation seam is missing"
    assert callable(getattr(module, "execute_case", None)), "external execution seam is missing"
    return module


def check_wrong_proof(prepared, request, receipt):
    """Check the executed denial; kept separate for controlled state fault tests."""
    from proofkey.admission import AdmissionAttempt, AdmissionLease
    from proofkey.host_admission import AdmissionClaimV1
    from proofkey.registered_releases import RegisteredReleaseV1
    shutdown = receipt["shutdown"]
    assert shutdown is not None, "executed denial has no shutdown receipt"
    assert shutdown.owner_closed and shutdown.admission_closed and not shutdown.pending_command_ids
    assert receipt["run"].command.result.status == "denied"
    paths = list(prepared.root.rglob("*.sqlite"))
    assert {path.name for path in paths} == {"host-claims.sqlite", "routes.sqlite", "journal.sqlite", "world.sqlite"}
    assert len(paths) == 4
    counts = {}
    for path in paths:
        with readonly(path) as db:
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            counts[path.name] = {table: db.execute("SELECT count(*) FROM " + table).fetchone()[0]
                                 for table in sorted(tables)}
    body = request.model_dump(mode="json")
    with readonly(prepared.control_parent / "host-claims.sqlite") as db:
        row = one(db, "claims")
        AdmissionClaimV1(row["wire"].encode())
        claim = strict(row["wire"])
        assert row["state"] == claim["state"] == "prepared"
        assert row["case_id"] == request.case_id and claim["request"] == body
        assert row["claim_id"] == claim["claim_id"] and row["attempt_id"] == claim["attempt_id"]
        assert claim["artifact_hash"] == prepared.binding.artifact_hash
    with readonly(prepared.control_parent / "routes.sqlite") as db:
        assert not rows(db, "routes")
        row = one(db, "releases")
        registered = RegisteredReleaseV1(row["artifact_json"].encode())
        assert registered.artifact_hash == row["artifact_hash"] == prepared.binding.artifact_hash
    with readonly(prepared.host_release.resource_root / "journal.sqlite") as db:
        for table in ("cases", "requests", "original_requests", "intents", "results"):
            assert not rows(db, table), "denial advanced into " + table
        row = one(db, "admission_attempts")
        attempt = AdmissionAttempt.model_validate(strict(row["attempt_json"]))
        assert row["state"] == attempt.state == "unbound"
        assert row["attempt_id"] == attempt.attempt_id == claim["attempt_id"]
        assert row["claimed_case_id"] == attempt.claimed_case_id == request.case_id
        assert row["dedup_hash"] == attempt.dedup_hash
        assert attempt.request_hash == h(body)
        assert attempt.business_fingerprint == h({key: body[key] for key in ("kind", "consent_mode", "arguments")})
        assert attempt.claimed_caller_id == claim["auth_claim"]["caller_id"] == request.principal_id
        assert attempt.proof_digest == claim["auth_claim"]["proof_digest"] == h({"proof_reference": "wrong-proof"})
        row = one(db, "admission_entries")
        lease = AdmissionLease.model_validate(strict(row["lease_json"]))
        assert row["state"] == lease.state == "settled"
        assert row["entry_id"] == lease.entry_id
        assert row["attempt_id"] == lease.attempt_id == attempt.attempt_id
        assert row["claimed_case_id"] == lease.claimed_case_id == request.case_id
    with readonly(prepared.host_release.resource_root / "world.sqlite") as db:
        assert not rows(db, "effects") and not rows(db, "reservations")
        assert all(row["active"] == 0 for row in rows(db, "pressure"))
    return counts


def execute_recorded(module, prepared, request, request_path, clock, surface, parent, **options):
    """Record identity before launch and preserve private exceptional close evidence."""
    write(parent / "private-preparation.json", {
        "root": str(prepared.root), "resource": str(prepared.host_release.resource_root),
        "control": str(prepared.control_parent), "artifact": prepared.binding.artifact_hash})
    try:
        receipt = module.execute_case(prepared, request, request_path, clock, surface, **options)
    except BaseException as error:
        shutdown = getattr(error, "_j06_shutdown", None)
        close_error = getattr(error, "_j06_shutdown_error", None)
        evidence = {"error": repr(error), "error_type": type(error).__name__,
            "shutdown": None if shutdown is None else shutdown.model_dump(mode="json"),
            "close_error": None if close_error is None else repr(close_error),
            "owner_closed": bool(shutdown is not None and shutdown.owner_closed
                and shutdown.admission_closed and not shutdown.pending_command_ids)}
        try:
            write(parent / "exception-lifecycle.json", evidence)
        except BaseException as evidence_error:
            error.add_note("Private lifecycle persistence failed: " + repr(evidence_error))
        raise
    write(parent / "execution.json", receipt["public"])
    return receipt


def probe(args):
    import proofkey
    from proofkey.clock import SyntheticReplayClock
    from proofkey.host_admission import AdmissionCompositionFailure
    from proofkey.synthetic_provisioning import SyntheticPreparationFailureV1
    output = Path(args.output)
    output.mkdir(mode=0o700, exist_ok=False)
    module = load_example(Path(args.examples) / "registered_case_bootstrap.py")
    package = Path(proofkey.__file__).resolve().parent
    assert package.is_relative_to(Path(sys.prefix).resolve())
    assert "PYTHONPATH" not in os.environ and sys.flags.isolated and sys.flags.no_user_site
    before = snapshot(package.parent)
    source_before = snapshot(Path(args.examples))
    report = {"candidate": args.commit, "python": sys.executable, "platform": platform.platform(),
              "positions": [], "negatives": [], "status": "started", "module_origins": {}}
    for surface in ("library", "cli"):
        for kind in ("window", "goods"):
            report["positions"].append({"surface": surface, "kind": kind, "status": "not_started"})
    negatives = ("wrong-proof", "wrong-release", "omitted-release", "expired-review", "mismatched-review", "drifted-fixture", "alias-parent")
    report["negatives"] = [{"name": name, "status": "not_started"} for name in negatives]
    try:
        for position in report["positions"]:
            label = position["surface"] + "-" + position["kind"]
            parent = output / label
            parent.mkdir(mode=0o700)
            position.update(status="attempted", parent=str(parent))
            write(output / "progress.json", report)
            try:
                clock = SyntheticReplayClock()
                request_path = Path(args.examples) / "registered-cases" / (position["kind"] + "-request.json")
                fixture_path = request_path.with_name(position["kind"] + "-fixture.json")
                prepared, request = module.prepare_case(request_path, fixture_path, parent, clock)
                fixture_hash = digest(prepared.host_release.fixture_path)
                receipt = execute_recorded(module, prepared, request, request_path, clock,
                                           position["surface"], parent)
                assert receipt["code"] == 0, receipt["public"]
                position.update(readback(prepared, request, receipt["run"], receipt["shutdown"]))
                assert digest(prepared.host_release.fixture_path) == fixture_hash
                position["status"] = "passed"
            except Exception as error:
                position.update(status="failed", error=repr(error))
                (parent / "traceback.txt").write_text(traceback.format_exc())
            write(output / "progress.json", report)
        for negative in report["negatives"]:
            parent = output / ("negative-" + negative["name"])
            parent.mkdir(mode=0o700)
            negative.update(status="attempted", parent=str(parent))
            prepared = None
            try:
                clock = SyntheticReplayClock()
                request_path = Path(args.examples) / "registered-cases/window-request.json"
                fixture_path = request_path.with_name("window-fixture.json")
                if negative["name"] == "alias-parent":
                    target = parent / "target"
                    target.mkdir(mode=0o700)
                    alias = parent / "alias"
                    alias.symlink_to(target, target_is_directory=True)
                    try:
                        module.prepare_case(request_path, fixture_path, alias, clock)
                    except SyntheticPreparationFailureV1 as error:
                        assert error.code == "invalid_target" and not list(target.iterdir())
                        negative.update(status="passed", denial=error.code, database_count=0)
                    else:
                        raise AssertionError("alias accepted")
                    continue
                prepared, request = module.prepare_case(request_path, fixture_path, parent, clock)
                if negative["name"] == "drifted-fixture":
                    with prepared.host_release.fixture_path.open("ab") as stream:
                        stream.write(b"\n")
                try:
                    receipt = execute_recorded(module, prepared, request, request_path, clock,
                        "cli", parent, negative=negative["name"])
                except (AdmissionCompositionFailure, SyntheticPreparationFailureV1) as error:
                    if negative["name"] in ("expired-review", "mismatched-review"):
                        assert type(error) is AdmissionCompositionFailure and error.code == "scope"
                    else:
                        assert negative["name"] == "drifted-fixture"
                        assert type(error) is SyntheticPreparationFailureV1 and error.code == "identity_changed"
                    negative["denial"] = {"type": type(error).__name__, "code": error.code}
                else:
                    write(parent / "execution.json", receipt["public"])
                    assert receipt["code"] != 0
                    if negative["name"] == "wrong-proof":
                        assert receipt["run"].command.result.status == "denied"
                    else:
                        assert negative["name"] in ("wrong-release", "omitted-release")
                        assert receipt["public"]["failure"] == "invalid_input"
                    if receipt["shutdown"] is not None:
                        assert receipt["shutdown"].owner_closed and not receipt["shutdown"].pending_command_ids
                    negative["denial"] = receipt["public"]
                databases = list(prepared.root.rglob("*.sqlite"))
                counts = {}
                if negative["name"] != "wrong-proof":
                    assert not databases
                else:
                    counts = check_wrong_proof(prepared, request, receipt)
                negative.update(status="passed", database_counts=counts)
            except Exception as error:
                negative.update(status="failed", error=repr(error))
                (parent / "traceback.txt").write_text(traceback.format_exc())
            finally:
                write(output / "progress.json", report)
        assert snapshot(package.parent) == before, "installed site-packages changed"
        assert snapshot(Path(args.examples)) == source_before, "original example bytes changed"
        origins = {name: str(Path(value.__file__).resolve()) for name, value in sys.modules.items()
                   if (name == "proofkey" or name.startswith("proofkey.")) and getattr(value, "__file__", None)}
        assert all(Path(path).is_relative_to(package) for path in origins.values())
        report.update(module_origins=origins, site_packages_inventory=before, examples_inventory=source_before,
                      site_packages_unchanged=True, examples_unchanged=True)
        assert all(row["status"] == "passed" for row in report["positions"] + report["negatives"]), "acceptance position failed"
        report["status"] = "passed"
    except Exception as error:
        report.update(status="failed", error=repr(error))
        raise
    finally:
        report["positive_denominator"] = len(report["positions"])
        report["positive_passed"] = sum(row["status"] == "passed" for row in report["positions"])
        report["negative_denominator"] = len(report["negatives"])
        report["negative_passed"] = sum(row["status"] == "passed" for row in report["negatives"])
        write(output / "receipt.json", report)


def build(args):
    evidence = Path(args.output)
    assert evidence.is_absolute() and evidence.resolve() == evidence
    evidence.mkdir(mode=0o700, exist_ok=False)
    scratch = Path(tempfile.mkdtemp(prefix="proofkey-j06-", dir="/private/tmp")).resolve()
    report = {"source_commit": args.commit, "output_dir": evidence, "scratch": scratch,
              "commands": [], "status": "started"}
    try:
        deps = Path(args.wheelhouse).resolve()
        receipt_path = Path(args.dependency_receipt).resolve()
        dependency = strict(receipt_path.read_bytes())
        assert len(dependency["artifacts"]) == 20
        seen = set()
        for item in dependency["artifacts"]:
            path = deps / Path(item["target_path"]).name
            assert path.name not in seen and not path.is_symlink() and path.is_file()
            seen.add(path.name)
            assert digest(path) == item["expected_sha256"], "dependency hash mismatch"
        assert seen == {path.name for path in deps.glob("*.whl")}
        report["dependency_receipt_sha256"] = digest(receipt_path)
        report["dependency_hashes"] = {name: digest(deps / name) for name in sorted(seen)}
        archive = run(report, "git-archive", ["git", "archive", args.commit, "runtime"], ROOT)
        tar_path = scratch / "source.tar"
        tar_path.write_bytes(archive.stdout)
        with tarfile.open(tar_path) as source_archive:
            source_archive.extractall(scratch, filter="data")
        source = scratch / "runtime"
        report["source_archive_sha256"] = digest(tar_path)
        report["source_inventory"] = snapshot(source)
        build_env, installed_env = scratch / "build-env", scratch / "installed-env"
        for label, path in (("build", build_env), ("installed", installed_env)):
            run(report, "venv-" + label, [sys.executable, "-I", "-B", "-m", "venv", path], scratch)
        build_python, installed_python = build_env / "bin/python", installed_env / "bin/python"
        report.update(build_python=str(build_python), installed_python=str(installed_python))
        backend = next(deps.glob("setuptools-*.whl"))
        run(report, "install-backend", [build_python, "-m", "pip", "install", "--no-index", "--no-deps", "--no-compile", backend], scratch)
        artifacts = evidence / "artifacts"
        artifacts.mkdir(mode=0o700)
        for hook in ("build_wheel", "build_sdist"):
            run(report, hook, [build_python, "-B", "-c",
                f"from setuptools.build_meta import {hook}; import sys; {hook}(sys.argv[1])", artifacts], source)
        wheel, sdist = next(artifacts.glob("*.whl")), next(artifacts.glob("*.tar.gz"))
        report["artifacts"] = {path.name: digest(path) for path in (wheel, sdist)}
        report["inventory"] = inspect_fixed(wheel, sdist, source)
        rebuild = scratch / "sdist-rebuild"
        rebuild.mkdir(mode=0o700)
        with tarfile.open(sdist) as source_archive:
            source_archive.extractall(rebuild, filter="data")
        rebuilt_dir = artifacts / "rebuilt"
        rebuilt_dir.mkdir(mode=0o700)
        run(report, "rebuild-sdist", [build_python, "-B", "-c",
            "from setuptools.build_meta import build_wheel; import sys; build_wheel(sys.argv[1])",
            rebuilt_dir], next(rebuild.iterdir()))
        rebuilt = next(rebuilt_dir.glob("*.whl"))
        assert wheel_payload(rebuilt) == wheel_payload(wheel)
        report["rebuilt_wheel_sha256"] = digest(rebuilt)
        run(report, "install-closure", [installed_python, "-m", "pip", "install", "--no-index",
            "--find-links", deps, "--require-hashes", "--no-compile", "-r", source / "requirements-api.lock"], scratch)
        run(report, "install-project", [installed_python, "-m", "pip", "install", "--no-index", "--no-deps", "--no-compile", wheel], scratch)
        run(report, "pip-check", [installed_python, "-m", "pip", "check"], scratch)
        run(report, "installed-probe", [installed_python, "-I", "-B",
            source / "scripts/verify_synthetic_provisioning.py", "--probe",
            "--commit", args.commit, "--output", evidence / "probe",
            "--examples", source / "examples"], scratch, timeout=600)
        report["status"] = "passed"
    except BaseException as error:
        report.update(status="failed", error=repr(error))
        raise
    finally:
        write(evidence / "receipt.json", serial(report))
        print(json.dumps({"status": report["status"], "receipt": str(evidence / "receipt.json")}))


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--wheelhouse")
    parser.add_argument("--dependency-receipt")
    parser.add_argument("--probe", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--examples", help=argparse.SUPPRESS)
    parser.add_argument("--check-example", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.check_example:
        load_example(Path(args.examples) / "registered_case_bootstrap.py")
    elif args.probe:
        probe(args)
    else:
        parser.error("--wheelhouse and --dependency-receipt required") if not args.wheelhouse or not args.dependency_receipt else build(args)


if __name__ == "__main__":
    main()
