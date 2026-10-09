"""Offline fact exports into new case directories, never authority grants.

POSIX no-follow descriptors pin ancestry; flock coordinates harness writers.
Each file publishes atomically without replacement. The pair is incremental,
not a single transaction. Pending files remain as visible run-owned artifacts.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import stat
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .contracts import CaseResult, ExportReceipt, SavedResult
from .identity import fingerprint


class ExportFailure(Exception):
    """Generic export failure; batch must retain the original supplied identity."""

    def __init__(self, reason: str, supplied_case_id: str | None = None):
        super().__init__(reason)
        self.reason = reason
        self.supplied_case_id = supplied_case_id


def _collision_key(name):
    return unicodedata.normalize("NFKC", unicodedata.normalize("NFKC", name).casefold())


def _case_name(value):
    normalized = unicodedata.normalize("NFKC", value)
    if (value in (".", "..") or normalized in (".", "..")
            or any(ch in value or ch in normalized for ch in ("/", "\\", ":"))
            or any(unicodedata.category(ch).startswith("C") for ch in value)
            or not value.strip() or len(value.encode("utf-8")) > 200):
        raise ExportFailure("unsafe_case_id", value)
    return value


class _Directories:
    """Keep every ancestor open and recheck its parent/name inode binding."""

    def __init__(self):
        self.entries = []

    def open(self, name, parent=None):
        fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        self.entries.append((fd, parent, name))
        self.check()
        return fd

    def check(self):
        for fd, parent, name in self.entries:
            info = os.fstat(fd)
            observed = os.stat(name, dir_fd=parent, follow_symlinks=False)
            if (not stat.S_ISDIR(observed.st_mode)
                    or (info.st_dev, info.st_ino) != (observed.st_dev, observed.st_ino)):
                raise ExportFailure("output_ancestry_changed")

    def close(self):
        for fd, _, _ in reversed(self.entries):
            os.close(fd)


def _open_root(root, directories):
    raw = os.fspath(root)
    if not isinstance(raw, str) or "\x00" in raw or ".." in Path(raw).parts:
        raise ExportFailure("unsafe_output_root")
    path = Path(os.path.abspath(raw))
    if not path.name:
        raise ExportFailure("unsafe_output_root")
    fd = directories.open(path.anchor)
    for component in path.parts[1:]:
        directories.check()
        try:
            child = directories.open(component, fd)
        except FileNotFoundError:
            os.mkdir(component, 0o700, dir_fd=fd)
            child = directories.open(component, fd)
        fd = child
    return fd


def _markdown(title, facts):
    # Indented JSON cannot activate Markdown supplied in result facts.
    text = json.dumps(facts, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
    return (f"# {title}\n\nSource mode: offline\n"
            "Auditable result facts; export status does not establish business success.\n\n"
            + "\n".join("    " + line for line in text.splitlines()) + "\n").encode("utf-8")


def _contents(result):
    wire = result.model_dump(mode="json")
    reasoning_keys = {"fingerprint", "rationale", "evidence_refs", "policy_refs"}
    answer = {key: value for key, value in wire.items() if key not in reasoning_keys}
    reasoning = {key: value for key, value in wire.items() if key in reasoning_keys}
    if result.status != "authorized":
        reasoning = wire
    return {"ANSWER.md": _markdown("Answer", answer),
            "REASONING.md": _markdown("Public rationale and evidence references", reasoning)}


def _readback(directory, filename, payload, directories):
    directories.check()
    fd = os.open(filename, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ExportFailure("output_integrity_failure")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            actual = stream.read(len(payload) + 1)
        directories.check()
        observed = os.stat(filename, dir_fd=directory, follow_symlinks=False)
        opened = os.fstat(fd)
        if ((observed.st_dev, observed.st_ino) != (opened.st_dev, opened.st_ino)
                or actual != payload):
            raise ExportFailure("output_integrity_failure")
        return hashlib.sha256(actual).hexdigest()
    finally:
        os.close(fd)


def _publish(directory, filename, payload, directories):
    directories.check()
    pending = filename + ".pending-" + uuid.uuid4().hex
    fd = os.open(pending, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                 0o600, dir_fd=directory)
    try:
        info = os.fstat(fd)
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(fd)
        directories.check()
        saved = os.stat(pending, dir_fd=directory, follow_symlinks=False)
        if not stat.S_ISREG(saved.st_mode) or (saved.st_dev, saved.st_ino) != (info.st_dev, info.st_ino):
            raise ExportFailure("output_ancestry_changed")
        os.link(pending, filename, src_dir_fd=directory, dst_dir_fd=directory, follow_symlinks=False)
        directories.check()
        published = os.stat(filename, dir_fd=directory, follow_symlinks=False)
        if not stat.S_ISREG(published.st_mode) or (published.st_dev, published.st_ino) != (info.st_dev, info.st_ino):
            raise ExportFailure("output_ancestry_changed")
        _readback(directory, filename, payload, directories)
        os.fsync(directory)
    finally:
        os.close(fd)


def _export_case(result: CaseResult, output_root) -> ExportReceipt:
    """Persist public facts from a trusted runtime result, without authorizing it.

    Receipt hash = fingerprint({fixed filename: sha256(exact UTF-8 bytes)}).
    Unsupported POSIX primitives and all storage failures fail closed. Generic
    exceptions never include paths, private exception text, or model contents.
    """
    supplied_id = None
    directories = _Directories()
    try:
        if type(result) not in (CaseResult, SavedResult):
            raise ExportFailure("invalid_result")
        # Revalidate raw fields, including fields a scoped serializer would hide.
        try:
            result = CaseResult.model_validate({key: getattr(result, key) for key in CaseResult.model_fields})
        except (ValueError, TypeError, AttributeError):
            raise ExportFailure("invalid_result") from None
        supplied_id = result.case_id
        name = _case_name(supplied_id)
        contents = _contents(result)
        root = _open_root(output_root, directories)
        try:
            fcntl.flock(root, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ExportFailure("output_busy", supplied_id) from None
        directories.check()
        collision = _collision_key(name)
        if any(_collision_key(existing) == collision for existing in os.listdir(root)):
            raise ExportFailure("output_conflict", supplied_id)
        directories.check()
        os.mkdir(name, 0o700, dir_fd=root)
        case = directories.open(name, root)
        os.fsync(root)
        for filename, payload in contents.items():
            _publish(case, filename, payload, directories)
        hashes = {filename: _readback(case, filename, payload, directories)
                  for filename, payload in contents.items()}
        directories.check()
        return ExportReceipt(supplied_case_id=supplied_id, output_name=name,
            output_hash=fingerprint(hashes),
            status="written", as_of=result.as_of or datetime.now(timezone.utc))
    except ExportFailure as exc:
        if exc.supplied_case_id is None:
            exc.supplied_case_id = supplied_id
        raise
    except Exception:
        raise ExportFailure("export_io_error", supplied_id) from None
    finally:
        directories.close()


def export_case(result: CaseResult, output_root) -> ExportReceipt:
    """Write scoped offline facts or raise a generic, context-free failure.

    Receipt hash = fingerprint({filename: SHA256(read-back file bytes)}), with
    fixed ANSWER.md and REASONING.md names. This function accepts trusted runtime
    results; it does not resolve caller proof or establish result authorization.
    """
    try:
        return _export_case(result, output_root)
    except ExportFailure as exc:
        reason, supplied_id = exc.reason, exc.supplied_case_id
    except Exception:
        reason, supplied_id = "export_io_error", None
    # Raise after the handler so private exceptions are absent even from context.
    raise ExportFailure(reason, supplied_id)
