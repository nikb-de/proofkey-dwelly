import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const source=await readFile(new URL('../session.js',import.meta.url),'utf8');
const {ModelPoller}=await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
const job=(status='running',caseId='first')=>({run_id:'run1',case_id:caseId,status});
function scheduler(){let id=0;const tasks=new Map();return {schedule:fn=>{tasks.set(++id,fn);return id;},cancel:key=>tasks.delete(key),size:()=>tasks.size,fire:async()=>{const entry=tasks.entries().next().value;if(!entry)return;tasks.delete(entry[0]);return entry[1]();}};}
const deferred=()=>{let resolve;const promise=new Promise(r=>{resolve=r;});return {resolve,promise};};

test('model polling uses GET only, reaches terminal once and does not restart on render',async()=>{
  const timer=scheduler(),updates=[],requests=[];
  const poller=new ModelPoller({api:async(path,options)=>{requests.push({path,method:options.method});return job('succeeded');},onUpdate:value=>updates.push(value),schedule:timer.schedule,cancel:timer.cancel});
  const context={caseId:'first',generation:1,jobs:[job()]};poller.watch(context);poller.watch(context);
  assert.equal(timer.size(),1);await timer.fire();
  assert.deepEqual(requests,[{path:'/model-runs/run1',method:'GET'}]);assert.equal(updates.length,1);assert.equal(timer.size(),0);
  poller.watch(context);assert.equal(timer.size(),0);
});

test('selection changes and dispose discard in-flight old-case results',async()=>{
  for(const exit of ['selection','dispose']){
    const timer=scheduler(),pending=deferred(),updates=[];
    const poller=new ModelPoller({api:()=>pending.promise,onUpdate:value=>updates.push(value),schedule:timer.schedule,cancel:timer.cancel});
    poller.watch({caseId:'first',generation:1,jobs:[job()]});const flight=timer.fire();
    if(exit==='selection')poller.watch({caseId:'second',generation:2,jobs:[]});else poller.dispose();
    pending.resolve(job('succeeded'));await flight;
    assert.deepEqual(updates,[]);assert.equal(timer.size(),0);
  }
});

test('poll errors stop observation; explicit reload resumes without a submission',async()=>{
  const timer=scheduler(),errors=[],requests=[];let failing=true;
  const poller=new ModelPoller({api:async(path,options)=>{requests.push(options.method);if(failing)throw Error('offline');return job('succeeded');},onError:error=>errors.push(error.message),schedule:timer.schedule,cancel:timer.cancel});
  const context={caseId:'first',generation:1,jobs:[job()]};poller.watch(context);await timer.fire();
  assert.deepEqual(errors,['offline']);assert.equal(poller.getState('run1').status,'paused');
  poller.watch(context);assert.equal(timer.size(),0);
  failing=false;poller.watch({...context,generation:2});await timer.fire();assert.deepEqual(requests,['GET','GET']);assert.equal(timer.size(),0);
});

test('polling has a finite request budget and explicit refresh can resume',async()=>{
  const timer=scheduler(),requests=[];
  const poller=new ModelPoller({api:async(path,options)=>{requests.push(options.method);return job();},maxPolls:2,schedule:timer.schedule,cancel:timer.cancel});
  poller.watch({caseId:'first',generation:1,jobs:[job()]});await timer.fire();await timer.fire();
  assert.equal(requests.length,2);assert.equal(timer.size(),0);assert.equal(poller.getState('run1').status,'paused');
  poller.retry('run1');await timer.fire();assert.equal(requests.length,3);assert.deepEqual(new Set(requests),new Set(['GET']));poller.dispose();
});

test('cross-case or wrong-run responses pause without being applied',async()=>{
  const timer=scheduler(),updates=[];
  const poller=new ModelPoller({api:async()=>job('succeeded','other'),onUpdate:value=>updates.push(value),schedule:timer.schedule,cancel:timer.cancel});
  poller.watch({caseId:'first',generation:1,jobs:[job()]});await timer.fire();assert.deepEqual(updates,[]);assert.equal(poller.getState('run1').status,'paused');
});

test('a fresh terminal reload cannot be overwritten by an older in-flight running response',async()=>{
  const timer=scheduler(),pending=deferred(),updates=[];
  const poller=new ModelPoller({api:()=>pending.promise,onUpdate:value=>updates.push(value),schedule:timer.schedule,cancel:timer.cancel});
  poller.watch({caseId:'first',generation:1,jobs:[job()]});const flight=timer.fire();
  poller.watch({caseId:'first',generation:1,jobs:[job('succeeded')]});
  pending.resolve(job());await flight;
  assert.deepEqual(updates,[]);assert.equal(timer.size(),0);
});

