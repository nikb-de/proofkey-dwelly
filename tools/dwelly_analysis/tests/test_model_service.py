"""Real PostgreSQL + loopback integration; provider transport is mocked."""
import copy
from http.client import HTTPConnection
import json
import os
import tempfile
import threading
import unittest
import uuid
from unittest.mock import patch

from tools.dwelly_analysis import server, model

DSN = os.environ.get('PROOFKEY_TEST_DATABASE_URL')


@unittest.skipUnless(DSN, 'set PROOFKEY_TEST_DATABASE_URL for real PostgreSQL tests')
class ModelServiceTests(unittest.TestCase):
    def setUp(self):
        from tools.dwelly_analysis import jobs, worker
        self.jobs, self.worker = jobs, worker
        self.schema = 'test_service_' + uuid.uuid4().hex
        jobs.migrate(DSN, self.schema)
        self.store = jobs.AnalysisJobStore(DSN, self.schema)
        self.addCleanup(self.cleanup)
        self.settings = model.load_profiles(model.__file__.replace('model.py', 'model-profiles.example.json'))
        self.settings['profiles'] = [self.settings['profiles'][0]]
        self.profile = self.settings['profiles'][0]
        self.env = patch.dict(os.environ, {self.profile['config']['api_key_env']: 'not-a-live-key'})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.runtime = worker.ModelRuntime(self.store, self.settings, 'test-run', allow_live=True)
        self.selected = server.step_record('case-002', 3)
        self.selector = {'case_id': 'case-002', 'step_index': 3, 'mode': 'model',
                         'expected_input_hash': self.selected['input']['input_hash'],
                         'model_profile_id': self.profile['id']}

    def cleanup(self):
        self.store.close()
        import psycopg
        from psycopg import sql
        with psycopg.connect(DSN) as conn:
            conn.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(self.schema)))

    def response(self):
        value = {'state': 'unknown', 'waiting_for': [], 'next_action': {'type': 'operator_review',
                 'target_actor_id': None, 'description': 'Review the evidence.'},
                 'evidence_event_ids': [], 'uncertainty': ['No validated authority.']}
        return {'text': json.dumps(value), 'provider': 'openai', 'requested_model': self.profile['config']['model'],
                'observed_model': 'observed-fixture', 'request_id': 'fixture-request', 'latency_ms': 1,
                'usage': {'input_tokens': 100, 'output_tokens': 50}}

    def submit(self, key='test-key'):
        return self.runtime.submit(self.selector, key, self.selected)

    def test_end_to_end_dedup_and_receipt_without_reference_in_request(self):
        first, created = self.submit()
        replay, again = self.submit()
        self.assertTrue(created)
        self.assertFalse(again)
        self.assertEqual(first['run_id'], replay['run_id'])
        with patch.object(model, 'request', return_value=self.response()) as request:
            self.assertTrue(self.runtime.work_once())
            self.assertFalse(self.runtime.work_once())
        request.assert_called_once()
        self.assertEqual(request.call_args.args[0], self.selected['input'])
        self.assertNotIn('reference', request.call_args.args[0])
        done = self.runtime.get(first['run_id'])
        self.assertEqual(done['status'], 'succeeded')
        self.assertEqual(done['receipt']['observed_model'], 'observed-fixture')
        self.assertEqual(done['transaction']['dispatch_attempts'], 1)
        self.assertEqual(done['transaction']['operational_effects'], 0)
        self.assertNotIn('lease_token', json.dumps(done))
        self.assertNotIn('not-a-live-key', json.dumps(done))

    def test_invalid_content_keeps_receipt_without_candidate(self):
        first, _ = self.submit()
        with patch.object(model, 'request', return_value=dict(self.response(), text='not json')):
            self.runtime.work_once()
        done = self.runtime.get(first['run_id'])
        self.assertEqual(done['status'], 'failed')
        self.assertIsNone(done['candidate'])
        self.assertEqual(done['receipt']['request_id'], 'fixture-request')
        self.assertEqual(done['error']['phase'], 'validation')

    def test_timeout_never_resends_and_retains_reservation(self):
        first, _ = self.submit()
        with patch.object(model, 'request', side_effect=ValueError('timeout')) as request:
            self.runtime.work_once()
            self.runtime.work_once()
        request.assert_called_once()
        done = self.runtime.get(first['run_id'])
        self.assertEqual(done['status'], 'outcome_unknown')
        self.assertGreater(done['transaction']['reserved_usd'], 0)

    def test_lost_ack_replays_after_credentials_are_removed(self):
        first, _ = self.submit()
        with patch.dict(os.environ, {self.profile['config']['api_key_env']: ''}):
            replay, created = self.submit()
            self.assertFalse(created)
            self.assertEqual(first['run_id'], replay['run_id'])
            with self.assertRaisesRegex(ValueError, '^model_credentials_unavailable$'):
                self.submit('new-key')

    def test_shutdown_between_claim_and_dispatch_does_not_call_provider(self):
        first, _ = self.submit()
        original = self.store.mark_dispatched
        def stop_during_mark(*args):
            result = original(*args)
            self.runtime.close()
            return result
        with patch.object(self.store, 'mark_dispatched', side_effect=stop_during_mark), patch.object(model, 'request') as request:
            self.runtime.work_once()
        request.assert_not_called()
        self.assertEqual(self.runtime.get(first['run_id'])['status'], 'failed')

    def test_durable_response_recovery_skips_transport(self):
        first, _ = self.submit()
        row = self.store.claim_next()
        self.store.mark_dispatched(row['job_id'], row['lease_token'])
        self.store.record_response(row['job_id'], row['lease_token'], self.response())
        import psycopg
        from psycopg import sql
        with psycopg.connect(DSN) as conn:
            conn.execute(sql.SQL('UPDATE {}.model_jobs SET lease_expires_at=clock_timestamp()-interval \'1 second\'').format(sql.Identifier(self.schema)))
        with patch.object(model, 'request', side_effect=AssertionError('must not redispatch')):
            self.runtime.work_once()
        self.assertEqual(self.runtime.get(first['run_id'])['status'], 'succeeded')

    def test_disabled_and_untrusted_profiles_cannot_queue(self):
        disabled = self.worker.ModelRuntime(self.store, self.settings, 'test-run', allow_live=False)
        with self.assertRaisesRegex(ValueError, '^model_execution_disabled$'):
            disabled.submit(self.selector, 'disabled', self.selected)
        with self.assertRaisesRegex(ValueError, '^unknown_model_profile$'):
            self.runtime.submit(dict(self.selector, model_profile_id='injected'), 'bad', self.selected)
        with self.assertRaisesRegex(ValueError, '^input_hash_conflict$'):
            self.runtime.submit(dict(self.selector, expected_input_hash='0'*64), 'bad', self.selected)

    def test_loopback_routes_and_idempotency_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            app = server.create_server(port=0, runs_dir=temp, model_runtime=self.runtime, start_workers=False)
            thread = threading.Thread(target=app.serve_forever, daemon=True)
            thread.start()
            try:
                def http(method, path, body=None, extra=None):
                    conn = HTTPConnection('127.0.0.1', app.server_address[1], timeout=3)
                    headers = {'Content-Type': 'application/json', 'X-ProofKey-Request': 'analysis-v1'}
                    headers.update(extra or {})
                    conn.request(method, path, json.dumps(body) if body is not None else None, headers)
                    response = conn.getresponse()
                    status, result = response.status, json.loads(response.read())
                    conn.close()
                    return status, result
                status, profiles = http('GET', '/api/model-profiles')
                self.assertEqual(status, 200)
                self.assertTrue(profiles['enabled'])
                self.assertNotIn('api_key_env', json.dumps(profiles))
                self.assertEqual(http('POST', '/api/model-runs', self.selector)[0], 400)
                status, first = http('POST', '/api/model-runs', self.selector, {'Idempotency-Key':'same'})
                self.assertEqual(status, 202)
                self.assertEqual(http('POST', '/api/model-runs', self.selector, {'Idempotency-Key':'same'})[0], 200)
                self.assertEqual(http('POST', '/api/model-runs', dict(self.selector, expected_input_hash='0'*64), {'Idempotency-Key':'other'})[0], 409)
                self.assertEqual(http('GET', '/api/model-runs/' + first['run_id'])[1]['status'], 'queued')
            finally:
                app.shutdown()
                app.server_close()
                thread.join()


