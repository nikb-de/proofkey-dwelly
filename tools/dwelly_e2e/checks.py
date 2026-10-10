"""External assertions, never a generator of expected provider outputs."""
from collections import Counter
import json

from tools.dwelly_analysis import model
from tools.dwelly_platform.models import project_snapshot
from tools.dwelly_service.cases import _snapshot


_SEMANTIC = ('candidate_schema', 'visible_evidence', 'allowed_state', 'allowed_action',
             'action_target', 'waiting_for', 'completion_supported', 'physical_delivery_not_inferred')


def evaluate(job, detail, plan):
    """Check a completed frozen candidate and independent operational evidence."""
    checks = []
    def add(name, category, passed, expected, actual):
        checks.append({'name': name, 'category': category,
                       'status': 'pass' if passed else 'fail', 'expected': expected, 'actual': actual})

    job = job if type(job) is dict else {}
    detail = detail if type(detail) is dict else {}
    candidate = job.get('candidate')
    available = job.get('status') == 'succeeded' and type(candidate) is dict
    add('output_available', 'operational', available, 'succeeded with candidate', job.get('status'))
    transaction = job.get('transaction') or {}
    dispatch = transaction.get('dispatch_attempts')
    retries = transaction.get('automatic_retries')
    add('bounded_dispatch', 'operational', type(dispatch) is int and 0 <= dispatch <= 1
        and (not available or dispatch == 1) and type(retries) is int and retries == 0,
        {'maximum_dispatch_attempts': 1, 'automatic_retries': 0},
        {'dispatch_attempts': dispatch, 'automatic_retries': retries})
    effects = {'external_effects': detail.get('external_effects'),
               'snapshot_effects': (detail.get('snapshot') or {}).get('operational_effects'),
               'transaction_effects': transaction.get('operational_effects'),
               'candidate_effects': candidate.get('operational_effects') if type(candidate) is dict else None,
               'actions': detail.get('actions'), 'reviews': detail.get('reviews'), 'decisions': detail.get('decisions')}
    zero = all(type(effects[key]) is int and effects[key] == 0 for key in
               ('external_effects', 'snapshot_effects', 'transaction_effects'))
    zero = zero and all(effects[key] == [] for key in ('actions', 'reviews', 'decisions'))
    zero = zero and (candidate is None or type(effects['candidate_effects']) is int and effects['candidate_effects'] == 0)
    add('zero_effects', 'operational', zero, 'zero effects and no decisions, reviews or actions', effects)
    binding, expected_input = False, None
    try:
        snapshot = _snapshot(plan['declaration'])
        for event in plan['events']:
            snapshot = _snapshot(plan['declaration'], [*snapshot['events'], event], snapshot['snapshot_hash'])
        expected_input = project_snapshot(snapshot)
        source = {'kind': 'platform_case', 'case_id': plan['case_id'], 'revision': snapshot['revision'],
                  'snapshot_hash': snapshot['snapshot_hash']}
        binding = (detail['snapshot'] == snapshot and detail['case_id'] == plan['case_id']
                   and job['source'] == source and job['case_id'] == plan['case_id']
                   and job.get('reference') is None
                   and job['step_index'] == snapshot['revision'] and job['input'] == expected_input
                   and job['input_hash'] == expected_input['input_hash'])
    except (KeyError, ValueError, TypeError):
        pass
    add('source_binding', 'operational', binding,
        {'case_id': plan['case_id'], 'input_hash': expected_input['input_hash'] if expected_input else None},
        {'case_id': job.get('case_id'), 'input_hash': job.get('input_hash')})
    if not available or not binding:
        for name in _SEMANTIC:
            checks.append({'name': name, 'category': 'semantic', 'status': 'not_run',
                           'expected': 'bound completed output', 'actual': 'unavailable' if not available else 'binding_failed'})
        return checks

    # Candidate identity/metadata must exactly match the existing parser's v1
    # contract. The external assertions below are independent of that parser.
    body_fields = ('state', 'waiting_for', 'next_action', 'evidence_event_ids', 'uncertainty')
    valid = False
    try:
        body = {field: candidate[field] for field in body_fields}
        valid = model.parse(expected_input, {'text': json.dumps(body, ensure_ascii=False, allow_nan=False)}) == candidate
    except (KeyError, ValueError, TypeError, OverflowError):
        pass
    add('candidate_schema', 'semantic', valid, 'proofkey-step-candidate-v1 bound to exact input', candidate.get('schema_version'))
    visible = {event['event_id'] for event in plan['events']}
    evidence = candidate.get('evidence_event_ids')
    evidence_ok = (type(evidence) is list and all(type(item) is str for item in evidence)
                   and len(evidence) == len(set(evidence)) and set(evidence) <= visible
                   and (candidate.get('state') == 'unknown' or bool(evidence)))
    add('visible_evidence', 'semantic', evidence_ok, sorted(visible), evidence)
    expectation = plan['expectation']
    action = candidate.get('next_action') if type(candidate.get('next_action')) is dict else {}
    add('allowed_state', 'semantic', candidate.get('state') in expectation['allowed_states'], expectation['allowed_states'], candidate.get('state'))
    add('allowed_action', 'semantic', action.get('type') in expectation['allowed_actions'], expectation['allowed_actions'], action.get('type'))
    add('action_target', 'semantic', action.get('target_actor_id') in expectation['action_targets'], expectation['action_targets'], action.get('target_actor_id'))
    waiting = candidate.get('waiting_for')
    wait_ok = type(waiting) is list and all(type(item) is str for item in waiting) and sorted(waiting) == sorted(expectation['waiting_for'])
    add('waiting_for', 'semantic', wait_ok, expectation['waiting_for'], waiting)
    add('completion_supported', 'semantic', candidate.get('state') != 'completed' or expectation['completion_allowed'],
        expectation['completion_allowed'], candidate.get('state') == 'completed')
    add('physical_delivery_not_inferred', 'semantic', candidate.get('physical_delivery') == 'not_inferred',
        'not_inferred', candidate.get('physical_delivery'))
    return checks


def summarize(records, mode):
    """Keep unavailable outputs separate from assertion totals and mode claims."""
    if mode not in {'simulated', 'live'}:
        raise ValueError('invalid_mode')
    totals = {category: Counter({'pass': 0, 'fail': 0, 'not_run': 0}) for category in ('semantic', 'operational')}
    unavailable = 0
    for record in records:
        checks = record.get('checks', [])
        output = next((check for check in checks if check['name'] == 'output_available'), None)
        unavailable += output is None or output['status'] != 'pass'
        for check in checks:
            totals[check['category']][check['status']] += 1
    return {'mode': mode, 'record_count': len(records), 'unavailable_count': unavailable,
            'semantic_qualification': 'fixture_only_not_live_evidence' if mode == 'simulated' else 'author_labels_unvalidated',
            'coverage_qualification': 'development_only_one_logistics_family_plus_ui_control',
            'semantic': dict(totals['semantic']), 'operational': dict(totals['operational'])}
