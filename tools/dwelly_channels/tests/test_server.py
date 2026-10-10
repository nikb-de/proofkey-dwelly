"""Actual HTTP + PostgreSQL ingress; no external provider or business effects."""
import hashlib
import hmac
import importlib
import json
import os
import threading
import time
import uuid
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

SECRET = 'local-test-signing-secret-' + 'x' * 40


def envelope(delivery='delivery-1', conversation='thread-1'):
    return {'schema_version':'proofkey-inbound-v1', 'delivery_id':delivery,
            'conversation_id':conversation, 'format':'message', 'payload':{
                'sender':'external-customer', 'recipients':['external-operator'],
                'occurred_at':'2026-10-10T10:00:00Z', 'text':'Please deliver tomorrow.'}}


def config():
    return {'schema_version':'proofkey-channel-config-v1','connectors':[{
        'id':'chat-demo','channel':'chat','secret_env':'PROOFKEY_CHAT_WEBHOOK_SECRET',
        'routes':{'thread-1':'case-1'},
        'contacts':{'external-customer':'customer','external-operator':'operator'}}]}


@pytest.fixture
def channels():
    assert importlib.util.find_spec('tools.dwelly_channels.service') is not None, 'durable channel service is required'
    from tools.dwelly_channels.service import ChannelService, migrate_channels
    from tools.dwelly_platform.store import PlatformStore, migrate
    dsn = os.environ.get('PROOFKEY_TEST_DATABASE_URL')
    if not dsn:
        pytest.skip('real PostgreSQL required')
    schema = 'channels_http_' + uuid.uuid4().hex
    migrate(dsn,schema=schema)
    store = PlatformStore(dsn,schema=schema)
    try:
        migrate_channels(store)
        store.create('case-1',{'case_id':'case-1','links':{'order_id':'order-1','customer_id':'customer',
            'operator_id':'operator'},'participants':['customer','operator'],'language':'en'})
        yield ChannelService(store,config()), store
    finally:
        store.close()
        import psycopg
        from psycopg import sql
        with psycopg.connect(dsn,autocommit=True) as connection:
            connection.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))


def launch(server):
    thread = threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    return thread, 'http://127.0.0.1:' + str(server.server_port)


def request(origin, path, body=None, headers=None, raw=None):
    supplied = dict(headers or {})
    if body is not None:
        raw = json.dumps(body,separators=(',',':')).encode()
    if raw is not None:
        supplied.setdefault('Content-Type','application/json')
    try:
        response = urlopen(Request(origin+path,data=raw,headers=supplied),timeout=10)
    except HTTPError as error:
        response = error
    return response.status,json.loads(response.read())


def signed(raw, *, timestamp=None, secret=SECRET):
    timestamp = str(int(time.time())) if timestamp is None else str(timestamp)
    signature = hmac.new(secret.encode(),timestamp.encode()+b'.'+raw,hashlib.sha256).hexdigest()
    return {'X-ProofKey-Timestamp':timestamp,'X-ProofKey-Signature':signature,'Content-Type':'application/json'}


def test_signed_delivery_replays_once_without_model_or_business_effect(channels):
    from tools.dwelly_channels.server import create_server
    service,store = channels
    server = create_server(service,{'chat-demo':SECRET},port=0)
    thread,origin = launch(server)
    try:
        raw = json.dumps(envelope()).encode()
        code,result = request(origin,'/webhooks/chat-demo',raw=raw,headers=signed(raw))
        assert code == 200 and result['receipt']['status'] == 'accepted'
        replay = request(origin,'/webhooks/chat-demo',raw=raw,headers=signed(raw))[1]
        assert replay == result
        assert store.get('case-1')['revision'] == 1
        detail = store.detail('case-1')
        assert detail['decisions'] == detail['actions'] == detail['model_jobs'] == []
        assert detail['external_effects'] == 0
        assert len(store.analysis_jobs('case-1')) == 2
    finally:
        server.shutdown(); server.server_close(); thread.join(3)


