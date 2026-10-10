"""Bounded read-only validation of existing service-owned experiment evidence.

This module imports draft validators, never the operational runtime. It does not
open JobStore, invoke providers, or create files in the source tree.
"""
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from hashlib import sha256
import math
import os
from pathlib import Path
import re
import sqlite3
import stat

from tools.dwelly_cases import baseline, runner as cases
from tools.dwelly_cases.importer import digest
from tools.dwelly_model import runner as models, semantic


MAX_JSON_BYTES = 4 * 1024 * 1024
MAX_CASES = 50
_CASE = re.compile(r"delivery-logistics-[0-9]{3}")
_JOB = re.compile(r"[a-f0-9]{32}")
_ERRORS = frozenset({"source_invalid", "source_identity_invalid", "source_path_unsafe",
                     "source_too_large", "source_incomplete", "source_case_missing",
                     "source_version_unsupported", "source_linkage_invalid"})


class ShadowError(ValueError):
    """A bounded error code only; never include source text or exception details."""

    def __init__(self, code="source_invalid"):
        self.code = code if type(code) is str and code in _ERRORS else "source_invalid"
        super().__init__(self.code)


@dataclass(frozen=True)
class SourceRecord:
    job_id: str
    case_id: str
    snapshot_hash: str
    proposal_hash: str
    receipt_hash: str | None
    source_hash: str
    provenance: str
    source_mode: str
    verifier_version: str

    def summary(self):
        return asdict(self)


def _require(condition, code="source_invalid"):
    if not condition:
        raise ShadowError(code)


def _finite(value):
    """strict_json rejects NaN tokens; also reject overflow such as 1e999."""
    if type(value) is float:
        _require(math.isfinite(value))
    elif type(value) is dict:
        for item in value.values():
            _finite(item)
    elif type(value) is list:
        for item in value:
            _finite(item)


def _json(raw):
    value = cases.strict_json(raw)
    _finite(value)
    return value


def _owned(info, *, directory=False):
    _require((stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
             and info.st_uid == os.getuid() and not info.st_mode & 0o022,
             "source_path_unsafe")


class _SourceFiles:
    """Open every component without following links; retain raw byte identities."""

    def __init__(self, root):
        path = Path(root).absolute()
        _require(".." not in path.parts, "source_path_unsafe")
        self.path = path
        self.hashes = {}
        descriptor = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            for component in path.parts[1:]:
                child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                dir_fd=descriptor)
                os.close(descriptor)
                descriptor = child
            _owned(os.fstat(descriptor), directory=True)
        except BaseException:
            os.close(descriptor)
            raise
        self.descriptor = descriptor

    def close(self):
        os.close(self.descriptor)

    @contextmanager
    def open(self, relative, *, directory=False):
        parts = Path(relative).parts
        _require(parts and not Path(relative).is_absolute() and ".." not in parts,
                 "source_path_unsafe")
        parent = os.dup(self.descriptor)
        child = None
        try:
            for component in parts[:-1]:
                child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                dir_fd=parent)
                _owned(os.fstat(child), directory=True)
                os.close(parent)
                parent, child = child, None
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
            if directory:
                flags |= os.O_DIRECTORY
            child = os.open(parts[-1], flags, dir_fd=parent)
            _owned(os.fstat(child), directory=directory)
            yield child
        finally:
            if child is not None:
                os.close(child)
            os.close(parent)

    def json(self, relative):
        with self.open(relative) as descriptor:
            _require(os.fstat(descriptor).st_size <= MAX_JSON_BYTES, "source_too_large")
            chunks, size = [], 0
            while True:
                chunk = os.read(descriptor, min(65536, MAX_JSON_BYTES + 1 - size))
                if not chunk:
                    break
                size += len(chunk)
                _require(size <= MAX_JSON_BYTES, "source_too_large")
                chunks.append(chunk)
            raw = b"".join(chunks)
        self.hashes[relative] = sha256(raw).hexdigest()
        return _json(raw)

    def case_ids(self, relative):
        names = []
        with self.open(relative, directory=True) as descriptor:
            with os.scandir(descriptor) as entries:
                for entry in entries:
                    _require(len(names) < MAX_CASES, "source_too_large")
                    _require(entry.name.endswith(".json") and _CASE.fullmatch(entry.name[:-5]))
                    _owned(entry.stat(follow_symlinks=False))
                    names.append(entry.name[:-5])
        _require(names)
        return sorted(names)


