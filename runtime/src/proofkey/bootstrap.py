"""Trusted offline launch configuration; synthetic registration only."""
from dataclasses import dataclass, field
from datetime import timedelta
import math
import os
from pathlib import Path
import stat
from typing import Literal

from pydantic import model_validator

from .contracts import AuthContext, WireModel
from .host import AuthResolver, ProfileRegistry, RuntimeFactory
from .host_contracts import (BatchRunReceiptV1, CommandRunReceiptV1, ShutdownReceiptV1,
                             HostLimitsV1, InterfaceLimitsV1)


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
