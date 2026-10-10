"""Actual loopback HTTP and PostgreSQL tests, no API response mocks."""
import base64
import json
import os
import threading
import uuid
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import psycopg
from psycopg import sql
import pytest


@pytest.fixture
def platform():
    from tools.dwelly_platform.store import PlatformStore, migrate
    from tools.dwelly_platform.server import create_server
    dsn = os.environ.get('PROOFKEY_TEST_DATABASE_URL')
    if not dsn:
        pytest.skip('real PostgreSQL required')
    schema = 'platform_http_' + uuid.uuid4().hex
    migrate(dsn, schema=schema)
    store = PlatformStore(dsn, schema=schema)
    server = create_server(store, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = 'http://127.0.0.1:' + str(server.server_port)
    def request(path, body=None, *, headers=None, raw=None):
        supplied = dict(headers or {})
        data = raw
        if body is not None:
            data = json.dumps(body).encode()
            supplied.setdefault('Content-Type', 'application/json')
        if data is not None:
            supplied.setdefault('X-ProofKey-Request', 'platform-v1')
            supplied.setdefault('Idempotency-Key', uuid.uuid4().hex)
        req = Request(origin + path, data=data, headers=supplied)
        try:
            response = urlopen(req, timeout=5)
        except HTTPError as error:
            response = error
        payload = response.read()
        if response.headers.get('Content-Type', '').startswith('application/json'):
            payload = json.loads(payload)
        return response.status, payload, response.headers
    yield request, store, origin
    server.shutdown(); server.server_close(); thread.join(3); store.close()
    with psycopg.connect(dsn) as conn:
        conn.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))


def declaration(case_id='case1'):
    return {'case_id': case_id, 'links': {'order_id':'order1', 'customer_id':'customer', 'operator_id':'operator'},
            'participants':['customer','operator'], 'language':'en'}


def event():
    return {'event_id':'event1','occurred_at':datetime.now(timezone.utc).isoformat(),'channel':'chat',
            'sender_id':'customer','recipient_ids':['operator'],'kind':'message',
            'text':'Please reschedule <img src=x onerror=alert(1)>','media':None}


def test_actual_case_to_verified_sandbox_flow(platform):
    request, store, origin = platform
    code, created, headers = request('/api/platform/cases', declaration())
    assert code == 201
    assert headers['Cache-Control'] == 'no-store'
    assert created['case']['snapshot']['revision'] == 0
    code, appended, _ = request('/api/platform/cases/case1/events', {'expected_revision':0,'event':event()})
    assert code == 200
    snapshot = appended['case']['snapshot']
    binding = {'expected_revision':1,'snapshot_hash':snapshot['snapshot_hash']}
    code, analyzed, _ = request('/api/platform/cases/case1/analyze', dict(binding, mode='deterministic'))
    assert code == 200
    assert analyzed['case']['decisions'][-1]['kind'] == 'deterministic'
    start = datetime.now(timezone.utc) + timedelta(days=1)
    code, proposed, _ = request('/api/platform/cases/case1/decisions', dict(binding,
        action={'type':'reschedule_delivery','slot_start':start.isoformat(),
                'slot_end':(start+timedelta(hours=2)).isoformat(),'address_change':False}, evidence_event_ids=['event1']))
    assert code == 200
    decision = proposed['case']['decisions'][-1]['decision_id']
    assert request('/api/platform/cases/case1/execute', {'decision_id':decision})[0] == 409
    assert request('/api/platform/cases/case1/reviews', {'decision_id':decision,'verdict':'approve',
        'note':'Customer consent checked by local operator','customer_consent_confirmed':True})[0] == 200
    code, executed, _ = request('/api/platform/cases/case1/execute', {'decision_id':decision})
    assert code == 200
    assert executed['case']['states']['action'] == 'verified'
    assert executed['case']['external_effects'] == 0
    assert executed['case']['snapshot']['operational_effects'] == 0
    assert request('/api/platform/cases/case1/execute', {'decision_id':decision})[1]['case']['actions'] == executed['case']['actions']
    reloaded = request('/api/platform/cases/case1')[1]['case']
    assert reloaded['actions'] == executed['case']['actions']
    assert len(request('/api/platform/cases')[1]['cases']) == 1


