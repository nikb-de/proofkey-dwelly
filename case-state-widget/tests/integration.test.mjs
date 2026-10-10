import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {validateCase, CaseStateViewer} from '../viewer.js';

const read = name => JSON.parse(fs.readFileSync(new URL(name, import.meta.url), 'utf8'));
const minimal = () => read('../examples/minimal.json');

test('all three original source documents remain valid', () => {
  for (const name of ['../case-002.json', '../examples/case-002-channel-failure.json', '../examples/minimal.json']) validateCase(read(name));
});
test('annotation source IDs must be an array even when every character is a valid event ID', () => {
  const data = minimal(); data.initial_state.annotations = [{text: 'unsafe', source_event_ids: ''}];
  assert.throws(() => validateCase(data), /source_event_ids/);
});
test('nested extras cannot bypass the depth budget', () => {
  const data = minimal(); let node = data;
  for (let i = 0; i < 66; i++) node = node.extra = {};
  assert.throws(() => validateCase(data), /depth|глубин/i);
});
test('completed state cannot retain a pending success criterion', () => {
  const data = minimal(); data.initial_state.agent_state.status = 'completed';
  assert.throws(() => validateCase(data), /completed|заверш/i);
});
test('completed state requires a nonempty set of supported criteria', () => {
  const data=minimal();data.initial_state.agent_state={status:'completed',waiting_for:[],next_action:null};
  data.initial_state.success_criteria=[];
  assert.throws(()=>validateCase(data),/completed|заверш/i);
});
test('completed state cannot retain a proposed next action', () => {
  const data=read('../case-002.json');data.steps.at(-1).state_after.agent_state.next_action='Send another message';
  assert.throws(()=>validateCase(data),/completed|заверш/i);
});
test('actor and optional annotation fields retain their declared types', () => {
  const data = minimal(); data.initial_state.actors.desk.name = {};
  assert.throws(() => validateCase(data), /actor|участник/i);
  const note = minimal(); note.initial_state.annotations = [{text: 'test', title: 4}];
  assert.throws(() => validateCase(note), /annotation|пояснен/i);
});
test('event message direction must match the current actor', () => {
  const data = minimal(); data.steps[0].event.type = 'message_received';
  assert.throws(() => validateCase(data), /direction|направлен/i);
});
test('incoming event must address our actor', () => {
  const data=minimal();
  data.steps[0].event.type='message_received';
  data.steps[0].state_after.messages[0].from_actor='service';
  data.steps[0].state_after.messages[0].to_actor='service';
  assert.throws(()=>validateCase(data),/direction|направлен/i);
});
test('outgoing event cannot send to our own actor', () => {
  const data=minimal();data.steps[0].state_after.messages[0].to_actor='desk';
  assert.throws(()=>validateCase(data),/direction|направлен/i);
});
test('UTF-8 size and node budgets are enforced on object imports', () => {
  const data = minimal(); data.extra = 'ж'.repeat(2700000);
  assert.throws(() => validateCase(data), /5 MiB|5 М/i);
  const nodes = minimal(); nodes.extra = Array(100001).fill(null);
  assert.throws(() => validateCase(nodes), /nodes|узл/i);
});
test('JSON objects with dangerous keys are rejected without polluting prototypes', () => {
  const data = minimal(); data.extra = JSON.parse('{"__proto__":{"polluted":true}}');
  assert.throws(() => validateCase(data), /key|ключ/i);
  assert.equal({}.polluted, undefined);
});
test('rejected imports preserve the previously selected data and step', () => {
  const previous = minimal();
  const viewer = Object.create(CaseStateViewer.prototype);
  viewer._data = previous; viewer._index = 1; viewer.render = () => {};
  const bad = minimal(); bad.initial_state.annotations = [{text:'bad', source_event_ids:''}];
  assert.throws(() => viewer.load(bad));
  assert.equal(viewer._data, previous); assert.equal(viewer.stepIndex, 1);
});
test('rendering failures restore the previous view and state and report the failure', () => {
  const previous = minimal();
  const viewer = Object.create(CaseStateViewer.prototype);
  viewer._data = previous; viewer._index = 1;
  viewer.shadowRoot = {innerHTML:'previous view'};
  viewer.render = () => { viewer.shadowRoot.innerHTML = 'partial new view'; throw new Error('render failed'); };
  assert.throws(() => viewer.load(minimal()), /render failed/);
  assert.equal(viewer._data, previous); assert.equal(viewer.stepIndex, 1);
  assert.equal(viewer.shadowRoot.innerHTML, 'previous view');
});

async function sessionModule() {
  assert.ok(fs.existsSync(new URL('../analysis.js', import.meta.url)), 'analysis session is available');
  return import('../analysis.js');
}
const deferred = () => { let resolve, reject; const promise = new Promise((a,b) => {resolve=a;reject=b}); return {promise,resolve,reject}; };
const step = hash => ({input:{input_hash:hash,messages:[]},reference:{qualification:'author_labels_unvalidated'},source:{family_id:'same-family'}});
test('case switching ignores an older document response', async () => {
  const {AnalysisSession} = await sessionModule();
  const first=deferred(), second=deferred(), documents=[];
  const session = new AnalysisSession({request: path => path === '/api/cases/a' ? first.promise : path === '/api/cases/b' ? second.promise : Promise.resolve(step('b-hash')), onDocument: doc => documents.push(doc)});
  const a=session.selectCase('a'); const b=session.selectCase('b');
  second.resolve({case_id:'b',document:{title:'b'}}); await b;
  first.resolve({case_id:'a',document:{title:'a'}}); await a;
  assert.deepEqual(documents,[{title:'b'}]); assert.equal(session.state.caseId,'b');
  assert.equal(session.state.step.input.input_hash,'b-hash');
});
test('step changes reject stale step and run responses and send the bound offline request', async () => {
  const {AnalysisSession} = await sessionModule();
  const oldStep=deferred(), oldRun=deferred(), posts=[];
  const session=new AnalysisSession({request:(path,options) => {
    if(path==='/api/cases/a')return Promise.resolve({case_id:'a',document:{title:'a'}});
    if(path.endsWith('/steps/1'))return oldStep.promise;
    if(path==='/api/runs'){posts.push(options);return oldRun.promise}
    return Promise.resolve(step(path.endsWith('/steps/2')?'hash-2':'hash-0'));
  }});
  await session.selectCase('a');
  const run=session.analyze(); const pending=session.selectStep(1); await session.selectStep(2);
  oldStep.resolve(step('hash-1')); await pending;
  oldRun.resolve({run_id:'stale',input:{input_hash:'hash-0'}}); await run;
  assert.equal(session.state.stepIndex,2); assert.equal(session.state.step.input.input_hash,'hash-2'); assert.equal(session.state.run,null);
  assert.deepEqual(JSON.parse(posts[0].body),{case_id:'a',step_index:0,expected_input_hash:'hash-0',mode:'offline'});
  assert.equal(posts[0].headers['X-ProofKey-Request'],'analysis-v1');
});
test('failed current requests surface an error and leave analysis unavailable', async () => {
  const {AnalysisSession} = await sessionModule();
  const session=new AnalysisSession({request:()=>Promise.reject(new Error('Cannot load source'))});
  await session.selectCase('a'); assert.match(session.state.error,/Cannot load source/); assert.equal(session.state.step,null); assert.equal(session.state.pending,null);
});
