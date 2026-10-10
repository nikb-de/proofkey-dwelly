"""Local media validation, durable admission and offline provider contracts."""
from concurrent.futures import ThreadPoolExecutor
import copy
import importlib
import io
import json
import os
import threading
import unittest
import uuid
import wave
from unittest.mock import patch

from PIL import Image

from tools.dwelly_platform.store import PlatformStore, migrate
from tools.dwelly_service.tests.test_cases import declaration

try:
    media = importlib.import_module('tools.dwelly_platform.media')
except ModuleNotFoundError:
    media = None


def image_bytes():
    stream = io.BytesIO()
    Image.new('RGB', (16, 16), 'white').save(stream, format='PNG')
    return stream.getvalue()


def audio_bytes():
    stream = io.BytesIO()
    with wave.open(stream, 'wb') as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(8000)
        output.writeframes(b'\0\0' * 800)
    return stream.getvalue()


class OfflineProvider:
    name = 'openai'

    def __init__(self):
        self.calls = []
        self.error = None
        self.enabled = True
        self.result = {'text': 'The parcel is beside a door.', 'provider': 'openai',
            'requested_model': 'fixture-vision', 'observed_model': 'observed-fixture',
            'request_id': 'fixture-request', 'usage': {'input_tokens': 100, 'output_tokens': 12},
            'latency_ms': 1}

    def model_id(self, mode):
        return 'fixture-vision' if mode == 'image_analysis' else 'fixture-asr'

    def availability(self, mode):
        return None if self.enabled else 'missing_api_key'

    def process(self, mode, data, mime_type):
        self.calls.append((mode, data, mime_type))
        if self.error:
            raise self.error
        result = copy.deepcopy(self.result)
        result['requested_model'] = self.model_id(mode)
        return result