def _job(files, job_id):
    # Holding a no-follow file descriptor allows identity checks around SQLite's
    # own read-only open. A rollback-journal service database needs no WAL writes.
    with files.open("queue.sqlite3") as descriptor:
        original = os.fstat(descriptor)
        _require(original.st_size <= 64 * 1024 * 1024, "source_too_large")
        # A read-only SQLite connection can still create WAL/SHM sidecars.
        # Reject unsupported formats through the already verified descriptor
        # before SQLite opens the path. Bytes 18 and 19 are the file-format
        # write/read versions: only rollback-journal version 1 is supported.
        header = os.pread(descriptor, 100, 0)
        _require(len(header) == 100 and header[:16] == b"SQLite format 3\x00"
                 and header[18:20] == b"\x01\x01")
        for suffix in ("-journal", "-wal", "-shm"):
            try:
                with files.open("queue.sqlite3" + suffix):
                    pass
            except FileNotFoundError:
                pass
        connection = sqlite3.connect((files.path / "queue.sqlite3").as_uri() + "?mode=ro", uri=True, timeout=1)
        try:
            connection.execute("PRAGMA query_only=ON")
            connection.execute("PRAGMA trusted_schema=OFF")
            _require(connection.execute("PRAGMA journal_mode").fetchone()[0] == "delete")
            connection.set_progress_handler(lambda: 1, 100000)
            connection.execute("BEGIN")
            _require(connection.execute("SELECT type FROM sqlite_master WHERE name='jobs'").fetchone() == ("table",))
            row = connection.execute("SELECT status, body, fingerprint, cancel_requested, error FROM jobs "
                                     "WHERE job_id=? AND length(body)<=?", (job_id, MAX_JSON_BYTES)).fetchone()
            _require(row is not None, "source_identity_invalid")
            _require(row[0] == "completed" and row[3] == 0 and row[4] is None, "source_incomplete")
            body = row[1]
            _require(type(body) is str and len(body.encode()) <= MAX_JSON_BYTES, "source_too_large")
            _require(sha256(body.encode()).hexdigest() == row[2])
            spec = _json(body)
            _require(type(spec) is dict and set(spec) == {
                "mode", "limit", "evaluate", "max_parallel_requests", "per_provider_limit"})
            _require(spec["mode"] in ("dry_run", "live") and type(spec["evaluate"]) is bool)
            for key, maximum in (("limit", 50), ("max_parallel_requests", 16), ("per_provider_limit", 8)):
                _require(type(spec[key]) is int and 1 <= spec[key] <= maximum)
            current = os.stat(files.path / "queue.sqlite3", follow_symlinks=False)
            _require((current.st_dev, current.st_ino) == (original.st_dev, original.st_ino), "source_path_unsafe")
            return spec, sha256(body.encode()).hexdigest()
        finally:
            connection.close()


_START_FIELDS = {"schema_version", "mode", "qualification", "case_count", "live_calls",
                 "operational_effects", "execution_errors", "include_reference", "compare_baseline",
                 "repeat_judges", "preflight", "max_parallel_requests", "per_provider_limit",
                 "proposals_only", "same_provider_judge_relationship", "status", "record_type", "terminal_records"}
_SUMMARY_FIELDS = (_START_FIELDS - {"record_type", "terminal_records"}) | {
    "proposal_count", "judge_coverage", "all_judge_coverage", "budget", "proposal_set_hash", "limits"}


