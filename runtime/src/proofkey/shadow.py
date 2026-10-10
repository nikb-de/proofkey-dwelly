"""Optional host-owned, point-in-time associations; never execution authority.

The caller owns the already-open CaseStore and both trusted callbacks. This
module opens no store, invokes no gateway and persists no runtime state.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import threading
from typing import Annotated

from pydantic import Field, StringConstraints, model_validator

from .contracts import AuthContext, Hash, RequestBinding, WireModel
from .identity import fingerprint, validate_json
from .journal import CaseStore


_SourceId = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,255}$")]
_BoundedId = Annotated[str, StringConstraints(min_length=1, max_length=256, pattern=r"^\S(?:[^\x00-\x1f\x7f]*\S)?$")]


class RuntimeShadowTarget(WireModel):
    """Frozen host registration of one exact source and runtime checkpoint."""

    source_case_id: _SourceId
    source_snapshot_hash: Hash
    binding: RequestBinding
    checkpoint_hash: Hash
    profile_version: _BoundedId
    process_version: _BoundedId
    policy_version: _BoundedId
    allowed_caller_ids: Annotated[tuple[_BoundedId, ...], Field(min_length=1, max_length=256)]

    @model_validator(mode="after")
    def bounded_registration(self):
        if len(set(self.allowed_caller_ids)) != len(self.allowed_caller_ids):
            raise ValueError("Duplicate shadow caller")
        for value in self.binding.model_dump().values():
            if value is not None and (type(value) is not str or len(value) > 256
                                      or re.search(r"[\x00-\x1f\x7f]", value)):
                raise ValueError("Unbounded shadow binding")
        return self


def _rejected(reason):
    return {"status": "rejected", "reason": reason}


class RuntimeShadowResolver:
    """Resolve only on the CaseStore's owning thread with fixed host auth.

    Registrations and authentication are detached at construction. ``authorize``
    receives a detached registration and AuthContext and must return literal
    True. Its execution is covered by SQLite query_only as well as the read
    transaction; callback failure never reveals the target.
    """

    def __init__(self, store, registrations, *, authorize, auth, clock):
        if (type(store) is not CaseStore or not callable(authorize) or not callable(clock)
                or type(auth) is not AuthContext or type(registrations) not in (tuple, list)
                or len(registrations) > 1024):
            raise ValueError("Invalid shadow host configuration")
        try:
            self._auth = AuthContext.model_validate(auth.model_dump())
            self._registrations = {}
            for target in registrations:
                if type(target) is not RuntimeShadowTarget:
                    raise ValueError()
                target = RuntimeShadowTarget.model_validate(target.model_dump())
                if target.source_case_id in self._registrations:
                    raise ValueError()
                self._registrations[target.source_case_id] = target
        except Exception:
            raise ValueError("Invalid shadow host registration") from None
        self._store, self._authorize, self._clock = store, authorize, clock

    @property
    def shadow_protected_roots(self) -> tuple[Path, ...]:
        """Trusted output-exclusion roots; reading them never opens a store.

        Bridge hosts must exclude these canonical directories from shadow
        storage. An unavailable main database raises a bounded error rather
        than supplying an empty set that could disable overlap protection.
        """
        store = self._store
        if threading.get_ident() != store._owner_thread or store._db is None:
            raise ValueError("runtime_unavailable")
        try:
            paths = [row[2] for row in store._db.execute("PRAGMA database_list") if row[1] == "main"]
            if len(paths) != 1 or type(paths[0]) is not str or not paths[0]:
                raise ValueError()
            path = Path(paths[0]).resolve(strict=True)
            if not path.is_file():
                raise ValueError()
            return (path.parent,)
        except Exception:
            raise ValueError("runtime_unavailable") from None

    def __call__(self, source_case_id, snapshot_hash):
        if (type(source_case_id) is not str or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,255}", source_case_id) is None
                or type(snapshot_hash) is not str or re.fullmatch(r"[a-f0-9]{64}", snapshot_hash) is None):
            return _rejected("source_invalid")
        target = self._registrations.get(source_case_id)
        if target is None:
            return {"status": "unmapped", "reason": "mapping_absent"}
        if snapshot_hash != target.source_snapshot_hash:
            return _rejected("source_mismatch")
        store = self._store
        if (threading.get_ident() != store._owner_thread or store._db is None
                or store._execution is not None):
            return _rejected("runtime_unavailable")
        db = store._db
        if db.in_transaction:
            return _rejected("runtime_unavailable")
        previous_query_only = None
        result = _rejected("runtime_unavailable")
        try:
            previous_query_only = db.execute("PRAGMA query_only").fetchone()[0]
            db.execute("PRAGMA query_only=ON")
            db.execute("BEGIN")
            result = self._resolve_snapshot(target)
        except Exception:
            result = _rejected("runtime_unavailable")
        finally:
            try:
                if db.in_transaction:
                    db.execute("ROLLBACK")
                if previous_query_only is not None:
                    db.execute("PRAGMA query_only=" + str(int(previous_query_only)))
            except Exception:
                result = _rejected("runtime_unavailable")
        return result

    def _resolve_snapshot(self, target):
        if self._auth.caller_id not in target.allowed_caller_ids:
            return _rejected("scope_denied")
        try:
            authorized = self._authorize(RuntimeShadowTarget.model_validate(target.model_dump()),
                                         AuthContext.model_validate(self._auth.model_dump()))
        except Exception:
            return _rejected("scope_denied")
        if authorized is not True:
            return _rejected("scope_denied")
        checkpoint = self._store.checkpoint(target.binding.case_id)
        original = self._store.original_request(target.binding.case_id, checkpoint.binding.generation)
        if original is None:
            return _rejected("binding_stale")
        if checkpoint.stop.requested or checkpoint.phase == "stopped" or checkpoint.ownership_state == "stopped":
            return _rejected("case_stopped")
        if (checkpoint.binding != target.binding
                or any(getattr(checkpoint, field) != getattr(target, field)
                       for field in ("profile_version", "process_version", "policy_version"))
                or fingerprint(checkpoint.model_dump(mode="json")) != target.checkpoint_hash):
            return _rejected("binding_stale")
        try:
            now = self._clock()
            if type(now) is not datetime or now.utcoffset() is None:
                return _rejected("clock_invalid")
            now = now.astimezone(timezone.utc)
        except Exception:
            return _rejected("clock_invalid")
        if now >= checkpoint.deadline:
            return _rejected("checkpoint_expired")
        payload = dict(binding=checkpoint.binding.model_dump(mode="json"),
                       profile_version=checkpoint.profile_version, process_version=checkpoint.process_version,
                       policy_version=checkpoint.policy_version, checkpoint_hash=target.checkpoint_hash,
                       checked_at=now.isoformat())
        validate_json(payload)
        if len(json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")) > 16384:
            return _rejected("binding_stale")
        return {"status": "bound", "reason": None, "target": payload}
