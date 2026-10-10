import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

const source=await readFile(new URL('../customer-model.js',import.meta.url),'utf8').catch(()=> 'export const validateWindow=()=>({}); export const buildRequest=()=>({}); export const offeredWindows=()=>[]; export const customerStatus=()=>({}); export class CustomerSession {}');
const {validateWindow,buildRequest,offeredWindows,customerStatus,CustomerSession}=await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
const now=Date.parse('2030-01-01T00:00:00Z');
const snapshot=(revision=1)=>({case_id:'case-1',revision,snapshot_hash:(revision===1?'a':'b').repeat(64),events:[{event_id:'source-1',kind:'message',text:'Please move my delivery.'}]});
const draft={slot_start:'2030-01-02T10:00:00Z',slot_end:'2030-01-02T12:00:00Z',evidence_event_ids:['source-1']};
const decision=(changes={})=>({case_id:'case-1',decision_id:'decision-1',revision:1,snapshot_hash:'a'.repeat(64),action:{type:'reschedule_delivery',slot_start:draft.slot_start,slot_end:draft.slot_end,address_change:false},evidence_event_ids:['source-1'],checks:[],...changes});
const detail=(changes={})=>({case_id:'case-1',snapshot:snapshot(),decisions:[],reviews:[],actions:[],...changes});

