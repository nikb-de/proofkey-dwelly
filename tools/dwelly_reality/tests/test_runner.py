import importlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


class RealityTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.source = self.root / 'source'
        case = self.source / '001'
        case.mkdir(parents=True)
        (case / 'index.md').write_text('# Test\nDecision time: `2026-10-14T08:50:00+01:00`.\n')
        (case / 'history.md').write_text('## E01 | 2026-10-14T08:00:00+01:00 | email\n\nFrom: Customer → To: Desk\nKnown at desk: `2026-10-14T08:00:00+01:00`\n\nPlease review.\n\n## E02 | 2026-10-14T09:00:00+01:00 | email\n\nFrom: Desk → To: Customer\nKnown at desk: `2026-10-14T09:00:00+01:00`\n\nHIDDEN FUTURE\n')

    def api(self):
        return importlib.import_module('tools.dwelly_reality.runner')

    def prepare(self):
        return self.api().prepare(self.source, self.root/'prepared', expected_cases=1)

    def test_prepare_retains_source_hashes_and_excludes_future(self):
        result = self.prepare()
        self.assertEqual(result['case_count'], 1)
        evidence = json.loads((self.root/'prepared/inputs/001.json').read_text())
        self.assertNotIn('HIDDEN FUTURE', json.dumps(evidence))
        self.assertEqual(evidence['messages'][1]['event_id'], 'E01')
        self.assertTrue(result['source_files']['001/history.md'])
        self.assertEqual(result['prompt_system_sha256'], 'f95514995513eed9c9591126daf10c141be1c1a4a50a4c17145950b0e46785ce')

    def test_prepare_refuses_replacing_existing_output(self):
        self.prepare()
        with self.assertRaises(FileExistsError): self.prepare()

    def test_explicit_existing_system_bytes_are_preserved(self):
        system=self.root/'system.txt'; system.write_text('Frozen existing prompt.\n')
        result=self.api().prepare(self.source,self.root/'prepared',expected_cases=1,system_file=system,effort='high')
        prompt=json.loads((self.root/'prepared/prompts/001.json').read_text())
        self.assertEqual(prompt['system'],'Frozen existing prompt.\n')
        self.assertEqual(result['effort'],'high')

    def test_effort_payload_preserves_existing_fields(self):
        result=self.api().effort_payload('anthropic',{'model':'claude','max_tokens':12},'high')
        self.assertEqual(result,{'model':'claude','max_tokens':12,'thinking':{'type':'adaptive'},'output_config':{'effort':'high'}})

    def test_formatter_quotes_only_recorded_decision_and_uncertainty(self):
        record={'status':'succeeded','error':None,'dispatch_attempts':1,'candidate':{'state':'ready',
            'next_action':{'type':'operator_review','description':'Exact model review.'},'uncertainty':['Exact unknown.']}}
        answer=self.api().format_answer('001',record,{'input_hash':'abc','derivatives':[]})
        self.assertIn('## Decision (proposed)',answer)
        self.assertIn('Exact model review.',answer)
        self.assertIn('Exact unknown.',answer)
        self.assertIn('Business operations executed: 0',answer)

    def test_formatter_displays_proposed_actors_and_waiting_names(self):
        evidence={'our_actor_id':'desk','actors':[{'id':'desk','name':'Desk'}, {'id':'customer','name':'Customer'}]}
        record={'status':'succeeded','error':None,'candidate':{'state':'waiting','waiting_for':['customer'],
            'next_action':{'type':'wait','target_actor_id':'customer','description':'Await reply.'}}}
        answer=self.api().format_answer('001',record,{'input_hash':'abc'},evidence)
        self.assertIn('Proposed action type: `wait`',answer)
        self.assertIn('Proposed target: `customer` — Customer',answer)
        self.assertIn('Our actor: `desk` — Desk',answer)
        self.assertIn('Waiting for: `customer` — Customer',answer)
        self.assertNotIn('REVIEW: self_target',answer)

    def test_self_target_review_is_display_only_and_action_specific(self):
        api=self.api()
        for kind in ('propose_forwarding','request_information','request_readback','operator_review'):
            with self.subTest(kind=kind):
                record={'candidate':{'next_action':{'type':kind,'target_actor_id':'desk'}}}
                original=json.dumps(record)
                warnings=api._review_warnings(record,{'our_actor_id':'desk'})
                self.assertEqual(bool(warnings),kind!='operator_review')
                self.assertEqual(json.dumps(record),original)
        self.assertEqual(api._review_warnings({'candidate':{'next_action':{
            'type':'propose_forwarding','target_actor_id':'customer'}}},{'our_actor_id':'desk'}),[])

    def test_failed_response_diagnostics_distinguish_json_and_contract(self):
        api=self.api()
        for text,expected in (('{broken','invalid_json_output'),('{}','rejected_output_contract'),
                              ('```json\n{}\n```','rejected_output_contract')):
            with self.subTest(text=text):
                record={'status':'failed','candidate':None,'error':'invalid_model_output','response':{'text':text}}
                original=json.dumps(record)
                answer=api.format_answer('001',record,{'input_hash':'abc'})
                self.assertIn('REVIEW: '+expected,answer)
                self.assertIn('Status: `failed`. Error: `invalid_model_output`',answer)
                self.assertEqual(json.dumps(record),original)

    def test_export_retained_025_and_014_exposes_defects_without_repair(self):
        api=self.api(); prepared=self.root/'retained'; profile='anthropic-claude-sonnet-5-5'
        items=[]; originals={}
        for case_id in ('025','014'):
            source=api.ROOT/'ANSWERS'/case_id
            evidence=json.loads((source/'INPUT.json').read_text())
            record=json.loads((source/'SOURCE_RESULT.json').read_text())
            originals[case_id]=record
            items.append({'case_id':case_id,'input_hash':evidence['input_hash']})
            api.save(prepared/'inputs'/(case_id+'.json'),evidence)
            api.save(prepared/'runs'/profile/case_id/'result.json',record)
        api.save(prepared/'manifest.json',{'cases':items,'source_commit':'retained',
            'code_commit':'retained','code_files':{},'source_files':{}})
        output=self.root/'exported'
        result=api.export(prepared,output,profile)
        self.assertEqual(result['exported_cases'],2)
        answer=(output/'025/ANSWER.md').read_text()
        self.assertIn('Proposed action type: `propose_forwarding`',answer)
        self.assertIn('Proposed target: `actor-02` — Vellora escalation desk',answer)
        self.assertIn('Our actor: `actor-02` — Vellora escalation desk',answer)
        self.assertIn('REVIEW: self_target',answer)
        answer=(output/'014/ANSWER.md').read_text()
        self.assertIn('REVIEW: invalid_json_output',answer)
        self.assertIn('No accepted model output.',answer)
        self.assertIn('Status: `failed`. Error: `invalid_model_output`',answer)
        for case_id,original in originals.items():
            self.assertEqual(json.loads((output/case_id/'SOURCE_RESULT.json').read_text()),original)
            self.assertEqual(json.loads((api.ROOT/'ANSWERS'/case_id/'SOURCE_RESULT.json').read_text()),original)
            candidate=json.loads((output/case_id/'ANSWER.md').read_text().split('## Exact retained candidate\n\n```json\n')[1].split('\n```')[0])
            self.assertEqual(candidate,original['candidate'])

    def test_deadline_record_has_zero_dispatch_attempts(self):
        self.prepare(); api=self.api()
        evidence=json.loads((self.root/'prepared/inputs/001.json').read_text())
        settings=json.loads((self.root/'prepared/profiles.json').read_text())
        profile=next(p for p in settings['profiles'] if p['id']=='anthropic-claude-sonnet-5-5')
        prompt=json.loads((self.root/'prepared/prompts/001.json').read_text())
        result=api._call(self.root/'deadline',evidence,profile,settings,prompt,deadline=0)
        self.assertEqual(result['dispatch_attempts'],0)
        self.assertEqual(result['error'],'batch_deadline_before_dispatch')

    def test_wire_capture_and_success_preserve_actual_output_without_credentials(self):
        self.prepare(); api=self.api()
        answer={'state':'unknown','waiting_for':[],'next_action':{'type':'operator_review','target_actor_id':None,'description':'Review source.'},'evidence_event_ids':[],'uncertainty':['Unverified source.']}
        body={'id':'msg_test','model':'claude-sonnet-5-5','stop_reason':'end_turn','usage':{'input_tokens':7,'output_tokens':8},'content':[{'type':'text','text':json.dumps(answer)}]}
        class Response:
            status=200
            headers={}
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def read(self,*args): return json.dumps(body).encode()
        with patch.dict('os.environ',{'ANTHROPIC_API_KEY':'SECRET-TEST-KEY','ANTHROPIC_WORKSPACE_ID':'wrkspc_test'}), patch.object(api.providers,'_open',return_value=Response()):
            result=api.run(self.root/'prepared',['anthropic-claude-sonnet-5-5'],live=True)
        self.assertEqual(result['succeeded'],1)
        record=json.loads((self.root/'prepared/runs/anthropic-claude-sonnet-5-5/001/result.json').read_text())
        wire=(self.root/'prepared/runs/anthropic-claude-sonnet-5-5/001/wire.json').read_text()
        self.assertEqual(record['response']['text'],json.dumps(answer))
        self.assertEqual(record['response']['observed_model'],'claude-sonnet-5-5')
        self.assertIn('response_body_utf8',wire)
        self.assertNotIn('SECRET-TEST-KEY',wire)

    def test_live_requires_opt_in(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError, 'live_opt_in_required'):
            self.api().run(self.root/'prepared', ['anthropic-claude-sonnet-5-5'], live=False)

    def test_failed_call_is_preserved_and_never_retried_or_secret_leaked(self):
        self.prepare()
        api = self.api()
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY':'SECRET-TEST-KEY','ANTHROPIC_WORKSPACE_ID':'wrkspc_test'}), patch.object(api.providers, 'complete', side_effect=api.providers.ProviderError('timeout')):
            result=api.run(self.root/'prepared', ['anthropic-claude-sonnet-5-5'], live=True)
            self.assertEqual(result['calls'], 1)
            second=api.run(self.root/'prepared', ['anthropic-claude-sonnet-5-5'], live=True)
            self.assertEqual(second['calls'], 0)
        record=json.loads((self.root/'prepared/runs/anthropic-claude-sonnet-5-5/001/result.json').read_text())
        self.assertEqual(record['status'],'failed')
        self.assertEqual(record['error'],'timeout')
        self.assertNotIn('SECRET-TEST-KEY', ''.join(p.read_text() for p in (self.root/'prepared').rglob('*.json')))
        api.export(self.root/'prepared',self.root/'ANSWERS','anthropic-claude-sonnet-5-5')
        self.assertIn('No accepted model output', (self.root/'ANSWERS/001/ANSWER.md').read_text())

if __name__=='__main__': unittest.main()
