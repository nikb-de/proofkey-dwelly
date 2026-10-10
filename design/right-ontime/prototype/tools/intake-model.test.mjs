import {test} from 'node:test';
import assert from 'node:assert/strict';
import {runInNewContext} from 'node:vm';
import '../assets/intake-model.js';
const {validateDeclaration,validateEvent,validateFileMetadata,mediaMetadata}=globalThis.ProofKeyIntakeModel;
const declaration={case_id:'case-1',links:{order_id:'order-1',customer_id:'customer',operator_id:'operator'},participants:['customer','operator'],language:'en'};
test('declarations reject unsafe IDs, unknown fields and invalid participants',()=>{assert.equal(validateDeclaration(declaration),declaration);for(const change of [{case_id:'<script>'},{extra:true},{participants:['customer']},{language:'ru'}])assert.throws(()=>validateDeclaration({...declaration,...change}));});
test('events enforce participants, closed fields and nonempty messages',()=>{const event={event_id:'e1',occurred_at:'2026-10-10T10:00:00Z',channel:'chat',sender_id:'customer',recipient_ids:['operator'],kind:'message',text:'Hello',media:null};assert.equal(validateEvent(event,declaration.participants),event);for(const change of [{text:' '},{sender_id:'intruder'},{occurred_at:'yesterday'},{extra:true},{recipient_ids:['operator','operator']}])assert.throws(()=>validateEvent({...event,...change},declaration.participants));});
test('file metadata rejects empty, oversized, unsupported files and maps backend media',()=>{for(const file of [{type:'image/png',size:0},{type:'image/png',size:10485761},{type:'text/html',size:3},{type:'audio/wav',size:26214401}])assert.throws(()=>validateFileMetadata(file));assert.deepEqual(mediaMetadata({type:'image/png',size:70},'asset1','a'.repeat(64)),{asset_id:'asset1',sha256:'a'.repeat(64),mime_type:'image/png',size_bytes:70});});
test('calendar-invalid timestamps and unpaired Unicode cannot enter backend payloads',()=>{const event={event_id:'e1',occurred_at:'2026-02-30T10:00:00Z',channel:'chat',sender_id:'customer',recipient_ids:['operator'],kind:'message',text:'Hello',media:null};assert.throws(()=>validateEvent(event,declaration.participants));assert.throws(()=>validateEvent({...event,occurred_at:'2026-02-28T10:00:00Z',text:'\ud800'},declaration.participants));});

test('reported case and foreign-realm plain declarations are valid',()=>{
 const reported={case_id:'tst',links:{order_id:'order-1',customer_id:'customer',operator_id:'operator'},participants:['customer','operator'],language:'en'};
 assert.equal(validateDeclaration(reported),reported);
 const foreign=runInNewContext(`(${JSON.stringify(reported)})`);
 assert.notEqual(Object.getPrototypeOf(foreign),Object.prototype);
 assert.equal(validateDeclaration(foreign),foreign);
 assert.doesNotThrow(()=>validateDeclaration({...reported,links:foreign.links}));
 const dictionary=Object.assign(Object.create(null),reported,{links:Object.assign(Object.create(null),reported.links)});
 assert.equal(validateDeclaration(dictionary),dictionary);
});

test('foreign-realm events including nested media remain valid',()=>{
 const foreign=runInNewContext(`({event_id:'event-1',occurred_at:'2026-10-10T10:00:00Z',channel:'chat',sender_id:'customer',recipient_ids:['operator'],kind:'photo',text:null,media:{asset_id:'asset-1',sha256:'${'a'.repeat(64)}',mime_type:'image/png',size_bytes:70}})`);
 assert.equal(validateEvent(foreign,declaration.participants),foreign);
});

test('portable validation still rejects non-records and foreign invalid declarations',()=>{
 for(const candidate of [[],new Date(),new (class Case {constructor(){Object.assign(this,declaration);}})(),Object.create({inherited:true})])assert.throws(()=>validateDeclaration(candidate));
 assert.throws(()=>validateDeclaration({...declaration,links:new (class Links {constructor(){Object.assign(this,declaration.links);}})()}));
 for(const change of [{extra:true},{case_id:'bad id'},{participants:['customer']},{participants:['customer','operator','operator']}]){
  const foreign=runInNewContext(`(${JSON.stringify({...declaration,...change})})`);
  assert.throws(()=>validateDeclaration(foreign));
 }
});

test('declaration errors identify fields or participant rules without echoing values',()=>{
 assert.throws(()=>validateDeclaration({...declaration,links:{...declaration.links,order_id:'private order value'}}),/order_id.*letters.*digits/i);
 assert.throws(()=>validateDeclaration({...declaration,links:{...declaration.links,order_id:'private order value'}}),error=>!error.message.includes('private order value'));
 assert.throws(()=>validateDeclaration({...declaration,participants:['customer']}),/participants.*customer.*operator/i);
 assert.throws(()=>validateDeclaration({...declaration,participants:['customer','operator','operator']}),/participants.*unique/i);
 assert.throws(()=>validateDeclaration({...declaration,language:'ru'}),/language.*en/i);
 assert.throws(()=>validateDeclaration({...declaration,extra:'secret'}),/case.*fields/i);
});

test('inherited fields and comma-joined key collisions cannot become persisted declarations',()=>{
 const inheritedCase=Object.assign(Object.create(null),declaration);
 const disguisedCase=Object.assign(Object.create(inheritedCase),{'case_id,language,links,participants':'not actual fields'});
 assert.throws(()=>validateDeclaration(disguisedCase));
 const inheritedLinks=Object.assign(Object.create(null),declaration.links);
 const disguisedLinks=Object.assign(Object.create(inheritedLinks),{'customer_id,operator_id,order_id':'not actual fields'});
 assert.throws(()=>validateDeclaration({...declaration,links:disguisedLinks}));
});

test('hidden required fields cannot disguise extra fields that survive storage',()=>{
 const disguised={...declaration,extra:'unexpected'};
 Object.defineProperty(disguised,'language',{value:'en',enumerable:false});
 assert.throws(()=>validateDeclaration(disguised));
});
