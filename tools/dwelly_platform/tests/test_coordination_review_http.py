"""Real HTTP/PostgreSQL review workflow; only provider HTTPS is substituted."""
import io
import json
import os
from datetime import datetime, timedelta, timezone

import pytest

from tools.dwelly_analysis import jobs, worker
from tools.dwelly_model import providers
from tools.dwelly_platform.models import ModelBridge
from tools.dwelly_platform.tests.test_server import platform


CASE = 'review-http'
ROUTE = '/api/platform/cases/' + CASE


def create(request):
    declaration = {'case_id': CASE, 'links': {'order_id': 'DL-001', 'customer_id': 'customer',
                   'operator_id': 'operator'}, 'participants': ['customer', 'operator', 'dispatch'], 'language': 'en'}
    assert request('/api/platform/cases', declaration)[0] == 201


def terms():
    start = datetime.now(timezone.utc) + timedelta(days=7)
    return {'slot_start': start.isoformat(), 'slot_end': (start + timedelta(hours=2)).isoformat(),
            'handover': 'concierge_allowed', 'recipient_present': False,
            'charge': {'amount_minor': 1200, 'currency': 'GBP'}}


def binding(request, command, **fields):
    detail = request(ROUTE)[1]['case']
    return {'command': command, 'expected_revision': detail['snapshot']['revision'],
            'snapshot_hash': detail['snapshot']['snapshot_hash'],
            'expected_workflow_version': (detail.get('coordination') or {}).get('version', 0), **fields}


def command(request, name, **fields):
    code, result, _ = request(ROUTE + '/coordination', binding(request, name, **fields))
    assert code == 200, result
    return result['coordination']


def source(request, identifier, sender, text):
    revision = request(ROUTE)[1]['case']['snapshot']['revision']
    body = {'expected_revision': revision, 'event': {'event_id': identifier,
            'occurred_at': datetime.now(timezone.utc).isoformat(), 'channel': 'chat',
            'kind': 'message', 'sender_id': sender, 'recipient_ids': ['operator'], 'text': text, 'media': None}}
    assert request(ROUTE + '/events', body)[0] == 200


def offer(request):
    create(request)
    command(request, 'initialize', dispatch_actor_id='dispatch',
            original_booking={'booking_id': 'original', 'terms': terms()})
    source(request, 'cancel-request', 'customer', 'Please cancel my old booking.')
    state = command(request, 'request_cancellation', evidence_event_ids=['cancel-request'])
    rid = state['pending_request']['request_id']
    source(request, 'cancel-readback', 'dispatch', 'Cancelled request ' + rid)
    command(request, 'confirm_cancellation', request_id=rid, evidence_event_ids=['cancel-readback'])
    source(request, 'offer-source', 'dispatch', 'Replacement with concierge allowed and GBP 12 surcharge.')
    return command(request, 'record_offer', terms=terms(), evidence_event_ids=['offer-source'])


@pytest.fixture
def runtime(platform, monkeypatch):
    _, store, _ = platform
    jobs.migrate(os.environ['PROOFKEY_TEST_DATABASE_URL'], schema=store.schema)
    job_store = jobs.AnalysisJobStore(os.environ['PROOFKEY_TEST_DATABASE_URL'], store.schema)
    settings = {'profiles': [{'id': 'controlled', 'label': 'Controlled transport, not a live model',
                'config': {'provider': 'openai', 'model': 'controlled-model', 'api_key_env': 'PROOFKEY_TEST_ONLY_KEY',
                           'input_usd_per_million': 1, 'output_usd_per_million': 2}}],
                'budget_per_model_usd': 1, 'max_output_tokens': 1024, 'timeout_seconds': 5}
    model_runtime = worker.ModelRuntime(job_store, settings, 'http-review-controlled', allow_live=True)
    monkeypatch.setenv('PROOFKEY_TEST_ONLY_KEY', 'not-a-live-secret')
    monkeypatch.setattr(ModelBridge, '_runtime', lambda self: model_runtime)
    yield model_runtime
    model_runtime.close()
    job_store.close()


class ControlledResponse(io.BytesIO):
    def __init__(self):
        candidate = {'state': 'ready', 'waiting_for': [], 'next_action': {'type': 'propose_forwarding',
                     'target_actor_id': 'dispatch', 'description': 'Review the request to cancel the original booking.'},
                     'evidence_event_ids': ['cancel-request'], 'uncertainty': ['Declared identity is not verified.']}
        response = {'id': 'controlled-response', 'model': 'controlled-model', 'status': 'completed',
                    'output': [{'type': 'message', 'status': 'completed', 'content':
                                [{'type': 'output_text', 'text': json.dumps(candidate)}]}],
                    'usage': {'input_tokens': 20, 'output_tokens': 30}}
        super().__init__(json.dumps(response).encode())
        self.status = 200
        self.headers = {'x-request-id': 'controlled-request'}


