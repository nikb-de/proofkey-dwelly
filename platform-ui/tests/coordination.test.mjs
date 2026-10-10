import test from 'node:test';
import assert from 'node:assert/strict';
const c=await import('../coordination.js').catch(()=>({}));
const {PlatformSession}=await import('../session.js');
const product=await import('../product.js');
const terms={slot_start:'2030-06-03T10:00:00+00:00',slot_end:'2030-06-03T12:00:00+00:00',handover:'recipient_only',recipient_present:true,charge:{amount_minor:500,currency:'GBP'}};
const detail=(phase='awaiting_consent')=>({case_id:'case-1',snapshot:{case_id:'case-1',revision:6,snapshot_hash:'a'.repeat(64),links:{customer_id:'customer',operator_id:'operator'},participants:['customer','operator','dispatch'],events:[{event_id:'e1',kind:'message',channel:'chat',sender_id:'customer',recipient_ids:['operator'],text:'accept'}]},coordination:{phase,version:3,revision:6,snapshot_hash:'a'.repeat(64),dispatch_actor_id:'dispatch',offer:{offer_id:'offer-1',terms_hash:'b'.repeat(64),terms,created_revision:0},consent:null,audit_history:[],operation_receipts:[]},model_jobs:[]});
const reviewedDraft=(d,values)=>({...values,reviewed:true,review_binding:c.reviewBinding(d,values)});
test('only phase-appropriate commands are offered and Team never locally accepts',()=>{
  assert.equal(typeof c.allowedCommands,'function');
  for(const [phase,want] of Object.entries({booked:['request_cancellation','escalate'],cancellation_pending:['confirm_cancellation','escalate'],awaiting_terms:['record_offer','escalate'],awaiting_consent:['record_offer','record_consent','escalate'],ready_to_book:['record_offer','record_consent','request_booking','escalate'],booking_pending:['confirm_booking','escalate'],booking_confirmed:[],escalated:[]}))assert.deepEqual(c.allowedCommands(detail(phase)),want);
  assert.deepEqual(c.allowedCommands({...detail(),coordination:null}),['initialize']);
});
test('reviewed command binds current snapshot, offer and source evidence exactly',()=>{
  assert.equal(typeof c.buildCoordinationCommand,'function');
  assert.deepEqual(c.buildCoordinationCommand(detail(),reviewedDraft(detail(),{command:'record_consent',evidence_event_ids:['e1']})),{command:'record_consent',expected_revision:6,snapshot_hash:'a'.repeat(64),expected_workflow_version:3,offer_id:'offer-1',terms_hash:'b'.repeat(64),evidence_event_ids:['e1']});
  assert.throws(()=>c.buildCoordinationCommand(detail(),{command:'record_consent',reviewed:false}),/review/i);
  assert.throws(()=>c.buildCoordinationCommand(detail(),reviewedDraft(detail(),{command:'request_booking'})),/phase/i);
});
test('initialize requires declared distinct dispatch and keeps unknown original facts',()=>{
  const d={...detail(),coordination:null};
  const draft=reviewedDraft(d,{command:'initialize',dispatch_actor_id:'dispatch',booking_id:'old-1',terms:{...terms,handover:'unspecified',recipient_present:null,charge:{amount_minor:null,currency:null}}});
  assert.equal(typeof c.buildCoordinationCommand,'function');
  assert.equal(c.buildCoordinationCommand(d,draft).original_booking.terms.charge.amount_minor,null);
  for(const id of ['operator','customer','invented'])assert.throws(()=>c.buildCoordinationCommand(d,reviewedDraft(d,{...draft,dispatch_actor_id:id})),/declared|distinct/i);
});
test('optional model context requires current succeeded run and paired human note',()=>{
  assert.equal(typeof c.buildCoordinationCommand,'function');
  const d=detail(),hash='c'.repeat(64);
  d.model_jobs=[{run_id:'run-1',case_id:'case-1',status:'succeeded',source:{kind:'platform_case',case_id:'case-1',revision:6,snapshot_hash:d.snapshot.snapshot_hash},input:{case_id:'case-1',step_index:6,input_hash:hash},input_hash:hash,candidate:{schema_version:'proofkey-step-candidate-v1',input_hash:hash,state:'ready',evidence_event_ids:['e1'],next_action:{type:'operator_review'}}}];
  const draft=reviewedDraft(d,{command:'record_consent',evidence_event_ids:['e1'],model_run_id:'run-1',model_review_note:'Checked original source'});
  assert.equal(c.buildCoordinationCommand(d,draft).model_review_note,'Checked original source');
  assert.throws(()=>c.buildCoordinationCommand(d,reviewedDraft(d,{...draft,model_review_note:''})),/note/i);
  d.model_jobs[0].source.revision=5;assert.throws(()=>c.buildCoordinationCommand(d,draft),/current/i);
});
test('stale coordination and stale consent are separate visible states',()=>{
  assert.equal(typeof c.coordinationView,'function');
  const d=detail('ready_to_book');d.coordination.consent={created_revision:5,offer_id:'offer-1',terms_hash:'b'.repeat(64)};
  assert.equal(c.coordinationView(d).freshness,'current');assert.equal(c.coordinationView(d).consentFresh,false);
  d.snapshot.revision=7;assert.equal(c.coordinationView(d).freshness,'stale');
});
test('controller blocks duplicates and freezes uncertain body/key across reload and editing',async()=>{
  assert.equal(typeof c.CoordinationController,'function');
  let release,fail=true;const requests=[];let d=detail();
  const session=new PlatformSession(async(path,opts)=>{if(opts?.method==='POST'){requests.push(structuredClone(opts));if(fail){await new Promise(r=>release=r);throw Error('offline');}return {coordination:d.coordination};}return {case:d};});
  await session.select('case-1');const controller=new c.CoordinationController(session);
  const draft=reviewedDraft(d,{command:'record_consent',evidence_event_ids:['e1']});
  const first=controller.submit(draft);await assert.rejects(controller.submit(draft),/progress/i);release();await assert.rejects(first,/offline/);
  d={...detail(),snapshot:{...detail().snapshot,revision:8}};await session.reload();
  await assert.rejects(controller.submit({...draft,command:'escalate',reason:'changed'}),/retry/i);
  fail=false;await controller.retry();assert.deepEqual(requests[0].body,requests[1].body);assert.equal(requests[0].idempotencyKey,requests[1].idempotencyKey);assert.equal(requests[1].body.expected_revision,6);
});
test('checked review cannot be silently rebound to a newer snapshot or workflow',()=>{
  assert.equal(typeof c.reviewBinding,'function');
  const d=detail(),draft=reviewedDraft(d,{command:'record_consent',evidence_event_ids:['e1']});
  assert.equal(c.buildCoordinationCommand(d,draft).expected_revision,6);
  d.snapshot.revision=7;assert.throws(()=>c.buildCoordinationCommand(d,draft),/review.*changed|changed.*review/i);
});
test('case creation declares optional dispatch without inventing or duplicating participants',()=>{
  assert.equal(typeof product.createCaseRequest,'function');
  const input={caseId:'c',orderId:'order',customerId:'customer',operatorId:'operator'};
  assert.deepEqual(product.createCaseRequest(input).participants,['customer','operator']);
  assert.deepEqual(product.createCaseRequest({...input,dispatchId:'dispatch'}).participants,['customer','operator','dispatch']);
  assert.throws(()=>product.createCaseRequest({...input,dispatchId:'customer'}),/different|distinct/i);
});
test('product summary follows current coordination instead of an unrelated old proposal',()=>{
  const d=detail('booking_pending');d.decisions=[];
  assert.match(product.caseSummary(d).title,/booking/i);
  assert.match(product.caseSummary(d).nextStep,/readback/i);
});
test('successful POST followed by failed readback still retries original key, never duplicates',async()=>{
  const d=detail(),posts=[];let failRead=false;
  const session=new PlatformSession(async(path,options)=>{
    if(options?.method==='POST'){posts.push(options.idempotencyKey);failRead=true;return {coordination:d.coordination};}
    if(failRead)throw Error('readback offline');return {case:d};
  });
  await session.select('case-1');const controller=new c.CoordinationController(session);
  await assert.rejects(controller.submit(reviewedDraft(d,{command:'record_consent',evidence_event_ids:['e1']})),/readback offline/);
  await assert.rejects(controller.retry(),/readback offline/);
  assert.equal(posts.length,2);assert.equal(posts[0],posts[1]);
});
test('review attestation binds selected fields, evidence and model context before submission',()=>{
  const d=detail('awaiting_terms');d.snapshot.events[0].sender_id='dispatch';const draft=reviewedDraft(d,{command:'record_offer',terms,evidence_event_ids:['e1']});
  assert.throws(()=>c.buildCoordinationCommand(d,{...draft,terms:{...terms,charge:{amount_minor:1000,currency:'GBP'}}}),/changed.*review|review.*changed/i);
  assert.throws(()=>c.buildCoordinationCommand(d,{...draft,evidence_event_ids:[]}),/changed.*review|review.*changed/i);
});
