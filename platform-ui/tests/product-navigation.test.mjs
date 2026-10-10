import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

const browserOptions={skip:!process.env.PROOFKEY_PLAYWRIGHT_MODULE,timeout:30000};
const deferred=()=>{let resolve;const promise=new Promise(done=>{resolve=done;});return {promise,resolve};};
const detail=id=>({case_id:id,snapshot:{case_id:id,revision:0,snapshot_hash:'a'.repeat(64),links:{order_id:'order-1',customer_id:'customer-1',operator_id:'operator-1'},participants:['customer-1','operator-1'],events:[]},states:{lifecycle:'new'},assets:[],decisions:[],reviews:[],actions:[],media_runs:[],model_jobs:[]});

async function fixture(onSecondRead=route=>route.fulfill({json:{case:detail('second')}})) {
  const {chromium}=await import(process.env.PROOFKEY_PLAYWRIGHT_MODULE);
  const browser=await chromium.launch({headless:true,...(process.env.PROOFKEY_CHROME_PATH?{executablePath:process.env.PROOFKEY_CHROME_PATH}:{})});
  try {
  const page=await browser.newPage(),errors=[],writes=[];
  page.setDefaultTimeout(4000);page.on('pageerror',error=>errors.push(error.message));
  const files=new Map(await Promise.all(['index.html','app.js','session.js','product.js'].map(async name=>[name,await readFile(new URL('../'+name,import.meta.url),'utf8')])));
  await page.route('**/*',async route=>{
    const request=route.request(),url=new URL(request.url());
    if(request.method()!=='GET')writes.push(request.method()+' '+url.pathname);
    if(url.pathname==='/api/platform/cases/second')return onSecondRead(route);
    if(url.pathname==='/api/platform/cases/first')return route.fulfill({json:{case:detail('first')}});
    if(url.pathname==='/api/platform/cases')return route.fulfill({json:{cases:[{case_id:'first'},{case_id:'second'}]}});
    if(url.pathname==='/api/platform/capabilities')return route.fulfill({json:{models:{enabled:false,profiles:[]},adapters:[],media:{}}});
    const name=url.pathname==='/'?'index.html':url.pathname.slice(1);
    return route.fulfill({body:files.get(name)||'',contentType:name.endsWith('.js')?'text/javascript':name.endsWith('.html')?'text/html':'text/css'});
  });
  await page.goto('http://127.0.0.1:8099/#case=first');
  await page.locator('#case-detail[data-case-id="first"]').waitFor({state:'visible'});
  return {browser,page,errors,writes};
  } catch(error) {await browser.close();throw error;}
}

test('Customer navigation follows the pending selected case and never reverts after its load fails',browserOptions,async()=>{
  const release=deferred();
  const {browser,page,errors,writes}=await fixture(async route=>{await release.promise;return route.fulfill({status:503,json:{error:'Second case unavailable'}});});
  try {
    assert.equal(await page.locator('#customer-link').getAttribute('href'),'/customer.html?case=first');
    await Promise.all([
      page.waitForRequest(request=>new URL(request.url()).pathname==='/api/platform/cases/second',{timeout:4000}),
      page.locator('.case-item[data-case-id="second"]').click(),
    ]);
    const during=await page.locator('#customer-link').getAttribute('href');
    release.resolve();await page.locator('#error-message').filter({hasText:'Second case unavailable'}).waitFor({state:'visible'});
    const after=await page.locator('#customer-link').getAttribute('href');
    assert.deepEqual({during,after},{during:'/customer.html?case=second',after:'/customer.html?case=second'});
    assert.equal(await page.locator('#case-detail').isVisible(),false);
    assert.deepEqual(errors,[]);assert.deepEqual(writes,[]);
  } finally {release.resolve();await browser.close();}
});

test('Team case title is readable while raw case identity remains in metadata and dataset',browserOptions,async()=>{
  const {browser,page,errors}=await fixture();
  try {
    assert.equal(await page.locator('#case-title').textContent(),'Gather the original request');
    assert.match(await page.locator('#case-meta').textContent(),/Case first/);
    assert.equal(await page.locator('#case-detail').getAttribute('data-case-id'),'first');
    assert.deepEqual(errors,[]);
  } finally {await browser.close();}
});
