"""Bounded synthetic preparation primitives; neither runtime nor authority.

Private helpers are shared only by this module's preparation API. Snapshots
carry bytes and identities, never open descriptors or caller-owned containers.
"""
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import stat
from uuid import uuid4

from .bootstrap import _PathPins
from .clock import SyntheticReplayClock
from .contracts import CanonicalRequest, EnvironmentProfile
from .host import (_PROFILE_RAW as _PINNED_PROFILE_FILE, _PROFILE as _PINNED_PROFILE,
                   _PROCESS as _PINNED_PROCESS, _POLICY as _PINNED_POLICY)
from .host_admission import (AdmissionCompositionFailure, FIXED_IMPLEMENTATION_PATHS,
                             control_context, _id)
from .host_contracts import parse_command
from .host_files import _read, _write
from .identity import request_fingerprint
from .profiles import validate_profile
from .registered_releases import ReleaseArtifactV1, ReleaseBlobV1, _POLICY

_MIB = 1048576
_CHILDREN = ("data", "resources", "control", "inventories", "outputs")


class SyntheticPreparationFailureV1(ValueError):
    def __init__(self, code, *, retained_root=None):
        self.code = code if code in {"invalid_input", "invalid_target", "timeout",
                                    "io_failure", "identity_changed"} else "invalid_input"
        self.retained_root = retained_root
        super().__init__(self.code)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _require(condition, code="invalid_input"):
    if not condition:
        raise SyntheticPreparationFailureV1(code)


def _boundary(clock, execution):
    _require(type(clock) is SyntheticReplayClock)
    try:
        control_context(execution, clock)
    except AdmissionCompositionFailure as error:
        raise SyntheticPreparationFailureV1("timeout" if error.code == "timeout"
                                            else "invalid_input") from None


def _request_snapshot(request, host_release_id):
    _require(type(request) is CanonicalRequest)
    command = parse_command(dict(tag="run", release_id=host_release_id,
                                 request=request.model_dump(mode="json")))
    _require(command.request.kind in {"reschedule_window", "goods_refusal"}
             and command.request.narrative is None and not command.request.evidence_ids)
    return command.request


@dataclass(frozen=True, slots=True)
class SyntheticCaseReleaseSpecV1:
    host_release_id: str
    registered_release_id: str
    resource_id: str
    request: CanonicalRequest = field(repr=False)
    fixture_bytes: bytes = field(repr=False)

    def __post_init__(self):
        try:
            _require(type(self) is SyntheticCaseReleaseSpecV1)
            for value in (self.host_release_id, self.registered_release_id, self.resource_id):
                _id(value)
                _canonical(value)
            _require(type(self.fixture_bytes) is bytes and 0 < len(self.fixture_bytes) <= _MIB)
            object.__setattr__(self, "request", _request_snapshot(self.request, self.host_release_id))
        except Exception:
            raise SyntheticPreparationFailureV1("invalid_input") from None


@dataclass(frozen=True, slots=True, repr=False)
class _ValidatedInput:
    host_release_id: str
    registered_release_id: str
    resource_id: str
    request: CanonicalRequest
    fixture_bytes: bytes
    business_fingerprint: str
    profile_bytes: bytes
    declarations: tuple[tuple[str, bytes], ...]
    implementations: tuple[ReleaseBlobV1, ...]


def _fixture_json(raw):
    # Count containers before the recursive decoder sees untrusted input.
    text = raw.decode("utf-8")
    depth, quoted, escaped = 0, False, False
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            depth += 1
            _require(depth <= 64)
        elif char in "]}":
            depth -= 1
            _require(depth >= 0)
    _require(not quoted and depth == 0)

    def pairs(items):
        result = {}
        for key, value in items:
            _require(key not in result)
            result[key] = value
        return result

    def nonfinite(_):
        raise SyntheticPreparationFailureV1("invalid_input")

    value = json.loads(text, object_pairs_hook=pairs, parse_constant=nonfinite)
    pending = [value]
    while pending:
        item = pending.pop()
        if type(item) is float:
            _require(math.isfinite(item))
        elif type(item) is dict:
            pending.extend(item.values())
        elif type(item) is list:
            pending.extend(item)
    return value


def _keys(value, names):
    _require(type(value) is dict and set(value) == set(names))


def _nonempty(value):
    return type(value) is str and bool(value)


