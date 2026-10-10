import test from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root=path.resolve(fileURLToPath(new URL('../',import.meta.url)));
const assets=path.resolve(root,'../design/right-ontime/prototype/assets');
const terms=(start,end,handover,present)=>({slot_start:start,slot_end:end,handover,recipient_present:present,charge:{amount_minor:3000,currency:'GBP'}});
const fixture={schema_version:'proofkey-showcase-v1',mode:'llm',case_id:'case-demo',order_id:'DL-001',customer_name:'Vessa Lorne',item:'Desk lamp',source:{sha256:'a'.repeat(64),path:'recorded-case.json',qualification:'Recorded source'},original_terms:terms('2026-02-03T09:00:00Z','2026-02-03T12:00:00Z','concierge',false),requested_terms:terms('2026-02-04T10:00:00Z','2026-02-04T13:00:00Z','concierge',false),offered_terms:terms('2026-02-05T14:00:00Z','2026-02-05T17:00:00Z','recipient_only',true),scenes:['request','review','change','consent','confirmed'].map((id,i)=>({id,role:i===1?'operator':'customer',phase:id,title:['A delivery that fits your day','A clear next step','The offer has changed','Your choice, with every detail','Booking confirmed'][i],eyebrow:'Recorded journey',description:'The recorded delivery journey.',messages:[{event_id:`event-${i}`,sender:'Vessa Lorne',role:'customer',text:i===0?'Please leave my desk lamp with the concierge.':'Recorded reply',time:'10:24'}],model:i===1?{run_id:'run-1',model:'recorded-model',action:'ask_dispatch',description:'Ask dispatch to confirm available windows.',evidence_event_ids:['event-0'],advisory_only:true}:null,coordination:{phase:id},qualification:'Recorded replay',source_event_ids:[`event-${i}`]})),receipt:{booking_confirmed:true,external_effects:0,physical_delivery:'not_confirmed',request_id:'booking-123'}};

