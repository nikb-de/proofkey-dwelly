"""Immutable trusted-host timing arithmetic; never transport permission."""
from dataclasses import dataclass
from datetime import datetime, timedelta
import math

from .execution import ExecutionContext


def _instant(value):
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError("Aware host instant required")
    return value


def _observation(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("Finite monotonic observation required")
    return float(value)


def _elapsed(value):
    value = _observation(value)
    if value < 0:
        raise ValueError("Nonnegative monotonic elapsed required")
    return value


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
        return None if self.execution is None else _observation(self.clock.monotonic())

    def elapsed_since(self, anchor):
        if self.execution is None:
            raise ValueError("Monotonic elapsed requires a scoped host context")
        return _elapsed(_observation(self.clock.monotonic()) - _observation(anchor))

    def _transport_deadline(self, deadline, lease, anchor):
        if self.execution is None:
            return deadline
        now, cutoff = self.window(deadline)
        # Sample elapsed after observing UTC: observation/construction is part
        # of the committed slice, even when the overall host has time left.
        elapsed = self.elapsed_since(anchor)
        reserved = _elapsed(lease.reserved_seconds)
        if now >= cutoff or elapsed >= reserved:
            raise ValueError("Reserved host execution slice exhausted")
        return min(cutoff, now + timedelta(seconds=reserved - elapsed))
