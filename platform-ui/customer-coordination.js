const validHash=value=>typeof value==='string' && /^[a-f0-9]{64}$/.test(value);
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const key=()=>globalThis.crypto?.randomUUID?.() || `accept-${Date.now()}-${Math.random().toString(16).slice(2)}`;
const titles={booked:'Original booking recorded',cancellation_pending:'Cancellation awaiting local readback',awaiting_terms:'Waiting for complete delivery terms',awaiting_consent:'Review your delivery offer',ready_to_book:'Acceptance recorded locally',booking_pending:'Booking awaiting local readback',booking_confirmed:'Booking confirmed locally',escalated:'Operator attention required'};
const bindingFor=detail=>({command:'record_local_acceptance',expected_revision:detail.snapshot.revision,snapshot_hash:detail.snapshot.snapshot_hash,expected_workflow_version:detail.coordination.version,offer_id:detail.coordination.offer?.offer_id,terms_hash:detail.coordination.offer?.terms_hash,acknowledged:true});
const completeTerms=t=>Boolean(t && Number.isFinite(Date.parse(t.slot_start)) && Number.isFinite(Date.parse(t.slot_end)) && Date.parse(t.slot_end)>Date.parse(t.slot_start) && ((t.handover==='recipient_only' && t.recipient_present===true) || (t.handover==='concierge_allowed' && t.recipient_present===false)) && Number.isInteger(t.charge?.amount_minor) && t.charge.amount_minor>=0 && (t.charge.currency===null?t.charge.amount_minor===0:/^[A-Z]{3}$/.test(t.charge.currency)));

export function coordinationCustomerView(detail,now=Date.now()) {
  const c=detail?.coordination,s=detail?.snapshot;if(!c || !s)return null;
  const freshness=c.revision===s.revision && c.snapshot_hash===s.snapshot_hash?'current':'stale';
  const offer=c.offer,terms=offer?.terms || c.original_booking?.terms;
  const consentCurrent=Boolean(c.consent && offer && c.consent.offer_id===offer.offer_id && c.consent.terms_hash===offer.terms_hash && c.consent.created_revision===s.revision);
  const consentBound=Boolean(c.consent && offer && c.consent.offer_id===offer.offer_id && c.consent.terms_hash===offer.terms_hash);
  const consentLabel=!c.consent?'Not yet recorded':consentBound && ['booking_pending','booking_confirmed'].includes(c.phase)?'Recorded for this local booking':consentCurrent && c.phase==='ready_to_book'?'Fresh for a new booking request':consentCurrent?'Recorded for this offer':'Recorded; fresh acceptance needed before a new booking request';
  return {phase:c.phase,title:titles[c.phase] || 'Delivery coordination',terms,offer,freshness,consent:c.consent,consentCurrent,consentLabel,pending:c.pending_request,bookingReceipt:(c.operation_receipts || []).filter(r=>r.kind==='booking' && r.status==='confirmed_locally').at(-1) || null,
    canAccept:c.phase==='awaiting_consent' && freshness==='current' && completeTerms(offer?.terms) && validHash(offer?.terms_hash) && typeof offer?.offer_id==='string' && Date.parse(offer.terms.slot_start)>now};
}

