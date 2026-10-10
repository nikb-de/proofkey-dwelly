import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {createLibrary} from '../server/server.mjs';
const dir=await fs.mkdtemp(path.join(os.tmpdir(),'case-library-test-'));
const staticDir=path.join(dir,'public'),dataDir=path.join(dir,'private');await fs.mkdir(staticDir);await fs.writeFile(path.join(staticDir,'index.html'),'test-page');
const example=JSON.parse(await fs.readFile(new URL('../examples/minimal.json',import.meta.url),'utf8'));
let app,url;
async function start(options={}){app=await createLibrary({dataDir,staticDir,access:'public',...options});await new Promise(r=>app.server.listen(0,'127.0.0.1',r));url='http://127.0.0.1:'+app.server.address().port}
async function stop(){await new Promise(r=>app.server.close(r))}
const post=(data,headers={})=>fetch(url+'/api/cases',{method:'POST',headers:{'Content-Type':'application/json',...headers},body:JSON.stringify({filename:'sample.json',data})});
try{
 await start();assert.equal(await (await fetch(url)).text(),'test-page');
 let r=await post(example);assert.equal(r.status,201);const saved=await r.json();
 assert.match(saved.entry.id,/^[a-f0-9]{64}$/);
 r=await post(example);assert.equal(r.status,200);assert.equal((await r.json()).entry.id,saved.entry.id);
 const changed=structuredClone(example);changed.title='Changed';r=await post(changed);assert.equal(r.status,201);assert.notEqual((await r.json()).entry.id,saved.entry.id);
 assert.equal((await (await fetch(url+'/api/cases')).json()).cases.length,2);
 assert.deepEqual((await (await fetch(url+'/api/cases/'+saved.entry.id)).json()).data,example);
 assert.equal((await post({})).status,422);
 assert.equal((await post(example,{Origin:'https://foreign.example'})).status,403);
 assert.equal((await fetch(url+'/api/cases',{method:'POST',body:'{}'})).status,415);
 assert.equal((await fetch(url+'/api/cases',{method:'POST',headers:{'Content-Type':'application/json'},body:'{'})).status,400);
 assert.equal((await fetch(url+'/api/cases/'+'a'.repeat(64))).status,404);
 assert.equal((await fetch(url+'/private/'+saved.entry.id+'.json')).status,404);
 await stop();await start();assert.equal((await (await fetch(url+'/api/cases')).json()).cases.length,2);
 assert.deepEqual((await (await fetch(url+'/api/cases/'+saved.entry.id)).json()).data,example);
 await stop();await start({access:'team',token:'test-only-token-123456789012345'});
 assert.equal((await fetch(url+'/api/cases')).status,401);
 assert.equal((await fetch(url+'/api/cases/'+saved.entry.id)).status,401);
 assert.equal((await post(example)).status,401);
 assert.equal((await fetch(url+'/api/cases',{headers:{Authorization:'Bearer test-only-token-123456789012345'}})).status,200);
 await stop();await start({maxEntries:2});assert.equal((await post({...example,title:'Third'})).status,507);
 const concurrent=await Promise.all([post(example),post(example)]);assert.deepEqual(concurrent.map(r=>r.status),[200,200]);
 console.log('PASS: persistence across restart, exact retrieval, deduplication, immutable versions, validation, capacity, origin checks and team authorization.');
}finally{if(app?.server.listening)await stop();await fs.rm(dir,{recursive:true,force:true})}
