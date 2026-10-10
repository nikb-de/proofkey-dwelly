import test from 'node:test';
import assert from 'node:assert/strict';
import {AnalysisSession} from '../analysis.js';

// Network and clock are external boundaries. The real session owns all transitions.
const profiles={enabled:true,profiles:[
  {id:'alpha',label:'Test OpenAI',provider:'openai',model:'model-alpha',available:true,reason:null},
  {id:'beta',label:'Test Claude',provider:'anthropic',model:'model-beta',available:true,reason:null},
  {id:'unavailable',label:'Missing credentials',provider:'gemini',model:'model-none',available:false,reason:'missing_api_key'}
]};
const input=(index=0)=>({schema_version:'proofkey-step-input-v1',case_id:'case-a',step_index:index,input_hash:`hash-${index}`,messages:[]});
const step=(index=0)=>({input:input(index),reference:{qualification:'author_labels_unvalidated'},source:{family_id:'family-a'}});
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b});return {promise,resolve,reject};};
function clock(){
  let serial=0;const pending=new Map();
  return {schedule:fn=>{const id=++serial;pending.set(id,fn);return id},cancel:id=>pending.delete(id),
    tick:async()=>{const next=pending.entries().next().value;assert.ok(next,'a poll is scheduled');pending.delete(next[0]);await next[1]()},
    get size(){return pending.size}};
}
function job(status='queued',overrides={}){
  return {schema_version:'proofkey-model-job-v1',run_id:'run-a',status,case_id:'case-a',step_index:0,input_hash:'hash-0',
    mode:'model',model_profile_id:'alpha',input:input(),reference:step().reference,source:step().source,
    candidate:status==='succeeded'?{state:'unknown',input_hash:'hash-0',uncertainty:['simulated'],next_action:{type:'operator_review'}}:null,
    evaluation:status==='succeeded'?{accuracy_score:null}:null,receipt:null,error:null,
    created_at:'2026-10-10T10:00:00Z',started_at:null,finished_at:null,
    transaction:{idempotency_key:'key-1',attempt_id:null,dispatch_attempts:0,automatic_retries:0,operational_effects:0,
      reserved_usd:'0.02',budget_scope:'ui-test',prompt_hash:'prompt-a',profile_hash:'profile-a'},...overrides};
}
async function fixture(handle=()=>{throw new Error('unexpected network request')},options={}){
  const timer=clock(),posts=[],profileData=options.profileData??profiles;let keys=0;
  const session=new AnalysisSession({schedule:timer.schedule,cancel:timer.cancel,makeKey:()=>`key-${++keys}`,...options,
    request:(path,options)=>{
      if(path==='/api/catalog')return Promise.resolve({cases:[{id:'case-a',title:'Case A',steps:2,family_id:'family-a'}]});
      if(path==='/api/capabilities')return Promise.resolve({mode:'offline',live_calls:0});
      if(path==='/api/model-profiles')return Promise.resolve(profileData);
      if(path==='/api/cases/case-a')return Promise.resolve({document:{title:'Case A'}});
      if(path.startsWith('/api/cases/case-a/steps/'))return Promise.resolve(step(Number(path.split('/').at(-1))));
      if(options?.method==='POST')posts.push({path,options,body:JSON.parse(options.body)});
      return Promise.resolve(handle(path,options));
    }});
  await session.start();return {session,timer,posts};
}

test('offline remains the default and unavailable profiles cannot be selected',async()=>{
  const {session,posts}=await fixture((path)=>{assert.equal(path,'/api/runs');return {run_id:'offline',candidate:{state:'unknown'}}});
  assert.equal(session.state.profileId,'offline');
  assert.equal(session.selectProfile('unavailable'),false);assert.equal(session.state.profileId,'offline');
  await session.analyze();
  assert.deepEqual(posts[0].body,{case_id:'case-a',step_index:0,expected_input_hash:'hash-0',mode:'offline'});
  assert.equal(posts[0].options.headers['Idempotency-Key'],undefined);
});

test('model submission sends only its bound selector and follows every nonterminal state',async()=>{
  const statuses=['running','response_received','succeeded'];
  const {session,timer,posts}=await fixture(path=>path==='/api/model-runs'?job():job(statuses.shift()));
  assert.equal(session.selectProfile('alpha'),true);await session.analyze();
  assert.deepEqual(posts[0].body,{case_id:'case-a',step_index:0,expected_input_hash:'hash-0',mode:'model',model_profile_id:'alpha'});
  assert.equal(posts[0].options.headers['Idempotency-Key'],'key-1');
  assert.equal(posts[0].options.headers['X-ProofKey-Request'],'analysis-v1');
  assert.equal(session.state.run.status,'queued');
  await timer.tick();assert.equal(session.state.run.status,'running');
  await timer.tick();assert.equal(session.state.run.status,'response_received');
  await timer.tick();assert.equal(session.state.run.status,'succeeded');assert.equal(timer.size,0);
});

