import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
import path from 'node:path';
const require=createRequire(process.env.PLAYWRIGHT_PACKAGE_JSON||import.meta.url);
const {chromium}=require('playwright');
const browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_EXECUTABLE_PATH?{executablePath:process.env.CHROMIUM_EXECUTABLE_PATH}:{})});
try{
 const page=await browser.newPage();page.setDefaultTimeout(10000);const errors=[];page.on('pageerror',e=>errors.push(String(e)));await page.route(/^https?:/,r=>r.abort());
 await page.goto(pathToFileURL(path.resolve(import.meta.dirname,'../intake.html')).href);await page.waitForFunction(()=>window.ProofKeyIntake);
 const result=await page.evaluate(async()=>{
  const api=window.ProofKeyIntake,store=api.store;
  const canvas=document.createElement('canvas');canvas.width=4;canvas.height=4;canvas.getContext('2d').fillRect(0,0,4,4);
  const blob=await new Promise(resolve=>canvas.toBlob(resolve));
  const file=new File([blob],'safe.png',{type:'image/png'});
  const asset=await api.prepareFile(file);
  const declaration={case_id:'storage-test',links:{order_id:'order1',customer_id:'c1',operator_id:'o1'},participants:['c1','o1'],language:'en'};
  await store.create(declaration,'Storage tests');
  const event=(id,media=null)=>({event_id:id,occurred_at:'2026-10-10T12:00:00Z',channel:'chat',sender_id:'c1',recipient_ids:['o1'],kind:media?'photo':'message',text:'Evidence',media});
  const rejected=async run=>{try{await run();return false;}catch{return true;}};
  const empty=await rejected(()=>store.append(declaration.case_id,0,[],[]));
  const orphan=await rejected(()=>store.append(declaration.case_id,0,[event('m1')],[asset]));
  const missing=await rejected(()=>store.append(declaration.case_id,0,[event('photo1',asset.media)],[]));
  await store.append(declaration.case_id,0,[event('photo1',asset.media)],[asset]);
  const stale=await rejected(()=>store.append(declaration.case_id,0,[event('m1')],[]));
  const duplicateEvent=await rejected(()=>store.append(declaration.case_id,1,[event('photo1')],[]));
  const duplicateFile=await rejected(()=>store.append(declaration.case_id,1,[event('photo2',asset.media)],[asset]));
  const wrongMime=await rejected(()=>api.prepareFile(new File([blob],'fake.jpg',{type:'image/jpeg'})));
  const oversized=await rejected(()=>api.prepareFile(new File([new Uint8Array(10485761)],'huge.png',{type:'image/png'})));
  const wavBytes=new ArrayBuffer(46),view=new DataView(wavBytes);
  const ascii=(offset,s)=>{for(let i=0;i<s.length;i++)view.setUint8(offset+i,s.charCodeAt(i));};
  ascii(0,'RIFF');view.setUint32(4,38,true);ascii(8,'WAVE');ascii(12,'fmt ');view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);view.setUint32(24,8000,true);view.setUint32(28,16000,true);view.setUint16(32,2,true);view.setUint16(34,16,true);ascii(36,'data');view.setUint32(40,2,true);
  const audio=await api.prepareFile(new File([wavBytes],'voice.wav',{type:'audio/wav'}));
  await store.append(declaration.case_id,1,[{...event('voice1',audio.media),kind:'voice_message'}],[audio]);
  return {empty,orphan,missing,stale,duplicateEvent,duplicateFile,wrongMime,oversized,revision:(await store.get(declaration.case_id)).revision,audioBytes:(await store.asset(audio.media.asset_id)).blob.size};
 });
 assert.deepEqual(result,{empty:true,orphan:true,missing:true,stale:true,duplicateEvent:true,duplicateFile:true,wrongMime:true,oversized:true,revision:2,audioBytes:46});
 await page.goto(pathToFileURL(path.resolve(import.meta.dirname,'../intake.html')).href+'?case=storage-test');await page.waitForSelector('#evidence-form');assert.equal(await page.locator('#history audio').count(),1);
 await page.locator('#message').fill('<script>window.injected=true</script>');
 // Inject a genuine IndexedDB write exception after validation to verify rollback and visible draft preservation.
 await page.evaluate(()=>{window.originalPut=IDBObjectStore.prototype.put;IDBObjectStore.prototype.put=function(){throw new DOMException('Test storage full','QuotaExceededError');};});
 await page.locator('#save-evidence').click();await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('Not saved:'));
 assert.equal(await page.locator('#message').inputValue(),'<script>window.injected=true</script>');
 assert.equal(await page.evaluate(()=>window.ProofKeyIntake.store.get('storage-test').then(x=>x.revision)),2);
 await page.evaluate(()=>{IDBObjectStore.prototype.put=window.originalPut;});
 await page.locator('#save-evidence').click();await page.waitForFunction(()=>document.querySelector('#history').textContent.includes('<script>window.injected=true</script>'));assert.equal(await page.evaluate(()=>window.injected),undefined);
 // Reject an excessive selection before reading or decoding the selected bytes.
 await page.evaluate(()=>{const transfer=new DataTransfer();const bytes=new Uint8Array(21*1024*1024);for(let i=0;i<5;i++)transfer.items.add(new File([bytes],`large-${i}.wav`,{type:'audio/wav'}));const input=document.querySelector('#files');input.files=transfer.files;input.dispatchEvent(new Event('change',{bubbles:true}));});
 await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('Draft exceeds'));
 assert.equal(await page.locator('#staged .file-row').count(),0);
 // Fill the independent test database with real Blob bytes up to the documented cap.
 await page.evaluate(async()=>{const open=indexedDB.open('right-ontime-local-intake-v1',1);await new Promise(r=>open.onsuccess=r);const tx=open.result.transaction('assets','readwrite');tx.objectStore('assets').add({id:'quota-fixture',blob:new Blob([new Uint8Array(100*1024*1024)]),media:{sha256:'quota-fixture'}});await new Promise((r,j)=>{tx.oncomplete=r;tx.onabort=j;});open.result.close();});
 const png=Buffer.from(await page.evaluate(()=>{const c=document.createElement('canvas');c.width=5;c.height=5;c.getContext('2d').fillRect(0,0,5,5);return c.toDataURL().split(',')[1];}),'base64');
 await page.locator('#files').setInputFiles([{name:'draft.png',mimeType:'image/png',buffer:png},{name:'duplicate.png',mimeType:'image/png',buffer:png}]);
 await page.waitForFunction(()=>document.querySelector('#staged').textContent.includes('Duplicate selected file'));
 await page.locator('#staged .file-row').last().getByRole('button',{name:'Remove'}).click();
 await page.locator('#save-evidence').click();await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('100 MiB'));
 assert.equal(await page.locator('[data-ready]').count(),1);assert.equal(await page.evaluate(()=>window.ProofKeyIntake.store.get('storage-test').then(x=>x.revision)),3);
 await page.locator('#staged button').click();assert.equal(await page.locator('#staged .file-row').count(),0);
 const downloadPromise=page.waitForEvent('download');await page.getByRole('button',{name:'Export payloads and local manifest'}).click();const download=await downloadPromise;
 const stream=await download.createReadStream();let json='';for await(const chunk of stream)json+=chunk;const exported=JSON.parse(json);assert.equal(exported.declaration.case_id,'storage-test');assert.deepEqual(exported.append_payloads.map(x=>x.expected_revision),[0,1,2]);assert.equal(exported.local_attachment_manifest.length,2);assert.equal(exported.snapshot_hash,undefined);
 assert.deepEqual(errors,[]);console.log('Intake storage checks passed: audio bytes/reload, metadata mismatch, empty/orphan/missing assets, duplicates, stale revision, transaction rollback, quota, retained drafts, removal, escaped text, export.');
}finally{await browser.close();}
