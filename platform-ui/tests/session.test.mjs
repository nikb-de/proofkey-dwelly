import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const source = await readFile(new URL('../session.js', import.meta.url), 'utf8').catch(() => 'export class PlatformSession {}');
const { PlatformSession, createAPI, needsReview, reviewedMediaMessage, canReview } = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
const detail = (id, revision = 0) => ({schema_version:'proofkey-platform-case-v1',case_id:id,snapshot:{case_id:id,revision,snapshot_hash:'a'.repeat(64),events:[]},states:{lifecycle:'new',evidence:'empty',analysis:'not_started',decision:'none',action:'none'},decisions:[],reviews:[],actions:[],assets:[],model_jobs:[],external_effects:0});
const deferred = () => {let resolve; const promise = new Promise(r => {resolve=r;}); return {promise,resolve};};

test('late case response cannot replace the newer selected case', async () => {
  const first=deferred();
  const session=new PlatformSession(async path => path.endsWith('/first') ? first.promise : detail('second'));
  const pending=session.select('first');
  await session.select('second'); first.resolve(detail('first')); await pending;
  assert.equal(session.detail.case_id,'second'); assert.equal(session.selectedId,'second');
});

test('revision conflict reloads current snapshot and keeps operator draft', async () => {
  let revision=0;
  const session=new PlatformSession(async (path, options) => {
    if(options?.method==='POST'){revision=1; const error=new Error('revision_conflict');error.status=409;throw error;}
    return detail('case1',revision);
  });
  await session.select('case1'); session.setDraft('proposal',{slot_start:'2030-01-01T10:00:00Z'});
  await assert.rejects(session.mutate('decisions',{expected_revision:0}), /revision_conflict/);
  assert.equal(session.detail.snapshot.revision,1);
  assert.equal(session.getDraft('proposal').slot_start,'2030-01-01T10:00:00Z');
  assert.match(session.error,/revision_conflict/);
});

test('failed reads preserve loaded detail and surface an error, successful reload clears it', async () => {
  let fail=false;
  const session=new PlatformSession(async () => {if(fail)throw Error('offline');return detail('case1');});
  await session.select('case1'); fail=true;
  await assert.rejects(session.reload(),/offline/);
  assert.equal(session.detail.case_id,'case1'); assert.equal(session.error,'offline');
  fail=false; await session.reload(); assert.equal(session.error,'');
});

test('mutation completion on another case does not overwrite selection or its drafts', async () => {
  const done=deferred();
  const session=new PlatformSession(async (path, options) => options?.method==='POST' ? done.promise : detail(path.split('/').pop()));
  await session.select('first'); session.setDraft('evidence',{text:'First draft'});
  const write=session.mutate('events',{event:{text:'First evidence'}});
  await session.select('second'); session.setDraft('evidence',{text:'Second draft'});
  done.resolve({}); await write;
  assert.equal(session.detail.case_id,'second'); assert.equal(session.getDraft('evidence').text,'Second draft');
  await session.select('first'); assert.equal(session.getDraft('evidence').text,'First draft');
});

test('uncertain failed mutation reuses its idempotency key on an identical retry', async () => {
  const keys=[]; let fail=true;
  const session=new PlatformSession(async (path,options) => {
    if(options?.method==='POST'){keys.push(options.idempotencyKey);if(fail){fail=false;throw Error('offline');}return {};}
    return detail('case1');
  });
  await session.select('case1');
  await assert.rejects(session.mutate('analyze',{mode:'deterministic'}));
  await session.mutate('analyze',{mode:'deterministic'});
  assert.ok(keys[0]); assert.equal(keys[0],keys[1]);
});

test('HTTP adapter sends write guard headers and exposes API errors', async () => {
  let sent;
  const api=createAPI(async (path,options) => {sent=options;return {ok:false,status:409,json:async()=>({error:'revision_conflict'})};});
  await assert.rejects(api('/cases',{method:'POST',body:{case_id:'c'},idempotencyKey:'retry-1'}),e=>e.status===409 && e.message==='revision_conflict');
  assert.equal(sent.headers['X-ProofKey-Request'],'platform-v1');
  assert.equal(sent.headers['Idempotency-Key'],'retry-1');
  assert.equal(sent.body,'{"case_id":"c"}');
});

test('review queue excludes resolved cases even when the immutable decision remains approved', () => {
  assert.equal(needsReview({states:{lifecycle:'resolved',decision:'approved'}}),false);
  assert.equal(needsReview({states:{lifecycle:'ready',decision:'approved'}}),true);
  assert.equal(needsReview({states:{lifecycle:'escalated',decision:'blocked'}}),true);
  assert.equal(needsReview({states:{lifecycle:'new',decision:'none'}}),false);
});

test('derived media text needs successful processing and explicit review, preserving source attribution', () => {
  const run={status:'succeeded',mode:'asr',asset_id:'asset-1',source_sha256:'a'.repeat(64),output_text:'Please deliver tomorrow.'};
  assert.throws(()=>reviewedMediaMessage(run,false),/review/i);
  assert.throws(()=>reviewedMediaMessage({...run,status:'failed'},true),/successful/i);
  const text=reviewedMediaMessage(run,true);
  assert.equal(text,'[Operator-reviewed ASR of asset asset-1 SHA256 '+ 'a'.repeat(64) +']\nPlease deliver tomorrow.');
  assert.throws(()=>reviewedMediaMessage({...run,output_text:'x'.repeat(4096)},true),/4096/);
});

test('reviewed media accepts actual provider envelope with asset_sha256 and output.text', () => {
  assert.equal(reviewedMediaMessage({status:'succeeded',mode:'image_analysis',asset_id:'photo-1',asset_sha256:'b'.repeat(64),output:{text:'A delivery note.'}},true),'[Operator-reviewed image analysis of asset photo-1 SHA256 '+ 'b'.repeat(64) +']\nA delivery note.');
});

test('current blocked actions may be rejected, follow-up acknowledged, but refund not approved', () => {
  assert.equal(canReview({action:{type:'refund'},checks:[{passed:false}]},'reject'),true);
  assert.equal(canReview({action:{type:'refund'},checks:[{passed:false}]},'approve'),false);
  assert.equal(canReview({action:{type:'operator_review'},checks:[{passed:false}]},'approve'),true);
  assert.equal(canReview({action:{type:'request_information'},checks:[{passed:false}]},'approve'),true);
  assert.equal(canReview({action:{type:'reschedule_delivery'},checks:[{passed:false}]},'approve'),false);
});
