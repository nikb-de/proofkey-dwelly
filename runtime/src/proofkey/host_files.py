"""New-run-only private digest inventory; readback never invokes the runtime."""
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat

from .host_contracts import CommandInventoryV1, InventoryReferenceV1

_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_NAME = re.compile(r"^COMMAND-([0-9]{8})-([012])\.json$")
_PHASE = {"queued": 0, "started": 1, "finished": 2}


class InventoryFailure(RuntimeError):
    def __init__(self):
        super().__init__("Host inventory unavailable or incomplete")


def _directory(path):
    path = Path(path)
    if not path.is_absolute() or ".." in path.parts or len(path.parts) > 64 or len(str(path)) > 1024:
        raise ValueError
    descriptor = os.open(path.anchor, _FLAGS)
    try:
        for part in path.parts[1:]:
            child = os.open(part, _FLAGS, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _identity(descriptor):
    value = os.fstat(descriptor)
    return value.st_dev, value.st_ino


def _check(path, identity):
    descriptor = _directory(path)
    try:
        if _identity(descriptor) != identity:
            raise ValueError
    finally:
        os.close(descriptor)


def _write(root, name, data):
    descriptor = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=root)
    try:
        view = memoryview(data)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.fsync(root)


def _read(root, name, limit):
    descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=root)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > limit:
            raise ValueError
        chunks, size = [], 0
        while True:
            part = os.read(descriptor, min(65536, limit + 1 - size))
            if not part:
                break
            size += len(part)
            if size > limit:
                raise ValueError
            chunks.append(part)
        after = os.fstat(descriptor)
        if ((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) !=
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)):
            raise ValueError
        return b"".join(chunks)
    finally:
        os.close(descriptor)


class HostInventory:
    def __init__(self, root, *, max_bytes=262144):
        self.root = Path(root).absolute()
        self.max_bytes = max_bytes
        self._descriptor = None
        self._total = 0
        try:
            if type(max_bytes) is not int or max_bytes <= 0:
                raise ValueError
            parent = _directory(self.root.parent)
            try:
                self._parent_identity = _identity(parent)
                fcntl.flock(parent, fcntl.LOCK_EX | fcntl.LOCK_NB)
                os.mkdir(self.root.name, mode=0o700, dir_fd=parent)
                self._descriptor = os.open(self.root.name, _FLAGS, dir_fd=parent)
                self._root_identity = _identity(self._descriptor)
                header = b'{"kind":"host-private-inventory-v1"}'
                if len(header) > max_bytes:
                    raise ValueError
                _write(self._descriptor, "HOST-INVENTORY.json", header)
                if _read(self._descriptor, "HOST-INVENTORY.json", max_bytes) != header:
                    raise ValueError
                self._total = len(header)
                self._check()
            finally:
                os.close(parent)
        except (OSError, ValueError, TypeError):
            self.close()
            raise InventoryFailure() from None

    def _check(self):
        _check(self.root.parent, self._parent_identity)
        _check(self.root, self._root_identity)

    def publish(self, sequence, phase, value):
        try:
            if (type(sequence) is not int or not 0 <= sequence <= 99999999 or phase not in _PHASE
                    or type(value) is not CommandInventoryV1 or value.phase != phase or self._descriptor is None):
                raise ValueError
            value = CommandInventoryV1.model_validate_json(value.model_dump_json())
            data = json.dumps(value.model_dump(mode="json"), sort_keys=True, separators=(",", ":"),
                              ensure_ascii=False, allow_nan=False).encode()
            if self._total + len(data) > self.max_bytes:
                raise ValueError
            self._check()
            name = f"COMMAND-{sequence:08d}-{_PHASE[phase]}.json"
            _write(self._descriptor, name, data)
            self._total += len(data)
            actual = _read(self._descriptor, name, self.max_bytes)
            self._check()
            if actual != data:
                raise ValueError
            return InventoryReferenceV1(name=name, file_hash=sha256(actual).hexdigest())
        except (OSError, ValueError, TypeError):
            raise InventoryFailure() from None

    def close(self):
        if self._descriptor is not None:
            os.close(self._descriptor)
            self._descriptor = None


def read_inventory(root, *, max_bytes=262144):
    """Trusted local bookkeeping only; started without finished remains unknown."""
    descriptor = None
    try:
        if type(max_bytes) is not int or max_bytes <= 0:
            raise ValueError
        root = Path(root).absolute()
        descriptor = _directory(root)
        identity = _identity(descriptor)
        header = _read(descriptor, "HOST-INVENTORY.json", max_bytes)
        if header != b'{"kind":"host-private-inventory-v1"}':
            raise ValueError
        size, rows, identities = len(header), [], {}
        names = os.listdir(descriptor)
        if len(names) > 4096:
            raise ValueError
        for name in sorted(names):
            if name == "HOST-INVENTORY.json":
                continue
            match = _NAME.fullmatch(name)
            if match is None:
                raise ValueError
            raw = _read(descriptor, name, max_bytes - size)
            size += len(raw)
            row = CommandInventoryV1.model_validate_json(raw)
            if _PHASE[row.phase] != int(match[2]):
                raise ValueError
            previous = identities.setdefault(match[1], row)
            if (row.command_id, row.command_tag, row.release_id, row.mode, row.payload_hash, row.execution) != (
                    previous.command_id, previous.command_tag, previous.release_id, previous.mode,
                    previous.payload_hash, previous.execution):
                raise ValueError
            rows.append(row)
        _check(root, identity)
        return tuple(rows)
    except (OSError, ValueError, TypeError):
        raise InventoryFailure() from None
    finally:
        if descriptor is not None:
            os.close(descriptor)
