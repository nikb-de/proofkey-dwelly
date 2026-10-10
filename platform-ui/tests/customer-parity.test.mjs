import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdir} from 'node:fs/promises';

const enabled=Boolean(process.env.PROOFKEY_CUSTOMER_BROWSER);
const base=process.env.PROOFKEY_CUSTOMER_URL || 'http://127.0.0.1:8105';
const fixture=()=>({case_id:'internal-case-opaque',snapshot:{case_id:'internal-case-opaque',revision:1,snapshot_hash:'a'.repeat(64),links:{order_id:'DL-002'},events:[{event_id:'source-used',kind:'message',text:'Move the delivery, please.'},{event_id:'source-unrelated',kind:'message',text:'Unrelated source.'}]},decisions:[],reviews:[],actions:[]});
const proposal=()=>({case_id:'internal-case-opaque',decision_id:'proposal-1',revision:1,snapshot_hash:'a'.repeat(64),action:{type:'reschedule_delivery',slot_start:'2099-01-02T10:00:00Z',slot_end:'2099-01-02T12:00:00Z',address_change:false},evidence_event_ids:['source-used']});
async function browser(){const {chromium}=await import(process.env.PROOFKEY_PLAYWRIGHT_MODULE || '/Users/nbk/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs');return chromium.launch({headless:true,channel:process.env.PROOFKEY_BROWSER_CHANNEL || 'chrome'});}

test('customer restores original compact composition and safe no-options actions',{skip:!enabled},async()=>{
  const chrome=await browser();
  try{
    const page=await chrome.newPage({viewport:{width:1280,height:900}}),writes=[];
    await page.route('**/api/platform/cases/**',route=>{if(route.request().method()!=='GET')writes.push(route.request().url());return route.fulfill({contentType:'application/json',body:JSON.stringify({case:fixture()})});});
    await page.goto(`${base}/customer.html?case=internal-case-opaque`);
    await page.locator('.case-strip').waitFor();
    const layout=await page.evaluate(()=>({shell:document.querySelector('.customer-shell').getBoundingClientRect().width,heading:getComputedStyle(document.querySelector('h1')).fontSize,cards:document.querySelectorAll('main .card').length,inCardSteps:document.querySelectorAll('.card .steps span').length,header:document.querySelector('.customer-header').innerText}));
    assert.equal(layout.shell,640,'Original customer shell is 640px');
    assert.equal(layout.heading,'28px');assert.equal(layout.cards,1);assert.equal(layout.inCardSteps,2);assert.match(layout.header,/Order DL-002/);
    assert.equal(await page.locator('input[type="datetime-local"],input[name="source-event"]').count(),0);
    assert.doesNotMatch(await page.locator('main').innerText(),/internal-case-opaque|source-unrelated|source-used/);
    assert.match(await page.locator('.card').innerText(),/No suitable windows yet/);
    const output=process.env.PROOFKEY_CUSTOMER_SCREENSHOTS;
    if(output){await mkdir(output,{recursive:true});await page.screenshot({path:`${output}/customer-empty-desktop.png`,fullPage:true});}
    await page.setViewportSize({width:390,height:844});await page.reload();await page.locator('.case-strip').waitFor();await page.evaluate(()=>document.fonts.ready);
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
    if(output)await page.screenshot({path:`${output}/customer-empty-mobile.png`,fullPage:true});
    await page.getByRole('button',{name:'Check status',exact:true}).click();
    await page.locator('#customer-status[data-status="none"]').waitFor();
    await page.getByRole('button',{name:'Stop new actions',exact:true}).click();
    assert.match(await page.locator('[role="status"]').innerText(),/operator|Team/i);assert.equal(writes.length,0);
  }finally{await chrome.close();}
});

