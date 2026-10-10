"""Loopback analysis API; paid model jobs require explicit server-side opt-in."""
import copy
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import tempfile
import threading
from urllib.parse import urlsplit
import uuid

from . import baseline, catalog, evaluation, widget
from tools.dwelly_service.dataset_export import _write_exclusive

MAX_RUNS = 256
MAX_REQUEST_BYTES = 16384
MAX_RUN_BYTES = 8 * 1024 * 1024
ASSETS = Path(__file__).resolve().parents[2] / 'case-state-widget'
STATIC = {'/': ('analysis.html', 'text/html'), '/source-viewer': ('index.html', 'text/html'),
          '/analysis.js': ('analysis.js', 'text/javascript'), '/analysis.css': ('analysis.css', 'text/css'),
          '/viewer.js': ('viewer.js', 'text/javascript'), '/viewer.css': ('viewer.css', 'text/css'),
          '/app.js': ('app.js', 'text/javascript'), '/case-002.json': ('case-002.json', 'application/json')}
CASE = re.compile(r'/api/cases/([a-z0-9-]+)(?:/steps/(0|[1-9][0-9]*))?')
RUN = re.compile(r'/api/runs/([a-f0-9]{32})')
MODEL_RUN = re.compile(r'/api/model-runs/([a-f0-9]{32})')


