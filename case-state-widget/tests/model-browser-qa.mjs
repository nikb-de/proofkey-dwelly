// Real UI against the local source/offline API; only model lifecycle endpoints are simulated.
// No provider transport is invoked. Simulated receipts do not prove provider or PostgreSQL behavior.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
const {chromium}=await import(process.env.PROOFKEY_PLAYWRIGHT_MODULE??'playwright');
const base=process.env.PROOFKEY_BASE_URL??'http://127.0.0.1:8093';
const output=process.env.PROOFKEY_QA_DIR??await fs.mkdtemp(path.join(os.tmpdir(),'proofkey-model-ui-qa-'));
await fs.mkdir(output,{recursive:true});
const browser=await chromium.launch({headless:true,...(process.env.PROOFKEY_CHROME_PATH?{executablePath:process.env.PROOFKEY_CHROME_PATH}:{})});
const page=await browser.newPage({viewport:{width:1440,height:1100}});
page.setDefaultTimeout(10000);
const errors=[],external=[],posts=[],jobs=new Map(),checks=[];
let scenario='success',lostOnce=false,pollFailed=false,releasePost=null,profileAvailable=true;
const profiles=[{id:'sim-openai',label:'Simulated OpenAI',provider:'openai',model:'sim-model',available:true,reason:null},
  {id:'sim-missing',label:'Unavailable test profile',provider:'gemini',model:'sim-missing',available:false,reason:'missing_api_key'}];