test('customer reviews the current offer with its own evidence and preserves POST contract',{skip:!enabled},async()=>{
  const chrome=await browser();
  try{
    const page=await chrome.newPage({viewport:{width:1280,height:1000}}),record=fixture(),posts=[];
    record.decisions=[proposal()];
    await page.route('**/api/platform/cases/**',async route=>{
      if(route.request().method()==='POST'){
        const body=route.request().postDataJSON();posts.push({body,url:route.request().url(),key:route.request().headers()['idempotency-key']});
        record.decisions.push({...proposal(),decision_id:'saved-preference',action:body.action,evidence_event_ids:body.evidence_event_ids});
      }
      await route.fulfill({contentType:'application/json',body:JSON.stringify({case:record})});
    });
    await page.goto(`${base}/customer.html?case=internal-case-opaque`);
    await page.locator('input[name="window-choice"][value="proposal-1"]').check();
    await page.locator('#review-preference').click();
    await page.locator('#submit-preference').waitFor();
    assert.doesNotMatch(await page.locator('main').innerText(),/source-used|source-unrelated|Supporting sources/);
    assert.match(await page.locator('main').innerText(),/Not confirmed|unconfirmed/);
    const output=process.env.PROOFKEY_CUSTOMER_SCREENSHOTS;
    if(output){await mkdir(output,{recursive:true});await page.screenshot({path:`${output}/customer-offer-review-desktop.png`,fullPage:true});}
    await page.locator('#submit-preference').click();
    await page.locator('#customer-status[data-status="proposed"]').waitFor();
    assert.equal(posts.length,1);assert.deepEqual(posts[0].body.evidence_event_ids,['source-used']);assert.equal(posts[0].body.expected_revision,1);assert.equal(posts[0].body.snapshot_hash,'a'.repeat(64));assert.ok(posts[0].key);assert.match(posts[0].url,/\/cases\/internal-case-opaque\/decisions$/);
    assert.equal(posts[0].body.action.slot_start,'2099-01-02T10:00:00.000Z');assert.equal(posts[0].body.action.slot_end,'2099-01-02T12:00:00.000Z');
    await page.setViewportSize({width:390,height:844});await page.reload();await page.getByRole('button',{name:'View current recorded status'}).click();await page.locator('#customer-status').waitFor();await page.evaluate(()=>document.fonts.ready);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
    if(output)await page.screenshot({path:`${output}/customer-offer-status-mobile.png`,fullPage:true});
  }finally{await chrome.close();}
});

for(const change of ['new-snapshot','superseding-offer'])test(`customer must reselect a current offer after ${change}`,{skip:!enabled},async()=>{
  const chrome=await browser();
  try{
    const page=await chrome.newPage(),record=fixture(),posts=[];
    record.decisions=[proposal()];
    await page.route('**/api/platform/cases/**',async route=>{
      if(route.request().method()==='POST')posts.push(route.request().postDataJSON());
      await route.fulfill({contentType:'application/json',body:JSON.stringify({case:record})});
    });
    await page.goto(`${base}/customer.html?case=internal-case-opaque`);
    await page.locator('input[name="window-choice"]').check();await page.locator('#review-preference').click();
    await page.locator('#submit-preference').waitFor();
    if(change==='new-snapshot'){record.snapshot.revision=2;record.snapshot.snapshot_hash='b'.repeat(64);}
    else record.decisions.push({...proposal(),decision_id:'proposal-2',action:{...proposal().action,slot_start:'2099-01-03T14:00:00Z',slot_end:'2099-01-03T16:00:00Z'}});
    await page.locator('#submit-preference').click();await page.locator('[role="alert"]').waitFor({timeout:5000});
    assert.equal(posts.length,0,'Stale or superseded offer cannot be posted');
    await page.getByRole('button',{name:/Review (latest snapshot|current options)/}).click();
    assert.equal(await page.locator('#submit-preference').count(),0,'Recovery cannot rebind the retained old window');
    if(change==='new-snapshot')assert.match(await page.locator('.card').innerText(),/No suitable windows yet/);
    else{
      assert.equal(await page.locator('input[name="window-choice"]:checked').count(),0,'Superseding offer requires deliberate reselection');
      assert.equal(await page.locator('#review-preference').isDisabled(),true);
      await page.locator('input[name="window-choice"][value="proposal-2"]').check();await page.locator('#review-preference').click();
      assert.match(await page.locator('.card').innerText(),/3 Jan 2099/);
    }
    assert.equal(posts.length,0);
  }finally{await chrome.close();}
});