def _encoded(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def _hash(value):
    return hashlib.sha256(_encoded(value)).hexdigest()


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate_key')
        result[key] = value
    return result


def _json(raw):
    def invalid(_):
        raise ValueError('nonfinite_json')
    return json.loads(raw, object_pairs_hook=_pairs, parse_constant=invalid)


class RunStore:
    def __init__(self, directory):
        self.directory = Path(directory)
        if self.directory.is_symlink():
            raise ValueError('invalid_run_directory')
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.lock = threading.Lock()

    def save(self, record):
        with self.lock:
            if sum(1 for p in self.directory.iterdir() if re.fullmatch(r'[a-f0-9]{32}\.json', p.name)) >= MAX_RUNS:
                raise OverflowError('run_capacity')
            result = copy.deepcopy(record)
            result['run_id'] = uuid.uuid4().hex
            result['record_hash'] = _hash(result)
            if len(_encoded(result)) > MAX_RUN_BYTES:
                raise ValueError('run_too_large')
            _write_exclusive(self.directory / (result['run_id'] + '.json'), result)
            return result

    def get(self, run_id):
        if not re.fullmatch(r'[a-f0-9]{32}', run_id):
            raise FileNotFoundError('run_not_found')
        path = self.directory / (run_id + '.json')
        descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
        try:
            with os.fdopen(descriptor, 'rb') as stream:
                raw = stream.read(MAX_RUN_BYTES + 1)
        except BaseException:
            raise
        if len(raw) > MAX_RUN_BYTES:
            raise ValueError('invalid_run_record')
        record = _json(raw)
        if type(record) is not dict:
            raise ValueError('invalid_run_record')
        expected_hash = record.get('record_hash')
        unhashed = {k: v for k, v in record.items() if k != 'record_hash'}
        if (record.get('run_id') != run_id or expected_hash != _hash(unhashed)
                or record.get('schema_version') != 'proofkey-analysis-run-v1'
                or record.get('mode') != 'offline' or record.get('live_calls') != 0
                or record.get('operational_effects') != 0):
            raise ValueError('invalid_run_record')
        return record


def step_record(case_id, index):
    item = next((item for item in catalog.load_catalog() if item['id'] == case_id), None)
    if item is None:
        raise KeyError('case_not_found')
    document = catalog.get_document(case_id)
    if type(index) is not int or not 0 <= index <= len(document['steps']):
        raise IndexError('step_not_found')
    projection = widget.project(document, index, case_id)
    return {'input': projection, 'reference': widget.reference(document, index, projection),
            'source': {key: item[key] for key in ('source_sha256', 'source_commit', 'family_id', 'qualification')}}


def make_run(selector, store):
    if (type(selector) is not dict or set(selector) != {'case_id', 'step_index', 'expected_input_hash', 'mode'}
            or selector['mode'] != 'offline' or type(selector['case_id']) is not str
            or type(selector['step_index']) is not int or selector['step_index'] < 0
            or type(selector['expected_input_hash']) is not str
            or re.fullmatch(r'[a-f0-9]{64}', selector['expected_input_hash']) is None):
        raise ValueError('invalid_run_request')
    selected = step_record(selector['case_id'], selector['step_index'])
    projection = selected['input']
    if selector['expected_input_hash'] != projection['input_hash']:
        raise RuntimeError('input_hash_conflict')
    # Inference receives the closed evidence projection only, never the document/reference.
    candidate = baseline.analyze(copy.deepcopy(projection))
    reference = selected['reference']
    compared = evaluation.compare(candidate, reference)
    return store.save({'schema_version': 'proofkey-analysis-run-v1', 'case_id': selector['case_id'],
        'step_index': selector['step_index'], 'mode': 'offline', 'input_hash': projection['input_hash'],
        'input': projection, 'candidate': candidate, 'reference': reference, 'evaluation': compared,
        'source': selected['source'], 'created_at': datetime.now(timezone.utc).isoformat(),
        'pipeline_version': 'case-state-analysis/1.0', 'live_calls': 0, 'operational_effects': 0})


def export_dataset(output):
    """Separate evidence and references; these development drafts are not training gold."""
    output = Path(output)
    prepared = []
    for item in catalog.load_catalog():
        for index in range(item['steps'] + 1):
            selected = step_record(item['id'], index)
            identifier = item['id'] + '-step-' + str(index)
            exclusions = ['author_labels_unvalidated']
            if index == 0:
                exclusions.append('context_only')
            if item['id'] == 'minimal':
                exclusions.append('ui_fixture')
            prepared.append((identifier, selected, {'case_id': item['id'], 'step_index': index,
                'family_id': item['family_id'], 'split': 'development', 'eligible_for_training': False,
                'qualification': item['qualification'], 'exclusions': exclusions,
                'input_path': 'inputs/' + identifier + '.json',
                'reference_path': 'references/' + identifier + '.json',
                'input_hash': selected['input']['input_hash'], 'source': selected['source']}))
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    (output / 'inputs').mkdir(mode=0o700)
    (output / 'references').mkdir(mode=0o700)
    rows = []
    for _, selected, row in prepared:
        for field, value in [('input_path', selected['input']), ('reference_path', selected['reference'])]:
            path = output / row[field]
            _write_exclusive(path, value)
            row[field.replace('_path', '_file_sha256')] = hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append(row)
    # Write the manifest last so an interrupted export cannot look complete.
    manifest = b''.join(_encoded(row) + b'\n' for row in rows)
    descriptor = os.open(output / 'manifest.jsonl', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(manifest)
        stream.flush()
        os.fsync(stream.fileno())
    summary = {'schema_version': 'proofkey-step-dataset-v1', 'snapshots': len(rows),
               'split': 'development', 'eligible_for_training': 0, 'complete': True}
    _write_exclusive(output / 'summary.json', summary)
    return summary


class AnalysisServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def server_close(self):
        if getattr(self, 'model_runtime', None):
            self.model_runtime.close()
        super().server_close()


class Handler(BaseHTTPRequestHandler):
    server_version = 'ProofKeyAnalysis/1'

    def log_message(self, *_):
        pass

    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def send_body(self, code, value, content_type='application/json', *, raw=False):
        body = value if raw else _encoded(value) if content_type == 'application/json' else value
        self.send_response(code)
        self.send_header('Content-Type', content_type + '; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
        self.end_headers()
        self.wfile.write(body)

    def guard(self, write=False):
        hosts = self.headers.get_all('Host', [])
        port = self.server.server_address[1]
        allowed = {'127.0.0.1:' + str(port), 'localhost:' + str(port)}
        origins = self.headers.get_all('Origin', [])
        if (len(hosts) != 1 or hosts[0].lower() not in allowed
                or len(origins) > 1 or (origins and origins[0] != 'http://' + hosts[0].lower())
                or self.headers.get('Sec-Fetch-Site') == 'cross-site'
                or (write and self.headers.get_all('X-ProofKey-Request', []) != ['analysis-v1'])):
            self.send_body(403, {'error': 'request_denied'})
            return False
        return True

    def do_GET(self):
        if not self.guard():
            return
        path = urlsplit(self.path)
        if path.query or path.fragment:
            return self.send_body(404, {'error': 'not_found'})
        try:
            if path.path == '/api/capabilities':
                return self.send_body(200, {'mode': 'offline', 'live_calls': 0, 'operational_effects': 0,
                    'model_execution': bool(self.server.model_runtime and self.server.model_runtime.enabled),
                    'cloud_connected': False, 'training_eligible': False,
                    'run_storage': 'local_explicit_directory' if self.server.persistent else 'temporary_session',
                    'max_runs': MAX_RUNS})
            if path.path == '/api/model-profiles':
                return self.send_body(200, self.server.model_runtime.profiles() if self.server.model_runtime else {'enabled': False, 'profiles': []})
            match = MODEL_RUN.fullmatch(path.path)
            if match:
                if not self.server.model_runtime:
                    return self.send_body(403, {'error': 'model_execution_disabled'})
                return self.send_body(200, self.server.model_runtime.get(match[1]))
            if path.path == '/api/catalog':
                return self.send_body(200, {'cases': catalog.load_catalog()})
            match = CASE.fullmatch(path.path)
            if match:
                if match[2] is not None:
                    return self.send_body(200, step_record(match[1], int(match[2])))
                if not any(item['id'] == match[1] for item in catalog.load_catalog()):
                    raise KeyError('case_not_found')
                return self.send_body(200, {'case_id': match[1], 'document': catalog.get_document(match[1])})
            match = RUN.fullmatch(path.path)
            if match:
                return self.send_body(200, self.server.runs.get(match[1]))
            if path.path in STATIC:
                filename, mime = STATIC[path.path]
                return self.send_body(200, (ASSETS / filename).read_bytes(), mime, raw=True)
            self.send_body(404, {'error': 'not_found'})
        except (KeyError, IndexError, FileNotFoundError):
            self.send_body(404, {'error': 'not_found'})
        except (ValueError, OSError, RecursionError, TypeError):
            self.send_body(503, {'error': 'analysis_data_unavailable'})

    def do_POST(self):
        if not self.guard(write=True):
            return
        if self.path not in {'/api/runs', '/api/model-runs'}:
            return self.send_body(404, {'error': 'not_found'})
        if self.headers.get('Transfer-Encoding') or len(self.headers.get_all('Content-Length', [])) != 1:
            return self.send_body(400, {'error': 'invalid_request'})
        try:
            length = int(self.headers['Content-Length'])
            if not 0 < length <= MAX_REQUEST_BYTES or self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                return self.send_body(400, {'error': 'invalid_request'})
            raw = self.rfile.read(length)
            if len(raw) != length:
                return self.send_body(400, {'error': 'invalid_request'})
            value = _json(raw)
            if self.path == '/api/model-runs':
                runtime = self.server.model_runtime
                if not runtime or not runtime.enabled:
                    return self.send_body(403, {'error': 'model_execution_disabled'})
                keys = self.headers.get_all('Idempotency-Key', [])
                if len(keys) != 1 or re.fullmatch(r'[A-Za-z0-9._:-]{1,128}', keys[0]) is None:
                    return self.send_body(400, {'error': 'invalid_idempotency_key'})
                if type(value) is not dict or type(value.get('case_id')) is not str or type(value.get('step_index')) is not int:
                    return self.send_body(400, {'error': 'invalid_model_request'})
                selected = step_record(value['case_id'], value['step_index'])
                result, created = runtime.submit(value, keys[0], selected)
                return self.send_body(202 if created else 200, result)
            return self.send_body(201, make_run(value, self.server.runs))
        except RuntimeError:
            self.send_body(409, {'error': 'input_hash_conflict'})
        except OverflowError:
            self.send_body(429, {'error': 'run_capacity'})
        except (KeyError, IndexError):
            self.send_body(404, {'error': 'not_found'})
        except (ValueError, TypeError, RecursionError) as error:
            if self.path == '/api/model-runs':
                code = str(error)
                allowed = {'input_hash_conflict': 409, 'idempotency_conflict': 409, 'model_execution_disabled': 403,
                           'model_credentials_unavailable': 503, 'unknown_model_profile': 400, 'invalid_model_request': 400,
                           'invalid_model_job': 400, 'budget_exhausted': 429, 'budget_cap_changed': 409,
                           'queue_full': 429, 'model_storage_error': 503, 'model_prompt_too_large': 413}
                return self.send_body(allowed.get(code, 400), {'error': code if code in allowed else 'invalid_model_request'})
            self.send_body(400, {'error': 'invalid_run_request'})
        except OSError:
            self.send_body(503, {'error': 'run_storage_unavailable'})


def create_server(*, port=8093, runs_dir=None, model_runtime=None, start_workers=True):
    if 'K_SERVICE' in os.environ or 'CLOUD_RUN_JOB' in os.environ:
        raise ValueError('managed_cloud_unsupported')
    if type(port) is not int or not 0 <= port <= 65535:
        raise ValueError('invalid_port')
    for item in catalog.load_catalog():
        catalog.get_document(item['id'])
    app = AnalysisServer(('127.0.0.1', port), Handler)
    app.model_runtime = model_runtime
    app.persistent = runs_dir is not None
    app.runs = RunStore(runs_dir if runs_dir is not None else tempfile.mkdtemp(prefix='proofkey-analysis-'))
    if model_runtime and start_workers:
        model_runtime.start()
    return app
