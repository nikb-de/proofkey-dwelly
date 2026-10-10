"""Test-only communications browser fixture: real HTTP, PostgreSQL and ingress.

No provider is installed. The stdin command restores one trusted test route to
exercise explicit quarantine recovery without adding a production HTTP route.
Every write stays in a random schema, dropped on shutdown.
"""
import argparse
from email.message import EmailMessage
from email import policy
import json
import os
from pathlib import Path
import signal
import sys
import threading
import uuid
import wave

import psycopg
from psycopg import sql
from PIL import Image

from tools.dwelly_channels.service import ChannelService, migrate_channels
from tools.dwelly_platform.server import create_server
from tools.dwelly_platform.store import PlatformStore, migrate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    dsn = os.environ.get('PROOFKEY_TEST_DATABASE_URL')
    if not dsn:
        parser.error('PROOFKEY_TEST_DATABASE_URL is required')
    schema = 'communications_ui_test_' + uuid.uuid4().hex
    case_id = 'communications-ui'
    args.output_dir.mkdir(parents=True, exist_ok=True)
    Image.new('RGB', (24, 16), '#ede6d8').save(args.output_dir / 'source.png')
    with wave.open(str(args.output_dir / 'source.wav'), 'wb') as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(8000)
        stream.writeframes(b'\0\0' * 800)
    email = EmailMessage(policy=policy.SMTP)
    email['From'] = 'customer@example.test'
    email['To'] = 'operator@example.test'
    email['Date'] = 'Sat, 10 Oct 2026 12:00:00 +0000'
    email['Subject'] = 'SYNTHETIC delivery evidence'
    email.set_content('SYNTHETIC EMAIL: Please retain the original delivery address.')
    email.add_attachment((args.output_dir / 'source.png').read_bytes(), maintype='image', subtype='png', filename='source.png')
    (args.output_dir / 'source.eml').write_bytes(email.as_bytes())
    contacts = {'customer@example.test': 'customer-1', 'operator@example.test': 'operator-1',
                '+441111111111': 'customer-1', '+442222222222': 'operator-1'}
    config = {'schema_version': 'proofkey-channel-config-v1', 'connectors': [
        {'id': 'local-' + channel, 'channel': channel, 'secret_env': 'UNUSED_TEST_SECRET',
         'routes': {'conversation-main': case_id}, 'contacts': contacts}
        for channel in ('chat', 'email', 'phone')]}
    store = server = None
    report = {'test_only': True, 'schema': schema, 'case_ids': [case_id], 'provider_calls': 0}
    try:
        migrate(dsn, schema=schema)
        store = PlatformStore(dsn, schema=schema)
        migrate_channels(store)
        channels = ChannelService(store, config)
        server = create_server(store, port=0, channels=channels)

        def stop(_signal, _frame):
            threading.Thread(target=server.shutdown, daemon=True).start()

        def controls():
            for command in sys.stdin:
                if command.strip() == 'restore_test_route':
                    channels.connectors['local-chat']['routes']['recover-thread'] = case_id
                    print(json.dumps({'event': 'trusted_route_restored'}), flush=True)

        threading.Thread(target=controls, daemon=True).start()
        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        print(json.dumps({'ready': True, 'origin': f'http://127.0.0.1:{server.server_port}',
                          'test_only': True, 'schema': schema, 'case_id': case_id}), flush=True)
        server.serve_forever(poll_interval=0.05)
        report['receipts'] = channels.list()
        report['snapshots'] = [store.get(item['case_id']) for item in store.list_cases()]
        report['case_details'] = [store.detail(item['case_id']) for item in store.list_cases()]
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
