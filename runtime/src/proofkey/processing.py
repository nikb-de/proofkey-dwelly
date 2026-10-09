"""Immutable host admission accounting; no processor, permit or entry grant."""
from dataclasses import dataclass
import math
from typing import Literal


def _finite_nonnegative(value):
    if type(value) not in (int, float):
        raise ValueError("Accounting limits require exact numbers, not bool/custom values")
    try:
        valid = math.isfinite(value) and value >= 0
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError("Accounting limits require finite nonnegative numbers")


@dataclass(frozen=True, slots=True)
class RoleAdmissionLimits:
    role: Literal["extraction", "transcription", "planning"]
    max_invocations: int
    usage_allowances: tuple[tuple[str, float], ...]
    max_cost: float

    def __post_init__(self):
        if type(self.role) is not str or self.role not in {"extraction", "transcription", "planning"}:
            raise ValueError("Only declared processing roles may receive admission limits")
        if type(self.max_invocations) is not int or self.max_invocations < 0:
            raise ValueError("Invocation capacity requires an exact nonnegative integer")
        _finite_nonnegative(self.max_cost)
        if type(self.usage_allowances) is not tuple:
            raise ValueError("Usage allowances require an immutable tuple")
        names = []
        for pair in self.usage_allowances:
            if type(pair) is not tuple or len(pair) != 2:
                raise ValueError("Usage allowances require immutable unit/amount pairs")
            name, amount = pair
            if type(name) is not str or not name.strip():
                raise ValueError("Usage units require nonempty exact names")
            _finite_nonnegative(amount)
            names.append(name)
        if names != sorted(set(names)):
            raise ValueError("Usage units must be unique and sorted")
        if self.max_invocations and not names:
            raise ValueError("Enabled roles require explicit named usage allowances")


def freeze_processing_allowances(allowances):
    """Validate and detach the constructor recipe before any source/store entry."""
    if allowances is None:
        return None
    if type(allowances) is not tuple or len(allowances) > 3:
        raise ValueError("Processing configuration requires at most three immutable roles")
    detached = []
    for item in allowances:
        if type(item) is not RoleAdmissionLimits:
            raise ValueError("Processing configuration requires exact typed role limits")
        detached.append(RoleAdmissionLimits(item.role, item.max_invocations,
            item.usage_allowances, item.max_cost))
    if len({item.role for item in detached}) != len(detached):
        raise ValueError("Processing configuration cannot repeat a role")
    if sum(item.max_invocations for item in detached) > 24:
        raise ValueError("Processing capacity exceeds the case tool ceiling")
    if any(item.role == "planning" and item.max_invocations > 4 for item in detached):
        raise ValueError("Planning capacity exceeds the case planner ceiling")
    return tuple(detached)
