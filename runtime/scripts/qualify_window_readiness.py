#!/usr/bin/env python3
"""Fixed J05 source-only qualification; historical pending preservation is unqualified."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

# This is shared runner infrastructure, not a caller-selected module.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import qualify_factory as common

INNER_MODULES = (
    'test_window_readiness_registration', 'test_window_readiness_envelopes',
    'test_window_readiness_engine', 'test_window_readiness_composition',
    'test_adaptation_factory', 'test_factory_registration', 'test_factory_current_v1',
    'test_observed_stop_v2')
FORBIDDEN_INNER_MODULES = frozenset({
    'test_window_readiness_evidence', 'test_factory_qualification',
    'test_observed_stop_v2_acceptance', 'test_synthetic_provisioning_acceptance'})
CHILD_TIMEOUT_SECONDS = 900  # Full 156-test source suite measured at 546 seconds; not a business budget.


def run_inner(modules, report, output, *, expected_ids=None):
    if any(module.__name__ in FORBIDDEN_INNER_MODULES for module in modules):
        raise ValueError('forbidden inner module')
    return common.run_inner(modules, report, output, expected_ids=expected_ids)


def capture_artifacts(root, fixture, output, manifest):
    from dataclasses import replace
    from proofkey.factory import (AdaptationFactory, WindowReadinessRegistrationV1,
                                 RegressionEvidence, RunnerIdentity, HumanReviewEvent)
    from proofkey.profiles import load_profile
    from support import NOW
    from support_window_readiness import window_material, window_context
    from test_adaptation_factory import approval_for

    row = fixture['registration']
    registration = WindowReadinessRegistrationV1(
        registration_id=row['registration_id'], provenance=row['provenance'],
        host_factory_key=row['host_factory_key'], baseline_hash=row['baseline_hash'],
        candidate_hash=row['candidate_hash'], process_hash=row['process_hash'],
        policy_hash=row['policy_hash'], implementations=tuple((path, digest) for path, digest in row['implementations']))
    # Expected pins are already loaded and preflight-checked before source bytes become material.
    sources = tuple((path, (root / 'runtime/src/proofkey' / path).read_bytes())
                    for path, _ in registration.implementations)
    material = replace(window_material(load_profile('flat-window-readiness-v1'), sources),
        tests=common.canonical({'required_cases': ['module:' + name for name in INNER_MODULES],
            'planned_test_ids_sha256': sha256(common.canonical(fixture['j05_test_ids'])).hexdigest()}))
    context = replace(window_context(material, registration), now=NOW,
        runners=(RunnerIdentity('j05-current-source-runner', 'local_controlled_synthetic',
                                sha256(material.tests).hexdigest()),))
    factory = AdaptationFactory(context)
    proposal = factory.prepare_proposal(material.source, load_profile('flat-v1.3'), material.agent)
    records = manifest['tests']['case_outputs']
    grouped_cases = common.group_case_records(manifest['tests'], fixture['j05_test_ids'])
    timings = [json.loads(line.removeprefix('J05_TIMING ')) for record in records
               for line in json.loads(record['raw_utf8'])['stdout'].splitlines()
               if line.startswith('J05_TIMING ')]
    if {row['lane'] for row in timings} != {'library', 'configured_cli'} or any(
            len(row['calls']) != 15 or row['active_seconds'] > 120
            or row['host_remaining_seconds'] <= 0
            or any(call['elapsed_seconds'] > 10 for call in row['calls']) for row in timings):
        raise ValueError('unmeasured_or_failed_fit_blocker')
    regression = RegressionEvidence(common.canonical(dict(
        proposal_hash=proposal.proposal_hash, candidate_hash=load_profile('flat-window-readiness-v1').release_hash,
        baseline_hash=proposal.baseline_hash, test_hash=proposal.test_hash,
        runner_id='j05-current-source-runner', provenance='local_controlled_synthetic',
        execution_id=manifest['execution_id'], executed_at=NOW.isoformat(), result='passed',
        cases=grouped_cases)))
    approval = approval_for(proposal, regression)
    event = HumanReviewEvent(approval.proof_reference, common.canonical(approval.model_dump(mode='json')),
                            'human', 'synthetic_rehearsal')
    factory = AdaptationFactory(replace(context, regressions=(regression,), reviews=(event,)))
    packet = factory.check_proposal(proposal, sha256(regression.receipt).hexdigest())
    stage = factory.release_profile(packet, approval, [])
    if stage.status != 'staged_simulation':
        raise ValueError('J05 did not remain staged_simulation')
    raws = {'proposal': common.canonical(proposal.model_dump(mode='json')), 'regression': regression.receipt,
            'simulated_approval': common.canonical(approval.model_dump(mode='json')),
            'review_packet': common.canonical(packet.model_dump(mode='json')),
            'staged_manifest': stage.manifest, 'staged_receipt': stage.receipt_bytes}
    artifacts = []
    for kind, raw in raws.items():
        value = json.loads(raw)
        (output / (kind + '.json')).write_bytes(raw)
        artifacts.append(dict(kind=kind, path=kind + '.json', sha256=sha256(raw).hexdigest(),
            proposal_hash=value['proposal_hash'], regression_execution_id=value.get('execution_id'),
            stage_hash=stage.receipt.release_hash if kind.startswith('staged_') else None))
    common.validate_j05_artifacts(output, artifacts)
    manifest.update(lane='window-readiness-current-source-v1', measured_fit=timings,
        executed_test_count=len(records), receipt_group_count=len(grouped_cases),
        evidence_scope={'default_v1': 'current-source comparison; historical default rejects changed source',
            'stop_v2': 'current-source comparison', 'candidate_in_domain': 'executed exact fixed test IDs',
            'candidate_out_of_domain': 'unavailable/unknown, no fallback',
            'unchanged_goods_and_other_paths': 'current-source regression tests',
            'raw_domain': 'UTF-8 <=262144 bytes, depth <=16, observations <=128, identifier/revision/reason fields <=1024 Unicode code points, evidence occurrences <=128; all conjunctive',
            'historical_pending_preservation': 'unqualified',
            'limitations': 'No installation, native HTTP, live provider, actual human, activation, migration, retained resolver or completed timed drill.'})
    return artifacts


def child(output):
    return common._execute_child(output, lane=common.CURRENT_LANE, selected_modules=INNER_MODULES,
        capture=capture_artifacts, test_ids_key='j05_test_ids')


def main():
    if common._CHILD_ACTIVE or os.environ.get('_PROOFKEY_QUALIFICATION_CHILD'):
        raise ValueError('nested launcher entry')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    output = parser.parse_args().output
    if not output.is_absolute():
        parser.error('--output must be an absolute new directory')
    if __name__ == '__window_readiness_child__':
        return child(output)
    root = Path(__file__).resolve().parents[2]
    if output.resolve().is_relative_to(root / 'runtime'):
        parser.error('--output must be outside the inventoried runtime')
    try:
        output.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        parser.error('--output directory already exists')
    manifest = common.blank_manifest()
    manifest.update(lane='window-readiness-current-source-v1', role='launcher')
    if sys.flags.optimize:
        manifest['error'] = 'optimized launcher is not permitted'
        (output / 'manifest.json').write_bytes(common.canonical(manifest))
        return 1
    env = dict(os.environ, PYTHONNOUSERSITE='1', PYTHONDONTWRITEBYTECODE='1')
    env.pop('PYTHONOPTIMIZE', None)
    with tempfile.TemporaryDirectory(prefix='j05-private-pycache-') as directory:
        code = "import runpy,sys; path=sys.argv.pop(1); runpy.run_path(path,run_name='__window_readiness_child__')"
        try:
            result = subprocess.run([sys.executable, '-B', '-s', '-X', 'pycache_prefix=' + directory,
                '-c', code, str(Path(__file__).resolve()), '--output', str(output)],
                env=env, capture_output=True, timeout=CHILD_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired as error:
            result = error
            manifest['error'] = 'child timeout after ' + str(CHILD_TIMEOUT_SECONDS) + ' seconds'
    (output / 'child.stdout.log').write_bytes(result.stdout or b'')
    (output / 'child.stderr.log').write_bytes(result.stderr or b'')
    if isinstance(result, subprocess.TimeoutExpired) or not (output / 'manifest.json').is_file():
        manifest.setdefault('error', 'child failed without a manifest')
        (output / 'manifest.json').write_bytes(common.canonical(manifest))
        return 1
    manifest = json.loads((output / 'manifest.json').read_bytes())
    manifest['launcher_events'] = [{'role': 'launcher', 'event': 'child_launch', 'count': 1,
                                    'returncode': result.returncode}]
    (output / 'manifest.json').write_bytes(common.canonical(manifest))
    return result.returncode


if __name__ in {'__main__', '__window_readiness_child__'}:
    sys.exit(main())
