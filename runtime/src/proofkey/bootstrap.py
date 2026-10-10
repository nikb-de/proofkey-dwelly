"""Trusted offline launch configuration; synthetic registration only."""
from base64 import b64decode
from dataclasses import asdict, dataclass, field
from datetime import timedelta
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import stat
from typing import Literal

from pydantic import model_validator

from .contracts import AuthContext, WireModel
from .clock import SyntheticReplayClock
from .host import ApprovedProfileRelease, AuthResolver, ProfileRegistry, RuntimeFactory
from .host_admission import LocalAdmissionCompositionV1
from .profiles import _validate_selected_profile
from .host_contracts import (BatchRunReceiptV1, CommandRunReceiptV1, ShutdownReceiptV1,
                             HostLimitsV1, InterfaceLimitsV1)
from .host_files import _read


def _duration(value):
    if type(value) not in (float, int) or not math.isfinite(value):
        raise ValueError("Invalid trusted launch configuration")
    value = float(value)
    if value < 0 or timedelta(seconds=value).total_seconds() != value:
        raise ValueError("Invalid trusted launch configuration")
    return value


class _PathPins:
    """Held no-follow ancestry, rechecked against every actual parent/name."""
    def __init__(self, path):
        path = Path(path)
        self.path, self.entries, self.private_fds = path, [], set()
        if (not path.is_absolute() or ".." in path.parts or len(path.parts) > 64
                or len(str(path)) > 1024):
            raise ValueError("Invalid trusted launch directory")
        try:
            root = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            self.entries.append((root, None, None, self.identity(root)))
            for name in path.parts[1:]:
                self._append(name, private=False)
            self.check()
        except Exception:
            self.close()
            raise ValueError("Invalid trusted launch directory") from None

    @staticmethod
    def identity(fd):
        value = os.fstat(fd)
        return value.st_dev, value.st_ino

    def _append(self, name, *, private):
        parent = self.entries[-1][0]
        child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        try:
            identity = self.identity(child)
            value = os.fstat(child)
            if identity in tuple(entry[3] for entry in self.entries):
                raise ValueError("Aliased directory")
            if private and (value.st_uid != os.geteuid() or stat.S_IMODE(value.st_mode) != 0o700):
                raise ValueError("Unsafe private directory")
            self.entries.append((child, parent, name, identity))
            if private:
                self.private_fds.add(child)
        except Exception:
            os.close(child)
            raise

    def child(self, name):
        self.check()
        parent = self.entries[-1][0]
        try:
            os.mkdir(name, mode=0o700, dir_fd=parent)
        except FileExistsError:
            pass
        self._append(name, private=True)
        self.path = self.path / name
        self.check()
        return self.path

    def check(self):
        for fd, parent, name, identity in self.entries:
            if self.identity(fd) != identity:
                raise ValueError("Launch ancestry changed")
            value = os.stat("/" if parent is None else name, dir_fd=parent, follow_symlinks=False)
            if not stat.S_ISDIR(value.st_mode) or (value.st_dev, value.st_ino) != identity:
                raise ValueError("Launch ancestry changed")
            if fd in self.private_fds and (value.st_uid != os.geteuid() or stat.S_IMODE(value.st_mode) != 0o700):
                raise ValueError("Unsafe private directory")

    def close(self):
        for fd, _, _, _ in reversed(self.entries):
            os.close(fd)
        self.entries = []
        self.private_fds = set()


def _registered_fixture_snapshot(release):
    """Pin the fixture across release validation and a bounded exact-byte read."""
    path = release.fixture_path
    pins = _PathPins(path.parent)
    try:
        parent = pins.entries[-1][0]
        pins.private_fds.add(parent)
        pins.check()
        attributes = ("st_dev", "st_ino", "st_mode", "st_uid", "st_nlink",
                      "st_size", "st_mtime_ns", "st_ctime_ns")

        def identity():
            value = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
            if (not stat.S_ISREG(value.st_mode) or value.st_nlink != 1
                    or value.st_uid != os.geteuid() or stat.S_IMODE(value.st_mode) != 0o600
                    or not 0 < value.st_size <= 1048576):
                raise ValueError
            return tuple(getattr(value, name) for name in attributes)

        before = identity()
        profile = release.validate()
        pins.check()
        if identity() != before:
            raise ValueError
        raw = _read(parent, path.name, 1048576)
        pins.check()
        if identity() != before or sha256(raw).hexdigest() != release.fixture_hash:
            raise ValueError
        return profile, raw.decode("utf-8")
    finally:
        pins.close()


