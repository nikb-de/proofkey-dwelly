"""Evidence-only platform projection and model-job binding contracts."""
import copy
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
import importlib
import json
import os
import threading
import unittest
import uuid
from unittest.mock import patch

from tools.dwelly_analysis import widget
from tools.dwelly_service.cases import _snapshot
from tools.dwelly_service.tests.test_cases import declaration, event

try:
    models = importlib.import_module('tools.dwelly_platform.models')
except ModuleNotFoundError:
    models = None


class CaseHistory:
    def __init__(self, snapshot):
        self.snapshots = {snapshot['revision']: snapshot}
        self.links = {}
        self.fail_link = False

    def get(self, case_id, revision=None):
        snapshot = self.snapshots[max(self.snapshots) if revision is None else revision]
        if snapshot['case_id'] != case_id:
            raise ValueError('case_not_found')
        return copy.deepcopy(snapshot)

    def link_model(self, case_id, revision, snapshot_hash, job_id):
        if self.fail_link:
            self.fail_link = False
            raise ValueError('case_storage_error')
        assert self.get(case_id, revision)['snapshot_hash'] == snapshot_hash
        self.links[job_id] = (case_id, revision, snapshot_hash)

    def admit_model(self, case_id, revision, snapshot_hash, callback):
        current = self.get(case_id)
        if current['revision'] != revision:
            raise ValueError('revision_conflict')
        if current['snapshot_hash'] != snapshot_hash:
            raise ValueError('snapshot_hash_mismatch')
        return callback()


class RuntimeBoundary:
    """Controlled boundary; real durable worker admission is tested separately."""
    def __init__(self):
        self.jobs = {}
        self.store = self

    def get_by_key(self, key):
        job = self.jobs.get(key)
        return None if job is None else {'job_id': job['run_id'], 'spec': {
            'input': job['input'], 'reference': job['reference'], 'source': job['source'],
            'profile': {'id': job['model_profile_id']}}}

    def profiles(self):
        return {'enabled': True, 'profiles': [{'id': 'test', 'available': True}]}

    def submit(self, selector, key, selected):
        if key in self.jobs:
            old = self.jobs[key]
            if old['input'] != selected['input'] or old['model_profile_id'] != selector['model_profile_id']:
                raise ValueError('idempotency_conflict')
            return copy.deepcopy(old), False
        self.jobs[key] = {'schema_version': 'proofkey-model-job-v1', 'run_id': str(len(self.jobs)),
                          'status': 'queued', **copy.deepcopy(selected),
                          'model_profile_id': selector['model_profile_id'],
                          'case_id': selector['case_id'], 'step_index': selector['step_index']}
        assert selector['expected_input_hash'] == selected['input']['input_hash']
        return copy.deepcopy(self.jobs[key]), True

    def get(self, job_id):
        return copy.deepcopy(next(job for job in self.jobs.values() if job['run_id'] == job_id))


class ModelBridgeTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(models, 'platform model bridge must be implemented')
        self.snapshot = _snapshot(declaration(), [event()['event']])
        self.store = CaseHistory(self.snapshot)
        self.runtime = RuntimeBoundary()
        self.bridge = models.ModelBridge(self.store, self.runtime)
        self.body = {'expected_revision': 1, 'snapshot_hash': self.snapshot['snapshot_hash'],
                     'model_profile_id': 'test'}

    def test_projection_retains_evidence_ids_participants_and_discards_authority(self):
        source = copy.deepcopy(self.snapshot)
        source.update(authorization='SECRET_AUTHORITY', decisions=['SECRET_DECISION'],
                      reviews=['SECRET_REVIEW'], runtime_binding={'token': 'SECRET_BINDING'})
        projected = models.project_snapshot(source)
        widget.validate_input(projected)
        self.assertEqual(projected['case_id'], 'demo-1')
        self.assertEqual(projected['step_index'], 1)
        self.assertEqual(projected['cutoff_event_id'], 'event-1')
        self.assertEqual(projected['messages'][0]['event_id'], 'event-1')
        self.assertEqual(projected['messages'][0]['body'], 'Please move my delivery to tomorrow.')
        self.assertEqual([actor['id'] for actor in projected['actors']], declaration()['participants'])
        self.assertNotIn('SECRET', str(projected))
        self.assertEqual(projected, models.project_snapshot(source))

    def test_recipient_lists_preserve_one_event_including_empty_and_multi_recipient(self):
        for recipients in ([], ['operator-1', 'courier-1']):
            source = copy.deepcopy(self.snapshot)
            source['events'][0]['recipient_ids'] = recipients
            projected = models.project_snapshot(source)
            widget.validate_input(projected)
            self.assertEqual(len(projected['messages']), 1)
            self.assertEqual(projected['messages'][0]['event_id'], 'event-1')
            for recipient in recipients:
                self.assertIn(recipient, str(projected))

    def test_media_marks_content_unprocessed_and_preserves_only_available_caption(self):
        source = copy.deepcopy(self.snapshot)
        source['events'][0].update(kind='photo', text='Box at the door', media={
            'asset_id': 'asset-1', 'sha256': 'a' * 64, 'mime_type': 'image/png', 'size_bytes': 10})
        result = models.project_snapshot(source)
        widget.validate_input(result)
        body = result['messages'][0]['body']
        self.assertIn('content unprocessed', body)
        self.assertIn('Box at the door', body)
        self.assertIn('asset-1', body)

    def test_empty_case_has_valid_zero_step_input(self):
        projected = models.project_snapshot(_snapshot(declaration()))
        widget.validate_input(projected)
        self.assertEqual(projected['messages'], [])
        self.assertIsNone(projected['cutoff_event_id'])

    def test_submission_has_no_gold_reference_and_links_exact_snapshot(self):
        job = self.bridge.submit('demo-1', 'key', self.body)
        self.assertIsNone(job['reference'])
        self.assertEqual(job['source'], {'kind': 'platform_case', 'case_id': 'demo-1',
            'revision': 1, 'snapshot_hash': self.snapshot['snapshot_hash']})
        self.assertEqual(self.store.links[job['run_id']], ('demo-1', 1, self.snapshot['snapshot_hash']))
        self.assertEqual(self.bridge.get(job['run_id']), job)

    def test_submission_rejects_hash_mismatch_without_queuing_or_linking(self):
        with self.assertRaisesRegex(ValueError, '^snapshot_hash_mismatch$'):
            self.bridge.submit('demo-1', 'key', dict(self.body, snapshot_hash='0' * 64))
        self.assertEqual(self.runtime.jobs, {})
        self.assertEqual(self.store.links, {})

    def test_submission_rejects_invalid_selector_before_queuing(self):
        for change in ({'expected_revision': True}, {'model_profile_id': ''},
                       {'snapshot_hash': None}, {'extra': 'untrusted'}):
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, '^invalid_model_request$'):
                self.bridge.submit('demo-1', 'key', dict(self.body, **change))
        self.assertEqual(self.runtime.jobs, {})

    def test_replay_repairs_missing_link_after_append_without_duplicate_job(self):
        self.store.fail_link = True
        with self.assertRaisesRegex(ValueError, '^case_storage_error$'):
            self.bridge.submit('demo-1', 'key', self.body)
        self.store.snapshots[2] = _snapshot(declaration(), self.snapshot['events'] + [event('event-2', 1)['event']],
                                             self.snapshot['snapshot_hash'])
        replay = self.bridge.submit('demo-1', 'key', self.body)
        self.assertEqual(len(self.runtime.jobs), 1)
        self.assertEqual(self.store.links[replay['run_id']], ('demo-1', 1, self.snapshot['snapshot_hash']))

    def test_new_run_for_stale_revision_cannot_queue(self):
        self.store.snapshots[2] = _snapshot(declaration(), self.snapshot['events'] + [event('event-2', 1)['event']],
                                             self.snapshot['snapshot_hash'])
        with self.assertRaisesRegex(ValueError, '^revision_conflict$'):
            self.bridge.submit('demo-1', 'new-key', self.body)
        self.assertEqual(self.runtime.jobs, {})
        self.assertEqual(self.store.links, {})

    def test_get_rejects_jobs_from_other_source_or_changed_binding(self):
        job = self.bridge.submit('demo-1', 'key', self.body)
        for change in ({'kind': 'dataset'}, {'case_id': 'other'}, {'snapshot_hash': '0' * 64}):
            self.runtime.jobs['key']['source'] = dict(job['source'], **change)
            with self.subTest(change=change), self.assertRaisesRegex((ValueError, KeyError),
                                                                   'model_job_binding_mismatch|case_not_found'):
                self.bridge.get(job['run_id'])

    def test_absent_runtime_is_explicitly_disabled(self):
        disabled = models.ModelBridge(self.store)
        self.assertEqual(disabled.profiles(), {'enabled': False, 'profiles': []})
        with self.assertRaisesRegex(ValueError, '^model_execution_disabled$'):
            disabled.submit('demo-1', 'key', self.body)
        with self.assertRaisesRegex(ValueError, '^model_execution_disabled$'):
            disabled.get('anything')
        self.assertEqual(self.bridge.profiles(), self.runtime.profiles())


