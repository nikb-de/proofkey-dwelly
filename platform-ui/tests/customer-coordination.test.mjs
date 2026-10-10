import test from 'node:test';
import assert from 'node:assert/strict';

const module = await import('../customer-coordination.js').catch(()=>({}));
const {CustomerCoordinationSession, coordinationCustomerView} = module;
const hash='a'.repeat(64), termsHash='b'.repeat(64);
const terms={slot_start:'2030-06-03T10:00:00+00:00',slot_end:'2030-06-03T12:00:00+00:00',handover:'recipient_only',recipient_present:true,charge:{amount_minor:3000,currency:'GBP'}};
export const fixture=(overrides={})=>({case_id:'case-1',snapshot:{case_id:'case-1',revision:4,snapshot_hash:hash,links:{order_id:'order-1'},events:[]},states:{coordination_freshness:'current'},coordination:{case_id:'case-1',version:3,revision:4,snapshot_hash:hash,phase:'awaiting_consent',offer:{offer_id:'offer-1',terms_hash:termsHash,terms,created_revision:4},consent:null,pending_request:null,operation_receipts:[],mode:'local_sandbox',external_effects:0,physical_delivery:'not_confirmed'},...overrides});
const accepted=()=>({...fixture().coordination,version:4,revision:6,snapshot_hash:'c'.repeat(64),phase:'ready_to_book',consent:{offer_id:'offer-1',terms_hash:termsHash,created_revision:6,evidence_event_ids:['local-evidence'],mode:'local_preview_simulation',authenticated:false},audit_history:[{audit_id:'acceptance-audit',command:'record_local_acceptance',version:4,revision:6}]});
const acceptedDetail=()=>fixture({snapshot:{...fixture().snapshot,revision:6,snapshot_hash:'c'.repeat(64)},coordination:accepted()});

test('projection keeps complete terms, required attendance, consent freshness and local receipts separate',()=>{
  assert.equal(typeof coordinationCustomerView,'function');
  const view=coordinationCustomerView(fixture(),Date.parse('2029-01-01'));
  assert.equal(view.canAccept,true);assert.equal(view.terms,terms);assert.equal(view.freshness,'current');
  const state=accepted();state.pending_request={request_id:'booking-1',kind:'booking',status:'pending_local_readback'};
  state.operation_receipts=[{request_id:'old-cancellation',kind:'cancellation',status:'confirmed_locally'}];
  const current=fixture({snapshot:{...fixture().snapshot,revision:7},coordination:state});
  const stale=coordinationCustomerView(current,Date.parse('2029-01-01'));
  assert.equal(stale.freshness,'stale');assert.equal(stale.consentCurrent,false);assert.equal(stale.canAccept,false);
  assert.equal(stale.pending.request_id,'booking-1');assert.equal(stale.bookingReceipt,null);
});

test('load and acknowledgment never write; acceptance binds exact snapshot and complete offer identity',async()=>{
  assert.equal(typeof CustomerCoordinationSession,'function');
  let posted=false;const requests=[];const s=new CustomerCoordinationSession(async(path,options)=>{requests.push({path,options});if(options?.method==='POST'){posted=true;return {coordination:accepted()};}return {case:posted?acceptedDetail():fixture()};},{now:()=>Date.parse('2029-01-01'),newKey:()=> 'fixed-key'});
  await s.load('case-1');assert.equal(requests.length,1);
  await assert.rejects(s.submit(),/acknowledge/i);assert.equal(requests.length,1);
  s.setAcknowledged(true);assert.equal(requests.length,1);
  await s.submit();
  const posts=requests.filter(r=>r.options?.method==='POST');assert.equal(posts.length,1);
  assert.deepEqual(posts[0],{path:'/cases/case-1/coordination',options:{method:'POST',idempotencyKey:'fixed-key',body:{command:'record_local_acceptance',expected_revision:4,snapshot_hash:hash,expected_workflow_version:3,offer_id:'offer-1',terms_hash:termsHash,acknowledged:true}}});
  assert.equal(s.savedOutcome.phase,'ready_to_book');assert.equal(s.statusConfirmed,true);
  await assert.rejects(s.submit(),/already|review|acknowledge/i);
});

test('inflight duplicates fail; uncertain retry retains exact immutable body/key despite later read',async()=>{
  const posts=[];let rejectFirst;
  const s=new CustomerCoordinationSession(async(_path,options)=>{if(!options)return {case:fixture()};posts.push(options);if(posts.length===1)return new Promise((_,reject)=>{rejectFirst=reject;});return {coordination:accepted()};},{now:()=>Date.parse('2029-01-01'),newKey:()=> 'same-key'});
  await s.load('case-1');s.setAcknowledged(true);const first=s.submit();
  await new Promise(resolve=>setImmediate(resolve));await assert.rejects(s.submit(),/progress/i);
  rejectFirst(Error('Reply lost'));await assert.rejects(first,/Reply lost/);
  const newer=fixture({snapshot:{...fixture().snapshot,revision:99}});s.accept(newer);
  await s.submit();assert.equal(posts.length,2);assert.deepEqual(posts[0],posts[1]);assert.equal(posts[1].body.expected_revision,4);
});