def test_http_model_proposal_is_advisory_and_current_review_is_audited(platform, runtime, monkeypatch):
    request, store, _ = platform
    create(request)
    command(request, 'initialize', dispatch_actor_id='dispatch', original_booking={'booking_id': 'original', 'terms': terms()})
    source(request, 'cancel-request', 'customer', 'Please cancel the old booking.')
    current = request(ROUTE)[1]['case']['snapshot']
    code, queued, _ = request(ROUTE + '/model-runs', {'expected_revision': current['revision'],
                 'snapshot_hash': current['snapshot_hash'], 'model_profile_id': 'controlled'})
    assert code == 202
    body = binding(request, 'request_cancellation', evidence_event_ids=['cancel-request'],
                   model_run_id=queued['run_id'], model_review_note='Operator checked source request and selected cancellation.')
    code, result, _ = request(ROUTE + '/coordination', body)
    assert code == 409, result
    assert store.get(CASE)['revision'] == current['revision']
    assert store.coordination_detail(CASE)['phase'] == 'booked'
    calls = []
    def controlled_https(req, timeout):
        calls.append(json.loads(req.data))
        return ControlledResponse()
    monkeypatch.setattr(providers, '_open', controlled_https)
    assert runtime.work_once()
    completed = request('/api/platform/model-runs/' + queued['run_id'])[1]
    assert completed['status'] == 'succeeded'
    assert len(calls) == 1
    assert store.get(CASE)['revision'] == current['revision'], 'A model result must not execute a command.'
    # One case connection must suffice: resolving the advisory job may not
    # borrow a second case connection while the command holds its write lock.
    from tools.dwelly_platform.store import PlatformStore
    single = PlatformStore(os.environ['PROOFKEY_TEST_DATABASE_URL'], schema=store.schema, max_size=1)
    store.pool.close()
    store.pool, single.pool = single.pool, None
    monkeypatch.setattr(store.pool, 'timeout', 0.1)
    code, result, _ = request(ROUTE + '/coordination', body, headers={'Idempotency-Key': 'review-command'})
    assert code == 200, result
    state = result['coordination']
    assert state['phase'] == 'cancellation_pending'
    context = state['audit_history'][-1]['model_context']
    assert context['run_id'] == queued['run_id']
    assert context['source_snapshot_hash'] == current['snapshot_hash']
    assert state['external_effects'] == 0
    source(request, 'intervening', 'customer', 'Thank you.')
    assert request(ROUTE + '/coordination', body, headers={'Idempotency-Key': 'review-command'})[1] == result
    stale = binding(request, 'escalate', reason='Needs current review', evidence_event_ids=['cancel-request'],
                    model_run_id=queued['run_id'], model_review_note='Old proposal cannot authorize a new command.')
    before = store.get(CASE)
    code, rejected, _ = request(ROUTE + '/coordination', stale)
    assert code == 409, rejected
    assert store.get(CASE) == before


def test_http_atomic_customer_preview_acceptance_to_local_booking_readback(platform):
    request, store, _ = platform
    offered = offer(request)
    before = store.get(CASE)
    body = binding(request, 'record_local_acceptance', offer_id=offered['offer']['offer_id'],
                   terms_hash=offered['offer']['terms_hash'], acknowledged=True)
    assert request(ROUTE + '/coordination', dict(body, acknowledged=False))[0] == 400
    assert store.get(CASE) == before
    code, result, _ = request(ROUTE + '/coordination', body, headers={'Idempotency-Key': 'customer-preview'})
    assert code == 200, result
    accepted = result['coordination']
    assert accepted['phase'] == 'ready_to_book'
    assert accepted['revision'] == before['revision'] + 2
    assert accepted['consent']['created_revision'] == accepted['revision']
    assert accepted['external_effects'] == 0
    assert accepted['pending_request'] is None
    assert request(ROUTE + '/coordination', body, headers={'Idempotency-Key': 'customer-preview'})[1] == result
    assert store.get(CASE)['revision'] == before['revision'] + 2
    pending = command(request, 'request_booking', offer_id=offered['offer']['offer_id'], terms_hash=offered['offer']['terms_hash'])
    assert pending['phase'] == 'booking_pending'
    assert pending['physical_delivery'] == 'not_confirmed'
    rid = pending['pending_request']['request_id']
    source(request, 'booking-readback', 'dispatch', 'Booking confirmed ' + rid + ' ' + offered['offer']['terms_hash'])
    final = command(request, 'confirm_booking', request_id=rid, terms_hash=offered['offer']['terms_hash'], evidence_event_ids=['booking-readback'])
    assert final['phase'] == 'booking_confirmed'
    assert final['physical_delivery'] == 'not_confirmed'
    assert final['external_effects'] == 0
    assert request(ROUTE)[1]['case']['coordination'] == final


def test_review_capabilities_and_new_static_assets(platform):
    request, _, _ = platform
    coordination = request('/api/platform/capabilities')[1]['coordination']
    assert 'record_local_acceptance' in coordination['commands']
    assert coordination['model_context'] == 'advisory_operator_review_only'
    for asset in ('coordination.js', 'coordination-panel.js', 'coordination.css', 'customer-coordination.js'):
        code, result, headers = request('/' + asset)
        assert code == 200, (asset, result)
        assert headers['Cache-Control'] == 'no-store'
