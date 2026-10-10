"""Test-only fresh preparations for the observed-stop v2 contract."""
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import json

from proofkey.contracts import AuthContext
from proofkey.host_admission import (
    LocalAdmissionCompositionV1, ProvisionedReviewResolverV1, SyntheticReviewGrantV1)
from proofkey.synthetic_provisioning import SyntheticCaseReleaseSpecV1, prepare_synthetic_release
from support_synthetic_provisioning import case_data, cj, context
from test_host_admission import paced_clock
from proofkey.host import RuntimeFactory


@contextmanager
def prepared_case(factory_key='fixed-synthetic-observed-stop-v2', *, missing=False):
    with TemporaryDirectory() as folder, paced_clock() as (clock, state):
        parent = Path(folder).resolve()
        parent.chmod(0o700)
        request, source = case_data()
        # Use the already executed J06 packet envelopes, before hashing.
        example = Path(__file__).resolve().parents[1] / 'examples/registered-cases/window-fixture.json'
        packet_facts = json.loads(example.read_text())['facts']
        for name in ('operator.packet_access', 'operator.packet_catalog'):
            source['facts'][name] = packet_facts[name]
        if missing:
            source['facts']['case.completeness']['value'] = 'missing'
        spec = SyntheticCaseReleaseSpecV1('J07-H', 'J07-L', 'J07-R', request, cj(source))
        prepared = prepare_synthetic_release(spec, parent=parent, clock=clock,
            execution=context(clock), factory_key=factory_key)
        grant = SyntheticReviewGrantV1('j07-review', prepared.binding.artifact_hash,
            'j07-synthetic-reviewer', 'admit_fixed_local_replay', 'synthetic_rehearsal',
            clock.now(), clock.now() + timedelta(minutes=10))
        composition = LocalAdmissionCompositionV1(prepared.registry, prepared.binding,
            ProvisionedReviewResolverV1((grant,)), grant.review_id, prepared.control_parent)
        yield SimpleNamespace(parent=parent, clock=clock, state=state, prepared=prepared,
            request=request, auth=AuthContext(caller_id=request.principal_id,
            proof_reference='j06-synthetic-proof'), composition=composition)


@contextmanager
def opened_case(factory_key='fixed-synthetic-observed-stop-v2', *, missing=False):
    with prepared_case(factory_key, missing=missing) as fx:
        fx.runtime = RuntimeFactory().create_registered(fx.prepared.host_release,
            fx.clock, composition=fx.composition, execution=context(fx.clock))
        try:
            yield fx
        finally:
            fx.runtime.close()


def snapshot_rows(runtime, clock):
    image = runtime.store.capture_retained_state(execution=context(clock), clock=clock)
    return {table['name']: [dict(zip(table['columns'], row)) for row in table['rows']]
            for table in json.loads(image.payload)['tables']}


def assert_budget_continuity(test, before, after):
    test.assertEqual(after.case_id, before.case_id)
    test.assertLessEqual(after.deadline, before.deadline)
    for name in type(before).model_fields:
        if name.startswith('max_') or name == 'reserved_handoff_effects':
            test.assertEqual(getattr(after, name), getattr(before, name))
    for name in ('active_seconds', 'tool_calls', 'planner_calls', 'effects', 'clarifications'):
        test.assertGreaterEqual(getattr(after, name), getattr(before, name))
    for name in ('reconciliation_reads', 'retries'):
        for key, count in getattr(before, name).items():
            test.assertGreaterEqual(getattr(after, name).get(key, -1), count)
    test.assertEqual(set(after.role_allowances), set(before.role_allowances))
    for name, old in before.role_allowances.items():
        new = after.role_allowances[name]
        for key in type(old).model_fields:
            if key not in ('invocations', 'cost', 'usage'):
                test.assertEqual(getattr(new, key), getattr(old, key))
        test.assertGreaterEqual(new.invocations, old.invocations)
        test.assertGreaterEqual(new.cost, old.cost)
        for key, count in old.usage.items():
            test.assertGreaterEqual(new.usage.get(key, -1), count)