test('changing model profiles invalidates an older accepted POST',async()=>{
  const response=deferred();const {session,timer}=await fixture(()=>response.promise);
  session.selectProfile('alpha');const run=session.analyze();session.selectProfile('beta');
  response.resolve(job());await run;
  assert.equal(session.state.profileId,'beta');assert.equal(session.state.run,null);assert.equal(timer.size,0);
});

test('changing steps invalidates both an in-flight poll and its stale failure',async()=>{
  const response=deferred();const {session,timer}=await fixture(path=>path==='/api/model-runs'?job():response.promise);
  session.selectProfile('alpha');await session.analyze();const poll=timer.tick();await session.selectStep(1);
  response.reject(new Error('old poll failed'));await poll;
  assert.equal(session.state.stepIndex,1);assert.equal(session.state.run,null);assert.equal(session.state.error,'');
  assert.equal(session.state.connectionError,'');assert.equal(timer.size,0);
});

test('changing profile cancels scheduled polling',async()=>{
  const {session,timer}=await fixture(()=>job());session.selectProfile('alpha');await session.analyze();
  assert.equal(timer.size,1);session.selectProfile('beta');assert.equal(timer.size,0);assert.equal(session.state.run,null);
});

test('lost POST acknowledgement is retried only explicitly using the identical key',async()=>{
  let calls=0;const {session,timer,posts}=await fixture(()=>{if(++calls===1)throw new Error('lost acknowledgement');return job()});
  session.selectProfile('alpha');await session.analyze();
  assert.equal(session.state.run,null);assert.match(session.state.connectionError,/lost acknowledgement/);assert.equal(timer.size,0);
  await session.reconnect();
  assert.equal(posts.length,2);assert.equal(posts[0].options.headers['Idempotency-Key'],posts[1].options.headers['Idempotency-Key']);
  assert.deepEqual(posts[0].body,posts[1].body);assert.equal(session.state.run.run_id,'run-a');
});

test('polling failure preserves the acknowledged job and reconnect uses GET',async()=>{
  let polls=0;const {session,timer,posts}=await fixture(path=>path==='/api/model-runs'?job():++polls===1?Promise.reject(new Error('disconnected')):job('succeeded'));
  session.selectProfile('alpha');await session.analyze();await timer.tick();
  assert.equal(session.state.run.status,'queued');assert.match(session.state.connectionError,/disconnected/);assert.equal(timer.size,0);
  await session.reconnect();assert.equal(session.state.run.status,'succeeded');assert.equal(posts.length,1);
});

test('an intentional new run after a terminal result gets a new idempotency key',async()=>{
  const {session,posts}=await fixture((path,options)=>job('succeeded',{transaction:{...job().transaction,idempotency_key:options.headers['Idempotency-Key']}}));
  session.selectProfile('alpha');await session.analyze();await session.analyze();
  assert.deepEqual(posts.map(post=>post.options.headers['Idempotency-Key']),['key-1','key-2']);
});

test('outcome_unknown is terminal and reconnect never resubmits it',async()=>{
  const {session,timer,posts}=await fixture(()=>job('outcome_unknown',{error:{code:'provider_outcome_unknown',phase:'dispatch'}}));
  session.selectProfile('alpha');await session.analyze();await session.reconnect();
  assert.equal(session.state.run.status,'outcome_unknown');assert.equal(session.state.run.candidate,null);assert.equal(timer.size,0);assert.equal(posts.length,1);
});

test('failed jobs retain sanitized errors with no candidate or scheduled poll',async()=>{
  const {session,timer}=await fixture(()=>job('failed',{error:{code:'invalid_model_output',phase:'validation'}}));
  session.selectProfile('alpha');await session.analyze();
  assert.equal(session.state.run.candidate,null);assert.equal(session.state.run.error.code,'invalid_model_output');assert.equal(timer.size,0);
});

for(const [name,change] of [
  ['selected profile',{model_profile_id:'beta'}],['selected input',{input_hash:'hash-other'}],
  ['provider receipt',{receipt:{provider:'anthropic',requested_model:'model-alpha'}}],
  ['requested model receipt',{receipt:{provider:'openai',requested_model:'model-other'}}],
  ['idempotency key',{transaction:{...job().transaction,idempotency_key:'wrong-key'}}]
])test(`mismatched ${name} cannot attach a model result`,async()=>{
  const {session,timer}=await fixture(()=>job('succeeded',change));session.selectProfile('alpha');await session.analyze();
  assert.equal(session.state.run,null);assert.match(session.state.error,/identity|binding/i);assert.equal(timer.size,0);
});

test('an observed model alias is displayed as reported, not mistaken for a binding mismatch',async()=>{
  const receipt={model_profile_id:'alpha',provider:'openai',requested_model:'model-alpha',observed_model:'model-alpha-2026',usage:{input_tokens:null,output_tokens:null},request_id:null,latency_ms:5};
  const {session}=await fixture(()=>job('succeeded',{receipt}));session.selectProfile('alpha');await session.analyze();
  assert.deepEqual(session.state.run.receipt,receipt);assert.equal(session.state.error,'');
});