@dataclass(frozen=True, slots=True)
class CliConfiguration:
    factory: RuntimeFactory
    auth_resolver: AuthResolver
    profile_registry: ProfileRegistry
    clock: object
    host_limits: HostLimitsV1
    interface_limits: InterfaceLimitsV1
    output_parent: Path
    inventory_parent: Path
    total_seconds: float = 120.0
    publication_reserve_seconds: float = 10.0
    shutdown_seconds: float = 2.0
    admission_composition: LocalAdmissionCompositionV1 | None = field(default=None, repr=False)
    _parent_identities: tuple = field(init=False, repr=False)

    def __post_init__(self):
        try:
            total = _duration(self.total_seconds)
            reserve = _duration(self.publication_reserve_seconds)
            shutdown = _duration(self.shutdown_seconds)
            if (type(self.host_limits) is not HostLimitsV1 or type(self.interface_limits) is not InterfaceLimitsV1
                    or not isinstance(self.factory, RuntimeFactory) or not isinstance(self.auth_resolver, AuthResolver)
                    or type(self.profile_registry) is not ProfileRegistry
                    or not all(callable(getattr(self.clock, name, None)) for name in ("now", "monotonic", "wait"))
                    or getattr(self.clock, "mode", None) != "synthetic_replay"
                    or not 0 <= reserve < total or shutdown <= 0
                    or total - reserve > self.host_limits.max_execution_seconds
                    or shutdown > self.host_limits.shutdown_max_seconds):
                raise ValueError
            object.__setattr__(self, "host_limits", HostLimitsV1.model_validate(self.host_limits.model_dump()))
            object.__setattr__(self, "interface_limits", InterfaceLimitsV1.model_validate(self.interface_limits.model_dump()))
            for name, value in (("total_seconds", total), ("publication_reserve_seconds", reserve),
                                ("shutdown_seconds", shutdown)):
                object.__setattr__(self, name, value)
            if self.admission_composition is not None:
                self._validate_registered()
            identities = []
            for name in ("output_parent", "inventory_parent"):
                value = getattr(self, name)
                if not isinstance(value, (str, Path)):
                    raise ValueError
                pins = _PathPins(value)
                try:
                    identities.append(tuple(item[3] for item in pins.entries))
                    object.__setattr__(self, name, pins.path)
                finally:
                    pins.close()
            object.__setattr__(self, "_parent_identities", tuple(identities))
        except Exception:
            raise ValueError("Invalid trusted launch configuration") from None

    def _validate_registered(self):
        """Check structural commitments only; authority needs a fresh context."""
        composition = self.admission_composition
        if (type(composition) is not LocalAdmissionCompositionV1
                or type(self.factory) is not RuntimeFactory
                or type(self.clock) is not SyntheticReplayClock):
            raise ValueError
        LocalAdmissionCompositionV1(composition.registry, composition.binding, composition.approvals,
            composition.review_id, composition.control_parent)
        binding = composition.binding
        entries = self.profile_registry._entries
        if (type(entries) is not dict or len(entries) != 1
                or tuple(entries) != (binding.host_release_id,)
                or composition.registry.commitments() != ((binding.registered_release_id, binding.artifact_hash),)):
            raise ValueError
        release = self.profile_registry.resolve(binding.host_release_id)
        if type(release) is not ApprovedProfileRelease:
            raise ValueError
        release = ApprovedProfileRelease(**asdict(release))
        registered = composition.registry.resolve(binding.registered_release_id)
        factory, resource = registered.factory, registered.resource
        profile, fixture = _registered_fixture_snapshot(release)
        _validate_selected_profile(binding.host_factory_key, profile, release.admitted_request_kind)
        source = json.loads(b64decode(json.loads(registered.wire_bytes)["blobs"]["source"]["base64"], validate=True))
        identity = os.lstat(release.resource_root)
        if (release.release_id != binding.host_release_id
                or registered.artifact_hash != binding.artifact_hash
                or release.mode != "synthetic_replay"
                or factory.factory_id != binding.factory_id
                or factory.implementation_pins != binding.implementation_pins
                or factory.dependency_hash != binding.dependency_hash
                or registered.profile.model_dump(mode="json") != profile.model_dump(mode="json")
                or not stat.S_ISDIR(identity.st_mode)
                or (resource.root_path, resource.root_device, resource.root_inode) !=
                   (str(release.resource_root), identity.st_dev, identity.st_ino)
                or source["source_id"] != "fixed-world-fixture"
                or source["documents"] != [dict(source_id="fixed-world-fixture", text=fixture)]
                or json.loads(fixture)["facts"]["customer.request_fingerprint"]["value"] !=
                   release.admitted_request_fingerprint):
            raise ValueError


def _default_configuration(clock, *, boundary):
    """Provision only fixed private children under the existing working directory."""
    pins = _PathPins(Path.cwd())
    holds = [pins]
    try:
        boundary()
        root = pins.child(".proofkey")
        children = {}
        for name in ("resources", "inventories", "runs"):
            boundary()
            child = _PathPins(root)
            holds.append(child)
            children[name] = child.child(name)
        boundary()
        configuration = CliConfiguration(factory=RuntimeFactory(),
            auth_resolver=AuthResolver({"synthetic-user": AuthContext(caller_id="U1", proof_reference="synthetic-proof")}),
            profile_registry=ProfileRegistry.builtin(children["resources"]), clock=clock,
            host_limits=HostLimitsV1(), interface_limits=InterfaceLimitsV1(),
            output_parent=children["runs"], inventory_parent=children["inventories"])
        for held in holds:
            held.check()
        return configuration, holds
    except Exception:
        for held in reversed(holds):
            held.close()
        raise


class CliReceiptV1(WireModel):
    kind: Literal["proofkey-cli-receipt-v1"] = "proofkey-cli-receipt-v1"
    run: CommandRunReceiptV1 | BatchRunReceiptV1 | None = None
    shutdown: ShutdownReceiptV1 | None = None
    failure: Literal["invalid_usage", "invalid_configuration", "invalid_input", "bootstrap_unavailable", "owner_pending"] | None = None

    @model_validator(mode="before")
    @classmethod
    def shutdown_json_tuples(cls, value, info):
        # The unchanged shared WireModel materializes arrays before strict tuple
        # validation; bridge only the two declared shutdown arrays in JSON mode.
        if info.mode == "json" and type(value) is dict and type(value.get("shutdown")) is dict:
            shutdown = dict(value["shutdown"])
            for name in ("pending_command_ids", "cancelled_command_ids"):
                if type(shutdown.get(name)) is list:
                    shutdown[name] = tuple(shutdown[name])
            return {**value, "shutdown": shutdown}
        return value