def _fixture_envelope(value, request, business):
    _keys(value, ("version", "as_of", "scopes", "facts"))
    _require(value["version"] == "synthetic-provider-v1" and type(value["as_of"]) is str)
    stamp = datetime.fromisoformat(value["as_of"].replace("Z", "+00:00"))
    _require(stamp.utcoffset() is not None)
    scopes, facts = value["scopes"], value["facts"]
    _require(type(scopes) is list and len(scopes) == 1 and type(facts) is dict and bool(facts))
    scope = scopes[0]
    _keys(scope, ("case_id", "object_id", "principal_id", "readers"))
    for key in ("case_id", "object_id", "principal_id"):
        _require(scope[key] == getattr(request, key))
    readers = scope["readers"]
    _require(type(readers) is dict and bool(readers)
             and all(_nonempty(k) and _nonempty(v) for k, v in readers.items()))
    for name, fact in facts.items():
        _require(_nonempty(name) and len(name.split(".")) >= 2
                 and all(part and not part.isspace() for part in name.split(".")))
        _keys(fact, ("value", "revision", "case_id", "object_id", "evidence_ref"))
        _require(fact["case_id"] == request.case_id and fact["object_id"] == request.object_id
                 and _nonempty(fact["revision"]) and _nonempty(fact["evidence_ref"]))
    binding = facts["case.binding"]["value"]
    _keys(binding, ("case_id", "object_id", "principal_id", "request_id"))
    _require(all(binding[key] == getattr(request, key) for key in binding))
    _require(facts["customer.request_fingerprint"]["value"] == business)


def _installed_bytes(path):
    # Only fixed package paths reach here; read with a finite no-follow handle.
    pins, descriptor = _PreparationPins(path.parent), None
    try:
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                             dir_fd=pins.entries[-1][0])
        before = os.fstat(descriptor)
        _require(stat.S_ISREG(before.st_mode) and before.st_size <= _MIB)
        chunks, size = [], 0
        while True:
            chunk = os.read(descriptor, min(65536, _MIB + 1 - size))
            if not chunk:
                break
            size += len(chunk)
            _require(size <= _MIB)
            chunks.append(chunk)
        after = os.fstat(descriptor)
        _require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
                 (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns))
        named = os.stat(path.name, dir_fd=pins.entries[-1][0], follow_symlinks=False)
        _require((named.st_dev, named.st_ino) == (before.st_dev, before.st_ino))
        _check_pins(pins)
        return b"".join(chunks)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        pins.close()


def _validate_input(spec, clock, execution):
    """Return detached fixed-family snapshots after every preallocation check."""
    try:
        _boundary(clock, execution)
        _require(type(spec) is SyntheticCaseReleaseSpecV1)
        copied = SyntheticCaseReleaseSpecV1(spec.host_release_id, spec.registered_release_id,
                                          spec.resource_id, spec.request, spec.fixture_bytes)
        request, raw = copied.request, copied.fixture_bytes
        business = request_fingerprint(request)
        _fixture_envelope(_fixture_json(raw), request, business)
        _boundary(clock, execution)
        package = Path(__file__).resolve().parent
        profile_bytes = _installed_bytes(package / "resources/profiles/flat-v1.3.json")
        _require(sha256(profile_bytes).hexdigest() == _PINNED_PROFILE_FILE)
        profile = validate_profile(EnvironmentProfile.model_validate_json(profile_bytes))
        _require(profile.profile_id == "flat-v1.3" and profile.version == "v1.3"
                 and (profile.release_hash, profile.process_hash, profile.policy_hash)
                 == (_PINNED_PROFILE, _PINNED_PROCESS, _PINNED_POLICY)
                 and all(item.version == "v1" for item in profile.processes.values()))
        implementations = []
        for name in FIXED_IMPLEMENTATION_PATHS:
            _boundary(clock, execution)
            implementations.append(ReleaseBlobV1(name, _installed_bytes(package / name)))
        implementations = tuple(implementations)
        source = _canonical({"kind": "route-source-declaration-v1", "mode": "synthetic",
            "source_id": "fixed-world-fixture",
            "documents": [{"source_id": "fixed-world-fixture", "text": raw.decode("utf-8")}]})
        _require(len(source) <= _MIB)
        tests = _canonical(dict(kind="route-test-declaration-v1", mode="synthetic", cases=[]))
        declarations = dict(
            profile=_canonical(profile.model_dump(mode="json")), policy=_canonical(_POLICY), source=source,
            proposal=_canonical(dict(kind="route-proposal-declaration-v1", mode="synthetic",
                baseline_profile_hash=profile.release_hash, candidate_profile_hash=profile.release_hash, diff=[])),
            tests=tests,
            regression=_canonical(dict(kind="route-regression-declaration-v1", mode="synthetic",
                execution="unestablished", tests_hash=sha256(tests).hexdigest(), case_ids=[])),
            migration=_canonical(dict(kind="route-migration-declaration-v1", mode="synthetic",
                strategy="preserve", affected_contracts=[])),
            agent=_canonical(dict(kind="route-agent-declaration-v1", mode="synthetic",
                authorship="unestablished", agent_label="synthetic-preparation-v1")),
            dependency=_canonical(dict(kind="route-closure-declaration-v1", mode="synthetic_declaration",
                completeness="unestablished", entries=[dict(name=item.name, sha256=item.sha256, role="code")
                                                       for item in implementations])))
        # Exercise all existing declaration and aggregate limits before allocation.
        ReleaseArtifactV1(copied.registered_release_id, "fixed-synthetic-v1", copied.resource_id,
            **{name + "_json": data for name, data in declarations.items()}, implementations=implementations)
        _boundary(clock, execution)
        return _ValidatedInput(copied.host_release_id, copied.registered_release_id, copied.resource_id,
            request, raw, business, profile_bytes, tuple(declarations.items()), implementations)
    except SyntheticPreparationFailureV1:
        raise
    except OSError:
        raise SyntheticPreparationFailureV1("io_failure") from None
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError):
        raise SyntheticPreparationFailureV1("invalid_input") from None
    except Exception:
        raise SyntheticPreparationFailureV1("io_failure") from None