test('a failed older POST cannot replace a new profile error or state',async()=>{
  const response=deferred();const {session}=await fixture(()=>response.promise);session.selectProfile('alpha');
  const run=session.analyze();session.selectProfile('beta');response.reject(new Error('stale failure'));await run;
  assert.equal(session.state.error,'');assert.equal(session.state.connectionError,'');assert.equal(session.state.profileId,'beta');
});

function memoryStorage(){const values=new Map();return {getItem:key=>values.get(key)??null,setItem:(key,value)=>values.set(key,value),removeItem:key=>values.delete(key),values};}
test('reload recovery stores metadata only and resumes an accepted run with GET',async()=>{
  const storage=memoryStorage();const first=await fixture(()=>job(),{storage});first.session.selectProfile('alpha');await first.session.analyze();
  const saved=JSON.parse([...storage.values.values()][0]);
  assert.deepEqual(Object.keys(saved).sort(),['caseId','key','profileId','runId','stepIndex','version']);
  assert.equal(saved.runId,'run-a');assert.equal(JSON.stringify(saved).includes('messages'),false);
  const second=await fixture(path=>{assert.equal(path,'/api/model-runs/run-a');return job('succeeded')},{storage});
  assert.equal(second.posts.length,0);assert.equal(second.session.state.profileId,'offline');
  await second.session.resumeLast();assert.equal(second.posts.length,0);assert.equal(second.session.state.run.status,'succeeded');
  assert.equal(storage.values.size,0);
});

test('reload after a lost acknowledgement waits for explicit same-key recovery',async()=>{
  const storage=memoryStorage();const first=await fixture(()=>Promise.reject(new Error('lost acknowledgement')),{storage});
  first.session.selectProfile('alpha');await first.session.analyze();
  const second=await fixture(()=>job(),{storage,makeKey:()=>{throw new Error('must retain original key')}});
  assert.equal(second.posts.length,0);await second.session.resumeLast();
  assert.equal(second.posts[0].options.headers['Idempotency-Key'],'key-1');
});

test('unavailable session storage does not interrupt analysis or selection',async()=>{
  const storage={getItem(){throw new Error('denied')},setItem(){throw new Error('denied')},removeItem(){throw new Error('denied')}};
  const {session}=await fixture(()=>job('succeeded'),{storage});session.selectProfile('alpha');await session.analyze();
  assert.equal(session.state.run.status,'succeeded');assert.equal(session.state.error,'');
});

test('changing profile while restoring a saved selection cancels the old resume action',async()=>{
  const storage=memoryStorage();const first=await fixture(()=>job(),{storage});first.session.selectProfile('alpha');await first.session.analyze();
  const second=await fixture(()=>job('succeeded'),{storage}),document=deferred(),original=second.session.request;
  second.session.request=(path,options)=>path==='/api/cases/case-a'?document.promise:original(path,options);
  const resume=second.session.resumeLast();second.session.selectProfile('beta');document.resolve({document:{title:'Case A'}});await resume;
  assert.equal(second.session.state.profileId,'beta');assert.equal(second.session.state.run,null);assert.equal(second.posts.length,0);
});

test('a delayed model-profile service cannot block the offline evidence and baseline',async()=>{
  const modelResponse=deferred();
  const session=new AnalysisSession({request:path=>{
    if(path==='/api/model-profiles')return modelResponse.promise;
    if(path==='/api/catalog')return Promise.resolve({cases:[{id:'case-a'}]});
    if(path==='/api/capabilities')return Promise.resolve({mode:'offline'});
    if(path==='/api/cases/case-a')return Promise.resolve({document:{title:'Case A'}});
    return Promise.resolve(step());
  }});
  const start=session.start();
  await new Promise(resolve=>setImmediate(resolve));
  const readyBeforeModels=!!session.state.step;
  modelResponse.resolve(profiles);await start;
  assert.equal(readyBeforeModels,true);assert.equal(session.state.profileId,'offline');
});

test('an acknowledged run resumes by GET after its profile credentials become unavailable',async()=>{
  const storage=memoryStorage(),first=await fixture(()=>job(),{storage});
  first.session.selectProfile('alpha');await first.session.analyze();
  const unavailable={...profiles,profiles:profiles.profiles.map(item=>item.id==='alpha'?{...item,available:false,reason:'missing_api_key'}:item)};
  const receipt={model_profile_id:'alpha',provider:'openai',requested_model:'model-alpha',observed_model:'model-alpha-2026',
    usage:{input_tokens:17,output_tokens:8},request_id:'request-a',latency_ms:5};
  const second=await fixture(path=>{assert.equal(path,'/api/model-runs/run-a');return job('succeeded',{receipt})},{storage,profileData:unavailable});
  await second.session.resumeLast();
  assert.equal(second.session.state.run?.status,'succeeded');assert.equal(second.session.state.profileId,'alpha');
  await second.session.analyze();assert.equal(second.posts.length,0);
});
