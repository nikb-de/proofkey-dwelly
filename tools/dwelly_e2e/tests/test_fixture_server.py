"""Controls for the explicitly simulated transport, not model accuracy evidence."""
import json
import unittest

from tools.dwelly_platform.models import project_snapshot
from tools.dwelly_service.cases import _snapshot
from tools.dwelly_service.tests.test_cases import declaration, event
from tools.dwelly_e2e.tests.fixture_server import SimulatedTransport


class SimulatedTransportTests(unittest.TestCase):
    def setUp(self):
        self.plan = {'case_id': 'demo-1', 'declaration': declaration(),
                     'events': [event()['event']],
                     'source': {'source_id': 'control', 'step_index': 1}}
        self.payload = {'state': 'unknown', 'waiting_for': [],
                        'next_action': {'type': 'operator_review', 'target_actor_id': None,
                                        'description': 'Review the source.'},
                        'evidence_event_ids': ['event-1'], 'uncertainty': ['Test fixture.']}
        self.input = project_snapshot(_snapshot(self.plan['declaration'], self.plan['events']))
        self.profile = {'config': {'provider': 'openai', 'model': 'SIMULATED-case-fixture'}}

    def transport(self, **kwargs):
        return SimulatedTransport([self.plan], {'control:1': self.payload}, delay_seconds=0, **kwargs)

    def test_exact_input_and_explicit_simulated_receipt(self):
        transport = self.transport()
        result = transport(self.input, self.profile, max_output_tokens=512, timeout=5)
        self.assertEqual(json.loads(result['text']), self.payload)
        self.assertTrue(result['observed_model'].startswith('SIMULATED'))
        self.assertTrue(result['request_id'].startswith('SIMULATED'))
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(transport.calls[0]['live_provider_calls'], 0)

    def test_wrong_input_never_returns_expected_answer(self):
        transport = self.transport()
        changed = dict(self.input, input_hash='0' * 64)
        with self.assertRaisesRegex(ValueError, '^fixture_input_mismatch$'):
            transport(changed, self.profile)
        self.assertEqual(transport.calls, [])

    def test_unknown_outcome_is_recorded_once_without_response(self):
        transport = self.transport(faults={'demo-1': 'timeout'})
        with self.assertRaisesRegex(ValueError, '^timeout$'):
            transport(self.input, self.profile)
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(transport.calls[0]['fault'], 'timeout')

    def test_live_profile_refused(self):
        transport = self.transport()
        with self.assertRaisesRegex(ValueError, '^fixture_profile_mismatch$'):
            transport(self.input, {'config': {'provider': 'openai', 'model': 'gpt-4.1-mini'}})
        self.assertEqual(transport.calls, [])
