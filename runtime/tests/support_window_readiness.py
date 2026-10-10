"""Independent J05 fixtures; unit source bytes confer no execution qualification."""
from datetime import datetime, timezone
from hashlib import sha256

from proofkey.contracts import EnvironmentProfile
from proofkey.factory import (FactoryContext, OriginalInventory, ProposalMaterial,
                             RunnerIdentity)
from proofkey.identity import fingerprint
from proofkey.packet_contracts import PacketCatalogV1, PacketAccessSnapshotV1
from proofkey.profiles import load_profile
from support_synthetic_provisioning import case_data, cj


UNIT_PATHS = (
    '__init__.py', 'adapters/__init__.py', 'adapters/case.py', 'adapters/delivery.py',
    'adapters/messaging.py', 'adapters/operator.py', 'adapters/ownership.py', 'adapters/returns.py',
    'adapters/scheduling.py', 'adapters/world.py', 'admission.py', 'admission_routes.py', 'api.py',
    'assessment/__init__.py', 'assessment/audit.py', 'assessment/cache.py', 'assessment/contracts.py',
    'assessment/coverage.py', 'assessment/drills.py', 'assessment/driver_contracts.py', 'assessment/drivers.py',
    'assessment/isolation.py', 'assessment/labels.py', 'assessment/ledger.py', 'assessment/readiness.py',
    'batch.py', 'batch_files.py', 'bootstrap.py', 'budget.py', 'cli.py', 'clock.py', 'contracts.py', 'engine.py',
    'evidence/__init__.py', 'evidence/catalog.py', 'evidence/intake.py', 'evidence/processing_contracts.py',
    'evidence/redaction.py', 'execution.py', 'execution_consumer.py', 'execution_trace.py', 'exporter.py',
    'factory/__init__.py', 'factory/proposal.py', 'factory/release.py', 'factory/views.py', 'gateway.py',
    'host.py', 'host_admission.py', 'host_contracts.py', 'host_files.py', 'host_writer.py', 'identity.py',
    'journal.py', 'ownership.py', 'ownership_contracts.py', 'ownership_gateway.py', 'ownership_store.py',
    'packet_contracts.py', 'packets.py', 'planner.py', 'policy.py', 'ports.py', 'process.py', 'processing.py',
    'processing_orchestration.py', 'processing_summary.py', 'profiles.py', 'providers/__init__.py',
    'providers/anthropic.py', 'providers/elevenlabs.py', 'providers/invocations.py', 'providers/protocols.py',
    'providers/replay.py', 'providers/unavailable.py', 'registered_releases.py', 'release.py', 'replay.py',
    'retained_state.py', 'schema.sql', 'source_retained_state.py', 'synthetic_provisioning.py', 'trace.py',
    'verifier.py', 'wait_contracts.py', 'waits.py',
)


def unit_sources():
    """Non-executing bytes for matcher tests; never a behavioral receipt source."""
    return tuple((path, ('non-executing J05 unit material: ' + path).encode()) for path in UNIT_PATHS)


def unit_registration(sources=None):
    from proofkey.factory import WindowReadinessRegistrationV1
    candidate = expected_candidate()
    return WindowReadinessRegistrationV1(
        'synthetic-window-readiness-delta-v1', 'local_controlled_synthetic',
        'fixed-synthetic-window-readiness-v3', load_profile('flat-v1.3').release_hash,
        candidate.release_hash, candidate.process_hash, candidate.policy_hash,
        tuple((path, sha256(raw).hexdigest()) for path, raw in (sources or unit_sources())))


