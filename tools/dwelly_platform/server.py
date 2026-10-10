"""Local same-origin product BFF. Never expose this trust model to the network."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit

from tools.dwelly_analysis.server import _json
from tools.dwelly_platform.models import ModelBridge
from tools.dwelly_service.cases import CaseError, _key

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / 'platform-ui'
DESIGN = ROOT / 'design/right-ontime/prototype/assets'
CASE_PATH = re.compile(r'/api/platform/cases/([A-Za-z0-9][A-Za-z0-9_-]{0,63})(?:/(events|analyze|decisions|reviews|execute|assets|model-runs))?')
ASSET_PATH = re.compile(r'/api/platform/cases/([A-Za-z0-9][A-Za-z0-9_-]{0,63})/assets/([A-Za-z0-9][A-Za-z0-9_-]{0,63})(/process)?')
MODEL_PATH = re.compile(r'/api/platform/model-runs/([a-f0-9]{32})')
CSP = "default-src 'self'; script-src 'self'; style-src 'self'; font-src 'self'; img-src 'self' blob: data:; media-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"


def project_model_states(detail):
    """Model transport lifecycle is not a decision or a business effect."""
    if not detail.get('model_jobs'):
        return detail
    job = detail['model_jobs'][-1]
    decisions = detail.get('decisions', [])
    if decisions and job.get('created_at') and decisions[-1].get('created_at', '') > job['created_at']:
        return detail
    revision = job.get('step_index', job.get('revision'))
    if revision != detail['snapshot']['revision']:
        state = 'stale'
    else:
        state = {'queued':'running','running':'running','response_received':'running',
                 'succeeded':'current','failed':'failed','outcome_unknown':'outcome_unknown',
                 'unavailable':'outcome_unknown'}.get(job.get('status'),'not_started')
    detail['states']['analysis'] = state
    return detail


def capabilities(bridge, media=None, channels=None):
    result = {'schema_version':'proofkey-platform-capabilities-v1',
        'execution_mode':'local_sandbox','external_effects':0,
        'authentication':'trusted_local_operator_not_production_auth',
        'models':bridge.profiles(),
        'media': media.capabilities() if media else {key:{'enabled':False,'status':'not_configured'}
                       for key in ('image_analysis','asr','image_generation')},
        'adapters':[
            {'id':'cases','label':'Case records','status':'connected','mode':'local_postgresql'},
            {'id':'delivery','label':'Delivery operations','status':'not_connected','mode':'interface_only'},
            {'id':'scheduling','label':'Scheduling','status':'sandbox','mode':'postgres_sandbox'},
            {'id':'returns','label':'Returns','status':'not_connected','mode':'interface_only'},
            {'id':'messaging','label':'Customer messaging','status':'not_connected','mode':'interface_only'},
            {'id':'operator','label':'Operator inbox','status':'connected','mode':'local_review_queue'}]}
    result['communications'] = {'connectors':channels.capabilities() if channels else [],
                                'provider_connections':False,'outbound_enabled':False}
    if channels is not None:
        result['adapters'][4].update(status='sandbox',mode='local_ingress')
    return result


class PlatformServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class Handler(BaseHTTPRequestHandler):
    server_version = 'ProofKeyLocal/1'
    def log_message(self, *_):
        pass  # Source messages, filenames, tokens and query strings never enter logs.

    def _headers(self, status, mime, length):
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(length))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', CSP)
        self.send_header('Referrer-Policy', 'no-referrer')

    def _send(self, status, payload):
        raw = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(',',':')).encode()
        self._headers(status, 'application/json; charset=utf-8', len(raw)); self.end_headers()
        self.wfile.write(raw)

    def _boundary(self):
        self.connection.settimeout(15)
        port = self.server.server_port
        hosts = {f'127.0.0.1:{port}', f'localhost:{port}'}
        if self.headers.get('Host') not in hosts:
            self._send(403, {'error':{'code':'invalid_host'}}); return False
        origin = self.headers.get('Origin')
        if origin is not None and origin not in {'http://' + host for host in hosts}:
            self._send(403, {'error':{'code':'invalid_origin'}}); return False
        if self.headers.get('Sec-Fetch-Site') in ('cross-site', 'same-site'):
            self._send(403, {'error':{'code':'cross_site_request'}}); return False
        return True

    def _body(self, limit, *, json_body=True):
        if self.headers.get('Transfer-Encoding') is not None:
            raise ValueError('invalid_request')
        values = self.headers.get_all('Content-Length', [])
        if len(values) != 1 or not re.fullmatch(r'[0-9]{1,9}', values[0]):
            raise ValueError('invalid_request')
        length = int(values[0])
        if not 1 <= length <= limit:
            raise ValueError('request_too_large')
        raw = self.rfile.read(length)
        if len(raw) != length:
            raise ValueError('invalid_request')
        if not json_body:
            return raw
        if self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
            raise ValueError('invalid_content_type')
        try:
            value = _json(raw)
        except (json.JSONDecodeError, UnicodeError, RecursionError):
            raise ValueError('invalid_request') from None
        if type(value) is not dict:
            raise ValueError('invalid_request')
        return value

    def _error(self, error):
        code = getattr(error, 'code', error.args[0] if error.args else None)
        if type(code) is not str:
            code = None
        missing = {'case_not_found','revision_not_found','asset_not_found','decision_not_found','model_job_not_found','job_not_found','run_not_found','receipt_not_found'}
        conflict = {'idempotency_conflict','revision_conflict','snapshot_conflict','snapshot_hash_mismatch',
                    'action_blocked','approval_required','decision_stale','stale_decision','model_execution_disabled',
                    'model_credentials_unavailable','model_job_binding_mismatch','asset_processing_disabled',
                    'case_capacity','asset_capacity','budget_exceeded','not_approved','consent_required',
                    'decision_superseded','already_executed','media_budget_exceeded',
                    'event_conflict','media_processing_disabled','media_budget_exhausted',
                    'media_budget_cap_changed','budget_exhausted','budget_cap_changed','queue_full',
                    'delivery_conflict','inbox_capacity','receipt_not_quarantined','communications_not_configured'}
        invalid = {'invalid_case_request','invalid_request','invalid_content_type','request_too_large','duplicate_key',
                   'invalid_model_request','invalid_media','invalid_asset','invalid_asset_type','evidence_not_found',
                   'invalid_platform_request','invalid_review','invalid_action','invalid_slot','invalid_media_request',
                   'asset_too_large','asset_mismatch','invalid_model_job','media_mode_mismatch',
                   'media_too_large','media_dimensions_exceeded','media_duration_exceeded',
                   'invalid_envelope','invalid_identity','envelope_too_large','unknown_connector'}
        if code in missing: status = 404
        elif code in conflict: status = 409
        # Only documented public codes may cross the HTTP boundary. A database
        # or arbitrary ValueError is not a malformed client request.
        elif code in invalid: status = 400
        else: status, code = 503, 'platform_unavailable'
        self._send(status, {'error':{'code':code}})

    def _detail(self, case_id):
        result = self.server.store.detail(case_id)
        # Model jobs remain immutable independent records, never execution authority.
        if result.get('model_jobs'):
            jobs = []
            for link in result['model_jobs']:
                try:
                    jobs.append(self.server.bridge.get(link['job_id']))
                except (ValueError, KeyError):
                    jobs.append(dict(link, status='unavailable'))
            result['model_jobs'] = jobs
        if self.server.media is not None:
            result['media_runs'] = self.server.media.list(case_id)
        if self.server.channels is not None:
            result['communications'] = self.server.channels.provenance(case_id)
        return project_model_states(result)

    def do_GET(self):
        if not self._boundary(): return
        path = urlsplit(self.path).path
        try:
            if path == '/healthz': return self._send(200, {'status':'ok','mode':'local_sandbox'})
            if path == '/api/platform/capabilities': return self._send(200, capabilities(self.server.bridge,self.server.media,self.server.channels))
            if path == '/api/platform/communications':
                channels = self.server.channels
                return self._send(200, {'connectors':channels.capabilities() if channels else [],
                                       'receipts':channels.list() if channels else [],'provider_connections':False})
            if path == '/api/platform/cases':
                summaries = self.server.store.list_cases()
                for summary in summaries:
                    summary['states'] = self._detail(summary['case_id'])['states']
                return self._send(200, {'cases':summaries})
            matched = CASE_PATH.fullmatch(path)
            if matched and not matched[2]: return self._send(200, {'case':self._detail(matched[1])})
            matched = ASSET_PATH.fullmatch(path)
            if matched and not matched[3]:
                meta, raw = self.server.store.get_asset(matched[1],matched[2])
                self._headers(200, meta['mime_type'], len(raw))
                # Do not reflect untrusted filenames into headers.
                self.send_header('Content-Disposition','inline; filename="evidence"')
                self.end_headers(); self.wfile.write(raw); return
            matched = MODEL_PATH.fullmatch(path)
            if matched: return self._send(200,self.server.bridge.get(matched[1]))
            static = {'/':(ASSETS/'index.html','text/html; charset=utf-8'),
                      '/index.html':(ASSETS/'index.html','text/html; charset=utf-8'),
                      '/app.js':(ASSETS/'app.js','text/javascript'),
                      '/session.js':(ASSETS/'session.js','text/javascript'),
                      '/style.css':(ASSETS/'style.css','text/css'),
                      '/tokens.css':(DESIGN/'tokens.css','text/css')}
            if re.fullmatch(r'/brand/forward-(?:paper|forest|symbol-paper|symbol-forest)\.svg',path):
                static[path] = (DESIGN/path.lstrip('/'),'image/svg+xml')
            if re.fullmatch(r'/fonts/(?:Inter|Manrope)\.ttf',path):
                static[path] = (DESIGN/path.lstrip('/'),'font/ttf')
            if path == '/evals/':
                self.send_response(302); self.send_header('Location','http://127.0.0.1:8093/');
                self.send_header('Content-Length','0'); self.send_header('Cache-Control','no-store'); self.end_headers(); return
            if path not in static: return self._send(404, {'error':{'code':'not_found'}})
            target, mime = static[path]
            raw = target.read_bytes(); self._headers(200,mime,len(raw)); self.end_headers(); self.wfile.write(raw)
        except (CaseError, ValueError, KeyError, OSError) as error:
            self._error(error)

    def do_POST(self):
        if not self._boundary(): return
        if self.headers.get('X-ProofKey-Request') != 'platform-v1':
            return self._send(403, {'error':{'code':'missing_request_marker'}})
        try:
            key = self.headers.get('Idempotency-Key'); _key(key)
            path = urlsplit(self.path).path
            if path == '/api/platform/communications/import':
                from tools.dwelly_channels.contracts import MAX_ENVELOPE_BYTES
                if self.server.channels is None: raise ValueError('communications_not_configured')
                body = self._body(MAX_ENVELOPE_BYTES + 1024)
                if set(body) != {'connector_id','envelope'}: raise ValueError('invalid_request')
                receipt = self.server.channels.ingest(body['connector_id'],body['envelope'],source='operator_import')
                return self._send(200, {'receipt':receipt})
            receipt_path = re.fullmatch(r'/api/platform/communications/([a-f0-9]{32})/retry',path)
            if receipt_path:
                if self.server.channels is None: raise ValueError('communications_not_configured')
                if self._body(1024) != {}: raise ValueError('invalid_request')
                return self._send(200, {'receipt':self.server.channels.retry(receipt_path[1])})
            if path == '/api/platform/cases':
                snapshot, created = self.server.store.create(key,self._body(16384))
                return self._send(201 if created else 200, {'case':self._detail(snapshot['case_id'])})
            matched = ASSET_PATH.fullmatch(path)
            if matched and matched[3]:
                body = self._body(16384)
                if self.server.media is None: raise ValueError('asset_processing_disabled')
                return self._send(200, self.server.media.process(matched[1],matched[2],key,body))
            matched = CASE_PATH.fullmatch(path)
            if not matched or not matched[2]: return self._send(404, {'error':{'code':'not_found'}})
            case_id, action = matched.groups()
            if action == 'assets':
                raw = self._body(25*1024*1024, json_body=False)
                descriptor = self.server.store.put_asset(case_id,key,self.headers.get('Content-Type',''),
                    self.headers.get('X-Filename','evidence'),raw)
                return self._send(201, {'asset':descriptor})
            body = self._body(16384)
            if action == 'model-runs': return self._send(202,self.server.bridge.submit(case_id,key,body))
            if action == 'events': self.server.store.append(case_id,key,body)
            else:
                methods = {'analyze':'analyze','decisions':'propose','reviews':'review','execute':'execute'}
                getattr(self.server.store,methods[action])(case_id,key,body)
            return self._send(200, {'case':self._detail(case_id)})
        except (CaseError, ValueError, KeyError, OSError) as error:
            self._error(error)


def create_server(store, *, host='127.0.0.1', port=8095, bridge=None, media=None, channels=None):
    if host != '127.0.0.1' or any(os.environ.get(name) for name in ('K_SERVICE','FUNCTION_TARGET','CLOUD_RUN_JOB')):
        raise ValueError('local_trust_boundary_only')
    server = PlatformServer((host,port),Handler)
    server.store, server.bridge, server.media = store, bridge or ModelBridge(store), media
    server.channels = channels
    return server
