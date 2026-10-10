import {createAPI} from './session.js';
import {CustomerSession,offeredWindows} from './customer-model.js';

const api=createAPI(),main=document.querySelector('#main');
const session=new CustomerSession(api,{onChange:render});
const timezone=Intl.DateTimeFormat().resolvedOptions().timeZone || 'browser local timezone';
let selectedId=new URLSearchParams(location.search).get('case'),cases=[],loading=true,screenError='',choice='',helpMessage='';
const node=(tag,text,className)=>{const element=document.createElement(tag);if(text!==undefined)element.textContent=text;if(className)element.className=className;return element;};
const button=(text,handler,className='')=>{const element=node('button',text,className);element.type='button';element.disabled=session.busy || loading;element.addEventListener('click',handler);return element;};
const formatDate=value=>{const date=new Date(value);return Number.isFinite(date.getTime())?date.toLocaleString('en-GB',{dateStyle:'medium',timeStyle:'short'}):'Not recorded';};
const windowLabel=action=>`${formatDate(action.slot_start)} – ${formatDate(action.slot_end)}`;
const teamURL=()=>selectedId?`/#case=${encodeURIComponent(selectedId)}`:'/';
async function perform(action){screenError='';try{await action();}catch(error){screenError=error.message || 'The request failed. Your draft is retained.';}render();}
function errorMessage(parent){const message=screenError || session.error;if(message){const alert=node('div',message,'note error');alert.setAttribute('role','alert');parent.append(alert);}}
function addRow(list,label,value,note){const row=node('div',undefined,'summary-row'),dd=node('dd',value);row.append(node('dt',label),dd);if(note)dd.append(node('small',note));list.append(row);}
function caseStrip(parent){const strip=node('div',undefined,'case-strip'),info=node('div'),parcel=node('span','▱','parcel');parcel.setAttribute('aria-hidden','true');info.append(node('strong','Your parcel'),node('span',`Order ${session.detail.snapshot.links?.order_id || 'reference not recorded'} · Delivery time not confirmed`));strip.append(parcel,info);parent.append(strip);}
function intro(title,description){const header=node('div',undefined,'intro');header.append(node('div','Your request','eyebrow'),node('h1',title),node('p',description));main.append(header);}
function progress(parent,complete=false){const steps=node('div',undefined,'steps');steps.setAttribute('aria-label',complete?'Step 2 of 2':'Step 1 of 2');steps.append(node('span',undefined,'done'),node('span',undefined,complete?'done':''));parent.append(steps);}
function card(complete=false){const element=node('section',undefined,'card');caseStrip(element);progress(element,complete);errorMessage(element);main.append(element);return element;}
function tools(){
  const actions=node('div',undefined,'client-tools');
  actions.append(button('Get help',()=>{helpMessage='Contact an operator in the Team workspace for help. This preview cannot send a support request.';render();},'quiet'),button('Check status',()=>perform(async()=>{loading=true;render();try{await session.load(selectedId);session.step='status';}finally{loading=false;}}),'quiet'),button('Stop new actions',()=>{helpMessage='An operator must stop ongoing work in the Team workspace. This preview has not cancelled any request, booking or delivery.';render();},'quiet'));
  main.append(actions);
  if(helpMessage){const notice=node('div',helpMessage,'note');notice.setAttribute('role','status');const link=node('a','Open Team workspace');link.href=teamURL();notice.append(document.createTextNode(' '),link);main.append(notice);}
}
function picker(){
  intro('Your delivery request.','Choose an existing delivery request to see its latest recorded options.');
  const content=node('section',undefined,'card');content.append(node('h2','Choose a request'));errorMessage(content);
  if(loading)content.append(node('p','Loading requests…','loading'));
  else if(!cases.length){content.append(node('p','No requests are available. Open the Team workspace for help.','empty'));const link=node('a','Open Team workspace','button');link.href='/';content.append(link);}
  else{const label=node('label','Existing request'),select=node('select');select.id='case-picker';label.htmlFor=select.id;for(const item of cases){const option=node('option',item.links?.order_id || item.snapshot?.links?.order_id || 'Delivery request');option.value=item.case_id;select.append(option);}content.append(label,select,button('Open delivery request',()=>{location.href=`/customer.html?case=${encodeURIComponent(select.value)}`;},'primary'));}
  main.append(content);
}
function choose(){
  const options=offeredWindows(session.detail);
  intro(options.length?'When can you receive your delivery?':'Check times and prices',options.length?'Review the recorded window before you confirm your preference.':'Your next step and confirmed outcome will appear here.');
  const content=card();
  if(!options.length){content.append(node('h2','No suitable windows yet'),node('p','No current delivery options have been recorded. Ask the team to check available times and prices. Your delivery has not changed.','muted'));
    content.append(button('Get help with delivery options',()=>{helpMessage='An operator can check available times and prices in the Team workspace. This preview cannot request options directly.';render();},'primary'));
  }else{
    content.append(node('h2','Available times'));
    const fieldset=node('fieldset'),legend=node('legend','Choose a delivery window','sr');fieldset.append(legend);
    for(const option of options){const label=node('label',undefined,'slot'),radio=node('input'),text=node('div',undefined,'slot-main');radio.type='radio';radio.name='window-choice';radio.value=option.decision_id;radio.checked=choice===option.decision_id;radio.disabled=session.busy;radio.addEventListener('change',()=>{choice=option.decision_id;session.setDraft({slot_start:option.slot_start,slot_end:option.slot_end,evidence_event_ids:[...option.evidence_event_ids]});render();});text.append(node('strong',windowLabel(option)),node('span','Recorded proposal · availability and price unconfirmed'));label.append(radio,text);fieldset.append(label);}content.append(fieldset,node('p',`All times are shown in ${timezone}. Selecting a time does not change the booking yet.`,'small muted'));
    const next=button('Continue',()=>perform(()=>{const current=offeredWindows(session.detail).find(option=>option.decision_id===choice);if(!current)throw Error('This offer is no longer current. Check status for the latest options.');session.setDraft({slot_start:current.slot_start,slot_end:current.slot_end,evidence_event_ids:[...current.evidence_event_ids]});session.review({offerId:current.decision_id});}),'primary');next.id='review-preference';next.disabled=session.busy || loading || !options.some(option=>option.decision_id===choice);content.append(next);
    const secondary=node('div',undefined,'actions');secondary.append(button('I need another date',()=>{helpMessage='An operator can check another date in the Team workspace. No new request has been sent.';render();},'quiet'));content.append(secondary);
  }
  if(session.status.kind!=='none'){const actions=node('div',undefined,'actions');actions.append(button('View current recorded status',()=>{session.step='status';render();},'quiet'));content.append(actions);}
  tools();
}
function review(){
  intro('Review your chosen time','Check the recorded window before submitting your preference.');
  const content=card(true);content.append(node('h2','Does this look right?'));
  const list=node('dl');addRow(list,'Requested time',windowLabel(session.draft),timezone);addRow(list,'Delivery address','Unchanged');addRow(list,'Full surcharge','Not confirmed');content.append(list);
  const changed=session.binding?.revision!==session.detail.snapshot.revision || session.binding?.snapshot_hash!==session.detail.snapshot.snapshot_hash || (!session.reviewedOfferCurrent && !session.canReplaySubmission);
  if(changed)content.append(node('div','This offer has changed since your review. Your draft is retained. Select a current delivery option before submitting.','note pending'));
  content.append(node('p','This records your preference for separate operator review. Availability, price and a carrier booking are not confirmed.','small muted'));
  if(changed)content.append(button('Review current options',()=>{choice='';session.step='choose';render();},'primary'));
  else{const submit=button(session.busy?'Recording preference…':session.error?'Try recording preference again':'Record window preference',()=>perform(()=>session.submit()),'primary');submit.id='submit-preference';content.append(submit);}
  const actions=node('div',undefined,'actions');actions.append(button('Change selection',()=>{choice='';session.step='choose';render();},'quiet'));content.append(actions);tools();
}
function status(){
  const state=session.status;intro(state.kind==='none'?'Check times and prices':'Your request is in progress','Request acknowledgement and delivery completion are separate events.');
  const content=card(true);content.id='customer-status';content.dataset.status=state.kind;content.append(node('div','…','status-mark'),node('h2',state.title),node('p',state.description));
  const list=node('dl');if(state.decision)addRow(list,'Requested time',windowLabel(state.decision.action),timezone);addRow(list,'Full surcharge','Not confirmed');addRow(list,'Carrier booking','Not confirmed');content.append(list);
  const refresh=button(loading?'Refreshing…':'Refresh status',()=>perform(async()=>{loading=true;render();try{await session.load(selectedId);}finally{loading=false;}}),'primary');refresh.id='refresh-status';content.append(refresh);
  const actions=node('div',undefined,'actions');actions.append(button('View delivery options',()=>{session.step='choose';render();},'quiet'));content.append(actions,node('p',session.checkedAt?`Last checked ${formatDate(session.checkedAt)} · ${timezone}`:'No current read available.','small muted'));
  const details=node('details',undefined,'technical');details.append(node('summary','Operator record details'),node('p',`Last read case revision ${session.detail.snapshot.revision}`));if(session.savedOutcome)details.append(node('p',`Saved submission receipt: proposal ${session.savedOutcome.decision_id}`));if(state.decision)details.append(node('p',`Current proposal ${state.decision.decision_id}`));if(state.receipt)details.append(node('p',`Execution mode: ${state.receipt.execution_mode} · Local receipt: ${state.receipt.action_id}`));content.append(details);tools();
}
function render(){
  main.replaceChildren();document.querySelector('#team-link').href=teamURL();
  const order=session.detail?.snapshot.links?.order_id;document.querySelector('#order-badge').textContent=order?`Order ${order}`:'Your delivery';document.querySelector('#order-badge').title=order?`Order ${order}`:'';
  if(!selectedId){picker();return;}
  if(!session.detail){intro('Your delivery request.','Your next step and confirmed outcome will appear here.');const content=node('section',undefined,'card');errorMessage(content);if(loading)content.append(node('p','Loading request…','loading'));else{content.append(node('p','The request could not be loaded. Check the link or choose an existing request.','muted'));const choose=node('a','Choose a request','button');choose.href='/customer.html';content.append(choose,button('Retry',()=>perform(loadSelected)));}main.append(content);return;}
  if(session.step==='review')review();else if(session.step==='status')status();else choose();
}
async function loadSelected(){loading=true;render();try{await session.load(selectedId);}finally{loading=false;}}
await perform(async()=>{if(selectedId)await loadSelected();else{try{const result=await api('/cases');cases=result.cases || [];}finally{loading=false;}}});
