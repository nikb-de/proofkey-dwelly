"""Exercise the standalone CLI against real files and adversarial mutations."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ValidatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / 'schemas', self.root / 'schemas')
        provenance = dict(source_kind='synthetic', source_id='fixture-1', collected_at='2026-10-10T10:00:00Z')
        review = dict(status='unreviewed', reviewer_id=None, reviewed_at=None)
        self.input = dict(schema_version='proofkey-decision-input-v1', visibility='model_visible', input_id='input-0',
            provenance=copy.deepcopy(provenance), source={}, snapshot=dict(schema_version='dwelly-local-case-v1',
            source_mode='local_fixture', case_id='case-1', links=dict(order_id='order-1', customer_id='customer-1', operator_id='operator-1'),
            participants=['customer-1', 'operator-1'], language='en', revision=0, events=[], previous_snapshot_hash=None,
            snapshot_hash='', runtime_binding=None, needs_analysis=True, analysis_status='pending_not_started', authorization='unverified', operational_effects=0))
        self.label = dict(schema_version='proofkey-decision-label-v1', visibility='evaluator_only', label_id='label-0', input_id='input-0',
            source={}, expected_disposition='request_information', rationale='Synthetic test annotation.', review=review, provenance=copy.deepcopy(provenance))
        self.episode = dict(schema_version='proofkey-episode-v1', visibility='evaluator_only', episode_id='episode-1', case_id='case-1',
            input_ids=['input-0'], label_ids=['label-0'], transition_ids=[], review=copy.deepcopy(review), provenance=copy.deepcopy(provenance))
        self.criteria = dict(schema_version='proofkey-eval-criteria-v1', visibility='evaluator_only',
            input_id='input-0', source=copy.deepcopy(self.input['source']),
            acceptable_dispositions=['request_information'], required_details=[], required_evidence_ids=[],
            forbidden_claims=[], forbidden_actions=[], missing_information=[], authority_notes='Proposal only.',
            ambiguities=[], human_control='proposal_only', risk_level='low', follow_up_trigger=None)
        self.row = dict(schema_version='proofkey-dataset-row-v1', input_id='input-0',
            family_id='family-1', episode_id=self.episode['episode_id'], split='train', origin='synthetic',
            as_of='2026-10-10T10:00:00Z', annotation_status='assistant_authored_draft', tags=[], exclusions=[],
            files={k: 'examples/' + folder + '/one.json' for k, folder in
                   [('input', 'inputs'), ('label', 'labels'), ('criteria', 'criteria'), ('episode', 'episodes')]}, sha256={})
        self.refresh_snapshot()
        self.write()

    def write(self):
        for kind in self.row['files']:
            path = self.root / self.row['files'][kind]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(getattr(self, kind)), encoding='utf-8')
            self.row['sha256'][kind] = hashlib.sha256(path.read_bytes()).hexdigest()
        (self.root / 'manifest.jsonl').write_text(json.dumps(self.row) + '\n')

    def run_cli(self):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/validate.py'), str(self.root)], capture_output=True, text=True)
        self.assertNotIn('Traceback', result.stderr + result.stdout)
        return result

    def rejected(self):
        result = self.run_cli()
        self.assertNotEqual(result.returncode, 0)
        return json.loads(result.stdout)['errors'][0]

    def refresh_snapshot(self):
        snapshot = self.input['snapshot']
        snapshot['snapshot_hash'] = hashlib.sha256(json.dumps({k:v for k,v in snapshot.items() if k != 'snapshot_hash'}, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
        self.input['source'] = {key: snapshot[key] for key in ('case_id', 'revision', 'snapshot_hash')}
        self.label['source'] = copy.deepcopy(self.input['source'])
        self.criteria['source'] = copy.deepcopy(self.input['source'])

    def test_family_cross_split_is_rejected(self):
        first_row = copy.deepcopy(self.row)
        self.input['input_id'] = self.label['input_id'] = self.criteria['input_id'] = self.row['input_id'] = 'input-2'
        self.label['label_id'] = 'label-2'
        self.input['snapshot']['case_id'] = self.episode['case_id'] = 'case-2'
        self.episode.update(episode_id='episode-2', input_ids=['input-2'], label_ids=['label-2'])
        self.row.update(episode_id='episode-2', split='test')
        for kind in self.row['files']:
            self.row['files'][kind] = self.row['files'][kind].replace('one.json', 'two.json')
        self.refresh_snapshot()
        self.write()
        with (self.root / 'manifest.jsonl').open('a') as out:
            out.write(json.dumps(first_row) + '\n')
        self.assertIn('cross-split leakage: family', self.rejected())

    def test_chain_corruption_with_valid_snapshot_and_file_hashes(self):
        package = ROOT
        shutil.copytree(package / 'examples', self.root / 'examples', dirs_exist_ok=True)
        rows = [json.loads(line) for line in (package / 'manifest.jsonl').read_text().splitlines()]
        # Use the actual independently generated multi-revision example package.
        target = next(row for row in rows if json.loads((self.root / row['files']['input']).read_text())['source']['revision'] == 1)
        inp_path = self.root / target['files']['input']
        inp = json.loads(inp_path.read_text())
        inp['snapshot']['previous_snapshot_hash'] = '0' * 64
        inp['snapshot']['snapshot_hash'] = hashlib.sha256(json.dumps({k:v for k,v in inp['snapshot'].items() if k != 'snapshot_hash'}, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
        inp['source']['snapshot_hash'] = inp['snapshot']['snapshot_hash']
        for kind in ('input', 'label', 'criteria'):
            path = self.root / target['files'][kind]
            value = inp if kind == 'input' else json.loads(path.read_text())
            value['source'] = copy.deepcopy(inp['source'])
            path.write_text(json.dumps(value))
            target['sha256'][kind] = hashlib.sha256(path.read_bytes()).hexdigest()
        (self.root / 'manifest.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in rows))
        self.assertIn('broken previous snapshot hash chain', self.rejected())

    def test_valid_and_reviewed_counts(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)['eligible_reviewed_rows'], 0)
        self.row['annotation_status'] = 'human_reviewed'
        self.label['review'] = dict(status='reviewed', reviewer_id='reviewer-1', reviewed_at='2026-10-10T11:00:00Z')
        self.write()
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)['eligible_reviewed_rows'], 1)

    def test_bad_hash(self):
        (self.root / self.row['files']['input']).write_text('{}')
        self.rejected()

    def test_missing_dependencies_fail_without_traceback(self):
        result = subprocess.run([sys.executable, '-S', str(ROOT / 'scripts/validate.py')], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('Traceback', result.stderr + result.stdout)
        self.assertFalse(json.loads(result.stdout)['valid'])

    def test_semantic_mutations_rejected_after_rehash(self):
        mutations = [
            lambda: self.input.update(expected_disposition='hold'),
            lambda: self.label['source'].update(case_id='different-case'),
            lambda: self.row.update(annotation_status='human_reviewed'),
            lambda: self.episode['input_ids'].append('missing-input'),
            lambda: self.criteria['required_evidence_ids'].append('invisible-event'),
            lambda: self.criteria.update(acceptable_dispositions=['hold']),
            lambda: self.row.update(as_of='2026-10-10T10:00:00'),
            lambda: self.input['snapshot']['links'].update(customer_id='missing-participant'),
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                saved = copy.deepcopy((self.input, self.label, self.episode, self.criteria, self.row))
                mutation()
                self.write()
                self.rejected()
                self.input, self.label, self.episode, self.criteria, self.row = saved

    def test_duplicate_row(self):
        with (self.root / 'manifest.jsonl').open('a') as out:
            out.write(json.dumps(self.row) + '\n')
        self.rejected()

    def test_malformed_and_empty_manifest(self):
        for value in ['{invalid\n', '']:
            (self.root / 'manifest.jsonl').write_text(value)
            self.rejected()

    def test_path_traversal(self):
        self.row['files']['input'] = '../outside.json'
        (self.root / 'manifest.jsonl').write_text(json.dumps(self.row) + '\n')
        self.rejected()

    def test_orphan(self):
        (self.root / 'examples/inputs/orphan.json').write_text('{}')
        self.rejected()

    def test_symlink_escape(self):
        target = self.root.parent / (self.root.name + '-outside.json')
        target.write_text('{}')
        self.addCleanup(target.unlink)
        path = self.root / self.row['files']['input']
        path.unlink()
        path.symlink_to(target)
        self.rejected()

    def test_future_event_and_missing_previous_revision(self):
        event = dict(event_id='event-1', occurred_at='2026-10-11T10:00:00Z', channel='chat',
                     sender_id='customer-1', recipient_ids=['operator-1'], kind='message', text='Hello', media=None)
        self.input['snapshot'].update(revision=1, events=[event], previous_snapshot_hash='0' * 64)
        snapshot = self.input['snapshot']
        snapshot['snapshot_hash'] = hashlib.sha256(json.dumps({k:v for k,v in snapshot.items() if k != 'snapshot_hash'}, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
        self.input['source'].update(revision=1, snapshot_hash=snapshot['snapshot_hash'])
        self.label['source'] = copy.deepcopy(self.input['source'])
        self.criteria['source'] = copy.deepcopy(self.input['source'])
        self.write()
        self.assertIn('event occurs after as_of', self.rejected())
        event['occurred_at'] = '2026-10-10T09:00:00Z'
        self.refresh_snapshot()
        self.write()
        self.assertIn('missing previous revision', self.rejected())

    def test_unknown_participant_with_valid_hash(self):
        self.input['snapshot']['links']['customer_id'] = 'unknown-person'
        self.refresh_snapshot()
        self.write()
        self.assertIn('linked identity missing', self.rejected())


if __name__ == '__main__':
    unittest.main()
