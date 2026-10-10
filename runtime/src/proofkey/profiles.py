"""Trusted, versioned offline profile loading and input normalization."""
import json
import re
from pathlib import Path

from .contracts import CanonicalRequest, EnvironmentProfile
from .identity import fingerprint
from .process import validate_process
from .packet_contracts import packet_enabled
from .ownership_contracts import ownership_enabled

_ROOT = Path(__file__).resolve().parent / "resources"
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
    if str(path) in {"flat-v1", "nested-v1", "flat-v1.1", "nested-v1.1", "flat-v1.2", "nested-v1.2", "flat-v1.3", "nested-v1.3", "flat-v1.4", "nested-v1.4", "flat-window-readiness-v1"}:
        path = _ROOT / "profiles" / f"{path.name}.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_strict_json)
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("Profile is unavailable or invalid JSON") from error
    profile = EnvironmentProfile.model_validate(raw)
    return validate_profile(profile)


def validate_profile(profile: EnvironmentProfile) -> EnvironmentProfile:
    """Apply the loader's canonical checks to detached in-memory profile data."""
    profile = EnvironmentProfile.model_validate(profile.model_dump(mode="json"))
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
    if profile.version in {"v1.3", "v1.4"} and not packet_enabled(profile):
        raise ValueError("Registered profile requires the packet content contract")
    packet_enabled(profile)
    if profile.version == "v1.4" and not ownership_enabled(profile):
        raise ValueError("v1.4 requires the registered ownership contract")
    ownership_enabled(profile)
    return profile


WINDOW_READINESS_FACTORY_KEY = "fixed-synthetic-window-readiness-v3"
WINDOW_READINESS_PROFILE_ID = "flat-window-readiness-v1"
WINDOW_READINESS_PROCESS_VERSION = "v2-window-readiness"
WINDOW_READINESS_IMPLEMENTATION_PATHS = (
    '__init__.py', 'adapters/__init__.py', 'adapters/case.py', 'adapters/delivery.py',
    'adapters/messaging.py', 'adapters/operator.py', 'adapters/ownership.py', 'adapters/returns.py',
    'adapters/scheduling.py', 'adapters/world.py', 'admission.py', 'admission_routes.py', 'api.py',
    'assessment/__init__.py', 'assessment/audit.py', 'assessment/cache.py', 'assessment/contracts.py',
    'assessment/coverage.py', 'assessment/drills.py', 'assessment/driver_contracts.py', 'assessment/drivers.py',
    'assessment/isolation.py', 'assessment/labels.py', 'assessment/ledger.py', 'assessment/readiness.py',
    'batch.py', 'batch_files.py', 'bootstrap.py', 'budget.py', 'cli.py', 'clock.py', 'contracts.py', 'engine.py',
    'evidence/__init__.py', 'evidence/catalog.py', 'evidence/intake.py', 'evidence/processing_contracts.py',
    'evidence/redaction.py', 'execution.py', 'execution_consumer.py', 'execution_trace.py', 'exporter.py',
    'factory/__init__.py', 'factory/proposal.py', 'factory/release.py', 'factory/views.py', 'gateway.py',
    'host.py', 'host_admission.py', 'host_contracts.py', 'host_files.py', 'host_writer.py', 'identity.py',
    'journal.py', 'ownership.py', 'ownership_contracts.py', 'ownership_gateway.py', 'ownership_store.py',
    'packet_contracts.py', 'packets.py', 'planner.py', 'policy.py', 'ports.py', 'process.py', 'processing.py',
    'processing_orchestration.py', 'processing_summary.py', 'profiles.py', 'providers/__init__.py',
    'providers/anthropic.py', 'providers/elevenlabs.py', 'providers/invocations.py', 'providers/protocols.py',
    'providers/replay.py', 'providers/unavailable.py', 'registered_releases.py', 'release.py', 'replay.py',
    'retained_state.py', 'schema.sql', 'source_retained_state.py', 'synthetic_provisioning.py', 'trace.py',
    'verifier.py', 'wait_contracts.py', 'waits.py',
)


