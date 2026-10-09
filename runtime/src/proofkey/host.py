"""Offline fixed-release host: one visible creator owns runtime and recovery."""
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import threading
import uuid
import weakref

from .adapters.world import SimulatedWorld
from .contracts import AuthContext, CaseResult, SavedResult, EnvironmentProfile
from .engine import WorkflowEngine
from .execution import ExecutionContext
from .host_contracts import (CommandInventoryV1, CommandReceiptV1, DetachedProfileViewV1, ExecutionWindowV1,
                             HostLimitsV1, ShutdownReceiptV1, parse_command)
from .host_files import HostInventory, InventoryFailure, _directory, _read
from .identity import fingerprint, request_fingerprint
from .journal import CaseStore
from .profiles import validate_profile

_ROOT = Path(__file__).resolve().parents[2]
_PROFILE_RAW = "8fcd07924f5518ffa6e8b7cfcb3d773e8ba9f10d48458031132f8749c177a940"
_PROFILE = "5bb712b13efaace655ee7180f3d913d93cbd637e3d1685331c6a1eecbade7bf4"
_PROCESS = "91cb93780a0cd1612fbeea2aab4e9ee7ac5cc6007e1d8ee2952d52655a9f75e2"
_POLICY = "1905842f17fd73559d48f4f2d04928a5be734464b966b7167808a05732cdf752"
_WINDOW = "cb9a2c3b8bcf77ee1f400cac7921b52b52f2468180c0b043b8f35f01058a0c59"
_GOODS = "e3ec67bfd42fb4e6e26394eb9e22fb0c822194768a4eb8eec2ba63b32a27973f"


def _pinned(path, expected):
    parent = _directory(path.parent)
    try:
        data = _read(parent, path.name, 1048576)
        if sha256(data).hexdigest() != expected:
            raise ValueError("Registered host resource unavailable")
        return data
    finally:
        os.close(parent)


def _profile_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate registered profile field")
        result[key] = value
    return result


@dataclass(frozen=True, slots=True)
class ApprovedProfileRelease:
    release_id: str
    mode: str
    profile_path: Path
    fixture_path: Path
    resource_root: Path
    profile_file_hash: str
    profile_hash: str
    process_hash: str
    policy_hash: str
    fixture_hash: str
    admitted_request_kind: str
    admitted_request_fingerprint: str
    profile_id: str = "flat-v1.3"
    profile_version: str = "v1.3"

    def __post_init__(self):
        if (type(self.admitted_request_kind) is not str
                or self.admitted_request_kind not in {"reschedule_window", "goods_refusal"}
                or type(self.admitted_request_fingerprint) is not str
                or re.fullmatch(r"[a-f0-9]{64}", self.admitted_request_fingerprint) is None):
            raise ValueError("Exact fixed demo request commitment required")
        self.view()
        for name in ("profile_path", "fixture_path", "resource_root"):
            value = Path(getattr(self, name))
            if not value.is_absolute() or ".." in value.parts:
                raise ValueError("Exact trusted host path required")
            object.__setattr__(self, name, value)

    def view(self):
        return DetachedProfileViewV1(release_id=self.release_id, mode=self.mode, profile_id=self.profile_id,
            profile_version=self.profile_version, profile_file_hash=self.profile_file_hash, profile_hash=self.profile_hash,
            process_hash=self.process_hash, policy_hash=self.policy_hash, fixture_hash=self.fixture_hash)

    def validate(self):
        profile_bytes = _pinned(self.profile_path, self.profile_file_hash)
        _pinned(self.fixture_path, self.fixture_hash)
        profile = validate_profile(EnvironmentProfile.model_validate(
            json.loads(profile_bytes.decode("utf-8"), object_pairs_hook=_profile_pairs)))
        if (profile.profile_id, profile.version, profile.release_hash, profile.process_hash, profile.policy_hash) != (
                self.profile_id, self.profile_version, self.profile_hash, self.process_hash, self.policy_hash):
            raise ValueError("Registered host release mismatch")
        return profile


