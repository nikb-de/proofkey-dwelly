import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const source=await readFile(new URL('../session.js',import.meta.url),'utf8');
const {CommunicationsSession,communicationEnvelope}=await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
const envelope={schema_version:'proofkey-inbound-v1',delivery_id:'delivery-1',conversation_id:'thread-1',format:'message',payload:{sender:'customer@example.test',recipients:['operator@example.test'],occurred_at:'2026-10-10T12:00:00Z',text:'<script>source claim</script>'}};
const deferred=()=>{let resolve,reject;const promise=new Promise((r,j)=>{resolve=r;reject=j;});return {resolve,reject,promise};};

test('JSON import preserves the complete source envelope and rejects malformed or oversized input',async()=>{
  assert.deepEqual(await communicationEnvelope({format:'json',jsonText:JSON.stringify(envelope)}),envelope);
  await assert.rejects(communicationEnvelope({format:'json',jsonText:'{bad'}),/valid JSON/);
  await assert.rejects(communicationEnvelope({format:'json',jsonText:JSON.stringify({...envelope,schema_version:'wrong'})}),/proofkey-inbound-v1/);
  await assert.rejects(communicationEnvelope({format:'json',jsonText:JSON.stringify({...envelope,case_id:'injected'})}),/fields/);
  await assert.rejects(communicationEnvelope({format:'json',jsonText:JSON.stringify({...envelope,delivery_id:''})}),/delivery/);
  await assert.rejects(communicationEnvelope({format:'json',jsonText:' '.repeat(40*1024*1024+1)}),/40 MiB/);
});

test('raw email import preserves bytes with explicit source IDs and enforces file bounds',async()=>{
  const bytes=Uint8Array.from([70,114,111,109,58,32,0xc3,0xa9,13,10]);
  const result=await communicationEnvelope({format:'eml',deliveryId:'delivery-2',conversationId:'thread-2',file:new Blob([bytes])});
  assert.deepEqual(result,{schema_version:'proofkey-inbound-v1',delivery_id:'delivery-2',conversation_id:'thread-2',format:'email',payload:{raw_base64:Buffer.from(bytes).toString('base64')}});
  await assert.rejects(communicationEnvelope({format:'eml',deliveryId:'x',conversationId:'y'}),/Choose/);
  await assert.rejects(communicationEnvelope({format:'eml',deliveryId:'',conversationId:'y',file:new Blob([bytes])}),/delivery/);
  await assert.rejects(communicationEnvelope({format:'eml',deliveryId:'x',conversationId:'y',file:{size:26*1024*1024+1}}),/26 MiB/);
});

test('communications refresh is GET only and a late response cannot replace a newer list',async()=>{
  const pending=deferred(),calls=[];
  const session=new CommunicationsSession(async(path,options)=>{calls.push([path,options?.method]);return calls.length===1?pending.promise:{connectors:[],receipts:[{receipt_id:'new'}],provider_connections:false};});
  const old=session.load();await session.load();pending.resolve({receipts:[{receipt_id:'old'}]});await old;
  assert.equal(session.value.receipts[0].receipt_id,'new');
  assert.deepEqual(calls,[['/communications','GET'],['/communications','GET']]);
});

test('superseded inbox failures do not reach the error presenter, but current failures still reject',async()=>{
  const pending=deferred();let calls=0;
  const session=new CommunicationsSession(async()=>++calls===1?pending.promise:{connectors:[],receipts:[{receipt_id:'current'}]});
  const stale=session.load();await session.load();pending.reject(Error('stale offline response'));
  await assert.doesNotReject(stale);
  assert.equal(session.error,'');assert.equal(session.value.receipts[0].receipt_id,'current');
  session.api=async()=>{throw Error('current offline response');};
  await assert.rejects(session.load(),/current offline response/);assert.equal(session.error,'current offline response');
});

