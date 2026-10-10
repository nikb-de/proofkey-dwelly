"""Pinned source replay with an evaluator-only, manually reviewed ledger.

The ledger was read against each visible transcript, not computed from the
source's agent_state or from simulated candidates. It remains unvalidated
development evidence from one logistics family and a separate UI control.
"""
from copy import deepcopy
from datetime import datetime, timezone
import json
import re

from tools.dwelly_analysis import catalog
from tools.dwelly_service.cases import _declaration, _event


_FALLBACK_TIME = '2026-02-03T00:00:00+00:00'
_RUN_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9-]{0,31}')
# Each row: allowed states, allowed actions, exact wait set, completion allowed,
# permitted action targets. No author label is read to construct this ledger.
_EXPECTATIONS = {
    ('case-002', 0): (['unknown'], ['operator_review'], [], False, [None]),
    ('case-002', 1): (['ready'], ['request_information'], [], False, ['recipient']),
    ('case-002', 2): (['ready'], ['request_information'], [], False, ['recipient']),
    ('case-002', 3): (['waiting'], ['wait'], ['recipient'], False, ['recipient']),
    ('case-002', 4): (['ready'], ['propose_forwarding'], [], False, ['address_desk']),
    ('case-002', 5): (['completed'], ['none'], [], True, [None]),
    ('case-002-n4', 0): (['unknown'], ['operator_review'], [], False, [None]),
    ('case-002-n4', 1): (['ready'], ['request_information'], [], False, ['recipient']),
    ('case-002-n4', 2): (['ready'], ['request_information'], [], False, ['recipient']),
    ('case-002-n4', 3): (['waiting'], ['wait'], ['recipient'], False, ['recipient']),
    ('case-002-n4', 4): (['ready'], ['propose_forwarding'], [], False, ['address_desk']),
    ('case-002-n4', 5): (['ready'], ['request_readback'], [], False, ['address_desk']),
    ('case-002-n4', 6): (['waiting'], ['wait'], ['address_desk'], False, ['address_desk']),
    ('case-002-n4', 7): (['completed'], ['none'], [], True, [None]),
    ('minimal', 0): (['unknown'], ['operator_review'], [], False, [None]),
    ('minimal', 1): (['waiting'], ['wait'], ['service'], False, ['service']),
}


def _timestamp(value):
    if value is None:
        return _FALLBACK_TIME
    if value.endswith(' UTC'):
        return datetime.strptime(value, '%Y-%m-%d %H:%M:%S UTC').replace(tzinfo=timezone.utc).isoformat()
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('source_timestamp_not_aware')
    return parsed.astimezone(timezone.utc).isoformat()


def build_case(source_id, step_index, run_id):
    """Return one isolated canonical replay, with references outside the upload."""
    if type(run_id) is not str or _RUN_ID.fullmatch(run_id) is None:
        raise ValueError('invalid_run_id')
    if type(step_index) is not int or (source_id, step_index) not in _EXPECTATIONS:
        raise ValueError('invalid_source_cutoff')
    row = next(row for row in catalog.load_catalog() if row['id'] == source_id)
    document = catalog.get_document(source_id)
    state = document['steps'][step_index - 1]['state_after'] if step_index else document['initial_state']
    actors = [{'id': key, 'name': value['name'], 'role': value['role']} for key, value in state['actors'].items()]
    participants = [actor['id'] for actor in actors]
    operator = state['our_actor_id']
    customer = state.get('client_actor_id')
    synthetic = []
    if not customer or customer == operator:
        if source_id != 'minimal':
            raise ValueError('missing_source_customer')
        customer = 'e2e-observer'
        participants.append(customer)
        synthetic = [{'id': customer, 'reason': 'Source control has no distinct customer.'}]
    case_id = f'e2e-{run_id}-{source_id}-s{step_index}'
    declaration = {'case_id': case_id, 'links': {'order_id': f'e2e-{source_id}', 'customer_id': customer,
                                               'operator_id': operator},
                   'participants': participants, 'language': 'en'}
    _declaration(declaration)
    messages = state.get('messages', [])
    times = [_timestamp(message.get('timestamp')) for message in messages if message.get('timestamp')]
    events = [{'event_id': 'source-context', 'occurred_at': min(times) if times else _FALLBACK_TIME,
               'channel': 'internal', 'sender_id': operator, 'recipient_ids': [], 'kind': 'message',
               'text': json.dumps({'goal': document['initial_state']['goal'], 'actors': actors}, ensure_ascii=False),
               'media': None}]
    mapping = []
    for message in messages:
        raw_channel = message.get('channel', 'internal')
        normalized = raw_channel.lower()
        channel = normalized if normalized in {'chat', 'email', 'phone', 'internal'} else 'internal'
        event = {'event_id': message['event_id'], 'occurred_at': _timestamp(message.get('timestamp')),
                 'channel': channel, 'sender_id': message['from_actor'], 'recipient_ids': [message['to_actor']],
                 'kind': 'message', 'text': message['body'] if 'body' in message else message['body_ru'], 'media': None}
        _event(event, participants)
        events.append(event)
        mapping.append({'source_event_id': message['event_id'], 'event_id': event['event_id'],
                        'source_channel': raw_channel, 'canonical_channel': channel,
                        'timestamp_fallback': not bool(message.get('timestamp')),
                        'body_source': 'body' if 'body' in message else 'body_ru'})
    _event(events[0], participants)
    states, actions, waiting, completion, targets = deepcopy(_EXPECTATIONS[source_id, step_index])
    return {'case_id': case_id,
            'source': {'source_id': source_id, 'step_index': step_index, 'family_id': row['family_id'],
                       'source_sha256': row['source_sha256'], 'qualification': row['qualification'],
                       'split': row['split'], 'kind': row['kind'], 'event_mapping': mapping,
                       'synthetic_participants': synthetic,
                       'transformation': 'Visible source messages plus internal goal/actor context; unsupported channels become internal; missing timestamps use fixed fallback.'},
            'declaration': declaration, 'events': events,
            'expectation': {'allowed_states': states, 'allowed_actions': actions, 'waiting_for': waiting,
                            'completion_allowed': completion, 'action_targets': targets,
                            'qualification': 'author_labels_unvalidated'}}


def case_plans(run_id):
    """All sixteen pinned source cutoffs in stable catalog order."""
    return [build_case(source, step, run_id) for source, step in _EXPECTATIONS]