def _experiment(start, terminal, spec, count, mode):
    for value in (start, terminal):
        _require(type(value) is dict)
        _require(value.get("schema_version") == "dwelly-model-experiment-v1", "source_version_unsupported")
        _require(value.get("mode") == mode and type(value.get("case_count")) is int
                 and value["case_count"] == count and count <= spec["limit"])
        _require(type(value.get("operational_effects")) is int and value["operational_effects"] == 0)
        _require(type(value.get("live_calls")) is int and value["live_calls"] >= 0)
        _require(value.get("qualification") == "development_only_unqualified")
        _require(value.get("proposals_only") is (not spec["evaluate"]))
        for key in ("max_parallel_requests", "per_provider_limit"):
            _require(type(value.get(key)) is int and value[key] == spec[key])
    _require(set(start) == _START_FIELDS)
    _require(_SUMMARY_FIELDS <= set(terminal) <= _SUMMARY_FIELDS | {"shared_budget", "experiment_namespace"})
    _require(("shared_budget" in terminal) == ("experiment_namespace" in terminal))
    _require(start["status"] == "running" and start["record_type"] == "experiment_started"
             and start["terminal_records"] == ["summary.json", "failure.json"])
    _require(start["live_calls"] == 0 and start["execution_errors"] == {})
    _require(terminal["status"] == "completed", "source_incomplete")
    _require(type(terminal["proposal_count"]) is int and terminal["proposal_count"] == count)
    if mode == "offline_dry_run":
        _require(terminal["live_calls"] == 0)
    else:
        _require(terminal["live_calls"] >= count)
    for key in _START_FIELDS - {"live_calls", "execution_errors", "status", "record_type", "terminal_records"}:
        _require(start[key] == terminal[key])
    _require(type(start["include_reference"]) is bool and type(start["compare_baseline"]) is bool)
    _require(type(start["repeat_judges"]) is int and 0 <= start["repeat_judges"] <= 10)
    _require(type(terminal["execution_errors"]) is dict)


def _live_attempt(files, prefix, case_id, snapshot, proposal, config):
    key = case_id + "-proposer"
    request = files.json(prefix + f"requests/{key}.json")
    receipt = files.json(prefix + f"receipts/{key}.json")
    _require(type(request) is dict and set(request) == {
        "request_key", "provider", "requested_model", "system", "prompt", "reservation"}, "source_linkage_invalid")
    _require(type(receipt) is dict and set(receipt) == {
        "request_key", "provider", "requested_model", "status", "response"}, "source_linkage_invalid")
    seat = config["proposer"]
    for value in (request, receipt):
        _require(value["request_key"] == key and value["provider"] == seat["provider"]
                 and value["requested_model"] == seat["model"], "source_linkage_invalid")
    system, prompt = semantic.proposal_prompt(snapshot)
    _require((request["system"], request["prompt"]) == (system, prompt), "source_linkage_invalid")
    reservation = request["reservation"]
    _require(type(reservation) is dict and set(reservation) == {
        "event", "request_key", "provider", "model", "estimated_input_token_upper_bound",
        "max_output_tokens", "amount_usd", "reserved_usd"}, "source_linkage_invalid")
    _require(reservation["event"] == "reserve" and reservation["request_key"] == key
             and reservation["provider"] == seat["provider"] and reservation["model"] == seat["model"]
             and type(reservation["max_output_tokens"]) is int
             and reservation["max_output_tokens"] == config["max_output_tokens"], "source_linkage_invalid")
    _require(type(reservation["estimated_input_token_upper_bound"]) is int
             and reservation["estimated_input_token_upper_bound"] > 0
             and type(reservation["reserved_usd"]) in (int, float)
             and reservation["reserved_usd"] > 0
             and type(reservation["amount_usd"]) is str, "source_linkage_invalid")
    response = receipt["response"]
    _require(receipt["status"] == "received" and type(response) is dict and set(response) == {
        "text", "provider", "requested_model", "observed_model", "input_tokens", "output_tokens",
        "request_id", "latency_ms", "raw_response"}, "source_linkage_invalid")
    _require(response["provider"] == seat["provider"] and response["requested_model"] == seat["model"],
             "source_linkage_invalid")
    for field in ("observed_model", "request_id"):
        _require(response[field] is None or type(response[field]) is str and len(response[field]) <= 256,
                 "source_linkage_invalid")
    for field in ("input_tokens", "output_tokens"):
        _require(response[field] is None or type(response[field]) is int and response[field] >= 0,
                 "source_linkage_invalid")
    _require(type(response["latency_ms"]) in (int, float) and response["latency_ms"] >= 0
             and type(response["raw_response"]) is dict, "source_linkage_invalid")
    try:
        candidate = semantic.validate_proposal(snapshot, models._model_json(response["text"]))
        _require(proposal == models._envelope(snapshot, candidate, "live_api"), "source_linkage_invalid")
    except (ValueError, TypeError, KeyError):
        raise ShadowError("source_linkage_invalid") from None
    return receipt