@unittest.skipUnless(os.environ.get('PROOFKEY_TEST_DATABASE_URL'), 'requires local PostgreSQL')
class ModelBridgeIntegrationTests(unittest.TestCase):
    def test_case_append_waits_until_model_admission_commits(self):
        from tools.dwelly_platform.store import PlatformStore, migrate
        from tools.dwelly_analysis import jobs, model, worker
        import psycopg
        from psycopg import sql
        dsn = os.environ['PROOFKEY_TEST_DATABASE_URL']
        schema = 'bridge_race_' + uuid.uuid4().hex
        def cleanup():
            with psycopg.connect(dsn, autocommit=True) as connection:
                connection.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))
        self.addCleanup(cleanup)
        migrate(dsn, schema=schema)
        jobs.migrate(dsn, schema=schema)
        store = PlatformStore(dsn, schema=schema, max_size=3)
        self.addCleanup(store.close)
        job_store = jobs.AnalysisJobStore(dsn, schema)
        self.addCleanup(job_store.close)
        store.create('create', declaration())
        snapshot, _ = store.append('demo-1', 'append', event())
        settings = model.load_profiles(model.__file__.replace('model.py', 'model-profiles.example.json'))
        settings['profiles'] = [settings['profiles'][0]]
        profile = settings['profiles'][0]
        runtime = worker.ModelRuntime(job_store, settings, 'race-fixture', allow_live=True)
        bridge = models.ModelBridge(store, runtime)
        body = {'expected_revision': 1, 'snapshot_hash': snapshot['snapshot_hash'],
                'model_profile_id': profile['id']}
        original = runtime.submit
        started = threading.Event()
        with ThreadPoolExecutor(max_workers=1) as pool:
            submitted = []
            def append():
                started.set()
                return store.append('demo-1', 'racing-append', event('event-2', 1))
            def admission(*args):
                future = pool.submit(append)
                submitted.append(future)
                self.assertTrue(started.wait(2))
                with self.assertRaises(FutureTimeout):
                    future.result(timeout=0.1)
                return original(*args)
            with patch.dict(os.environ, {profile['config']['api_key_env']: 'not-a-live-key'}), \
                    patch.object(runtime, 'submit', side_effect=admission):
                result = bridge.submit('demo-1', 'model-key', body)
            self.assertEqual(submitted[0].result(timeout=3)[0]['revision'], 2)
        self.assertEqual(result['step_index'], 1)
        with self.assertRaisesRegex(ValueError, '^revision_conflict$'):
            bridge.submit('demo-1', 'new-stale-key', body)
        self.assertIsNone(job_store.get_by_key('new-stale-key'))
        current = store.get('demo-1')
        with self.assertRaisesRegex(ValueError, '^unknown_model_profile$'):
            bridge.submit('demo-1', 'bad-profile', {'expected_revision': current['revision'],
                'snapshot_hash': current['snapshot_hash'], 'model_profile_id': 'unknown-profile'})

    def test_real_admission_history_replay_and_injected_transport(self):
        from tools.dwelly_platform.store import PlatformStore, migrate
        from tools.dwelly_analysis import jobs, model, worker
        import psycopg
        from psycopg import sql
        dsn = os.environ['PROOFKEY_TEST_DATABASE_URL']
        schema = 'bridge_test_' + uuid.uuid4().hex
        def cleanup():
            with psycopg.connect(dsn, autocommit=True) as connection:
                connection.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))
        self.addCleanup(cleanup)
        migrate(dsn, schema=schema)
        jobs.migrate(dsn, schema=schema)
        store = PlatformStore(dsn, schema=schema, max_size=2)
        self.addCleanup(store.close)
        job_store = jobs.AnalysisJobStore(dsn, schema)
        self.addCleanup(job_store.close)
        store.create('create', declaration())
        snapshot, _ = store.append('demo-1', 'append', event())
        settings = model.load_profiles(model.__file__.replace('model.py', 'model-profiles.example.json'))
        settings['profiles'] = [settings['profiles'][0]]
        profile = settings['profiles'][0]
        runtime = worker.ModelRuntime(job_store, settings, 'bridge-fixture', allow_live=True)
        bridge = models.ModelBridge(store, runtime)
        body = {'expected_revision': 1, 'snapshot_hash': snapshot['snapshot_hash'],
                'model_profile_id': profile['id']}
        response = {'text': json.dumps({'state': 'unknown', 'waiting_for': [],
            'next_action': {'type': 'operator_review', 'target_actor_id': None, 'description': 'Review evidence.'},
            'evidence_event_ids': ['event-1'], 'uncertainty': ['Identity is unverified.']}),
            'provider': profile['config']['provider'], 'requested_model': profile['config']['model'],
            'observed_model': 'injected-test-model', 'request_id': 'injected-request', 'latency_ms': 1,
            'usage': {'input_tokens': 100, 'output_tokens': 50}}
        with patch.dict(os.environ, {profile['config']['api_key_env']: 'not-a-live-key'}):
            first = bridge.submit('demo-1', 'model-key', body)
            store.append('demo-1', 'append-2', event('event-2', 1))
            self.assertEqual(bridge.submit('demo-1', 'model-key', body)['run_id'], first['run_id'])
            with patch.object(model, 'request', return_value=response) as transport:
                self.assertTrue(runtime.work_once())
                self.assertFalse(runtime.work_once())
            transport.assert_called_once()
        done = bridge.get(first['run_id'])
        self.assertEqual(done['status'], 'succeeded')
        self.assertIsNone(done['reference'])
        self.assertIsNone(done['evaluation'])
        self.assertEqual(done['transaction']['dispatch_attempts'], 1)
        self.assertEqual(done['transaction']['operational_effects'], 0)
        self.assertEqual(store.detail('demo-1')['model_jobs'], [{'job_id': first['run_id'],
            'revision': 1, 'snapshot_hash': snapshot['snapshot_hash']}])