def test_origin_json_and_credentials_boundaries(platform):
    request, _, origin = platform
    assert request('/api/platform/cases', declaration(), headers={'Origin':'https://evil.example'})[0] == 403
    assert request('/api/platform/cases', declaration(), headers={'X-ProofKey-Request':'wrong'})[0] == 403
    code, _, _ = request('/api/platform/cases', declaration(), headers={'Origin':origin})
    assert code == 201
    assert request('/api/platform/cases', raw=b'{"a":1,"a":2}', headers={'Content-Type':'application/json'})[0] == 400
    caps = request('/api/platform/capabilities')[1]
    assert caps['models']['enabled'] is False
    assert len(caps['adapters']) == 6
    assert caps['external_effects'] == 0
    code, _, _ = request('/api/platform/cases/case1/model-runs', {'expected_revision':0,
        'snapshot_hash':request('/api/platform/cases/case1')[1]['case']['snapshot']['snapshot_hash'],'model_profile_id':'openai'})
    assert code == 409


def test_private_asset_upload_and_cross_case_retrieval(platform):
    request, _, _ = platform
    request('/api/platform/cases', declaration())
    request('/api/platform/cases', declaration('case2'))
    image = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jGxoAAAAASUVORK5CYII=')
    code, media, _ = request('/api/platform/cases/case1/assets', raw=image,
        headers={'Content-Type':'image/png','X-Filename':'image.png'})
    assert code == 201
    asset_id = media['asset']['asset_id']
    code, data, headers = request('/api/platform/cases/case1/assets/' + asset_id)
    assert code == 200 and data == image
    assert headers['X-Content-Type-Options'] == 'nosniff'
    assert request('/api/platform/cases/case2/assets/' + asset_id)[0] == 404
    assert request('/api/platform/cases/case1/assets', raw=b'bad png',headers={'Content-Type':'image/png'})[0] == 400
    assert request('/api/platform/cases/case1/assets/' + asset_id + '/process', {'mode':'asr'})[0] in (400,409)


def test_static_ui_exists_with_no_external_code(platform):
    request, _, _ = platform
    code, page, headers = request('/')
    assert code == 200 and b'<html' in page.lower()
    assert 'default-src' in headers['Content-Security-Policy']
    assert request('/../.env')[0] == 404


def test_model_lifecycle_is_independent_of_actions():
    from tools.dwelly_platform.server import project_model_states
    detail = {'snapshot': {'revision':2,'snapshot_hash':'a'*64},
              'states':{'analysis':'not_started','lifecycle':'in_review','action':'none'},
              'decisions':[], 'model_jobs':[{'step_index':2,'status':'running'}]}
    assert project_model_states(detail)['states']['analysis'] == 'running'
    assert detail['states']['action'] == 'none'
    detail['model_jobs'][0]['status'] = 'failed'
    assert project_model_states(detail)['states']['analysis'] == 'failed'
    detail['model_jobs'][0]['status'] = 'outcome_unknown'
    assert project_model_states(detail)['states']['analysis'] == 'outcome_unknown'
    detail['model_jobs'][0]['status'] = 'succeeded'
    assert project_model_states(detail)['states']['analysis'] == 'current'
    detail['snapshot']['revision'] = 3
    assert project_model_states(detail)['states']['analysis'] == 'stale'


def test_malformed_json_is_a_client_error(platform):
    request, _, _ = platform
    assert request('/api/platform/cases',raw=b'{broken',headers={'Content-Type':'application/json'})[0] == 400


def test_database_failure_is_unavailable_not_a_client_validation_error(platform):
    request, store, _ = platform
    store.close()
    code, body, _ = request('/api/platform/cases')
    assert code == 503
    assert body == {'error':{'code':'platform_unavailable'}}


@pytest.mark.parametrize('error, status, code', [
    (ValueError('internal_connection_details'), 503, 'platform_unavailable'),
    (ValueError({'private': 'internal details'}), 503, 'platform_unavailable'),
    (ValueError('media_processing_disabled'), 409, 'media_processing_disabled'),
    (ValueError('media_budget_exhausted'), 409, 'media_budget_exhausted'),
    (ValueError('media_mode_mismatch'), 400, 'media_mode_mismatch'),
    (KeyError('job_not_found'), 404, 'job_not_found'),
])
def test_only_known_public_errors_are_exposed(platform, monkeypatch, error, status, code):
    request, store, _ = platform
    def fail():
        raise error
    monkeypatch.setattr(store, 'list_cases', fail)
    response_status, body, _ = request('/api/platform/cases')
    assert response_status == status
    assert body == {'error':{'code':code}}
