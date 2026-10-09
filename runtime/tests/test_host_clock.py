"""Real local timing, explicit replay epoch; no native timing qualification."""
from datetime import datetime, timezone
import math
import unittest
from unittest.mock import patch

from proofkey.clock import SyntheticReplayClock, SystemClock


class HostClockTests(unittest.TestCase):
    def test_system_clock_actual_aware_progress_and_bounded_wait(self):
        clock = SystemClock(max_wait_seconds=0.05)
        before = clock.monotonic()
        now = clock.now()
        clock.wait(0.003)
        self.assertGreater(clock.monotonic(), before)
        self.assertIsNotNone(now.utcoffset())
        self.assertLess(abs((datetime.now(timezone.utc) - clock.now()).total_seconds()), 1)
        for value in (-1, True, math.inf, math.nan, 0.06):
            with self.assertRaises(ValueError):
                clock.wait(value)

    def test_replay_epoch_progresses_with_actual_monotonic_not_constant_or_body_time(self):
        clock = SyntheticReplayClock(max_wait_seconds=0.05)
        epoch = datetime(2026, 10, 8, 10, tzinfo=timezone.utc)
        before = clock.now()
        self.assertLess((before - epoch).total_seconds(), 0.05)
        clock.wait(0.003)
        self.assertGreater(clock.now(), before)
        self.assertEqual(clock.mode, "synthetic_replay")
        with self.assertRaises(TypeError):
            SyntheticReplayClock(epoch=datetime.now(timezone.utc))

    def test_invalid_raw_monotonic_observation_never_becomes_replay_authority(self):
        clock = SyntheticReplayClock()
        with patch("proofkey.clock.time.monotonic", return_value=float("inf")):
            with self.assertRaises(ValueError):
                clock.now()
