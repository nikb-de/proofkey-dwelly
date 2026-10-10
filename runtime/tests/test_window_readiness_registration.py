"""J05 semantic/registration contracts; these are not behavioral qualification receipts."""
import unittest
from dataclasses import FrozenInstanceError, replace
from hashlib import sha256
import json
import proofkey.profiles as profiles
from proofkey.contracts import EnvironmentProfile, HumanReviewApproval
from proofkey.factory import AdaptationFactory, FactoryDenied, RegressionEvidence, HumanReviewEvent
from proofkey.factory.proposal import canonical
from proofkey.identity import fingerprint
from proofkey.packet_contracts import PacketCatalogV1, PacketAccessSnapshotV1

from proofkey.factory.proposal import _affected
from proofkey.profiles import load_profile
from support_window_readiness import (expected_candidate, candidate_case_data, window_material,
                                     window_context, unit_sources, unit_registration, UNIT_PATHS)
from support_synthetic_provisioning import cj


def rehashed(data):
    for process in data['processes'].values():
        process['release_hash'] = fingerprint({k: v for k, v in process.items() if k != 'release_hash'})
    data['process_hash'] = fingerprint(data['processes'])
    data['release_hash'] = fingerprint({k: v for k, v in data.items() if k != 'release_hash'})
    return EnvironmentProfile.model_validate(data)


class ProfileDeltaTests(unittest.TestCase):
    def test_exact_candidate_and_only_two_affected_contracts(self):
        baseline = load_profile('flat-v1.3')
        candidate = load_profile('flat-window-readiness-v1')
        self.assertEqual(candidate, expected_candidate())
        self.assertEqual(_affected(baseline, candidate),
            ['capability:reschedule:v1.1', 'process:reschedule_window:v1'])
        self.assertEqual(candidate.processes['reschedule_exact'], baseline.processes['reschedule_exact'])

    def test_exact_matcher_rejects_forgery_and_sibling_changes(self):
        candidate = expected_candidate()
        self.assertTrue(profiles.is_window_readiness_profile(candidate))
        for path, value in (
                (('profile_id',), 'forged-window'), (('release_hash',), '0' * 64),
                (('capabilities', 'reschedule', 'timeout_seconds'), 9),
                (('processes', 'reschedule_window', 'prerequisites', -1, 'expected'), 'S1'),
                (('processes', 'reschedule_exact', 'process_id'), 'forged-exact')):
            with self.subTest(path=path):
                data = candidate.model_dump(mode='json')
                parent = data
                for key in path[:-1]:
                    parent = parent[key]
                parent[path[-1]] = value
                changed = EnvironmentProfile.model_validate(data) if path == ('release_hash',) else rehashed(data)
                self.assertFalse(profiles.is_window_readiness_profile(changed))
        with self.assertRaises(ValueError):
            profiles._window_readiness_profile_data(load_profile('nested-v1.3'))
        self.assertEqual(profiles.WINDOW_READINESS_IMPLEMENTATION_PATHS, UNIT_PATHS)
        self.assertEqual(len(UNIT_PATHS), 86)

    def test_operation_admission_follows_exact_process_and_source_mode(self):
        candidate = expected_candidate()
        for version, operation, mode, allowed in (
                ('v2-window-readiness', 'reschedule', 'window', True),
                ('v2-window-readiness', 'request_stop', 'window', True),
                ('v2-window-readiness', 'reschedule', 'exact_slot', False),
                ('v2-window-readiness', 'create_return', 'window', False),
                ('v2-window-readiness', 'register_service_refusal', 'window', False),
                ('v1', 'reschedule', 'window', False), ('v1', 'reschedule', 'exact_slot', True),
                ('v1', 'create_return', 'unknown', True), ('v1', 'undeclared', 'window', False)):
            with self.subTest(version=version, operation=operation, mode=mode):
                self.assertEqual(profiles.supports_process_operation(candidate, version, operation, mode), allowed)
        self.assertTrue(profiles.supports_process_operation(load_profile('flat-v1.3'), 'v1', 'anything', None))
        self.assertFalse(profiles.supports_process_operation(load_profile('flat-v1.3'), 'v2-window-readiness', 'reschedule', 'window'))

    def test_original_id_uses_full_explicit_fields_and_strict_inputs(self):
        fields = dict(account_id='A', provider_key='P', case_id='C', object_id='O',
                      operation='reschedule', generation='G', action_id='X',
                      fingerprint='a' * 64, identity_hash='b' * 64)
        expected = 'provider:window-envelope-v1:' + sha256(cj({
            'domain': 'synthetic-window-original-v1', 'account_id': 'A', 'provider_key': 'P',
            'case_id': 'C', 'object_id': 'O', 'operation': 'reschedule', 'generation': 'G',
            'action_id': 'X', 'fingerprint': 'a' * 64, 'identity_hash': 'b' * 64})).hexdigest()
        self.assertEqual(profiles._window_original_request_id(**fields), expected)
        class StringSubclass(str):
            pass
        for key in fields:
            for value in ('', '  ', None, 3, StringSubclass(fields[key])):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    profiles._window_original_request_id(**{**fields, key: value})
        for key, value in (('operation', 'create_return'), ('fingerprint', 'A' * 64),
                           ('identity_hash', 'f' * 63), ('identity_hash', 'g' * 64)):
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                profiles._window_original_request_id(**{**fields, key: value})
        for key in fields:
            value = 'c' * 64 if key in ('fingerprint', 'identity_hash') else fields[key] + '-changed'
            if key != 'operation':
                self.assertNotEqual(profiles._window_original_request_id(**{**fields, key: value}), expected)

    def test_complete_packet_fixture_is_fresh_and_bound_before_hashing(self):
        request, source = candidate_case_data()
        facts = source['facts']
        catalog = PacketCatalogV1.model_validate(facts['operator.packet_catalog']['value'])
        access = PacketAccessSnapshotV1.model_validate(facts['operator.packet_access']['value'])
        self.assertEqual(access.catalog_hash, sha256(cj(catalog.model_dump(mode='json'))).hexdigest())
        self.assertEqual((catalog.case_id, access.case_id), (request.case_id, request.case_id))
        self.assertEqual(facts['scheduling.slot']['value'], 'S0')
        self.assertLessEqual(len(cj(source)), 1048576)
        facts['scheduling.slot']['value'] = 'altered'
        self.assertEqual(candidate_case_data()[1]['facts']['scheduling.slot']['value'], 'S0')


