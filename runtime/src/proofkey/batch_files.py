"""Private local publication bookkeeping; never runtime permission or replay."""
import fcntl
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import stat
from uuid import uuid4

from .contracts import CaseResult, ExportReceipt
from .host_contracts import (BatchManifestV1, BatchPositionReceiptV1, CommandManifestV1, ConsumedExportV1,
    InterfaceLimitsV1, PublicationWindowV1, RunReadbackV1, RunReferenceV1,
    _OrdinalAdmissionV1, _ResultPublicationV1, _pending_command)
from .identity import fingerprint

_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_POSITION = re.compile(r"^POSITION-([0-9]{8})-(ADMISSION|RESULT|PROGRESS)\.json$")
_PENDING = re.compile(r"^(INPUT-INVENTORY|FINAL-MANIFEST|POSITION-[0-9]{8}-(ADMISSION|RESULT|PROGRESS))\.json\.pending-[a-f0-9]{32}$")


class PublicationFailure(RuntimeError):
    def __init__(self, reason="publication_io_error"):
        self.reason = reason
        super().__init__("Private publication unavailable")


def _observation(window, clock):
    try:
        now, mono = clock.now(), clock.monotonic()
        if (now.utcoffset() is None or now < window.execution.captured_at
                or type(mono) not in (int, float) or not math.isfinite(mono)
                or mono < window.execution.captured_monotonic):
            raise ValueError
        return now, mono, max(0.0, min((window.deadline - now).total_seconds(), window.monotonic_deadline - mono))
    except (ValueError, TypeError, AttributeError, OverflowError):
        raise PublicationFailure("deadline_exceeded") from None


def _remaining(window, clock):
    return _observation(window, clock)[2]


class _Pins:
    def __init__(self, path, *, create=False, boundary=lambda: None):
        self.entries = []
        self.boundary = boundary
        path = Path(path)
        if not path.is_absolute() or ".." in path.parts or len(path.parts) > 64 or len(str(path)) > 1024:
            raise PublicationFailure("publication_integrity_failure")
        try:
            self.boundary()
            fd = os.open(path.anchor, _FLAGS)
            self.entries.append((fd, None, path.anchor, self.identity(fd)))
            for index, name in enumerate(path.parts[1:], 1):
                self.boundary()
                if create and index == len(path.parts) - 1:
                    os.mkdir(name, 0o700, dir_fd=fd)
                    os.fsync(fd)
                child = os.open(name, _FLAGS, dir_fd=fd)
                self.entries.append((child, fd, name, self.identity(child)))
                fd = child
            self.root = fd
            self.check()
        except BaseException:
            self.close()
            raise

    @staticmethod
    def identity(fd):
        info = os.fstat(fd)
        return info.st_dev, info.st_ino

    def child(self, parent, name):
        if type(name) is not str or name in ("", ".", "..") or "/" in name or "\\" in name:
            raise PublicationFailure("publication_integrity_failure")
        self.boundary()
        self.check()
        fd = os.open(name, _FLAGS, dir_fd=parent)
        self.entries.append((fd, parent, name, self.identity(fd)))
        self.check()
        return fd

    def check(self):
        self.boundary()
        for fd, parent, name, identity in self.entries:
            info = os.stat(name, dir_fd=parent, follow_symlinks=False)
            if not stat.S_ISDIR(info.st_mode) or (info.st_dev, info.st_ino) != identity or self.identity(fd) != identity:
                raise PublicationFailure("publication_integrity_failure")

    def close(self):
        while self.entries:
            fd = self.entries.pop()[0]
            os.close(fd)


def _read(pins, directory, name, limit):
    pins.check()
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise PublicationFailure("publication_limit_exceeded")
        chunks, size = [], 0
        while True:
            pins.check()
            chunk = os.read(fd, min(65536, limit + 1 - size))
            if not chunk:
                break
            size += len(chunk)
            if size > limit:
                raise PublicationFailure("publication_limit_exceeded")
            chunks.append(chunk)
        pins.check()
        after, current = os.fstat(fd), os.stat(name, dir_fd=directory, follow_symlinks=False)
        fields = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
        if fields(before) != fields(after) or fields(after) != fields(current) or not stat.S_ISREG(current.st_mode):
            raise PublicationFailure("publication_integrity_failure")
        return b"".join(chunks)
    finally:
        os.close(fd)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate inventory field")
        result[key] = value
    return result


