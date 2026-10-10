// Run against the local analysis server. No provider calls; the only writes are local run records and QA files.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
const {chromium}=await import(process.env.PROOFKEY_PLAYWRIGHT_MODULE??'playwright');
const base=process.env.PROOFKEY_BASE_URL??'http://127.0.0.1:8093';
const output=process.env.PROOFKEY_QA_DIR??await fs.mkdtemp(path.join(os.tmpdir(),'proofkey-browser-qa-'));
await fs.mkdir(output,{recursive:true});
const browser=await chromium.launch({headless:true,...(process.env.PROOFKEY_CHROME_PATH?{executablePath:process.env.PROOFKEY_CHROME_PATH}:{})});
const page=await browser.newPage({viewport:{width:1440,height:1100}});
const errors=[], external=[];page.on('pageerror',error=>errors.push(error.message));
page.on('request',request=>{if(!request.url().startsWith(base)&&!request.url().startsWith('blob:'))external.push(request.url())});
const waitReady=()=>page.waitForFunction(()=>!document.getElementById('analyze').disabled);
const read=id=>page.locator(`#${id}`).textContent();
const parse=async id=>JSON.parse(await read(id));
const choose=async(id,index=0)=>{
  await page.selectOption('#case-select',id);await waitReady();
  if(index){await page.selectOption('#step-select',String(index));await waitReady()}
};
const run=async()=>{await page.click('#analyze');await page.waitForFunction(()=>!document.getElementById('download-run').disabled);return parse('candidate-json')};
const checks=[];
try {
  await page.goto(base);await waitReady();
  assert.equal(await page.title(),'ProofKey · Case state workbench');
  const catalog=await page.evaluate(async()=> (await (await fetch('/api/catalog')).json()).cases);
  let count=0;
  for(const item of catalog){
    await choose(item.id);
    for(let index=0;index<=item.steps;index++){
      if(index){await page.selectOption('#step-select',String(index));await waitReady()}
      const input=await parse('input-json'); assert.equal(input.case_id,item.id);assert.equal(input.step_index,index);
      assert.equal(await page.locator('case-state-viewer').evaluate(el=>el.stepIndex),index);
      for(const key of ['reference','state_after','annotations','success_criteria','explanation'])assert.equal(Object.hasOwn(input,key),false);
      const candidate=await run();assert.equal(candidate.input_hash,input.input_hash);assert.equal(candidate.live_calls,0);assert.equal(candidate.operational_effects,0);
      assert.equal((await parse('reference-json')).qualification,'author_labels_unvalidated');
      count++;
    }
  }
  assert.equal(catalog.filter(item=>!item.id.startsWith('team-')).reduce((total,item)=>total+item.steps+1,0),16);
  assert.equal(catalog.filter(item=>item.id.startsWith('team-')).reduce((total,item)=>total+item.steps+1,0),20);
  assert.equal(count,36);checks.push('36 catalog snapshots (legacy 16 + team 20): input, source navigation, offline candidate, zero calls/effects, separate reference');
  await choose('case-002-n4',5);const n4=await run();
  assert.match(JSON.stringify(n4.next_action),/readback|verify|saved/i);checks.push('N4 ambiguous outcome requests verification');
  const downloadEvent=page.waitForEvent('download');await page.click('#download-run');const download=await downloadEvent;
  const stream=await download.createReadStream();const chunks=[];for await(const chunk of stream)chunks.push(chunk);
  const record=JSON.parse(Buffer.concat(chunks).toString());assert.equal(record.input.step_index,5);assert.equal(record.candidate.input_hash,record.input.input_hash);assert.equal(record.live_calls,0);checks.push('Full run JSON download includes bound input and candidate');
  await page.screenshot({path:path.join(output,'desktop-source.png'),fullPage:true});
  await page.locator('details.source > summary').click();await page.locator('.results').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(output,'desktop-results.png'),fullPage:true});

  // Keep real service responses, delaying delivery to exercise browser-level races.
  let releaseCase;const caseGate=new Promise(resolve=>releaseCase=resolve);let caseSeen,caseDone;
  const caseDoneGate=new Promise(resolve=>caseDone=resolve);
  const caseSeenGate=new Promise(resolve=>caseSeen=resolve);
  await page.route('**/api/cases/case-002',async route=>{const response=await route.fetch();caseSeen();await caseGate;await route.fulfill({response});caseDone()});
  await page.selectOption('#case-select','case-002');await caseSeenGate;
  await choose('minimal');releaseCase();await caseDoneGate;await page.unroute('**/api/cases/case-002');
  await page.waitForTimeout(100);assert.equal((await parse('input-json')).case_id,'minimal');
  assert.match(await page.locator('case-state-viewer').evaluate(el=>el.data.title),/Пример/);checks.push('Delayed older case cannot overwrite current source or input');

  await choose('case-002');let releaseStep;const stepGate=new Promise(resolve=>releaseStep=resolve);let stepSeen,stepDone;
  const stepDoneGate=new Promise(resolve=>stepDone=resolve);
  const stepSeenGate=new Promise(resolve=>stepSeen=resolve);
  await page.route('**/api/cases/case-002/steps/1',async route=>{const response=await route.fetch();stepSeen();await stepGate;await route.fulfill({response});stepDone()});
  await page.selectOption('#step-select','1');await stepSeenGate;await page.selectOption('#step-select','2');await waitReady();releaseStep();await stepDoneGate;await page.unroute('**/api/cases/case-002/steps/1');await page.waitForTimeout(100);
  assert.equal((await parse('input-json')).step_index,2);checks.push('Delayed older step cannot overwrite current evidence');

  let releaseRun;const runGate=new Promise(resolve=>releaseRun=resolve);let runSeen,runDone;const runSeenGate=new Promise(resolve=>runSeen=resolve),runDoneGate=new Promise(resolve=>runDone=resolve);
  await page.route('**/api/runs',async route=>{const response=await route.fetch();runSeen();await runGate;await route.fulfill({response});runDone()});
  await page.click('#analyze');await runSeenGate;await page.selectOption('#step-select','3');await waitReady();releaseRun();await runDoneGate;await page.unroute('**/api/runs');await page.waitForTimeout(100);
  assert.equal(await page.locator('#download-run').isDisabled(),true);assert.match(await read('candidate-json'),/Run the offline/);checks.push('Delayed previous run cannot populate a new selection');

  await page.route('**/api/cases/case-002/steps/4',route=>route.fulfill({status:503,contentType:'application/json',body:'{"error":"unavailable"}'}));
  await page.selectOption('#step-select','4');await page.locator('#error').waitFor({state:'visible'});
  assert.match(await read('error'),/HTTP 503/);assert.equal(await page.locator('#analyze').isDisabled(),true);await page.unroute('**/api/cases/case-002/steps/4');checks.push('HTTP failures are announced and disable analysis');
  await choose('case-002');
  const imports=await page.locator('case-state-viewer').evaluate(viewer=>{
    viewer.goToStep(2);const old=viewer.data;const html=viewer.shadowRoot.innerHTML;
    const bad=structuredClone(old);bad.initial_state.annotations=[{text:'bad',source_event_ids:''}];
    let rejected=false;try{viewer.load(bad)}catch{rejected=true}
    const preserved=JSON.stringify(viewer.data)===JSON.stringify(old)&&viewer.stepIndex===2&&html===viewer.shadowRoot.innerHTML;
    const originalRender=viewer.render;viewer.render=function(){this.shadowRoot.innerHTML='partial';throw new Error('injected render failure')};
    let reported=false;try{viewer.load(old)}catch(error){reported=/previous view restored/.test(error.message)}finally{viewer.render=originalRender}
    const restored=viewer.stepIndex===2&&viewer.shadowRoot.innerHTML===html;
    const unsafe=structuredClone(old);unsafe.title='<img src=x onerror="window.__unsafe=true">';viewer.load(unsafe);
    return {rejected,preserved,reported,restored,unsafeElement:!!viewer.shadowRoot.querySelector('img')};
  });assert.deepEqual(imports,{rejected:true,preserved:true,reported:true,restored:true,unsafeElement:false});
  assert.equal(await page.evaluate(()=>window.__unsafe),undefined);
  await page.locator('case-state-viewer').evaluate(viewer=>viewer.shadowRoot.getElementById('next').click());
  assert.equal(await page.locator('case-state-viewer').evaluate(viewer=>viewer.stepIndex),1);checks.push('Invalid imports/render rollback preserve view; HTML injection escaped; delegated controls survive rollback');

  await page.setViewportSize({width:390,height:844});await choose('case-002-n4',5);await run();
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.screenshot({path:path.join(output,'mobile-results.png'),fullPage:true});
  await page.locator('details.source > summary').click();await page.locator('details.source').scrollIntoViewIfNeeded();
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.screenshot({path:path.join(output,'mobile-source.png'),fullPage:true});checks.push('390px mobile layout has no horizontal overflow, source and results navigable');
  const sourceRequests=[];
  const trackSource=request=>sourceRequests.push(new URL(request.url()).pathname);
  page.on('request',trackSource);
  await page.goto(`${base}/source-viewer`);await page.waitForFunction(()=>document.querySelector('case-state-viewer').data);
  assert.equal(await read('load-error'),'');checks.push('Standalone source viewer loads its default JSON successfully');
  await page.locator('#editor > summary').click();
  const sourceText=await fs.readFile(new URL('../examples/minimal.json',import.meta.url),'utf8');
  await page.locator('#json-input').fill(sourceText);await page.click('#apply-json');
  await page.locator('case-state-viewer').evaluate(viewer=>viewer.goToStep(1));
  await page.locator('#json-input').evaluate(el=>el.value=' '.repeat(5*1024*1024+1)+JSON.stringify(document.querySelector('case-state-viewer').data));
  await page.click('#apply-json');assert.match(await read('load-error'),/5 MiB/);
  assert.equal(await page.locator('case-state-viewer').evaluate(viewer=>viewer.stepIndex),1);
  await page.locator('#file').setInputFiles({name:'too-large.json',mimeType:'application/json',buffer:Buffer.from(' '.repeat(5*1024*1024+1)+sourceText)});
  assert.match(await read('load-error'),/5 МБ|5 MiB/);assert.equal(await page.locator('case-state-viewer').evaluate(viewer=>viewer.stepIndex),1);
  checks.push('Standalone paste and file upload reject oversized raw whitespace and preserve current selection');
  page.off('request',trackSource);
  assert.equal(sourceRequests.some(path=>path.startsWith('/api/')),false);
  checks.push('Standalone source viewer uses no library or model API routes');
  assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
  const receipt={base,output,checks,snapshots:count,errors,external,live_calls:0,operational_effects:0};
  await fs.writeFile(path.join(output,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');console.log(JSON.stringify(receipt,null,2));
} finally {await browser.close()}
