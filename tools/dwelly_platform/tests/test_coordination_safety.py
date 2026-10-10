"""Audit bounds fail atomically and operator escalation remains model-visible."""
import json

import pytest

from tools.dwelly_platform.tests.test_server import platform
from tools.dwelly_platform.tests.test_coordination_http import declaration, terms


def initialized(store):
    store.create('create', declaration())
    snapshot = store.get('terms-http')
    store.coordination_command('terms-http', 'init', {
        'command': 'initialize', 'expected_revision': snapshot['revision'],
        'snapshot_hash': snapshot['snapshot_hash'], 'expected_workflow_version': 0,
        'dispatch_actor_id': 'dispatch', 'original_booking': {'booking_id': 'old', 'terms': terms()}})


def evidence(store, identifier):
    snapshot = store.get('terms-http')
    store.append('terms-http', identifier, {'expected_revision': snapshot['revision'], 'event': {
        'event_id': identifier, 'occurred_at': '2026-10-10T10:00:00Z', 'channel': 'chat',
        'sender_id': 'customer', 'recipient_ids': ['operator'], 'kind': 'message',
        'text': 'Please ask an operator.', 'media': None}})


def escalation(store, ids):
    snapshot = store.get('terms-http')
    return {'command': 'escalate', 'expected_revision': snapshot['revision'],
            'snapshot_hash': snapshot['snapshot_hash'], 'expected_workflow_version': 1,
            'reason': 'The replacement terms cannot be agreed.', 'evidence_event_ids': ids}


def test_escalation_reason_is_part_of_immutable_case_context(platform):
    _, store, _ = platform
    initialized(store)
    evidence(store, 'message-one')
    body = escalation(store, ['message-one'])
    store.coordination_command('terms-http', 'escalate', body)
    audit = json.loads(store.get('terms-http')['events'][-1]['text'])
    assert audit['escalation']['reason'] == body['reason']
    assert audit['escalation']['evidence_event_ids'] == ['message-one']


def test_oversized_canonical_audit_has_a_specific_error_and_no_partial_write(platform):
    request, store, _ = platform
    initialized(store)
    ids = [f'evidence-{index:03d}-' + 'a' * 51 for index in range(60)]
    for identifier in ids:
        evidence(store, identifier)
    before = store.get('terms-http')
    code, response, _ = request('/api/platform/cases/terms-http/coordination', escalation(store, ids))
    assert code == 400
    assert response['error']['code'] == 'coordination_audit_too_large'
    assert store.get('terms-http') == before
    assert store.coordination_detail('terms-http')['version'] == 1