test('browser polling preserves each run inspector without reopening closed sections or leaking across cases',
  {skip:!process.env.PROOFKEY_PLAYWRIGHT_MODULE},async()=>{
  const {chromium}=await import(process.env.PROOFKEY_PLAYWRIGHT_MODULE);
  const browser=await chromium.launch({headless:true,...(process.env.PROOFKEY_CHROME_PATH?{executablePath:process.env.PROOFKEY_CHROME_PATH}:{})});
  try {
    const page=await browser.newPage(),errors=[],writes=[];
    page.on('pageerror',error=>errors.push(error.message));
    const staticFiles=new Map(await Promise.all(['index.html','app.js','session.js','product.js','style.css','coordination.js','coordination-panel.js','coordination.css'].map(async name=>[name,await readFile(new URL('../'+name,import.meta.url),'utf8')])));
    let reads=0;
    const pending={run_id:'pending',case_id:'first',status:'running'};
    const done={run_id:'done',case_id:'first',status:'succeeded',candidate:{state:'waiting'}};
    const detail=caseId=>({case_id:caseId,snapshot:{case_id:caseId,revision:0,links:{order_id:'order',customer_id:'customer',operator_id:'operator'},participants:['customer','operator'],events:[]},states:{},assets:[],decisions:[],reviews:[],actions:[],media_runs:[],model_jobs:[{...pending,case_id:caseId},{...done,case_id:caseId}]});
    await page.route('**/*',async route=>{
      const request=route.request(),url=new URL(request.url());
      if(request.method()!=='GET')writes.push(request.method()+' '+url.pathname);
      if(url.pathname.startsWith('/api/platform')){
        let body;
        if(url.pathname==='/api/platform/capabilities')body={models:{enabled:false,profiles:[]},adapters:[],media:{}};
        else if(url.pathname==='/api/platform/cases')body={cases:[{case_id:'first'},{case_id:'second'}]};
        else if(url.pathname==='/api/platform/model-runs/pending'){reads++;body={...pending,observation:reads};}
        else if(url.pathname==='/api/platform/cases/first')body=detail('first');
        else if(url.pathname==='/api/platform/cases/second')body=detail('second');
        else throw Error('Unexpected read: '+url.pathname);
        return route.fulfill({json:body});
      }
      const name=url.pathname==='/'?'index.html':url.pathname.slice(1);
      return route.fulfill({body:staticFiles.get(name)||'',contentType:name.endsWith('.js')?'text/javascript':name.endsWith('.html')?'text/html':'text/css'});
    });
    await page.goto('http://127.0.0.1:8099/#case=first');
    await page.locator('.model-options > summary').click();
    const pendingPanel=page.locator('[data-job-id="pending"] details');
    const donePanels=page.locator('[data-job-id="done"] details');
    await pendingPanel.locator('summary').click();
    for(const panel of await donePanels.all())await panel.locator('summary').click();
    await page.getByRole('tab',{name:/Sources/}).click();
    await page.fill('#evidence-text','Keep source draft');
    await page.getByRole('tab',{name:/Requests/}).click();
    await page.fill('#review-note','Keep review draft');
    await page.getByRole('tab',{name:/Summary/}).click();
    await page.waitForFunction(()=>document.querySelector('[data-job-id="pending"] pre')?.textContent.includes('"observation": 1'));
    assert.equal(await pendingPanel.evaluate(panel=>panel.open),true,'the pending run receipt stays open after its own update');
    assert.deepEqual(await donePanels.evaluateAll(panels=>panels.map(panel=>panel.open)),[true,true],'both completed-run sections stay open during another run update');
    await donePanels.first().locator('summary').click();
    await page.waitForFunction(()=>document.querySelector('[data-job-id="pending"] pre')?.textContent.includes('"observation": 2'));
    assert.deepEqual(await donePanels.evaluateAll(panels=>panels.map(panel=>panel.open)),[false,true],'a manually closed proposal stays closed independently of the receipt');
    assert.equal(await page.inputValue('#evidence-text'),'Keep source draft');
    assert.equal(await page.inputValue('#review-note'),'Keep review draft');
    await page.locator('.case-item[data-case-id="second"]').click();
    await page.locator('#case-detail[data-case-id="second"]').waitFor();
    assert.deepEqual(await page.locator('#model-jobs details').evaluateAll(panels=>panels.map(panel=>panel.open)),[false,false,false],'the next case starts closed even if run IDs coincide');
    assert.deepEqual(writes,[]);assert.deepEqual(errors,[]);
  } finally {await browser.close();}
});
