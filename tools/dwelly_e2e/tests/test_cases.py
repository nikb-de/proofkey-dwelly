"""Replay tests catch future leakage, label injection, and source distortion."""
from copy import deepcopy
from datetime import datetime, timezone
import importlib
import json
import re

import pytest

from tools.dwelly_analysis import catalog
from tools.dwelly_service.cases import _declaration, _event


def cases():
    return importlib.import_module('tools.dwelly_e2e.cases')


def test_all_sixteen_cutoffs_have_distinct_valid_ids_and_pinned_hashes():
    plans = cases().case_plans('canary')
    assert len(plans) == len({p['case_id'] for p in plans}) == 16
    assert [(p['source']['source_id'], p['source']['step_index']) for p in plans] == [
        *[('case-002', i) for i in range(6)],
        *[('case-002-n4', i) for i in range(8)], ('minimal', 0), ('minimal', 1)]
    hashes = {'case-002': 'e30276ee9c0d62475296084474f1357b6c3d1905c0dab9894d8ed1c9577fd5a7',
              'case-002-n4': 'c6c028af21fa456f8505ea22feece25525a95beaf5aca57e28074c14507eedf5',
              'minimal': '7371c3816502b3a347c6b83b9b1ebc8aa471ce355d2f43558285ddca29ec43c2'}
    for p in plans:
        assert re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', p['case_id'])
        assert p['source']['source_sha256'] == hashes[p['source']['source_id']]
        _declaration(p['declaration'])
        for event in p['events']:
            _event(event, p['declaration']['participants'])


def test_context_preserves_goal_and_only_visible_actor_names_and_roles():
    for p in cases().case_plans('context'):
        d = catalog.get_document(p['source']['source_id'])
        i = p['source']['step_index']
        state = d['steps'][i - 1]['state_after'] if i else d['initial_state']
        context = json.loads(p['events'][0]['text'])
        assert set(context) == {'goal', 'actors'}
        assert context['goal'] == d['initial_state']['goal']
        assert context['actors'] == [{'id': k, 'name': v['name'], 'role': v['role']}
                                    for k, v in state['actors'].items()]
        assert p['events'][0]['event_id'] == 'source-context'
        assert p['events'][0]['channel'] == 'internal'
        assert p['events'][0]['occurred_at'] == ('2026-02-03T00:00:00+00:00' if not state['messages']
                                                   or p['source']['source_id'] == 'minimal'
                                                   else '2026-02-03T09:00:00+00:00')
        upload = json.dumps({'declaration': p['declaration'], 'events': p['events']})
        for excluded in ['agent_state', 'success_criteria', 'next_step', 'evidence_event_ids', 'source_sha256', 'completion_allowed']:
            assert excluded not in upload
    early = cases().build_case('case-002-n4', 4, 'canary')
    assert 'correction_form' not in early['declaration']['participants']
    assert 'correction_form' not in early['events'][0]['text']
    assert 'address_desk' not in cases().build_case('case-002', 0, 'canary')['declaration']['participants']
    assert 'correction_form' in cases().build_case('case-002-n4', 5, 'canary')['declaration']['participants']


def test_source_message_ids_text_direction_channels_and_timestamps_are_preserved():
    for p in cases().case_plans('fidelity'):
        d = catalog.get_document(p['source']['source_id'])
        i = p['source']['step_index']
        messages = (d['steps'][i - 1]['state_after'] if i else d['initial_state'])['messages']
        assert len(p['events']) == len(messages) + 1
        for raw, event, mapping in zip(messages, p['events'][1:], p['source']['event_mapping']):
            assert event['event_id'] == raw['event_id']
            assert event['text'] == raw.get('body', raw.get('body_ru'))
            assert event['sender_id'] == raw['from_actor']
            assert event['recipient_ids'] == [raw['to_actor']]
            assert mapping['source_channel'] == raw['channel']
            assert event['channel'] == ('email' if raw['channel'] == 'Email' else 'internal')
            expected = (datetime.strptime(raw['timestamp'], '%Y-%m-%d %H:%M:%S UTC').replace(tzinfo=timezone.utc).isoformat()
                        if 'timestamp' in raw else '2026-02-03T00:00:00+00:00')
            assert event['occurred_at'] == expected


def test_observer_is_explicit_and_only_for_control_without_customer():
    for p in cases().case_plans('observer'):
        if p['source']['source_id'] == 'minimal':
            assert p['declaration']['links']['customer_id'] == 'e2e-observer'
            assert p['source']['synthetic_participants'] == [{'id': 'e2e-observer', 'reason': 'Source control has no distinct customer.'}]
        else:
            assert 'e2e-observer' not in p['declaration']['participants']
            assert p['source']['synthetic_participants'] == []


@pytest.mark.parametrize('run_id', ['', '-a', 'a_b', 'a/b', 'a b', 'a' * 33, None, 1])
def test_malformed_run_identifiers_are_rejected(run_id):
    with pytest.raises(ValueError, match='invalid_run_id'):
        cases().case_plans(run_id)


@pytest.mark.parametrize('source_id,step', [('missing', 0), ('case-002', -1), ('case-002', 6), ('case-002', True), ('minimal', 2)])
def test_unknown_sources_and_cutoffs_are_rejected(source_id, step):
    with pytest.raises(ValueError):
        cases().build_case(source_id, step, 'canary')


def test_handwritten_expectations_match_each_observable_checkpoint():
    expected = [
        ('unknown', 'operator_review', [], False),
        ('ready', 'request_information', [], False),
        ('ready', 'request_information', [], False),
        ('waiting', 'wait', ['recipient'], False),
        ('ready', 'propose_forwarding', [], False),
        ('completed', 'none', [], True),
        ('unknown', 'operator_review', [], False),
        ('ready', 'request_information', [], False),
        ('ready', 'request_information', [], False),
        ('waiting', 'wait', ['recipient'], False),
        ('ready', 'propose_forwarding', [], False),
        ('ready', 'request_readback', [], False),
        ('waiting', 'wait', ['address_desk'], False),
        ('completed', 'none', [], True),
        ('unknown', 'operator_review', [], False),
        ('waiting', 'wait', ['service'], False),
    ]
    for p, (state, action, wait, completion) in zip(cases().case_plans('expected'), expected):
        e = p['expectation']
        assert e['allowed_states'] == [state]
        assert e['allowed_actions'] == [action]
        assert e['waiting_for'] == wait
        assert e['completion_allowed'] is completion
        assert e['qualification'] == 'author_labels_unvalidated'
    first = cases().build_case('case-002', 0, 'expected')
    first['expectation']['allowed_states'].append('completed')
    assert cases().build_case('case-002', 0, 'expected')['expectation']['allowed_states'] == ['unknown']