test('failed imports reuse the request key, retain source input, and never retry automatically',async()=>{
  const calls=[];let fail=true;
  const session=new CommunicationsSession(async(path,options)=>{calls.push({path,...options});if(fail)throw Error('offline');return {receipt:{receipt_id:'receipt-1',status:'accepted',case_id:'case-1'}};});
  await assert.rejects(session.import('local-chat',envelope),/offline/);
  assert.equal(session.busy,false);assert.equal(session.error,'offline');assert.equal(calls.length,1);
  assert.deepEqual(calls[0].body,{connector_id:'local-chat',envelope});
  fail=false;const receipt=await session.import('local-chat',envelope);
  assert.equal(receipt.status,'accepted');assert.equal(calls[0].idempotencyKey,calls[1].idempotencyKey);assert.ok(calls[0].idempotencyKey);
  assert.equal(session.error,'');assert.equal(session.lastReceipt.receipt_id,'receipt-1');assert.equal(calls.length,2);
});

test('quarantine retry is explicit, receipt scoped, and guarded against concurrent writes',async()=>{
  const pending=deferred(),calls=[];
  const session=new CommunicationsSession(async(path,options)=>{calls.push({path,...options});return pending.promise;});
  const first=session.retry('receipt/with spaces');
  await assert.rejects(session.retry('another'),/in progress/);
  assert.equal(calls.length,1);assert.equal(calls[0].path,'/communications/receipt%2Fwith%20spaces/retry');assert.deepEqual(calls[0].body,{});assert.equal(calls[0].method,'POST');
  pending.resolve({receipt:{receipt_id:'receipt/with spaces',status:'quarantined',reason:'unknown_contact'}});await first;
  assert.equal(session.lastReceipt.status,'quarantined');assert.equal(session.busy,false);
});

