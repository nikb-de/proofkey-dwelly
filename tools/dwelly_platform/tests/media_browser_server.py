"""Browser acceptance fixture: real PostgreSQL and MediaService; no network provider.

Only this test module installs the clearly identified in-process test provider.
Its unique test schema is dropped when the fixture stops, including on SIGTERM.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import threading
import uuid
import wave

import psycopg
from psycopg import sql
from PIL import Image

from tools.dwelly_platform.media import MediaService, migrate_media
from tools.dwelly_platform.models import project_snapshot
from tools.dwelly_platform.server import create_server
from tools.dwelly_platform.store import PlatformStore, migrate


class BrowserTestProvider:
    name = 'test-provider'

    def __init__(self):
        self.calls = []

    def model_id(self, mode):
        return 'fixture-vision' if mode == 'image_analysis' else 'fixture-asr'

    def availability(self, mode):
        return None

    def process(self, mode, data, mime_type):
        self.calls.append({'mode': mode, 'mime_type': mime_type, 'size_bytes': len(data)})
        text = ('TEST PROVIDER: A parcel note reads tomorrow morning. '
                '<script>window.mediaInjected=true</script>') if mode == 'image_analysis' else (
                'TEST PROVIDER: Please deliver after ten tomorrow morning.')
        return {'text': text, 'provider': self.name, 'requested_model': self.model_id(mode),
                'observed_model': self.model_id(mode) + '-observed',
                'request_id': 'test-request-' + mode, 'usage': {'input_tokens': 10, 'output_tokens': 10},
                'latency_ms': 1}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8096)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    dsn = os.environ.get('PROOFKEY_TEST_DATABASE_URL')
    if not dsn:
        parser.error('PROOFKEY_TEST_DATABASE_URL is required')
    schema = 'media_ui_test_' + uuid.uuid4().hex
    args.output_dir.mkdir(parents=True, exist_ok=True)
    Image.new('RGB', (24, 16), '#ede6d8').save(args.output_dir / 'source.png', format='PNG')
    with wave.open(str(args.output_dir / 'source.wav'), 'wb') as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(8000)
        stream.writeframes(b'\0\0' * 800)
    (args.output_dir / 'invalid.png').write_bytes(b'\x89PNG\r\n\x1a\ninvalid-content')
    store = server = None
    provider = BrowserTestProvider()
    report = {'test_only': True, 'provider': provider.name, 'schema': schema, 'live_provider_calls': 0}
    try:
        migrate(dsn, schema=schema)
        store = PlatformStore(dsn, schema=schema)
        migrate_media(store)
        media = MediaService(store, provider=provider, budget_scope='browser-test-' + uuid.uuid4().hex)
        server = create_server(store, port=args.port, media=media)

        def stop(_signal, _frame):
            threading.Thread(target=server.shutdown, daemon=True).start()

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        print(json.dumps({'ready': True, 'origin': f'http://127.0.0.1:{server.server_port}',
                          'test_only': True, 'provider': provider.name, 'schema': schema}), flush=True)
        server.serve_forever(poll_interval=0.05)
        report['calls'] = provider.calls
        report['cases'] = []
        for case in store.list_cases():
            snapshot = store.get(case['case_id'])
            report['cases'].append({'snapshot': snapshot, 'model_projection': project_snapshot(snapshot),
                                    'media_runs': media.list(case['case_id'])})
    finally:
        if server:
            server.server_close()
        if store:
            store.close()
        with psycopg.connect(dsn, autocommit=True) as connection:
            connection.execute(sql.SQL('DROP SCHEMA IF EXISTS {} CASCADE').format(sql.Identifier(schema)))
            report['schema_dropped'] = connection.execute(
                'SELECT NOT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name=%s)',
                (schema,)).fetchone()[0]
        (args.output_dir / 'database-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