@pytest.mark.parametrize('change', ['missing','wrong','expired','future','origin','content_changed'])
def test_authentication_precedes_parsing_and_storage(channels, change):
    from tools.dwelly_channels.server import create_server
    service,store = channels
    server = create_server(service,{'chat-demo':SECRET},port=0)
    thread,origin = launch(server)
    try:
        raw = b'{not valid JSON'
        headers = signed(raw)
        if change == 'missing': headers.pop('X-ProofKey-Signature')
        if change == 'wrong': headers['X-ProofKey-Signature'] = '0'*64
        if change == 'expired': headers = signed(raw,timestamp=int(time.time())-301)
        if change == 'future': headers = signed(raw,timestamp=int(time.time())+301)
        if change == 'origin': headers['Origin'] = origin
        if change == 'content_changed': raw += b'!'
        assert request(origin,'/webhooks/chat-demo',raw=raw,headers=headers)[0] == 403
        assert service.list() == []
        assert store.get('case-1')['revision'] == 0
    finally:
        server.shutdown(); server.server_close(); thread.join(3)


def test_authenticated_invalid_json_and_conflicting_delivery_are_bounded(channels):
    from tools.dwelly_channels.server import create_server
    service,_ = channels
    server = create_server(service,{'chat-demo':SECRET},port=0)
    thread,origin = launch(server)
    try:
        for raw in (b'{broken',b'{"schema_version":1,"schema_version":2}'):
            assert request(origin,'/webhooks/chat-demo',raw=raw,headers=signed(raw))[0] == 400
        first = json.dumps(envelope()).encode()
        assert request(origin,'/webhooks/chat-demo',raw=first,headers=signed(first))[0] == 200
        changed = envelope(); changed['payload']['text'] = 'Changed message'
        raw = json.dumps(changed).encode()
        assert request(origin,'/webhooks/chat-demo',raw=raw,headers=signed(raw))[0] == 409
    finally:
        server.shutdown(); server.server_close(); thread.join(3)


def test_operator_import_exposes_receipt_and_case_provenance(channels):
    from tools.dwelly_platform.server import create_server
    service,store = channels
    server = create_server(store,channels=service,port=0)
    thread,origin = launch(server)
    headers = {'X-ProofKey-Request':'platform-v1','Idempotency-Key':'local-import'}
    try:
        body = {'connector_id':'chat-demo','envelope':envelope()}
        assert request(origin,'/api/platform/communications/import',body=body)[0] == 403
        code,result = request(origin,'/api/platform/communications/import',body=body,headers=headers)
        assert code == 200 and result['receipt']['status'] == 'accepted'
        code,listing = request(origin,'/api/platform/communications')
        assert code == 200 and listing['provider_connections'] is False
        assert len(listing['receipts']) == 1
        assert SECRET not in json.dumps(listing)
        assert 'external-customer' not in json.dumps(listing['connectors'])
        code,case = request(origin,'/api/platform/cases/case-1')
        assert code == 200 and case['case']['communications'][0]['receipt_id'] == result['receipt']['receipt_id']
        caps = request(origin,'/api/platform/capabilities')[1]
        assert caps['communications']['provider_connections'] is False
        assert next(a for a in caps['adapters'] if a['id']=='messaging')['mode'] == 'local_ingress'
    finally:
        server.shutdown(); server.server_close(); thread.join(3)


def test_listeners_reject_public_bind_and_weak_secrets(channels, monkeypatch):
    from tools.dwelly_channels.server import create_server
    service,_ = channels
    with pytest.raises(ValueError,match='local_trust_boundary_only'):
        create_server(service,{'chat-demo':SECRET},host='0.0.0.0',port=0)
    with pytest.raises(ValueError,match='invalid_channel_secret'):
        create_server(service,{'chat-demo':'short'},port=0)
    monkeypatch.setenv('K_SERVICE','cloud')
    with pytest.raises(ValueError,match='local_trust_boundary_only'):
        create_server(service,{'chat-demo':SECRET},port=0)
