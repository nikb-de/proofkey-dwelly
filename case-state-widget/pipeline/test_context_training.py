"""Regression checks for independent IDs, withheld evidence and pending actions."""
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))
from tools.dwelly_analysis import widget, model
from source import load_case
from compile import compile_case

DATA = ROOT / 'data/training-context-cases'


class ContextTrainingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entries = json.loads((DATA/'index.json').read_text())['cases']
        cls.pairs = [json.loads(line) for line in (DATA/'training.jsonl').read_text().splitlines()]

    def test_independent_cases_leave_parents_unchanged(self):
        self.assertEqual(len({e['case_id'] for e in self.entries}),3)
        for e in self.entries:
            self.assertNotEqual(e['case_id'], e['parent_case_id'])
            self.assertEqual(e['additional_complications'],1)
            parent = ROOT / f"case-state-widget/cases/{e['parent_case_id']}.json"
            self.assertEqual(hashlib.sha256(parent.read_bytes()).hexdigest(),e['source_parent_sha256'])

    def test_source_and_annotation_reproduce_catalog(self):
        for e in self.entries:
            cid = e['case_id']
            annotation = json.loads((ROOT/f'case-state-widget/annot/{cid}.json').read_text())
            document = json.loads((ROOT/f'case-state-widget/cases/{cid}.json').read_text())
            self.assertEqual(compile_case(annotation),document)
            self.assertEqual(document['steps'][-1]['event']['id'],e['cutoff_event_id'])
            self.assertEqual(len(load_case(cid)['events']),len(document['steps']))
            widget.validate_document(document)

    def test_training_input_has_no_reference_labels(self):
        self.assertEqual(len(self.pairs),3)
        for pair in self.pairs:
            self.assertEqual(set(pair),{'input','target'})
            value,target = pair['input'],pair['target']
            cid=value['case_id']
            self.assertEqual(value,json.loads((DATA/f'agent_inputs/{cid}.json').read_text()))
            self.assertEqual(target,json.loads((DATA/f'targets/{cid}.json').read_text()))
            widget.validate_input(value)
            model.parse(value,{'text':json.dumps(target)})
            self.assertFalse(set(value) & {'target','curation','provenance','annotations','author_limits'})
            self.assertEqual(value['messages'][-1]['event_id'],value['cutoff_event_id'])

    def test_missing_options_change_the_decision(self):
        pair = next(p for p in self.pairs if p['input']['case_id']=='012-N2-A1-MISSING')
        cid=pair['input']['case_id']
        document = json.loads((ROOT/f'case-state-widget/cases/{cid}.json').read_text())
        for hidden in ['09:00–12:00','14:00–17:00','2026-02-15']:
            self.assertNotIn(hidden,json.dumps(pair['input'],ensure_ascii=False))
            self.assertNotIn(hidden,json.dumps(document,ensure_ascii=False))
        self.assertEqual(pair['target']['next_action']['target_actor_id'],'dispatch')
        self.assertEqual(pair['target']['next_action']['type'],'request_information')
        self.assertEqual(pair['input']['cutoff_event_id'],'004')
        self.assertEqual(document['steps'][-1]['state_after']['agent_state']['status'],'ready')

    def test_long_context_preserves_pending_readback(self):
        pair = next(p for p in self.pairs if p['input']['case_id']=='002-N4-A1-LONG')
        messages=pair['input']['messages']
        self.assertEqual(len(messages),18)
        self.assertEqual([m['event_id'] for m in messages],[f'{i:03d}' for i in range(1,19)])
        self.assertEqual(sorted(m['timestamp'] for m in messages),[m['timestamp'] for m in messages])
        self.assertTrue(all('4B' not in m['body'] for m in messages[:12]))
        self.assertEqual(messages[-1]['from_actor'],'coordinator')
        self.assertEqual(messages[-1]['to_actor'],'address_desk')
        self.assertEqual(pair['target']['state'],'waiting')
        self.assertEqual(pair['target']['next_action']['type'],'wait')
        self.assertEqual(pair['target']['evidence_event_ids'],['017','018'])


if __name__ == '__main__':
    unittest.main()
