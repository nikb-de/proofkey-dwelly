import {CoordinationController,coordinationView,coordinationEvidence,commandLabel,buildCoordinationCommand,reviewBinding} from './coordination.js';

const text=value=>String(value ?? 'Not recorded');
const human=value=>text(value).replaceAll('_',' ');
function node(tag,value,className){const e=document.createElement(tag);if(value!==undefined)e.textContent=text(value);if(className)e.className=className;return e;}
function fact(list,label,value){const row=node('div');row.append(node('dt',label),node('dd',value));list.append(row);}
function termsBlock(title,terms){
  const section=node('section',undefined,'coordination-terms');section.append(node('h4',title));
  const list=node('dl',undefined,'coordination-facts');
  fact(list,'Window starts',terms.slot_start);fact(list,'Window ends',terms.slot_end);
  fact(list,'Handover',human(terms.handover));fact(list,'Attendance required',terms.recipient_present===null?'Unknown':terms.recipient_present?'Recipient must attend':'Recipient attendance not required');
  fact(list,'Charge (minor units)',terms.charge?.amount_minor===null?'Unknown':`${terms.charge?.amount_minor} ${terms.charge?.currency || '(currency not specified)'}`);
  section.append(list);return section;
}
function field(form,label,id,value,{type='text',placeholder='',maxLength}={}){
  const wrapper=node('label',label),input=node(type==='textarea'?'textarea':'input');input.id=id;if(type!=='textarea')input.type=type;input.value=value ?? '';input.placeholder=placeholder;if(maxLength)input.maxLength=maxLength;wrapper.append(input);form.append(wrapper);return input;
}
function select(form,label,id,choices,value){const wrapper=node('label',label),input=node('select');input.id=id;for(const [key,title] of choices){const option=node('option',title);option.value=key;input.append(option);}input.value=value ?? '';wrapper.append(input);form.append(wrapper);return input;}
function check(parent,label,id,checked=false){const wrapper=node('label',undefined,'check'),input=node('input');input.type='checkbox';input.id=id;input.checked=checked;wrapper.append(input,node('span',label));parent.append(wrapper);return input;}

