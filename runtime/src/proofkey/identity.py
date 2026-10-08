"""Provider-neutral identities; arguments are deliberately not action identity."""
import hashlib
import json
import math


def validate_json(value) -> None:
    """Require genuine JSON values; JSON encoders otherwise coerce bad keys."""
    if value is None or type(value) in (str, bool, int):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("JSON values must be finite")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("JSON object keys must be strings")
            validate_json(item)
        return
    if isinstance(value, list):
        for item in value:
            validate_json(item)
        return
    raise TypeError("Expected a JSON value")


def fingerprint(arguments: dict) -> str:
    if not isinstance(arguments, dict):
        raise TypeError("Arguments must be a JSON object")
    validate_json(arguments)
    encoded = json.dumps(arguments, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def request_fingerprint(request) -> str:
    """Business semantics only; request/revision identity is separately bound.

    Narrative and transport metadata do not mint a new business intent. Consent
    scope and kind must participate even when their arguments happen to match.
    """
    return fingerprint({"kind": request.kind, "consent_mode": request.consent_mode,
                        "arguments": request.arguments})


def stable_action_id(binding, operation: str, stage: str) -> str:
    for value in (binding.case_id, binding.object_id, binding.generation, operation, stage):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Action identity components require nonempty strings")
    return fingerprint({"case": binding.case_id, "object": binding.object_id,
                        "generation": binding.generation,
                        "operation": operation, "stage": stage})
