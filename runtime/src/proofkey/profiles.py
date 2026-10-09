"""Trusted, versioned offline profile loading and input normalization."""
import json
from pathlib import Path

from .contracts import CanonicalRequest, EnvironmentProfile
from .identity import fingerprint
from .process import validate_process
from .packet_contracts import packet_enabled

_ROOT = Path(__file__).resolve().parents[2]
_SYNTHETIC_POLICY = {"policy_id": "synthetic-test-policy-v1", "version": "v1",
                     "evidence_mode": "synthetic", "native_routes_enabled": False,
                     "live_roles": {"extraction": False, "transcription": False, "planning": False},
                     "wait_expiry_seconds": 300, "internal_case_creation": False,
                     "automatic_reminders": False}


def _strict_json(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON field")
        result[key] = value
    return result


def requires_completed_service(profile: EnvironmentProfile) -> bool:
    """Frozen legacy releases retain semantics; declared coverage opts in.

    New profile versions cannot silently remove the lifecycle guarantee.
    """
    capability = profile.capabilities.get("register_service_refusal")
    return (profile.version not in {"v1", "v1.1"}
            or capability is not None and "delivery.status" in capability.conditional_coverage.covered_fields)


def _mapping_tree(profile):
    tree, canonical = {}, set()
    for mapping in profile.mappings.values():
        field = mapping.canonical_field
        if field not in CanonicalRequest.model_fields or field in canonical:
            raise ValueError("Mapping must name one unique canonical input field")
        if field == "consent_mode" and any(key != value for key, value in mapping.value_map.items()):
            raise ValueError("Mappings cannot infer or change business consent")
        canonical.add(field)
        parts = mapping.source_path.split(".")
        if any(not part or part in {"__proto__", "__class__"} for part in parts):
            raise ValueError("Invalid mapping path")
        node = tree
        for part in parts:
            if not isinstance(node, dict):
                raise ValueError("Mapping source paths cannot overlap")
            node = node.setdefault(part, {})
        if node:
            raise ValueError("Mapping source paths cannot overlap")
        parent = tree
        for part in parts[:-1]:
            parent = parent[part]
        parent[parts[-1]] = mapping
    required = {name for name, field in CanonicalRequest.model_fields.items() if field.is_required()}
    if not required <= canonical:
        raise ValueError("Mapping omits required canonical input fields")
    return tree


def load_profile(path: str | Path) -> EnvironmentProfile:
    """Load a reviewed built-in name or caller-selected trusted file path.

    Release hashes detect changes; they are not signatures or approval receipts.
    Request content must never choose this path. Unknown capabilities are kept
    intact so the controller/policy can deny the corresponding operation.
    """
    path = Path(path)
    if str(path) in {"flat-v1", "nested-v1", "flat-v1.1", "nested-v1.1", "flat-v1.2", "nested-v1.2", "flat-v1.3", "nested-v1.3"}:
        path = _ROOT / "profiles" / f"{path.name}.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_strict_json)
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("Profile is unavailable or invalid JSON") from error
    profile = EnvironmentProfile.model_validate(raw)
    data = profile.model_dump(mode="json")
    if profile.release_hash != fingerprint({k: v for k, v in data.items() if k != "release_hash"}):
        raise ValueError("Profile release hash mismatch")
    if profile.process_hash != fingerprint(data["processes"]):
        raise ValueError("Process bundle hash mismatch")
    if profile.policy_hash != fingerprint(_SYNTHETIC_POLICY):
        raise ValueError("Unknown offline policy hash")
    if not profile.processes:
        raise ValueError("Profile needs a finite process bundle")
    for spec in profile.processes.values():
        validate_process(spec)
        process_data = spec.model_dump(mode="json")
        if spec.release_hash != fingerprint({k: v for k, v in process_data.items() if k != "release_hash"}):
            raise ValueError("Process release hash mismatch")
    _mapping_tree(profile)
    if profile.version == "v1.3" and not packet_enabled(profile):
        raise ValueError("v1.3 requires the registered packet content contract")
    packet_enabled(profile)
    return profile


def normalize_input(payload: object, profile: EnvironmentProfile) -> CanonicalRequest:
    """Map only declared input fields; mapping cannot produce authority/policy."""
    if not isinstance(profile, EnvironmentProfile):
        raise ValueError("Normalization requires a typed trusted profile")
    tree = _mapping_tree(profile)
    canonical = {}

    def visit(value, node):
        if not isinstance(value, dict) or not set(value) <= set(node):
            raise ValueError("Unexpected mapping envelope or input field")
        for key, item in value.items():
            branch = node[key]
            if isinstance(branch, dict):
                visit(item, branch)
            else:
                if branch.value_map:
                    if not isinstance(item, str) or item not in branch.value_map:
                        raise ValueError("Unknown mapped input value")
                    item = branch.value_map[item]
                canonical[branch.canonical_field] = item

    visit(payload, tree)
    request = CanonicalRequest.model_validate(canonical)
    if request.kind not in profile.processes:
        raise ValueError("Input names an unknown reviewed process kind")
    mode = {"reschedule_window": "window", "reschedule_exact": "exact_slot"}.get(request.kind)
    if mode and request.consent_mode not in {mode, "unknown"}:
        raise ValueError("Consent does not match the requested process")
    return request
