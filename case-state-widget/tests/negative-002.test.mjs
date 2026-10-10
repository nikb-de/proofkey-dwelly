import assert from 'node:assert/strict';
import fs from 'node:fs';
import {validateCase,presentStep} from '../viewer.js';
const read=p=>JSON.parse(fs.readFileSync(new URL(p,import.meta.url),'utf8'));
const x=read('../examples/case-002-channel-failure.json');
const base=read('../case-002.json');
validateCase(x);
assert.equal(x.steps.length,7);
const snapshots=[x.initial_state,...x.steps.map(s=>s.state_after)];
for(const [i,s] of snapshots.entries()){
 assert.equal(s.messages.length,i);
 assert.equal(s.success_criteria.filter(c=>c.status==='met').length,i===7?4:i>=4?1:0);
 if(i<7){assert.equal(s.result,null);assert.notEqual(s.agent_state.status,'completed')}
 if(i<5)assert.ok(!JSON.stringify(s).includes('Session expired'));
 for(const c of s.success_criteria)for(const event of c.evidence_event_ids)assert.ok(Number(event)<=i);
}
assert.deepEqual(snapshots[4].messages,base.steps[3].state_after.messages);
assert.equal(presentStep(x,3).agent.waiting_for[0].actor_id,'recipient');
assert.equal(presentStep(x,5).agent.status,'ready');
assert.equal(snapshots[5].requests.r2.status,'outcome_unknown');
assert.equal(snapshots[5].decision.selected_option,null);
assert.deepEqual(snapshots[5].decision.options.filter(o=>o.allowed).map(o=>o.id),['verify_saved_state']);
assert.equal(presentStep(x,6).agent.status,'waiting');
assert.equal(presentStep(x,6).agent.waiting_for[0].actor_id,'address_desk');
assert.equal(snapshots[6].requests.r4.status,'awaiting_response');
assert.equal(snapshots[6].decision.selected_option,'verify_saved_state');
assert.equal(presentStep(x,7).agent.status,'completed');
assert.deepEqual(snapshots[7].result.evidence_event_ids,['007']);
assert.deepEqual(x.steps.filter(s=>s.event.type==='message_sent').map(s=>s.event.id),['003','006']);
assert.equal(snapshots[5].messages.at(-1).from_actor,'correction_form');
assert.match(snapshots[5].annotations.at(-1).text,/09:54/);
console.log('PASS: negative 002, seven source events, unknown outcome → verify → wait for executor → confirmed; no early success or invented re-submission.');
