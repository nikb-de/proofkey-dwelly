import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
import path from 'node:path';
const require=createRequire(process.env.PLAYWRIGHT_PACKAGE_JSON||import.meta.url);
const {chromium}=require('playwright');
const browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_EXECUTABLE_PATH?{executablePath:process.env.CHROMIUM_EXECUTABLE_PATH}:{})});
const failures=[];
const url=pathToFileURL(path.resolve(import.meta.dirname,'../intake.html')).href;
async function run(name,callback){const context=await browser.newContext();try{const page=await context.newPage();page.setDefaultTimeout(5000);await page.route(/^https?:/,r=>r.abort());await page.goto(url);await page.waitForFunction(()=>window.ProofKeyIntake);await callback(page);console.log(`PASS ${name}`);}catch(error){failures.push(`${name}: ${error.message}`);console.log(`FAIL ${name}: ${error.message}`);}finally{await context.close();}}
async function fillCreate(page,id){await page.locator('#case-id').fill(id);await page.locator('#case-title').fill('Recovery test');await page.locator('#extra-participants').fill('courier');}
try{
 await run('committed create stays saved when list refresh fails',async page=>{
  await fillCreate(page,'create-fault');
  await page.evaluate(()=>{window.realList=window.ProofKeyIntake.store.list;window.ProofKeyIntake.store.list=async()=>{throw Error('Read unavailable');};});
  await page.locator('#create-form button').click();
  await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('Read unavailable'));
  assert.equal(await page.evaluate(()=>window.ProofKeyIntake.store.get('create-fault').then(c=>c.revision)),0);
  assert.match(await page.locator('#status').innerText(),/saved locally/i);
  assert.doesNotMatch(await page.locator('#status').innerText(),/not saved|draft is retained/i);
  assert.equal(await page.locator('#create-form button').isDisabled(),true);
  assert.equal(await page.locator('#case-id').inputValue(),'');
  await page.getByRole('button',{name:'Reload saved case'}).click();await page.waitForSelector('#evidence-form');
  assert.equal(await page.evaluate(()=>window.ProofKeyIntake.store.list().then(c=>c.length)),1);
 });
 await run('committed append stays saved when detail refresh fails',async page=>{
  await fillCreate(page,'append-fault');await page.locator('#create-form button').click();await page.waitForSelector('#evidence-form');
  await page.locator('#message').fill('Exactly one source message');
  await page.evaluate(()=>{window.realGet=window.ProofKeyIntake.store.get;window.ProofKeyIntake.store.get=async()=>{throw Error('Read unavailable');};});
  await page.locator('#save-evidence').click();await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('Read unavailable'));
  assert.equal(await page.evaluate(()=>window.realGet('append-fault').then(c=>c.revision)),1);
  assert.match(await page.locator('#status').innerText(),/saved locally/i);
  assert.doesNotMatch(await page.locator('#status').innerText(),/not saved|draft is retained/i);
  assert.equal(await page.locator('#save-evidence').isDisabled(),true);assert.equal(await page.locator('#message').inputValue(),'');
  await page.getByRole('button',{name:'Reload saved case'}).click();await page.waitForSelector('#history article');
  assert.equal(await page.locator('#history article').count(),1);
 });
 await run('explicit recipients preserve a subset and empty set through save/export',async page=>{
  await fillCreate(page,'recipients');await page.locator('#create-form button').click();await page.waitForSelector('#evidence-form');
  assert.equal(await page.locator('#recipients input:checked').count(),0);
  await page.locator('#recipients input[value="operator"]').check();await page.locator('#message').fill('Operator only');
  await page.evaluate(()=>{window.realPut=IDBObjectStore.prototype.put;IDBObjectStore.prototype.put=function(){throw Error('Write failed');};});
  await page.locator('#save-evidence').click();await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('Not saved:'));
  assert.equal(await page.locator('#recipients input[value="operator"]').isChecked(),true);
  await page.evaluate(()=>{IDBObjectStore.prototype.put=window.realPut;});
  await page.locator('#save-evidence').click();await page.waitForSelector('#history article');
  assert.deepEqual(await page.evaluate(()=>window.ProofKeyIntake.store.get('recipients').then(c=>c.events[0].recipient_ids)),['operator']);
  await page.locator('#message').fill('No recipient recorded');await page.locator('#save-evidence').click();await page.waitForFunction(()=>document.querySelectorAll('#history article').length===2);
  const downloadPromise=page.waitForEvent('download');await page.getByRole('button',{name:'Export payloads and local manifest'}).click();const download=await downloadPromise;let raw='';for await(const chunk of await download.createReadStream())raw+=chunk;const value=JSON.parse(raw);
  assert.deepEqual(value.append_payloads.map(p=>p.event.recipient_ids),[['operator'],[]]);
 });
 assert.deepEqual(failures,[]);
}finally{await browser.close();}