class _PreparationPins(_PathPins):
    """The shared no-follow protocol, with BaseException-safe ownership."""
    def __init__(self, path):
        path = Path(path)
        self.path, self.entries, self.private_fds = path, [], set()
        if (not path.is_absolute() or ".." in path.parts or len(path.parts) > 64
                or len(str(path)) > 1024):
            raise ValueError("Invalid trusted launch directory")
        try:
            root = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            registered = False
            try:
                self.entries.append((root, None, None, self.identity(root)))
                registered = True
            finally:
                if not registered:
                    os.close(root)
            for name in path.parts[1:]:
                self._append(name, private=False)
            self.check()
        except BaseException:
            self.close()
            raise

    def _append(self, name, *, private):
        parent = self.entries[-1][0]
        child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        appended = False
        try:
            identity = self.identity(child)
            value = os.fstat(child)
            _require(identity not in tuple(entry[3] for entry in self.entries), "invalid_target")
            if private:
                _require(value.st_uid == os.geteuid() and stat.S_IMODE(value.st_mode) == 0o700,
                         "invalid_target")
            self.entries.append((child, parent, name, identity))
            appended = True
            if private:
                self.private_fds.add(child)
        finally:
            if not appended:
                os.close(child)


@dataclass(frozen=True, slots=True)
class _PrivateAllocation:
    root: Path
    data: Path
    resources: Path
    control: Path
    inventories: Path
    outputs: Path
    # Every path includes identities for its full ancestry, from / onward.
    identities: tuple[tuple[Path, tuple[tuple[int, int], ...]], ...] = field(repr=False)


def _check_pins(pins):
    try:
        pins.check()
    except (OSError, ValueError):
        raise SyntheticPreparationFailureV1("identity_changed") from None


def _validate_parent(pins):
    parent = pins.path
    identities = tuple(entry[3] for entry in pins.entries)
    for forbidden in (Path("/"), Path.home(), Path.cwd()):
        value = forbidden.stat()
        _require(identities[-1] != (value.st_dev, value.st_ino), "invalid_target")
    package = Path(__file__).resolve().parent
    _require(not any(part.casefold() == "site-packages" for part in parent.parts), "invalid_target")
    installation_roots = (package, *(path for path in package.parents
                                    if path.name.casefold() == "site-packages"))
    for installation_root in installation_roots:
        value = installation_root.stat()
        _require(not parent.is_relative_to(installation_root)
                 and (value.st_dev, value.st_ino) not in identities, "invalid_target")
    value = os.fstat(pins.entries[-1][0])
    _require(value.st_uid == os.geteuid() and stat.S_IMODE(value.st_mode) == 0o700, "invalid_target")
    pins.private_fds.add(pins.entries[-1][0])
    _check_pins(pins)