test('browser communications imports explicitly, preserves drafts and renders untrusted provenance as text',
  {skip:!process.env.PROOFKEY_PLAYWRIGHT_MODULE},async()=>{
  const {chromium}=await import(process.env.PROOFKEY_PLAYWRIGHT_MODULE);
  const browser=await chromium.launch({headless:true,...(process.env.PROOFKEY_CHROME_PATH?{executablePath:process.env.PROOFKEY_CHROME_PATH}:{})});
  try {
    const page=await browser.newPage(),writes=[],errors=[];let communicationsReads=0;
    page.setDefaultTimeout(4000);page.on('pageerror',error=>errors.push(error.message));
    const files=new Map(await Promise.all(['index.html','app.js','session.js'].map(async name=>[name,await readFile(new URL('../'+name,import.meta.url),'utf8')])));
    const receipt={receipt_id:'receipt-1',connector_id:'local-chat',channel:'chat',delivery_id:'<script>window.injected=true</script>',conversation_id:'thread-1',status:'accepted',case_id:'first',event_ids:['event-1'],revision:1,source:'operator_import',raw_sha256:'a'.repeat(64),provenance:{normalizer_version:'test-normalizer'}};
    const value={connectors:[{id:'local-chat',channel:'chat',configured:true,route_count:1,contact_count:2,provider_connected:false}],receipts:[receipt],provider_connections:false};
    await page.route('**/*',async route=>{
      const request=route.request(),url=new URL(request.url());
      if(!url.pathname.startsWith('/api/platform')){const name=url.pathname==='/'?'index.html':url.pathname.slice(1);return route.fulfill({body:files.get(name)||'',contentType:name.endsWith('.js')?'text/javascript':name.endsWith('.html')?'text/html':'text/css'});}
      let body;
      if(request.method()==='POST'){
        writes.push({path:url.pathname,body:request.postDataJSON(),headers:request.headers()});
        body={receipt};
      } else if(url.pathname==='/api/platform/capabilities')body={models:{enabled:false,profiles:[]},adapters:[],media:{}};
      else if(url.pathname==='/api/platform/cases')body={cases:[{case_id:'first'}]};
      else if(url.pathname==='/api/platform/cases/first')body={case:{case_id:'first',snapshot:{case_id:'first',revision:1,links:{order_id:'order',customer_id:'customer',operator_id:'operator'},participants:['customer','operator'],events:[]},states:{},decisions:[],reviews:[],actions:[],assets:[],model_jobs:[],communications:[receipt]}};
      else if(url.pathname==='/api/platform/communications'){communicationsReads++;body=value;}
      else throw Error('Unexpected URL '+url.pathname);
      return route.fulfill({json:body});
    });
    await page.goto('http://127.0.0.1:8099/#case=first');
    await page.locator('#case-title').filter({hasText:'first'}).waitFor();
    await page.fill('#evidence-text','Keep my evidence draft');
    assert.equal(communicationsReads,0);
    await page.locator('[data-view="communications"]').click();
    await page.selectOption('#communication-connector','local-chat');
    await page.fill('#communication-json','{invalid');await page.locator('#communication-import').click();
    await page.locator('#error-message').filter({hasText:'valid JSON'}).waitFor();assert.equal(writes.length,0);
    await page.fill('#communication-json',JSON.stringify(envelope));await page.locator('#communication-import').click();
    await page.locator('#communication-outcome').filter({hasText:'Accepted'}).waitFor();
    assert.equal(writes.length,1);assert.deepEqual(writes[0].body,{connector_id:'local-chat',envelope});
    assert.equal(writes[0].headers['x-proofkey-request'],'platform-v1');assert.ok(writes[0].headers['idempotency-key']);
    assert.match(await page.locator('#communication-receipts').innerText(),/<script>window.injected=true<\/script>/);
    assert.equal(await page.evaluate(()=>Boolean(window.injected)),false);
    await page.locator('[data-view="cases"]').click();
    assert.equal(await page.inputValue('#evidence-text'),'Keep my evidence draft');
    await page.locator('#case-communications > details > summary').click();
    assert.match(await page.locator('#case-communications').innerText(),/receipt-1/);
    await page.locator('[data-view="communications"]').click();
    assert.equal(await page.inputValue('#communication-json'),JSON.stringify(envelope));
    await page.selectOption('#communication-format','eml');
    await page.fill('#communication-delivery','email-1');await page.fill('#communication-conversation','thread-1');
    await page.setInputFiles('#communication-file',{name:'message.eml',mimeType:'message/rfc822',buffer:Buffer.from('From: source@example.test\r\n\r\nOriginal text')});
    await page.locator('#communication-import').click();
    await page.waitForFunction(()=>!document.getElementById('communication-import').disabled);
    assert.equal(writes.length,2);assert.equal(writes[1].body.envelope.format,'email');
    assert.equal(Buffer.from(writes[1].body.envelope.payload.raw_base64,'base64').toString(),'From: source@example.test\r\n\r\nOriginal text');
    assert.deepEqual(errors,[]);
  } finally {await browser.close();}
});

