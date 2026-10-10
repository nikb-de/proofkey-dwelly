const newKey=()=>globalThis.crypto?.randomUUID?.() || `customer-${Date.now()}-${Math.random().toString(16).slice(2)}`;
const sameSnapshot=(a,b)=>Boolean(a && b && a.case_id===b.case_id && a.revision===b.revision && a.snapshot_hash===b.snapshot_hash);
const validSnapshot=s=>Boolean(s && typeof s.case_id==='string' && Number.isInteger(s.revision) && /^[a-f0-9]{64}$/.test(s.snapshot_hash));
const boundRecord=(record,snapshot)=>Boolean(record && validSnapshot(snapshot) && sameSnapshot(record,snapshot));
const dateValue=value=>{
  if(typeof value!=='string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,3})?)?(?:Z|[+-]\d{2}:\d{2})$/.test(value))return NaN;
  const [year,month,day]=value.slice(0,10).split('-').map(Number);
  if(month<1 || month>12 || day<1 || day>new Date(Date.UTC(year,month,0)).getUTCDate())return NaN;
  return Date.parse(value);
};

export function validateWindow(draft,now=Date.now()) {
  const start=dateValue(draft.slot_start),end=dateValue(draft.slot_end);
  if(!Number.isFinite(start) || !Number.isFinite(end))return {valid:false,error:'Enter valid start and end times with a timezone.'};
  if(start<=now)return {valid:false,error:'Choose a start time in the future.'};
  if(end<=start || end-start>8*3600000)return {valid:false,error:'The window must end after it starts and last no more than eight hours.'};
  return {valid:true,start:new Date(start).toISOString(),end:new Date(end).toISOString()};
}

export function buildRequest(binding,current,draft,now=Date.now()) {
  if(!validSnapshot(binding) || !sameSnapshot(binding,current))throw Error('This case changed. Review the latest snapshot before submitting; your draft is retained.');
  const window=validateWindow(draft,now);
  if(!window.valid)throw Error(window.error);
  const ids=draft.evidence_event_ids;
  const available=new Set((current.events || []).map(event=>event.event_id));
  if(!Array.isArray(ids) || !ids.length || new Set(ids).size!==ids.length || ids.some(id=>typeof id!=='string' || !available.has(id)))throw Error('Select at least one supporting source evidence event from this case.');
  return {expected_revision:binding.revision,snapshot_hash:binding.snapshot_hash,action:{type:'reschedule_delivery',slot_start:window.start,slot_end:window.end,address_change:false},evidence_event_ids:[...ids]};
}

export function offeredWindows(detail,now=Date.now()) {
  const latest=detail?.decisions?.at(-1);
  if(!boundRecord(latest,detail?.snapshot) || latest.action?.type!=='reschedule_delivery' || latest.action.address_change!==false || !validateWindow(latest.action,now).valid)return [];
  return [{decision_id:latest.decision_id,slot_start:latest.action.slot_start,slot_end:latest.action.slot_end,evidence_event_ids:[...(latest.evidence_event_ids || [])]}];
}

export function customerStatus(detail) {
  const none={kind:'none',title:'No current delivery proposal',description:'Choose a requested window and its supporting sources. Carrier availability and price are not confirmed.',decision:null,receipt:null};
  const d=detail?.decisions?.at(-1),snapshot=detail?.snapshot;
  if(!boundRecord(d,snapshot) || d.action?.type!=='reschedule_delivery')return none;
  const matching=record=>boundRecord(record,snapshot) && record.decision_id===d.decision_id;
  const receipt=detail.actions?.filter(matching).at(-1);
  if(receipt?.status==='verified' && receipt.execution_mode==='postgres_sandbox')return {kind:'sandbox',title:'Local sandbox action recorded',description:'A local sandbox receipt is persisted. This is not a confirmed physical delivery or external carrier booking.',decision:d,receipt};
  const review=detail.reviews?.filter(matching).at(-1);
  if(review?.verdict==='approve')return {kind:'approved',title:'Operator approval recorded',description:'This proposal has operator approval. No matching verified sandbox execution is recorded; carrier booking and physical delivery are not confirmed.',decision:d,receipt:null};
  if(review?.verdict==='reject')return {kind:'rejected',title:'Proposal needs another review',description:'An operator rejected this proposal. Review the source evidence before requesting a new window.',decision:d,receipt:null};
  return {kind:'proposed',title:'Window preference recorded',description:'The operator proposal is saved and awaits review. Carrier availability, price and delivery are not confirmed.',decision:d,receipt:null};
}

export class CustomerSession {
  constructor(api,{now=Date.now,onChange=()=>{}}={}) {
    this.api=api;this.now=now;this.onChange=onChange;this.detail=null;this.binding=null;
    this.draft={slot_start:'',slot_end:'',evidence_event_ids:[]};this.step='choose';this.busy=false;
    this.error='';this.pending=new Map();this.completed=new Set();this.generation=0;this.checkedAt=null;
    this.savedOutcome=null;this.statusConfirmed=true;
  }
  get status(){
    if(!this.statusConfirmed)return {kind:'unknown',title:'Preference saved; refresh status',description:'The submission receipt confirms this preference was saved. The current case status could not be refreshed. Refresh before relying on an approval or action status.',decision:null,receipt:null};
    return customerStatus(this.detail);
  }
  accept(detail){
    if(!validSnapshot(detail?.snapshot) || detail.case_id!==detail.snapshot.case_id)throw Error('The case response is invalid.');
    this.detail=detail;this.binding={...detail.snapshot};this.checkedAt=new Date(this.now()).toISOString();this.statusConfirmed=true;
  }
  setDraft(value){if(this.busy)throw Error('A submission is in progress.');this.draft={...this.draft,...value};this.error='';}
  async load(id,{rebase=false}={}) {
    if(this.busy)throw Error('A submission is in progress.');
    const generation=++this.generation;
    const response=await this.api(`/cases/${encodeURIComponent(id)}`),detail=response.case || response;
    if(generation!==this.generation)return;
    if(detail.case_id!==id || !validSnapshot(detail.snapshot) || detail.snapshot.case_id!==id)throw Error('The response does not match the selected case.');
    if(!this.detail || this.detail.case_id!==id || rebase)this.accept(detail);
    else {this.detail=detail;this.checkedAt=new Date(this.now()).toISOString();}
    this.statusConfirmed=true;this.error='';this.onChange();return detail;
  }
  review(){
    if(this.busy)throw Error('A submission is in progress.');
    const snapshot=this.detail?.snapshot;
    buildRequest(snapshot,snapshot,this.draft,this.now());
    this.binding={...snapshot};this.step='review';this.error='';this.onChange();
  }
  async submit(){
    if(this.busy)throw Error('A submission is already in progress.');
    const id=this.detail?.case_id;
    const body=buildRequest(this.binding,this.detail?.snapshot,this.draft,this.now());
    const signature=JSON.stringify([id,body]);
    if(this.completed.has(signature))throw Error('This proposal is already recorded. Refresh its status.');
    const key=this.pending.get(signature) || newKey();this.pending.set(signature,key);
    this.busy=true;this.error='';this.onChange();
    try {
      const freshResponse=await this.api(`/cases/${encodeURIComponent(id)}`);
      const fresh=freshResponse.case || freshResponse;
      if(fresh.case_id!==id || fresh.snapshot?.case_id!==id)throw Error('The response does not match the selected case.');
      this.detail=fresh;this.checkedAt=new Date(this.now()).toISOString();this.statusConfirmed=true;
      buildRequest(this.binding,fresh.snapshot,this.draft,this.now());
      const response=await this.api(`/cases/${encodeURIComponent(id)}/decisions`,{method:'POST',body,idempotencyKey:key});
      const result=response.case || response,latest=result?.decisions?.at(-1);
      if(result?.case_id!==id || !sameSnapshot(result.snapshot,this.binding) || !boundRecord(latest,result.snapshot) || latest.action?.type!=='reschedule_delivery' || dateValue(latest.action.slot_start)!==dateValue(body.action.slot_start) || dateValue(latest.action.slot_end)!==dateValue(body.action.slot_end) || latest.action.address_change!==false || JSON.stringify([...(latest.evidence_event_ids || [])].sort())!==JSON.stringify([...body.evidence_event_ids].sort()))throw Error('The submission result could not be verified. Retry this unchanged request to recover its result.');
      this.savedOutcome={...latest,action:{...latest.action},evidence_event_ids:[...latest.evidence_event_ids]};
      this.completed.add(signature);this.pending.delete(signature);this.step='status';this.statusConfirmed=false;
      // A replay is an immutable submission receipt, not a fresh case projection.
      try {
        const currentResponse=await this.api(`/cases/${encodeURIComponent(id)}`),current=currentResponse.case || currentResponse;
        if(current?.case_id!==id || current.snapshot?.case_id!==id || !validSnapshot(current.snapshot))throw Error('The response does not match the selected case.');
        this.detail=current;this.checkedAt=new Date(this.now()).toISOString();this.statusConfirmed=true;
      } catch(error){this.error=`Preference saved, but current status refresh failed: ${error.message || 'Connection unavailable'}`;}
      return result;
    } catch(error){
      if(error.status===409){
        try {
          const response=await this.api(`/cases/${encodeURIComponent(id)}`),current=response.case || response;
          if(current.case_id===id && current.snapshot?.case_id===id && validSnapshot(current.snapshot)){this.detail=current;this.checkedAt=new Date(this.now()).toISOString();}
        } catch { /* Preserve the original conflict and draft if refresh also fails. */ }
      }
      this.error=error.message || 'The request failed. Your draft is retained.';throw error;
    }
    finally{this.busy=false;this.onChange();}
  }
}