@contextmanager
def _allocate_private(parent, clock, execution):
    """Own all directory handles until exit; yield only paths and identities."""
    holds, retained_root = [], None
    try:
        _boundary(clock, execution)
        _require(isinstance(parent, (str, Path)), "invalid_target")
        try:
            parent_pins = _PreparationPins(parent)
        except (OSError, ValueError, TypeError):
            raise SyntheticPreparationFailureV1("invalid_target") from None
        holds.append(parent_pins)
        _validate_parent(parent_pins)
        _boundary(clock, execution)
        _check_pins(parent_pins)
        parent_fd = parent_pins.entries[-1][0]
        name = "case-" + uuid4().hex
        os.mkdir(name, mode=0o700, dir_fd=parent_fd)
        retained_root = parent_pins.path / name
        _check_pins(parent_pins)
        parent_pins._append(name, private=True)
        parent_pins.path = retained_root
        _check_pins(parent_pins)
        recorded = [(retained_root, tuple(entry[3] for entry in parent_pins.entries))]
        for child_name in _CHILDREN:
            _boundary(clock, execution)
            _check_pins(parent_pins)
            os.mkdir(child_name, mode=0o700, dir_fd=parent_pins.entries[-1][0])
            child = _PreparationPins(retained_root)
            holds.append(child)
            _require(tuple(entry[3] for entry in child.entries) == recorded[0][1],
                     "identity_changed")
            # Root and private parent must retain their owner/mode too.
            child.private_fds.update(entry[0] for entry in child.entries[-2:])
            child._append(child_name, private=True)
            child.path = retained_root / child_name
            _check_pins(child)
            recorded.append((child.path, tuple(entry[3] for entry in child.entries)))
        for held in holds:
            _check_pins(held)
        _boundary(clock, execution)
        yield _PrivateAllocation(retained_root, *(retained_root / name for name in _CHILDREN),
                                 tuple(recorded))
        _boundary(clock, execution)
        for held in holds:
            _check_pins(held)
    except SyntheticPreparationFailureV1 as error:
        raise SyntheticPreparationFailureV1(error.code, retained_root=retained_root) from None
    except OSError:
        raise SyntheticPreparationFailureV1("io_failure", retained_root=retained_root) from None
    except (ValueError, TypeError, AttributeError):
        raise SyntheticPreparationFailureV1("invalid_target", retained_root=retained_root) from None
    except Exception:
        raise SyntheticPreparationFailureV1("io_failure", retained_root=retained_root) from None
    finally:
        for held in reversed(holds):
            held.close()


def _stage_private(allocation, directory, name, data, clock, execution):
    """Exclusively stage one bounded file and verify bytes, mode and ancestry."""
    pins = None
    root = allocation.root if type(allocation) is _PrivateAllocation else None
    try:
        _boundary(clock, execution)
        _require(type(allocation) is _PrivateAllocation and directory in _CHILDREN
                 and type(name) is str and name not in {"", ".", ".."}
                 and "/" not in name and "\\" not in name and "\0" not in name
                 and type(data) is bytes and len(data) <= _MIB)
        target = getattr(allocation, directory)
        try:
            pins = _PreparationPins(target)
        except (OSError, ValueError):
            raise SyntheticPreparationFailureV1("identity_changed") from None
        _require(tuple(entry[3] for entry in pins.entries) == dict(allocation.identities)[target],
                 "identity_changed")
        pins.private_fds.update(entry[0] for entry in pins.entries[-3:])
        _check_pins(pins)
        descriptor = pins.entries[-1][0]
        _write(descriptor, name, data)
        _boundary(clock, execution)
        _check_pins(pins)
        value = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
        _require(stat.S_ISREG(value.st_mode) and value.st_nlink == 1
                 and value.st_uid == os.geteuid() and stat.S_IMODE(value.st_mode) == 0o600,
                 "identity_changed")
        _require(_read(descriptor, name, _MIB) == data, "identity_changed")
        after = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
        attributes = ("st_dev", "st_ino", "st_mode", "st_uid", "st_nlink", "st_size", "st_mtime_ns")
        _require(tuple(getattr(value, key) for key in attributes)
                 == tuple(getattr(after, key) for key in attributes), "identity_changed")
        _check_pins(pins)
        _boundary(clock, execution)
        return target / name
    except SyntheticPreparationFailureV1 as error:
        raise SyntheticPreparationFailureV1(error.code, retained_root=root) from None
    except OSError:
        raise SyntheticPreparationFailureV1("io_failure", retained_root=root) from None
    except (ValueError, TypeError, KeyError, AttributeError):
        raise SyntheticPreparationFailureV1("invalid_input", retained_root=root) from None
    except Exception:
        raise SyntheticPreparationFailureV1("io_failure", retained_root=root) from None
    finally:
        if pins is not None:
            pins.close()
