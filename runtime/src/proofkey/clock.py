"""Actual host timing with an explicitly labeled fixed synthetic replay epoch."""
from datetime import datetime, timedelta, timezone
import math
import time


def _finite(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("Finite host timing required")
    return float(value)


class SystemClock:
    mode = "system_utc"

    def __init__(self, *, max_wait_seconds=120.0):
        self._max_wait_seconds = _finite(max_wait_seconds)
        if self._max_wait_seconds <= 0:
            raise ValueError("Positive bounded wait required")

    def now(self):
        return datetime.now(timezone.utc)

    def monotonic(self):
        return _finite(time.monotonic())

    def wait(self, seconds):
        seconds = _finite(seconds)
        if seconds < 0 or seconds > self._max_wait_seconds:
            raise ValueError("Wait exceeds trusted finite bound")
        time.sleep(seconds)


class SyntheticReplayClock(SystemClock):
    mode = "synthetic_replay"
    _EPOCH = datetime(2026, 10, 8, 10, tzinfo=timezone.utc)

    def __init__(self, *, max_wait_seconds=120.0):
        super().__init__(max_wait_seconds=max_wait_seconds)
        self._anchor = self.monotonic()

    def now(self):
        elapsed = self.monotonic() - self._anchor
        if elapsed < 0:
            raise ValueError("Monotonic host clock reversed")
        return self._EPOCH + timedelta(seconds=elapsed)