test('changed snapshot fails before write and conflict keeps review while fetching current case',async()=>{
  let posts=0;const current=fixture({snapshot:{...fixture().snapshot,revision:5}});
  const s=new CustomerCoordinationSession(async(_path,options)=>{if(options){posts++;const error=Error('revision_conflict');error.status=409;throw error;}return {case:posts?current:fixture()};},{now:()=>Date.parse('2029-01-01')});
  await s.load('case-1');s.setAcknowledged(true);s.accept(current);await assert.rejects(s.submit(),/changed|current/i);assert.equal(posts,0);
  s.detail=fixture();s.reviewCurrent();s.setAcknowledged(true);await assert.rejects(s.submit(),/revision_conflict/);
  assert.equal(s.detail.snapshot.revision,5);assert.equal(s.binding.expected_revision,4);assert.equal(s.pending,null);assert.equal(s.acknowledged,false);
});

test('unverified response remains retryable; failed refresh never claims cached receipt is current',async()=>{
  let posts=0;const s=new CustomerCoordinationSession(async(_path,options)=>{if(options){posts++;return {coordination:posts===1?{...accepted(),consent:{...accepted().consent,terms_hash:'d'.repeat(64)}}:accepted()};}if(posts)throw Error('Offline');return {case:fixture()};},{now:()=>Date.parse('2029-01-01')});
  await s.load('case-1');s.setAcknowledged(true);await assert.rejects(s.submit(),/verified/i);assert.ok(s.pending);
  await s.submit();assert.equal(s.statusConfirmed,false);assert.match(s.error,/refresh/i);assert.equal(s.savedOutcome.consent.terms_hash,termsHash);assert.equal(s.pending,null);
});

test('past slots, terminal phases and missing complete terms cannot offer local acceptance',()=>{
  for(const phase of ['ready_to_book','booking_pending','booking_confirmed','escalated'])assert.equal(coordinationCustomerView(fixture({coordination:{...fixture().coordination,phase}}),Date.parse('2029-01-01')).canAccept,false);
  assert.equal(coordinationCustomerView(fixture(),Date.parse('2031-01-01')).canAccept,false);
  assert.equal(coordinationCustomerView(fixture({coordination:{...fixture().coordination,offer:{...fixture().coordination.offer,terms:{...terms,charge:{amount_minor:null,currency:null}}}}}),Date.parse('2029-01-01')).canAccept,false);
});

test('an older refresh cannot replace a later case read or mutation result',async()=>{
  let resolveOld;let reads=0;
  const s=new CustomerCoordinationSession(async()=>{reads++;if(reads===1)return new Promise(resolve=>{resolveOld=resolve;});return {case:fixture({snapshot:{...fixture().snapshot,revision:5}})};});
  const old=s.load('case-1');await s.load('case-1');resolveOld({case:fixture()});await old;
  assert.equal(s.detail.snapshot.revision,5);
});

test('acceptance receipt must contain exactly two new audits and explicit simulated consent',async()=>{
  for(const result of [{...accepted(),revision:7,consent:{...accepted().consent,created_revision:7}},{...accepted(),consent:{...accepted().consent,mode:undefined}},{...accepted(),consent:{...accepted().consent,authenticated:true}}]){
    const s=new CustomerCoordinationSession(async(_path,options)=>options?{coordination:result}:{case:fixture()},{now:()=>Date.parse('2029-01-01')});
    await s.load('case-1');s.setAcknowledged(true);await assert.rejects(s.submit(),/verified/i);assert.ok(s.pending);assert.equal(s.savedOutcome,null);
  }
});

test('post-acceptance regressed GET cannot mark the old head current and later correlated reads recover',async()=>{
  let response=fixture();const s=new CustomerCoordinationSession(async(_path,options)=>options?{coordination:accepted()}:{case:response},{now:()=>Date.parse('2029-01-01')});
  await s.load('case-1');s.setAcknowledged(true);await s.submit();
  assert.equal(s.statusConfirmed,false);assert.equal(s.savedOutcome.revision,6);assert.match(s.error,/refresh failed/);assert.equal(s.pending,null);
  await assert.rejects(s.load('case-1'),/receipt|predates/i);assert.equal(s.statusConfirmed,false);
  response=acceptedDetail();await s.load('case-1');assert.equal(s.statusConfirmed,true);assert.equal(s.detail.snapshot.revision,6);
  response={...acceptedDetail(),snapshot:{...acceptedDetail().snapshot,snapshot_hash:'d'.repeat(64)}};
  await assert.rejects(s.load('case-1'),/receipt|match/i);assert.equal(s.statusConfirmed,false);
  response=acceptedDetail();response.snapshot.revision=8;response.snapshot.snapshot_hash='e'.repeat(64);response.coordination={...accepted(),version:5,revision:8,snapshot_hash:'e'.repeat(64),phase:'booking_pending',audit_history:[]};
  await assert.rejects(s.load('case-1'),/receipt|history/i);assert.equal(s.statusConfirmed,false);
  response.coordination.audit_history=[...accepted().audit_history,{audit_id:'booking-audit',command:'request_booking',version:5,revision:8}];
  await s.load('case-1');assert.equal(s.statusConfirmed,true);assert.equal(s.detail.coordination.phase,'booking_pending');
});