export class CustomerCoordinationSession {
  constructor(api,{now=Date.now,onChange=()=>{},newKey=key}={}) {Object.assign(this,{api,now,onChange,newKey,detail:null,binding:null,pending:null,busy:false,acknowledged:false,error:'',savedOutcome:null,statusConfirmed:true,checkedAt:null,generation:0});}
  get view(){return coordinationCustomerView(this.detail,this.now());}
  get reviewChanged(){return !this.detail || !this.binding || !same(this.binding,bindingFor(this.detail));}
  get canSubmit(){return !this.busy && Boolean(this.pending || (this.acknowledged && this.view?.canAccept && !this.reviewChanged && !this.savedOutcome));}
  accept(detail){
    if(!detail || detail.case_id!==detail.snapshot?.case_id || !Number.isInteger(detail.snapshot.revision) || !validHash(detail.snapshot.snapshot_hash) || detail.coordination?.case_id!==detail.case_id || !Number.isInteger(detail.coordination.version))throw Error('The coordination response does not match the selected case.');
    if(this.detail && this.detail.case_id!==detail.case_id)throw Error('The response does not match the selected case.');
    if(this.savedOutcome){
      const saved=this.savedOutcome,c=detail.coordination,s=detail.snapshot;
      const audit=saved.audit_history?.find(item=>item.command==='record_local_acceptance' && item.version===saved.version && item.revision===saved.revision);
      const historyMatches=typeof audit?.audit_id==='string' && audit.audit_id.length>0 && c.audit_history?.some(item=>item.audit_id===audit.audit_id && item.command===audit.command && item.version===audit.version && item.revision===audit.revision);
      const sameAcceptance=c.revision===saved.revision && c.snapshot_hash===saved.snapshot_hash && c.consent?.offer_id===saved.consent.offer_id && c.consent?.terms_hash===saved.consent.terms_hash && c.consent?.created_revision===saved.consent.created_revision && c.consent?.mode==='local_preview_simulation' && c.consent?.authenticated===false;
      if(s.revision<saved.revision || (s.revision===saved.revision && s.snapshot_hash!==saved.snapshot_hash) || c.version<saved.version || c.revision<saved.revision || c.revision>s.revision || (c.revision===s.revision && c.snapshot_hash!==s.snapshot_hash) || (c.version===saved.version?!sameAcceptance:!historyMatches)){
        this.statusConfirmed=false;
        throw Error('The refreshed case does not match the saved acceptance receipt or its later audit history. Current status remains unverified.');
      }
    }
    this.detail=detail;this.checkedAt=new Date(this.now()).toISOString();this.statusConfirmed=true;
    if(!this.binding)this.binding=bindingFor(detail);
  }
  async load(id){
    if(this.busy)throw Error('A submission is in progress.');
    const generation=++this.generation;
    const response=await this.api(`/cases/${encodeURIComponent(id)}`),detail=response.case || response;
    if(generation!==this.generation)return;
    if(detail?.case_id!==id)throw Error('The response does not match the selected case.');
    this.accept(detail);this.error='';this.onChange();return detail;
  }
  reviewCurrent(){if(this.busy || this.pending)throw Error('Resolve the pending submission before starting another review.');this.binding=bindingFor(this.detail);this.acknowledged=false;this.savedOutcome=null;this.error='';this.onChange();}
  setAcknowledged(value){if(this.busy || this.pending)throw Error('A submission is pending.');this.acknowledged=value===true;this.error='';this.onChange();}
  async submit(){
    if(this.busy)throw Error('A submission is already in progress.');
    if(!this.pending){
      if(this.savedOutcome)throw Error('This acceptance is already recorded. Refresh current status.');
      if(!this.acknowledged)throw Error('Explicitly acknowledge the complete terms and local-preview limitation.');
      if(this.reviewChanged || !this.view?.canAccept)throw Error('The offer changed or is no longer current. Review current terms before accepting.');
      this.pending=Object.freeze({caseId:this.detail.case_id,body:Object.freeze({...this.binding}),idempotencyKey:this.newKey()});
    }
    const request=this.pending;this.generation++;this.busy=true;this.error='';this.onChange();
    try{
      const response=await this.api(`/cases/${encodeURIComponent(request.caseId)}/coordination`,{method:'POST',body:request.body,idempotencyKey:request.idempotencyKey});
      const result=response.coordination,b=request.body;
      if(result?.case_id!==request.caseId || result.phase!=='ready_to_book' || result.version!==b.expected_workflow_version+1 || result.mode!=='local_sandbox' || result.external_effects!==0 || result.physical_delivery!=='not_confirmed' || result.offer?.offer_id!==b.offer_id || result.offer?.terms_hash!==b.terms_hash || result.consent?.offer_id!==b.offer_id || result.consent?.terms_hash!==b.terms_hash || result.consent?.created_revision!==result.revision || result.consent?.mode!=='local_preview_simulation' || result.consent?.authenticated!==false || result.revision!==b.expected_revision+2 || !validHash(result.snapshot_hash))throw Error('The acceptance result could not be verified. Retry the unchanged request to recover its receipt.');
      this.savedOutcome=structuredClone(result);this.pending=null;this.acknowledged=false;this.statusConfirmed=false;
      try{const fresh=await this.api(`/cases/${encodeURIComponent(request.caseId)}`);if((fresh.case || fresh)?.case_id!==request.caseId)throw Error('Mismatched case response');this.accept(fresh.case || fresh);}catch(error){this.error=`Acceptance recorded locally, but current status refresh failed: ${error.message || 'Connection unavailable'}`;}
      return result;
    }catch(error){
      if(error.status>=400 && error.status<500){this.pending=null;this.acknowledged=false;if(error.status===409){try{const fresh=await this.api(`/cases/${encodeURIComponent(request.caseId)}`);this.accept(fresh.case || fresh);}catch{ /* Retain the original conflict and reviewed binding. */ }}}
      this.error=error.message || 'Connection unavailable. Retry the unchanged local acceptance.';throw error;
    }finally{this.busy=false;this.onChange();}
  }
}

