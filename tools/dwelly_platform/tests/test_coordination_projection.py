"""The case overview exposes coordination without claiming delivery completion."""
from copy import deepcopy

import pytest

from tools.dwelly_platform import domain


def detail():
    return {'snapshot': {'revision': 8, 'snapshot_hash': 'a' * 64}, 'decisions': [],
            'states': {'lifecycle': 'new', 'analysis': 'not_started', 'decision': 'none', 'action': 'none'}}


@pytest.mark.parametrize('phase,lifecycle', [
    ('booked', 'in_review'), ('cancellation_pending', 'awaiting_information'),
    ('awaiting_terms', 'awaiting_information'), ('awaiting_consent', 'awaiting_approval'),
    ('ready_to_book', 'ready'), ('booking_pending', 'awaiting_information'),
    ('booking_confirmed', 'resolved'), ('escalated', 'escalated')])
def test_current_coordination_has_its_own_state_and_case_overview(phase, lifecycle):
    current = {'phase': phase, 'revision': 8, 'snapshot_hash': 'a' * 64,
               'physical_delivery': 'not_confirmed'}
    projected = domain.project_coordination(detail(), current)
    assert projected['coordination'] == current
    assert projected['states']['coordination'] == phase
    assert projected['states']['coordination_freshness'] == 'current'
    assert projected['states']['lifecycle'] == lifecycle
    assert projected['states']['analysis'] == 'not_started'
    assert projected['states']['action'] == 'none'
    assert current['physical_delivery'] == 'not_confirmed'


def test_new_evidence_invalidates_overview_without_erasing_confirmed_history():
    current = {'phase': 'booking_confirmed', 'revision': 7, 'snapshot_hash': 'b' * 64}
    before = deepcopy(current)
    projected = domain.project_coordination(detail(), current)
    assert projected['states']['coordination'] == 'booking_confirmed'
    assert projected['states']['coordination_freshness'] == 'stale'
    assert projected['states']['lifecycle'] == 'in_review'
    assert current == before


def test_current_model_or_operator_decision_keeps_its_lifecycle_priority():
    result = detail()
    result['decisions'] = [{'revision': 8, 'snapshot_hash': 'a' * 64}]
    result['states']['lifecycle'] = 'escalated'
    projected = domain.project_coordination(result, {'phase': 'ready_to_book', 'revision': 8, 'snapshot_hash': 'a' * 64})
    assert projected['states']['lifecycle'] == 'escalated'
    assert projected['states']['coordination'] == 'ready_to_book'


def test_no_coordination_retains_existing_overview():
    projected = domain.project_coordination(detail(), None)
    assert projected['coordination'] is None
    assert projected['states']['coordination'] == 'not_initialized'
    assert projected['states']['coordination_freshness'] == 'not_initialized'
    assert projected['states']['lifecycle'] == 'new'
