"""Test-only fresh preparations for the observed-stop v2 contract."""
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from proofkey.contracts import AuthContext
from proofkey.host_admission import (
    LocalAdmissionCompositionV1, ProvisionedReviewResolverV1, SyntheticReviewGrantV1)
from proofkey.synthetic_provisioning import SyntheticCaseReleaseSpecV1, prepare_synthetic_release
from support_synthetic_provisioning import case_data, cj, context
from test_host_admission import paced_clock


@contextmanager
def prepared_case(factory_key='fixed-synthetic-observed-stop-v2', *, missing=False):
    with TemporaryDirectory() as folder, paced_clock() as (clock, state):
        parent = Path(folder).resolve()
        parent.chmod(0o700)
        request, source = case_data()
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