@unittest.skipUnless(os.environ.get('PROOFKEY_TEST_DATABASE_URL'), 'requires local PostgreSQL')
class MediaServiceTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(media, 'media processing service must be implemented')
        self.dsn = os.environ['PROOFKEY_TEST_DATABASE_URL']
        self.schema = 'media_test_' + uuid.uuid4().hex
        self.addCleanup(self.cleanup)
        migrate(self.dsn, schema=self.schema)
        self.store = PlatformStore(self.dsn, schema=self.schema, max_size=4)
        self.addCleanup(self.store.close)
        self.store.create('case', declaration())
        media.migrate_media(self.store)
        self.provider = OfflineProvider()
        self.service = media.MediaService(self.store, self.provider)
        self.asset = self.store.put_asset('demo-1', 'image', 'image/png', 'parcel.png', image_bytes())

    def cleanup(self):
        import psycopg
        from psycopg import sql
        with psycopg.connect(self.dsn, autocommit=True) as connection:
            connection.execute(sql.SQL('DROP SCHEMA IF EXISTS {} CASCADE').format(sql.Identifier(self.schema)))
            if hasattr(self, 'shared_schema'):
                connection.execute(sql.SQL('DROP SCHEMA IF EXISTS {} CASCADE').format(sql.Identifier(self.shared_schema)))

    def process(self, key='run', asset=None, mode='image_analysis'):
        return self.service.process('demo-1', (asset or self.asset)['asset_id'], key, {'mode': mode})

    def test_storing_does_not_process_and_migration_is_idempotent(self):
        media.migrate_media(self.store)
        self.assertEqual(self.service.list('demo-1'), [])
        self.assertEqual(self.provider.calls, [])

    def test_unconfigured_controls_disabled_and_image_generation_is_evals_only(self):
        disabled = media.MediaService(self.store)
        capability = disabled.capabilities()
        for mode in ('image_analysis', 'asr'):
            self.assertFalse(capability[mode]['enabled'])
            self.assertEqual(capability[mode]['status'], 'not_configured')
        self.assertEqual(capability['image_generation'], {'enabled': False, 'status': 'evals_only'})
        with self.assertRaisesRegex(ValueError, '^media_processing_disabled$'):
            disabled.process('demo-1', self.asset['asset_id'], 'none', {'mode': 'image_analysis'})
        self.assertEqual(disabled.list('demo-1'), [])

    def test_valid_image_result_is_anchored_reviewable_and_allowlisted(self):
        self.provider.result['raw_response'] = {'secret': 'must-not-persist'}
        result = self.process()
        self.assertEqual(result['status'], 'succeeded')
        self.assertEqual(result['text'], 'The parcel is beside a door.')
        self.assertEqual(result['output']['text'], result['text'])
        self.assertEqual(result['asset_sha256'], self.asset['sha256'])
        self.assertEqual(result['human_review'], 'required')
        self.assertEqual(result['external_effects'], 0)
        self.assertEqual(result['receipt']['observed_model'], 'observed-fixture')
        self.assertNotIn('must-not-persist', json.dumps(result))
        self.assertEqual(self.service.list('demo-1'), [result])
        self.assertEqual(self.store.get('demo-1')['events'], [])
        self.assertEqual(result['validation']['width'], 16)

    def test_audio_validated_and_processed_as_asr(self):
        audio = self.store.put_asset('demo-1', 'audio', 'audio/wav', 'note.wav', audio_bytes())
        result = self.process(asset=audio, mode='asr')
        self.assertEqual(result['status'], 'succeeded')
        self.assertEqual(self.provider.calls[0][0], 'asr')
        self.assertAlmostEqual(result['validation']['duration_seconds'], 0.1, places=2)

    def test_truncated_signature_valid_image_rejected_before_dispatch(self):
        invalid = self.store.put_asset('demo-1', 'bad', 'image/png', 'bad.png', b'\x89PNG\r\n\x1a\ninvalid')
        with self.assertRaisesRegex(ValueError, '^invalid_media$'):
            self.process(asset=invalid)
        self.assertEqual(self.provider.calls, [])
        self.assertEqual(self.service.list('demo-1'), [])

    def test_wrong_modality_rejected_before_dispatch(self):
        with self.assertRaisesRegex(ValueError, '^media_mode_mismatch$'):
            self.process(mode='asr')
        self.assertEqual(self.provider.calls, [])

    def test_cross_case_asset_cannot_process(self):
        self.store.create('other', declaration('other'))
        with self.assertRaisesRegex(ValueError, '^asset_not_found$'):
            self.service.process('other', self.asset['asset_id'], 'run', {'mode': 'image_analysis'})
        self.assertEqual(self.provider.calls, [])

    def test_replay_after_disabled_credentials_returns_original_without_redispatch(self):
        first = self.process()
        self.provider.enabled = False
        second = self.process()
        self.assertEqual(first, second)
        self.assertEqual(len(self.provider.calls), 1)

    def test_body_bound_idempotency_rejects_other_asset(self):
        self.process()
        second = self.store.put_asset('demo-1', 'image2', 'image/png', 'second.png', image_bytes())
        with self.assertRaisesRegex(ValueError, '^idempotency_conflict$'):
            self.process(asset=second)
        self.assertEqual(len(self.provider.calls), 1)

    def test_full_reservation_blocks_another_call_even_after_success(self):
        self.process()
        with self.assertRaisesRegex(ValueError, '^media_budget_exhausted$'):
            self.process('another-key')
        self.assertEqual(len(self.provider.calls), 1)

    def test_timeout_is_unknown_keeps_reservation_and_never_retries(self):
        self.provider.error = TimeoutError('sensitive detail')
        result = self.process()
        self.assertEqual(result['status'], 'outcome_unknown')
        self.assertEqual(result['error'], 'media_timeout')
        self.assertNotIn('sensitive', json.dumps(result))
        self.assertEqual(self.process(), result)
        with self.assertRaisesRegex(ValueError, '^media_budget_exhausted$'):
            self.process('another-key')
        self.assertEqual(len(self.provider.calls), 1)

    def test_invalid_provider_output_is_failed_without_saved_raw_result(self):
        self.provider.result['text'] = ' ' * 2
        result = self.process()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['error'], 'invalid_media_result')
        self.assertIsNone(result['text'])
        self.assertEqual(self.process(), result)

    def test_non_utf8_provider_text_is_failed_without_persisting_it(self):
        self.provider.result['text'] = '\ud800'
        result = self.process()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['error'], 'invalid_media_result')
        self.assertIsNone(result['text'])

    def test_oversized_provider_output_is_failed_without_persisting_it(self):
        self.provider.result['text'] = 'x' * 16385
        result = self.process()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['error'], 'invalid_media_result')

    def test_invalid_receipt_fields_are_discarded_before_storage(self):
        self.provider.result.update(observed_model='\ud800', request_id='\x00bad',
                                    latency_ms=10**1000, usage={'input_tokens': 10**1000})
        result = self.process()
        self.assertEqual(result['status'], 'succeeded')
        self.assertIsNone(result['receipt']['observed_model'])
        self.assertIsNone(result['receipt']['request_id'])
        self.assertIsNone(result['receipt']['usage'])
        self.assertIsNone(result['receipt']['latency_ms'])

    def test_asset_hash_is_revalidated_before_processing(self):
        original = self.store.get_asset
        def mismatched(*args):
            asset, data = original(*args)
            return dict(asset, sha256='0' * 64), data
        with patch.object(self.store, 'get_asset', side_effect=mismatched):
            with self.assertRaisesRegex(ValueError, '^asset_mismatch$'):
                self.process()
        self.assertEqual(self.provider.calls, [])

    def test_image_pixel_limit_rejected_before_processing(self):
        stream = io.BytesIO()
        Image.new('RGB', (4001, 4000)).save(stream, format='PNG')
        asset = self.store.put_asset('demo-1', 'oversized', 'image/png', 'large.png', stream.getvalue())
        with self.assertRaisesRegex(ValueError, '^media_dimensions_exceeded$'):
            self.process(asset=asset)
        self.assertEqual(self.provider.calls, [])

    def test_audio_duration_limit_rejected_before_processing(self):
        audio = self.store.put_asset('demo-1', 'audio', 'audio/wav', 'note.wav', audio_bytes())
        probe = {'streams': [{'codec_type': 'audio', 'codec_name': 'pcm_s16le', 'channels': 1}],
                 'format': {'duration': '600.1'}}
        completed = type('Result', (), {'returncode': 0, 'stdout': json.dumps(probe).encode()})()
        with patch.object(media.subprocess, 'run', return_value=completed):
            with self.assertRaisesRegex(ValueError, '^media_duration_exceeded$'):
                self.process(asset=audio, mode='asr')
        self.assertEqual(self.provider.calls, [])

    def test_concurrent_replay_observes_running_row_without_second_call(self):
        entered, release = threading.Event(), threading.Event()
        original = self.provider.process
        def blocked(*args):
            entered.set()
            release.wait(5)
            return original(*args)
        self.provider.process = blocked
        with ThreadPoolExecutor(max_workers=2) as pool:
            future = pool.submit(self.process)
            self.assertTrue(entered.wait(3))
            try:
                running = self.process()
                self.assertEqual(running['status'], 'running')
                self.assertEqual(len(self.service.list('demo-1')), 1)
            finally:
                release.set()
            result = future.result(timeout=5)
        self.assertEqual(result['run_id'], running['run_id'])
        self.assertEqual(len(self.provider.calls), 1)

    def test_expired_dispatch_is_unknown_and_late_success_cannot_overwrite_it(self):
        original = self.provider.process
        observed = []
        def delayed(*args):
            with self.store._transaction(write=True) as connection:
                connection.execute("""UPDATE platform_media_runs SET record=jsonb_set(record::jsonb,
                    '{created_at}',to_jsonb((clock_timestamp()-interval '301 seconds')::text))::text
                    WHERE status='running'""")
            observed.extend(self.service.list('demo-1'))
            return original(*args)
        self.provider.process = delayed
        result = self.process()
        self.assertEqual(observed[0]['status'], 'outcome_unknown')
        self.assertEqual(result['status'], 'outcome_unknown')
        self.assertEqual(result['error'], 'media_processing_expired')
        self.assertIsNone(result['text'])
        self.assertEqual(self.process(), result)
        self.assertEqual(self.service.list('demo-1'), [result])
        self.assertEqual(len(self.provider.calls), 1)

    def test_replay_recovers_crashed_dispatch_without_resending(self):
        with patch.object(self.provider, 'process', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.process()
        with self.store._transaction(write=True) as connection:
            connection.execute("""UPDATE platform_media_runs SET record=jsonb_set(record::jsonb,
                '{created_at}',to_jsonb((clock_timestamp()-interval '301 seconds')::text))::text
                WHERE status='running'""")
        result = self.process()
        self.assertEqual(result['status'], 'outcome_unknown')
        self.assertEqual(result['error'], 'media_processing_expired')
        self.assertEqual(self.provider.calls, [])
        with self.assertRaisesRegex(ValueError, '^media_budget_exhausted$'):
            self.process('another-key')

    def shared_ledger(self):
        from tools.dwelly_analysis import jobs
        self.shared_schema = self.schema + '_models'
        jobs.migrate(self.dsn, self.shared_schema)
        ledger = jobs.AnalysisJobStore(self.dsn, self.shared_schema)
        self.addCleanup(ledger.close)
        self.service = media.MediaService(self.store, self.provider, budget_scope='shared', budget_schema=self.shared_schema)
        return ledger

    def test_existing_text_reservation_prevents_media_from_exceeding_shared_cap(self):
        from tools.dwelly_analysis.tests.test_jobs import spec
        ledger = self.shared_ledger()
        ledger.submit('text', spec(model='fixture-vision'), '0.1', '25', 'shared')
        with self.assertRaisesRegex(ValueError, '^media_budget_exhausted$'):
            self.process()
        self.assertEqual(self.provider.calls, [])
        self.assertEqual(self.service.list('demo-1'), [])

    def test_media_reservation_prevents_text_and_survives_service_restart(self):
        from tools.dwelly_analysis.tests.test_jobs import spec
        ledger = self.shared_ledger()
        self.process()
        with self.assertRaisesRegex(ValueError, '^budget_exhausted$'):
            ledger.submit('text', spec(model='fixture-vision'), '0.1', '25', 'shared')
        restarted = media.MediaService(self.store, self.provider, budget_scope='shared', budget_schema=self.shared_schema)
        with self.assertRaisesRegex(ValueError, '^media_budget_exhausted$'):
            restarted.process('demo-1', self.asset['asset_id'], 'another-key', {'mode': 'image_analysis'})
        self.assertEqual(len(self.provider.calls), 1)

    def test_shared_budget_reservation_rolls_back_with_failed_media_insert(self):
        ledger = self.shared_ledger()
        with self.store._transaction(write=True) as connection:
            connection.execute("ALTER TABLE platform_media_runs ADD CONSTRAINT reject_fixture CHECK (idempotency_key <> 'run')")
        with self.assertRaisesRegex(ValueError, '^case_storage_error$'):
            self.process()
        with ledger._transaction() as connection:
            self.assertEqual(connection.execute('SELECT count(*) AS count FROM model_budget_buckets').fetchone()['count'], 0)
        with self.store._transaction() as connection:
            self.assertEqual(connection.execute('SELECT count(*) FROM platform_media_runs').fetchone()[0], 0)
        self.assertEqual(self.provider.calls, [])

    def test_concurrent_text_and_media_share_one_atomic_cap(self):
        from tools.dwelly_analysis.tests.test_jobs import spec
        ledger = self.shared_ledger()
        barrier = threading.Barrier(2)
        def text():
            barrier.wait()
            try:
                ledger.submit('text', spec(model='fixture-vision'), '0.1', '25', 'shared')
                return 'text'
            except ValueError as error:
                return str(error)
        def image():
            barrier.wait()
            try:
                self.process()
                return 'media'
            except ValueError as error:
                return str(error)
        with ThreadPoolExecutor(max_workers=2) as pool:
            one, two = pool.submit(text), pool.submit(image)
            results = [one.result(timeout=5), two.result(timeout=5)]
        self.assertTrue(results in (['text', 'media_budget_exhausted'], ['budget_exhausted', 'media']))
        with ledger._transaction() as connection:
            reserved = connection.execute('SELECT reserved_usd FROM model_budget_buckets').fetchone()['reserved_usd']
            self.assertLessEqual(reserved, 25)

    def test_even_tiny_text_reservation_leaves_insufficient_room_for_full_media_reservation(self):
        from tools.dwelly_analysis.tests.test_jobs import spec
        ledger = self.shared_ledger()
        ledger.submit('text', spec(model='fixture-vision'), '1e-30', '25', 'shared')
        with self.assertRaisesRegex(ValueError, '^media_budget_exhausted$'):
            self.process()
        self.assertEqual(self.provider.calls, [])


class MediaProviderTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(media, 'media processing service must be implemented')

    def response(self, body, requests):
        class Response:
            status = 200
            headers = {'x-request-id': 'request-test', 'Authorization': 'never-save'}
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, size): return json.dumps(body).encode()
        def transport(request, timeout):
            requests.append(request)
            return Response()
        return transport

    def test_vision_uses_base64_input_image_without_generation_tool(self):
        requests = []
        body = {'status': 'completed', 'model': 'actual-vision', 'output': [
            {'type': 'message', 'content': [{'type': 'output_text', 'text': 'A parcel.'}]}],
            'usage': {'input_tokens': 2, 'output_tokens': 3, 'unsafe': 'drop'}}
        provider = media.OpenAIMediaProvider(image_model='configured-vision', transport=self.response(body, requests))
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'fake-test-key'}):
            result = provider.process('image_analysis', image_bytes(), 'image/png')
        request = requests[0]
        self.assertEqual(request.full_url, 'https://api.openai.com/v1/responses')
        payload = json.loads(request.data)
        self.assertEqual(payload['model'], 'configured-vision')
        self.assertFalse(payload['store'])
        self.assertNotIn('tools', payload)
        parts = payload['input'][0]['content']
        self.assertEqual(parts[0]['type'], 'input_text')
        self.assertTrue(parts[1]['image_url'].startswith('data:image/png;base64,'))
        self.assertEqual(result['text'], 'A parcel.')
        self.assertEqual(result['observed_model'], 'actual-vision')
        self.assertNotIn('fake-test-key', json.dumps(result))
        self.assertNotIn('never-save', json.dumps(result))

    def test_asr_uses_multipart_file_and_configured_model(self):
        requests = []
        provider = media.OpenAIMediaProvider(asr_model='whisper-1', transport=self.response({'text': 'hello'}, requests))
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'fake-test-key'}):
            result = provider.process('asr', audio_bytes(), 'audio/wav')
        request = requests[0]
        self.assertEqual(request.full_url, 'https://api.openai.com/v1/audio/transcriptions')
        self.assertIn('multipart/form-data; boundary=', request.get_header('Content-type'))
        self.assertIn(b'whisper-1', request.data)
        self.assertIn(b'name="language"\r\n\r\nen\r\n', request.data)
        self.assertIn(b'filename="audio.wav"', request.data)
        self.assertIn(audio_bytes(), request.data)
        self.assertIsNone(result['observed_model'])

    def test_absent_key_never_invokes_transport(self):
        provider = media.OpenAIMediaProvider(transport=lambda *args: self.fail('no transport without credentials'))
        with patch.dict(os.environ, {'OPENAI_API_KEY': ''}):
            self.assertEqual(provider.availability('asr'), 'missing_api_key')
            with self.assertRaisesRegex(ValueError, '^media_processing_disabled$'):
                provider.process('asr', audio_bytes(), 'audio/wav')