class ProfileRegistry:
    def __init__(self, entries):
        if type(entries) not in (tuple, list) or not entries or len(entries) > 64:
            raise ValueError("Finite trusted registry required")
        self._entries = {}
        for entry in entries:
            if type(entry) is not ApprovedProfileRelease or entry.release_id in self._entries:
                raise ValueError("Exact unique registered release required")
            self._entries[entry.release_id] = entry

    @classmethod
    def builtin(cls, resource_root):
        resource_root = Path(resource_root).absolute()
        return cls(tuple(ApprovedProfileRelease(release_id=release_id, mode="synthetic_replay",
            profile_path=_ROOT / "profiles/flat-v1.3.json", fixture_path=_ROOT / "fixtures/development" / fixture,
            resource_root=resource_root / release_id, profile_file_hash=_PROFILE_RAW, profile_hash=_PROFILE,
            process_hash=_PROCESS, policy_hash=_POLICY, fixture_hash=fixture_hash,
            admitted_request_kind=kind, admitted_request_fingerprint=request_hash)
            for release_id, fixture, fixture_hash, kind, request_hash in (
                ("host-window-replay-v1", "packet-world-v1.json", _WINDOW, "reschedule_window",
                 "e51bc7df8304c4f88f09e979b60505c20610e2bd13209ac60afd8e9d47a8af34"),
                ("host-goods-replay-v1", "host-goods-world-v1.json", _GOODS, "goods_refusal",
                 "f1a95a447f2a6726a3459f37790557326b3361a15894a7b4a2baa28451321ce2"))))

    def resolve(self, release_id):
        if type(release_id) is not str or release_id not in self._entries:
            raise ValueError("Unregistered host release")
        return self._entries[release_id]

    def inspect(self, release_id):
        release = self.resolve(release_id)
        release.validate()
        return release.view()


class TransportProofHandle:
    """Opaque host object; only a provisioning resolver's identity map accepts it."""
    __slots__ = ()


class AuthResolver:
    def __init__(self, credentials):
        if type(credentials) is not dict or not 0 < len(credentials) <= 256:
            raise ValueError("Finite external credential registry required")
        self._references, self._credentials = {}, {}
        for reference, auth in credentials.items():
            if type(reference) is not str or not reference or len(reference) > 256 or type(auth) is not AuthContext:
                raise ValueError("Trusted credential reference required")
            handle = TransportProofHandle()
            self._references[reference] = handle
            self._credentials[handle] = AuthContext.model_validate_json(auth.model_dump_json())

    def handle(self, reference):
        if type(reference) is not str or reference not in self._references:
            raise ValueError("External proof unavailable")
        return self._references[reference]

    def resolve(self, proof_handle, command):
        if type(proof_handle) is not TransportProofHandle or proof_handle not in self._credentials:
            raise ValueError("External proof unavailable")
        return AuthContext.model_validate_json(self._credentials[proof_handle].model_dump_json())


def _resource_directory(path):
    # Only the two fixed trusted bootstrap directory levels may be created.
    parent = _directory(path.parent.parent)
    try:
        for name in (path.parent.name, path.name):
            try:
                os.mkdir(name, mode=0o700, dir_fd=parent)
            except FileExistsError:
                pass
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            os.close(parent)
            parent = child
    finally:
        os.close(parent)


class RuntimeResources:
    def __init__(self, profile, world, store, engine):
        self.profile, self.world, self.store, self.engine = profile, world, store, engine
        self._owner = threading.get_ident()
        self.closed = False

    def close(self):
        if threading.get_ident() != self._owner:
            raise ValueError("Runtime close requires creator thread")
        if not self.closed:
            self.store.close()
            self.closed = True