def _model(data, choices):
    tree = json.loads(data, object_pairs_hook=_pairs, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    # Parse JSON again through the strict schema; Python mode cannot coerce arrays to tuples.
    for cls in choices:
        if tree.get("kind") == cls.model_fields["kind"].default:
            return cls.model_validate_json(data)
    raise ValueError("Invalid inventory kind")


def _export_hashes(pins, root, receipt, result, limit):
    receipt = ExportReceipt.model_validate_json(receipt.model_dump_json())
    if receipt.supplied_case_id != result.case_id:
        raise PublicationFailure("publication_integrity_failure")
    if receipt.status == "failed":
        return ConsumedExportV1(actual_receipt=receipt, actual_file_hashes=())
    if receipt.output_name != result.case_id or receipt.failure is not None:
        raise PublicationFailure("publication_integrity_failure")
    retained = len(pins.entries)
    try:
        answers = pins.child(root, "ANSWERS")
        case = pins.child(answers, receipt.output_name)
        hashes = tuple((name, sha256(_read(pins, case, name, limit)).hexdigest())
                       for name in ("ANSWER.md", "REASONING.md"))
        pins.check()
        return ConsumedExportV1(actual_receipt=receipt, actual_file_hashes=hashes)
    finally:
        # Keep the run's original ancestry pins, not repeated export children.
        while len(pins.entries) > retained:
            os.close(pins.entries.pop()[0])


class RunPublisher:
    def __init__(self, output_root, *, window, clock, limits):
        if type(window) is not PublicationWindowV1 or type(limits) is not InterfaceLimitsV1:
            raise ValueError("Exact publication configuration required")
        self.window = PublicationWindowV1.model_validate(window.model_dump())
        self.limits = InterfaceLimitsV1.model_validate(limits.model_dump())
        self.clock = clock
        self._pins = None
        self._initial = None
        self._used = 0
        self._admissions = {}
        self._last_utc = None
        self._last_mono = None
        try:
            self._pins = _Pins(output_root, create=True, boundary=self._boundary)
            self._boundary()
            fcntl.flock(self._pins.root, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except Exception as error:
            self.close()
            if isinstance(error, PublicationFailure):
                raise
            raise PublicationFailure() from None

    def _boundary(self):
        now, mono, remaining = _observation(self.window, self.clock)
        if (remaining <= 0 or self._last_utc is not None and now < self._last_utc
                or self._last_mono is not None and mono < self._last_mono):
            raise PublicationFailure("deadline_exceeded")
        self._last_utc, self._last_mono = now, mono

    def _write(self, name, value):
        try:
            self._boundary()
            self._pins.check()
            data = json.dumps(value.model_dump(mode="json"), sort_keys=True, ensure_ascii=False,
                              separators=(",", ":"), allow_nan=False).encode("utf-8")
            if len(data) + self._used > self.limits.max_run_bytes:
                raise PublicationFailure("publication_limit_exceeded")
            self._used += len(data)
            self._boundary()
            self._pins.check()
            pending = name + ".pending-" + uuid4().hex
            fd = os.open(pending, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=self._pins.root)
            try:
                identity = _Pins.identity(fd)
                view = memoryview(data)
                while view:
                    self._boundary()
                    written = os.write(fd, view)
                    if written <= 0:
                        raise OSError
                    view = view[written:]
                self._boundary()
                os.fsync(fd)
                self._pins.check()
                saved = os.stat(pending, dir_fd=self._pins.root, follow_symlinks=False)
                if (saved.st_dev, saved.st_ino) != identity or not stat.S_ISREG(saved.st_mode):
                    raise PublicationFailure("publication_integrity_failure")
                self._boundary()
                os.link(pending, name, src_dir_fd=self._pins.root, dst_dir_fd=self._pins.root, follow_symlinks=False)
                self._pins.check()
                current = os.stat(name, dir_fd=self._pins.root, follow_symlinks=False)
                if (current.st_dev, current.st_ino) != identity or not stat.S_ISREG(current.st_mode):
                    raise PublicationFailure("publication_integrity_failure")
                self._boundary()
                os.fsync(self._pins.root)
            finally:
                os.close(fd)
            actual = _read(self._pins, self._pins.root, name, self.limits.max_run_bytes)
            if actual != data:
                raise PublicationFailure("publication_integrity_failure")
            self._pins.check()
            return RunReferenceV1(name=name, file_hash=sha256(actual).hexdigest())
        except Exception as error:
            if isinstance(error, PublicationFailure):
                raise
            raise PublicationFailure() from None

    def publish_input(self, inventory):
        if type(inventory) not in (BatchManifestV1, CommandManifestV1) or self._initial is not None:
            raise PublicationFailure("invalid_inventory")
        initial = type(inventory).model_validate_json(inventory.model_dump_json())
        if (initial.references or initial.pending_command_ids or
                isinstance(initial, BatchManifestV1) and any(p != BatchPositionReceiptV1(inventory=p.inventory) for p in initial.positions)
                or isinstance(initial, CommandManifestV1) and (initial.command is not None or initial.unresolved_admission
                                                             or initial.export_outcome != "not_attempted")):
            raise PublicationFailure("invalid_inventory")
        reference = self._write("INPUT-INVENTORY.json", initial)
        self._initial = initial
        return reference

    def publish_admission(self, ordinal, inventory):
        self._ordinal(ordinal)
        if self._initial is None or type(inventory) is not _OrdinalAdmissionV1:
            raise PublicationFailure("invalid_inventory")
        admission = _OrdinalAdmissionV1.model_validate_json(inventory.model_dump_json())
        expected = self._initial.inventories[ordinal] if isinstance(self._initial, BatchManifestV1) else self._initial.input
        if (type(ordinal) is not int or ordinal < 0 or ordinal > 99999999 or admission.ordinal != ordinal
                or admission.inventory != expected or admission.run_id != self._initial.run_id
                or admission.input_hash != self._initial.input.input_hash or admission.window != self._initial.window):
            raise PublicationFailure("invalid_inventory")
        reference = self._write(f"POSITION-{ordinal:08d}-ADMISSION.json", admission)
        self._admissions[ordinal] = admission
        return reference

    def publish_result(self, ordinal, actual_result):
        self._ordinal(ordinal)
        if ordinal not in self._admissions or type(actual_result) is not CaseResult:
            raise PublicationFailure("invalid_inventory")
        result = CaseResult.model_validate({key: getattr(actual_result, key) for key in CaseResult.model_fields})
        if result.case_id != self._admissions[ordinal].inventory.supplied_case_id:
            raise PublicationFailure("publication_integrity_failure")
        payload = _ResultPublicationV1(run_id=self._initial.run_id, ordinal=ordinal, result=result,
                                      result_hash=fingerprint(result.model_dump(mode="json")))
        return self._write(f"POSITION-{ordinal:08d}-RESULT.json", payload)

    def publish_progress(self, ordinal, position):
        self._ordinal(ordinal)
        if isinstance(self._initial, BatchManifestV1):
            if type(position) is not BatchPositionReceiptV1 or position.inventory != self._initial.inventories[ordinal]:
                raise PublicationFailure("invalid_inventory")
            if position.admission_status != "not_attempted" and ordinal not in self._admissions:
                raise PublicationFailure("invalid_inventory")
        elif type(position) is not CommandManifestV1 or not self._same_initial(position):
            raise PublicationFailure("invalid_inventory")
        return self._write(f"POSITION-{ordinal:08d}-PROGRESS.json", type(position).model_validate_json(position.model_dump_json()))

    def publish_final(self, manifest):
        if self._initial is None or type(manifest) is not type(self._initial) or not self._same_initial(manifest):
            raise PublicationFailure("invalid_inventory")
        return self._write("FINAL-MANIFEST.json", type(manifest).model_validate_json(manifest.model_dump_json()))

    def _ordinal(self, ordinal):
        count = self._initial.input.position_count if isinstance(self._initial, BatchManifestV1) else 1
        if self._initial is None or type(ordinal) is not int or not 0 <= ordinal < count:
            raise PublicationFailure("invalid_inventory")

    def _same_initial(self, snapshot):
        return all(getattr(snapshot, name) == getattr(self._initial, name)
                   for name in ("run_id", "input", "window", "release_id", "mode", "clock_mode"))

    def verify_export(self, actual_receipt, actual_result):
        try:
            self._boundary()
            if type(actual_receipt) is not ExportReceipt or type(actual_result) is not CaseResult:
                raise ValueError
            result = CaseResult.model_validate({key: getattr(actual_result, key) for key in CaseResult.model_fields})
            return _export_hashes(self._pins, self._pins.root, actual_receipt, result, self.limits.max_run_bytes)
        except Exception as error:
            if isinstance(error, PublicationFailure):
                raise
            raise PublicationFailure("publication_integrity_failure") from None

    def _readback(self):
        self._boundary()
        return _inventory(self._pins, self.limits)

    def close(self):
        if self._pins is not None:
            self._pins.close()
            self._pins = None


def read_run_inventory(output_root, *, limits):
    if type(limits) is not InterfaceLimitsV1:
        raise ValueError("Exact private inventory limits required")
    pins = None
    try:
        pins = _Pins(output_root)
        return _inventory(pins, limits)
    except Exception as error:
        reason = error.reason if isinstance(error, PublicationFailure) else "invalid_inventory"
        if reason not in ("publication_io_error", "publication_integrity_failure", "publication_limit_exceeded"):
            reason = "invalid_inventory"
        return RunReadbackV1(status="invalid", failure=reason)
    finally:
        if pins is not None:
            pins.close()


def _inventory(pins, limits):
    pins.check()
    names = sorted(os.listdir(pins.root))
    if len(names) > limits.max_run_bytes:
        raise PublicationFailure("publication_limit_exceeded")
    files, pending, total = {}, [], 0
    for name in names:
        if name == "ANSWERS":
            continue
        if _PENDING.fullmatch(name):
            target = name.split(".pending-", 1)[0]
            actual = os.stat(name, dir_fd=pins.root, follow_symlinks=False)
            if not stat.S_ISREG(actual.st_mode):
                raise ValueError
            if target not in names:
                pending.append(name)
            else:
                target_info = os.stat(target, dir_fd=pins.root, follow_symlinks=False)
                if (actual.st_dev, actual.st_ino) != (target_info.st_dev, target_info.st_ino):
                    pending.append(name)
            continue
        if name not in ("INPUT-INVENTORY.json", "FINAL-MANIFEST.json") and not _POSITION.fullmatch(name):
            raise ValueError
        data = _read(pins, pins.root, name, limits.max_run_bytes - total)
        total += len(data)
        files[name] = (data, RunReferenceV1(name=name, file_hash=sha256(data).hexdigest()))
    if "INPUT-INVENTORY.json" not in files:
        return RunReadbackV1(status="partial", unknown_pending_names=tuple(pending), failure="invalid_inventory")
    initial = _model(files["INPUT-INVENTORY.json"][0], (BatchManifestV1, CommandManifestV1))
    is_batch = isinstance(initial, BatchManifestV1)
    if initial.references or initial.pending_command_ids or (is_batch and
            any(p != BatchPositionReceiptV1(inventory=p.inventory) for p in initial.positions)) or (not is_batch and initial.command is not None):
        raise ValueError
    inventories = initial.inventories if is_batch else ()
    admissions, progresses, results = {}, {}, {}
    for name, (data, _) in files.items():
        match = _POSITION.fullmatch(name)
        if match is None:
            continue
        ordinal, phase = int(match[1]), match[2]
        if ordinal >= (initial.input.position_count if is_batch else 1):
            raise ValueError
        expected = inventories[ordinal] if is_batch else initial.input
        if phase == "ADMISSION":
            value = _OrdinalAdmissionV1.model_validate_json(data)
            if (value.inventory != expected or value.ordinal != ordinal or value.run_id != initial.run_id
                    or value.window != initial.window or value.input_hash != initial.input.input_hash):
                raise ValueError
            admissions[ordinal] = value
        elif phase == "RESULT":
            value = _ResultPublicationV1.model_validate_json(data)
            if value.ordinal != ordinal or value.run_id != initial.run_id or value.result.case_id != expected.supplied_case_id:
                raise ValueError
            results[ordinal] = value
        else:
            value = BatchPositionReceiptV1.model_validate_json(data) if is_batch else CommandManifestV1.model_validate_json(data)
            if is_batch and value.inventory != expected or not is_batch and (value.input != expected or value.run_id != initial.run_id):
                raise ValueError
            progresses[ordinal] = value
    for ordinal, result in results.items():
        if ordinal not in admissions:
            raise ValueError
    joined, pending_ids = [], []
    for ordinal, progress in progresses.items():
        command = progress.command
        if command is not None:
            if ordinal not in admissions:
                raise ValueError
            joined.append(command.command_id)
            if command.result is not None and (ordinal not in results or results[ordinal].result != command.result):
                raise ValueError
            if _pending_command(command):
                pending_ids.append(command.command_id)
        if progress.export is not None:
            if _export_hashes(pins, pins.root, progress.export.actual_receipt, command.result, limits.max_run_bytes) != progress.export:
                raise ValueError
        for reference in progress.references:
            if reference.name not in files or reference != files[reference.name][1] or reference.name == f"POSITION-{ordinal:08d}-PROGRESS.json":
                raise ValueError
    if len(set(joined)) != len(joined):
        raise ValueError
    unresolved = tuple(ordinal for ordinal in sorted(admissions) if ordinal not in progresses or progresses[ordinal].command is None)
    final = None
    if "FINAL-MANIFEST.json" in files:
        final = _model(files["FINAL-MANIFEST.json"][0], (BatchManifestV1, CommandManifestV1))
        if type(final) is not type(initial) or any(getattr(final, name) != getattr(initial, name)
                for name in ("input", "run_id", "window", "release_id", "mode", "clock_mode")):
            raise ValueError
        expected_refs = tuple(reference for name, (_, reference) in files.items() if name != "FINAL-MANIFEST.json")
        if set(final.references) != set(expected_refs):
            raise ValueError
        if final.pending_command_ids != tuple(pending_ids):
            raise ValueError
        if is_batch:
            if final.inventories != inventories or final.unresolved_admission_ordinals != unresolved:
                raise ValueError
            if tuple(p.command.command_id for p in final.positions if p.command is not None) != tuple(joined):
                raise ValueError
            for ordinal, position in enumerate(final.positions):
                progress = progresses.get(ordinal)
                if progress is None:
                    if (position.command is not None or position.export_outcome != "not_attempted"
                            or position.publication_status == "committed"):
                        raise ValueError
                    continue
                without_self = tuple(ref for ref in final.positions[ordinal].references
                                     if ref.name != f"POSITION-{ordinal:08d}-PROGRESS.json")
                if position.model_copy(update={"references": without_self}) != progress:
                    raise ValueError
        else:
            if final.unresolved_admission != bool(unresolved):
                raise ValueError
            progress = progresses.get(0)
            if progress is None:
                if final.command is not None or final.export_outcome != "not_attempted":
                    raise ValueError
            elif final.model_copy(update={"references": progress.references, "as_of": progress.as_of}) != progress:
                raise ValueError
    pins.check()
    return RunReadbackV1(run_id=initial.run_id, run_kind="batch" if is_batch else "command",
        status="committed_snapshot" if final is not None and not pending else "partial", input_inventory=initial.input,
        position_inventories=inventories, committed_references=tuple(ref for _, ref in files.values()),
        joined_command_ids=tuple(joined), pending_command_ids=tuple(pending_ids), unresolved_admission_ordinals=unresolved,
        final_manifest=final, unknown_pending_names=tuple(pending))
