"""Real HTTP/PostgreSQL contracts for source-bound local Dispatch coordination."""
from datetime import datetime, timedelta, timezone

from tools.dwelly_platform.tests.test_server import platform  # shared real-server fixture


def declaration():
    return {'case_id': 'terms-http', 'links': {'order_id': 'DL-001',
            'customer_id': 'customer', 'operator_id': 'operator'},
            'participants': ['customer', 'operator', 'dispatch'], 'language': 'en'}


def terms():
    start = datetime.now(timezone.utc) + timedelta(days=7)
    return {'slot_start': start.isoformat(), 'slot_end': (start + timedelta(hours=3)).isoformat(),
            'handover': 'recipient_only', 'recipient_present': True,
            'charge': {'amount_minor': 0, 'currency': 'GBP'}}


def test_coordination_routes_preserve_existing_case_and_replay(platform):
    request, store, _ = platform
    assert request('/api/platform/cases', declaration())[0] == 201
    code, empty, _ = request('/api/platform/cases/terms-http/coordination')
    assert code == 200
    assert empty == {'coordination': None}
    before = store.get('terms-http')
    body = {'expected_revision': before['revision'], 'snapshot_hash': before['snapshot_hash'],
            'expected_workflow_version': 0, 'command': 'initialize', 'dispatch_actor_id': 'dispatch',
            'original_booking': {'booking_id': 'original', 'terms': terms()}}
    code, result, _ = request('/api/platform/cases/terms-http/coordination', body,
                             headers={'Idempotency-Key': 'terms-init'})
    assert code == 200
    assert result['coordination']['phase'] == 'booked'
    assert result['coordination']['version'] == 1
    assert result['coordination']['external_effects'] == 0
    assert request('/api/platform/cases/terms-http')[1]['case']['coordination'] == result['coordination']
    assert store.get('terms-http')['revision'] == before['revision'] + 1
    assert request('/api/platform/cases/terms-http/coordination', body,
                   headers={'Idempotency-Key': 'terms-init'})[1] == result
    assert store.get('terms-http')['revision'] == before['revision'] + 1
    assert request('/api/platform/cases/terms-http/coordination', body,
                   headers={'Idempotency-Key': 'terms-stale'})[0] == 409


def test_coordination_bad_payload_and_missing_case_have_public_errors(platform):
    request, _, _ = platform
    assert request('/api/platform/cases', declaration())[0] == 201
    code, result, _ = request('/api/platform/cases/terms-http/coordination', {})
    assert code == 400
    assert result['error']['code'] == 'invalid_coordination_request'
    assert request('/api/platform/cases/missing/coordination')[0] == 404
