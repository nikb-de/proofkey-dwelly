"""Immutable trusted-host timing, never caller permission or a hard-kill sandbox."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math


def _utc(value):
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError("Execution timing requires an aware UTC timestamp")
    return value.astimezone(timezone.utc)


def _monotonic(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("Execution timing requires a finite monotonic observation")
    return float(value)


def _sample(clock, *, capture=False):
    if not callable(getattr(clock, "now", None)) or not callable(getattr(clock, "monotonic", None)):
        raise ValueError("Trusted UTC and monotonic clock required")
    if capture:
        # An early monotonic anchor cannot extend setup/capture time.
        monotonic = _monotonic(clock.monotonic())
        return _utc(clock.now()), monotonic
    # Current entry checks include time spent obtaining the UTC observation.
    now = _utc(clock.now())
    return now, _monotonic(clock.monotonic())


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    deadline: datetime
    captured_at: datetime
    captured_monotonic: float
    monotonic_deadline: float

    def __post_init__(self):
        deadline, captured = _utc(self.deadline), _utc(self.captured_at)
        start, cutoff = _monotonic(self.captured_monotonic), _monotonic(self.monotonic_deadline)
        if cutoff != start + max(0.0, (deadline - captured).total_seconds()):
            raise ValueError("Execution cutoff must retain the original captured window")
        object.__setattr__(self, "deadline", deadline)
        object.__setattr__(self, "captured_at", captured)
        object.__setattr__(self, "captured_monotonic", start)
        object.__setattr__(self, "monotonic_deadline", cutoff)

    @classmethod
    def capture(cls, deadline, clock):
        deadline = _utc(deadline)
        now, monotonic = _sample(clock, capture=True)
        return cls(deadline, now, monotonic, monotonic + max(0.0, (deadline - now).total_seconds()))

    def window(self, clock):
        """Actual observed UTC and no-later physical cutoff from one sample."""
        now, monotonic = _sample(clock)
        if monotonic < self.captured_monotonic:
            raise ValueError("Monotonic clock moved backwards")
        remaining = max(0.0, min((self.deadline - now).total_seconds(), self.monotonic_deadline - monotonic))
        return now, min(self.deadline, now + timedelta(seconds=remaining))

    def remaining_seconds(self, clock):
        now, cutoff = self.window(clock)
        return max(0.0, (cutoff - now).total_seconds())

    def effective_deadline(self, clock):
        return self.window(clock)[1]
