"""Trusted service catalog; construction and register scope are not request-body API.

The resolver receives (AuthContext, ArtifactRecord, immutable scope, purpose).
Only the literal True authorizes access. Roots, scope and derivative policies
are configured by the hosting service, never by narrative/model instructions.
"""
import hashlib
import json
import os
import stat
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType

from proofkey.contracts import ArtifactRecord, AuthContext, EvidenceAssertion, UnknownLocator, Locator
from pydantic import TypeAdapter
from proofkey.identity import fingerprint


class EvidenceAccessDenied(PermissionError):
    pass


class EvidencePathError(ValueError):
    pass


class UTCClock:
    def now(self):
        return datetime.now(timezone.utc)


def _freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _safe_path(path):
    raw = os.fspath(path)
    if "://" in raw or "\x00" in raw:
        raise EvidencePathError("Only permitted local paths are accepted")
    if ".." in Path(raw).parts:
        raise EvidencePathError("Parent traversal is forbidden")
    path = Path(os.path.abspath(raw))
    for parent in [path, *path.parents]:
        if parent.is_symlink():
            raise EvidencePathError("Symlink paths are forbidden")
    return path


def _open_parent(path):
    """Walk directories with no-follow descriptors, including ancestor races."""
    path = _safe_path(path)
    fd = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for component in path.parts[1:-1]:
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd, path.name
    except BaseException:
        os.close(fd)
        raise


def _bounded_read(path, limit, *, private=False):
    directory = None
    try:
        directory, name = _open_parent(path)
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
                raise EvidencePathError("Not a permitted finite regular file")
            if private and info.st_mode & 0o077:
                raise EvidencePathError("Catalog storage permissions are not private")
            payload = stream.read(limit + 1)
    except OSError as exc:
        raise EvidencePathError("Local bytes unavailable") from exc
    finally:
        if directory is not None:
            os.close(directory)
    if len(payload) > limit:
        raise EvidencePathError("Byte limit exceeded")
    return payload


