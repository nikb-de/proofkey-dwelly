// Requires the explicit test-only fixture server. Refuses real provider profiles.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
const {chromium}=await import(process.env.PROOFKEY_PLAYWRIGHT_MODULE??'playwright');
const base=process.env.PROOFKEY_BASE_URL??'http://127.0.0.1:8094';
const output=process.env.PROOFKEY_QA_DIR??await fs.mkdtemp(path.join(os.tmpdir(),'proofkey-postgres-ui-qa-'));
await fs.mkdir(output,{recursive:true});
const profiles=await (await fetch(`${base}/api/model-profiles`)).json();
assert.equal(profiles.profiles.length,1);
assert.equal(profiles.profiles[0].id,'browser-fixture');
assert.equal(profiles.profiles[0].model,'SIMULATED-NOT-A-PROVIDER');
const browser=await chromium.launch({headless:true,...(process.env.PROOFKEY_CHROME_PATH?{executablePath:process.env.PROOFKEY_CHROME_PATH}:{})});
const page=await browser.newPage({viewport:{width:1440,height:1100}});
const errors=[],posts=[];
page.on('pageerror',error=>errors.push(error.message));
page.on('request',request=>{if(request.method()==='POST')posts.push(request.url())});
try {
  await page.goto(base);
  await page.waitForFunction(()=>!document.getElementById('analyze').disabled);
  await page.selectOption('#step-select','3');
  await page.waitForFunction(()=>!document.getElementById('analyze').disabled);
  await page.selectOption('#engine-select','browser-fixture');
  // Simulate a browser-only status outage; API worker and PostgreSQL remain real.
  await page.route('**/api/model-runs/*',route=>route.abort('failed'));
  await page.click('#analyze');
  await page.locator('#connection-warning').waitFor({state:'visible'});
  const saved=await page.evaluate(()=>JSON.parse(sessionStorage.getItem('proofkey.analysis.pending.v1')));
  assert.ok(saved.runId);
  const before=posts.length;
  await page.unroute('**/api/model-runs/*');
  await page.reload();await page.waitForFunction(()=>!document.getElementById('analyze').disabled);
  await page.click('#resume-last');
  await page.waitForFunction(()=>document.getElementById('job-status').textContent==='Succeeded');
  assert.equal(posts.length,before);
  assert.equal(await page.locator('case-state-viewer').evaluate(viewer=>viewer.stepIndex),3);
  assert.equal(await page.locator('#step-select').inputValue(),'3');
  const download=page.waitForEvent('download');
  await page.click('#download-run');
  const stream=await (await download).createReadStream();
  const chunks=[];for await(const chunk of stream)chunks.push(chunk);
  const job=JSON.parse(Buffer.concat(chunks).toString());
  assert.equal(job.status,'succeeded');assert.equal(job.receipt.request_id,'SIMULATED-BROWSER-POSTGRES');
  assert.equal(job.transaction.dispatch_attempts,1);assert.equal(job.transaction.automatic_retries,0);
  assert.equal(job.transaction.operational_effects,0);assert.equal(job.receipt.usage.input_tokens,123);
  await page.locator('#transaction-details > summary').click();
  assert.match(await page.locator('#receipt-summary').textContent(),/123/);
  const reread=await (await fetch(`${base}/api/model-runs/${job.run_id}`)).json();
  assert.deepEqual(reread,job);
  await page.screenshot({path:path.join(output,'postgres-ui-desktop.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.screenshot({path:path.join(output,'postgres-ui-mobile.png'),fullPage:true});
  assert.deepEqual(errors,[]);
  const receipt={mode:'REAL_UI_API_POSTGRES_WITH_SIMULATED_PROVIDER_TRANSPORT',run_id:job.run_id,base,output,
    checks:['UI submission through real API and PostgreSQL','single dispatch marker and durable result',
      'nested usage rendered','API readback equals download','reload resumes by GET only','mobile no horizontal overflow'],
    actual_provider_calls:0,postgres_verified:true,operational_effects:0,errors};
  await fs.writeFile(path.join(output,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');
  console.log(JSON.stringify(receipt,null,2));
} finally {await browser.close()}
