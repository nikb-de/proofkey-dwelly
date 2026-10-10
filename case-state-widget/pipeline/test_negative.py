"""Dataset regressions: parent preservation, evidence, decisions and saved outcomes."""
import copy
import csv
import hashlib
import json
import re
import unittest
from pathlib import Path
from compile import compile_case
from source import NEG, load_case

W = Path(__file__).resolve().parents[1]
ROWS = list(csv.DictReader((NEG / 'index.csv').open(newline='')))


def read(folder, cid):
    return json.loads((W / folder / f'{cid}.json').read_text())


def comparable(state):
    s = copy.deepcopy(state)
    s.pop('case_id')
    s.pop('limits', None)
    if s.get('intake'):
        s['intake'].pop('source', None)
    return s


class NegativeDataset(unittest.TestCase):
    def test_complete_unique_coverage_and_reproducible_builds(self):
        self.assertEqual(len(ROWS), 275)
        self.assertEqual(len({r['branch'] for r in ROWS}), 275)
        for cid in sorted({r['case'] for r in ROWS} | {r['branch'] for r in ROWS}):
            with self.subTest(case=cid):
                a, d = read('annot', cid), read('cases', cid)
                self.assertEqual(a['lang'], 'en')
                self.assertEqual(compile_case(a), d)
                text = json.dumps(d, ensure_ascii=False)
                self.assertNotRegex(text, '[А-Яа-яЁё]')
                self.assertNotRegex(text, r'\bTODO\b')

    def test_all_retained_states_and_messages_are_the_reviewed_parent(self):
        for r in ROWS:
            with self.subTest(branch=r['branch']):
                base, branch = read('cases', r['case']), read('cases', r['branch'])
                keep = int(r['insert_after'])
                self.assertEqual(comparable(base['initial_state']), comparable(branch['initial_state']))
                for i in range(keep):
                    self.assertEqual(base['steps'][i]['event'], branch['steps'][i]['event'])
                    self.assertEqual(base['steps'][i]['explanation'], branch['steps'][i]['explanation'])
                    self.assertEqual(comparable(base['steps'][i]['state_after']), comparable(branch['steps'][i]['state_after']))

    def test_branch_source_fingerprints_and_exact_message_payloads(self):
        for r in ROWS:
            with self.subTest(branch=r['branch']):
                a, d, source = read('annot', r['branch']), read('cases', r['branch']), load_case(r['branch'])
                for name, digest in a['provenance']['source_sha256'].items():
                    self.assertEqual(hashlib.sha256((Path(source['folder']) / name).read_bytes()).hexdigest(), digest)
                events, messages = source['events'], d['steps'][-1]['state_after']['messages']
                self.assertEqual(len(events), int(r['insert_after']) + 3)
                self.assertEqual(len(events), len(messages))
                aliases = {n: aid for aid, actor in a['actors'].items() for n in actor['source_names']}
                for e, m in zip(events, messages):
                    self.assertEqual(e['body'], m['body'])
                    self.assertEqual(e['timestamp'], m['timestamp'])
                    self.assertEqual(aliases[e['meta']['From']], m['from_actor'])
                    recipients = [aliases[n.strip()] for n in e['meta']['To'].split(';')]
                    self.assertEqual(recipients, [m['to_actor']] + m.get('copy_to', []))

    def test_no_early_closure_or_prohibited_decision(self):
        for r in ROWS:
            with self.subTest(branch=r['branch']):
                d = read('cases', r['branch'])
                keep = int(r['insert_after'])
                divergence, action, final = [s['state_after'] for s in d['steps'][keep:]]
                self.assertEqual(divergence['agent_state']['status'], 'ready')
                self.assertIsNone(divergence['result'])
                self.assertIsNone(divergence['decision']['selected_option'])
                allowed = [o for o in divergence['decision']['options'] if o.get('allowed')]
                self.assertEqual(len(allowed), 1)
                self.assertEqual(allowed[0]['id'], action['decision']['selected_option'])
                self.assertIsNone(action['result'])
                self.assertNotEqual(action['agent_state']['status'], 'completed')
                self.assertEqual(final['agent_state']['status'], 'completed')
                self.assertEqual(final['result']['evidence_event_ids'], [d['steps'][-1]['event']['id']])
                self.assertTrue(all(c['status'] == 'met' for c in final['success_criteria']))
                self.assertTrue(all(c['status'] == 'pending' for c in final.get('prior_success_criteria', [])))

    def test_uncertain_operations_are_verified_before_repeating(self):
        checked = 0
        for r in ROWS:
            if r['expected_decision'] != 'VERIFY_FIRST':
                continue
            checked += 1
            with self.subTest(branch=r['branch']):
                d = read('cases', r['branch'])
                keep = int(r['insert_after'])
                new, action, final = [s['state_after'] for s in d['steps'][keep:]]
                self.assertTrue(any(q['status'] == 'outcome_unknown' for q in new['requests'].values()))
                self.assertEqual(action['agent_state']['status'], 'waiting')
                waiting = action['agent_state']['waiting_for'][0]
                self.assertEqual(action['requests'][waiting['request_id']]['type'], 'verification')
                self.assertNotIn('outcome_unknown', [q['status'] for q in final['requests'].values()])
        self.assertEqual(checked, 34)

    def test_deadline_expiry_does_not_answer_for_the_silent_party(self):
        for cid in ['002-N3', '003-N1', '008-N5', '009-N3', '018-N1', '041-N4', '046-N6']:
            with self.subTest(branch=cid):
                final = read('cases', cid)['steps'][-1]['state_after']
                q = final['requests']['branch_request']
                self.assertEqual(q['status'], 'superseded')
                self.assertNotIn('responded_by', q)

    def test_measured_information_is_not_a_customer_decision(self):
        for cid in ['002-N2', '009-N1', '043-N1', '043-N3']:
            with self.subTest(branch=cid):
                d = read('cases', cid)
                self.assertEqual(d['steps'][-2]['state_after']['requests']['branch_request']['type'], 'information')
        self.assertEqual(read('cases', '047-N1')['steps'][-2]['state_after']['requests']['branch_request']['type'], 'information')


if __name__ == '__main__':
    unittest.main(verbosity=2)
