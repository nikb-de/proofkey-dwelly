"""Real-clock, trusted-library acceptance for same-owner observed stop."""
from pathlib import Path
from tempfile import TemporaryDirectory
import runpy
import unittest


BASE_KEYS = {
    'scope', 'factory_id', 'artifact_hash', 'run_status', 'stop_requested',
    'original_generation', 'original_request_preserved', 'claim_preserved',
    'route_preserved', 'deadline_not_extended', 'tool_calls_before',
    'tool_calls_after', 'business_effects_before', 'business_effects_after',
    'owner_closed',
}
WAIT_KEYS = {
    'wait_observed', 'wait_stopped', 'wait_context_preserved',
    'wait_expiry_preserved',
}


class ObservedStopV2AcceptanceTests(unittest.TestCase):
    def test_real_clock_trusted_library_same_owner_acceptance(self):
        with TemporaryDirectory() as folder:
            parent = Path(folder).resolve()
            parent.chmod(0o700)
            demo = runpy.run_path(str(Path(__file__).resolve().parents[1] /
                'examples/observed_stop_v2.py'))['run_demo']
            receipt = demo(parent)
            self.assertEqual(set(receipt), BASE_KEYS)
            self.assertEqual(receipt['scope'], 'trusted-library-same-owner-no-restart')
            self.assertEqual(receipt['factory_id'], 'fixed-synthetic-observed-stop-v2')
            self.assertEqual(receipt['run_status'], 'authorized')
            self.assertEqual(receipt['original_generation'], 'G1')
            self.assertRegex(receipt['artifact_hash'], r'\A[0-9a-f]{64}\Z')
            for key in ('stop_requested', 'original_request_preserved', 'claim_preserved',
                        'route_preserved', 'deadline_not_extended', 'owner_closed'):
                self.assertIs(receipt[key], True, key)
            self.assertEqual(receipt['business_effects_before'], 1)
            self.assertEqual(receipt['business_effects_before'], receipt['business_effects_after'])
            self.assertGreater(receipt['tool_calls_after'], receipt['tool_calls_before'])

    def test_real_clock_pending_wait_is_stopped_without_changing_context(self):
        with TemporaryDirectory() as folder:
            parent = Path(folder).resolve()
            parent.chmod(0o700)
            demo = runpy.run_path(str(Path(__file__).resolve().parents[1] /
                'examples/observed_stop_v2.py'))['run_pending_demo']
            receipt = demo(parent)
            self.assertEqual(set(receipt), BASE_KEYS | WAIT_KEYS)
            self.assertEqual(receipt['scope'], 'trusted-library-same-owner-no-restart')
            self.assertEqual(receipt['factory_id'], 'fixed-synthetic-observed-stop-v2')
            self.assertEqual(receipt['run_status'], 'authorized')
            self.assertEqual(receipt['original_generation'], 'G1')
            self.assertRegex(receipt['artifact_hash'], r'\A[0-9a-f]{64}\Z')
            for key in ('stop_requested', 'original_request_preserved', 'claim_preserved',
                        'route_preserved', 'deadline_not_extended', 'owner_closed',
                        'wait_observed', 'wait_stopped', 'wait_context_preserved',
                        'wait_expiry_preserved'):
                self.assertIs(receipt[key], True, key)
            self.assertEqual(receipt['business_effects_before'], 0)
            self.assertEqual(receipt['business_effects_after'], 0)
            self.assertGreater(receipt['tool_calls_after'], receipt['tool_calls_before'])


if __name__ == '__main__':
    unittest.main()