page.on('pageerror',error=>errors.push(error.message));
page.on('request',request=>{if(!request.url().startsWith(base)&&!request.url().startsWith('blob:'))external.push(request.url())});
const read=id=>page.locator(`#${id}`).textContent();
const parse=async id=>JSON.parse(await read(id));
const ready=()=>page.waitForFunction(()=>!document.getElementById('analyze').disabled);
const status=async expected=>{await page.waitForFunction(value=>document.getElementById('job-status').textContent===value,expected,{timeout:10000});console.log(`UI status: ${expected}`)};
function response(record,state){
  const terminal=['succeeded','failed','outcome_unknown'].includes(state);
  return {...record,status:state,finished_at:terminal?'2026-10-10T12:00:02Z':null,
    candidate:state==='succeeded'?{schema_version:'proofkey-step-candidate-v1',input_hash:record.input_hash,state:'unknown',mode:'model',
      waiting_for:[],next_action:{type:'operator_review',target_actor_id:null,description:'Simulated browser fixture'},
      evidence_event_ids:[],uncertainty:['SIMULATED UI RECEIPT — no model was called'],operational_effects:0}:null,
    evaluation:state==='succeeded'?{accuracy_score:null,qualification:'Simulated UI fixture'}:null,
    error:state==='failed'?{code:'invalid_model_output',phase:'validation'}:state==='outcome_unknown'?{code:'provider_outcome_unknown',phase:'dispatch'}:null,
    receipt:state==='succeeded'?{model_profile_id:'sim-openai',provider:'openai',requested_model:'sim-model',observed_model:'sim-model-snapshot',
      request_id:'SIMULATED <img src=x onerror="window.unsafe=true">',usage:{input_tokens:null,output_tokens:22},latency_ms:1234}:null};
}
await page.route('**/api/model-profiles',route=>route.fulfill({json:{enabled:true,profiles:profiles.map(item=>item.id==='sim-openai'?{...item,available:profileAvailable,reason:profileAvailable?null:'missing_api_key'}:item)}}));
await page.route('**/api/model-runs',async route=>{
  const body=route.request().postDataJSON(),key=route.request().headers()['idempotency-key'];posts.push({body,key});
  const input=await parse('input-json'),reference=await parse('reference-json'),source=await parse('source-json');
  let record=jobs.get(key);
  if(!record){record={schema_version:'proofkey-model-job-v1',run_id:`sim-run-${jobs.size+1}`,status:'queued',...body,input_hash:body.expected_input_hash,
    input,reference,source,candidate:null,evaluation:null,receipt:null,error:null,created_at:'2026-10-10T12:00:00Z',started_at:null,finished_at:null,
    transaction:{idempotency_key:key,attempt_id:'SIMULATED-attempt',dispatch_attempts:0,automatic_retries:0,operational_effects:0,
      reserved_usd:'0.02',budget_scope:'SIMULATED-BROWSER-ONLY',prompt_hash:'sim-prompt',profile_hash:'sim-profile'},polls:0,scenario};jobs.set(key,record)}
  if(scenario==='lost'&&!lostOnce){lostOnce=true;await route.abort('failed');return}
  if(scenario==='stale')await new Promise(resolve=>releasePost=resolve);
  await route.fulfill({status:202,json:response(record,'queued')});
});
await page.route('**/api/model-runs/*',async route=>{
  const id=route.request().url().split('/').at(-1),record=[...jobs.values()].find(item=>item.run_id===id);assert.ok(record);
  if(scenario==='poll-failure'&&!pollFailed){pollFailed=true;await route.abort('failed');return}
  record.polls++;
  const states=record.scenario==='failed'?['failed']:record.scenario==='unknown'?['outcome_unknown']:scenario==='paused'?['running']:['running','response_received','succeeded'];
  await route.fulfill({json:response(record,states[Math.min(record.polls-1,states.length-1)])});
});
try {
  await page.goto(base);await ready();
  assert.equal(await page.locator('#engine-select').inputValue(),'offline');
  assert.equal(await page.locator('#engine-select option[value="sim-missing"]').isDisabled(),true);
  await page.selectOption('#engine-select','sim-openai');await ready();
  await page.click('#analyze');await status('Queued');await status('Running');await status('Response received');await status('Succeeded');
  assert.equal((await parse('candidate-json')).state,'unknown');
  await page.locator('#transaction-details > summary').click();
  assert.match(await read('receipt-summary'),/sim-model-snapshot/);assert.match(await read('receipt-summary'),/Not reported/);
  const usage=await page.locator('#receipt-summary').evaluate(el=>Object.fromEntries([...el.querySelectorAll('dt')].map(term=>[term.textContent,term.nextElementSibling.textContent])));
  assert.equal(usage['Input tokens'],'Not reported');assert.equal(usage['Output tokens'],'22');
  assert.equal(await page.locator('#transaction-details img').count(),0);assert.equal(await page.evaluate(()=>window.unsafe),undefined);
  assert.equal((await parse('input-json')).reference,undefined);assert.equal((await parse('reference-json')).qualification,'author_labels_unvalidated');
  checks.push('Simulated queued/running/response_received/succeeded lifecycle; separate author reference; nullable usage; escaped receipt text');
  await page.screenshot({path:path.join(output,'model-desktop.png'),fullPage:true});

  scenario='failed';await page.click('#analyze');await status('Failed');assert.match(await read('candidate-json'),/No valid candidate/);
  assert.match(await read('job-error'),/invalid_model_output/);checks.push('Failed simulated job renders its error with a null candidate');
  scenario='unknown';const beforeUnknown=posts.length;await page.click('#analyze');await status('Outcome unknown');
  await page.waitForTimeout(1200);assert.equal(posts.length,beforeUnknown+1);assert.equal(await page.locator('#reconnect').isVisible(),false);
  checks.push('Unknown simulated outcome is terminal and does not automatically resubmit');

  scenario='poll-failure';await page.click('#analyze');await page.locator('#connection-warning').waitFor({state:'visible'});
  assert.equal(await read('job-status'),'Queued');const beforeReconnect=posts.length;await page.click('#reconnect');await status('Succeeded');
  assert.equal(posts.length,beforeReconnect);checks.push('A failed status read retains the acknowledged job; reconnect only polls');

  scenario='lost';await page.click('#analyze');await page.locator('#connection-warning').waitFor({state:'visible'});
  const lostKey=posts.at(-1).key;await page.reload();await ready();
  const beforeResume=posts.length;await page.click('#resume-last');await status('Succeeded');
  assert.equal(posts.length,beforeResume+1);assert.equal(posts.at(-1).key,lostKey);
  checks.push('Lost acknowledgement survives reload as metadata and replays the same key only on explicit resume');

  await page.selectOption('#step-select','3');await ready();
  scenario='paused';await page.click('#analyze');await status('Queued');await page.reload();await ready();
  scenario='success';const beforeGetResume=posts.length;await page.click('#resume-last');await status('Succeeded');
  assert.equal(posts.length,beforeGetResume);
  assert.equal((await parse('input-json')).step_index,3);
  assert.equal(await page.locator('case-state-viewer').evaluate(viewer=>viewer.stepIndex),3);
  checks.push('Nonzero-step accepted-run recovery uses GET and synchronizes source timeline, selection, and evidence');

  scenario='paused';await page.click('#analyze');await status('Queued');profileAvailable=false;
  await page.reload();await ready();scenario='success';const beforeUnavailableResume=posts.length;
  await page.click('#resume-last');await status('Succeeded');
  assert.equal(posts.length,beforeUnavailableResume);assert.equal(await page.locator('#analyze').isDisabled(),true);
  assert.equal(await page.locator('#engine-select').inputValue(),'sim-openai');
  checks.push('Acknowledged run remains viewable by GET after credentials disappear; new model runs are disabled');
  profileAvailable=true;await page.reload();await ready();await page.selectOption('#engine-select','sim-openai');await ready();

  scenario='stale';await page.click('#analyze');await page.waitForFunction(()=>document.getElementById('status').textContent.includes('Submitting'));
  while(!releasePost)await new Promise(resolve=>setTimeout(resolve,10));
  await page.selectOption('#engine-select','offline');releasePost();await ready();await page.waitForTimeout(100);
  assert.equal(await page.locator('#download-run').isDisabled(),true);assert.equal(await page.locator('#job-status').isVisible(),false);
  checks.push('A delayed model acknowledgement cannot populate a different profile selection');

  await page.selectOption('#engine-select','offline');await page.click('#analyze');
  await page.waitForFunction(()=>!document.getElementById('download-run').disabled);
  assert.equal((await parse('candidate-json')).live_calls,0);checks.push('Existing real offline API still returns its zero-call baseline');

  scenario='success';await page.selectOption('#engine-select','sim-openai');await page.click('#analyze');await status('Succeeded');
  await page.setViewportSize({width:390,height:844});
  if(await page.locator('#transaction-details').getAttribute('open')===null)await page.locator('#transaction-details > summary').click();
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.screenshot({path:path.join(output,'model-mobile.png'),fullPage:true});checks.push('390px mobile model controls and receipt details have no horizontal overflow');
  assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
  const result={mode:'SIMULATED_MODEL_LIFECYCLE_WITH_REAL_LOCAL_UI_AND_OFFLINE_API',base,output,checks,errors,external,
    actual_provider_calls:0,postgres_verification:false,operational_effects:0};
  await fs.writeFile(path.join(output,'receipt.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
} catch(error) {
  console.error(JSON.stringify({errors,posts,status:await read('status'),error:await read('error'),connection:await read('connection-message')},null,2));
  await page.screenshot({path:path.join(output,'failure.png'),fullPage:true});throw error;
} finally {await browser.close()}
