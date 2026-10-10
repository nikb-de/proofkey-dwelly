"""Real database restart/lease controls with no external provider calls.

These tests inject a transport and expire a lease; they do not claim a literal
machine crash or evidence about a live provider's billing/delivery guarantees.
"""
import json
import os
from pathlib import Path
import unittest
import uuid
from unittest.mock import patch

import psycopg
from psycopg import sql

from tools.dwelly_analysis import jobs, model
from tools.dwelly_analysis.worker import ModelRuntime
from tools.dwelly_platform.models import ModelBridge
from tools.dwelly_platform.store import PlatformStore, migrate
from tools.dwelly_e2e.tests.fixture_server import SimulatedTransport


@unittest.skipUnless(os.environ.get('PROOFKEY_TEST_DATABASE_URL'), 'requires isolated local PostgreSQL')
class RecoveryE2ETests(unittest.TestCase):
    def setUp(self):
        from tools.dwelly_e2e.cases import build_case
        self.dsn = os.environ['PROOFKEY_TEST_DATABASE_URL']
        self.schema = 'e2e_recovery_' + uuid.uuid4().hex
        self.plan = build_case('case-002', 3, 'recovery')
        self.settings = {'profiles': [{'id': 'simulated-recovery', 'label': 'SIMULATED recovery',
            'config': {'provider': 'openai', 'model': 'SIMULATED-recovery',
                       'api_key_env': 'PROOFKEY_SIMULATED_RECOVERY_KEY',
                       'input_usd_per_million': '0.01', 'output_usd_per_million': '0.01'}}],
            'budget_per_model_usd': 25, 'max_output_tokens': 1024, 'timeout_seconds': 5}
        self.environment = patch.dict(os.environ, {'PROOFKEY_SIMULATED_RECOVERY_KEY': 'fixture-only'})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.addCleanup(self.cleanup_schema)
        migrate(self.dsn, schema=self.schema)
        jobs.migrate(self.dsn, self.schema)
        self.cases = PlatformStore(self.dsn, schema=self.schema)
        self.addCleanup(self.cases.close)
        self.store = jobs.AnalysisJobStore(self.dsn, self.schema)
        self.addCleanup(self.store.close)
        self.runtime = ModelRuntime(self.store, self.settings, 'recovery-probe', allow_live=True)
        self.bridge = ModelBridge(self.cases, self.runtime)
        self.cases.create('create', self.plan['declaration'])
        for revision, event in enumerate(self.plan['events']):
            self.cases.append(self.plan['case_id'], 'event-' + str(revision),
                              {'expected_revision': revision, 'event': event})
        snapshot = self.cases.get(self.plan['case_id'])
        self.body = {'expected_revision': snapshot['revision'], 'snapshot_hash': snapshot['snapshot_hash'],
                     'model_profile_id': 'simulated-recovery'}
        self.job = self.bridge.submit(self.plan['case_id'], 'one-logical-request', self.body)
        fixtures = json.loads(Path(__file__).with_name('fixtures').joinpath('good-candidates.json').read_text())
        self.transport = SimulatedTransport([self.plan], fixtures['candidates'], delay_seconds=0)

    def cleanup_schema(self):
        with psycopg.connect(self.dsn, autocommit=True) as connection:
            connection.execute(sql.SQL('DROP SCHEMA IF EXISTS {} CASCADE').format(sql.Identifier(self.schema)))
            self.assertFalse(connection.execute(
                'SELECT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name=%s)',
                (self.schema,)).fetchone()[0])

    def expire(self, job_id):
        with psycopg.connect(self.dsn, autocommit=True) as connection:
            connection.execute(sql.SQL("UPDATE {}.model_jobs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE job_id=%s")
                               .format(sql.Identifier(self.schema)), (job_id,))

    def restart(self):
        replacement = jobs.AnalysisJobStore(self.dsn, self.schema)
        self.addCleanup(replacement.close)
        return ModelRuntime(replacement, self.settings, 'recovery-probe', allow_live=True)

    def verify_no_business_effects(self):
        detail = self.cases.detail(self.plan['case_id'])
        self.assertEqual(detail['actions'], [])
        self.assertEqual(detail['decisions'], [])
        self.assertEqual(detail['external_effects'], 0)

    def test_queued_job_is_executed_once_after_runtime_reconstruction(self):
        runtime = self.restart()
        with patch.object(model, 'request', self.transport):
            self.assertTrue(runtime.work_once())
            self.assertFalse(runtime.work_once())
        after = runtime.get(self.job['run_id'])
        self.assertEqual(after['status'], 'succeeded')
        self.assertEqual(after['transaction']['dispatch_attempts'], 1)
        self.assertEqual(len(self.transport.calls), 1)
        replay = ModelBridge(self.cases, runtime).submit(self.plan['case_id'], 'one-logical-request', self.body)
        self.assertEqual(replay['run_id'], self.job['run_id'])
        self.verify_no_business_effects()

    def test_saved_response_is_parsed_after_lease_expiry_without_redispatch(self):
        row = self.store.claim_next()
        self.assertTrue(self.store.mark_dispatched(row['job_id'], row['lease_token']))
        response = self.transport(row['spec']['input'], row['spec']['profile'])
        self.assertTrue(self.store.record_response(row['job_id'], row['lease_token'], response))
        self.expire(row['job_id'])
        runtime = self.restart()
        with patch.object(model, 'request', side_effect=AssertionError('must not redispatch')) as request:
            self.assertTrue(runtime.work_once())
            self.assertFalse(runtime.work_once())
        request.assert_not_called()
        after = runtime.get(self.job['run_id'])
        self.assertEqual(after['status'], 'succeeded')
        self.assertEqual(after['transaction']['dispatch_attempts'], 1)
        self.assertEqual(len(self.transport.calls), 1)
        self.verify_no_business_effects()

    def test_dispatched_job_without_saved_response_becomes_unknown_and_is_not_retried(self):
        row = self.store.claim_next()
        self.assertTrue(self.store.mark_dispatched(row['job_id'], row['lease_token']))
        self.expire(row['job_id'])
        runtime = self.restart()
        with patch.object(model, 'request', side_effect=AssertionError('must not redispatch')) as request:
            self.assertFalse(runtime.work_once())
            self.assertFalse(runtime.work_once())
        request.assert_not_called()
        after = runtime.get(self.job['run_id'])
        self.assertEqual(after['status'], 'outcome_unknown')
        self.assertEqual(after['error']['code'], 'provider_outcome_unknown')
        self.assertEqual(after['transaction']['dispatch_attempts'], 1)
        self.assertEqual(after['transaction']['automatic_retries'], 0)
        self.assertEqual(ModelBridge(self.cases, runtime).submit(
            self.plan['case_id'], 'one-logical-request', self.body)['run_id'], self.job['run_id'])
        self.verify_no_business_effects()
