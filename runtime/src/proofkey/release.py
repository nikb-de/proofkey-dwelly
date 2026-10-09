"""Trusted, exact source preparation; static byte integrity is not reproduction."""
from datetime import datetime, timezone
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
import tomllib
import unicodedata

from pydantic import ConfigDict, Field

from .contracts import Hash, Identifier, SourceReleaseReceipt, Timestamp, WireModel
from .identity import fingerprint, validate_json


class ReleaseRightsError(ValueError):
    """Closed invalid context/rights/path/pin failure, never matched private bytes."""


class ReleasePreparationError(RuntimeError):
    def __init__(self, *, partial_output, failure_recorded):
        super().__init__("Release preparation failed; no valid receipt returned")
        self.partial_output = partial_output
        self.failure_recorded = failure_recorded


class ReleaseVerificationUnavailable(RuntimeError):
    pass


class ReleaseModel(WireModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid", revalidate_instances="always")


class RootIdentityV1(ReleaseModel):
    path: str
    device: int = Field(ge=0)
    inode: int = Field(ge=0)

    @classmethod
    def capture(cls, path):
        path = Path(path).absolute()
        value = path.stat(follow_symlinks=False)
        if not stat.S_ISDIR(value.st_mode):
            raise ReleaseRightsError("Invalid trusted directory")
        return cls(path=str(path), device=value.st_dev, inode=value.st_ino)


class ArtifactPinV1(ReleaseModel):
    path: str
    file_hash: Hash


class DependencyReleaseV1(ReleaseModel):
    pyproject_path: str
    lock_path: str
    inventory_path: str
    file_hashes: dict[str, Hash]
    notice_paths: list[str]
    artifacts: dict[Identifier, ArtifactPinV1]
    verification_mode: str


class SyntheticScanExceptionV1(ReleaseModel):
    path: str
    file_hash: Hash
    field: list[str]
    value_hash: Hash
    origin: Identifier


class SourceReleaseContextV1(ReleaseModel):
    source_root: RootIdentityV1
    output_parent: RootIdentityV1
    file_hashes: dict[str, Hash]
    rights_hash: Hash
    rights_evidence: list[Identifier]
    dependency: DependencyReleaseV1
    expected_candidate_hash: Hash
    groups: dict[Identifier, list[str]]
    max_files: int = Field(gt=0, le=4096)
    max_file_bytes: int = Field(gt=0, le=32 * 1024 * 1024)
    max_total_bytes: int = Field(gt=0, le=256 * 1024 * 1024)
    scan_exceptions: list[SyntheticScanExceptionV1]
    mode: str
    unsupported_modes: list[Identifier]
    captured_at: Timestamp


class RightsEntryV1(ReleaseModel):
    file_hash: Hash
    classification: Identifier
    origin: Identifier
    license: Identifier
    evidence_refs: list[Identifier] = Field(min_length=1, max_length=64)
    notices: list[str] = Field(min_length=1, max_length=64)
    include_in_release: bool
    public_rights: bool


class StaticReleaseVerificationV1(ReleaseModel):
    kind: str = "static_source_readback"
    outcome: str = "verified"
    candidate_hash: Hash
    release_hash: Hash
    observed_file_hashes: dict[str, Hash]
    manifest_hash: Hash
    context_hash: Hash
    mode: str
    unsupported_modes: list[Identifier]
    started_at: Timestamp
    ended_at: Timestamp


_CONTROLS = {"RELEASE-MANIFEST.json", "SOURCE-RECEIPT.json", "PREPARATION-PENDING.json", "PREPARATION-FAILED.json"}
_EXCLUDED = {"work", "outputs", "answers", "attachments", "organizer", "customer", "rawprovider",
             "privateeval", ".superpowers", ".git", "__pycache__", ".venv", "venv", "site-packages"}


def _deny():
    raise ReleaseRightsError("Invalid trusted release scope, rights or bytes")


def _hash(data):
    return sha256(data).hexdigest()


def _canonical_bytes(value):
    if isinstance(value, WireModel):
        value = value.model_dump(mode="json")
    validate_json(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def _relative(path):
    if (type(path) is not str or not path or path.startswith("/") or "\\" in path or "\0" in path
            or ":" in path or unicodedata.normalize("NFC", path) != path
            or len(path) > 1024 or len(path.split("/")) > 32
            or any(part in {"", ".", ".."} or part.casefold() in _EXCLUDED for part in path.split("/"))
            or path in _CONTROLS or path.lower().endswith((".sqlite", ".sqlite-wal", ".sqlite-shm", ".db", ".zip", ".tar", ".gz"))):
        _deny()
    return path.split("/")


def _directory(path):
    path = str(path)
    if not path.startswith("/") or any(part in {"", ".", ".."} for part in path.split("/")[1:]):
        _deny()
    descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for component in path.split("/")[1:]:
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _root(identity):
    descriptor = _directory(identity.path)
    value = os.fstat(descriptor)
    if (value.st_dev, value.st_ino) != (identity.device, identity.inode):
        os.close(descriptor)
        _deny()
    return descriptor


def _parents(root, components, *, create=False):
    descriptor = os.dup(root)
    try:
        for component in components:
            if create:
                try:
                    os.mkdir(component, mode=0o700, dir_fd=descriptor)
                except FileExistsError:
                    pass
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _identity(value):
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns


def _read(root, path, ceiling):
    components = path.split("/")
    parent = _parents(root, components[:-1])
    descriptor = None
    try:
        descriptor = os.open(components[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > ceiling:
            _deny()
        pieces, total = [], 0
        while True:
            piece = os.read(descriptor, min(65536, ceiling + 1 - total))
            if not piece:
                break
            pieces.append(piece)
            total += len(piece)
            if total > ceiling:
                _deny()
        after = os.fstat(descriptor)
        named = os.stat(components[-1], dir_fd=parent, follow_symlinks=False)
        if _identity(before) != _identity(after) or _identity(after) != _identity(named):
            _deny()
        return b"".join(pieces), _identity(after)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(parent)


def _write(root, path, data):
    components = path.split("/")
    parent = _parents(root, components[:-1], create=True)
    descriptor = None
    try:
        descriptor = os.open(components[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o600, dir_fd=parent)
        offset = 0
        while offset < len(data):
            written = os.write(descriptor, data[offset:])
            if written <= 0:
                raise OSError("Incomplete release write")
            offset += written
        os.fsync(descriptor)
        os.fsync(parent)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(parent)


def _context(context):
    if type(context) is not SourceReleaseContextV1:
        _deny()
    try:
        context = SourceReleaseContextV1.model_validate_json(context.model_dump_json())
        if (not context.rights_evidence or not context.file_hashes
                or len(context.file_hashes) > context.max_files
                or context.mode not in {"offline_synthetic", "replay", "unavailable"}
                or not {"native", "live", "reproduction", "rights_certification"} <= set(context.unsupported_modes)):
            _deny()
        normalized = set()
        for path in context.file_hashes:
            _relative(path)
            key = path.casefold()
            if key in normalized:
                _deny()
            normalized.add(key)
        groups = [path for paths in context.groups.values() for path in paths]
        if set(groups) != set(context.file_hashes) or len(groups) != len(set(groups)):
            _deny()
        dependency = context.dependency
        if (dependency.verification_mode not in {"static_unverified", "artifact_pinned"}
                or not dependency.notice_paths
                or any(context.file_hashes.get(path) != value for path, value in dependency.file_hashes.items())
                or not {dependency.pyproject_path, dependency.lock_path, dependency.inventory_path,
                        *dependency.notice_paths} <= dependency.file_hashes.keys()):
            _deny()
        for artifact in dependency.artifacts.values():
            if context.file_hashes.get(artifact.path) != artifact.file_hash:
                _deny()
        candidate = fingerprint({"kind": "SourceReleaseCandidateV1", "file_hashes": dict(sorted(context.file_hashes.items())),
            "rights_hash": context.rights_hash, "dependency_hash": _hash(_canonical_bytes(dependency)),
            "groups": context.groups})
        if candidate != context.expected_candidate_hash:
            _deny()
        return context
    except (ValueError, TypeError):
        _deny()


def _rights(context, rights_inventory):
    if type(rights_inventory) is not dict or set(rights_inventory) != set(context.file_hashes):
        _deny()
    approved = {}
    for path, raw in rights_inventory.items():
        if type(raw) is not dict:
            _deny()
        value = RightsEntryV1.model_validate(raw)
        if (value.classification not in {"owned", "synthetic", "public"} or not value.include_in_release
                or not value.public_rights or value.file_hash != context.file_hashes[path]
                or not value.evidence_refs or not value.notices
                or any(notice not in context.dependency.notice_paths for notice in value.notices)):
            _deny()
        approved[path] = value
    if _hash(_canonical_bytes({path: value.model_dump(mode="json") for path, value in approved.items()})) != context.rights_hash:
        _deny()
    return approved


def _json(data):
    depth, quoted, escaped = 0, False, False
    for byte in data:
        if quoted:
            if escaped:
                escaped = False
            elif byte == 92:
                escaped = True
            elif byte == 34:
                quoted = False
        elif byte == 34:
            quoted = True
        elif byte in (91, 123):
            depth += 1
            if depth > 64:
                _deny()
        elif byte in (93, 125):
            depth -= 1
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                _deny()
            result[key] = value
        return result
    def nonfinite(value):
        _deny()
    return json.loads(data, object_pairs_hook=pairs, parse_constant=nonfinite)


def _dependencies(context, contents):
    dependency = context.dependency
    project = tomllib.loads(contents[dependency.pyproject_path].decode("utf-8"))
    package, build = project.get("project", {}), project.get("build-system", {})
    if type(package) is not dict or type(build) is not dict:
        _deny()
    required, build_required = package.get("dependencies", []), build.get("requires", [])
    optional = package.get("optional-dependencies", {})
    if type(required) is not list or type(build_required) is not list or type(optional) is not dict:
        _deny()
    declared = required + build_required
    for values in optional.values():
        if type(values) is not list:
            _deny()
        declared += values
    def pins(values):
        result = {}
        for value in values:
            if type(value) is not str or not re.fullmatch(r"[A-Za-z0-9_.-]+==[^;\s]+", value):
                _deny()
            name, version = value.split("==", 1)
            name = re.sub(r"[-_.]+", "-", name).lower()
            if name in result and result[name] != version:
                _deny()
            result[name] = version
        return result
    locked = pins([line.strip() for line in contents[dependency.lock_path].decode("utf-8").splitlines()
                   if line.strip() and not line.lstrip().startswith("#")])
    if not locked or any(locked.get(name) != version for name, version in pins(declared).items()):
        _deny()
    metadata = _json(contents[dependency.inventory_path])
    records = metadata.get("dependencies") if type(metadata) is dict else None
    if type(records) is not list or not records or len(records) > context.max_files:
        _deny()
    observed = {}
    for item in records:
        if (type(item) is not dict or type(item.get("name")) is not str or type(item.get("version")) is not str
                or type(item.get("license")) is not str or not item["license"].strip()
                or item.get("notice") not in dependency.notice_paths):
            _deny()
        name = re.sub(r"[-_.]+", "-", item["name"]).lower()
        if name in observed:
            _deny()
        observed[name] = item["version"]
    if observed != locked or any(not contents[path].strip() for path in dependency.notice_paths):
        _deny()
    if (not dependency.artifacts.keys() <= locked.keys()
            or dependency.verification_mode == "artifact_pinned" and dependency.artifacts.keys() != locked.keys()):
        _deny()


_SENSITIVE = re.compile(rb"(?i)(?:-----BEGIN[^\n]*PRIVATE KEY-----|\bsk-[A-Za-z0-9]{12,}|"
    rb"[\"']?(?:api[_-]?key|access[_-]?token|password|secret|authorization)[\"']?\s*[=:]\s*[\"']?[^\s\"']{8,}|"
    rb"ORGANIZER PRIVATE|PRIVATE RECORDING|RAW PROVIDER OUTPUT)")
_PRIVATE = re.compile(rb"(?i)(?:-----BEGIN[^\n]*PRIVATE KEY-----|"
    rb"ORGANIZER PRIVATE|PRIVATE RECORDING|RAW PROVIDER OUTPUT)")


def _scan(context, path, data, rights):
    # A narrow synthetic credential exception never clears raw private markers.
    if _PRIVATE.search(data):
        _deny()
    exceptions = [item for item in context.scan_exceptions if item.path == path]
    if exceptions or path.lower().endswith(".json"):
        value = _json(data)
        data = _canonical_bytes(value)
        if _PRIVATE.search(data):
            _deny()
    if exceptions:
        fields = set()
        for exception in exceptions:
            if (rights.classification != "synthetic" or exception.origin != rights.origin
                    or exception.file_hash != context.file_hashes[path]
                    or not exception.field or len(exception.field) > 16 or tuple(exception.field) in fields):
                _deny()
            fields.add(tuple(exception.field))
            current = value
            for key in exception.field[:-1]:
                if type(current) is not dict or key not in current:
                    _deny()
                current = current[key]
            key = exception.field[-1]
            if (type(current) is not dict or key not in current or type(current[key]) is not str
                    or _hash(_canonical_bytes(current[key])) != exception.value_hash):
                _deny()
            current[key] = ""
        data = _canonical_bytes(value)
    if _SENSITIVE.search(data):
        _deny()


def _inventory(root, intended):
    directories = {"/".join(path.split("/")[:index]) for path in intended
                   for index in range(1, len(path.split("/")))}
    observed, count = set(), 0
    def visit(descriptor, prefix):
        nonlocal count
        with os.scandir(descriptor) as entries:
            for entry in entries:
                count += 1
                if count > len(intended) + len(directories):
                    _deny()
                path = prefix + entry.name
                value = entry.stat(follow_symlinks=False)
                if stat.S_ISDIR(value.st_mode) and path in directories:
                    child = os.open(entry.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
                    try:
                        visit(child, path + "/")
                    finally:
                        os.close(child)
                elif stat.S_ISREG(value.st_mode) and path in intended and value.st_nlink == 1:
                    observed.add(path)
                else:
                    _deny()
    visit(root, "")
    if observed != intended:
        _deny()


def _verify_copied(root, context):
    for path, expected in context.file_hashes.items():
        data, _ = _read(root, path, context.max_file_bytes)
        if _hash(data) != expected:
            _deny()


def _release_hash(receipt):
    return fingerprint({"kind": "SourceReleaseReceiptV1", **receipt.model_dump(mode="json", exclude={"release_hash"})})


def prepare_release(source_root, rights_inventory, output_root, *, context=None):
    context = _context(context)
    source = parent = output = None
    claimed = False
    try:
        destination = Path(output_root).absolute()
        rights = _rights(context, rights_inventory)
        if (str(Path(source_root).absolute()) != context.source_root.path
                or str(destination.parent) != context.output_parent.path
                or destination == Path(context.source_root.path)
                or destination in Path(context.source_root.path).parents
                or Path(context.source_root.path) in destination.parents):
            _deny()
        _relative(destination.name)
        source, parent = _root(context.source_root), _root(context.output_parent)
        originals, contents, total = {}, {}, 0
        for path, expected in context.file_hashes.items():
            data, identity = _read(source, path, context.max_file_bytes)
            total += len(data)
            if _hash(data) != expected or total > context.max_total_bytes:
                _deny()
            originals[path] = identity
            contents[path] = data
            _scan(context, path, data, rights[path])
        if (len(context.scan_exceptions) > 64
                or any(item.path not in context.file_hashes for item in context.scan_exceptions)):
            _deny()
        _dependencies(context, contents)
        fcntl.flock(parent, fcntl.LOCK_EX | fcntl.LOCK_NB)
        os.mkdir(destination.name, mode=0o700, dir_fd=parent)
        claimed = True
        output = os.open(destination.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        output_stat = os.fstat(output)
        output_identity = RootIdentityV1(path=str(destination), device=output_stat.st_dev, inode=output_stat.st_ino)
        _write(output, "PREPARATION-PENDING.json", _canonical_bytes({"kind": "release_pending"}))
        for path, expected in context.file_hashes.items():
            data, identity = _read(source, path, context.max_file_bytes)
            if identity != originals[path] or _hash(data) != expected:
                _deny()
            _write(output, path, data)
            actual, _ = _read(output, path, context.max_file_bytes)
            if _hash(actual) != expected:
                _deny()
        for path, expected in context.file_hashes.items():
            data, identity = _read(source, path, context.max_file_bytes)
            if identity != originals[path] or _hash(data) != expected:
                _deny()
        _inventory(output, set(context.file_hashes) | {"PREPARATION-PENDING.json"})
        _verify_copied(output, context)
        for identity in (context.source_root, context.output_parent, output_identity):
            checked = _root(identity)
            os.close(checked)
        receipt = SourceReleaseReceipt(candidate_hash=context.expected_candidate_hash, file_hashes=context.file_hashes,
            rights_hash=context.rights_hash, dependency_hash=_hash(_canonical_bytes(context.dependency)),
            release_hash="0" * 64, created_at=datetime.now(timezone.utc))
        receipt = receipt.model_copy(update={"release_hash": _release_hash(receipt)})
        manifest = {"kind": "SourceReleaseManifestV1", "context_hash": fingerprint(context.model_dump(mode="json")),
            "release_root": output_identity.model_dump(mode="json"), "groups": context.groups,
            "mode": context.mode, "unsupported_modes": context.unsupported_modes, "receipt": receipt.model_dump(mode="json")}
        _write(output, "RELEASE-MANIFEST.json", _canonical_bytes(manifest))
        _write(output, "SOURCE-RECEIPT.json", _canonical_bytes(receipt))
        os.fsync(output)
        _inventory(output, set(context.file_hashes) | {"PREPARATION-PENDING.json", "RELEASE-MANIFEST.json", "SOURCE-RECEIPT.json"})
        _verify_copied(output, context)
        for path, expected in (("RELEASE-MANIFEST.json", _canonical_bytes(manifest)),
                               ("SOURCE-RECEIPT.json", _canonical_bytes(receipt))):
            actual, _ = _read(output, path, context.max_total_bytes)
            if actual != expected:
                _deny()
        checked = _root(output_identity)
        os.close(checked)
        # No fallible publication follows removal. A crash may conservatively
        # retain pending; static readback never treats that as complete.
        os.unlink("PREPARATION-PENDING.json", dir_fd=output)
        return receipt
    except (OSError, ValueError, TypeError):
        if not claimed:
            _deny()
        recorded = False
        if output is not None:
            try:
                _write(output, "PREPARATION-FAILED.json", _canonical_bytes({"kind": "release_failed",
                    "reason": "preparation_failed", "valid_receipt": False}))
                recorded = True
            except (OSError, ValueError, TypeError):
                pass
        raise ReleasePreparationError(partial_output=str(destination), failure_recorded=recorded) from None
    finally:
        for descriptor in (output, parent, source):
            if descriptor is not None:
                os.close(descriptor)


def verify_release_static(receipt, *, release_root, context):
    started = datetime.now(timezone.utc)
    context = _context(context)
    descriptor = parent = None
    try:
        if type(receipt) is not SourceReleaseReceipt:
            _deny()
        receipt = SourceReleaseReceipt.model_validate_json(receipt.model_dump_json())
        root = RootIdentityV1.capture(release_root)
        if str(Path(root.path).parent) != context.output_parent.path:
            _deny()
        parent = _root(context.output_parent)
        descriptor = _root(root)
        raw, _ = _read(descriptor, "RELEASE-MANIFEST.json", context.max_total_bytes)
        manifest = _json(raw)
        saved, _ = _read(descriptor, "SOURCE-RECEIPT.json", context.max_total_bytes)
        if (manifest != {"kind": "SourceReleaseManifestV1", "context_hash": fingerprint(context.model_dump(mode="json")),
                "release_root": root.model_dump(mode="json"), "groups": context.groups, "mode": context.mode,
                "unsupported_modes": context.unsupported_modes, "receipt": receipt.model_dump(mode="json")}
                or _json(saved) != receipt.model_dump(mode="json") or _canonical_bytes(manifest) != raw
                or _canonical_bytes(receipt) != saved
                or dict(receipt.file_hashes) != dict(context.file_hashes)
                or receipt.candidate_hash != context.expected_candidate_hash or receipt.rights_hash != context.rights_hash
                or receipt.dependency_hash != _hash(_canonical_bytes(context.dependency)) or receipt.release_hash != _release_hash(receipt)):
            _deny()
        intended = set(context.file_hashes) | {"RELEASE-MANIFEST.json", "SOURCE-RECEIPT.json"}
        _inventory(descriptor, intended)
        hashes = {}
        for path, expected in context.file_hashes.items():
            data, _ = _read(descriptor, path, context.max_file_bytes)
            hashes[path] = _hash(data)
            if hashes[path] != expected:
                _deny()
        for identity in (context.output_parent, root):
            checked = _root(identity)
            os.close(checked)
        return StaticReleaseVerificationV1(candidate_hash=receipt.candidate_hash, release_hash=receipt.release_hash,
            observed_file_hashes=hashes, manifest_hash=_hash(raw), context_hash=fingerprint(context.model_dump(mode="json")),
            mode=context.mode, unsupported_modes=context.unsupported_modes, started_at=started,
            ended_at=datetime.now(timezone.utc))
    except (OSError, ValueError, TypeError):
        _deny()
    finally:
        for value in (descriptor, parent):
            if value is not None:
                os.close(value)


def verify_release(receipt, *, release_root, context, reproduction_plan):
    raise ReleaseVerificationUnavailable("Actual reproduction is unavailable; static readback is not reproduction")