class RuntimeFactory:
    def create(self, release, clock):
        if type(release) is not ApprovedProfileRelease or getattr(clock, "mode", None) != release.mode:
            raise ValueError("Exact registered offline clock/resource required")
        store = None
        try:
            profile = release.validate()
            fixture_bytes = _pinned(release.fixture_path, release.fixture_hash)
            _resource_directory(release.resource_root)
            # Refuse preexisting symlink/foreign alias database targets.
            root = _directory(release.resource_root)
            try:
                for name in ("world.sqlite", "journal.sqlite"):
                    try:
                        value = os.stat(name, dir_fd=root, follow_symlinks=False)
                    except FileNotFoundError:
                        continue
                    import stat
                    if not stat.S_ISREG(value.st_mode) or value.st_nlink != 1:
                        raise ValueError("Invalid owned runtime database")
            finally:
                os.close(root)
            world = SimulatedWorld(release.resource_root / "world.sqlite", release.fixture_path,
                                   profile=profile, clock=clock, fixture_bytes=fixture_bytes)
            store = CaseStore(release.resource_root / "journal.sqlite")
            engine = WorkflowEngine(profile, world.bundle(), store, clock)
            release.validate()
            return RuntimeResources(profile, world, store, engine)
        except BaseException:
            if store is not None:
                store.close()
            raise


class HostSubmission:
    """No serializable ID/proof fields: an exact dispatcher-owned object."""
    __slots__ = ("__weakref__",)


@dataclass
class _State:
    command_id: str
    command: object = None
    proof_handle: object = None
    execution: object = None
    window: object = None
    payload_hash: str | None = None
    sequence: int = 0
    phase: str = "new"
    outcome: str | None = None
    failure: str | None = None
    queued_at: object = None
    started_at: object = None
    finished_at: object = None
    result: object = None
    inspection: object = None
    inventory_status: str = "not_admitted"
    references: list = field(default_factory=list)
    done: threading.Event = field(default_factory=threading.Event)