test('window validation rejects naive, past, reversed and longer than eight-hour slots',()=>{
  assert.equal(validateWindow(draft,now).valid,true);
  for(const bad of [{slot_start:'2030-01-02T10:00:00'}, {slot_start:'2029-01-01T10:00:00Z'}, {slot_end:draft.slot_start}, {slot_end:'2030-01-02T18:01:00Z'}, {slot_end:'invalid'}]) assert.equal(validateWindow({...draft,...bad},now).valid,false);
});
test('request requires current case, revision, hash and real supporting evidence',()=>{
  const body=buildRequest(snapshot(),snapshot(),draft,now);
  assert.deepEqual(body,{expected_revision:1,snapshot_hash:'a'.repeat(64),action:{type:'reschedule_delivery',slot_start:'2030-01-02T10:00:00.000Z',slot_end:'2030-01-02T12:00:00.000Z',address_change:false},evidence_event_ids:['source-1']});
  for(const changed of [snapshot(2),{...snapshot(),case_id:'case-2'},{...snapshot(),snapshot_hash:'c'.repeat(64)}]) assert.throws(()=>buildRequest(snapshot(),changed,draft,now),/changed|stale/i);
  for(const ids of [[],['missing'],['source-1','source-1']]) assert.throws(()=>buildRequest(snapshot(),snapshot(),{...draft,evidence_event_ids:ids},now),/evidence/i);
});
test('window options only expose the latest current real reschedule proposal',()=>{
  assert.deepEqual(offeredWindows(detail(),now),[]);
  assert.equal(offeredWindows(detail({decisions:[decision()]}),now)[0].decision_id,'decision-1');
  assert.deepEqual(offeredWindows(detail({decisions:[decision(),decision({revision:0})]}),now),[]);
  assert.deepEqual(offeredWindows(detail({decisions:[decision({action:{type:'operator_review'}})]}),now),[]);
});
test('offered windows require their own valid evidence references',()=>{
  for(const ids of [[],['missing'],['source-1','source-1']])assert.deepEqual(offeredWindows(detail({decisions:[decision({evidence_event_ids:ids})]}),now),[]);
});
test('optional reviewed offer binding blocks a same-snapshot superseding proposal at preflight',async()=>{
  let posts=0;
  const newer=decision({decision_id:'decision-2',action:{...decision().action,slot_start:'2030-01-03T10:00:00Z',slot_end:'2030-01-03T12:00:00Z'}});
  const s=new CustomerSession(async(_path,options)=>{if(options?.method==='POST')posts++;return {case:detail({decisions:[decision(),newer]})};},{now:()=>now});
  s.accept(detail({decisions:[decision()]}));s.setDraft(draft);s.review({offerId:'decision-1'});
  await assert.rejects(s.submit(),/offer.*changed|offer.*current/i);
  assert.equal(posts,0);assert.deepEqual(s.draft,draft);assert.equal(s.binding.revision,1);
});
test('offer-bound uncertain retry recovers only the unchanged dispatched request with its original key',async()=>{
  const keys=[],saved=decision({decision_id:'saved-preference'}),newer=decision({decision_id:'newer-offer'});let posts=0;
  const s=new CustomerSession(async(_path,options)=>{
    if(options?.method!=='POST')return {case:detail({decisions:posts?[decision(),saved,newer]:[decision()]})};
    keys.push(options.idempotencyKey);posts++;
    if(posts===1)throw Error('Reply lost');
    return {case:detail({decisions:[decision(),saved]})};
  },{now:()=>now});
  s.accept(detail({decisions:[decision()]}));s.setDraft(draft);s.review({offerId:'decision-1'});
  await assert.rejects(s.submit(),/Reply lost/);
  assert.equal(s.canReplaySubmission,true);
  await s.load('case-1');assert.equal(s.reviewedOfferCurrent,false);
  await s.submit();assert.equal(posts,2);assert.equal(keys[0],keys[1]);assert.equal(s.savedOutcome.decision_id,'saved-preference');assert.equal(s.status.decision.decision_id,'newer-offer');
});
test('a rejected offer-bound POST cannot bypass current-offer checks on retry',async()=>{
  let posts=0;
  const s=new CustomerSession(async(_path,options)=>{
    if(options?.method==='POST'){posts++;const error=Error('Request rejected');error.status=400;throw error;}
    return {case:detail({decisions:[decision()]})};
  },{now:()=>now});
  s.accept(detail({decisions:[decision()]}));s.setDraft(draft);s.review({offerId:'decision-1'});
  await assert.rejects(s.submit(),/Request rejected/);assert.equal(s.canReplaySubmission,false);
  s.detail=detail({decisions:[decision(),decision({decision_id:'replacement'})]});
  await assert.rejects(s.submit(),/offer.*changed/i);assert.equal(posts,1);assert.deepEqual(s.draft,draft);
});
test('status refuses stale, foreign, superseded and mismatched execution receipts',()=>{
  const d=decision();
  const receipt={case_id:'case-1',decision_id:d.decision_id,revision:1,snapshot_hash:d.snapshot_hash,status:'verified',execution_mode:'postgres_sandbox',sandbox_effects:1,external_effects:0,action_id:'receipt-1'};
  const current=detail({decisions:[d],actions:[receipt]});
  assert.equal(customerStatus(current).kind,'sandbox');
  assert.equal(customerStatus(current).receipt.action_id,'receipt-1');
  assert.match(customerStatus(current).description,/not.*delivery|no.*carrier/i);
  for(const bad of [{revision:0},{case_id:'foreign'},{snapshot_hash:'c'.repeat(64)},{decision_id:'old'},{status:'failed'}]) assert.equal(customerStatus({...current,actions:[{...receipt,...bad}]}).kind,'proposed');
  assert.equal(customerStatus({...current,snapshot:snapshot(2)}).kind,'none');
  assert.equal(customerStatus({...current,decisions:[d,decision({decision_id:'new'})]}).kind,'proposed');
});
test('review is shown only when matching current proposal and never means delivered',()=>{
  const d=decision(); const review={case_id:'case-1',decision_id:d.decision_id,revision:1,snapshot_hash:d.snapshot_hash,verdict:'approve'};
  assert.equal(customerStatus(detail({decisions:[d],reviews:[review]})).kind,'approved');
  assert.equal(customerStatus(detail({decisions:[d],reviews:[{...review,revision:0}]})).kind,'proposed');
});
test('stale preflight preserves draft and blocks the POST',async()=>{
  let posts=0; const s=new CustomerSession(async(_path,options)=>{if(options?.method==='POST')posts++;return {case:detail({snapshot:snapshot(2)})};},{now:()=>now});
  s.accept(detail());s.setDraft(draft);
  await assert.rejects(s.submit(),/changed|stale/i);
  assert.equal(posts,0);assert.deepEqual(s.draft,draft);
});
test('uncertain submission retry preserves idempotency and blocks duplicate submits',async()=>{
  const requests=[]; let rejectFirst; let count=0;
  const api=async(path,options)=>{
    if(options?.method!=='POST')return {case:detail({decisions:count===2?[decision()]:[]})};
    requests.push({path,...options});count++;
    if(count===1)return new Promise((_resolve,reject)=>{rejectFirst=reject;});
    return {case:detail({decisions:[decision()]})};
  };
  const s=new CustomerSession(api,{now:()=>now});s.accept(detail());s.setDraft(draft);
  const first=s.submit();await new Promise(resolve=>setImmediate(resolve));
  await assert.rejects(s.submit(),/progress/i);
  rejectFirst(Error('Connection lost'));await assert.rejects(first,/Connection lost/);
  assert.deepEqual(s.draft,draft);
  await s.submit();
  assert.equal(requests.length,2);assert.equal(requests[0].idempotencyKey,requests[1].idempotencyKey);
  assert.equal(requests[1].path,'/cases/case-1/decisions');
  assert.equal(s.step,'status');assert.equal(s.status.kind,'proposed');
  await assert.rejects(s.submit(),/already/i);assert.equal(requests.length,2);
});

test('write-time conflict loads the newer snapshot without losing the reviewed draft',async()=>{
  let reads=0;
  const s=new CustomerSession(async(_path,options)=>{
    if(options?.method==='POST'){const error=Error('revision_conflict');error.status=409;throw error;}
    reads++;return {case:detail({snapshot:reads===1?snapshot():snapshot(2)})};
  },{now:()=>now});s.accept(detail());s.setDraft(draft);s.review();
  await assert.rejects(s.submit(),/conflict/);
  assert.equal(s.detail.snapshot.revision,2);assert.equal(s.binding.revision,1);assert.equal(s.step,'review');assert.deepEqual(s.draft,draft);
});
test('a response with different evidence cannot report the requested proposal saved',async()=>{
  const s=new CustomerSession(async(_path,options)=>options?.method==='POST'?{case:detail({decisions:[decision({evidence_event_ids:[]})]})}:{case:detail()},{now:()=>now});
  s.accept(detail());s.setDraft(draft);s.review();
  await assert.rejects(s.submit(),/could not be verified/);
  assert.equal(s.step,'review');assert.deepEqual(s.draft,draft);
});