def _window_readiness_profile_data(baseline: EnvironmentProfile) -> dict:
    baseline = validate_profile(baseline)
    if baseline.release_hash != "5bb712b13efaace655ee7180f3d913d93cbd637e3d1685331c6a1eecbade7bf4":
        raise ValueError("Unregistered window-readiness baseline")
    data = baseline.model_dump(mode='json')
    data['profile_id'] = 'flat-window-readiness-v1'
    cap = data['capabilities']['reschedule']
    cap['version'] = 'synthetic-scheduling-dual-v1'
    cap['acknowledgement']['basis'] = 'synthetic-scheduling-dual-v1: window v2 envelope ack only; exact v1 typed ack'
    cap['readback']['basis'] = 'synthetic-scheduling-dual-v1: bounded original scheduling receipt; out-of-domain unavailable'
    for name in ('acknowledgement', 'readback'):
        cap[name]['evidence_ref'] = 'synthetic-scheduling-envelope-v1'
    process = data['processes']['reschedule_window']
    process['process_id'] = 'reschedule-window-readiness-v2'
    process['version'] = 'v2-window-readiness'
    process['phases'].insert(process['phases'].index('window_gate'), 'window_readiness')
    edge = next(e for e in process['edges'] if e['origin'] == 'read_authority' and e['operation'] == 'check_window')
    edge['target'] = 'window_readiness'
    process['edges'].extend([
        {'origin': 'window_readiness', 'operation': 'read_authority', 'target': 'window_gate', 'condition': None},
        {'origin': 'window_readiness', 'operation': 'request_stop', 'target': 'stop', 'condition': None},
        {'origin': 'window_readiness', 'operation': 'ask_operator', 'target': 'wait_operator', 'condition': None},
    ])
    process['prerequisites'].append({'phase': 'window_gate', 'authority': 'scheduling', 'fact': 'slot', 'expected': 'S0'})
    process['acknowledgements']['reschedule'] = dict(cap['acknowledgement'])
    process['readbacks']['reschedule'] = dict(cap['readback'])
    for item in data['processes'].values():
        item['release_hash'] = fingerprint({k: v for k, v in item.items() if k != 'release_hash'})
    data['process_hash'] = fingerprint(data['processes'])
    data['release_hash'] = fingerprint({k: v for k, v in data.items() if k != 'release_hash'})
    return data


def is_window_readiness_profile(profile: EnvironmentProfile) -> bool:
    try:
        actual = validate_profile(profile).model_dump(mode="json")
        return actual == _window_readiness_profile_data(load_profile("flat-v1.3"))
    except (ValueError, TypeError, AttributeError):
        return False


def _validate_selected_profile(factory_key: str, profile: EnvironmentProfile,
                               request_kind: str | None = None) -> None:
    """Accept only a fixed factory/profile selection; otherwise raise ValueError."""
    if type(factory_key) is not str or type(profile) is not EnvironmentProfile:
        raise ValueError("Unsupported fixed profile selection")
    validate_profile(profile)
    if factory_key in ('fixed-synthetic-v1', 'fixed-synthetic-observed-stop-v2'):
        if ((profile.profile_id, profile.version, profile.release_hash,
             profile.process_hash, profile.policy_hash) !=
            ('flat-v1.3', 'v1.3',
             '5bb712b13efaace655ee7180f3d913d93cbd637e3d1685331c6a1eecbade7bf4',
             '91cb93780a0cd1612fbeea2aab4e9ee7ac5cc6007e1d8ee2952d52655a9f75e2',
             '1905842f17fd73559d48f4f2d04928a5be734464b966b7167808a05732cdf752')
                or any(item.version != 'v1' for item in profile.processes.values())):
            raise ValueError("Unsupported fixed profile selection")
    elif factory_key == WINDOW_READINESS_FACTORY_KEY:
        if (not is_window_readiness_profile(profile)
                or (request_kind is not None and request_kind != 'reschedule_window')):
            raise ValueError("Unsupported fixed profile selection")
    else:
        raise ValueError("Unsupported fixed profile selection")


def supports_process_operation(profile: EnvironmentProfile, process_version: str,
                               operation: str, consent_mode: object) -> bool:
    if not is_window_readiness_profile(profile):
        return process_version == "v1"
    if process_version == WINDOW_READINESS_PROCESS_VERSION:
        return (consent_mode == "window" and
                operation in profile.processes["reschedule_window"].operations)
    if process_version != "v1":
        return False
    if operation == "reschedule":
        return consent_mode == "exact_slot"
    return any(spec.version == "v1" and operation in spec.operations
               for spec in profile.processes.values())


def _window_original_request_id(*, account_id: str, provider_key: str, case_id: str,
                                object_id: str, operation: str, generation: str,
                                action_id: str, fingerprint: str, identity_hash: str) -> str:
    from .identity import fingerprint as hash_fields
    fields = dict(account_id=account_id, provider_key=provider_key, case_id=case_id,
                  object_id=object_id, operation=operation, generation=generation,
                  action_id=action_id, fingerprint=fingerprint, identity_hash=identity_hash)
    if any(type(value) is not str or not value.strip() for value in fields.values()):
        raise ValueError("Invalid window original identity")
    if operation != "reschedule" or any(re.fullmatch("[0-9a-f]{64}", value) is None
                                       for value in (fingerprint, identity_hash)):
        raise ValueError("Invalid window original identity")
    return "provider:window-envelope-v1:" + hash_fields(
        {"domain": "synthetic-window-original-v1", **fields})


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