test('browser accepted import refreshes the case despite inbox failure and ignores an older failed observation',
  {skip:!process.env.PROOFKEY_PLAYWRIGHT_MODULE},async()=>{
  const {chromium}=await import(process.env.PROOFKEY_PLAYWRIGHT_MODULE);
  const browser=await chromium.launch({headless:true,...(process.env.PROOFKEY_CHROME_PATH?{executablePath:process.env.PROOFKEY_CHROME_PATH}:{})});
  try {
    const page=await browser.newPage(),errors=[];let writes=0,caseReads=0,listReads=0,mode='normal',oldRoute;
    page.setDefaultTimeout(4000);page.on('pageerror',error=>errors.push(error.message));
    const files=new Map(await Promise.all(['index.html','app.js','session.js'].map(async name=>[name,await readFile(new URL('../'+name,import.meta.url),'utf8')])));
    const receipt={receipt_id:'receipt-accepted',connector_id:'local-chat',channel:'chat',delivery_id:'delivery-1',status:'accepted',case_id:'first',event_ids:['event-1'],revision:1,source:'operator_import'};
    const inbox={connectors:[{id:'local-chat',channel:'chat',configured:true,route_count:1,contact_count:2,provider_connected:false}],receipts:[],provider_connections:false};
    await page.route('**/*',async route=>{
      const request=route.request(),url=new URL(request.url());
      if(!url.pathname.startsWith('/api/platform')){const name=url.pathname==='/'?'index.html':url.pathname.slice(1);return route.fulfill({body:files.get(name)||'',contentType:name.endsWith('.js')?'text/javascript':name.endsWith('.html')?'text/html':'text/css'});}
      let body;
      if(request.method()==='POST'){writes++;body={receipt};}
      else if(url.pathname==='/api/platform/capabilities')body={models:{enabled:false,profiles:[]},adapters:[],media:{}};
      else if(url.pathname==='/api/platform/cases'){listReads++;body={cases:[{case_id:'first'}]};}
      else if(url.pathname==='/api/platform/cases/first'){
        caseReads++;body={case:{case_id:'first',snapshot:{case_id:'first',revision:writes?1:0,links:{order_id:'order',customer_id:'customer',operator_id:'operator'},participants:['customer','operator'],events:writes?[{event_id:'event-1',kind:'message',channel:'chat',sender_id:'customer',text:'Accepted source evidence'}]:[]},states:{},decisions:[],reviews:[],actions:[],assets:[],model_jobs:[],communications:writes?[receipt]:[]}};
      } else if(url.pathname==='/api/platform/communications'){
        if(mode==='hold-old'){oldRoute=route;mode='normal';return;}
        if(writes && mode!=='recovered')return route.fulfill({status:503,json:{error:{code:'inbox_unavailable'}}});
        body=inbox;
      } else throw Error('Unexpected URL '+url.pathname);
      return route.fulfill({json:body});
    });
    await page.goto('http://127.0.0.1:8099/#case=first');await page.locator('#case-title').filter({hasText:'first'}).waitFor();
    await page.fill('#evidence-text','Unfinished evidence draft');await page.fill('#review-note','Unfinished review draft');
    await page.locator('[data-view="communications"]').click();await page.selectOption('#communication-connector','local-chat');
    await page.fill('#communication-json',JSON.stringify(envelope));await page.locator('#communication-import').click();
    await page.locator('#error-message').waitFor({state:'visible'});
    assert.equal(caseReads,2,'accepted POST must refresh the selected case even when inbox GET fails');
    assert.equal(listReads,2,'accepted POST must refresh the case list independently');
    assert.match(await page.locator('#error-message').innerText(),/Accepted.*saved.*inbox/i);
    assert.match(await page.locator('#communication-outcome').innerText(),/Accepted.*receipt-accepted/);
    assert.equal(await page.inputValue('#communication-json'),JSON.stringify(envelope));
    await page.locator('[data-view="cases"]').click();
    assert.match(await page.locator('#case-meta').innerText(),/Revision 1/);
    assert.match(await page.locator('#evidence-list').innerText(),/Accepted source evidence/);
    assert.equal(await page.inputValue('#evidence-text'),'Unfinished evidence draft');assert.equal(await page.inputValue('#review-note'),'Unfinished review draft');
    mode='hold-old';const requested=page.waitForRequest(request=>request.url().endsWith('/communications'));
    await page.locator('[data-view="communications"]').click();await requested;
    await page.locator('[data-view="cases"]').click();mode='recovered';
    await page.locator('[data-view="communications"]').click();await page.locator('#communications-loading').filter({hasText:'Local receipt history'}).waitFor();
    const oldResponse=page.waitForResponse(response=>response.url().endsWith('/communications') && response.status()===503);
    await oldRoute.fulfill({status:503,json:{error:{code:'stale_inbox_failure'}}});await (await oldResponse).finished();
    await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
    assert.equal(await page.locator('#error-message').isHidden(),true,'the older failure must not overwrite the newer successful observation');
    assert.equal(writes,1);assert.deepEqual(errors,[]);
  } finally {await browser.close();}
});
