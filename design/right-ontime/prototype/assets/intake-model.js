(()=>{
const LIMITS={image:10*1024*1024,audio:25*1024*1024,total:100*1024*1024,cases:256,events:128};
const id=/^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/;
const requireValue=(ok,message='Invalid case payload')=>{if(!ok)throw Error(message);};
const identifier=(v,field='ID')=>requireValue(typeof v==='string'&&id.test(v),`${field} must be 1–64 letters, digits, underscores or hyphens, starting with a letter or digit`);
const keys=(o,names,field='Payload')=>{
 requireValue(o!==null&&typeof o==='object',`${field} must be a plain record`);
 const prototype=Object.getPrototypeOf(o);
 // Object.prototype identity differs between realms; its own prototype does not.
 requireValue(prototype===null||Object.getPrototypeOf(prototype)===null,`${field} must be a plain record`);
 const actual=Object.keys(o);
 requireValue(actual.length===names.length&&actual.every(name=>names.includes(name)),`${field} fields must be: ${names.join(', ')}`);
};
const ids=(v,field='IDs')=>{
 requireValue(Array.isArray(v)&&v.length<=16,`${field} must be a list of at most 16 IDs`);
 requireValue(new Set(v).size===v.length,`${field} must contain unique IDs`);
 v.forEach(value=>identifier(value,`${field} ID`));
};
const bounded=v=>{const pending=[v];while(pending.length){const item=pending.pop();if(typeof item==='string')requireValue(Array.from(item).every(char=>{const cp=char.codePointAt(0);return cp<0xd800||cp>0xdfff;}),'Invalid Unicode text');else if(item&&typeof item==='object')pending.push(...Object.values(item));}requireValue(new TextEncoder().encode(JSON.stringify(v)).length<=16384,'Payload exceeds 16 KiB');};
function validTimestamp(value){if(typeof value!=='string'||value.length>64)return false;const p=/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(Z|[+-]\d{2}:\d{2})$/.exec(value);if(!p)return false;const [,year,month,day,hour,minute,second,zone]=p;const end=new Date(0);end.setUTCFullYear(Number(year),Number(month),0);return Number(year)>0&&Number(month)>=1&&Number(month)<=12&&Number(day)>=1&&Number(day)<=end.getUTCDate()&&Number(hour)<24&&Number(minute)<60&&Number(second)<60&&(zone==='Z'||Number(zone.slice(1,3))<24&&Number(zone.slice(4))<60)&&Number.isFinite(Date.parse(value));}
function validateDeclaration(v){
 keys(v,['case_id','links','participants','language'],'Case');
 identifier(v.case_id,'case_id');
 keys(v.links,['order_id','customer_id','operator_id'],'Case links');
 Object.entries(v.links).forEach(([field,value])=>identifier(value,field));
 ids(v.participants,'participants');
 requireValue(v.language==='en','language must be en');
 requireValue(v.links.customer_id!==v.links.operator_id,'customer_id and operator_id must be different');
 requireValue(v.participants.includes(v.links.customer_id)&&v.participants.includes(v.links.operator_id),'participants must include both customer_id and operator_id');
 bounded(v);return v;
}
function validateFileMetadata(f){const image=['image/png','image/jpeg'].includes(f.type),audio=['audio/mpeg','audio/wav','audio/mp4','audio/webm'].includes(f.type);requireValue(image||audio,'Unsupported file type');requireValue(Number.isInteger(f.size)&&f.size>0,'File is empty');requireValue(f.size<=(image?LIMITS.image:LIMITS.audio),'File exceeds size limit');return image?'photo':'audio';}
function mediaMetadata(f,asset_id,sha256){validateFileMetadata(f);identifier(asset_id);requireValue(/^[a-f0-9]{64}$/.test(sha256));return {asset_id,sha256,mime_type:f.type,size_bytes:f.size};}
function validateEvent(v,participants){keys(v,['event_id','occurred_at','channel','sender_id','recipient_ids','kind','text','media']);identifier(v.event_id);requireValue(validTimestamp(v.occurred_at));requireValue(['chat','email','phone','internal'].includes(v.channel));identifier(v.sender_id);ids(v.recipient_ids);requireValue(participants.includes(v.sender_id)&&v.recipient_ids.every(x=>participants.includes(x)));requireValue(v.text===null||typeof v.text==='string'&&v.text.length<=4096);if(v.kind==='message'){requireValue(typeof v.text==='string'&&!!v.text.trim()&&v.media===null);}else{requireValue(['photo','voice_message','call_recording'].includes(v.kind));keys(v.media,['asset_id','sha256','mime_type','size_bytes']);const type=validateFileMetadata({type:v.media.mime_type,size:v.media.size_bytes});requireValue((v.kind==='photo')===(type==='photo'));mediaMetadata({type:v.media.mime_type,size:v.media.size_bytes},v.media.asset_id,v.media.sha256);}bounded({expected_revision:0,event:v});return v;}

globalThis.ProofKeyIntakeModel={LIMITS,validateDeclaration,validateEvent,validateFileMetadata,mediaMetadata};
})();