const node=(tag,text,className)=>{const element=document.createElement(tag);if(text!==undefined)element.textContent=text;if(className)element.className=className;return element;};
const row=(list,label,value,note)=>{const wrapper=node('div',undefined,'summary-row'),dd=node('dd',value);wrapper.append(node('dt',label),dd);if(note)dd.append(node('small',note));list.append(wrapper);};
const date=value=>{const d=new Date(value);return Number.isFinite(d.getTime())?d.toLocaleString('en-GB',{dateStyle:'medium',timeStyle:'short',timeZone:'UTC'})+' UTC':'Not recorded';};
function chargeLabel(charge){
  if(charge?.amount_minor===null || !charge)return 'Not recorded';
  if(charge.amount_minor===0)return `No charge · 0 minor units · ${charge.currency || 'currency not specified'}`;
  let formatted='';
  try{const formatter=new Intl.NumberFormat('en-GB',{style:'currency',currency:charge.currency});formatted=formatter.format(charge.amount_minor / 10 ** formatter.resolvedOptions().maximumFractionDigits)+' · ';}catch{ /* Exact recorded units remain visible for unrecognized currencies. */ }
  return `${formatted}${charge.amount_minor.toLocaleString('en-GB')} minor units · ${charge.currency}`;
}

export function renderCustomerCoordination(parent,session,{onAction,loading=false,error=''}={}) {
  const view=session.view,c=session.detail.coordination;
  const act=handler=>()=>onAction(handler);
  const button=(text,handler,style='quiet')=>{const b=node('button',text,style);b.type='button';b.disabled=loading || session.busy;b.addEventListener('click',act(handler));return b;};
  const intro=node('div',undefined,'intro');intro.append(node('div','Delivery coordination','eyebrow'),node('h1',session.statusConfirmed?view.title:'Acceptance saved; verify current status'),node('p','Review the recorded delivery terms and local coordination status.'));parent.append(intro);
  const card=node('section',undefined,'card coordination-customer');card.id='customer-coordination';card.dataset.phase=view.phase;
  card.append(node('div','Operator-assisted local preview. Customer identity is not authenticated. Acceptance below records simulated customer evidence in the local sandbox.','note'));
  if(error || session.error){const alert=node('div',error || session.error,'note error');alert.setAttribute('role','alert');card.append(alert);}
  if(!session.statusConfirmed)card.append(node('p','A local acceptance receipt was saved. Current case status is unavailable until refresh succeeds.','note pending'));
  card.append(node('h2',view.offer?(session.statusConfirmed?'Current delivery offer':'Last read delivery offer'):'Original booking terms'));
  const list=node('dl');const t=view.terms;
  if(t){row(list,'Delivery window',`${date(t.slot_start)} – ${date(t.slot_end)}`,`Recorded offsets: ${t.slot_start} – ${t.slot_end}`);row(list,'Handover',t.handover==='recipient_only'?'Recipient only':t.handover==='concierge_allowed'?'Concierge allowed':'Not specified');row(list,'Required attendance',t.recipient_present===true?'Recipient must be present':t.recipient_present===false?'Recipient presence not required':'Not specified','This is an attendance requirement, not observed physical presence.');row(list,'Full surcharge',chargeLabel(t.charge));}else row(list,'Delivery terms','No complete offer recorded');
  row(list,'Record freshness',!session.statusConfirmed?'Current status unverified':view.freshness==='current'?'Current case snapshot':'Stale — source events have changed');
  row(list,'Recorded consent',view.consentLabel);
  if(view.pending)row(list,'Pending local request',`${view.pending.kind} · ${view.pending.status}`,view.pending.request_id);
  row(list,'Local booking receipt',view.bookingReceipt?'Confirmed locally':'No confirmed local booking receipt',view.bookingReceipt?.request_id);
  row(list,'Physical delivery','Not confirmed');card.append(list);
  card.append(node('p','No carrier message or external booking is sent by this preview. A local booking receipt does not confirm physical delivery.','small muted'));
  if(session.pending){card.append(node('p','The previous submission outcome is uncertain. Retry sends exactly the same terms, case revision and request key, even if newer records now exist.','note pending'));const retry=button(session.busy?'Recording local acceptance…':'Retry unchanged local acceptance',()=>session.submit(),'primary');retry.id='submit-local-acceptance';card.append(retry);}
  else if(view.canAccept && !session.reviewChanged && !session.savedOutcome){
    const label=node('label',undefined,'coordination-ack'),input=node('input');input.type='checkbox';input.id='local-acceptance-ack';input.checked=session.acknowledged;input.disabled=session.busy || loading;input.addEventListener('change',()=>session.setAcknowledged(input.checked));label.append(input,node('span','I acknowledge the complete delivery terms above and understand this records operator-assisted, simulated local acceptance, not authenticated customer consent.'));card.append(label);
    const submit=button(session.busy?'Recording local acceptance…':'Record local acceptance',()=>session.submit(),'primary');submit.id='submit-local-acceptance';submit.disabled=!session.canSubmit || loading;card.append(submit);
  }else if(session.reviewChanged && view.canAccept){card.append(node('p','The case or offer changed after your review. Review the current terms and acknowledge them again.','note pending'),button('Review current terms',()=>session.reviewCurrent(),'primary'));}
  else if(view.phase==='awaiting_consent')card.append(node('p',view.freshness==='stale'?'Source records changed. Ask the Team operator to review this stale offer.':'This offer is unavailable for local acceptance. Ask the Team operator to check the complete terms and delivery date.','note pending'));
  if(session.savedOutcome)card.append(node('p',`Saved local acceptance receipt · offer ${session.savedOutcome.consent.offer_id} · audit revision ${session.savedOutcome.consent.created_revision}`,'note'));
  card.append(button(loading?'Refreshing…':'Refresh current status',()=>session.load(session.detail.case_id)));
  const details=node('details',undefined,'technical');details.append(node('summary','Operator record details'),node('p',`Case revision ${session.detail.snapshot.revision} · workflow version ${c.version} · phase ${c.phase}`));if(view.offer)details.append(node('p',`Offer ${view.offer.offer_id}`),node('p',`Terms hash ${view.offer.terms_hash}`));details.append(node('p',`Last checked ${session.checkedAt || 'not recorded'}`));card.append(details);parent.append(card);
}