def expected_candidate():
    data = load_profile('flat-v1.3').model_dump(mode='json')
    data['profile_id'] = 'flat-window-readiness-v1'
    cap = data['capabilities']['reschedule']
    cap['version'] = 'synthetic-scheduling-dual-v1'
    cap['acknowledgement']['basis'] = 'synthetic-scheduling-dual-v1: window v2 envelope ack only; exact v1 typed ack'
    cap['readback']['basis'] = 'synthetic-scheduling-dual-v1: bounded original scheduling receipt; out-of-domain unavailable'
    for name in ('acknowledgement', 'readback'):
        cap[name]['evidence_ref'] = 'synthetic-scheduling-envelope-v1'
    process = data['processes']['reschedule_window']
    process['process_id'] = 'reschedule-window-readiness-v2'
    process['version'] = 'v2-window-readiness'
    process['phases'].insert(process['phases'].index('window_gate'), 'window_readiness')
    edge = next(e for e in process['edges'] if e['origin'] == 'read_authority' and e['operation'] == 'check_window')
    edge['target'] = 'window_readiness'
    process['edges'].extend([
        {'origin': 'window_readiness', 'operation': 'read_authority', 'target': 'window_gate', 'condition': None},
        {'origin': 'window_readiness', 'operation': 'request_stop', 'target': 'stop', 'condition': None},
        {'origin': 'window_readiness', 'operation': 'ask_operator', 'target': 'wait_operator', 'condition': None},
    ])
    process['prerequisites'].append({'phase': 'window_gate', 'authority': 'scheduling', 'fact': 'slot', 'expected': 'S0'})
    process['acknowledgements']['reschedule'] = dict(cap['acknowledgement'])
    process['readbacks']['reschedule'] = dict(cap['readback'])
    for item in data['processes'].values():
        item['release_hash'] = fingerprint({k: v for k, v in item.items() if k != 'release_hash'})
    data['process_hash'] = fingerprint(data['processes'])
    data['release_hash'] = fingerprint({k: v for k, v in data.items() if k != 'release_hash'})
    return EnvironmentProfile.model_validate(data)


def candidate_case_data():
    request, source = case_data()
    catalog = dict(version='packet-catalog-v1', case_id=request.case_id,
        object_id=request.object_id, complete=True, revision='v1',
        relevant_set_id='j05-empty-artifacts', originals=[], extracts=[], restrictions=[])
    catalog = PacketCatalogV1.model_validate(catalog).model_dump(mode='json')
    access = dict(version='packet-access-v1', decision_id='j05-operator-access', revision='v1',
        case_id=request.case_id, object_id=request.object_id, sender=request.principal_id,
        recipient='J06-OPERATOR', role='operator', purpose='operator_packet',
        catalog_hash=sha256(cj(catalog)).hexdigest(), permitted_originals=[], permitted_extracts=[],
        issued_at='2026-10-08T10:00:00Z', expires_at='2026-10-08T12:00:00Z', metadata_restrictions=[])
    access = PacketAccessSnapshotV1.model_validate(access).model_dump(mode='json')
    for key, value in (('operator.packet_catalog', catalog), ('operator.packet_access', access)):
        source['facts'][key] = dict(value=value, revision='v1', case_id=request.case_id,
            object_id=request.object_id, evidence_ref='synthetic-j05:' + key)
    source['facts']['scheduling.slot']['value'] = 'S0'
    if len(cj(source)) > 1048576:
        raise ValueError('candidate_fixture_limit')
    return request, source


def window_material(candidate, sources):
    baseline = load_profile('flat-v1.3')
    before, after = baseline.model_dump(mode='json'), candidate.model_dump(mode='json')
    _, source = candidate_case_data()
    return ProposalMaterial(
        proposal_id='j05-window-unit-material', source=cj(source), baseline=cj(before),
        candidate=cj(after), tests=cj({'required_cases': ['j05-unit-contract']}),
        agent=cj({'mode': 'synthetic', 'scope': 'non-executing unit material'}),
        diff=cj([{'path': key, 'before': before[key], 'after': after[key]}
                 for key in ('capabilities', 'processes')]),
        migration=cj({'strategy': 'preserve', 'affected_contracts':
                      ['capability:reschedule:v1.1', 'process:reschedule_window:v1']}),
        adapter_sources=sources, reviewed_supplement=cj(before))


def window_context(material, registration, *, regressions=(), reviews=(), pending=()):
    return FactoryContext(
        materials=(material,), regressions=regressions,
        runners=(RunnerIdentity('j05-unit-runner', 'local_controlled_synthetic',
                                fingerprint({'required_cases': ['j05-unit-contract']})),),
        reviews=reviews, inventory=OriginalInventory('j05-unit-inventory', 'controlled_fixture',
            load_profile('flat-v1.3').release_hash, pending),
        now=datetime(2026, 10, 10, 10, tzinfo=timezone.utc),
        process_delta_registration=registration)
