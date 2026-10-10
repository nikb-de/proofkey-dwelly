"""Read completed local drafts into inert, bounded shadow observations."""
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import re

from .source import ShadowError, load_source
from .store import ShadowStore


_HASH = re.compile(r"[a-f0-9]{64}")
_BINDING = {"case_id", "object_id", "principal_id", "request_id", "request_revision",
            "consent_revision", "generation", "fingerprint", "supersedes_generation"}
_TARGET = {"binding", "profile_version", "process_version", "policy_version", "checkpoint_hash", "checked_at"}
_HOST_REASONS = {"scope_denied", "source_invalid", "source_mismatch", "binding_stale",
                 "runtime_unavailable", "case_stopped", "clock_invalid", "checkpoint_expired"}
_STORE_REASONS = {"unsafe_shadow_directory", "unsafe_shadow_database", "shadow_storage_busy",
                  "shadow_storage_error", "invalid_shadow_identity", "invalid_shadow_content", "idempotency_conflict"}


class _Invalid(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _require(condition, reason="resolver_invalid"):
    if not condition:
        raise _Invalid(reason)


def _identifier(value):
    return (type(value) is str and 1 <= len(value) <= 256 and bool(value.strip())
            and re.search(r"[\x00-\x1f\x7f]", value) is None)


def _target(value):
    _require(type(value) is dict and set(value) == _TARGET)
    binding = value["binding"]
    _require(type(binding) is dict and set(binding) == _BINDING)
    for key in _BINDING - {"fingerprint", "supersedes_generation"}:
        _require(_identifier(binding[key]))
    _require(binding["supersedes_generation"] is None or _identifier(binding["supersedes_generation"]))
    for item in (binding["fingerprint"], value["checkpoint_hash"]):
        _require(type(item) is str and _HASH.fullmatch(item) is not None)
    for key in ("profile_version", "process_version", "policy_version"):
        _require(_identifier(value[key]))
    stamp = value["checked_at"]
    _require(type(stamp) is str and len(stamp) <= 64)
    try:
        parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        _require("T" in stamp and parsed.utcoffset() is not None)
    except (ValueError, TypeError, OverflowError):
        raise _Invalid("resolver_invalid") from None
    # Detach the trusted host's mutable containers before persisting.
    return json.loads(json.dumps(value, allow_nan=False))


def _resolve(resolver, source):
    if resolver is None:
        return "unmapped", "resolver_absent", None
    try:
        value = resolver(source.case_id, source.snapshot_hash)
    except Exception:
        raise _Invalid("resolver_unavailable") from None
    _require(type(value) is dict)
    status = value.get("status")
    if status == "bound":
        _require(set(value) == {"status", "reason", "target"} and value["reason"] is None)
        return "shadow_recorded", None, _target(value["target"])
    _require(set(value) == {"status", "reason"})
    reason = value["reason"]
    _require(type(reason) is str)
    if status == "unmapped":
        _require(reason == "mapping_absent")
    else:
        _require(status == "rejected" and reason in _HOST_REASONS)
    return status, reason, None


def _paths(service_root, shadow_root, resolver):
    """Compute output exclusions before the store can create any directories."""
    try:
        service = Path(service_root).resolve(strict=True)
        output = Path(shadow_root)
        _require(".." not in output.parts, "unsafe_shadow_directory")
        output = output.resolve(strict=False)
    except _Invalid:
        raise
    except (OSError, TypeError, ValueError):
        raise _Invalid("source_path_unsafe") from None
    protected = [service]
    if resolver is not None:
        try:
            roots = resolver.shadow_protected_roots
            _require(type(roots) is tuple)
            for root in roots:
                _require(isinstance(root, (str, Path)))
                path = Path(root)
                _require(path.is_absolute() and ".." not in path.parts)
                _require(path == path.resolve(strict=True) and path.is_dir())
                protected.append(path)
        except Exception:
            raise _Invalid("resolver_invalid") from None
    for root in protected:
        _require(output != root and root not in output.parents and output not in root.parents,
                 "shadow_root_overlap")
    return service


def _record(status, reason, source=None, target=None):
    return {"schema_version": "dwelly-shadow-record-v1", "status": status, "reason": reason,
            "source": source, "target": target, "effects": [], "authorization": False}


def _validate_readback(record, content):
    """Storage corruption must not bypass the bridge's public wire contract."""
    _require(type(record) is dict and set(record) == set(content) | {"import_id"}, "shadow_storage_error")
    _require(type(record["import_id"]) is str and _HASH.fullmatch(record["import_id"]) is not None,
             "shadow_storage_error")
    try:
        returned = json.loads(json.dumps(record, allow_nan=False))
        returned.pop("import_id")
        expected = json.loads(json.dumps(content, allow_nan=False))
        if returned.get("target") is not None:
            _target(returned["target"])
            returned["target"].pop("checked_at")
            expected["target"].pop("checked_at")
        _require(json.dumps(returned, sort_keys=True, allow_nan=False) ==
                 json.dumps(expected, sort_keys=True, allow_nan=False), "shadow_storage_error")
    except (ValueError, TypeError, KeyError):
        raise _Invalid("shadow_storage_error") from None
    return record


def import_shadow(service_root, job_id, case_id, shadow_root, *, resolver=None):
    """Persist an inert observation, or return a sanitized nonpersistent rejection.

    A resolver is trusted host code with fixed authentication and canonical
    ``shadow_protected_roots``. The CLI deliberately supplies no resolver.
    """
    summary = None
    try:
        namespace = _paths(service_root, shadow_root, resolver)
        source = load_source(service_root, job_id, case_id)
        summary = source.summary()
        status, reason, target = _resolve(resolver, source)
        if status == "rejected":
            return {**_record(status, reason, summary), "import_id": None}
        content = _record(status, reason, summary, target)
        target_identity = "unmapped" if target is None else {
            key: target["binding"][key] for key in ("case_id", "object_id", "principal_id", "request_id")}
        identity = {"service_namespace": sha256(str(namespace).encode()).hexdigest(),
                    "job_id": source.job_id, "source_case_id": source.case_id, "target": target_identity}
        stored = ShadowStore(shadow_root).record(identity, content)
        return _validate_readback(stored, content)
    except ShadowError as error:
        reason = error.code
    except _Invalid as error:
        reason = error.code
    except ValueError as error:
        code = getattr(error, "code", None)
        reason = code if type(code) is str and code in _STORE_REASONS else "shadow_storage_error"
    except (OSError, TypeError, RecursionError, OverflowError):
        reason = "shadow_storage_error"
    return {**_record("rejected", reason, summary), "import_id": None}
