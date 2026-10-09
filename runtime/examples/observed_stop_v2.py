"""Explicit local synthetic run/stop acceptance within one live runtime owner.

The grant is synthetic authority, not external human approval. Private prepared
roots are retained for inspection; only the returned summary is public-safe.
"""
from datetime import timedelta
import json
from pathlib import Path

from proofkey.clock import SyntheticReplayClock
from proofkey.contracts import AuthContext, CanonicalRequest
from proofkey.execution import ExecutionContext
from proofkey.host import RuntimeFactory
from proofkey.host_admission import (
    LocalAdmissionCompositionV1, ProvisionedReviewResolverV1, SyntheticReviewGrantV1,
)
from proofkey.synthetic_provisioning import (
    SyntheticCaseReleaseSpecV1, prepare_synthetic_release,
)
from proofkey.wait_contracts import WaitRecordV1


def _run_demo(parent: Path, *, pending_wait: bool) -> dict:
    inputs = Path(__file__).resolve().parent / 'registered-cases'
    request = CanonicalRequest.model_validate_json((inputs / 'window-request.json').read_bytes())
    fixture_bytes = (inputs / 'window-fixture.json').read_bytes()
    if pending_wait:
        fixture = json.loads(fixture_bytes)
        fixture['facts']['case.completeness']['value'] = 'missing'
        fixture_bytes = json.dumps(fixture, sort_keys=True, separators=(',', ':')).encode('utf-8')

    clock = SyntheticReplayClock()

    def context(seconds=5):
        return ExecutionContext.capture(clock.now() + timedelta(seconds=seconds), clock)

    prepared = prepare_synthetic_release(
        SyntheticCaseReleaseSpecV1('J07-DEMO-H', 'J07-DEMO-L', 'J07-DEMO-R', request, fixture_bytes),
        parent=parent, clock=clock, execution=context(),
        factory_key='fixed-synthetic-observed-stop-v2',
    )
    grant = SyntheticReviewGrantV1(
        'j07-demo-review', prepared.binding.artifact_hash, 'j07-demo-reviewer',
        'admit_fixed_local_replay', 'synthetic_rehearsal', clock.now(),
        clock.now() + timedelta(minutes=10),
    )
    composition = LocalAdmissionCompositionV1(
        prepared.registry, prepared.binding, ProvisionedReviewResolverV1((grant,)),
        grant.review_id, prepared.control_parent,
    )
    auth = AuthContext(caller_id=request.principal_id, proof_reference='j06-synthetic-proof')
    resources = RuntimeFactory().create_registered(
        prepared.host_release, clock, composition=composition, execution=context(),
    )
    try:
        run = resources.run_registered(request, auth, execution=context(120))
        case_id, generation = request.case_id, run.binding.generation
        before = resources.store.checkpoint(case_id)
        original = resources.store.original_request(case_id, generation)
        saved = resources.store.saved_result(case_id, generation)
        claim = resources.admission.claim_for_case(case_id, execution=context())
        route = resources.admission.route_for_case(case_id, execution=context())
        effects_before = resources.world.effect_count('reschedule')
        wait_before = None
        if pending_wait:
            if before.question_id is not None:
                wait_before = resources.store.load_wait_record(before.question_id)
            if type(wait_before) is not WaitRecordV1 or wait_before.lifecycle != 'pending':
                raise RuntimeError('Expected an actual pending wait before stop')

        stopped = resources.stop_registered(case_id, generation, auth, execution=context())
        after = resources.store.checkpoint(case_id)
        summary = {
            'scope': 'trusted-library-same-owner-no-restart',
            'factory_id': prepared.binding.factory_id,
            'artifact_hash': prepared.binding.artifact_hash,
            'run_status': run.status,
            'stop_requested': stopped.stop.requested is True and after.stop.requested is True,
            'original_generation': generation,
            'original_request_preserved': (
                resources.store.original_request(case_id, generation) == original == request
                and after.binding == before.binding
                and resources.store.saved_result(case_id, generation) == saved
            ),
            'claim_preserved': resources.admission.claim_for_case(case_id, execution=context()) == claim,
            'route_preserved': resources.admission.route_for_case(case_id, execution=context()) == route,
            'deadline_not_extended': (
                after.deadline <= before.deadline and after.budget.deadline <= before.budget.deadline
            ),
            'tool_calls_before': before.budget.tool_calls,
            'tool_calls_after': after.budget.tool_calls,
            'business_effects_before': effects_before,
            'business_effects_after': resources.world.effect_count('reschedule'),
        }
        if pending_wait:
            wait_after = resources.store.load_wait_record(wait_before.wait.question_id)
            if type(wait_after) is not WaitRecordV1 or wait_after.lifecycle != 'stopped':
                raise RuntimeError('Expected the observed pending wait to become stopped')
            summary.update({
                'wait_observed': wait_before.lifecycle == 'pending',
                'wait_stopped': wait_after.lifecycle == 'stopped',
                'wait_context_preserved': wait_after.model_dump(exclude={'lifecycle', 'successor_hash'})
                    == wait_before.model_dump(exclude={'lifecycle', 'successor_hash'}),
                'wait_expiry_preserved': (
                    wait_after.wait.expires_at == wait_before.wait.expires_at
                    and wait_after.wait.budget.deadline == wait_before.wait.budget.deadline
                    and wait_after.origin_checkpoint == wait_before.origin_checkpoint
                ),
            })
    finally:
        resources.close()
    summary['owner_closed'] = resources.closed is True
    return summary


def run_demo(parent: Path) -> dict:
    """Run and stop a complete case using one live owner and real host timing."""
    return _run_demo(parent, pending_wait=False)


def run_pending_demo(parent: Path) -> dict:
    """Observe and stop a real pending wait without changing its original scope."""
    return _run_demo(parent, pending_wait=True)


if __name__ == '__main__':
    import argparse, json
    parser = argparse.ArgumentParser(description='Explicit synthetic same-owner v2 stop demo')
    parser.add_argument('--parent', type=Path, required=True)
    parser.add_argument('--pending-wait', action='store_true')
    args = parser.parse_args()
    demo = run_pending_demo if args.pending_wait else run_demo
    print(json.dumps(demo(args.parent), sort_keys=True))
