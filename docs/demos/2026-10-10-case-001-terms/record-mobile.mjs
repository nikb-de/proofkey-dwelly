// Actual browser capture of the frozen case. No mocked HTTP or provider output.
// Run with PROOFKEY_RECORD_TERMS=1 and PROOFKEY_RECORD_MODE=synthetic|llm.
import assert from 'node:assert/strict';
import {mkdir,writeFile} from 'node:fs/promises';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {performance} from 'node:perf_hooks';

assert.equal(process.env.PROOFKEY_RECORD_TERMS,'1','Explicit recording opt-in required');
const mode=process.env.PROOFKEY_RECORD_MODE;
assert.ok(['synthetic','llm'].includes(mode),'Select synthetic or llm explicitly');
const root=fileURLToPath(new URL('../../../',import.meta.url));
const origin=new URL(process.env.PROOFKEY_RECORD_ORIGIN || 'http://127.0.0.1:8110');
assert.ok(origin.protocol==='http:' && ['127.0.0.1','localhost'].includes(origin.hostname) && origin.pathname==='/' && !origin.username && !origin.password && !origin.search && !origin.hash);
const runId=`${Date.now()}-${crypto.randomUUID().slice(0,8)}`;
const caseId=`terms-video-${mode}-${runId}`;
const output=path.join(root,'docs/demos/2026-10-10-case-001-terms/recordings',`${mode}-${runId}`);
await mkdir(output,{recursive:true});
const python=process.env.PROOFKEY_RECORD_PYTHON || '/tmp/proofkey-postgres-tests-20261010/bin/python';
const source=await promisify(execFile)(python,['-c','import json,sys; from tools.dwelly_platform.scenarios import prepare_terms_demo; print(json.dumps(prepare_terms_demo(sys.argv[1],sys.argv[2])))',caseId,'2026-10-10'],{cwd:root,env:{...process.env,PYTHONPATH:'.:tools:runtime/src'}});
const prepared=JSON.parse(source.stdout),events=new Map(prepared.events.map(e=>[e.event_id,e]));
const report={run_id:runId,mode,case_id:caseId,origin:origin.origin,status:'running',provenance:prepared.provenance,model_calls:0,model_call_limit:mode==='llm'?5:0,model_profile:'openai-gpt-6-1-sol',external_effects:0,physical_delivery:'not_confirmed',qualification:'Actual mobile browser capture; frozen synthetic scenario; operator-reviewed local coordination; pseudo-Dispatch readbacks, not a carrier integration.',http:[],ui_commands:[],models:[],segments:[],browser_errors:[],screenshots:[]};
const casePath=`/api/platform/cases/${caseId}`;
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function http(route,body,status=200){
  assert.ok(!body || route==='/api/platform/cases' || route.startsWith(`${casePath}/`),'Fresh owned case writes only');
  const response=await fetch(new URL(route,origin),{method:body?'POST':'GET',redirect:'error',headers:body?{'Content-Type':'application/json','X-ProofKey-Request':'platform-v1','Idempotency-Key':`video-${runId}-${crypto.randomUUID()}`}:{},body:body?JSON.stringify(body):undefined});
  const value=await response.json();report.http.push({path:route,status:response.status,method:body?'POST':'GET',request:body || null,response:value});assert.equal(response.status,status,JSON.stringify(value));return value;
}
const detail=async()=>(await http(casePath)).case;
async function append(event){const d=await detail();assert.ok(!d.snapshot.events.some(e=>e.event_id===event.event_id));await http(`${casePath}/events`,{expected_revision:d.snapshot.revision,event});}
async function appendId(id){await append(events.get(id));}
async function readback(id,kind){
  const d=await detail(),request=d.coordination.pending_request,sourceEvent=events.get(id);
  const payload={simulation:'LOCAL_SANDBOX_DISPATCH_READBACK_NOT_AUTHENTIC_CARRIER',source_event_id:id,request_id:request.request_id};
  if(kind==='booking')payload.terms_hash=request.terms_hash;
  const event={...sourceEvent,event_id:`demo-readback-${id}`,text:JSON.stringify(payload)};await append(event);return event.event_id;
}
let browser,page,video,clock;
const time=()=>Number(((performance.now()-clock)/1000).toFixed(3));
const stages=[
  {title:'01  Request & cancellation',subtitle:'Cancel the original slot, then verify the readback.',clips:[]},
  {title:'02  Find workable terms',subtitle:'Evening delivery and concierge handover requested.',clips:[]},
  {title:'03  Review changed conditions',subtitle:'New daytime slot. Recipient must attend. No charge.',clips:[]},
  {title:'04  Consent before booking',subtitle:'Review consent, then request the accepted booking.',clips:[]},
  {title:'05  Confirm, do not assume',subtitle:'Verify booking by readback. Delivery is NOT confirmed.',clips:[]},
];
async function team(){await page.goto(`${origin.origin}/#case=${caseId}`);await page.reload();await page.locator('#coordination-command, #coordination-panel .coordination-boundary').first().waitFor({state:'attached'});await page.locator('#case-detail').waitFor({state:'visible'});}
async function focus(locator){await locator.waitFor({state:'visible'});await locator.evaluate(el=>window.scrollTo({top:Math.max(0,el.getBoundingClientRect().top+window.scrollY-24),behavior:'instant'}));await sleep(450);}
async function hold(stage,locator,seconds=3){await focus(locator);const start=time();await sleep(seconds*1000);const end=time();stage.clips.push({start,end});const file=path.join(output,`stage-${stages.indexOf(stage)+1}-${stage.clips.length}.png`);await page.screenshot({path:file});report.screenshots.push(file);}
async function sourceView(stage,id,seconds=3){await page.locator('#tab-sources').click();await hold(stage,page.locator(`#evidence-list [data-event-id="${id}"]`),seconds);await page.locator('#tab-summary').click();}
async function assess(stage){
  await page.locator('#tab-summary').click();
  if(mode==='synthetic'){
    await focus(page.locator('#analysis-card'));
    const pending=page.waitForResponse(r=>r.url()===`${origin.origin}${casePath}/analyze` && r.request().method()==='POST');
    await page.locator('#analyze-case').click();const response=await pending;assert.equal(response.status(),200);report.http.push({path:`${casePath}/analyze`,status:200,method:'POST',request:response.request().postDataJSON(),response:await response.json()});
    await page.locator('#status-message').filter({hasText:'Analysis recorded'}).waitFor();
    await hold(stage,page.locator('#summary-next-step'),3);return null;
  }
  assert.ok(report.model_calls<5,'Paid call ceiling reached');
  await page.locator('#analysis-card details.model-options').evaluate(el=>el.open=true);
  await page.selectOption('#model-profile',report.model_profile);await focus(page.locator('#run-model'));
  const prior=await detail();
  const pending=page.waitForResponse(r=>r.url()===`${origin.origin}${casePath}/model-runs` && r.request().method()==='POST');
  await page.locator('#run-model').click();const response=await pending;report.model_calls++;assert.equal(response.status(),202);const admitted=await response.json();
  report.http.push({path:`${casePath}/model-runs`,status:202,method:'POST',request:response.request().postDataJSON(),response:admitted});
  assert.equal(admitted.source.revision,prior.snapshot.revision);assert.equal(admitted.source.snapshot_hash,prior.snapshot.snapshot_hash);assert.equal(admitted.reference,null);
  let job=admitted;const deadline=performance.now()+155000;
  while(['queued','running','response_received'].includes(job.status) && performance.now()<deadline){await sleep(1200);job=await http(`/api/platform/model-runs/${admitted.run_id}`);}
  report.models.push(job);await writeFile(path.join(output,`model-${report.model_calls}.json`),JSON.stringify(job,null,2));
  assert.equal(job.status,'succeeded',`Stop without automatic retry: ${JSON.stringify(job.error)}`);
  assert.equal(job.receipt.provider,'openai');assert.equal(job.receipt.requested_model,'gpt-6.1-sol');assert.equal(job.transaction.dispatch_attempts,1);assert.equal(job.transaction.automatic_retries,0);
  assert.ok(job.input.messages.every(m=>prior.snapshot.events.some(e=>e.event_id===m.event_id)),'No future messages');
  await page.locator('#refresh-case').click();await page.locator(`#model-jobs [data-job-id="${job.run_id}"] .model-transport`).filter({hasText:'Succeeded'}).waitFor();
  await hold(stage,page.locator(`#model-jobs [data-job-id="${job.run_id}"]`),4);return job;
}
async function act(command,phase,{evidence=[],terms,job}={}){
  await page.locator('#tab-summary').click();
  if(await page.locator('#coordination-command').inputValue()!==command)await page.selectOption('#coordination-command',command);
  if(terms){await page.fill('#coordination-start',terms.slot_start);await page.fill('#coordination-end',terms.slot_end);await page.selectOption('#coordination-handover',terms.handover);await page.fill('#coordination-amount',terms.charge.amount_minor===null?'':String(terms.charge.amount_minor));await page.fill('#coordination-currency',terms.charge.currency || '');}
  for(const id of evidence)await page.locator(`[name="coordination-evidence"][value="${id}"]`).check();
  if(job && evidence.every(id=>job.candidate.evidence_event_ids.includes(id))){await page.locator('#coordination-form details').filter({has:page.locator('#coordination-model')}).evaluate(el=>el.open=true);await page.selectOption('#coordination-model',job.run_id);await page.fill('#coordination-model-note','Reviewed advisory against the current original source. Explicit operator command; no model execution authority.');}
  await page.locator('#coordination-reviewed').check();assert.equal(await page.locator('#coordination-submit').isEnabled(),true,await page.locator('#coordination-validation').innerText());
  const pending=page.waitForResponse(r=>r.url()===`${origin.origin}${casePath}/coordination` && r.request().method()==='POST');
  await page.locator('#coordination-submit').click();const response=await pending,value=await response.json();report.ui_commands.push({command,status:response.status(),request:response.request().postDataJSON(),response:value});assert.equal(response.status(),200,JSON.stringify(value));assert.equal(value.coordination.phase,phase);
  await page.locator('#coordination-panel').filter({has:page.locator(`.tag:text-is("${phase.replaceAll('_',' ')}")`)}).waitFor();
  const d=await detail();assert.equal(d.coordination.phase,phase);assert.equal(d.coordination.external_effects,0);assert.equal(d.coordination.physical_delivery,'not_confirmed');return d;
}
try{
  const cap=await http('/api/platform/capabilities');assert.equal(cap.execution_mode,'local_sandbox');assert.equal(cap.external_effects,0);
  if(mode==='llm')assert.ok(cap.models.enabled && cap.models.profiles.some(p=>p.id===report.model_profile && p.available));
  await http(casePath,null,404);await http('/api/platform/cases',prepared.declaration,201);await appendId('source-context');await appendId('001');
  let d=await detail();await http(`${casePath}/coordination`,{command:'initialize',expected_revision:d.snapshot.revision,snapshot_hash:d.snapshot.snapshot_hash,expected_workflow_version:0,dispatch_actor_id:'dispatch',original_booking:prepared.original_booking});
  const {chromium}=await import(process.env.PROOFKEY_PLAYWRIGHT_MODULE || '/Users/nbk/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs');
  browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
  const context=await browser.newContext({viewport:{width:390,height:666},deviceScaleFactor:1,recordVideo:{dir:path.join(output,'raw'),size:{width:390,height:666}}});
  await context.route('**/*',route=>{const u=new URL(route.request().url());if(u.origin!==origin.origin)return route.abort();return route.continue();});
  page=await context.newPage();page.setDefaultTimeout(15000);page.on('pageerror',e=>report.browser_errors.push(e.message));video=page.video();clock=performance.now();
  await team();await sourceView(stages[0],'001',3);let job=await assess(stages[0]);await act('request_cancellation','cancellation_pending',{evidence:['001'],job});
  await appendId('002');await appendId('003');const cancelled=await readback('003','cancellation');await team();await act('confirm_cancellation','awaiting_terms',{evidence:[cancelled]});await hold(stages[0],page.locator('#coordination-panel'),3);
  await appendId('004');await appendId('005');await team();await sourceView(stages[1],'005',3);await assess(stages[1]);await appendId('006');await team();await hold(stages[1],page.locator('#summary-next-step'),3);
  await appendId('007');await team();await sourceView(stages[2],'007',3);job=await assess(stages[2]);await act('record_offer','awaiting_consent',{evidence:['007'],terms:prepared.offered_terms,job});
  await appendId('008');await page.goto(`${origin.origin}/customer.html?case=${caseId}`);await hold(stages[2],page.locator('#customer-coordination'),3);
  await appendId('009');await team();await sourceView(stages[3],'009',3);job=await assess(stages[3]);await act('record_consent','ready_to_book',{evidence:['009'],job});await act('request_booking','booking_pending');await appendId('010');await team();await hold(stages[3],page.locator('#coordination-panel'),3);
  await appendId('011');const booked=await readback('011','booking');await team();await sourceView(stages[4],'011',3);job=await assess(stages[4]);await act('confirm_booking','booking_confirmed',{evidence:[booked],job});
  await page.goto(`${origin.origin}/customer.html?case=${caseId}`);await page.getByRole('heading',{name:'Booking confirmed locally',exact:true}).waitFor();await hold(stages[4],page.locator('#customer-coordination'),4);
  d=await detail();report.final=d;assert.equal(d.coordination.phase,'booking_confirmed');assert.equal(d.coordination.version,7);assert.equal(d.coordination.operation_receipts.length,2);assert.equal(d.coordination.consent.evidence_event_ids[0],'009');assert.equal(d.snapshot.revision,21);assert.equal(d.model_jobs.length,mode==='llm'?5:0);assert.equal(report.models.length,mode==='llm'?5:0);assert.deepEqual(report.browser_errors,[]);
  report.status='passed';report.segments=stages;await context.close();report.raw_video=await video.path();
  await writeFile(path.join(output,'assembly.json'),JSON.stringify({raw_video:report.raw_video,mode_label:mode==='llm'?'LIVE LLM · GPT-6.1 SOL':'SCRIPTED · ZERO MODEL CALLS',segments:stages,output:path.join(output,`case-001-${mode}-50s.mp4`)},null,2));
}catch(error){report.status='failed';report.failure={message:error.message,stack:error.stack};process.exitCode=1;if(page)await page.screenshot({path:path.join(output,'failure.png'),fullPage:true}).catch(()=>{});}
finally{if(browser)await browser.close();if(video)report.raw_video=await video.path().catch(()=>null);await writeFile(path.join(output,'capture-report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({status:report.status,output,case_id:caseId,model_calls:report.model_calls,failure:report.failure},null,2));}