test('uncertain retry keeps the saved receipt separate from a newer same-revision proposal',async()=>{
  const saved=decision(),newer=decision({decision_id:'newer-proposal'}),keys=[];let posts=0;
  const current=detail({decisions:[saved,newer]});
  const s=new CustomerSession(async(_path,options)=>{
    if(options?.method!=='POST')return {case:posts?current:detail()};
    keys.push(options.idempotencyKey);posts++;if(posts===1)throw Error('Reply lost');
    return {case:detail({decisions:[saved]})};
  },{now:()=>now});s.accept(detail());s.setDraft(draft);
  await assert.rejects(s.submit(),/Reply lost/);await s.submit();
  assert.equal(keys[0],keys[1]);assert.equal(s.status.decision.decision_id,'newer-proposal');
  assert.equal(s.savedOutcome.decision_id,'decision-1');assert.equal(s.detail.decisions.length,2);
});

test('uncertain retry reads same-revision approval and execution added after the cached response',async()=>{
  const saved=decision(),review={case_id:'case-1',decision_id:saved.decision_id,revision:1,snapshot_hash:saved.snapshot_hash,verdict:'approve'};
  const receipt={...review,action_id:'action-later',status:'verified',execution_mode:'postgres_sandbox',external_effects:0,sandbox_effects:1};
  let posts=0;
  const s=new CustomerSession(async(_path,options)=>{
    if(options?.method!=='POST')return {case:posts?detail({decisions:[saved],reviews:[review],actions:[receipt]}):detail()};
    posts++;if(posts===1)throw Error('Reply lost');return {case:detail({decisions:[saved]})};
  },{now:()=>now});s.accept(detail());s.setDraft(draft);
  await assert.rejects(s.submit(),/Reply lost/);await s.submit();
  assert.equal(s.status.kind,'sandbox');assert.equal(s.status.receipt.action_id,'action-later');
  assert.equal(s.detail.reviews.length,1);
});

test('failed post-save refresh preserves saved outcome without presenting the cached case as current',async()=>{
  const saved=decision();let savedOnServer=false,reads=0;
  const s=new CustomerSession(async(_path,options)=>{
    if(options?.method==='POST'){savedOnServer=true;return {case:detail({decisions:[saved]})};}
    reads++;if(savedOnServer && reads===2)throw Error('Status connection lost');
    return {case:savedOnServer?detail({decisions:[saved]}):detail()};
  },{now:()=>now});s.accept(detail());s.setDraft(draft);s.review();await s.submit();
  assert.equal(s.savedOutcome.decision_id,'decision-1');assert.equal(s.status.kind,'unknown');
  assert.equal(s.status.decision,null);assert.equal(s.step,'status');assert.match(s.error,/refresh/i);
  assert.deepEqual(s.draft,draft);await assert.rejects(s.submit(),/already/);
  await s.load('case-1');assert.equal(s.status.kind,'proposed');
});

test('customer case and order metadata fit 390px with valid maximum-length IDs',{skip:!process.env.PROOFKEY_CUSTOMER_BROWSER},async()=>{
  const {chromium}=await import(process.env.PROOFKEY_PLAYWRIGHT_MODULE || '/Users/nbk/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs');
  const browser=await chromium.launch({headless:true,channel:process.env.PROOFKEY_BROWSER_CHANNEL || 'chrome'});
  try {
    const page=await browser.newPage({viewport:{width:390,height:844}});
    const id='c'.repeat(64),order='o'.repeat(64),fixture=detail({case_id:id,snapshot:{...snapshot(),case_id:id,links:{order_id:order}}});
    await page.route('**/api/platform/cases/**',route=>route.fulfill({contentType:'application/json',body:JSON.stringify({case:fixture})}));
    await page.goto(`${process.env.PROOFKEY_CUSTOMER_URL || 'http://127.0.0.1:8105'}/customer.html?case=${id}`);
    await page.locator('.case-strip').waitFor();
    assert.equal(await page.locator('.case-strip').innerText().then(text=>text.includes(order)),true);
    const bounds=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,metadata:[...document.querySelectorAll('.case-strip strong,.case-strip span')].map(element=>({left:element.getBoundingClientRect().left,right:element.getBoundingClientRect().right,scroll:element.scrollWidth,width:element.clientWidth}))}));
    assert.ok(bounds.scroll<=bounds.width,`Document overflows: ${JSON.stringify(bounds)}`);
    for(const item of bounds.metadata)assert.ok(item.left>=0 && item.right<=bounds.width,`Metadata overflows: ${JSON.stringify(bounds)}`);
  } finally {await browser.close();}
});