async function withBrowser(run){
 const {chromium}=await import(process.env.PROOFKEY_PLAYWRIGHT_MODULE||'/Users/nbk/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs');
 let data=structuredClone(fixture);const writes=[];
 const server=createServer(async(req,res)=>{try{res.setHeader('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'");const pathname=new URL(req.url,'http://localhost').pathname;if(req.method!=='GET')writes.push(req.method);if(pathname.startsWith('/showcase-data-')){res.setHeader('Content-Type','application/json');res.end(JSON.stringify({...data,mode:pathname.includes('synthetic')?'synthetic':'llm'}));return;}const base=/^\/(fonts|brand)\//.test(pathname)?assets:root;const filename=path.resolve(base,`.${pathname}`);if(!filename.startsWith(base+path.sep))throw Error('Path');const body=await readFile(filename);res.setHeader('Content-Type',filename.endsWith('.js')?'application/javascript':filename.endsWith('.css')?'text/css':filename.endsWith('.svg')?'image/svg+xml':filename.endsWith('.ttf')?'font/ttf':'text/html');res.end(body);}catch{res.statusCode=404;res.end('Not found');}});
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 try{await run({browser,url:`http://127.0.0.1:${server.address().port}/showcase.html`,writes,setData:value=>{data=value;}});}finally{await browser.close();await new Promise(resolve=>server.close(resolve));}
}

// Catches a replay that loses the changed terms, writes acceptance, or confirms physical delivery.
test('mobile replay preserves the changed offer and replays acceptance without external writes',async()=>withBrowser(async({browser,url,writes})=>{
 const page=await browser.newPage({viewport:{width:390,height:780}});const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.goto(`${url}?mode=llm&scene=1`);
 await page.locator('#scene-title').waitFor({timeout:3000});
 assert.deepEqual(errors,[]);
 assert.equal(await page.locator('#scene-title').count(),1,await page.locator('body').innerText());
 assert.equal(await page.locator('#scene-title').textContent({timeout:1200}),'A delivery that fits your day');
 assert.match(await page.locator('body').innerText(),/Demo · Replay/);
 assert.match(await page.locator('body').innerText(),/Please leave my desk lamp with the concierge/);
 await page.locator('#next-scene').click();
 assert.match(await page.locator('#replay-stage').innerText(),/Recorded model response/i);
 assert.match(await page.locator('#replay-stage').innerText(),/Ask dispatch to confirm available windows/);
 await page.locator('#next-scene').click();
 const comparison=await page.locator('#replay-stage').innerText();
 assert.match(comparison,/4 February/);assert.match(comparison,/5 February/);
 assert.match(comparison,/Concierge/);assert.match(comparison,/Recipient must be present/);assert.match(comparison,/£30\.00/);
 await page.locator('#next-scene').click();await page.getByRole('button',{name:'Replay customer acceptance'}).click();
 assert.equal(await page.locator('#scene-title').textContent(),'Booking confirmed');
 assert.match(await page.locator('#replay-stage').innerText(),/Sandbox receipt · physical delivery not confirmed/);
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 assert.deepEqual(writes,[]);assert.deepEqual(errors,[]);
}));

// Catches shortened scene timing, accidental looping, and a synthetic run presented as a model call.
test('autoplay holds each of the five scenes for eight seconds and stops after forty seconds',async()=>withBrowser(async({browser,url})=>{
 const page=await browser.newPage({viewport:{width:1440,height:900}});await page.clock.install({time:new Date('2030-01-01T00:00:00Z')});await page.goto(`${url}?mode=synthetic&scene=1`);await page.locator('#scene-title').waitFor();await page.clock.pauseAt(new Date('2030-01-01T00:01:00Z'));
 assert.match(await page.locator('body').innerText(),/Scripted reference · no model call/);
 await page.locator('#play-replay').click();await page.clock.runFor(7999);assert.equal(await page.locator('#replay-stage').getAttribute('data-scene'),'1');
 await page.clock.runFor(1);assert.equal(await page.locator('#replay-stage').getAttribute('data-scene'),'2');
 await page.clock.runFor(24000);assert.equal(await page.locator('#replay-stage').getAttribute('data-scene'),'5');
 await page.clock.runFor(8000);assert.match(await page.locator('#play-replay').innerText(),/Play replay/);
 assert.equal(await page.locator('#replay-stage').getAttribute('data-scene'),'5');
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
}));

// Catches regression to a narrow desktop card, inaccessible app navigation, and content clipped in the recording.
test('capture presents a rounded phone with safe areas, usable app tabs, and five fully fitted screens',async()=>withBrowser(async({browser,url,setData})=>{
 setData(JSON.parse(await readFile(path.join(root,'showcase-data-llm.json'),'utf8')));
 const page=await browser.newPage({viewport:{width:450,height:800}});await page.goto(`${url}?capture=1`);await page.locator('#scene-title').waitFor();await page.evaluate(()=>document.fonts.ready);
 const device=await page.locator('.device-frame').boundingBox();
 assert.ok(device.width>=340&&device.width<=350,JSON.stringify(device));assert.ok(device.height>=740&&device.height<=755,JSON.stringify(device));
 assert.ok(device.x>=0&&device.y>=0&&device.x+device.width<=450&&device.y+device.height<=800);
 assert.equal(await page.locator('.camera-island').isVisible(),true);assert.equal(await page.locator('.status-bar').isVisible(),true);
 assert.equal(await page.locator('.app-header').innerText().then(text=>text.includes('Delivery help')),true);
 assert.equal(await page.locator('.playback').isVisible(),false);
 const shape=await page.locator('.phone-screen').evaluate(node=>({radius:parseFloat(getComputedStyle(node).borderRadius),overflow:getComputedStyle(node).overflow}));
 assert.ok(shape.radius>=32);assert.equal(shape.overflow,'hidden');
 for(let index=0;index<5;index++){
  await page.evaluate(index=>window.proofkeyReplay.goTo(index),index);
  assert.equal(await page.locator('#replay-stage').getAttribute('data-scene'),String(index+1));
  const fit=await page.locator('.screen-body').evaluate(node=>({height:node.clientHeight,scroll:node.scrollHeight,width:node.clientWidth,scrollWidth:node.scrollWidth}));
  assert.ok(fit.scroll<=fit.height+1,`Scene ${index+1} overflows vertically: ${JSON.stringify(fit)}`);
  assert.ok(fit.scrollWidth<=fit.width+1,`Scene ${index+1} overflows horizontally: ${JSON.stringify(fit)}`);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  assert.equal(await page.locator('.phone-screen').getByText(/physical delivery not confirmed/i).count(),index===4?1:0);
  for(const button of await page.locator('.phone-screen button').all()){
   const box=await button.boundingBox();if(!box)continue;
   assert.ok(box.width>=44&&box.height>=44,`Small tap target: ${await button.getAttribute('aria-label')} ${JSON.stringify(box)}`);
  }
 }
 await page.getByRole('button',{name:'Messages',exact:true}).click();assert.equal(await page.locator('#replay-stage').getAttribute('data-scene'),'1');
 await page.getByRole('button',{name:'Delivery',exact:true}).click();assert.equal(await page.locator('#replay-stage').getAttribute('data-scene'),'3');
 await page.getByRole('button',{name:'Activity',exact:true}).click();assert.equal(await page.locator('#replay-stage').getAttribute('data-scene'),'5');
 await page.setViewportSize({width:360,height:780});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
}));

// Catches a presentation that leaks verification UI, rewrites the agreement, or sends acceptance.
test('presentation keeps both journeys clean, complete, fitted and read-only through acceptance',async()=>withBrowser(async({browser,url,writes,setData})=>{
 const technicalCopy=/\bdemo\b|\bsandbox\b|\breplay\b|\brecorded\b|\bprovenance\b|SHA-256|advisory only|no new request|physical delivery|source details|\bLLM\b|\bsynthetic\b/i;
 const modes=[
  {name:'llm',card:'Delivery assistant',advice:'Forward the requested 2026-10-13 18:00–20:00 UTC slot and concierge handover preference for DL-001, asking dispatch to confirm availability and booking terms.'},
  {name:'synthetic',card:'Delivery plan',advice:'Vessa Lorne asks for 2026-10-13, 18:00–20:00 UTC, with concierge handover if she is out. Which terms can you book for DL-001?'},
 ];
 for(const mode of modes){
  const data=JSON.parse(await readFile(path.join(root,`showcase-data-${mode.name}.json`),'utf8'));setData(data);
  for(const capture of [false,true]){
   const page=await browser.newPage({viewport:{width:450,height:800}});const errors=[],nonGets=[];
   page.on('pageerror',error=>errors.push(error.message));page.on('request',request=>{if(request.method()!=='GET')nonGets.push(request.method());});
   await page.goto(`${url}?presentation=1&mode=${mode.name}${capture?'&capture=1':''}`);await page.locator('#scene-title').waitFor();await page.evaluate(()=>document.fonts.ready);
   for(let index=0;index<5;index++){
    assert.equal(await page.locator('#replay-stage').getAttribute('data-scene'),String(index+1));
    const text=await page.locator('body').innerText();
    assert.doesNotMatch(text,technicalCopy,`${mode.name} scene ${index+1}`);
    for(const rawId of [data.case_id,data.source.path,data.source.sha256,data.scenes[index].model?.run_id,data.receipt.request_id].filter(Boolean))assert.ok(!text.includes(rawId),`Visible source identifier: ${rawId}`);
    assert.equal(await page.getByRole('button',{name:'Open recording details'}).count(),0);
    assert.equal(await page.locator('#evidence-details').isVisible(),false);
    assert.equal(await page.locator('.replay-tools').isVisible(),false);
    const fit=await page.locator('.screen-body').evaluate(node=>({height:node.clientHeight,scroll:node.scrollHeight,width:node.clientWidth,scrollWidth:node.scrollWidth}));
    assert.ok(fit.scroll<=fit.height+1,`${mode.name} scene ${index+1} overflows: ${JSON.stringify(fit)}`);
    assert.ok(fit.scrollWidth<=fit.width+1,`${mode.name} scene ${index+1} overflows horizontally`);
    for(const button of await page.locator('.phone-screen button').all()){
     const box=await button.boundingBox();if(box)assert.ok(box.width>=44&&box.height>=44,`Small tap target: ${JSON.stringify(box)}`);
    }
    if(index===0)assert.equal(await page.locator('.person-role').innerText(),'Customer');
    if(index===1){assert.equal(await page.locator('.model-card .card-label').innerText(),mode.card.toUpperCase());assert.equal(await page.locator('.model-card p').innerText(),mode.advice);}
    if(index===2){assert.match(text,/13 October/);assert.match(text,/18:00–20:00 UTC/);assert.match(text,/Concierge/);assert.match(text,/Recipient not required/);assert.match(text,/14 October/);assert.match(text,/10:00–13:00 UTC/);assert.match(text,/Recipient only/);assert.match(text,/Recipient must be present/);assert.equal(await page.locator('.terms-column:not(.is-offered) [data-field="charge"] .term-value').innerText(),'Not specified');assert.equal(await page.locator('.is-offered [data-field="charge"] .term-value').innerText(),'No extra charge');}
    if(index===3){assert.match(text,/14 October 2026/);assert.match(text,/10:00–13:00 UTC/);assert.match(text,/Recipient only/);assert.match(text,/Recipient must be present/);assert.match(text,/No extra charge/);assert.equal(await page.locator('.primary-action').innerText(),'Accept these terms');}
    if(index===4){assert.equal(await page.locator('#scene-title').innerText(),'Booking confirmed');assert.doesNotMatch(text,/\bdelivered\b/i);assert.equal(await page.locator('.primary-action').innerText(),'Back to messages');}
    await page.locator('.primary-action').click();
   }
   assert.equal(await page.locator('#replay-stage').getAttribute('data-scene'),'1');
   await page.setViewportSize({width:1440,height:900});
   assert.equal(await page.locator('.story-rail').isVisible(),false);
   assert.equal(await page.locator('.replay-tools').isVisible(),false);
   await page.locator('#evidence-details').evaluate(node=>{node.open=true;});
   assert.equal(await page.locator('#evidence-details').isVisible(),false);
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
   assert.deepEqual(nonGets,[]);assert.deepEqual(errors,[]);await page.close();
  }
 }
 assert.deepEqual(writes,[]);
}));

// Catches data being interpolated as executable markup, and error responses shown as a success.
test('untrusted messages render as text and invalid recordings show a recoverable error',async()=>withBrowser(async({browser,url,setData})=>{
 const malicious=structuredClone(fixture);malicious.scenes[0].messages[0].text='<img src=x onerror="window.wasInjected=true">';setData(malicious);
 const page=await browser.newPage();await page.goto(`${url}?scene=1`);await page.locator('#scene-title').waitFor();assert.match(await page.locator('#replay-stage').innerText(),/<img src=x/);assert.equal(await page.evaluate(()=>window.wasInjected),undefined);
 setData({schema_version:'wrong'});await page.reload();await page.getByRole('heading',{name:'This replay is unavailable'}).waitFor();assert.equal(await page.locator('#play-replay').isDisabled(),true);
}));
