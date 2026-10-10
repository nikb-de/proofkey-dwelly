// Actual browser playback capture. No case writes and no provider requests.
import {mkdir, readFile, writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';
import assert from 'node:assert/strict';
import {captureContract as contract,validateCapture} from './showcase-capture-contract.mjs';

const {chromium} = await import(process.env.PROOFKEY_PLAYWRIGHT_MODULE || '/Users/nbk/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs');
const origin = process.env.PROOFKEY_SHOWCASE_URL || 'http://127.0.0.1:8111';
const cleanPresentation=process.env.PROOFKEY_PRESENTATION==='1';
const viewUrl=(mode,capture=false,scene)=>`${origin}/showcase.html?mode=${mode}${capture?'&capture=1':''}${cleanPresentation?'&presentation=1':''}${scene?`&scene=${scene}`:''}`;
const acceptanceLabel=cleanPresentation?'Accept these terms':'Replay customer acceptance';
const assertCleanScreen=async page=>{
  if(cleanPresentation)assert.doesNotMatch(await page.locator('.phone-screen').innerText(),/\b(demo|sandbox|replay|recorded|provenance|sha-256|advisory)\b|model call|no new request|physical delivery not confirmed/i,'Technical framing leaked into the presentation');
};
const output = path.resolve(process.argv[2] || `docs/demos/2026-10-10-case-001-terms/showcase-${Date.now()}`);
await mkdir(output, {recursive:true});
const browser = await chromium.launch({headless:true, executablePath:process.env.PROOFKEY_CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
const receipts = [];
const assetFiles=['showcase.html','showcase.js','showcase.css','showcase-data-llm.json','showcase-data-synthetic.json'];
const assetHashes=async()=>Object.fromEntries(await Promise.all(assetFiles.map(async file=>[file,createHash('sha256').update(await readFile(path.resolve('platform-ui',file))).digest('hex')])));
const hashes=await assetHashes();
try {
  for (const mode of ['synthetic','llm']) {
    const context = await browser.newContext({viewport:contract.viewport,deviceScaleFactor:2});
    const page = await context.newPage(), errors=[],writes=[];
    page.on('pageerror',error=>errors.push(error.message));
    page.on('request',request=>{if(request.method()!=='GET')writes.push({url:request.url(),method:request.method()});});
    await page.goto(viewUrl(mode,true),{waitUntil:'networkidle'});
    await page.locator('#replay-stage[data-scene="1"] #scene-title').waitFor();
    await page.evaluate(()=>document.fonts.ready);
    const scenes=[];
    for(const [index,id] of contract.sceneIds.entries()) {
      if(index===4)await page.getByRole('button',{name:acceptanceLabel,exact:true}).click();
      else if(index)await page.evaluate(index=>window.proofkeyReplay.goTo(index),index);
      await page.locator(`#replay-stage[data-scene="${index+1}"]`).waitFor();
      await page.waitForTimeout(500);
      await assertCleanScreen(page);
      const geometry=await page.evaluate(()=>({width:innerWidth,height:innerHeight,scrollWidth:document.documentElement.scrollWidth,scrollHeight:document.documentElement.scrollHeight,stage:document.querySelector('#replay-stage').getBoundingClientRect().toJSON(),device:document.querySelector('.device-frame').getBoundingClientRect().toJSON()}));
      assert(geometry.scrollWidth<=geometry.width,`${mode}/${id}: horizontal overflow`);
      assert(geometry.device.top>=0&&geometry.device.bottom<=geometry.height,`${mode}/${id}: phone frame clipped`);
      const screenshot=path.join(output,`${mode}-${index+1}-${id}-mobile.png`);
      await page.screenshot({path:screenshot,fullPage:true});
      scenes.push({id,geometry,screenshot});
    }
    await page.setViewportSize({width:1440,height:1000});
    await page.goto(viewUrl(mode,false,3),{waitUntil:'networkidle'});
    await page.screenshot({path:path.join(output,`${mode}-desktop.png`),fullPage:true});
    assert.deepEqual(errors,[],`${mode}: browser errors`);assert.deepEqual(writes,[],`${mode}: playback must not mutate`);
    receipts.push({mode,scenes,errors,writes});
    await context.close();
  }

  const capture = async mode => {
    const dir=path.join(output,mode);await mkdir(dir,{recursive:true});
    // Chromium's video recorder ignores DPR and otherwise pads the larger
    // canvas. Render the logical mobile layout at 2x inside the real viewport.
    const context=await browser.newContext({viewport:contract.videoSize,deviceScaleFactor:1,recordVideo:{dir,size:contract.videoSize}});
    const page=await context.newPage();const started=performance.now();const errors=[],writes=[];
    page.on('pageerror',error=>errors.push(error.message));
    page.on('request',request=>{if(request.method()!=='GET')writes.push(request.method());});
    await page.goto(viewUrl(mode,true),{waitUntil:'networkidle'});
    await page.evaluate(({width,height})=>{
      document.documentElement.style.zoom='2';
      document.body.style.width=`${width}px`;
      document.body.style.height=`${height}px`;
      const layout=document.querySelector('.showcase-layout');
      layout.style.height=`${height}px`;
      layout.style.minHeight=`${height}px`;
    },contract.viewport);
    await page.locator('#replay-stage[data-scene="1"] #scene-title').waitFor();await page.evaluate(()=>document.fonts.ready);await page.waitForTimeout(700);
    const captureStart=(performance.now()-started)/1000;const marks=[];
    for (const [index,id] of contract.sceneIds.entries()) {
      if(index===4)await page.getByRole('button',{name:acceptanceLabel,exact:true}).click();
      else if(index)await page.evaluate(index=>window.proofkeyReplay.goTo(index),index);
      await page.locator(`#replay-stage[data-scene="${index+1}"]`).waitFor();
      await assertCleanScreen(page);
      marks.push({scene:id,at:(performance.now()-started)/1000});
      const target=started+(captureStart+(index+1)*contract.sceneSeconds)*1000;
      await page.waitForTimeout(Math.max(0,target-performance.now()));
    }
    const video=page.video();await context.close();const videoPath=await video.path();
    assert.deepEqual(errors,[]);assert.deepEqual(writes,[]);
    const record={mode,presentation:cleanPresentation,raw_video:videoPath,capture_start_seconds:captureStart,duration_seconds:contract.durationSeconds,viewport:contract.viewport,browser_viewport:contract.videoSize,video_size:contract.videoSize,device_scale_factor:1,display_scale:2,marks,errors,writes,qualification:'Recorded browser playback of existing source and run receipts. No fresh provider calls or case mutations.'};
    validateCapture(record);
    return record;
  };
  receipts.push(...await Promise.all(['synthetic','llm'].map(capture)));
  assert.deepEqual(await assetHashes(),hashes,'Presentation assets changed while recording');
  await writeFile(path.join(output,'capture.json'),JSON.stringify({origin,presentation:cleanPresentation,assets:hashes,receipts},null,2));
  console.log(JSON.stringify({output,receipts},null,2));
} finally {await browser.close();}
