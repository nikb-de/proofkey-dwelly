"""Creator-owned cooperative lock for fixed local runtime resources."""
import fcntl
import errno
import os
from pathlib import Path
import stat
import threading


class RuntimeWriterFailure(ValueError):
    def __init__(self, code):
        if code not in {'writer_busy', 'writer_scope', 'writer_storage'}:
            code = 'writer_storage'
        self.code = code
        super().__init__(code)


_NAME = '.proofkey-resource-writer.lock'
_DIRECTORY = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


def _scope():
    raise RuntimeWriterFailure('writer_scope')


def _identity(value):
    return value.st_dev, value.st_ino


def _lock_valid(value):
    if (not stat.S_ISREG(value.st_mode) or value.st_nlink != 1 or value.st_size != 0
            or value.st_uid != os.geteuid() or value.st_mode & 0o077):
        _scope()


def _close_owned(descriptors):
    failed = False
    while descriptors:
        descriptor = descriptors.pop()
        try:
            os.close(descriptor)
        except OSError:
            failed = True
    if failed:
        raise RuntimeWriterFailure('writer_storage') from None


def _directory(root):
    owned = []
    try:
        owned.append(os.open(root.anchor, _DIRECTORY))
        for part in root.parts[1:]:
            owned.append(os.open(part, _DIRECTORY, dir_fd=owned[-1]))
        result = owned.pop()
    except BaseException:
        _close_owned(owned)
        raise
    try:
        _close_owned(owned)
    except BaseException:
        _close_owned([result])
        raise
    return result


def _error(error):
    if isinstance(error, RuntimeWriterFailure):
        return error.code
    if isinstance(error, OSError) and error.errno in (errno.ELOOP, errno.ENOTDIR, errno.EISDIR, errno.ENOENT):
        return 'writer_scope'
    if isinstance(error, (TypeError, ValueError)):
        return 'writer_scope'
    return 'writer_storage'


class RuntimeWriterLease:
    def __init__(self, root: Path):
        self._owner = threading.get_ident()
        self._root_fd = self._lock_fd = None
        self._closed = False
        self._locked = False
        self._uncertain = False
        self._cleanup_attempted = False
        try:
            if (type(root) is not type(Path()) or not root.is_absolute() or '..' in root.parts
                    or len(root.parts) > 64 or len(str(root)) > 1024):
                _scope()
            resolved = root.resolve(strict=True)
            forbidden = (Path('/'), Path.home(), Path.cwd())
            identities = {_identity(item.stat()) for item in forbidden}
            if resolved in tuple(item.resolve() for item in forbidden) or _identity(root.stat()) in identities:
                _scope()
            self._root = root
            self._root_fd = _directory(root)
            root_stat = os.fstat(self._root_fd)
            if root_stat.st_uid != os.geteuid():
                _scope()
            self._root_identity = _identity(root_stat)
            try:
                _lock_valid(os.stat(_NAME, dir_fd=self._root_fd, follow_symlinks=False))
            except FileNotFoundError:
                pass
            self._lock_fd = os.open(_NAME,
                os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=self._root_fd)
            _lock_valid(os.fstat(self._lock_fd))
            self._lock_identity = _identity(os.fstat(self._lock_fd))
            try:
                fcntl.flock(self._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise RuntimeWriterFailure('writer_busy') from None
            self._locked = True
            self.check()
        except BaseException as error:
            self.close()
            if isinstance(error, (OSError, TypeError, ValueError)):
                raise RuntimeWriterFailure(_error(error)) from None
            raise

    def __reduce_ex__(self, protocol):
        _scope()

    def check(self) -> None:
        if threading.get_ident() != self._owner:
            raise RuntimeWriterFailure('writer_scope')
        if self._uncertain:
            raise RuntimeWriterFailure('writer_storage')
        if self._closed:
            raise RuntimeWriterFailure('writer_scope')
        descriptor = None
        try:
            descriptor = _directory(self._root)
            value = os.fstat(descriptor)
            if _identity(value) != self._root_identity or value.st_uid != os.geteuid():
                _scope()
            held = os.fstat(self._lock_fd)
            named = os.stat(_NAME, dir_fd=descriptor, follow_symlinks=False)
            _lock_valid(held)
            _lock_valid(named)
            if _identity(held) != self._lock_identity or _identity(named) != self._lock_identity:
                _scope()
        except (OSError, TypeError, ValueError) as error:
            raise RuntimeWriterFailure(_error(error)) from None
        finally:
            if descriptor is not None:
                try:
                    _close_owned([descriptor])
                except RuntimeWriterFailure:
                    self._uncertain = True
                    raise

    def close(self) -> None:
        if threading.get_ident() != self._owner:
            raise RuntimeWriterFailure('writer_scope')
        if self._uncertain and self._cleanup_attempted:
            raise RuntimeWriterFailure('writer_storage')
        if self._closed:
            return
        if self._lock_fd is not None:
            if self._locked:
                try:
                    fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
                except OSError:
                    self._uncertain = True
            self._locked = False
            descriptor = self._lock_fd
            self._lock_fd = None
            try:
                os.close(descriptor)
            except OSError:
                self._uncertain = True
        if self._root_fd is not None:
            descriptor = self._root_fd
            self._root_fd = None
            try:
                os.close(descriptor)
            except OSError:
                self._uncertain = True
        self._cleanup_attempted = True
        if self._uncertain:
            raise RuntimeWriterFailure('writer_storage') from None
        self._closed = True
