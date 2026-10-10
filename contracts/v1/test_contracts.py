"""Executable structural contracts plus explicit CaseStore semantic checks.

Run from the repository root with python3 -m unittest discover -s contracts/v1.
JSON Schema does not implement cross-record identity, hashes or authorization.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from tools.dwelly_service.cases import CaseStore, CaseError
from tools.dwelly_service.store import JobStore

ROOT = Path(__file__).resolve().parent
NAMES = ('local-case', 'decision-input', 'decision-label', 'episode',
         'transition', 'decision-run', 'asset', 'analysis')


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.schemas = {}
        for name in NAMES:
            path = ROOT / 'schemas' / (name + '.schema.json')
            self.assertTrue(path.exists(), 'missing schema: ' + name)
            self.schemas[name] = json.loads(path.read_text())
        self.registry = Registry().with_resources(
            (schema['$id'], Resource.from_contents(schema)) for schema in self.schemas.values())

    def example(self, name):
        return json.loads((ROOT / 'examples' / (name + '.json')).read_text())

    def validator(self, name, definition=None):
        schema = self.schemas[name]
        if definition:
            schema = {'$ref': schema['$id'] + '#/$defs/' + definition}
        return Draft202012Validator(schema, registry=self.registry, format_checker=FormatChecker())

    def assert_invalid(self, name, value, definition=None):
        self.assertTrue(list(self.validator(name, definition).iter_errors(value)), value)

    def test_all_schemas_and_positive_examples(self):
        for name in NAMES:
            with self.subTest(name=name):
                Draft202012Validator.check_schema(self.schemas[name])
                self.validator(name).validate(self.example(name))

    def test_revision_is_zero_based(self):
        value = self.example('decision-input')
        self.assertEqual(value['source']['revision'], 0)
        value['source']['revision'] = -1
        self.assert_invalid('decision-input', value)

    def test_closed_fields_at_record_and_nested_boundaries(self):
        for name in NAMES:
            value = self.example(name)
            value['injected'] = True
            self.assert_invalid(name, value)
        value = self.example('decision-input')
        value['source']['labels'] = self.example('decision-label')
        self.assert_invalid('decision-input', value)

    def test_evaluator_labels_and_future_evidence_cannot_enter_input(self):
        for field in ('label', 'labels', 'episode', 'transitions', 'future_events', 'expected_action'):
            value = self.example('decision-input')
            value[field] = self.example('decision-label')
            self.assert_invalid('decision-input', value)
        value = self.example('decision-input')
        value['visibility'] = 'evaluator_only'
        self.assert_invalid('decision-input', value)

    def test_negative_examples(self):
        paths = list((ROOT / 'examples' / 'invalid').glob('*.json'))
        self.assertGreaterEqual(len(paths), 3)
        for path in paths:
            item = json.loads(path.read_text())
            with self.subTest(path=path.name):
                self.assert_invalid(item['schema'], item['value'], item.get('definition'))

    def test_actual_store_snapshots_hash_chain_and_declaration_append_contracts(self):
        with tempfile.TemporaryDirectory() as tmp:
            owner = JobStore(Path(tmp).resolve() / 'state')
            self.addCleanup(owner.close)
            store = CaseStore(owner)
            declaration = self.example('declaration')
            self.validator('local-case', 'declaration').validate(declaration)
            zero, created = store.create('create-1', declaration)
            self.assertTrue(created)
            self.assertEqual(zero, self.example('local-case'))
            body = self.example('append-request')
            self.validator('local-case', 'appendRequest').validate(body)
            one, _ = store.append(declaration['case_id'], 'append-1', body)
            for snapshot in (zero, one):
                self.validator('local-case').validate(snapshot)
                unhashed = {key: value for key, value in snapshot.items() if key != 'snapshot_hash'}
                digest = hashlib.sha256(json.dumps(unhashed, ensure_ascii=False, sort_keys=True,
                                                   separators=(',', ':'), allow_nan=False).encode()).hexdigest()
                self.assertEqual(snapshot['snapshot_hash'], digest)
                self.assertEqual(len(snapshot['events']), snapshot['revision'])
            self.assertEqual(one['previous_snapshot_hash'], zero['snapshot_hash'])
            source = self.example('decision-input')['source']
            self.assertEqual((source['case_id'], source['revision'], source['snapshot_hash']),
                             (zero['case_id'], zero['revision'], zero['snapshot_hash']))
            self.assertEqual(store.append(declaration['case_id'], 'append-1', body), (one, False))

    def test_store_rejects_structurally_valid_tampered_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            owner = JobStore(Path(tmp).resolve() / 'state')
            self.addCleanup(owner.close)
            store = CaseStore(owner)
            value, _ = store.create('create-1', self.example('declaration'))
            value['snapshot_hash'] = 'a' * 64
            # A valid hex string is not a valid content hash: schema validation
            # passes but the service must reject the corrupted stored record.
            self.validator('local-case').validate(value)
            encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
            with owner._connect() as connection:
                connection.execute('UPDATE case_snapshots SET snapshot=?', (encoded,))
            with self.assertRaises(CaseError) as caught:
                store.get(value['case_id'])
            self.assertEqual(caught.exception.code, 'case_storage_error')

    def test_versions_and_human_review_provenance_are_explicit(self):
        for name in NAMES:
            value = self.example(name)
            value['schema_version'] = 'unknown-v999'
            self.assert_invalid(name, value)
        value = self.example('decision-label')
        value['review']['status'] = 'reviewed'
        self.assert_invalid('decision-label', value)

    def test_example_record_source_links_match_the_frozen_snapshot(self):
        snapshot = self.example('local-case')
        expected = {key: snapshot[key] for key in ('case_id', 'revision', 'snapshot_hash')}
        for name in ('decision-input', 'decision-label', 'decision-run', 'asset', 'analysis'):
            self.assertEqual(self.example(name)['source'], expected, name)

    def test_event_shape_mime_limits_and_timestamp_parity(self):
        body = self.example('append-request')
        for kind, mime, maximum in [('photo', 'image/png', 10485760),
                                     ('voice_message', 'audio/mpeg', 26214400),
                                     ('call_recording', 'audio/webm', 26214400)]:
            value = deepcopy(body)
            value['event'].update(kind=kind, text=None, media={
                'asset_id': 'asset-1', 'sha256': 'a' * 64, 'mime_type': mime, 'size_bytes': maximum})
            self.validator('local-case', 'appendRequest').validate(value)
            value['event']['media']['size_bytes'] += 1
            self.assert_invalid('local-case', value, 'appendRequest')
        for field, invalid in [('text', '   '),
                               ('sender_id', '../unsafe'), ('recipient_ids', ['operator-1'] * 2)]:
            value = deepcopy(body)
            value['event'][field] = invalid
            self.assert_invalid('local-case', value, 'appendRequest')

    def test_declaration_semantics_remain_enforced_by_store(self):
        # JSON Schema cannot express linked participant membership; the actual
        # store is the semantic authority. This must never be claimed as schema-only parity.
        with tempfile.TemporaryDirectory() as tmp:
            owner = JobStore(Path(tmp).resolve() / 'state')
            self.addCleanup(owner.close)
            store = CaseStore(owner)
            value = self.example('declaration')
            value['participants'] = ['outsider-1', 'outsider-2']
            with self.assertRaises(CaseError):
                store.create('invalid', value)

    def test_typed_transition_conditions(self):
        value = self.example('transition')
        value['conditions'] = ['approved']
        self.assert_invalid('transition', value)
        value['conditions'] = [{'type': 'policy_approved', 'value': True}]
        self.assert_invalid('transition', value)

    def test_service_accepted_source_timestamps_remain_valid_without_normalization(self):
        for timestamp in ('2026-10-10T10:00:00+00:00:30', '2026-10-10X10:00:00+00:00'):
            with self.subTest(timestamp=timestamp), tempfile.TemporaryDirectory() as tmp:
                owner = JobStore(Path(tmp).resolve() / 'state')
                self.addCleanup(owner.close)
                store = CaseStore(owner)
                store.create('create-1', self.example('declaration'))
                body = self.example('append-request')
                body['event']['occurred_at'] = timestamp
                snapshot, _ = store.append('demo-1', 'append-1', body)
                self.assertEqual(snapshot['events'][0]['occurred_at'], timestamp)
                self.validator('local-case').validate(snapshot)

    def test_timestamp_date_and_timezone_semantics_remain_in_casestore(self):
        for timestamp in ('not-a-date', '2026-10-10T10:00:00'):
            with self.subTest(timestamp=timestamp), tempfile.TemporaryDirectory() as tmp:
                owner = JobStore(Path(tmp).resolve() / 'state')
                self.addCleanup(owner.close)
                store = CaseStore(owner)
                store.create('create-1', self.example('declaration'))
                body = self.example('append-request')
                body['event']['occurred_at'] = timestamp
                self.validator('local-case', 'append').validate(body)
                with self.assertRaises(CaseError):
                    store.append('demo-1', 'append-1', body)

    def test_asset_states_represent_observed_invalid_or_unreadable_files(self):
        for status, mime, size, category in (
                ('rejected', 'image/png', 0, 'empty'),
                ('rejected', 'image/png', 10485761, 'oversized'),
                ('rejected', 'text/plain', 50, 'unsupported_type'),
                ('failed', None, None, 'read_failed')):
            value = self.example('asset')
            value.update(status=status, error_category=category)
            value['media'].update(sha256=None, mime_type=mime, size_bytes=size)
            with self.subTest(category=category):
                self.validator('asset').validate(value)
                value['status'] = 'ready'
                self.assert_invalid('asset', value)

    def test_completed_analysis_requires_run_and_result_references(self):
        value = self.example('analysis')
        value['status'] = 'completed'
        self.assert_invalid('analysis', value)
        value['run_id'] = 'run-1'
        self.assert_invalid('analysis', value)
        value['result_id'] = 'result-1'
        self.validator('analysis').validate(value)

    def test_state_specific_positive_examples(self):
        for name in ('asset-empty', 'asset-oversized', 'asset-unsupported_type',
                     'asset-read_failed', 'asset-ready'):
            self.validator('asset').validate(self.example(name))
        self.validator('analysis').validate(self.example('analysis-completed'))
        self.validator('analysis', 'result').validate(self.example('analysis-result'))

    def test_connected_episode_contains_two_immutable_revisions(self):
        bundle = self.example('connected-episode')
        inputs = {item['input_id']: item for item in bundle['inputs']}
        transitions = {item['transition_id']: item for item in bundle['transitions']}
        episode = bundle['episode']
        self.validator('episode').validate(episode)
        self.assertEqual(set(episode['input_ids']), set(inputs))
        self.assertEqual(set(episode['transition_ids']), set(transitions))
        labels = {item['label_id']: item for item in bundle['labels']}
        self.assertEqual(set(episode['label_ids']), set(labels))
        for label in labels.values():
            self.validator('decision-label').validate(label)
            self.assertEqual(label['source'], inputs[label['input_id']]['source'])
        for item in inputs.values():
            self.validator('decision-input').validate(item)
            self.assertEqual(item['source'], {key: item['snapshot'][key]
                                             for key in ('case_id', 'revision', 'snapshot_hash')})
        for edge in transitions.values():
            self.validator('transition').validate(edge)
            self.assertIn(edge['from_input_id'], inputs)
            self.assertIn(edge['to_input_id'], inputs)
        before, after = inputs['input-0']['snapshot'], inputs['input-1']['snapshot']
        self.assertEqual(before['events'], [])
        self.assertEqual(after['previous_snapshot_hash'], before['snapshot_hash'])
        self.assertEqual(len(after['events']), 1)
        with tempfile.TemporaryDirectory() as tmp:
            owner = JobStore(Path(tmp).resolve() / 'state')
            self.addCleanup(owner.close)
            store = CaseStore(owner)
            zero, _ = store.create('create-1', self.example('declaration'))
            one, _ = store.append('demo-1', 'append-1', self.example('append-request'))
            self.assertEqual(before, zero)
            self.assertEqual(after, one)

    def test_state_machine_edges_reference_declared_states(self):
        machines = json.loads((ROOT / 'state-machines.json').read_text())
        for name, machine in machines.items():
            if not isinstance(machine, dict):
                continue
            with self.subTest(machine=name):
                self.assertIn(machine['initial'], machine['states'])
                for edge in machine['transitions']:
                    self.assertIn(edge['from'], machine['states'])
                    self.assertIn(edge['to'], machine['states'])
        self.assertEqual(machines['operation_projection']['availability'],
                         'target_service_projection_not_runtime_wire_enum')

    def test_openapi_separates_existing_routes_and_resolves_local_schema_references(self):
        api = json.loads((ROOT / 'openapi.json').read_text())
        self.assertEqual(set(api['paths']), {'/healthz', '/v1/cases',
                                            '/v1/cases/{case_id}', '/v1/cases/{case_id}/events'})
        self.assertTrue(api['x-target-interfaces'])
        def check(value):
            if isinstance(value, dict):
                reference = value.get('$ref', '')
                if reference.startswith('schemas/'):
                    filename, _, pointer = reference.partition('#')
                    target = json.loads((ROOT / filename).read_text())
                    for part in pointer.strip('/').split('/') if pointer else []:
                        target = target[part.replace('~1', '/').replace('~0', '~')]
                    self.assertIsInstance(target, dict)
                for child in value.values():
                    check(child)
            elif isinstance(value, list):
                for child in value:
                    check(child)
        check(api)


if __name__ == '__main__':
    unittest.main()