class RegistrationTests(unittest.TestCase):
    def setUp(self):
        self.mat = window_material(expected_candidate(), unit_sources())
        self.registration = unit_registration()

    def assert_denied(self, mat=None, registration=None, reason=None):
        with self.assertRaises(FactoryDenied) as caught:
            AdaptationFactory(window_context(mat or self.mat, registration or self.registration))
        if reason:
            self.assertEqual(caught.exception.reason, reason)

    def test_all_reconstruction_paths_use_the_retained_registration(self):
        factory = AdaptationFactory(window_context(self.mat, self.registration))
        retained = factory.context.process_delta_registration
        self.assertIsNot(retained, self.registration)
        self.assertIsNot(retained.implementations, self.registration.implementations)
        self.assertFalse(hasattr(retained, '__dict__'))
        with self.assertRaises(FrozenInstanceError):
            retained.registration_id = 'edited'
        proposal = factory.prepare_proposal(self.mat.source, load_profile('flat-v1.3'), self.mat.agent)
        self.assertEqual(factory._resolve(proposal)[1], proposal)
        self.assertEqual(factory._proposal_hash(proposal.proposal_hash), proposal)
        body = factory._resolve(proposal)[4]
        commitment = body['process_delta_registration']
        self.assertEqual(set(commitment), {'registration_id', 'provenance', 'host_factory_key',
            'baseline_hash', 'candidate_hash', 'process_hash', 'policy_hash',
            'inventory_sha256', 'registration_sha256'})
        self.assertNotIn('implementation_registration', body)
        inventory = [{'path': path, 'sha256': sha256(raw).hexdigest()} for path, raw in unit_sources()]
        self.assertEqual(commitment['inventory_sha256'], sha256(canonical(inventory)).hexdigest())
        without_self = {k: v for k, v in commitment.items() if k != 'registration_sha256'}
        self.assertEqual(commitment['registration_sha256'], sha256(canonical(without_self)).hexdigest())
        object.__setattr__(self.registration, 'candidate_hash', '0' * 64)
        object.__setattr__(self.mat, 'adapter_sources', ())
        object.__setattr__(self.mat, 'candidate', b'caller-mutated')
        self.assertEqual(factory._resolve(proposal)[4], body)
        self.assertEqual(factory._proposal_hash(proposal.proposal_hash), proposal)

    def test_registration_rejects_every_field_type_and_wrong_identity_or_hash(self):
        class StringSubclass(str):
            pass
        for name in ('registration_id', 'provenance', 'host_factory_key', 'baseline_hash',
                     'candidate_hash', 'process_hash', 'policy_hash'):
            original = getattr(self.registration, name)
            for value in (None, 1, '', StringSubclass(original), 'different', 'A' * 64, '0' * 64):
                with self.subTest(field=name, value=value):
                    self.assert_denied(registration=replace(self.registration, **{name: value}),
                                       reason='invalid_process_delta_registration')
        class Child(type(self.registration)):
            pass
        for bad in (Child(*[getattr(self.registration, n) for n in self.registration.__slots__]),
                    dict(registration_id='synthetic-window-readiness-delta-v1')):
            self.assert_denied(registration=bad, reason='invalid_process_delta_registration')

    def test_inventory_rejects_unsorted_duplicate_alias_missing_extra_and_mutable_values(self):
        class TupleSubclass(tuple):
            pass
        class StringSubclass(str):
            pass
        pins = self.registration.implementations
        variants = (tuple(reversed(pins)), pins[:-1], (*pins, ('extra.py', '0' * 64)),
            (*pins[:-1], pins[0]), list(pins), TupleSubclass(pins), (),
            (list(pins[0]), *pins[1:]), (TupleSubclass(pins[0]), *pins[1:]),
            ((StringSubclass(pins[0][0]), pins[0][1]), *pins[1:]),
            ((pins[0][0], StringSubclass(pins[0][1])), *pins[1:]),
            ((pins[0][0], 'f' * 63), *pins[1:]), ((pins[0][0], 'G' * 64), *pins[1:]))
        variants += tuple(((alias, pins[0][1]), *pins[1:]) for alias in
                          ('./__init__.py', '/__init__.py', 'a/../__init__.py', 'a\\__init__.py'))
        for pins in variants:
            with self.subTest(pins_type=type(pins)):
                self.assert_denied(registration=replace(self.registration, implementations=pins),
                                   reason='invalid_process_delta_registration')

    def test_uninitialized_registration_is_denied_before_material_decode(self):
        missing = object.__new__(type(self.registration))
        self.assert_denied(mat=replace(self.mat, source=b'invalid-json'),
                           registration=missing, reason='invalid_process_delta_registration')

    def test_sources_are_exact_nonempty_immutable_and_closed(self):
        class BytesSubclass(bytes):
            pass
        sources = self.mat.adapter_sources
        variants = (list(sources), tuple(reversed(sources)), sources[:-1],
            (*sources, ('extra.py', b'x')), (*sources[:-1], sources[0]),
            (('./' + sources[0][0], sources[0][1]), *sources[1:]),
            ((sources[0][0], b''), *sources[1:]),
            ((sources[0][0], b'drift'), *sources[1:]), (list(sources[0]), *sources[1:]),
            ((sources[0][0], bytearray(b'x')), *sources[1:]),
            ((sources[0][0], BytesSubclass(b'x')), *sources[1:]))
        for sources in variants:
            with self.subTest(sources_type=type(sources)):
                self.assert_denied(mat=replace(self.mat, adapter_sources=sources))

    def test_source_bounds_are_inclusive_and_precede_json_decode(self):
        sources = self.mat.adapter_sources
        for size, accepted in ((1048576, True), (1048577, False)):
            changed = ((sources[0][0], b'x' * size), *sources[1:])
            reg = unit_registration(changed)
            mat = replace(self.mat, adapter_sources=changed)
            if accepted:
                AdaptationFactory(window_context(mat, reg))
            else:
                self.assert_denied(mat=replace(mat, source=b'invalid-json'), registration=reg,
                                   reason='material_limit_exceeded')
        for size, accepted in ((8388608, True), (8388609, False)):
            # 7 full MiB plus one almost-full file, leaving 78 nonempty files.
            changed = tuple((path, b'x' * (1048576 if i < 7 else
                            size - 7 * 1048576 - 78 if i == 7 else 1))
                            for i, (path, _) in enumerate(sources))
            self.assertEqual(sum(len(raw) for _, raw in changed), size)
            reg = unit_registration(changed)
            mat = replace(self.mat, adapter_sources=changed)
            if accepted:
                AdaptationFactory(window_context(mat, reg))
            else:
                self.assert_denied(mat=replace(mat, source=b'invalid-json'), registration=reg,
                                   reason='material_limit_exceeded')

    def test_registration_modes_conflict_before_decoding_material(self):
        context = window_context(replace(self.mat, source=b'invalid-json'), self.registration)
        with self.assertRaises(FactoryDenied) as caught:
            AdaptationFactory(replace(context, implementation_registration=object()))
        self.assertEqual(caught.exception.reason, 'conflicting_implementation_registrations')

    def test_semantic_siblings_and_unrelated_material_are_rejected(self):
        for path, value in ((('profile_id',), 'forged-window'),
                (('capabilities', 'reschedule', 'timeout_seconds'), 9),
                (('processes', 'reschedule_window', 'prerequisites', -1, 'expected'), 'S1'),
                (('processes', 'reschedule_exact', 'process_id'), 'changed-sibling')):
            data = expected_candidate().model_dump(mode='json')
            target = data
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            candidate = rehashed(data)
            with self.subTest(path=path):
                self.assert_denied(mat=window_material(candidate, unit_sources()))
        self.assert_denied(mat=window_material(load_profile('flat-v1.3'), unit_sources()))

    def reviewed_unit_fixture(self, **receipt_overrides):
        # Fabricated complete contract evidence only, never executed qualification.
        factory = AdaptationFactory(window_context(self.mat, self.registration))
        proposal = factory.prepare_proposal(self.mat.source, load_profile('flat-v1.3'), self.mat.agent)
        body = dict(proposal_hash=proposal.proposal_hash, candidate_hash=self.registration.candidate_hash,
            baseline_hash=self.registration.baseline_hash, test_hash=proposal.test_hash,
            runner_id='j05-unit-runner', provenance='local_controlled_synthetic',
            execution_id='non-executing-unit-contract', executed_at='2026-10-10T09:00:00+00:00',
            result='passed', cases=[dict(case_id='j05-unit-contract', result='passed', output_hash='a' * 64)])
        body.update(receipt_overrides)
        regression = RegressionEvidence(cj(body))
        digest = fingerprint(body)
        approval = HumanReviewApproval.model_validate(dict(proposal_hash=proposal.proposal_hash,
            regression_hash=digest, reviewer_id='unit-human', proof_reference='unit-review',
            scope=['review_profile', 'review_process'], decision='approved',
            reviewed_at='2026-10-10T09:00:00+00:00', mode='simulated'))
        event = HumanReviewEvent('unit-review', cj(approval.model_dump(mode='json')), 'human', 'synthetic_rehearsal')
        factory = AdaptationFactory(window_context(self.mat, self.registration,
                                                   regressions=(regression,), reviews=(event,)))
        return factory, proposal, digest, approval

    def test_staged_commitment_is_exact_and_retains_remaining_limitations(self):
        factory, proposal, digest, approval = self.reviewed_unit_fixture()
        packet = factory.check_proposal(proposal, digest)
        stage = factory.release_profile(packet, approval, [])
        body = factory._resolve(proposal)[4]
        manifest = json.loads(stage.manifest)
        self.assertEqual(manifest['process_delta_registration'], body['process_delta_registration'])
        self.assertNotIn('implementation_registration', manifest)
        self.assertEqual(stage.status, 'staged_simulation')
        self.assertNotIn('changed_process_adapter_dispatch_unavailable', stage.unmet_requirements)
        self.assertEqual(len(stage.unmet_requirements), 7)
        body['process_delta_registration']['candidate_hash'] = '0' * 64
        self.assertEqual(factory.release_profile(packet, approval, []).manifest, stage.manifest)

    def test_every_receipt_binding_and_provenance_field_denies_mutation(self):
        for key, value in (
                ('proposal_hash', '0' * 64), ('candidate_hash', '0' * 64),
                ('baseline_hash', '0' * 64), ('test_hash', '0' * 64),
                ('runner_id', 'foreign'), ('provenance', 'actual'),
                ('execution_id', ''), ('executed_at', '2026-10-11T09:00:00+00:00'),
                ('result', 'failed'), ('cases', []),
                ('cases', [dict(case_id='j05-unit-contract', result='passed', output_hash='invalid')])):
            with self.subTest(field=key):
                factory, proposal, digest, _ = self.reviewed_unit_fixture(**{key: value})
                with self.assertRaises(FactoryDenied):
                    factory.check_proposal(proposal, digest)