class HostDispatcher:
    def __init__(self, factory, auth_resolver, profile_registry, clock, inventory_root, limits, *, release_id):
        if type(limits) is not HostLimitsV1 or type(profile_registry) is not ProfileRegistry:
            raise ValueError("Exact trusted host limits/registry required")
        if not callable(getattr(factory, "create", None)) or not callable(getattr(auth_resolver, "resolve", None)):
            raise ValueError("Trusted complete factory/resolver required")
        self.limits = HostLimitsV1.model_validate(limits.model_dump())
        self.release = profile_registry.resolve(release_id)
        if getattr(clock, "mode", None) != self.release.mode:
            raise ValueError("Registered clock mode mismatch")
        self.factory, self.resolver, self.registry, self.clock = factory, auth_resolver, profile_registry, clock
        self.inventory_root = Path(inventory_root).absolute()
        self._condition = threading.Condition()
        self._publication_lock = threading.Lock()
        self._handle_lock = threading.Lock()
        self._handles = weakref.WeakKeyDictionary()
        self._queue, self._finalize_queue, self._pending = deque(), deque(), {}
        self._closing = self._owner_closed = self._inventory_failed = False
        self._admitting = self._publishing = self._sequence = 0
        self._resources = None
        startup = self._monotonic()
        try:
            self._inventory = HostInventory(self.inventory_root, max_bytes=self.limits.inventory_max_bytes)
        except InventoryFailure:
            self._inventory = None
            self._inventory_failed = True
        self.startup_seconds = self._monotonic() - startup
        self._thread = threading.Thread(target=self._owner, name="proofkey-runtime-owner", daemon=False)
        self._thread.start()

    def _now(self):
        value = self.clock.now()
        if not isinstance(value, datetime) or value.utcoffset() is None:
            raise ValueError("Aware trusted clock required")
        return value

    def _monotonic(self):
        value = self.clock.monotonic()
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError("Finite trusted clock required")
        return float(value)

    def _check_context(self, execution):
        window = ExecutionWindowV1.from_context(execution)
        duration = (execution.deadline - execution.captured_at).total_seconds()
        if duration > self.limits.max_execution_seconds:
            raise ValueError("Context exceeds host ceiling")
        return window, execution.remaining_seconds(self.clock)

    def _handle(self, state):
        handle = HostSubmission()
        with self._handle_lock:
            self._handles[handle] = state
        return handle

    def _state(self, submission):
        with self._handle_lock:
            if type(submission) is not HostSubmission or submission not in self._handles:
                raise ValueError("Foreign host submission")
            return self._handles[submission]

    def _external_entry(self):
        if threading.get_ident() == self._thread.ident:
            raise ValueError("Owner cannot recursively enter public host routing")

    def _publish(self, state, phase, *, nonblocking=False):
        if self._inventory is None:
            raise InventoryFailure()
        acquired = self._publication_lock.acquire(blocking=not nonblocking)
        if not acquired:
            raise InventoryFailure()
        with self._condition:
            self._publishing += 1
        try:
            returned = state.result if state.result is not None else state.inspection
            record = CommandInventoryV1(command_id=state.command_id, command_tag=state.command.tag,
                release_id=state.command.release_id, mode=self.release.mode, payload_hash=state.payload_hash,
                execution=state.window, phase=phase, timestamp=self._now(),
                outcome=state.outcome if phase == "finished" else None,
                failure=state.failure if phase == "finished" else None,
                result_hash=fingerprint(returned.model_dump(mode="json")) if phase == "finished" and returned is not None else None)
            reference = self._inventory.publish(state.sequence, phase, record)
            with self._condition:
                state.references.append(reference)
                state.inventory_status = "committed"
        except (InventoryFailure, ValueError, TypeError, OSError):
            with self._condition:
                state.inventory_status = "partial" if state.references else "unavailable"
                self._inventory_failed = True
            raise InventoryFailure() from None
        finally:
            with self._condition:
                self._publishing -= 1
                self._condition.notify_all()
            self._publication_lock.release()

    def _finish(self, state):
        try:
            self._publish(state, "finished")
        except InventoryFailure:
            state.failure = "inventory_failed"
        finally:
            with self._condition:
                state.phase = "finished"
                state.proof_handle = None
                try:
                    state.finished_at = self._now()
                except (ValueError, TypeError, OSError):
                    state.finished_at = None
                state.done.set()
                self._pending.pop(state.command_id, None)
                self._condition.notify_all()

    def _cancel_locked(self, state, outcome, failure):
        # Called under the dequeue Condition. Prevention is not durable completion.
        if state.phase == "queued":
            self._queue.remove(state)
        state.phase = "cancelled"
        state.outcome, state.failure = outcome, failure
        state.proof_handle = None
        state.inventory_status = "partial"
        self._finalize_queue.append(state)
        self._condition.notify_all()

    def _terminal(self, state, outcome, failure):
        state.outcome, state.failure = outcome, failure
        state.proof_handle = None
        try:
            state.finished_at = self._now()
        except (ValueError, TypeError, OSError):
            pass
        state.done.set()
        return self._handle(state)

    def enqueue(self, command, proof_handle, execution):
        self._external_entry()
        state = _State(uuid.uuid4().hex)
        try:
            state.window, remaining = self._check_context(execution)
            state.execution = execution
        except (ValueError, TypeError, OSError):
            return self._terminal(state, "denied", "scope_denied")
        if remaining <= 0:
            return self._terminal(state, "expired", "deadline_exceeded")
        try:
            state.command = parse_command(command, max_bytes=self.limits.max_command_bytes)
            state.payload_hash = fingerprint(state.command.model_dump(mode="json"))
        except (ValueError, TypeError):
            return self._terminal(state, "denied", "invalid_command")
        if state.command.release_id != self.release.release_id:
            return self._terminal(state, "denied", "scope_denied")
        if state.command.tag == "run" and (
                state.command.request.kind != self.release.admitted_request_kind
                or request_fingerprint(state.command.request) != self.release.admitted_request_fingerprint):
            return self._terminal(state, "denied", "scope_denied")
        with self._condition:
            if self._closing:
                return self._terminal(state, "denied", "host_closed")
            if len(self._queue) + self._admitting >= self.limits.queue_capacity:
                return self._terminal(state, "queue_full", "queue_full")
            self._admitting += 1
            self._sequence += 1
            state.sequence = self._sequence
            state.proof_handle = proof_handle
            try:
                state.queued_at = self._now()
            except (ValueError, TypeError, OSError):
                self._admitting -= 1
                self._condition.notify_all()
                return self._terminal(state, "denied", "scope_denied")
        try:
            self._publish(state, "queued", nonblocking=True)
        except InventoryFailure:
            with self._condition:
                self._admitting -= 1
                self._condition.notify_all()
            return self._terminal(state, "infrastructure_error", "no_durable_inventory")
        handle = self._handle(state)
        with self._condition:
            self._admitting -= 1
            self._pending[state.command_id] = state
            if self._closing:
                self._cancel_locked(state, "cancelled_before_start", "cancelled_before_start")
            else:
                state.phase = "queued"
                self._queue.append(state)
                self._condition.notify_all()
        return handle

    def _receipt(self, state, outcome=None):
        elapsed = overrun = None
        try:
            if state.window is not None:
                elapsed = self._monotonic() - state.window.captured_monotonic
                if elapsed < 0:
                    raise ValueError
                overrun = max(0.0, self._monotonic() - state.window.monotonic_deadline,
                              (self._now() - state.window.deadline).total_seconds())
        except (ValueError, TypeError, OSError):
            elapsed = overrun = None
        return CommandReceiptV1(command_id=state.command_id, command_tag=state.command.tag if state.command else None,
            release_id=self.release.release_id, mode=self.release.mode, clock_mode=self.clock.mode,
            outcome=outcome or state.outcome, payload_hash=state.payload_hash, execution=state.window,
            queued_at=state.queued_at, started_at=state.started_at,
            finished_at=state.finished_at if outcome != "started_pending" else None,
            elapsed_seconds=elapsed, overrun_seconds=overrun,
            result=state.result if outcome is None else None, inspection=state.inspection if outcome is None else None,
            inventory_status=state.inventory_status, inventory_references=tuple(state.references), failure=state.failure)

    def wait(self, submission):
        self._external_entry()
        state = self._state(submission)
        with self._condition:
            if state.done.is_set() or state.phase == "cancelled":
                return self._receipt(state)
        try:
            remaining = state.execution.remaining_seconds(self.clock)
        except (ValueError, TypeError, OSError):
            remaining = 0.0
        with self._condition:
            self._condition.wait_for(lambda: state.done.is_set() or state.phase == "cancelled", max(0.0, remaining))
            if state.done.is_set() or state.phase == "cancelled":
                return self._receipt(state)
            if state.phase == "queued":
                self._cancel_locked(state, "expired", "deadline_exceeded")
                return self._receipt(state)
            else:
                return self._receipt(state, "started_pending")

    def submit(self, command, proof_handle, execution):
        return self.wait(self.enqueue(command, proof_handle, execution))

    def cancel_queued(self, submission):
        self._external_entry()
        state = self._state(submission)
        with self._condition:
            if state.phase != "queued":
                return False
            self._cancel_locked(state, "cancelled_before_start", "cancelled_before_start")
        return True

    def _execute(self, state):
        _, remaining = self._check_context(state.execution)
        if remaining <= 0:
            state.outcome, state.failure = "expired", "deadline_exceeded"
            return
        auth = self.resolver.resolve(state.proof_handle, state.command)
        if type(auth) is not AuthContext:
            raise ValueError("External proof unavailable")
        auth = AuthContext.model_validate_json(auth.model_dump_json())
        if self._check_context(state.execution)[1] <= 0:
            state.outcome, state.failure = "expired", "deadline_exceeded"
            return
        tag = state.command.tag
        if tag in {"batch", "transfer"}:
            state.outcome, state.failure = "unavailable", "unavailable"
            return
        if tag == "inspect-profile":
            inspection = self.registry.inspect(self.release.release_id)
            if self._check_context(state.execution)[1] <= 0:
                state.outcome, state.failure = "expired", "deadline_exceeded"
            else:
                state.inspection, state.outcome = inspection, "inspection"
            return
        if self._resources is None:
            self._resources = self.factory.create(self.release, self.clock)
            if not isinstance(self._resources, RuntimeResources):
                raise ValueError("Complete creator-owned resources required")
        if self._check_context(state.execution)[1] <= 0:
            state.outcome, state.failure = "expired", "deadline_exceeded"
            return
        engine, command = self._resources.engine, state.command
        if tag == "run":
            result = engine.run(command.request, auth, execution=state.execution)
        elif tag == "recover":
            result = engine.recover(command.case_id, auth, execution=state.execution)
        elif tag == "reply":
            result = engine.reply(command.reply, auth, execution=state.execution)
        else:
            result = engine.stop(command.case_id, command.generation, auth, execution=state.execution)
        if type(result) not in (CaseResult, SavedResult):
            raise ValueError("Actual scoped runtime result required")
        state.result, state.outcome = CaseResult.model_validate_json(result.model_dump_json()), "result"

    def _owner(self):
        try:
            while True:
                with self._condition:
                    while not self._queue and not self._finalize_queue:
                        if self._closing and not self._admitting and not self._publishing and not self._pending:
                            return
                        self._condition.wait()
                    if self._finalize_queue:
                        state = self._finalize_queue.popleft()
                        finalize_only = True
                    else:
                        state = self._queue.popleft()
                        finalize_only = False
                    if finalize_only:
                        clock_failed = False
                    else:
                        state.phase = "started"
                        clock_failed = False
                        try:
                            state.started_at = self._now()
                        except Exception:
                            state.phase = "finishing"
                            state.outcome, state.failure = "denied", "scope_denied"
                            clock_failed = True
                if finalize_only or clock_failed:
                    self._finish(state)
                    continue
                try:
                    self._publish(state, "started")
                except InventoryFailure:
                    state.outcome, state.failure = "infrastructure_error", "no_durable_inventory"
                    self._finish(state)
                    continue
                try:
                    self._execute(state)
                except ValueError:
                    state.outcome, state.failure = "denied", "scope_denied"
                except Exception:
                    state.outcome, state.failure = "infrastructure_error", "runtime_error"
                self._finish(state)
        finally:
            try:
                if self._resources is not None:
                    self._resources.close()
            finally:
                if self._inventory is not None:
                    self._inventory.close()
                with self._condition:
                    self._owner_closed = True
                    self._condition.notify_all()

    def close(self, shutdown_cutoff):
        self._external_entry()
        started, anchor = self._now(), self._monotonic()
        if not isinstance(shutdown_cutoff, datetime) or shutdown_cutoff.utcoffset() is None:
            raise ValueError("Aware shutdown cutoff required")
        allowance = max(0.0, (shutdown_cutoff - started).total_seconds())
        if allowance > self.limits.shutdown_max_seconds:
            raise ValueError("Shutdown exceeds configured ceiling")
        with self._condition:
            self._closing = True
            cancelled = tuple(self._queue)
            for state in cancelled:
                self._cancel_locked(state, "cancelled_before_start", "cancelled_before_start")
            self._condition.notify_all()
        remaining = max(0.0, min((shutdown_cutoff - self._now()).total_seconds(), allowance - (self._monotonic() - anchor)))
        self._thread.join(remaining)
        finished, elapsed = self._now(), self._monotonic() - anchor
        with self._condition:
            return ShutdownReceiptV1(admission_closed=True, owner_closed=self._owner_closed,
                pending_command_ids=tuple(self._pending), cancelled_command_ids=tuple(state.command_id for state in cancelled),
                started_at=started, finished_at=finished, elapsed_seconds=elapsed,
                overrun_seconds=max(0.0, elapsed - allowance, (finished - shutdown_cutoff).total_seconds()),
                inventory_failure=self._inventory_failed)
