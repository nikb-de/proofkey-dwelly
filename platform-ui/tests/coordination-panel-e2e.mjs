// Isolated browser contract: real panel/session, controlled HTTP transport, no provider calls.
import assert from 'node:assert/strict';
import {readFile,mkdtemp} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
const {chromium}=await import('/Users/nbk/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs');
const output=await mkdtemp(path.join(tmpdir(),'proofkey-coordination-team-'));
const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
const terms={slot_start:'2030-06-03T10:00:00+00:00',slot_end:'2030-06-03T12:00:00+00:00',handover:'recipient_only',recipient_present:true,charge:{amount_minor:1250,currency:'GBP'}};
const state={case_id:'test-case',snapshot:{case_id:'test-case',revision:3,snapshot_hash:'a'.repeat(64),links:{customer_id:'c',operator_id:'o'},participants:['c','o','dispatch'],events:[{event_id:'audit-1',channel:'internal',kind:'message',text:'internal'},{event_id:'audit-2',channel:'internal',kind:'message',text:'internal'},{event_id:'e3',kind:'message',channel:'chat',sender_id:'c',recipient_ids:['o'],text:'I accept <script>window.injected=true</script>'}]},coordination:{phase:'awaiting_consent',version:2,revision:2,snapshot_hash:'b'.repeat(64),dispatch_actor_id:'dispatch',original_booking:{booking_id:'original-1',terms},offer:{offer_id:'offer-1',terms_hash:'c'.repeat(64),terms,created_revision:2},consent:null,pending_request:null,operation_receipts:[],audit_history:[]},model_jobs:[]};
let writes=[];
try{
  const page=await browser.newPage({viewport:{width:1100,height:950}});page.setDefaultTimeout(6000);
  await page.route('http://coordination.test/**',async route=>{
    const url=new URL(route.request().url());
    if(url.pathname==='/')return route.fulfill({contentType:'text/html',body:`<link rel="stylesheet" href="/style.css"><link rel="stylesheet" href="/coordination.css"><main><div id="panel"></div></main><script type="module">import {PlatformSession,createAPI} from '/session.js';import {createCoordinationPanel} from '/coordination-panel.js'; window.session=new PlatformSession(createAPI(),()=>panel.render()); const panel=createCoordinationPanel({root:document.querySelector('#panel'),session});window.panel=panel; await session.select('test-case');</script>`});
    if(url.pathname.startsWith('/api/')){
      if(url.pathname.endsWith('/capabilities'))return route.fulfill({json:{models:{enabled:false,profiles:[]},adapters:[],media:{}}});
      if(url.pathname==='/api/platform/cases' && route.request().method()==='GET')return route.fulfill({json:{cases:[{...state,states:{lifecycle:'awaiting_approval'}}]}});
      if(route.request().method()==='POST'){writes.push(JSON.parse(route.request().postData()));return route.fulfill({status:409,contentType:'application/json',body:JSON.stringify({error:{code:'consent_stale'}})});}
      return route.fulfill({contentType:'application/json',body:JSON.stringify({case:state})});
    }
    try{const file=url.pathname==='/team'?'/index.html':url.pathname;return route.fulfill({contentType:file.endsWith('.html')?'text/html':file.endsWith('.css')?'text/css':'text/javascript',body:await readFile(new URL(`..${file}`,import.meta.url),'utf8')});}catch{return route.fulfill({status:404,body:'missing'});}
  });
  await page.goto('http://coordination.test/');
  await page.locator('#coordination-command').waitFor();
  assert.deepEqual(writes,[],'render/load must not write');
  assert.match(await page.locator('#panel').innerText(),/1250.*GBP/);
  assert.match(await page.locator('#panel').innerText(),/Attendance required/);
  assert.match(await page.locator('#panel').innerText(),/stale/i);
  await page.selectOption('#coordination-command','record_consent');
  await page.locator('[name="coordination-evidence"][value="e3"]').check();
  assert.equal(await page.evaluate(()=>Boolean(window.injected)),false);
  assert.equal(await page.locator('#coordination-submit').isDisabled(),true);
  await page.locator('#coordination-reviewed').check();
  await page.locator('#coordination-submit').click();
  await page.locator('#coordination-status').filter({hasText:/consent_stale/}).waitFor();
  assert.equal(writes.length,1);assert.equal(writes[0].offer_id,'offer-1');assert.deepEqual(writes[0].evidence_event_ids,['e3']);assert.equal(writes[0].expected_revision,3);
  assert.equal(await page.locator('[name="coordination-evidence"][value="e3"]').isChecked(),true);
  await page.evaluate(()=>{session.detail.snapshot.revision+=1;panel.render();});
  assert.equal(await page.locator('#coordination-reviewed').isChecked(),false,'new source revision requires renewed review');
  assert.equal(await page.locator('#coordination-submit').isDisabled(),true);
  assert.equal(await page.locator('[name="coordination-evidence"][value="e3"]').isChecked(),true,'source selection remains available for review');
  await page.screenshot({path:path.join(output,'team-desktop.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:path.join(output,'team-mobile.png'),fullPage:true});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  Object.assign(state,{states:{lifecycle:'awaiting_approval',evidence:'text_available',analysis:'not_started',decision:'none',action:'none'},decisions:[],reviews:[],actions:[],assets:[],media_runs:[]});
  const audit={audit_id:'audit-123',command:'record_offer',version:2,source_revision:1,mode:'local_sandbox',external_effects:0,attestation_scope:'local_operator_attestation_not_customer_or_carrier_authentication'};
  state.coordination.audit_history=[audit];
  state.snapshot.events[1]={event_id:'coord-audit-123',kind:'message',channel:'internal',sender_id:'o',recipient_ids:['c','dispatch'],occurred_at:'2030-06-01T12:00:00Z',text:JSON.stringify({...audit,phase:'awaiting_consent'})};
  state.snapshot.events[2].text=JSON.stringify({qualification:'scripted_local_attestation',source_text:'I accept these terms'});
  await page.goto('http://coordination.test/team#case=test-case');
  await page.locator('#coordination-panel #coordination-command').waitFor();
  assert.match(await page.locator('#case-title').innerText(),/coordination/i);
  assert.equal(await page.locator('#summary-proposal').isVisible(),false);
  assert.match(await page.locator('#summary-next-step').innerText(),/sourced customer consent/i);
  assert.doesNotMatch(await page.locator('#summary-next-step').innerText(),/qualification|attestation_scope|\{/);
  const auditEntry=page.locator('#case-history [data-event-id="coord-audit-123"]');
  assert.match(await auditEntry.innerText(),/Record offer/);
  assert.match(await auditEntry.innerText(),/workflow version 2.*source revision 1/i);
  assert.doesNotMatch(await auditEntry.innerText(),/attestation_scope|\{/);
  await auditEntry.getByRole('button',{name:'Source event coord-audit-123'}).click();
  assert.equal(await page.locator('#panel-sources').isVisible(),true);
  assert.match(await page.locator('#evidence-list [data-event-id="coord-audit-123"]').innerText(),/attestation_scope/,'original raw audit is preserved in Sources');
  assert.equal(writes.length,1,'full app render must not write');
  state.coordination=null;
  await page.reload();await page.locator('#case-detail').waitFor({state:'visible'});
  assert.match(await page.locator('#summary-next-step').innerText(),/scripted_local_attestation/,'legacy source summary remains unchanged');
  assert.match(await page.locator('#case-history').innerText(),/attestation_scope/,'unbound internal JSON remains source text, not a trusted workflow audit');
  console.log(JSON.stringify({status:'passed',output,writes:writes.length,providerCalls:0}));
}finally{await browser.close();}