export function createCoordinationPanel({root,session,onMutation=async()=>{}}){
  const controller=new CoordinationController(session);let status='',statusCase=null;
  async function perform(action){
    const id=session.selectedId;status='';statusCase=id;
    try{await action();if(session.selectedId===id)status='Local coordination record saved. No carrier message was sent; physical delivery remains unconfirmed.';await onMutation();}
    catch(error){if(session.selectedId===id)status=`${error.message}. Your draft is retained. Review the current snapshot before a new command.`;}
    finally{render();}
  }
  function render(){
    root.replaceChildren();const detail=session.detail;if(!detail)return;
    const view=coordinationView(detail),state=view.state,draft=session.getDraft('coordination'),pending=controller.pending();
    root.className='card coordination-card';root.dataset.phase=state?.phase || 'not_initialized';
    const heading=node('div',undefined,'section-heading'),title=node('div');title.append(node('p','DELIVERY COORDINATION','eyebrow'),node('h3','Terms & booking review'));heading.append(title,node('span',human(state?.phase || 'not initialized'),'tag'));root.append(heading);
    root.append(node('p','Local records only. Requests are not sent to a carrier. A local readback is not proof of physical delivery.','hint coordination-boundary'));
    const facts=node('dl',undefined,'coordination-facts');fact(facts,'Snapshot',`Revision ${detail.snapshot.revision} · workflow version ${state?.version || 0}`);fact(facts,'Workflow freshness',human(view.freshness));
    if(state)fact(facts,'Declared Dispatch',state.dispatch_actor_id);root.append(facts);
    if(view.freshness==='stale')root.append(node('p','Source evidence changed since the last workflow record. Review the current evidence; the next command uses the current snapshot.','coordination-caution'));
    if(state?.original_booking){const original=node('details');original.append(node('summary',`Original booking · ${state.original_booking.booking_id}`),termsBlock('Original recorded terms',state.original_booking.terms));root.append(original);}
    if(state?.offer){root.append(termsBlock('Current offered terms',state.offer.terms));const ids=node('dl',undefined,'coordination-facts');fact(ids,'Offer ID',state.offer.offer_id);fact(ids,'Terms hash',state.offer.terms_hash);const bookingConsent=state.consent && ['booking_pending','booking_confirmed'].includes(state.phase) && state.consent.offer_id===state.offer.offer_id && state.consent.terms_hash===state.offer.terms_hash;fact(ids,'Consent',state.consent?bookingConsent?'Recorded for this local booking':view.consentFresh?'Current for this exact offer and snapshot':'Stale — new sourced consent required':'Not recorded');if(state.consent)fact(ids,'Consent evidence',(state.consent.evidence_event_ids || []).join(', '));root.append(ids);}
    if(state?.pending_request){const section=node('section',undefined,'coordination-request');section.append(node('h4','Pending local request'),node('p',`${human(state.pending_request.kind)} · ${human(state.pending_request.status)}`),node('p',`Request ID: ${state.pending_request.request_id}`,'hint'));if(state.pending_request.terms_hash)section.append(node('p',`Terms hash: ${state.pending_request.terms_hash}`,'hint'));section.append(node('p','Awaiting a separately supplied Dispatch readback. No transmission or delivery is established.','hint'));root.append(section);}
    if(state?.operation_receipts?.length){const receipts=node('details');receipts.append(node('summary',`Local operation receipts · ${state.operation_receipts.length}`));for(const receipt of state.operation_receipts){const item=node('article',undefined,'coordination-request');item.append(node('h4',`${human(receipt.kind)} · ${human(receipt.status)}`),node('p',`Request ID: ${receipt.request_id}`),node('p',`Readback evidence: ${(receipt.evidence_event_ids || []).join(', ')}`),node('p',`Recorded: ${receipt.confirmed_at}`),node('p','Confirmed locally. Physical delivery not confirmed.','hint'));receipts.append(item);}root.append(receipts);}
    const message=node('p',statusCase===session.selectedId?status:'','hint');message.id='coordination-status';message.setAttribute('role','status');root.append(message);
    if(pending){
      const notice=node('section',undefined,'coordination-caution');notice.append(node('h4',controller.busy?'Saving exact request…':'Request outcome uncertain'),node('p','Keep the original body and idempotency key. Retry sends the exact saved request, even if the snapshot changes.'));
      const details=node('details');details.append(node('summary','Exact saved request'),node('pre',JSON.stringify(pending.body,null,2)));if(pending.key)details.append(node('p',`Idempotency key: ${pending.key}`,'hint'));notice.append(details);
      const retry=node('button','Retry exact request','secondary');retry.id='coordination-retry';retry.type='button';retry.disabled=controller.busy || session.busy;retry.addEventListener('click',()=>perform(()=>controller.retry()));notice.append(retry);root.append(notice);return;
    }
    if(!view.commands.length){root.append(node('p','This workflow is closed. Review its recorded evidence and local receipts.','hint'));return;}
    let formHost=root;if(!state){formHost=node('details');formHost.append(node('summary','Set up delivery terms coordination'));root.append(formHost);}
    const form=node('form',undefined,'stack coordination-form');form.id='coordination-form';formHost.append(form);
    const command=select(form,'Explicit operator command','coordination-command',view.commands.map(c=>[c,commandLabel(c)]),view.commands.includes(draft.command)?draft.command:view.commands[0]);
    const action=command.value;
    if(action==='initialize'){
      select(form,'Declared Dispatch participant','coordination-dispatch',[['','Select a declared participant'],...view.dispatchActors.map(id=>[id,id])],draft.dispatch_actor_id);
      if(!view.dispatchActors.length)form.append(node('p','No distinct Dispatch participant is declared. Create a case with its Dispatch ID to initialize this workflow.','coordination-caution'));
      field(form,'Original booking ID','coordination-booking',draft.booking_id,{maxLength:64});
    }
    if(['initialize','record_offer'].includes(action)){
      const terms=draft.terms || {};const group=node('fieldset',undefined,'coordination-terms-form');group.append(node('legend',action==='initialize'?'Original source terms':'Complete offered terms'));form.append(group);
      field(group,'Window starts (with UTC offset)','coordination-start',terms.slot_start,{placeholder:'2030-06-03T10:00:00+00:00'});
      field(group,'Window ends (with UTC offset)','coordination-end',terms.slot_end,{placeholder:'2030-06-03T12:00:00+00:00'});
      select(group,'Handover / required attendance','coordination-handover',[['','Select the source requirement'],...(action==='initialize'?[['unspecified','Unknown in original source']]:[]),['recipient_only','Recipient only · recipient must attend'],['concierge_allowed','Concierge allowed · recipient need not attend']],terms.handover || (action==='initialize'?'unspecified':''));
      field(group,'Charge in minor units (for example 1250 = 12.50)','coordination-amount',terms.charge?.amount_minor,{type:'number'});group.querySelector('#coordination-amount').min='0';group.querySelector('#coordination-amount').step='1';
      field(group,'Currency (three uppercase letters)','coordination-currency',terms.charge?.currency,{placeholder:'GBP',maxLength:3});
      group.append(node('p',action==='initialize'?'Leave charge and currency empty only when the original source does not state them.':'Enter zero explicitly for no charge. Currency may be empty only for zero. Attendance describes a requirement, not observed presence.','hint'));
    }
    if(action==='escalate')field(form,'Reason for escalation','coordination-reason',draft.reason,{type:'textarea',maxLength:2048});
    if(!['initialize','request_booking'].includes(action)){
      const evidence=node('fieldset');evidence.append(node('legend','Review source evidence'));const selected=new Set(draft.evidence_event_ids || []);const excluded=node('details');let excludedCount=0;
      for(const {event,eligible,reason} of coordinationEvidence(detail,action)){
        const wrapper=node('label',undefined,'check coordination-evidence'),input=node('input');input.type='checkbox';input.name='coordination-evidence';input.value=event.event_id;input.checked=eligible && selected.has(event.event_id);input.disabled=!eligible;
        const content=node('span');content.append(node('strong',`${event.event_id} · ${event.sender_id || 'internal'} → ${(event.recipient_ids || []).join(', ')}`));if(event.channel!=='internal')content.append(node('span',event.text || '(No source text)','coordination-source-text'));
        if(reason)content.append(node('span',reason,'hint'));wrapper.append(input,content);if(eligible)evidence.append(wrapper);else{excluded.append(wrapper);excludedCount++;}
      }
      if(excludedCount){excluded.prepend(node('summary',`Excluded evidence · ${excludedCount}`));evidence.append(excluded);}
      if(!detail.snapshot.events.length)evidence.append(node('p','Add source messages before recording this command.','hint'));form.append(evidence);
    }
    if(action!=='initialize'){
      const model=node('details');model.open=Boolean(draft.model_run_id);model.append(node('summary','Optional reviewed model context'));
      const picker=select(model,'Current succeeded model run','coordination-model',[['','No model context'],...view.modelJobs.map(job=>[job.run_id,`${job.run_id} · ${human(job.candidate.state)}`])],draft.model_run_id);
      model.append(node('p','Advisory only. Choose the command and its fields yourself. No model prose is converted into an action.','hint'));
      const proposal=node('pre',undefined,'coordination-model-proposal');proposal.id='coordination-model-proposal';model.append(proposal);
      field(model,'Human review note (required when attaching a run)','coordination-model-note',draft.model_review_note,{type:'textarea',maxLength:1000});form.append(model);
      const showModel=()=>{const job=view.modelJobs.find(job=>job.run_id===picker.value);proposal.textContent=job?JSON.stringify(job.candidate,null,2):'No model run attached.';};picker.addEventListener('change',showModel);showModel();
    }
    const preview=node('details');preview.append(node('summary','Exact command preview'));const payload=node('pre');payload.id='coordination-preview';preview.append(payload);form.append(preview);
    const reviewed=check(form,'I reviewed this exact command, complete terms, identifiers and selected original source evidence. This saves a local operator record.','coordination-reviewed',draft.reviewed===true && draft.review_binding===reviewBinding(detail,draft));
    const validation=node('p',undefined,'hint');validation.id='coordination-validation';form.append(validation);
    const submit=node('button',commandLabel(action),'primary');submit.type='submit';submit.id='coordination-submit';form.append(submit);
    function capture(){
      const val=id=>form.querySelector(`#${id}`)?.value;
      const value={...session.getDraft('coordination'),command:command.value,reviewed:reviewed.checked};
      if(val('coordination-dispatch')!==undefined)value.dispatch_actor_id=val('coordination-dispatch');
      if(val('coordination-booking')!==undefined)value.booking_id=val('coordination-booking');
      if(val('coordination-start')!==undefined){const handover=val('coordination-handover'),amount=val('coordination-amount');value.terms={slot_start:val('coordination-start'),slot_end:val('coordination-end'),handover,recipient_present:handover==='recipient_only'?true:handover==='concierge_allowed'?false:null,charge:{amount_minor:amount===''?null:Number(amount),currency:val('coordination-currency') || null}};}
      if(val('coordination-reason')!==undefined)value.reason=val('coordination-reason');
      value.evidence_event_ids=[...form.querySelectorAll('[name="coordination-evidence"]:checked')].map(input=>input.value);
      value.model_run_id=val('coordination-model') || '';value.model_review_note=val('coordination-model-note') || '';
      value.review_binding=reviewed.checked?reviewBinding(detail,value):null;
      session.setDraft('coordination',value);return value;
    }
    function updatePreview(value){
      let error='';try{payload.textContent=JSON.stringify(buildCoordinationCommand(detail,{...value,reviewed:true,review_binding:reviewBinding(detail,value)}),null,2);}catch(e){error=e.message;payload.textContent='Complete the required fields and source selection to preview the command.';}
      validation.textContent=error;submit.disabled=Boolean(error) || !value.reviewed || value.review_binding!==reviewBinding(detail,value) || session.busy || controller.busy;
    }
    command.addEventListener('change',()=>{const value=capture();session.setDraft('coordination',{...value,reviewed:false});render();});
    form.addEventListener('input',event=>{if(event.target!==reviewed)reviewed.checked=false;updatePreview(capture());});
    form.addEventListener('change',event=>{if(event.target!==command){if(event.target!==reviewed)reviewed.checked=false;updatePreview(capture());}});
    form.addEventListener('submit',event=>{event.preventDefault();const value=capture();perform(()=>controller.submit(value));});
    for(const input of form.querySelectorAll('input,textarea,select'))if(session.busy || controller.busy)input.disabled=true;
    updatePreview({...draft,command:action});
  }
  return {render,controller};
}
