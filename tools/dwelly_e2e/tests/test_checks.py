"""Independent candidates and adversarial mutations exercise real evaluators."""
from copy import deepcopy
import importlib
import json
from pathlib import Path

import pytest

from tools.dwelly_analysis import model
from tools.dwelly_platform.models import project_snapshot
from tools.dwelly_service.cases import _snapshot


def modules():
    return importlib.import_module('tools.dwelly_e2e.cases'), importlib.import_module('tools.dwelly_e2e.checks')


def record(source='case-002', step=3):
    cases, checks = modules()
    plan = cases.build_case(source, step, 'checks')
    snapshot = _snapshot(plan['declaration'])
    for event in plan['events']:
        snapshot = _snapshot(plan['declaration'], [*snapshot['events'], event], snapshot['snapshot_hash'])
    detail = {'case_id': plan['case_id'], 'snapshot': snapshot, 'actions': [], 'reviews': [], 'decisions': [], 'external_effects': 0}
    value = project_snapshot(snapshot)
    fixtures = json.loads((Path(__file__).parent / 'fixtures/good-candidates.json').read_text())
    candidate = model.parse(value, {'text': json.dumps(fixtures['candidates'][f'{source}:{step}'])})
    job = {'status': 'succeeded', 'case_id': plan['case_id'], 'input': value, 'input_hash': value['input_hash'],
           'step_index': snapshot['revision'], 'source': {'kind': 'platform_case', 'case_id': plan['case_id'],
               'revision': snapshot['revision'], 'snapshot_hash': snapshot['snapshot_hash']},
           'candidate': candidate, 'transaction': {'dispatch_attempts': 1, 'automatic_retries': 0, 'operational_effects': 0}}
    return {'plan': plan, 'job': job, 'detail': detail}


def evaluated(record):
    return modules()[1].evaluate(record['job'], record['detail'], record['plan'])


def named(record, name):
    return next(c for c in evaluated(record) if c['name'] == name)


def test_independent_good_candidates_pass_all_sixteen():
    cases, checks = modules()
    for plan in cases.case_plans('all'):
        r = record(plan['source']['source_id'], plan['source']['step_index'])
        results = evaluated(r)
        assert results and all(c['status'] == 'pass' for c in results), results
        assert all(set(c) == {'name', 'category', 'status', 'expected', 'actual'} for c in results)


def test_premature_completed_is_rejected():
    r = record()
    r['job']['candidate'].update(state='completed', waiting_for=[], next_action={'type': 'none', 'target_actor_id': None, 'description': 'Done.'})
    assert named(r, 'completion_supported')['status'] == 'fail'
    assert named(r, 'allowed_state')['status'] == 'fail'


def test_wrong_wait_target_is_rejected_even_if_actor_is_visible():
    r = record()
    r['job']['candidate']['waiting_for'] = ['address_desk']
    r['job']['candidate']['next_action']['target_actor_id'] = 'address_desk'
    assert named(r, 'waiting_for')['status'] == 'fail'


def test_wrong_action_target_is_rejected_even_if_actor_is_visible():
    r = record('case-002', 4)
    r['job']['candidate']['next_action']['target_actor_id'] = 'recipient'
    assert named(r, 'action_target')['status'] == 'fail'


def test_invented_evidence_is_rejected():
    r = record()
    r['job']['candidate']['evidence_event_ids'] = ['not-visible']
    assert named(r, 'visible_evidence')['status'] == 'fail'


@pytest.mark.parametrize('status', ['queued', 'running', 'failed', 'outcome_unknown', 'succeeded'])
def test_missing_output_is_unavailable_never_semantic_pass(status):
    r = record()
    r['job'].update(status=status, candidate=None)
    results = evaluated(r)
    assert named(r, 'output_available')['status'] == 'fail'
    assert all(c['status'] == 'not_run' for c in results if c['category'] == 'semantic')


def test_wrong_input_hash_is_rejected_and_semantics_are_not_scored():
    r = record()
    r['job']['input_hash'] = '0' * 64
    assert named(r, 'source_binding')['status'] == 'fail'
    assert all(c['status'] == 'not_run' for c in evaluated(r) if c['category'] == 'semantic')


@pytest.mark.parametrize('field', ['actions', 'external_effects', 'candidate_effects', 'transaction_effects', 'automatic_retries'])
def test_effects_and_automatic_retries_are_rejected(field):
    r = record()
    if field == 'actions':
        r['detail']['actions'] = [{'action_id': 'unexpected'}]
    elif field == 'external_effects':
        r['detail']['external_effects'] = 1
    elif field == 'candidate_effects':
        r['job']['candidate']['operational_effects'] = 1
    elif field == 'transaction_effects':
        r['job']['transaction']['operational_effects'] = 1
    else:
        r['job']['transaction']['automatic_retries'] = 1
    assert named(r, 'zero_effects' if field != 'automatic_retries' else 'bounded_dispatch')['status'] == 'fail'


def test_tampered_snapshot_is_rejected():
    r = record()
    r['detail']['snapshot']['events'][1]['text'] = 'Fabricated source.'
    assert named(r, 'source_binding')['status'] == 'fail'


def test_reference_labels_cannot_be_accepted_in_model_job():
    r = record()
    r['job']['reference'] = {'status': 'waiting', 'waiting_for': ['recipient']}
    assert named(r, 'source_binding')['status'] == 'fail'


def test_candidate_for_another_input_is_rejected():
    r = record()
    r['job']['candidate']['input_hash'] = 'f' * 64
    assert named(r, 'candidate_schema')['status'] == 'fail'


@pytest.mark.parametrize('attempts', [0, 2, True])
def test_completed_output_requires_exactly_one_recorded_dispatch(attempts):
    r = record()
    r['job']['transaction']['dispatch_attempts'] = attempts
    assert named(r, 'bounded_dispatch')['status'] == 'fail'


def test_invalid_candidate_shape_is_rejected():
    r = record()
    r['job']['candidate']['unexpected'] = True
    assert named(r, 'candidate_schema')['status'] == 'fail'


def test_summary_separates_semantics_operations_unavailable_and_fixture_mode():
    cases, checks = modules()
    records = [record(), record()]
    records[1]['job'].update(status='failed', candidate=None)
    for r in records:
        r['checks'] = evaluated(r)
    report = checks.summarize(records, 'simulated')
    assert report['mode'] == 'simulated'
    assert report['semantic_qualification'] == 'fixture_only_not_live_evidence'
    assert report['record_count'] == 2
    assert report['unavailable_count'] == 1
    assert report['semantic']['pass'] > 0 and report['semantic']['not_run'] > 0
    assert report['operational']['fail'] == 1
    assert checks.summarize(records, 'live')['semantic_qualification'] == 'author_labels_unvalidated'
    with pytest.raises(ValueError):
        checks.summarize(records, 'pretend-live')
