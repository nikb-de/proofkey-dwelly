"""Opt-in signed loopback ingress. Not a native provider or public auth gateway."""
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import re
import time

from tools.dwelly_analysis.server import _json
from tools.dwelly_service.cases import CaseError
from .contracts import MAX_ENVELOPE_BYTES

_PATH = re.compile(r'/webhooks/([A-Za-z0-9][A-Za-z0-9_-]{0,63})')


class Handler(BaseHTTPRequestHandler):
    server_version = 'ProofKeyIngress/1'

    def log_message(self, *_):
        pass

    def reply(self, status, value):
        raw = json.dumps(value,separators=(',',':'),allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(raw)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        self.connection.settimeout(15)
        try:
            matched = _PATH.fullmatch(self.path)
            if not matched:
                return self.reply(404,{'error':{'code':'not_found'}})
            connector_id = matched[1]
            port = self.server.server_port
            if (self.headers.get_all('Host',[]) not in ([f'127.0.0.1:{port}'],[f'localhost:{port}'])
                    or self.headers.get_all('Origin',[]) or self.headers.get('Sec-Fetch-Site') is not None):
                return self.reply(403,{'error':{'code':'invalid_ingress_boundary'}})
            lengths = self.headers.get_all('Content-Length',[])
            if (self.headers.get('Transfer-Encoding') is not None or len(lengths) != 1
                    or re.fullmatch(r'[0-9]{1,9}',lengths[0]) is None):
                return self.reply(400,{'error':{'code':'invalid_request'}})
            length = int(lengths[0])
            if not 1 <= length <= MAX_ENVELOPE_BYTES:
                return self.reply(413,{'error':{'code':'request_too_large'}})
            timestamps = self.headers.get_all('X-ProofKey-Timestamp',[])
            signatures = self.headers.get_all('X-ProofKey-Signature',[])
            secret = self.server.secrets.get(connector_id)
            if (secret is None or len(timestamps) != 1 or len(signatures) != 1
                    or re.fullmatch(r'[0-9]{1,12}',timestamps[0]) is None
                    or re.fullmatch(r'[a-f0-9]{64}',signatures[0]) is None
                    or abs(time.time()-int(timestamps[0])) > 300):
                return self.reply(403,{'error':{'code':'invalid_signature'}})
            raw = self.rfile.read(length)
            if len(raw) != length:
                return self.reply(400,{'error':{'code':'invalid_request'}})
            expected = hmac.new(secret,timestamps[0].encode()+b'.'+raw,hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected,signatures[0]):
                return self.reply(403,{'error':{'code':'invalid_signature'}})
            if self.headers.get_all('Content-Type',[]) != ['application/json']:
                return self.reply(400,{'error':{'code':'invalid_content_type'}})
            try:
                envelope = _json(raw)
            except (ValueError,UnicodeError,RecursionError):
                return self.reply(400,{'error':{'code':'invalid_request'}})
            receipt = self.server.channels.ingest(connector_id,envelope,source='signed_webhook')
            return self.reply(200,{'receipt':receipt})
        except (CaseError,ValueError,KeyError,OSError) as error:
            code = getattr(error,'code',error.args[0] if error.args else None)
            status = 409 if code in ('delivery_conflict','inbox_capacity') else 400
            if code not in ('delivery_conflict','inbox_capacity','unknown_connector','invalid_envelope','envelope_too_large','invalid_identity'):
                status,code = 503,'ingress_unavailable'
            return self.reply(status,{'error':{'code':code}})


def create_server(channels, secrets, *, host='127.0.0.1', port=8096):
    if host != '127.0.0.1' or any(os.environ.get(key) for key in ('K_SERVICE','FUNCTION_TARGET','CLOUD_RUN_JOB')):
        raise ValueError('local_trust_boundary_only')
    if (type(secrets) is not dict or not secrets
            or any(type(key) is not str or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}',key) is None
                   or type(value) is not str or len(value.encode()) < 32 for key,value in secrets.items())):
        raise ValueError('invalid_channel_secret')
    server = ThreadingHTTPServer((host,port),Handler)
    server.daemon_threads = True
    server.channels = channels
    server.secrets = {key:value.encode() for key,value in secrets.items()}
    return server
