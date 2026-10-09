"""Immutable trusted-host timing arithmetic; never transport permission."""
from dataclasses import dataclass
from datetime import datetime
import math

from .execution import ExecutionContext


def _instant(value):
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError("Aware host instant required")
    return value


def _elapsed(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError("Finite nonnegative monotonic measurement required")
    return float(value)


@dataclass(frozen=True, slots=True)
class ExecutionTiming:
    clock: object
    execution: ExecutionContext | None

    def __post_init__(self):
        if self.execution is not None and type(self.execution) is not ExecutionContext:
            raise ValueError("Exact trusted execution context required")
        if not callable(getattr(self.clock, "now", None)):
            raise ValueError("Trusted host timing clock required")
        if self.execution is not None:
            if not callable(getattr(self.clock, "wait", None)):
                raise ValueError("Bounded host wait required")
            ExecutionContext(self.execution.deadline, self.execution.captured_at,
                self.execution.captured_monotonic, self.execution.monotonic_deadline)
            if self.remaining_seconds(self.execution.deadline) <= 0:
                raise ValueError("Host execution window exhausted")

    def window(self, deadline):
        deadline = _instant(deadline)
        if self.execution is None:
            return _instant(self.clock.now()), deadline
        now, cutoff = self.execution.window(self.clock)
        return now, min(deadline, cutoff)

    def remaining_seconds(self, deadline):
        now, cutoff = self.window(deadline)
        return max(0.0, (cutoff - now).total_seconds())

    def monotonic_anchor(self):
        return None if self.execution is None else _elapsed(self.clock.monotonic())

    def elapsed_since(self, anchor):
        if self.execution is None:
            raise ValueError("Monotonic elapsed requires a scoped host context")
        return _elapsed(_elapsed(self.clock.monotonic()) - _elapsed(anchor))
