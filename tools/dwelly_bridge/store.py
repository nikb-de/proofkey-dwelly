"""Private, durable shadow observations; no source or runtime dependencies."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import stat
import time


_LIMIT = 64 * 1024
_FILES = ("shadow.sqlite3", "shadow.sqlite3-journal", "shadow.sqlite3-wal", "shadow.sqlite3-shm")


class ShadowStoreError(ValueError):
    """A bounded storage failure with no input or operating-system details."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _canonical(value, code):
    """Reject Python-only values and excessive nesting before JSON encoding."""
    def check(item, depth):
        if depth > 64:
            raise ShadowStoreError(code)
        kind = type(item)
        if item is None or kind in (str, bool, int):
            return
        if kind is float and math.isfinite(item):
            return
        if kind is list:
            for child in item:
                check(child, depth + 1)
            return
        if kind is dict:
            for key, child in item.items():
                if type(key) is not str:
                    raise ShadowStoreError(code)
                check(child, depth + 1)
            return
        raise ShadowStoreError(code)

    if type(value) is not dict or not value:
        raise ShadowStoreError(code)
    try:
        check(value, 0)
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=True, allow_nan=False)
        if len(encoded.encode("utf-8")) > _LIMIT:
            raise ShadowStoreError(code)
        return encoded
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise ShadowStoreError(code) from None


def _private_directory(metadata):
    return (stat.S_ISDIR(metadata.st_mode) and metadata.st_uid == os.getuid()
            and metadata.st_mode & 0o077 == 0)


def _private_file(metadata):
    return (stat.S_ISREG(metadata.st_mode) and metadata.st_uid == os.getuid()
            and metadata.st_nlink == 1 and metadata.st_mode & 0o077 == 0)


def _content_fingerprint(value, code):
    comparable = value.copy()
    if type(comparable.get("target")) is dict:
        comparable["target"] = comparable["target"].copy()
        comparable["target"].pop("checked_at", None)
    return hashlib.sha256(_canonical(comparable, code).encode()).hexdigest()


class ShadowStore:
    """Store one immutable complete record per logical import identity.

    Instances retain no connection. A directory lock serializes both initial
    database creation and transactions across independent local processes.
    SQLite's FULL synchronous mode commits records before they are returned.
    """

    def __init__(self, root):
        try:
            candidate = Path(root)
            if ".." in candidate.parts:
                raise ShadowStoreError("unsafe_shadow_directory")
            self.root = candidate.absolute()
            self._check_components()
            self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
            if not _private_directory(self.root.lstat()):
                raise ShadowStoreError("unsafe_shadow_directory")
            self.database = self.root / _FILES[0]
        except (OSError, TypeError, ValueError):
            raise ShadowStoreError("unsafe_shadow_directory") from None
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("""CREATE TABLE IF NOT EXISTS records (
                identity TEXT PRIMARY KEY NOT NULL,
                import_id TEXT UNIQUE NOT NULL,
                fingerprint TEXT NOT NULL,
                record TEXT NOT NULL)""")
            connection.commit()

    def _check_components(self):
        for component in (self.root, *self.root.parents):
            if component.is_symlink():
                raise ShadowStoreError("unsafe_shadow_directory")

    def _check_files(self):
        for name in _FILES:
            try:
                metadata = (self.root / name).lstat()
            except FileNotFoundError:
                continue
            if not _private_file(metadata):
                raise ShadowStoreError("unsafe_shadow_database")

    @contextmanager
    def _connection(self):
        directory_fd = database_fd = None
        connection = None
        try:
            self._check_components()
            directory_fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            directory_stat = os.fstat(directory_fd)
            if not _private_directory(directory_stat):
                raise ShadowStoreError("unsafe_shadow_directory")
            deadline = time.monotonic() + 10
            while True:
                try:
                    fcntl.flock(directory_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise ShadowStoreError("shadow_storage_busy") from None
                    time.sleep(0.01)
            current_stat = self.root.lstat()
            if ((directory_stat.st_dev, directory_stat.st_ino) !=
                    (current_stat.st_dev, current_stat.st_ino)):
                raise ShadowStoreError("unsafe_shadow_directory")
            self._check_files()
            database_fd = os.open(_FILES[0], os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,
                                  0o600, dir_fd=directory_fd)
            if not _private_file(os.fstat(database_fd)):
                raise ShadowStoreError("unsafe_shadow_database")
            connection = sqlite3.connect(str(self.database), timeout=10)
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("PRAGMA journal_mode=DELETE")
            self._check_files()
            yield connection
            self._check_files()
            os.fsync(directory_fd)
        except ShadowStoreError:
            raise
        except (sqlite3.Error, OSError, ValueError, TypeError, OverflowError):
            raise ShadowStoreError("shadow_storage_error") from None
        finally:
            if connection is not None:
                connection.close()
            if database_fd is not None:
                os.close(database_fd)
            if directory_fd is not None:
                os.close(directory_fd)

    def record(self, identity, content):
        identity_json = _canonical(identity, "invalid_shadow_identity")
        content_json = _canonical(content, "invalid_shadow_content")
        value = json.loads(content_json)
        if "import_id" in value or ("target" in value and value["target"] is not None
                                    and type(value["target"]) is not dict):
            raise ShadowStoreError("invalid_shadow_content")
        fingerprint = _content_fingerprint(value, "invalid_shadow_content")
        import_id = hashlib.sha256(identity_json.encode()).hexdigest()
        value["import_id"] = import_id
        record_json = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT fingerprint, record FROM records WHERE identity = ?",
                                     (identity_json,)).fetchone()
            if row is not None:
                if row[0] != fingerprint:
                    raise ShadowStoreError("idempotency_conflict")
                try:
                    if type(row[1]) is not str or len(row[1]) > _LIMIT + 128:
                        raise ShadowStoreError("shadow_storage_error")
                    result = json.loads(row[1])
                except (TypeError, ValueError):
                    raise ShadowStoreError("shadow_storage_error") from None
                if type(result) is not dict or result.get("import_id") != import_id:
                    raise ShadowStoreError("shadow_storage_error")
                stored_content = result.copy()
                del stored_content["import_id"]
                if _content_fingerprint(stored_content, "shadow_storage_error") != fingerprint:
                    raise ShadowStoreError("shadow_storage_error")
                connection.rollback()
                return result
            connection.execute("INSERT INTO records VALUES (?, ?, ?, ?)",
                               (identity_json, import_id, fingerprint, record_json))
            connection.commit()
        return value