def _verifier_version():
    # These are current local validators, not a claim about the original runner.
    modules = {"bridge_source": __file__, "baseline": baseline.__file__, "cases": cases.__file__,
               "model_runner": models.__file__, "semantic": semantic.__file__}
    return digest({name: sha256(Path(path).read_bytes()).hexdigest() for name, path in modules.items()})


def load_source(service_root, job_id, case_id):
    """Validate an entire frozen experiment and return only immutable identities."""
    _require(type(job_id) is str and _JOB.fullmatch(job_id)
             and type(case_id) is str and _CASE.fullmatch(case_id), "source_identity_invalid")
    files = None
    try:
        files = _SourceFiles(service_root)
        spec, body_hash = _job(files, job_id)
        prefix = f"jobs/{job_id}/"
        try:
            with files.open(prefix + "failure.json"):
                raise ShadowError("source_incomplete")
        except FileNotFoundError:
            pass
        start = files.json(prefix + "manifest.json")
        terminal = files.json(prefix + "summary.json")
        config = files.json(prefix + "config.json")
        models._validate_config(config)
        ids = files.case_ids(prefix + "snapshots")
        _require(case_id in ids, "source_case_missing")
        _require(files.case_ids(prefix + "proposals") == ids)
        _require(files.case_ids(prefix + "baseline_proposals") == ids)
        mode = "live_api" if spec["mode"] == "live" else "offline_dry_run"
        _experiment(start, terminal, spec, len(ids), mode)
        frozen = files.json(prefix + "proposals-frozen.json")
        _require(type(frozen) is dict and set(frozen) == {
            "proposal_set_hash", "baseline_set_hash", "input_set_hash"})
        snapshots, proposals, baselines, receipts = {}, {}, {}, {}
        for identity in ids:
            snapshot = files.json(prefix + f"snapshots/{identity}.json")
            cases.validate_snapshot(snapshot, identity)
            proposal = files.json(prefix + f"proposals/{identity}.json")
            expected_baseline = baseline.propose(snapshot)
            saved_baseline = files.json(prefix + f"baseline_proposals/{identity}.json")
            _require(saved_baseline == expected_baseline, "source_linkage_invalid")
            if mode == "offline_dry_run":
                _require(proposal == expected_baseline, "source_linkage_invalid")
            else:
                receipts[identity] = _live_attempt(files, prefix, identity, snapshot, proposal, config)
            snapshots[identity], proposals[identity], baselines[identity] = snapshot, proposal, saved_baseline
        _require(frozen == {"proposal_set_hash": digest(proposals), "baseline_set_hash": digest(baselines),
                            "input_set_hash": digest({c: s["input_hash"] for c, s in snapshots.items()})})
        _require(terminal["proposal_set_hash"] == frozen["proposal_set_hash"])
        verifier = _verifier_version()
        provenance = "historical_live_api" if mode == "live_api" else "baseline"
        evidence = {"job_id": job_id, "case_id": case_id, "job_spec_hash": body_hash,
                    "artifacts": files.hashes, "verifier_version": verifier, "provenance": provenance}
        return SourceRecord(job_id, case_id, snapshots[case_id]["input_hash"], digest(proposals[case_id]),
                            digest(receipts[case_id]) if receipts else None, digest(evidence),
                            provenance, mode, verifier)
    except ShadowError:
        raise
    except OSError as error:
        # ELOOP and ENOTDIR cover terminal and intermediate symlink refusals.
        if error.errno in (40, 62, 20):
            raise ShadowError("source_path_unsafe") from None
        raise ShadowError("source_invalid") from None
    except (ValueError, TypeError, KeyError, RecursionError, OverflowError, sqlite3.Error):
        raise ShadowError("source_invalid") from None
    finally:
        if files is not None:
            files.close()
