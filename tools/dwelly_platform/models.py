"""Bridge canonical case evidence to the opt-in durable model worker."""
import json
import re

from tools.dwelly_analysis import widget


def project_snapshot(snapshot):
    """Project visible evidence only; declared identities never grant authority."""
    operator = snapshot['links']['operator_id']
    result = {
        'schema_version': widget.INPUT_SCHEMA,
        'case_id': snapshot['case_id'], 'step_index': snapshot['revision'],
        'cutoff_event_id': snapshot['events'][-1]['event_id'] if snapshot['events'] else None,
        'goal': 'Review the available case evidence and propose the next coordination step.',
        'our_actor_id': operator,
        'actors': [{'id': participant, 'name': participant, 'role': 'declared participant'}
                   for participant in snapshot['participants']],
        'messages': [],
    }
    for event in snapshot['events']:
        recipients = event['recipient_ids']
        body = event['text'] or ''
        if event['kind'] != 'message':
            media = event['media']
            body += ('\n[Media content unprocessed; no image interpretation or audio transcription. '
                     'kind=' + event['kind'] + '; asset_id=' + media['asset_id'] +
                     '; mime_type=' + media['mime_type'] + ']')
        # The legacy input has one recipient slot. Preserve the full source list
        # in evidence text, including the absence of recipients, without creating
        # additional messages or changing the canonical event ID.
        if len(recipients) != 1:
            body += '\n[Declared recipient_ids: ' + json.dumps(recipients) + ']'
        result['messages'].append({
            'event_id': event['event_id'], 'from_actor': event['sender_id'],
            'to_actor': recipients[0] if recipients else operator,
            'body': body, 'body_source': 'body', 'timestamp': event['occurred_at'],
            'channel': event['channel'],
        })
    result['input_hash'] = widget.canonical_hash(result)
    widget.validate_input(result)
    return result


class ModelBridge:
    def __init__(self, store, runtime=None):
        self.store = store
        self.runtime = runtime

    def profiles(self):
        return self.runtime.profiles() if self.runtime is not None else {'enabled': False, 'profiles': []}

    def _runtime(self):
        if self.runtime is None:
            raise ValueError('model_execution_disabled')
        return self.runtime

    def _bound_snapshot(self, job):
        source = job.get('source')
        if (type(source) is not dict or source.get('kind') != 'platform_case'
                or type(source.get('revision')) is not int
                or source['revision'] < 0 or source.get('case_id') != job.get('case_id')):
            raise ValueError('model_job_binding_mismatch')
        snapshot = self.store.get(source['case_id'], source['revision'])
        if (source.get('snapshot_hash') != snapshot['snapshot_hash']
                or job.get('input') != project_snapshot(snapshot)
                or job.get('reference') is not None):
            raise ValueError('model_job_binding_mismatch')
        return snapshot

    def submit(self, case_id, key, body):
        runtime = self._runtime()
        if (type(body) is not dict
                or set(body) != {'expected_revision', 'snapshot_hash', 'model_profile_id'}
                or type(body['expected_revision']) is not int or body['expected_revision'] < 0
                or type(body['snapshot_hash']) is not str
                or re.fullmatch(r'[a-f0-9]{64}', body['snapshot_hash']) is None
                or type(body['model_profile_id']) is not str
                or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', body['model_profile_id']) is None):
            raise ValueError('invalid_model_request')
        snapshot = self.store.get(case_id, body['expected_revision'])
        if snapshot['snapshot_hash'] != body['snapshot_hash']:
            raise ValueError('snapshot_hash_mismatch')
        evidence = project_snapshot(snapshot)
        selected = {'input': evidence, 'reference': None, 'source': {
            'kind': 'platform_case', 'case_id': case_id, 'revision': snapshot['revision'],
            'snapshot_hash': snapshot['snapshot_hash']}}
        selector = {'case_id': case_id, 'step_index': snapshot['revision'], 'mode': 'model',
                    'expected_input_hash': evidence['input_hash'],
                    'model_profile_id': body['model_profile_id']}
        job_store = getattr(runtime, 'store', None)
        existing = job_store.get_by_key(key) if job_store is not None else None
        if existing is not None:
            frozen = existing['spec']
            if (frozen['input'] != evidence or frozen['source'] != selected['source']
                    or frozen['reference'] is not None or frozen['profile']['id'] != body['model_profile_id']
                    or existing.get('budget_scope') != getattr(runtime, 'scope', None)):
                raise ValueError('idempotency_conflict')
            # Historical replay is read-only: it cannot create a replacement
            # job if the original row disappears or credentials are removed.
            job = runtime.get(existing['job_id'])
        else:
            job, _created = self.store.admit_model(case_id, snapshot['revision'], snapshot['snapshot_hash'],
                                                   lambda: runtime.submit(selector, key, selected))
        bound = self._bound_snapshot(job)
        if bound['case_id'] != case_id or bound['snapshot_hash'] != snapshot['snapshot_hash']:
            raise ValueError('model_job_binding_mismatch')
        # A lost acknowledgement can leave a durable job without a case link.
        # Replaying admission returns that same job and repairs its history link.
        self.store.link_model(case_id, snapshot['revision'], snapshot['snapshot_hash'], job['run_id'])
        return job

    def get(self, job_id):
        job = self._runtime().get(job_id)
        self._bound_snapshot(job)
        return job

    def get_for_coordination(self, job_id):
        """Fetch advisory data for validation in the caller's case transaction.

        Coordination validates the entire frozen input and candidate against
        its locked snapshot. A second case-store read here would borrow another
        connection and could starve a single-connection or busy case pool.
        This method neither dispatches a model nor grants execution authority.
        """
        return self._runtime().get(job_id)
