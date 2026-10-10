import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {createGitHubLibrary} from '../server/github.mjs';
const initial=JSON.parse(await fs.readFile(new URL('../examples/minimal.json',import.meta.url),'utf8'));
const changed=structuredClone(initial);changed.title='Предложенное изменение';
let draft=null,ref=false,pull=null,mainSha='file-1';const writes=[];
const encode=(data,sha)=>({type:'file',encoding:'base64',size:Buffer.byteLength(JSON.stringify(data)),content:Buffer.from(JSON.stringify(data)).toString('base64'),sha});
const result=(data,status=200)=>new Response(JSON.stringify(data),{status});
const fake=async(url,options)=>{
 const u=new URL(url),route=u.pathname.replace('/repos/nikb-de/proofkey-dwelly',''),method=options.method;
 if(method!=='GET')writes.push({route,body:JSON.parse(options.body)});
 if(route==='/contents/case-state-widget/cases')return result([{type:'file',name:'sample.json',sha:mainSha}]);
 if(route==='/pulls'&&method==='GET')return result(pull?[{number:42}]:[]);
 if(route==='/git/ref/heads/main')return result({object:{sha:'main-head'}});
 if(route.startsWith('/git/ref/heads/case-widget'))return result(ref?{object:{sha:'draft-head'}}:{},ref?200:404);
 if(route==='/git/refs'){ref=true;return result({object:{sha:'main-head'}},201)}
 if(route==='/contents/case-state-widget/cases/sample.json'){
  if(method==='PUT'){draft=JSON.parse(Buffer.from(JSON.parse(options.body).content,'base64').toString());return result({commit:{sha:'new-commit'}},201)}
  return result(u.searchParams.get('ref')?.startsWith('case-widget/')&&draft?encode(draft,'draft-file'):encode(initial,mainSha));
 }
 if(route==='/pulls'&&method==='POST'){pull=true;return result({number:42},201)}
 throw new Error('Unexpected '+method+' '+url);
};
const lib=createGitHubLibrary({readToken:'read-only',fetchImpl:fake});
assert.equal((await lib.list())[0].id,'sample');assert.deepEqual((await lib.get('sample')).data,initial);
const input={id:'sample',data:changed,base_revision:'file-1',request_id:'12345678-1234-1234-1234-123456789012'};
await assert.rejects(lib.propose(input,''),/токен/);
await assert.rejects(lib.propose({...input,id:'../README'},'write'),/Некорректный/);
await assert.rejects(lib.propose({...input,base_revision:'old'},'write'),/изменился/);
await assert.rejects(lib.propose({...input,data:initial},'write'),/нет изменений/);
assert.equal(writes.length,0);
const pr=await lib.propose(input,'write');assert.equal(pr.url,'https://github.com/nikb-de/proofkey-dwelly/pull/42');
assert.equal(writes.length,3);assert.equal(writes[0].body.ref,'refs/heads/case-widget/'+input.request_id);
assert.equal(writes[1].body.branch,'case-widget/'+input.request_id);assert.deepEqual(draft,changed);
assert.equal(writes[2].body.base,'main');assert.equal(writes[2].body.draft,true);
const retry=await lib.propose(input,'write');assert.equal(retry.reused,true);assert.equal(writes.length,3);
const broken=createGitHubLibrary({fetchImpl:async()=>result({},404)});await assert.rejects(broken.list(),/GITHUB_READ_TOKEN/);
console.log('PASS: GitHub catalog/read, stale-base rejection, no-op rejection, scoped branch/file changes, draft PR and idempotent retry; no main mutation.');
