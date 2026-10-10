"""Actual HTTP replay through the transactional PostgreSQL platform."""
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib
import json
import subprocess
import sys
import threading

import pytest

from tools.dwelly_platform.scenarios import prepare_terms_demo
from tools.dwelly_platform.tests.test_server import platform

try:
    demo = importlib.import_module('tools.dwelly_platform.terms_demo')
except ModuleNotFoundError:
    demo = None


def anchor():
    return (datetime.now(timezone.utc) + timedelta(days=7)).date().isoformat()


def run(*args):
    assert demo is not None, 'HTTP terms demo runner must exist'
    return demo.run_terms_demo(*args)


def test_full_http_demo_preserves_source_and_confirms_only_local_booking(platform):
    _, store, origin = platform
    day = anchor()
    receipt = run(origin, 'scripted-terms', day)
    assert receipt['mode'] == 'backend_scripted_operator_e2e'
    assert receipt['model_calls'] == receipt['external_effects'] == 0
    assert receipt['phase'] == 'booking_confirmed'
    assert receipt['physical_delivery'] == 'not_confirmed'
    assert receipt['phase_trace'] == ['booked', 'cancellation_pending', 'awaiting_terms',
                                      'awaiting_consent', 'ready_to_book', 'booking_pending', 'booking_confirmed']
    final = store.detail('scripted-terms')
    assert final['coordination'] == receipt['coordination']
    assert final['model_jobs'] == []
    source = prepare_terms_demo('scripted-terms', day)
    events = {e['event_id']: e for e in final['snapshot']['events']}
    for source_event in source['events']:
        assert events[source_event['event_id']] == source_event
    assert len(events) == 21  # 12 source/context + 7 command audits + 2 local readbacks.
    pseudo = [e for e in events.values() if e['event_id'].startswith('demo-readback-')]
    assert len(pseudo) == 2
    assert all('scripted_local_attestation_not_authentic_dispatch' in e['text'] for e in pseudo)
    assert {json.loads(e['text'])['source_event_id'] for e in pseudo} == {'003', '011'}
    assert all(step['status'] in (200, 201, 404) for step in receipt['http_steps'])
    assert all('Idempotency-Key' in step['request_headers'] for step in receipt['http_steps'] if step['method'] == 'POST')
    assert receipt['provenance']['source_sha256'] == source['provenance']['source_sha256']


def test_existing_case_is_never_overwritten_or_resumed(platform):
    request, store, origin = platform
    day = anchor()
    declaration = prepare_terms_demo('already-present', day)['declaration']
    assert request('/api/platform/cases', declaration)[0] == 201
    before = store.detail('already-present')
    with pytest.raises(ValueError, match='case_already_exists'):
        run(origin, 'already-present', day)
    assert store.detail('already-present') == before


@pytest.mark.parametrize('origin', ['https://127.0.0.1:80', 'http://example.com',
    'http://127.0.0.1.evil.test', 'http://user@127.0.0.1:80', 'http://127.0.0.1:80/path',
    'http://127.0.0.1:80?x=1', 'http://127.0.0.1:80#fragment', True, None])
def test_only_plain_loopback_origins_are_accepted(origin):
    with pytest.raises(ValueError, match='invalid_loopback_origin'):
        run(origin, 'valid-case', anchor())


def test_redirect_is_rejected_without_following_location():
    class Redirect(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(302)
            self.send_header('Location', 'https://example.com/should-never-be-contacted')
            self.end_headers()
        def log_message(self, *_):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Redirect)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with pytest.raises(ValueError, match='http_status_302'):
            run(f'http://127.0.0.1:{server.server_port}', 'redirect-case', anchor())
    finally:
        server.shutdown(); server.server_close(); thread.join(3)


def test_capabilities_gate_prevents_case_creation(platform, monkeypatch):
    from tools.dwelly_platform import server
    request, store, origin = platform
    original = server.capabilities
    def disabled(*args, **kwargs):
        value = original(*args, **kwargs)
        value['coordination']['external_effects'] = 1
        return value
    monkeypatch.setattr(server, 'capabilities', disabled)
    with pytest.raises(ValueError, match='unsafe_platform_capabilities'):
        run(origin, 'disabled-case', anchor())
    assert request('/api/platform/cases/disabled-case')[0] == 404


def test_cli_produces_machine_readable_receipt(platform):
    _, store, origin = platform
    result = subprocess.run([sys.executable, '-m', 'tools.dwelly_platform.terms_demo',
                             '--base-url', origin, '--case-id', 'cli-terms', '--anchor-date', anchor()],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt['phase'] == 'booking_confirmed'
    assert store.detail('cli-terms')['coordination']['phase'] == 'booking_confirmed'


@pytest.mark.parametrize('corruption', ['phase', 'revision', 'hash', 'external_effects',
                                       'physical_delivery', 'source_text', 'context', 'readback', 'audit'])
def test_inconsistent_final_http_readback_cannot_produce_success(platform, monkeypatch, corruption):
    from tools.dwelly_platform.server import Handler
    _, store, origin = platform
    original_detail = Handler._detail

    def corrupted_detail(handler, case_id):
        detail = original_detail(handler, case_id)
        state = detail.get('coordination')
        if handler.command != 'GET' or not state or state['phase'] != 'booking_confirmed':
            return detail
        snapshot = detail['snapshot']
        if corruption == 'phase':
            state['phase'] = 'escalated'
        elif corruption == 'revision':
            snapshot['revision'] += 1
        elif corruption == 'hash':
            snapshot['snapshot_hash'] = '0' * 64
        elif corruption == 'external_effects':
            state['external_effects'] = 1
        elif corruption == 'physical_delivery':
            state['physical_delivery'] = 'delivered'
        elif corruption == 'source_text':
            next(event for event in snapshot['events'] if event['event_id'] == '001')['text'] = 'Unrelated source'
        else:
            prefix = {'context': 'source-context', 'readback': 'demo-readback-', 'audit': 'coord-'}[corruption]
            index = next(i for i, event in enumerate(snapshot['events']) if event['event_id'].startswith(prefix))
            snapshot['events'].pop(index)
        return detail

    monkeypatch.setattr(Handler, '_detail', corrupted_detail)
    with pytest.raises(ValueError, match='inconsistent_final_readback'):
        run(origin, 'corrupted-final', anchor())
    # Only the HTTP readback was changed; the actual transactional workflow succeeded.
    assert store.detail('corrupted-final')['coordination']['phase'] == 'booking_confirmed'
