// Real HTTP/PostgreSQL/MediaService acceptance; only the external provider is a test double.
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {mkdtemp,readFile} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {once} from 'node:events';
import readline from 'node:readline';
const {chromium}=await import(process.env.PROOFKEY_PLAYWRIGHT_MODULE || '/Users/nbk/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs');
const output=process.env.PROOFKEY_QA_DIR || await mkdtemp(path.join(os.tmpdir(),'proofkey-media-ui-'));
const python=process.env.PROOFKEY_TEST_PYTHON || '/tmp/proofkey-postgres-tests-20261010/bin/python';
const server=spawn(python,['-m','tools.dwelly_platform.tests.media_browser_server','--port',process.env.PROOFKEY_MEDIA_PORT || '8096','--output-dir',output],{cwd:process.cwd(),env:process.env,stdio:['ignore','pipe','pipe']});
let stderr='';server.stderr.on('data',value=>{stderr+=value;});
const lines=readline.createInterface({input:server.stdout});
const ready=await Promise.race([once(lines,'line').then(([line])=>JSON.parse(line)),once(server,'exit').then(([code])=>{throw Error(`Fixture exited ${code}: ${stderr}`);})]);
assert.equal(ready.test_only,true);assert.equal(ready.provider,'test-provider');
const browser=await chromium.launch({headless:true,executablePath:process.env.PROOFKEY_CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
const page=await browser.newPage({viewport:{width:1512,height:1100}});
const errors=[];page.on('pageerror',e=>errors.push(e.message));
let outcome;
try {
  await page.goto(ready.origin);await page.locator('#create-case-panel summary').click();
  await page.fill('#case-id','test-media-case');await page.fill('#order-id','test-media-order');
  await page.locator('#create-case-form button').click();await page.locator('#case-title').filter({hasText:'test-media-case'}).waitFor();
  const waitWrite=route=>page.waitForResponse(r=>r.url().includes('/cases/test-media-case/'+route) && r.request().method()==='POST');
  async function upload(kind,file,text){
    await page.selectOption('#evidence-kind',kind);await page.fill('#evidence-text',text);
    await page.setInputFiles('#evidence-file',path.join(output,file));
    const done=waitWrite('events');await page.locator('#evidence-form button').click();assert.ok((await done).ok());
    await page.waitForFunction(()=>!document.getElementById('analyze-case').disabled);
  }
  await upload('photo','source.png','TEST SOURCE: delivery note photo');
  await upload('voice_message','source.wav','TEST SOURCE: customer voice note');
  const before=await page.evaluate(async()=>await (await fetch('/api/platform/cases/test-media-case')).json());
  assert.equal(before.case.media_runs.length,0);
  const photo=page.locator('.evidence-item').filter({hasText:'TEST SOURCE: delivery note photo'});
  const audio=page.locator('.evidence-item').filter({hasText:'TEST SOURCE: customer voice note'});
  let pending=waitWrite('assets/');await photo.getByRole('button',{name:'Analyze image',exact:true}).click();assert.ok((await pending).ok());
  await photo.locator('.derived-evidence').waitFor();
  assert.match(await photo.innerText(),/pillow decode/i);
  assert.match(await photo.locator('.derived-evidence').innerText(),/TEST PROVIDER/);
  assert.equal(await page.evaluate(()=>Boolean(window.mediaInjected)),false);
  pending=waitWrite('assets/');await audio.getByRole('button',{name:'Transcribe audio',exact:true}).click();assert.ok((await pending).ok());
  await audio.locator('.derived-evidence').waitFor();assert.match(await audio.innerText(),/ffprobe/i);
  await photo.getByRole('button',{name:'Use reviewed text',exact:true}).click();
  assert.match(await page.locator('#error-message').innerText(),/Confirm you reviewed/);
  assert.equal((await page.evaluate(async()=>await (await fetch('/api/platform/cases/test-media-case')).json())).case.snapshot.revision,2);
  for(const source of [photo,audio]){
    await source.locator('.derived-evidence input[type="checkbox"]').check();
    pending=waitWrite('events');await source.getByRole('button',{name:'Use reviewed text',exact:true}).click();assert.ok((await pending).ok());
    await page.waitForFunction(()=>!document.getElementById('analyze-case').disabled);
  }
  const current=await page.evaluate(async()=>await (await fetch('/api/platform/cases/test-media-case')).json());
  assert.equal(current.case.media_runs.length,2);assert.equal(current.case.snapshot.revision,4);
  const derived=current.case.snapshot.events.filter(e=>e.channel==='internal');assert.equal(derived.length,2);
  for(const event of derived){assert.equal(event.sender_id,'operator-1');assert.deepEqual(event.recipient_ids,['customer-1']);assert.match(event.text,/^\[Operator-reviewed (ASR|image analysis) of asset .* SHA256 [a-f0-9]{64}\]/);}
  for(const run of current.case.media_runs){assert.equal(run.receipt.provider,'test-provider');assert.equal(run.human_review,'required');assert.equal(run.validation.sha256_verified,true);assert.equal(run.status,'succeeded');}
  await page.reload();await page.locator('#case-detail').waitFor({state:'visible'});
  assert.equal(await page.locator('.derived-evidence').count(),2);
  assert.equal(await page.getByRole('button',{name:'Reviewed text added',exact:true}).count(),2);
  await upload('photo','invalid.png','TEST SOURCE: intentionally corrupt photo');
  await page.fill('#evidence-text','Keep this unfinished operator draft after validation fails.');
  const invalid=page.locator('.evidence-item').filter({hasText:'TEST SOURCE: intentionally corrupt photo'});
  pending=waitWrite('assets/');await invalid.getByRole('button',{name:'Analyze image',exact:true}).click();assert.equal((await pending).status(),400);
  await page.locator('#error-message').waitFor({state:'visible'});assert.match(await page.locator('#error-message').innerText(),/invalid_media/);
  assert.equal(await page.inputValue('#evidence-text'),'Keep this unfinished operator draft after validation fails.');
  await page.evaluate(()=>window.scrollTo(0,0));
  await page.screenshot({path:path.join(output,'desktop.png'),fullPage:true});
  const mobile=await browser.newPage({viewport:{width:390,height:844}});mobile.on('pageerror',e=>errors.push(e.message));
  await mobile.goto(ready.origin+'/#case=test-media-case');await mobile.locator('#case-detail').waitFor({state:'visible'});await mobile.evaluate(()=>document.fonts.ready);
  assert.equal(await mobile.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  await mobile.screenshot({path:path.join(output,'mobile.png'),fullPage:true});
  assert.deepEqual(errors,[]);
  outcome={status:'passed',output,testOnlyProvider:'test-provider',liveProviderCalls:0,checks:['real PNG/WAV validation','separate derived output','provider receipt','source hash','explicit human review','canonical internal evidence','reload persistence','no automatic processing','corrupt media rejected','draft retained','inert HTML-like output','mobile layout']};
} finally {
  await browser.close();const stopped=once(server,'exit');server.kill('SIGTERM');await stopped;lines.close();
}
const report=JSON.parse(await readFile(path.join(output,'database-report.json'),'utf8'));
assert.equal(report.schema_dropped,true);assert.equal(report.calls.length,2);
assert.deepEqual(report.calls.map(c=>c.mode),['image_analysis','asr']);
assert.equal(report.cases[0].media_runs.length,2);
assert.equal(report.cases[0].model_projection.messages.filter(m=>m.body.startsWith('[Operator-reviewed')).length,2);
assert.equal(report.cases[0].snapshot.events.length,5);
console.log(JSON.stringify({...outcome,schemaDropped:report.schema_dropped,providerDispatches:report.calls.length}));