def _mime(payload, suffix):
    if payload.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if payload.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if payload.startswith(b"%PDF-"):
        return "application/pdf"
    if payload[:4] == b"RIFF" and payload[8:12] == b"WAVE":
        return "audio/wav"
    if payload.startswith(b"ID3") or payload[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return "audio/mpeg"
    return {".txt": "text/plain", ".json": "application/json", ".transcript": "text/x-supplied-transcript",
            ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".pdf": "application/pdf", ".wav": "audio/wav", ".mp3": "audio/mpeg"}.get(suffix.lower(), "application/octet-stream")


class EvidenceCatalog:
    def __init__(self, root, clock=None, *, allowed_input_roots, access_resolver,
                 max_bytes=8 * 1024 * 1024, derivative_policies=None):
        if type(max_bytes) is not int or not 0 < max_bytes <= 8 * 1024 * 1024:
            raise ValueError("Catalog byte ceiling must be finite and at most 8 MiB")
        if not callable(access_resolver):
            raise ValueError("A trusted proof resolver is required")
        self.root = _safe_path(root)
        self.clock = clock or UTCClock()
        self.max_bytes = max_bytes
        self.allowed_input_roots = tuple(_safe_path(item) for item in allowed_input_roots)
        if not self.allowed_input_roots:
            raise ValueError("Explicit permitted input roots required")
        self.access_resolver = access_resolver
        self.derivative_policies = _freeze(json.loads(json.dumps(derivative_policies or {}, allow_nan=False)))
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.root.stat().st_mode & 0o077:
            raise EvidencePathError("Catalog root must have private permissions")
        for name in ("objects", "records", "assertions", "receipts"):
            directory = _safe_path(self.root / name)
            directory.mkdir(exist_ok=True, mode=0o700)
            if directory.stat().st_mode & 0o077:
                raise EvidencePathError("Catalog directories must have private permissions")

    def read_permitted_local_bytes(self, path):
        path = _safe_path(path)
        if not any(path.is_relative_to(root) for root in self.allowed_input_roots):
            raise EvidencePathError("Input path is outside trusted roots")
        return _bounded_read(path, self.max_bytes)

    def _store(self, path, payload):
        if len(payload) > self.max_bytes:
            raise EvidencePathError("Catalog storage byte ceiling exceeded")
        path = _safe_path(path)
        directory = None
        try:
            directory, name = _open_parent(path)
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
        except FileExistsError:
            if _bounded_read(path, self.max_bytes, private=True) != payload:
                raise EvidencePathError("Stored content collision")
            return
        except OSError as exc:
            raise EvidencePathError("Private catalog storage unavailable") from exc
        finally:
            if directory is not None:
                os.close(directory)
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())

    def _persist(self, payload, case_id, source, scope, mime, parents=(), policy=None):
        scope = json.loads(json.dumps(scope, allow_nan=False))
        if not isinstance(scope, dict) or not scope.get("allowed_actors") or not all(
                isinstance(actor, str) and actor for actor in scope["allowed_actors"]):
            raise ValueError("Trusted explicit source scope required")
        digest = hashlib.sha256(payload).hexdigest()
        identifier = "artifact-" + uuid.uuid4().hex
        record = ArtifactRecord(artifact_id=identifier, original_hash=digest, mime_type=mime,
            source=source, case_id=case_id, access="restricted", created_at=self.clock.now(),
            lineage_hash=fingerprint({"bytes": digest, "parents": list(parents), "scope": scope,
                                      "case": case_id, "source": source, "policy": policy}),
            parent_hashes=list(parents), source_reference="private-catalog:" + identifier)
        envelope = {"record": record.model_dump(mode="json"), "scope": scope, "policy": policy}
        encoded = json.dumps(envelope, sort_keys=True, allow_nan=False).encode()
        if len(encoded) > self.max_bytes:
            raise EvidencePathError("Catalog metadata byte ceiling exceeded")
        self._store(self.root / "objects" / digest, payload)
        self._store(self.root / "records" / (identifier + ".json"), encoded)
        return record

    def register(self, path, case_id, source, scope):
        payload = self.read_permitted_local_bytes(path)
        return self._persist(payload, case_id, source, scope, _mime(payload, Path(path).suffix))

    def _load(self, artifact_id):
        if not isinstance(artifact_id, str) or not artifact_id.startswith("artifact-") or len(artifact_id) != 41 or any(
                ch not in "0123456789abcdef" for ch in artifact_id[9:]):
            raise EvidenceAccessDenied("Evidence unavailable or denied")
        try:
            envelope = json.loads(_bounded_read(self.root / "records" / (artifact_id + ".json"), self.max_bytes, private=True))
            record = ArtifactRecord.model_validate(envelope["record"])
            if record.artifact_id != artifact_id:
                raise ValueError("Mismatched stored identity")
            return record, envelope
        except (ValueError, KeyError, TypeError) as exc:
            raise EvidenceAccessDenied("Evidence unavailable or denied") from exc

    def get(self, artifact_id, auth=None, *, purpose="read"):
        if not isinstance(auth, AuthContext):
            raise EvidenceAccessDenied("Evidence unavailable or denied")
        record, envelope = self._load(artifact_id)
        expected = fingerprint({"bytes": record.original_hash, "parents": list(record.parent_hashes),
            "scope": envelope["scope"], "case": record.case_id, "source": record.source, "policy": envelope["policy"]})
        if expected != record.lineage_hash:
            raise EvidenceAccessDenied("Evidence unavailable or denied")
        try:
            permitted = self.access_resolver(auth, record, _freeze(envelope["scope"]), purpose)
        except Exception as exc:
            raise EvidenceAccessDenied("Evidence unavailable or denied") from exc
        if permitted is not True:
            raise EvidenceAccessDenied("Evidence unavailable or denied")
        return record

    def resolve_record(self, record, auth=None, *, purpose="inspect"):
        if not isinstance(record, ArtifactRecord):
            raise EvidenceAccessDenied("Evidence unavailable or denied")
        trusted = self.get(record.artifact_id, auth, purpose=purpose)
        if trusted != record:
            raise EvidenceAccessDenied("Evidence unavailable or denied")
        return trusted

    def read_original(self, artifact_id, auth=None, *, purpose="read", max_bytes=None):
        record = self.get(artifact_id, auth, purpose=purpose)
        payload = _bounded_read(self.root / "objects" / record.original_hash,
                               min(self.max_bytes, max_bytes if max_bytes is not None else self.max_bytes), private=True)
        if hashlib.sha256(payload).hexdigest() != record.original_hash:
            raise EvidencePathError("Stored bytes failed integrity check")
        return payload

    def assertion(self, artifact_id, content, locator=None, *, auth=None):
        record = self.get(artifact_id, auth, purpose="assertion")
        from proofkey.evidence.intake import inspect_content, IntakeLimits
        receipt = inspect_content(record, IntakeLimits(max_bytes=self.max_bytes), catalog=self, auth=auth)
        locator = TypeAdapter(Locator).validate_python(locator or UnknownLocator(reason="source_coordinates_not_supplied"))
        if locator.kind != "unknown":
            if receipt.status != "completed":
                raise ValueError("Coordinates require a successfully decoded original")
            _validate_locator(locator, receipt.available_coordinates)
        assertion = EvidenceAssertion(artifact_id=artifact_id, claim=content,
            content_hash=hashlib.sha256(content.encode()).hexdigest(), lineage_hash=record.lineage_hash,
            locator=locator, uncertainty="unverified", processing_receipt_id=receipt.invocation_id)
        self._store(self.root / "assertions" / (artifact_id + "-" + uuid.uuid4().hex + ".json"),
                    assertion.model_dump_json().encode())
        return assertion

    def assertions(self, artifact_id, auth=None):
        self.get(artifact_id, auth, purpose="assertion")
        return [EvidenceAssertion.model_validate_json(_bounded_read(path, self.max_bytes, private=True))
                for path in sorted((self.root / "assertions").glob(artifact_id + "-*.json"))]


def _validate_locator(locator, coordinates):
    matching = [item for item in coordinates if item.kind == locator.kind]
    if locator.kind == "text_span" and matching and locator.end <= matching[0].end:
        return
    if locator.kind == "audio_time" and matching and locator.end_seconds <= matching[0].end_seconds:
        return
    if locator.kind == "page_region":
        pages = [item for item in matching if item.page == locator.page]
        if pages:
            if locator.region is None:
                return
            region, bounds = locator.region, pages[0].region
            if bounds is not None:
                width, height = (1, 1) if region.units == "normalized" else (bounds.width, bounds.height)
                if region.x + region.width <= width and region.y + region.height <= height:
                    return
    raise ValueError("Coordinates exceed or are unavailable in the decoded source")
