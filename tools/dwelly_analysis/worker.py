"""Local opt-in model worker. Durable dispatch markers forbid automatic retries."""
import copy
import hashlib
import json
import re
import threading

from . import evaluation, model


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def public_job(row):
    spec, result = row['spec'], row['result'] or {}
    receipt = result.get('receipt')
    if receipt is None and row['response'] is not None:
        try:
            receipt = model.receipt(row['response'], spec['profile'])
        except ValueError:
            pass
    error = row['error']
    return {'schema_version': 'proofkey-model-job-v1', 'run_id': row['job_id'],
            'status': row['status'], 'case_id': spec['input']['case_id'],
            'step_index': spec['input']['step_index'], 'input_hash': spec['input']['input_hash'],
            'mode': 'model', 'model_profile_id': spec['profile']['id'],
            'input': spec['input'], 'reference': spec['reference'], 'source': spec['source'],
            'candidate': result.get('candidate'), 'evaluation': result.get('evaluation'),
            'receipt': receipt,
            'error': None if error is None else {'phase': 'validation' if row['response'] is not None else 'dispatch', 'code': error},
            'created_at': row['created_at'], 'started_at': row['started_at'], 'finished_at': row['finished_at'],
            'transaction': {'idempotency_key': row['idempotency_key'], 'attempt_id': row['attempt_id'],
                'dispatch_attempts': row['dispatch_attempts'], 'automatic_retries': 0, 'operational_effects': 0,
                'reserved_usd': row['reserved_usd'], 'budget_scope': row['budget_scope'],
                'prompt_hash': spec['prompt_hash'], 'profile_hash': spec['profile_hash']}}


