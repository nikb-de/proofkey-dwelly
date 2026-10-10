import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

const source = await readFile(new URL('../preparation-model.js', import.meta.url), 'utf8').catch(() => 'export default {}');
const model = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
const profile = () => ({name:'Dispatch review',process_type:'reschedule',acknowledgement:'receipt_only',readback_required:true,mappings:{cases:'case record',delivery:'delivery record',scheduling:'availability record',returns:'return record',messaging:'message record',operator:'review queue'}});
const capabilities = () => ({schema_version:'proofkey-platform-capabilities-v1',execution_mode:'local_sandbox',authentication:'trusted_local_operator_not_production_auth',external_effects:0,adapters:[{id:'cases',status:'connected',mode:'local_postgresql'},{id:'delivery',status:'not_connected',mode:'interface_only'},{id:'scheduling',status:'sandbox',mode:'postgres_sandbox'},{id:'returns',status:'not_connected',mode:'interface_only'},{id:'messaging',status:'not_connected',mode:'interface_only'},{id:'operator',status:'connected',mode:'local_review_queue'}],models:{enabled:false,profiles:[]},media:{},communications:{provider_connections:false,outbound_enabled:false,connectors:[]}});
const environment = () => ({capabilities:capabilities(),cases:{cases:[]},errors:{},checked_at:'2026-10-10T12:00:00.000Z'});

test('every adapter surface needs a mapping before a profile can be handed off', () => {
  assert.deepEqual(model.validateProfile(profile()),[]);
  for (const id of ['cases','delivery','scheduling','returns','messaging','operator']) {
    const value=profile();value.mappings[id]='';
    assert.ok(model.validateProfile(value).some(error => error.field===`mappings.${id}`));
  }
});

test('invalid profile settings and unbounded mapping inputs are rejected', () => {
  for (const change of [{name:' '},{process_type:'execute'},{acknowledgement:'done'},{readback_required:'true'},{mappings:[]}]) {
    assert.ok(model.validateProfile({...profile(),...change}).length>0);
  }
  const value=profile();value.mappings.delivery='a'.repeat(241);
  assert.ok(model.validateProfile(value).some(error => error.field==='mappings.delivery'));
});

test('storage refusal keeps the caller draft and never reports a saved profile', () => {
  const draft=profile(),before=structuredClone(draft);
  const result=model.saveProfile({setItem(){throw Error('Quota exceeded');}},draft);
  assert.equal(result.ok,false);assert.match(result.error,/browser|storage|save/i);
  assert.deepEqual(draft,before);
  assert.equal(model.loadProfile({getItem(){throw Error('Access denied');}}).ok,false);
});

test('saved draft survives a round trip and malformed stored data cannot replace it', () => {
  let raw;const storage={setItem(key,value){raw=value;},getItem(){return raw;}};
  assert.equal(model.saveProfile(storage,profile()).ok,true);
  assert.deepEqual(model.loadProfile(storage).profile,profile());
  raw='not JSON';assert.equal(model.loadProfile(storage).ok,false);
  raw=JSON.stringify({schema_version:'unsupported',profile:profile()});
  assert.equal(model.loadProfile(storage).ok,false);
});

test('exports explicitly stay local drafts even if an input carries activation fields', () => {
  const document=model.profileDocument({...profile(),runtime_activation:true,api_key:'do-not-copy'});
  assert.equal(document.status,'local_draft');assert.equal(document.runtime_activation,false);
  assert.equal(document.profile.runtime_activation,undefined);assert.equal(document.profile.api_key,undefined);
  assert.equal(document.profile.acknowledgement,'receipt_only');
});

test('preflight separates missing mappings, disconnected surfaces and unknown upstream readback', () => {
  const draft=profile();draft.mappings.returns='';
  const result=model.runPreflight(draft,environment());
  const status=id=>result.checks.find(check=>check.id===id)?.status;
  assert.equal(status('mapping.cases'),'passed');
  assert.equal(status('mapping.delivery'),'fail');
  assert.equal(status('mapping.scheduling'),'passed');
  assert.equal(status('mapping.returns'),'not_configured');
  assert.equal(status('source_readback'),'unknown');
  assert.equal(result.scope,'local_read_only');assert.equal(result.runtime_activation,false);
});

test('unknown capability versions and failed API reads never pass environment checks', () => {
  const env=environment();env.capabilities.schema_version='unknown-v2';
  assert.equal(model.runPreflight(profile(),env).checks.find(x=>x.id==='version').status,'fail');
  env.capabilities=null;env.cases=null;env.errors={capabilities:'offline',cases:'offline'};
  const result=model.runPreflight(profile(),env);
  assert.equal(result.checks.find(x=>x.id==='version').status,'unknown');
  assert.equal(result.checks.find(x=>x.id==='cases').status,'fail');
  assert.equal(result.checks.find(x=>x.id==='mapping.cases').status,'unknown');
});

test('malformed adapter entries remain unknown rather than stopping the preflight report', () => {
  const env=environment();env.capabilities.adapters=[null,{id:'delivery',status:'invented'}];
  const result=model.runPreflight(profile(),env);
  assert.equal(result.checks.find(x=>x.id==='mapping.cases').status,'unknown');
  assert.equal(result.checks.find(x=>x.id==='mapping.delivery').status,'unknown');
});

test('environment refresh only reads the two authorized endpoints and preserves independent failures', async () => {
  const calls=[];
  const result=await model.readEnvironment(async(path,options)=>{calls.push([path,options.method]);if(path==='/cases')throw Error('offline');return capabilities();});
  assert.deepEqual(calls,[['/capabilities','GET'],['/cases','GET']]);
  assert.equal(result.capabilities.schema_version,'proofkey-platform-capabilities-v1');
  assert.equal(result.cases,null);assert.match(result.errors.cases,/offline/);
});