class DisabledRoutesTests(unittest.TestCase):
    def test_private_env_is_data_not_shell_and_existing_values_win(self):
        from tools.dwelly_analysis.__main__ import load_provider_env
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '.env'
            path.write_text('OPENAI_API_KEY="test-value"\nGEMINI_API_KEY=another-value\nUNRELATED=x\n')
            with patch.dict(os.environ, {'OPENAI_API_KEY': 'already-present'}, clear=True):
                load_provider_env(path)
                self.assertEqual(os.environ['OPENAI_API_KEY'], 'already-present')
                self.assertEqual(os.environ['GEMINI_API_KEY'], 'another-value')
                self.assertNotIn('UNRELATED', os.environ)
            path.write_text('OPENAI_API_KEY=$(echo unexpected)\n')
            with self.assertRaisesRegex(ValueError, '^invalid_provider_env$'):
                load_provider_env(path)

    def test_profiles_available_without_database_dependency(self):
        with tempfile.TemporaryDirectory() as temp:
            app = server.create_server(port=0, runs_dir=temp)
            thread = threading.Thread(target=app.serve_forever, daemon=True)
            thread.start()
            try:
                conn = HTTPConnection('127.0.0.1', app.server_address[1], timeout=3)
                conn.request('GET', '/api/model-profiles')
                response = conn.getresponse()
                self.assertEqual(response.status, 200)
                self.assertEqual(json.loads(response.read()), {'enabled': False, 'profiles': []})
                conn.close()
            finally:
                app.shutdown()
                app.server_close()
                thread.join()
