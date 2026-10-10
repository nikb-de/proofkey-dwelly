import {modelStatusView} from './session.js';

const phases={booked:['request_cancellation','escalate'],cancellation_pending:['confirm_cancellation','escalate'],awaiting_terms:['record_offer','escalate'],awaiting_consent:['record_offer','record_consent','escalate'],ready_to_book:['record_offer','record_consent','request_booking','escalate'],booking_pending:['confirm_booking','escalate'],booking_confirmed:[],escalated:[]};
export const commandLabel=command=>({initialize:'Record original booking',request_cancellation:'Request local cancellation',confirm_cancellation:'Record cancellation readback',record_offer:'Record offered terms',record_consent:'Record sourced customer consent',request_booking:'Request local booking',confirm_booking:'Record booking readback',escalate:'Escalate for review'}[command] || command);
export function allowedCommands(detail){return detail.coordination?[...(phases[detail.coordination.phase] || [])]:['initialize'];}
export function reviewBinding(detail,draft={}){return JSON.stringify([detail.case_id,detail.snapshot.revision,detail.snapshot.snapshot_hash,detail.coordination?.version || 0,detail.coordination?.offer?.offer_id,detail.coordination?.offer?.terms_hash,detail.coordination?.pending_request?.request_id,draft.command || '',draft.dispatch_actor_id || '',draft.booking_id || '',draft.terms || null,draft.evidence_event_ids || [],draft.reason || '',draft.model_run_id || '',draft.model_review_note || '']);}
export function coordinationView(detail){
  const state=detail.coordination,snapshot=detail.snapshot;
  return {state,commands:allowedCommands(detail),freshness:!state?'not_initialized':state.revision===snapshot.revision && state.snapshot_hash===snapshot.snapshot_hash?'current':'stale',
    consentFresh:Boolean(state?.consent && state.offer && state.consent.offer_id===state.offer.offer_id && state.consent.terms_hash===state.offer.terms_hash && state.consent.created_revision===snapshot.revision),
    dispatchActors:(snapshot.participants || []).filter(id=>id!==snapshot.links.customer_id && id!==snapshot.links.operator_id),
    modelJobs:(detail.model_jobs || []).filter(job=>job.status==='succeeded' && modelStatusView(job,snapshot).current && job.candidate)};
}
export function coordinationEvidence(detail,command){
  const state=detail.coordination,snapshot=detail.snapshot;
  const customer=['request_cancellation','record_consent'].includes(command);
  const actor=command==='escalate'?null:customer?snapshot.links.customer_id:state?.dispatch_actor_id;
  const cutoff=command==='record_consent'?state?.offer?.created_revision:['confirm_cancellation','confirm_booking'].includes(command)?state?.pending_request?.created_revision:null;
  const used=new Set(command==='escalate'?[]:(state?.audit_history || []).flatMap(a=>a.evidence_event_ids || []));
  const tokens=command==='confirm_booking'?[state?.pending_request?.request_id,state?.pending_request?.terms_hash]:command==='confirm_cancellation'?[state?.pending_request?.request_id]:[];
  const tokenPresent=(text,token)=>Boolean(token && new RegExp(`(?<![A-Za-z0-9_-])${token.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')}(?![A-Za-z0-9_-])`).test(text || ''));
  return snapshot.events.map((event,index)=>{
    let reason='';
    if(event.kind!=='message' || event.channel==='internal' || !event.recipient_ids?.includes(snapshot.links.operator_id))reason='Needs a source message addressed to the operator';
    else if(actor && event.sender_id!==actor)reason=`Needs a message from ${actor}`;
    else if(used.has(event.event_id))reason='Already used by a workflow command';
    else if(cutoff!=null && index+1<=cutoff)reason='Received before the current offer or request';
    else if(tokens.some(token=>!tokenPresent(event.text,token)))reason='Exact current request ID and booking hash must appear in the source';
    return {event,eligible:!reason,reason};
  });
}
function required(value,message){if(!value)throw Error(message);}
export function validateTerms(terms,original=false){
  required(terms && typeof terms==='object','Enter the complete terms.');
  const aware=value=>typeof value==='string' && /(?:Z|[+-]\d{2}:\d{2})$/.test(value) && Number.isFinite(Date.parse(value));
  required(aware(terms.slot_start) && aware(terms.slot_end),'Slot timestamps need a UTC offset, for example +00:00.');
  const duration=Date.parse(terms.slot_end)-Date.parse(terms.slot_start);
  required(duration>0 && duration<=8*60*60*1000,'The delivery window must be positive and at most eight hours.');
  required(original && terms.handover==='unspecified' && terms.recipient_present===null || terms.handover==='recipient_only' && terms.recipient_present===true || terms.handover==='concierge_allowed' && terms.recipient_present===false,'Select a handover rule and its required attendance.');
  const amount=terms.charge?.amount_minor,currency=terms.charge?.currency;
  required(original && amount===null && currency===null || Number.isInteger(amount) && amount>=0 && (typeof currency==='string' && /^[A-Z]{3}$/.test(currency) || amount===0 && currency===null),'Enter a nonnegative charge in minor units and its three-letter currency. Unknown charge is only allowed for the original booking.');
  return {slot_start:terms.slot_start,slot_end:terms.slot_end,handover:terms.handover,recipient_present:terms.recipient_present,charge:{amount_minor:amount,currency}};
}
export function buildCoordinationCommand(detail,draft){
  const command=draft.command,state=detail.coordination,view=coordinationView(detail);
  required(draft.reviewed===true,'Confirm you reviewed the exact terms, identifiers and source evidence.');
  required(draft.review_binding===reviewBinding(detail,draft),'The snapshot, workflow or command fields changed. Review the exact current command again.');
  required(view.commands.includes(command),'This command is not available in the current phase.');
  const body={command,expected_revision:detail.snapshot.revision,snapshot_hash:detail.snapshot.snapshot_hash,expected_workflow_version:state?.version || 0};
  if(command==='initialize'){
    required(view.dispatchActors.includes(draft.dispatch_actor_id),'Choose a declared Dispatch participant distinct from customer and operator.');
    required(/^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/.test(draft.booking_id || ''),'Enter the original booking ID.');
    body.dispatch_actor_id=draft.dispatch_actor_id;body.original_booking={booking_id:draft.booking_id,terms:validateTerms(draft.terms,true)};
  }
  if(command==='record_offer')body.terms=validateTerms(draft.terms);
  if(!['initialize','request_booking'].includes(command)){
    const ids=draft.evidence_event_ids || [],eligible=new Set(coordinationEvidence(detail,command).filter(row=>row.eligible).map(row=>row.event.event_id));
    required(ids.length>0 && ids.length<=128 && new Set(ids).size===ids.length && ids.every(id=>eligible.has(id)),'Select qualifying source evidence for this command.');
    body.evidence_event_ids=[...ids];
  }
  if(['record_consent','request_booking'].includes(command)){
    required(state?.offer,'A current offer is required.');body.offer_id=state.offer.offer_id;body.terms_hash=state.offer.terms_hash;
  }
  if(command==='request_booking')required(view.consentFresh,'Customer consent is stale or missing. Record current sourced consent first.');
  if(['confirm_cancellation','confirm_booking'].includes(command)){
    required(state?.pending_request,'A pending request is required.');body.request_id=state.pending_request.request_id;
    if(command==='confirm_booking')body.terms_hash=state.pending_request.terms_hash;
  }
  if(command==='escalate'){required(typeof draft.reason==='string' && draft.reason.trim() && draft.reason.length<=2048,'Enter an escalation reason (up to 2048 characters).');body.reason=draft.reason;}
  if(draft.model_run_id || draft.model_review_note){
    required(command!=='initialize','Initialization does not accept model context.');
    required(typeof draft.model_review_note==='string' && draft.model_review_note.trim() && draft.model_review_note.length<=1000,'Add a human model review note (up to 1000 characters).');
    const job=view.modelJobs.find(job=>job.run_id===draft.model_run_id);
    required(job,'Choose a current succeeded model run.');
    required((body.evidence_event_ids || []).every(id=>job.candidate.evidence_event_ids?.includes(id)),'Selected source evidence must be covered by the reviewed model proposal.');
    body.model_run_id=draft.model_run_id;body.model_review_note=draft.model_review_note;
  }
  return body;
}
export class CoordinationController {
  constructor(session){this.session=session;this.attempts=new Map();this.busy=false;}
  pending(){return this.attempts.get(this.session.selectedId);}
  async submit(draft){
    required(!this.busy && !this.session.busy,'A request is already in progress.');
    required(!this.pending(),'Resolve the uncertain request with the exact retry before preparing another command.');
    const body=buildCoordinationCommand(this.session.detail,draft);
    this.attempts.set(this.session.selectedId,{body:structuredClone(body)});
    return this.send();
  }
  async retry(){required(this.pending(),'No uncertain request is available to retry.');return this.send();}
  async send(){
    required(!this.busy && !this.session.busy,'A request is already in progress.');
    const id=this.session.selectedId,attempt=this.pending();this.busy=true;
    const signature=`${id}:coordination:${JSON.stringify(attempt.body)}`;
    // mutate removes its key after POST succeeds, before the follow-up GET. Keep
    // that same key if readback fails, so an exact replay cannot append twice.
    if(attempt.key)this.session.pending.set(signature,attempt.key);
    try{const request=this.session.mutate('coordination',attempt.body);attempt.key ||= this.session.pending.get(signature);const result=await request;this.attempts.delete(id);const draft=this.session.drafts.get(`${id}:coordination`) || {};this.session.drafts.set(`${id}:coordination`,{...draft,reviewed:false,model_run_id:'',model_review_note:''});return result;}
    catch(error){if(error.status>=400 && error.status<500){this.attempts.delete(id);this.session.pending.delete(signature);}else if(attempt.key)this.session.pending.set(signature,attempt.key);throw error;}
    finally{this.busy=false;}
  }
}