class ModelRuntime:
    def __init__(self, store, settings, scope, *, allow_live=False):
        self.store = store
        self.settings = model._settings(settings)
        if type(scope) is not str or re.fullmatch(r'[A-Za-z0-9._:-]{1,128}', scope) is None:
            raise ValueError('invalid_budget_scope')
        self.scope, self.enabled = scope, allow_live is True
        self.stop_event = threading.Event()
        self.threads = []
        self.last_error = None

    def profiles(self):
        return {'enabled': self.enabled, 'profiles': model.public_profiles(self.settings)}

    def submit(self, selector, key, selected):
        if not self.enabled or self.stop_event.is_set():
            raise ValueError('model_execution_disabled')
        required = {'case_id', 'step_index', 'expected_input_hash', 'mode', 'model_profile_id'}
        if (type(selector) is not dict or set(selector) != required or selector['mode'] != 'model'
                or type(selector['case_id']) is not str or type(selector['step_index']) is not int
                or type(selector['model_profile_id']) is not str or type(selector['expected_input_hash']) is not str
                or re.fullmatch(r'[a-f0-9]{64}', selector['expected_input_hash']) is None):
            raise ValueError('invalid_model_request')
        evidence = selected['input']
        if (selector['case_id'] != evidence['case_id'] or selector['step_index'] != evidence['step_index']
                or selector['expected_input_hash'] != evidence['input_hash']):
            raise ValueError('input_hash_conflict')
        existing = self.store.get_by_key(key)
        if existing is not None:
            frozen = existing['spec']
            if (existing['budget_scope'] != self.scope or frozen['profile']['id'] != selector['model_profile_id']
                    or any(frozen['input'][field] != evidence[field] for field in ('case_id', 'step_index', 'input_hash'))):
                raise ValueError('idempotency_conflict')
            return public_job(existing), False
        profile = next((p for p in self.settings['profiles'] if p['id'] == selector['model_profile_id']), None)
        if profile is None:
            raise ValueError('unknown_model_profile')
        availability = next(p for p in self.profiles()['profiles'] if p['id'] == profile['id'])
        if not availability['available']:
            raise ValueError('model_credentials_unavailable')
        system, prompt = model.prepare(evidence)
        settings = {k: self.settings[k] for k in ('max_output_tokens', 'timeout_seconds')}
        spec = copy.deepcopy(dict(selected, profile=profile, settings=settings,
                     profile_hash=digest(profile), prompt_hash=digest({'system': system, 'prompt': prompt}),
                     budget_key=profile['config']['provider'] + ':' + profile['config']['model']))
        reservation = model.reservation(evidence, profile, settings['max_output_tokens'])
        row, created = self.store.submit(key, spec, reservation, self.settings['budget_per_model_usd'], self.scope)
        return public_job(row), created

    def get(self, job_id):
        return public_job(self.store.get(job_id))

    def work_once(self):
        if not self.enabled or self.stop_event.is_set():
            return False
        # Socket timeout is not a wall-clock guarantee. Expired writes are fenced;
        # this generous lease reduces false unknowns but does not claim exactly-once.
        lease = 660  # Also covers frozen jobs created with the maximum allowed timeout (600s).
        row = self.store.claim_next(lease_seconds=lease, max_running=3, per_profile=1)
        if row is None:
            return False
        job_id, token, spec = row['job_id'], row['lease_token'], row['spec']
        response = row['response']
        if response is None:
            # Validate frozen artifacts before any external call. A newer process
            # must not silently execute a changed prompt for an older queued job.
            try:
                system, prompt = model.prepare(spec['input'])
                if (digest({'system': system, 'prompt': prompt}) != spec['prompt_hash']
                        or digest(spec['profile']) != spec['profile_hash']):
                    raise ValueError('frozen_spec_mismatch')
            except (ValueError, KeyError, TypeError):
                self.store.finish(job_id, token, error='frozen_spec_mismatch', status='failed')
                return True
            if self.stop_event.is_set():
                self.store.finish(job_id, token, error='worker_stopped', status='failed')
                return True
            if not self.store.mark_dispatched(job_id, token):
                return True
            if self.stop_event.is_set():
                self.store.finish(job_id, token, error='worker_stopped', status='failed')
                return True
            try:
                response = model.request(spec['input'], spec['profile'],
                    max_output_tokens=spec['settings']['max_output_tokens'], timeout=spec['settings']['timeout_seconds'])
            except Exception as error:
                raw = str(error) if isinstance(error, ValueError) else ''
                known = {'timeout', 'network_error', 'response_too_large', 'invalid_response', 'incomplete_response',
                         'missing_text', 'invalid_model_response', 'provider_error', 'request_failed',
                         'missing_api_key', 'invalid_api_key', 'missing_workspace_id', 'invalid_workspace_id', 'invalid_config'}
                code = raw if raw in known or re.fullmatch(r'http_[0-9]{3}', raw) else 'request_failed'
                status = 'failed' if code in {'missing_api_key', 'invalid_api_key', 'missing_workspace_id', 'invalid_workspace_id', 'invalid_config'} or re.fullmatch(r'http_4[0-9]{2}', code) else 'outcome_unknown'
                self.store.finish(job_id, token, error=code, status=status)
                return True
            if not self.store.record_response(job_id, token, response):
                return True  # Lease lost: never publish a stale result or resend.
        try:
            candidate = model.parse(spec['input'], response)
            receipt = model.receipt(response, spec['profile'])
            compared = evaluation.compare(candidate, spec['reference'])
        except (ValueError, KeyError, TypeError, RecursionError):
            self.store.finish(job_id, token, error='invalid_model_output', status='failed')
            return True
        self.store.finish(job_id, token, result={'candidate': candidate, 'receipt': receipt, 'evaluation': compared})
        return True

    def _loop(self):
        while not self.stop_event.is_set():
            try:
                active = self.work_once()
                self.last_error = None
            except Exception:
                # Storage failures leave durable state for recovery; never leak DSN
                # or provider errors and never retry an already dispatched call.
                self.last_error = 'model_worker_unavailable'
                active = False
            if not active:
                self.stop_event.wait(0.5)

    def start(self):
        if self.enabled and not self.threads:
            for index in range(3):
                thread = threading.Thread(target=self._loop, name='model-worker-' + str(index), daemon=True)
                self.threads.append(thread)
                thread.start()

    def close(self):
        self.stop_event.set()
        for thread in self.threads:
            thread.join(timeout=0.2)
        # In-flight calls may still finish. Do not invalidate their store. A dead
        # process is recovered by leases, never a second automatic dispatch.
