import {createAPI} from './session.js';
import {CustomerSession,offeredWindows,buildRequest} from './customer-model.js';

const api=createAPI(),main=document.querySelector('#main');
const session=new CustomerSession(api,{onChange:render});
const timezone=Intl.DateTimeFormat().resolvedOptions().timeZone || 'browser local timezone';
let selectedId=new URLSearchParams(location.search).get('case'),cases=[],loading=true,screenError='',choice='custom';
const node=(tag,text,className)=>{const element=document.createElement(tag);if(text!==undefined)element.textContent=text;if(className)element.className=className;return element;};
const button=(text,handler,className='')=>{const element=node('button',text,className);element.type='button';element.disabled=session.busy || loading;element.addEventListener('click',handler);return element;};
const formatDate=value=>{const date=new Date(value);return Number.isFinite(date.getTime())?date.toLocaleString(undefined,{dateStyle:'medium',timeStyle:'short'}):'Not recorded';};
const windowLabel=action=>`${formatDate(action.slot_start)} – ${formatDate(action.slot_end)}`;
const toLocal=value=>{if(!value)return '';const date=new Date(value);if(!Number.isFinite(date.getTime()))return '';return new Date(date.getTime()-date.getTimezoneOffset()*60000).toISOString().slice(0,16);};
const toISO=value=>{const date=new Date(value);return value && Number.isFinite(date.getTime())?date.toISOString():'';};
async function perform(action){screenError='';try{await action();}catch(error){screenError=error.message || 'The request failed. Your draft is retained.';}render();}
function errorMessage(parent){const message=screenError || session.error;if(message){const alert=node('div',message,'note error');alert.setAttribute('role','alert');parent.append(alert);}}
function addRow(list,label,value,note){const row=node('div',undefined,'row'),dd=node('dd',value);row.append(node('dt',label),dd);if(note)dd.append(node('small',note));list.append(row);}
function caseStrip(parent){const strip=node('div',undefined,'case-strip'),info=node('div');info.append(node('span','DELIVERY CASE','eyebrow'),node('strong',session.detail.case_id),node('span',`Order ${session.detail.snapshot.links?.order_id || 'not linked'}`,'muted small'));strip.append(node('span','↗','parcel'),info);parent.append(strip);}
function intro(title,description){const header=node('div',undefined,'intro');header.append(node('div','YOUR DELIVERY WINDOW','eyebrow'),node('h1',title),node('p',description));main.append(header);}
function renderStepper(){const steps=node('ol',undefined,'stepper');['Choose window','Review','Status'].forEach((label,index)=>{const li=node('li',`${index+1}  ${label}`,index<=['choose','review','status'].indexOf(session.step)?'active':'');if(index===['choose','review','status'].indexOf(session.step))li.setAttribute('aria-current','step');steps.append(li);});main.append(steps);}
function picker(){
  intro('A better time for your delivery.','Open an existing case to review its sources and record a requested delivery window.');
  const card=node('section',undefined,'card');card.append(node('h2','Choose a case'));errorMessage(card);
  if(loading)card.append(node('p','Loading cases…','loading'));
  else if(!cases.length){card.append(node('p','No cases are available. Create a case and add source evidence in the Team workspace first.','empty'));const link=node('a','Open Team workspace','button');link.href='/';card.append(link);}
  else{const label=node('label','Existing case'),select=node('select');select.id='case-picker';label.htmlFor=select.id;for(const item of cases){const option=node('option',`${item.case_id} · ${item.links?.order_id || item.snapshot?.links?.order_id || 'No linked order'}`);option.value=item.case_id;select.append(option);}card.append(label,select,button('Open delivery case',()=>{location.href=`/customer.html?case=${encodeURIComponent(select.value)}`;},'primary wide'));}
  main.append(card);
}
function choose(){
  intro('What time works for you?','Choose a recorded proposal or enter a preferred window for an operator to review.');renderStepper();
  const form=node('form',undefined,'card');form.addEventListener('submit',event=>{event.preventDefault();perform(()=>session.review());});caseStrip(form);errorMessage(form);
  const options=offeredWindows(session.detail),fieldset=node('fieldset');fieldset.append(node('legend','Your requested window'));
  if(!options.length)fieldset.append(node('p','No current window options have been recorded. Enter your preferred time below.','muted small'));
  for(const option of options){const label=node('label',undefined,'slot'),radio=node('input'),text=node('div');radio.type='radio';radio.name='window-choice';radio.value=option.decision_id;radio.checked=choice===option.decision_id;radio.disabled=session.busy;radio.addEventListener('change',()=>{choice=option.decision_id;session.setDraft({slot_start:option.slot_start,slot_end:option.slot_end});render();});text.append(node('strong',windowLabel(option)),node('span','Recorded proposal · availability and price unconfirmed'));label.append(radio,text);fieldset.append(label);}
  const custom=node('label',undefined,'slot'),radio=node('input'),copy=node('div');radio.type='radio';radio.name='window-choice';radio.value='custom';radio.checked=choice==='custom';radio.disabled=session.busy;radio.addEventListener('change',()=>{choice='custom';render();});copy.append(node('strong','Request a different time'),node('span','A preference for review; subject to carrier confirmation'));custom.append(radio,copy);fieldset.append(custom);
  if(choice==='custom'){
    const fields=node('div',undefined,'fields');for(const [key,labelText] of [['slot_start','Window starts'],['slot_end','Window ends']]){const field=node('div',undefined,'field'),label=node('label',labelText),input=node('input');input.type='datetime-local';input.id=key;input.required=true;input.disabled=session.busy;input.value=toLocal(session.draft[key]);label.htmlFor=key;input.addEventListener('input',()=>session.setDraft({[key]:toISO(input.value)}));field.append(label,input);fields.append(field);}fieldset.append(fields);
  }
  fieldset.append(node('p',`Times are shown in ${timezone}. Choose a future window of up to eight hours.`,'muted small'));form.append(fieldset);
  const evidence=node('fieldset');evidence.append(node('legend','Supporting sources'),node('p','Select the case evidence supporting this preference. Source content has not been verified by this preview.','muted small'));
  const events=session.detail.snapshot.events || [];
  if(!events.length)evidence.append(node('p','No source evidence yet. Add the delivery request in Team before submitting.','note pending'));
  for(const event of events){const container=node('div',undefined,'source'),label=node('label'),check=node('input'),text=node('span');check.type='checkbox';check.value=event.event_id;check.name='source-event';check.checked=session.draft.evidence_event_ids.includes(event.event_id);check.disabled=session.busy;check.addEventListener('change',()=>{const ids=new Set(session.draft.evidence_event_ids);if(check.checked)ids.add(event.event_id);else ids.delete(event.event_id);session.setDraft({evidence_event_ids:[...ids]});});text.append(node('strong',event.event_id),node('span',`${event.kind || 'Source'} · ${formatDate(event.occurred_at)}`,'muted small'));label.append(check,text);const details=node('details');details.append(node('summary','Read source'),node('pre',event.text || 'No source text. Inspect the original media in Team before selecting this evidence.'));container.append(label,details);evidence.append(container);}form.append(evidence);
  const note=node('div',undefined,'note');note.append(node('p','Carrier availability and price are not confirmed.'),node('p','The delivery address stays unchanged. This preview records an operator proposal for separate review.'));form.append(note);
  const submit=node('button','Review preference →','primary wide');submit.id='review-preference';submit.type='submit';submit.disabled=session.busy || !events.length;form.append(submit);
  if(session.status.kind!=='none')form.append(button('View current recorded status',()=>{session.step='status';render();},'wide'));
  main.append(form);
}
function review(){
  intro('Does this look right?','Check the window and supporting sources before recording this preference.');renderStepper();
  const card=node('section',undefined,'card');caseStrip(card);errorMessage(card);card.append(node('h2','Your delivery preference'));
  const list=node('dl');addRow(list,'Requested time',windowLabel(session.draft),timezone);addRow(list,'Address','Unchanged');addRow(list,'Price','Not confirmed');addRow(list,'Availability','Not confirmed by the carrier');addRow(list,'Sources',session.draft.evidence_event_ids.join(', '));card.append(list);
  const changed=session.binding?.revision!==session.detail.snapshot.revision || session.binding?.snapshot_hash!==session.detail.snapshot.snapshot_hash;
  if(changed)card.append(node('div','This case has changed since your review. Your draft is retained. Review it against the latest snapshot before submitting.','note pending'));
  card.append(node('p','Recording this preference creates an operator proposal. Approval and any sandbox action happen separately in Team.','note'));
  const actions=node('div',undefined,'actions');actions.append(button('Back',()=>{session.step='choose';render();}));
  if(changed)actions.append(button('Review latest snapshot',()=>perform(()=>session.review()),'primary'));
  else {const submit=button(session.busy?'Recording preference…':session.error?'Try recording preference again':'Record window preference',()=>perform(()=>session.submit()),'primary');submit.id='submit-preference';actions.append(submit);}
  card.append(actions,node('p','A failed request keeps your draft. Retrying the same request uses the same submission key.','muted small'));main.append(card);
}
function status(){
  const state=session.status;intro('Your request, at a glance.','The latest recorded state for this case. Refresh to check for operator updates.');renderStepper();
  const card=node('section',undefined,'card status-card');card.id='customer-status';card.dataset.status=state.kind;caseStrip(card);errorMessage(card);card.append(node('div','↗','status-mark'),node('h2',state.title),node('p',state.description));
  const list=node('dl');if(state.decision)addRow(list,'Requested time',windowLabel(state.decision.action),timezone);addRow(list,'Price','Not confirmed');addRow(list,'Carrier booking','Not confirmed');if(state.receipt){addRow(list,'Local receipt',state.receipt.action_id);addRow(list,'External effects',Number.isInteger(state.receipt.external_effects)?String(state.receipt.external_effects):'Not recorded');}card.append(list);
  const actions=node('div',undefined,'actions'),refresh=button(loading?'Refreshing…':'Refresh status',()=>perform(async()=>{loading=true;render();try{await session.load(selectedId);}finally{loading=false;}}),'primary');refresh.id='refresh-status';actions.append(refresh,button('Choose another window',()=>{session.step='choose';choice='custom';render();}));card.append(actions);
  card.append(node('p',session.checkedAt?`Last read ${formatDate(session.checkedAt)} · ${timezone}`:'No current read available.','muted small'));
  const details=node('details',undefined,'technical');details.append(node('summary','Record details'),node('p',`Last read case revision ${session.detail.snapshot.revision}`));if(session.savedOutcome)details.append(node('p',`Saved submission receipt: proposal ${session.savedOutcome.decision_id}`));if(state.decision)details.append(node('p',`Current proposal ${state.decision.decision_id}`));if(state.receipt)details.append(node('p',`Execution mode: ${state.receipt.execution_mode}`));card.append(details);main.append(card);
}
function render(){
  main.replaceChildren();document.querySelector('#team-link').href=selectedId?`/#case=${encodeURIComponent(selectedId)}`:'/';
  if(!selectedId){picker();return;}
  if(!session.detail){intro('Your delivery window.','Loading the selected case and its recorded sources.');const card=node('section',undefined,'card');errorMessage(card);if(loading)card.append(node('p','Loading case…','loading'));else{card.append(node('p','The case could not be loaded. Check the link or choose an existing case.','muted'));const choose=node('a','Choose a case','button');choose.href='/customer.html';card.append(choose,button('Retry',()=>perform(loadSelected)));}main.append(card);return;}
  if(session.step==='review')review();else if(session.step==='status')status();else choose();
}
async function loadSelected(){loading=true;render();try{await session.load(selectedId);}finally{loading=false;}}
await perform(async()=>{if(selectedId)await loadSelected();else{try{const result=await api('/cases');cases=result.cases || [];}finally{loading=false;}}});
