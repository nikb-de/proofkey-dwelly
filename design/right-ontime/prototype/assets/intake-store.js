(()=>{
const {LIMITS,validateDeclaration,validateEvent,validateFileMetadata,mediaMetadata}=globalThis.ProofKeyIntakeModel;
const DATABASE='right-ontime-local-intake-v1';
const request=r=>new Promise((resolve,reject)=>{r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});
async function prepareFile(file){
 const kind=validateFileMetadata(file);const bytes=await file.arrayBuffer();
 const b=new Uint8Array(bytes),starts=values=>values.every((v,i)=>b[i]===v),ascii=(start,end)=>String.fromCharCode(...b.slice(start,end));
 const signature={
  'image/png':()=>starts([137,80,78,71,13,10,26,10]),
  'image/jpeg':()=>starts([255,216,255]),
  'audio/wav':()=>ascii(0,4)==='RIFF'&&ascii(8,12)==='WAVE',
  'audio/mpeg':()=>ascii(0,3)==='ID3'||b[0]===255&&(b[1]&224)===224,
  'audio/mp4':()=>ascii(4,8)==='ftyp',
  'audio/webm':()=>starts([26,69,223,163])
 };
 if(!signature[file.type]())throw Error('File bytes do not match its declared type');
 if(kind==='photo'){let bitmap;try{bitmap=await createImageBitmap(file);if(!bitmap.width||!bitmap.height)throw Error();}catch{throw Error('Image cannot be decoded');}finally{bitmap?.close();}}
 else{const context=new (window.AudioContext||window.webkitAudioContext)();try{await context.decodeAudioData(bytes.slice(0));}catch{throw Error('Audio cannot be decoded');}finally{await context.close();}}
 const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),x=>x.toString(16).padStart(2,'0')).join('');
 return {blob:file,name:file.name,media:mediaMetadata(file,'asset-'+crypto.randomUUID(),hash),kind};
}
async function openStore(){
 const opening=indexedDB.open(DATABASE,1);opening.onupgradeneeded=()=>{opening.result.createObjectStore('cases',{keyPath:'id'});opening.result.createObjectStore('assets',{keyPath:'id'});};
 const db=await request(opening);
 async function read(name,key){return request(db.transaction(name).objectStore(name).get(key));}
 async function mutate(run){return new Promise((resolve,reject)=>{const tx=db.transaction(['cases','assets'],'readwrite');let result,problem;tx.oncomplete=()=>resolve(result);tx.onabort=()=>reject(problem||tx.error||Error('Storage transaction failed; draft retained'));tx.onerror=()=>{};Promise.resolve().then(()=>run(tx)).then(v=>{result=v;}).catch(e=>{problem=e;tx.abort();});});}
 return {get:id=>read('cases',id),asset:id=>read('assets',id),list:()=>request(db.transaction('cases').objectStore('cases').getAll()),
 create:async(declaration,title)=>{validateDeclaration(declaration);return mutate(async tx=>{const cases=tx.objectStore('cases');if(await request(cases.get(declaration.case_id)))throw Error('Case ID already exists');if(await request(cases.count())>=LIMITS.cases)throw Error('Local case limit reached');const record={id:declaration.case_id,title:String(title).slice(0,160),declaration:structuredClone(declaration),revision:0,events:[],created_at:new Date().toISOString()};cases.add(record);return record;});},
 append:async(id,revision,events,assets)=>{
  if(!Array.isArray(events)||!events.length||!Array.isArray(assets))throw Error("No evidence to save");
  events=structuredClone(events);
  assets=assets.map(a=>({...a,media:{...a.media}}));
  for(const a of assets){
   if(!(a.blob instanceof Blob))throw Error("Missing attachment bytes");
   const checked=await prepareFile(a.blob);
   if(checked.media.sha256!==a.media.sha256||checked.media.mime_type!==a.media.mime_type||checked.media.size_bytes!==a.media.size_bytes)throw Error("Attachment metadata does not match bytes");
   if(events.filter(e=>e.media?.asset_id===a.media.asset_id).length!==1)throw Error("Attachment must belong to exactly one event");
  }
  return mutate(async tx=>{const cases=tx.objectStore('cases'),blobs=tx.objectStore('assets');const record=await request(cases.get(id));if(!record)throw Error('Case not found');if(record.revision!==revision)throw Error('Case changed in another tab; reload before retry');if(record.events.length+events.length>LIMITS.events)throw Error('Event limit reached');const used=new Set(record.events.map(e=>e.event_id));for(const e of events){validateEvent(e,record.declaration.participants);if(used.has(e.event_id))throw Error('Duplicate event ID');used.add(e.event_id);}const all=await request(blobs.getAll());let total=all.reduce((n,a)=>n+a.blob.size,0);const hashes=new Set(all.map(a=>a.media.sha256));for(const a of assets){if(hashes.has(a.media.sha256))throw Error('Duplicate file bytes already stored');hashes.add(a.media.sha256);total+=a.blob.size;if(total>LIMITS.total)throw Error('100 MiB local storage limit exceeded');if(await request(blobs.get(a.media.asset_id)))throw Error('Duplicate asset ID');blobs.add({id:a.media.asset_id,...a});}for(const e of events){if(e.media){const a=assets.find(a=>a.media.asset_id===e.media.asset_id);if(!a||JSON.stringify(a.media)!==JSON.stringify(e.media))throw Error('Missing attachment bytes');}}record.events.push(...structuredClone(events));record.revision=record.events.length;cases.put(record);return record;});}};
}

globalThis.ProofKeyIntakeStore={DATABASE,prepareFile,openStore};
})();
