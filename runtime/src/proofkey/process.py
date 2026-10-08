"""Finite offline graph gates; callers still need policy/auth/journal checks.

Prerequisites are observations from the trusted core, never request narrative.
Synthetic manifests describe test-world guarantees and enable no native route.
"""
from collections.abc import Mapping

from .contracts import EnvironmentProfile, ProcessSpec


BASE_MATERIAL = frozenset({"case.binding", "case.request_revision", "customer.consent",
                          "customer.consent_revision", "delivery.risk", "delivery.stage",
                          "policy.version", "ownership.state_revision"})
_ESCAPE_OPERATIONS = frozenset({"request_stop", "ask_operator", "ask_customer", "expire_wait", "read_effect"})


def material_fields(operation: str) -> frozenset[str]:
    """Minimum designated revision coverage; capabilities may cover more."""
    extra = {
        "reschedule": {"scheduling.capacity", "scheduling.slot", "delivery.status"},
        "register_goods_refusal": {"goods.inventory", "goods.quantity", "delivery.status"},
        "create_return": {"goods.inventory", "goods.quantity", "goods.refusal", "delivery.status", "returns.destination"},
    }
    return BASE_MATERIAL | extra.get(operation, set())


def validate_process(spec: ProcessSpec) -> None:
    """Reject broken finite graphs before they can interpret saved checkpoints."""
    phases, operations = set(spec.phases), set(spec.operations)
    if len(phases) != len(spec.phases) or len(operations) != len(spec.operations):
        raise ValueError("Process phases and operations must be unique")
    if "intake" not in phases or spec.completion.phase not in phases:
        raise ValueError("Process needs intake and a declared completion phase")
    if not set(spec.completion.required_operations) <= operations:
        raise ValueError("Completion names an undeclared operation")
    pairs = set()
    for edge in spec.edges:
        if edge.origin not in phases or edge.target not in phases or edge.operation not in operations:
            raise ValueError("Process edge names an undeclared phase/operation")
        key = (edge.origin, edge.operation)
        if key in pairs:
            raise ValueError("A phase/operation must select exactly one edge")
        pairs.add(key)
        if edge.origin in {spec.completion.phase, "stopped"}:
            raise ValueError("Terminal phases cannot dispatch further operations")
    for requirement in spec.prerequisites:
        if requirement.phase not in phases:
            raise ValueError("Prerequisite phase is undeclared")
    for wait in spec.waits:
        if wait.phase not in phases or wait.next_gate not in phases or not wait.awaited_fields:
            raise ValueError("Wait contract is incomplete")
        if not any(e.origin == wait.phase and e.target == wait.next_gate for e in spec.edges):
            raise ValueError("Wait next gate must be an explicit graph edge")
    if any(a.operation not in operations or not a.required_scope for a in spec.approvals):
        raise ValueError("Approval scope/operation is incomplete")
    if not set(spec.acknowledgements) <= operations or not set(spec.readbacks) <= operations:
        raise ValueError("Process contract names an undeclared operation")


class ProcessController:
    def __init__(self, profile: EnvironmentProfile, kind: str | None = None):
        if not isinstance(profile, EnvironmentProfile):
            raise ValueError("Controller requires a typed trusted profile")
        if kind is not None and kind not in profile.processes:
            raise ValueError("Unknown process kind")
        for spec in profile.processes.values():
            validate_process(spec)
        self.profile = profile
        self.kind = kind

    def permits(self, phase: str, operation: str, observed_prerequisites: Mapping[str, object]) -> bool:
        return self.next_phase(phase, operation, observed_prerequisites) is not None

    def next_phase(self, phase: str, operation: str, observed_prerequisites: Mapping[str, object]) -> str | None:
        """Return the unique permitted successor, or None (never guess a kind)."""
        if not isinstance(observed_prerequisites, Mapping):
            return None
        specs = ([self.profile.processes[self.kind]] if self.kind is not None
                 else self.profile.processes.values())
        matches = [(spec, edge) for spec in specs for edge in spec.edges
                   if edge.origin == phase and edge.operation == operation]
        if len(matches) != 1:
            return None
        spec, edge = matches[0]
        if edge.condition is not None and observed_prerequisites.get(edge.condition) is not True:
            return None
        for requirement in spec.prerequisites:
            if requirement.phase != phase or operation in _ESCAPE_OPERATIONS:
                continue
            qualified = f"{requirement.authority}.{requirement.fact}"
            # Brief-compatible short names only when the qualified observation is
            # absent. A conflicting alias must never override designated facts.
            value = observed_prerequisites.get(qualified, observed_prerequisites.get(requirement.fact))
            if value != requirement.expected or type(value) is not type(requirement.expected):
                return None
        capability = self.profile.capabilities.get(operation)
        if capability is None or capability.operation != operation or capability.evidence_mode != "synthetic":
            return None
        contracts = [capability.permission_basis, capability.acknowledgement, capability.readback,
                     capability.idempotency_scope, capability.conditional_coverage,
                     capability.terminal_nonexecution_basis,
                     spec.acknowledgements.get(operation), spec.readbacks.get(operation)]
        if any(c is None or c.status != "supported" or not c.basis or not c.evidence_ref for c in contracts):
            return None
        required = material_fields(operation)
        if not required <= set(capability.conditional_coverage.covered_fields):
            return None
        if any(self.profile.authorities.get(key) != key.partition(".")[0] for key in required):
            return None
        limits = capability.shared_limits
        if (capability.timeout_seconds is None or capability.version is None or
                limits.account_id is None or limits.quota is None or limits.quota <= 0 or
                limits.concurrency is None or limits.concurrency <= 0 or
                limits.rate_per_second is None or limits.rate_per_second <= 0):
            return None
        return edge.target
