"""Explicit J05 comparison contexts backed only by the reviewed fixed fixture."""
import json
from hashlib import sha256
from pathlib import Path

from proofkey.contracts import EnvironmentProfile
from proofkey.factory import (FactoryContext, OriginalInventory, ProposalMaterial, RunnerIdentity,
                             SyntheticImplementationRegistration)
from proofkey.identity import fingerprint
from proofkey.profiles import WINDOW_READINESS_IMPLEMENTATION_PATHS
from support import NOW

FIXTURE = Path(__file__).resolve().parent / 'fixtures/window-readiness-current-registration-v1.json'
LEGACY_PATHS = ('adapters/operator.py', 'adapters/world.py', 'packet_contracts.py',
                'process.py', 'profiles.py', 'verifier.py')


def fixed_current_fixture():
    try:
        data = json.loads(FIXTURE.read_bytes())
    except FileNotFoundError as error:
        raise ValueError('fixed fixture unavailable: final J05 freeze pending') from error
    if set(data) != {'registration', 'candidate_file_sha256', 'current_v1_inventory_sha256',
                     'current_v1_test_ids', 'j05_test_ids'}:
        raise ValueError('invalid fixed J05 fixture')
    registration = data['registration']
    if (set(registration) != {'registration_id', 'provenance', 'host_factory_key', 'baseline_hash',
                             'candidate_hash', 'process_hash', 'policy_hash', 'implementations'}
            or registration['registration_id'] != 'synthetic-window-readiness-delta-v1'
            or registration['provenance'] != 'local_controlled_synthetic'
            or registration['host_factory_key'] != 'fixed-synthetic-window-readiness-v3'
            or tuple(row[0] for row in registration['implementations']) != WINDOW_READINESS_IMPLEMENTATION_PATHS):
        raise ValueError('invalid fixed J05 registration')
    return data


def current_v1_registration() -> SyntheticImplementationRegistration:
    data = fixed_current_fixture()
    pins = tuple((path, digest) for path, digest in data['registration']['implementations']
                 if path in LEGACY_PATHS)
    raw = json.dumps([{'path': path, 'sha256': digest} for path, digest in pins],
                     sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    if tuple(path for path, _ in pins) != LEGACY_PATHS or sha256(raw).hexdigest() != data['current_v1_inventory_sha256']:
        raise ValueError('invalid fixed current comparison inventory')
    return SyntheticImplementationRegistration('synthetic-factory-j05-current-v1',
                                               'local_controlled_synthetic', pins)


def current_v1_context(material: ProposalMaterial, *, registration: SyntheticImplementationRegistration,
                       regressions=(), reviews=(), pending=(), inventory=True) -> FactoryContext:
    base = EnvironmentProfile.model_validate_json(material.baseline)
    encode = lambda value: json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                                      allow_nan=False).encode()
    return FactoryContext(materials=(material,), regressions=tuple(regressions),
        runners=(RunnerIdentity('controlled-local-tests', 'local_controlled_synthetic',
                                fingerprint(json.loads(material.tests))),),
        reviews=tuple(reviews), inventory=OriginalInventory('synthetic-complete-1', 'controlled_fixture',
            base.release_hash, tuple(encode(item.model_dump(mode='json')) for item in pending)) if inventory else None,
        now=NOW, implementation_registration=registration, process_delta_registration=None)
