import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,mkdir} from 'node:fs/promises';

const enabled=Boolean(process.env.PROOFKEY_PLAYWRIGHT_MODULE);
const record=()=>({case_id:'long-technical-case-identifier-001',snapshot:{case_id:'long-technical-case-identifier-001',revision:2,snapshot_hash:'a'.repeat(64),links:{order_id:'DL-002',customer_id:'recipient',operator_id:'coordinator'},participants:['recipient','coordinator'],events:[{event_id:'source-1',channel:'chat',sender_id:'recipient',kind:'message',text:'Please change the delivery. <script>window.injected=true</script>',occurred_at:'2026-10-10T12:00:00Z'}]},states:{lifecycle:'in_review',decision:'proposed'},assets:[],decisions:[],reviews:[],actions:[],media_runs:[],model_jobs:[]});
const proposal={decision_id:'proposal-1',revision:2,snapshot_hash:'a'.repeat(64),kind:'operator',action:{type:'reschedule_delivery',slot_start:'2099-01-02T10:00:00Z',slot_end:'2099-01-02T12:00:00Z'},evidence_event_ids:['source-1']};
async function fixture(detail){
  const {chromium}=await import(process.env.PROOFKEY_PLAYWRIGHT_MODULE);
  const browser=await chromium.launch({headless:true,executablePath:process.env.PROOFKEY_CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
  const page=await browser.newPage({viewport:{width:1440,height:1100}}),errors=[],writes=[];
  page.on('pageerror',e=>errors.push(e.message));
  const files=new Map(await Promise.all(['index.html','app.js','session.js','product.js','style.css','coordination.js','coordination-panel.js','coordination.css'].map(async name=>[name,await readFile(new URL('../'+name,import.meta.url),'utf8')])));
  files.set('tokens.css',await readFile(new URL('../../design/right-ontime/prototype/assets/tokens.css',import.meta.url),'utf8'));
  await page.route('**/*',async route=>{
    const req=route.request(),url=new URL(req.url());if(req.method()!=='GET')writes.push(req.method());
    if(url.pathname==='/api/platform/cases')return route.fulfill({json:{cases:[detail]}});
    if(url.pathname.startsWith('/api/platform/cases/'))return route.fulfill({json:{case:detail}});
    if(url.pathname==='/api/platform/capabilities')return route.fulfill({json:{models:{enabled:false,profiles:[]},adapters:[],media:{}}});
    if(/^\/(brand|fonts)\/[A-Za-z0-9_.-]+$/.test(url.pathname))return route.fulfill({body:await readFile(new URL('../../design/right-ontime/prototype/assets'+url.pathname,import.meta.url)),contentType:url.pathname.endsWith('.svg')?'image/svg+xml':'font/ttf'});
    const name=url.pathname==='/'?'index.html':url.pathname.slice(1);
    return route.fulfill({body:files.get(name)||'',contentType:name.endsWith('.js')?'text/javascript':name.endsWith('.html')?'text/html':'text/css'});
  });
  await page.goto('http://127.0.0.1:8099/#case='+detail.case_id);
  await page.locator('#case-detail').waitFor({state:'visible'});
  await page.evaluate(()=>document.fonts.ready);
  return {browser,page,errors,writes};
}

test('Team renders current proposal separately from source context and analysis',{skip:!enabled},async()=>{
  const detail=record();detail.decisions=[proposal];const {browser,page,errors,writes}=await fixture(detail);
  try{
    await page.locator('#summary-proposal').waitFor({state:'visible',timeout:2000});
    assert.match(await page.locator('#summary-proposal').innerText(),/Reschedule delivery/);
    assert.match(await page.locator('#summary-proposal').innerText(),/Awaiting human review/);
    assert.match(await page.locator('#summary-proposal').innerText(),/not sent/i);
    assert.ok((await page.locator('#summary-proposal').boundingBox()).y<(await page.locator('#analysis-card').boundingBox()).y);
    if(process.env.PROOFKEY_TEAM_SCREENSHOTS){await mkdir(process.env.PROOFKEY_TEAM_SCREENSHOTS,{recursive:true});await page.screenshot({path:process.env.PROOFKEY_TEAM_SCREENSHOTS+'/team-current-proposal-desktop.png',fullPage:true});}
    await page.locator('#summary-proposal [data-open-tab="requests"]').click();
    assert.equal(await page.locator('#panel-requests').isVisible(),true);
    assert.equal(await page.evaluate(()=>Boolean(window.injected)),false);
    assert.deepEqual(errors,[]);assert.deepEqual(writes,[]);
  }finally{await browser.close();}
});

test('stale proposal stays historical and Team keeps the reference rail and readable metadata',{skip:!enabled},async()=>{
  const detail=record();detail.decisions=[{...proposal,revision:1}];const {browser,page,errors}=await fixture(detail);
  try{
    assert.equal((await page.locator('.case-rail').boundingBox()).width,290);
    assert.match(await page.locator('#summary-proposal').innerText(),/No current proposal/);
    assert.doesNotMatch(await page.locator('#summary-proposal').innerText(),/2099/);
    const sizes=await page.evaluate(()=>['.task-facts dt','.task-facts dd','.case-control h3'].map(s=>parseFloat(getComputedStyle(document.querySelector(s)).fontSize)));
    assert.ok(sizes[0]>=12 && sizes[1]>=13 && sizes[2]>=15);
    assert.equal(await page.locator('.case-item strong').textContent(),'DL-002');
    assert.match(await page.locator('.case-item').innerText(),/long-technical-case-identifier-001/);
    assert.equal(await page.locator('.case-header #summary-state').count(),1);
    await page.locator('#refresh-list').click();
    await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
    assert.deepEqual(errors,[]);
    if(process.env.PROOFKEY_TEAM_SCREENSHOTS){await mkdir(process.env.PROOFKEY_TEAM_SCREENSHOTS,{recursive:true});await page.screenshot({path:process.env.PROOFKEY_TEAM_SCREENSHOTS+'/team-stale-mobile.png',fullPage:true});}
  }finally{await browser.close();}
});
