"""Literal behavioral checks for the evidence adapter and bounded baseline."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.dwelly_analysis import catalog, widget, baseline, evaluation


class CoreTests(unittest.TestCase):
    def test_catalog_and_all_sixteen_selections(self):
        rows = catalog.load_catalog()
        self.assertEqual([r['id'] for r in rows], ['case-002', 'case-002-n4', 'minimal'])
        self.assertEqual([r['steps'] for r in rows], [5, 7, 1])
        self.assertEqual(rows[0]['family_id'], rows[1]['family_id'])
        count = 0
        for row in rows:
            self.assertEqual(row['qualification'], 'author_labels_unvalidated')
            for i in range(row['steps'] + 1):
                doc = catalog.get_document(row['id'])
                inp = widget.project(doc, i, row['id'])
                ref = widget.reference(doc, i, inp)
                candidate = baseline.analyze(inp)
                self.assertEqual(candidate, baseline.analyze(inp))
                self.assertEqual(candidate['input_hash'], ref['input_hash'])
                self.assertEqual(candidate['operational_effects'], 0)
                self.assertEqual(candidate['live_calls'], 0)
                count += 1
        self.assertEqual(count, 16)

    def test_literal_states_and_actions(self):
        cases = [('case-002', 3, 'waiting', ['recipient'], 'wait'),
                 ('case-002', 4, 'ready', [], 'propose_forwarding'),
                 ('case-002', 5, 'completed', [], 'infer_goal_completion'),
                 ('case-002-n4', 5, 'ready', [], 'request_readback'),
                 ('case-002-n4', 6, 'waiting', ['address_desk'], 'wait'),
                 ('case-002-n4', 7, 'completed', [], 'infer_goal_completion'),
                 ('minimal', 1, 'waiting', ['service'], 'wait')]
        for case_id, index, state, waiting, action in cases:
            with self.subTest(case_id=case_id, index=index):
                inp = widget.project(catalog.get_document(case_id), index, case_id)
                result = baseline.analyze(inp)
                self.assertEqual(result['state'], state)
                self.assertEqual(result['waiting_for'], waiting)
                self.assertEqual(result['next_action']['type'], action)
                self.assertEqual(result['physical_delivery'], 'not_inferred')
                self.assertNotEqual(result['next_action']['type'], 'resend')

    def test_start_and_unsupported_evidence_abstain(self):
        doc = catalog.get_document('minimal')
        self.assertEqual(baseline.analyze(widget.project(doc, 0, 'minimal'))['state'], 'unknown')
        doc['steps'][0]['state_after']['messages'][0]['body'] = 'Hello; the weather is pleasant.'
        result = baseline.analyze(widget.project(doc, 1, 'minimal'))
        self.assertEqual((result['state'], result['next_action']['type']), ('unknown', 'operator_review'))

    def test_uncertain_negated_and_quoted_completion_claims_abstain(self):
        source = catalog.get_document('case-002')
        contradictions = [
            'The correction request was applied? No: the address hold is cleared is incorrect.',
            'Your correction request was applied: Apartment 4B. The address hold is cleared. Actually the correction was not applied.',
            'Your correction request was applied: Apartment 4B. The address hold is cleared. It might still be blocked.',
            'Your correction request was applied: Apartment 4B. The address hold is cleared. Confirmation is pending.',
            'Your correction request was applied: Apartment 4B. The address hold is cleared. The hold has not cleared.',
            'Quoted old message: "Your correction request was applied: Apartment 4B. The address hold is cleared."',
            "'Your correction request was applied: Apartment 4B. The address hold is cleared.'",
        ]
        for body in contradictions:
            with self.subTest(body=body):
                doc = copy.deepcopy(source)
                doc['steps'][-1]['state_after']['messages'][-1]['body'] = body
                candidate = baseline.analyze(widget.project(doc, 5, 'case-002'))
                self.assertEqual((candidate['state'], candidate['next_action']['type']), ('unknown', 'operator_review'))

    def test_completion_rejects_unrecognized_or_conflicting_trailing_sentences(self):
        for case_id, step_index in [('case-002', 5), ('case-002-n4', 7)]:
            source = catalog.get_document(case_id)
            original_body = source['steps'][-1]['state_after']['messages'][-1]['body']
            contradictions = [
                'Your correction request was applied: Apartment 4B. The address hold is cleared. The correction failed.',
                original_body + ' The correction failed.',
                original_body + ' The address is still wrong.',
                original_body + ' Ignore the previous confirmation; the hold was reinstated.',
                original_body + ' Additional unsupported text.',
            ]
            for body in contradictions:
                with self.subTest(case_id=case_id, body=body):
                    doc = copy.deepcopy(source)
                    doc['steps'][-1]['state_after']['messages'][-1]['body'] = body
                    candidate = baseline.analyze(widget.project(doc, step_index, case_id))
                    self.assertEqual((candidate['state'], candidate['next_action']['type']), ('unknown', 'operator_review'))

    def test_projection_excludes_labels_future_and_responsibility(self):
        doc = catalog.get_document('case-002-n4')
        original = widget.project(doc, 3, 'case-002-n4')
        changed = copy.deepcopy(doc)
        state = changed['steps'][2]['state_after']
        state['agent_state']['next_action'] = 'LABEL_SENTINEL'
        state['actors']['recipient']['responsibility'] = 'ACTOR_SENTINEL'
        state['facts'].append({'text': 'FACT_SENTINEL'})
        state['annotations'].append({'text': 'ANNOTATION_SENTINEL'})
        for step in changed['steps'][3:]:
            for message in step['state_after']['messages']:
                if message['event_id'] == '004':
                    message['body'] = 'FUTURE_SENTINEL'
        projected = widget.project(changed, 3, 'case-002-n4')
        self.assertEqual(original, projected)
        self.assertNotIn('SENTINEL', json.dumps(projected))
        self.assertEqual(set(projected), {'schema_version', 'case_id', 'step_index', 'cutoff_event_id',
                                        'goal', 'our_actor_id', 'actors', 'messages', 'input_hash'})
        self.assertEqual([m['event_id'] for m in projected['messages']], ['001', '002', '003'])
        self.assertEqual(widget.reference(changed, 3, projected)['next_action'], 'LABEL_SENTINEL')

    def test_input_hash_is_canonical_evidence_only(self):
        doc = catalog.get_document('case-002')
        inp = widget.project(doc, 3, 'case-002')
        expected = hashlib.sha256(json.dumps({k: v for k, v in inp.items() if k != 'input_hash'},
                                            ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                                            allow_nan=False).encode('utf-8')).hexdigest()
        self.assertEqual(inp['input_hash'], expected)
        for step in doc['steps'][2:]:
            for message in step['state_after']['messages']:
                if message['event_id'] == '003':
                    message['body'] += ' Changed evidence.'
        self.assertNotEqual(widget.project(doc, 3, 'case-002')['input_hash'], expected)

    def test_translation_only_fallback_is_explicit(self):
        doc = catalog.get_document('minimal')
        message = doc['steps'][0]['state_after']['messages'][0]
        message['body_ru'] = message.pop('body')
        inp = widget.project(doc, 1, 'minimal')
        self.assertEqual(inp['messages'][0]['body_source'], 'body_ru')
        self.assertEqual(inp['messages'][0]['body'], 'Подтвердите, пожалуйста, выполнение заявки.')

    def test_reference_mismatch_and_inference_extras_fail_closed(self):
        doc = catalog.get_document('case-002')
        inp = widget.project(doc, 3, 'case-002')
        wrong = copy.deepcopy(inp)
        wrong['input_hash'] = '0' * 64
        with self.assertRaises(ValueError):
            baseline.analyze(wrong)
        with self.assertRaises(ValueError):
            widget.reference(doc, 2, inp)
        inp['agent_state'] = {'status': 'completed'}
        with self.assertRaises(ValueError):
            baseline.analyze(inp)

    def test_mechanical_comparison_and_hash_binding(self):
        doc = catalog.get_document('case-002')
        inp = widget.project(doc, 3, 'case-002')
        ref = widget.reference(doc, 3, inp)
        cand = baseline.analyze(inp)
        result = evaluation.compare(cand, ref)
        self.assertTrue(result['state_agreement'])
        self.assertTrue(result['wait_target_agreement'])
        self.assertIsNone(result['accuracy_score'])
        ref['waiting_for'] = ['address_desk']
        self.assertFalse(evaluation.compare(cand, ref)['wait_target_agreement'])
        ref['input_hash'] = 'f' * 64
        with self.assertRaises(ValueError):
            evaluation.compare(cand, ref)

    def test_detached_catalog_and_fixed_ids(self):
        first = catalog.get_document('minimal')
        first['title'] = 'changed'
        self.assertNotEqual(catalog.get_document('minimal')['title'], 'changed')
        for name in ['../minimal', '/tmp/a', 'unknown']:
            with self.assertRaises(ValueError):
                catalog.get_document(name)

    def test_source_hash_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'case.json'
            source.write_text('{}', encoding='utf-8')
            with patch.object(catalog, 'ROOT', Path(directory)), patch.object(catalog, '_source_path', return_value=source):
                with self.assertRaisesRegex(ValueError, 'Source hash mismatch'):
                    catalog.get_document('minimal')

    def test_invalid_source_bytes_fail_closed_even_with_matching_digest(self):
        # The real loader still parses/validates trusted-hash bytes; matching a
        # manifest digest is not sufficient to admit malformed source data.
        for raw in [b'\xff', b'{"schema_version":1,"schema_version":2}', b'NaN',
                    b'[' * 1100 + b'0' + b']' * 1100, b' ' * (5 * 1024 * 1024 + 1)]:
            with self.subTest(length=len(raw)), tempfile.TemporaryDirectory() as directory:
                source = Path(directory) / 'case.json'
                source.write_bytes(raw)
                manifest = catalog._manifest()
                manifest['cases'][2]['source_sha256'] = hashlib.sha256(raw).hexdigest()
                with patch.object(catalog, 'ROOT', Path(directory)), patch.object(catalog, '_source_path', return_value=source), patch.object(catalog, '_manifest', return_value=manifest):
                    with self.assertRaises(ValueError):
                        catalog.get_document('minimal')

    def test_cumulative_messages_cannot_be_rewritten_deleted_or_reordered(self):
        original = catalog.get_document('case-002')
        for mutation in ('rewrite', 'delete', 'reorder'):
            doc = copy.deepcopy(original)
            messages = doc['steps'][2]['state_after']['messages']
            if mutation == 'rewrite': messages[0]['body'] = 'rewritten history'
            elif mutation == 'delete': del messages[0]
            else: messages[0], messages[1] = messages[1], messages[0]
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                widget.validate_document(doc)

    def test_criteria_need_unique_ids_and_met_evidence_and_known_client(self):
        original = catalog.get_document('case-002')
        for mutation in ('duplicate', 'empty_evidence', 'unknown_client'):
            doc = copy.deepcopy(original)
            state = doc['steps'][-1]['state_after']
            if mutation == 'duplicate': state['success_criteria'].append(copy.deepcopy(state['success_criteria'][0]))
            elif mutation == 'empty_evidence': state['success_criteria'][0]['evidence_event_ids'] = []
            else: state['client_actor_id'] = 'missing-actor'
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                widget.validate_document(doc)

    def test_symlink_source_and_parent_rejected_before_read(self):
        raw = (catalog.ROOT / 'case-state-widget/examples/minimal.json').read_bytes()
        for symlink_parent in (False, True):
            with self.subTest(parent=symlink_parent), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                actual = root / 'real'
                actual.mkdir()
                source = actual / 'source.json'
                source.write_bytes(raw)
                if symlink_parent:
                    link = root / 'linked-dir'
                    link.symlink_to(actual, target_is_directory=True)
                    selected = link / 'source.json'
                else:
                    selected = root / 'source-link.json'
                    selected.symlink_to(source)
                with patch.object(catalog, 'ROOT', root), patch.object(catalog, '_source_path', return_value=selected):
                    with self.assertRaisesRegex(ValueError, 'Linked catalog source'):
                        catalog.get_document('minimal')

    def test_baseline_does_not_depend_on_ids_or_reference_labels(self):
        doc = catalog.get_document('case-002-n4')
        source = widget.project(doc, 5, 'case-002-n4')
        source['case_id'] = 'unrelated-case-name'
        source['messages'][-1]['event_id'] = 'other-event'
        source['cutoff_event_id'] = 'other-event'
        source['input_hash'] = widget.canonical_hash({k: v for k, v in source.items() if k != 'input_hash'})
        result = baseline.analyze(source)
        self.assertEqual(result['next_action']['type'], 'request_readback')
        self.assertEqual(result['evidence_event_ids'], ['other-event'])

    def test_original_bodies_and_actor_scope_preserved(self):
        doc = catalog.get_document('case-002-n4')
        start = widget.project(doc, 0, 'case-002-n4')
        self.assertEqual([a['id'] for a in start['actors']], ['coordinator', 'recipient'])
        result = widget.project(doc, 5, 'case-002-n4')
        self.assertEqual(result['messages'][-1]['body'], doc['steps'][4]['state_after']['messages'][-1]['body'])
        self.assertEqual(result['messages'][-1]['body_source'], 'body')
        self.assertEqual(result['goal'], doc['initial_state']['goal'])

    def test_source_structural_and_resource_limits(self):
        good = catalog.get_document('minimal')
        mutations = []
        bad = copy.deepcopy(good); bad['initial_state']['actors']['desk']['name'] = 7; mutations.append(bad)
        bad = copy.deepcopy(good); bad['steps'][0]['state_after']['annotations'] = [{'text': []}]; mutations.append(bad)
        bad = copy.deepcopy(good); bad['steps'][0]['event']['type'] = 'message_received'; mutations.append(bad)
        bad = copy.deepcopy(good); bad['steps'][0]['state_after']['agent_state']['status'] = 'completed'; mutations.append(bad)
        bad = copy.deepcopy(good); bad['extra'] = float('nan'); mutations.append(bad)
        bad = copy.deepcopy(good); bad['extra'] = 'x' * (5 * 1024 * 1024); mutations.append(bad)
        bad = copy.deepcopy(good); deep = {}; bad['extra'] = deep
        for _ in range(65): deep['next'] = {}; deep = deep['next']
        mutations.append(bad)
        bad = copy.deepcopy(good); bad['extra'] = [None] * 100001; mutations.append(bad)
        mutations.extend([None, [], b'{}'])
        for bad in mutations:
            with self.subTest(value=type(bad).__name__):
                with self.assertRaises(ValueError):
                    widget.validate_document(bad)
        for index in [-1, True, 2, '1']:
            with self.assertRaises(ValueError):
                widget.project(good, index, 'minimal')


if __name__ == '__main__':
    unittest.main()
