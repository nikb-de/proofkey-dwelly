import assert from 'node:assert/strict';
import fs from 'node:fs';
import {validateCase,diffStates,presentStep,renderJSON} from '../viewer.js';
const data=JSON.parse(fs.readFileSync(new URL('../case-002.json',import.meta.url),'utf8'));
validateCase(data);
function replay(state,patch){
 state=structuredClone(state);
 for(const op of patch){if(op.path===''){state=structuredClone(op.value);continue}
  const keys=op.path.slice(1).split('/').map(s=>s.replace(/~1/g,'/').replace(/~0/g,'~'));let parent=state;
  for(const key of keys.slice(0,-1))parent=parent[key];const key=keys.at(-1);
  if(op.op==='remove'){if(Array.isArray(parent))parent.splice(Number(key),1);else delete parent[key]}
  else if(op.op==='add'&&Array.isArray(parent))parent.splice(Number(key),0,structuredClone(op.value));else parent[key]=structuredClone(op.value);
 }return state;
}
const text=html=>html.replace(/<[^>]*>/g,'').replace(/&quot;/g,'"').replace(/&#39;/g,"'").replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&');
for(let i=0;i<=data.steps.length;i++){
 const p=presentStep(data,i),prior=i>1?data.steps[i-2].state_after:data.initial_state;
 assert.deepEqual(replay(prior,p.patch),p.state);
 assert.deepEqual(JSON.parse(text(renderJSON(p.state,p.patch))),p.state);
 assert.equal(p.state.messages.length,i);
 assert.equal(p.state.success_criteria.filter(c=>c.status==='met').length,i===5?3:i===4?1:0);
 if(i<4)assert.ok(!JSON.stringify(p.state).includes('4B'));
}
assert.equal(presentStep(data,3).agent.waiting_for[0].actor_id,'recipient');
assert.equal(presentStep(data,4).agent.status,'ready');
assert.equal(presentStep(data,5).agent.status,'completed');
for(const [a,b] of [[{'a/b':{'x~y':[1,2,3]}},{'a/b':{'x~y':[4]}}],[{x:{a:1}},{x:null,new:[true]}],[{a:[1]},{a:[1,2]}]])assert.deepEqual(replay(a,diffStates(a,b)),b);
assert.match(renderJSON({x:'<script>alert(1)</script>'},[]),/&lt;script&gt;/);
const other={schema_version:'case-step-viewer/1.0',title:'Проверка оборудования',initial_state:{case_id:'equipment-test',our_actor_id:'operator',actors:{operator:{name:'Саша',role:'Оператор'},workshop:{name:'Мастерская',role:'Исполнитель'}},goal:'Получить подтверждение ремонта',agent_state:{status:'ready',waiting_for:[],next_action:'Написать мастерской'},success_criteria:[],messages:[],facts:[]},steps:[]};
const sent=structuredClone(other.initial_state);sent.agent_state={status:'waiting',waiting_for:[{actor_id:'workshop',expected:'Подтверждение ремонта',request_id:'repair'}],next_action:'Проверить результат'};
sent.messages=[{event_id:'request-7',from_actor:'operator',to_actor:'workshop',channel:'Chat',body:'Подтвердите завершение ремонта.'}];
other.steps.push({event:{id:'request-7',type:'message_sent',title:'Запрос подтверждения',message_id:'request-7'},explanation:'Работу должен подтвердить исполнитель.',state_after:sent});
validateCase(other);assert.equal(presentStep(other,1).actor('workshop'),'Мастерская · Исполнитель');assert.equal(presentStep(other,1).agent.waiting_for[0].actor_id,'workshop');
validateCase(JSON.parse(fs.readFileSync(new URL('../examples/minimal.json',import.meta.url),'utf8')));
const bad=structuredClone(data);bad.steps[0].state_after.agent_state={status:'waiting',waiting_for:[]};assert.throws(()=>validateCase(bad),/кого и чего/);
const future=structuredClone(data);future.steps[0].state_after.success_criteria[0]={...future.steps[0].state_after.success_criteria[0],status:'met',evidence_event_ids:['004']};assert.throws(()=>validateCase(future),/ещё не наступило/);
const changed=structuredClone(data);changed.steps[1].state_after.messages[0].body='Changed';assert.throws(()=>validateCase(changed),/без изменения/);
assert.throws(()=>validateCase({}),/schema_version/);
const code=fs.readFileSync(new URL('../viewer.js',import.meta.url),'utf8');for(const word of ['Tarin','Iona','4B','Plover','DL-002','Copperfin'])assert.ok(!code.includes(word),word);
console.log('PASS: 6 snapshots, exact JSON/diffs incl. remove and escaped pointers; generic second case and waiting for executor; evidence boundaries, unsafe text escaping and validation errors.');

const readme=fs.readFileSync(new URL('../README.md',import.meta.url),'utf8');
const example=JSON.parse(readme.match(/```json\n([\s\S]*?)```/)[1]);
validateCase(example);
assert.deepEqual(example,JSON.parse(fs.readFileSync(new URL('../examples/minimal.json',import.meta.url),'utf8')));
console.log('PASS: README JSON matches the loadable minimal example.');
