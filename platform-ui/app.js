import { PlatformSession, CommunicationsSession, communicationEnvelope, createAPI, needsReview, reviewedMediaMessage, normalizeMediaRun, canReview, modelStatusView, ModelPoller } from './session.js';

const $ = id => document.getElementById(id);
const api = createAPI();
const session = new PlatformSession(api, renderDetail);
const communications = new CommunicationsSession(api, renderCommunications);
let preparingImport = false;
let cases = [], capabilities = null, activeView = 'cases', renderedCase = null, notice = '';
let createAttempt = null;
const mediaReviewed = new Set();
const mediaDraftEvents = new Map();
function createModelPoller() {
  return new ModelPoller({api,onUpdate(job,{caseId}){
    if(session.selectedId!==caseId || !session.detail)return;
    const index=session.detail.model_jobs.findIndex(value=>(value.run_id || value.job_id)===job.run_id);
    if(index<0)return;
    session.detail.model_jobs[index]=job;
    renderJobs(session.detail);
    // Refresh the server's case-state projection once on completion, never submit.
    if(!['queued','running','response_received'].includes(job.status) && !session.busy)session.reload().catch(()=>{});
  },onError(){if(session.detail)renderJobs(session.detail);}});
}
let modelPoller=createModelPoller();
window.addEventListener('pagehide',()=>modelPoller.dispose());
window.addEventListener('pageshow',event=>{if(event.persisted){modelPoller=createModelPoller();renderDetail();}});
const human = value => String(value ?? 'Unknown').replaceAll('_',' ').replace(/^./,c=>c.toUpperCase());
const stamp = value => value ? new Date(value).toLocaleString('en-GB') : '';
const uid = prefix => `${prefix}-${crypto.randomUUID()}`;
const node = (tag, text, className) => {const e=document.createElement(tag);if(text!==undefined)e.textContent=String(text);if(className)e.className=className;return e;};
const empty = (parent, text) => parent.append(node('p',text,'muted small'));
const button = (label, action, className='secondary') => {const b=node('button',label,className);b.type='button';b.disabled=session.busy;b.addEventListener('click',action);return b;};
function showMessages() {
  $('error-message').textContent=session.error;$('error-message').hidden=!session.error;
  $('status-message').textContent=notice;$('status-message').hidden=!notice;
}
async function perform(action, message='') {
  notice='';session.error='';showMessages();
  try {await action();notice=message;}
  catch(error){session.error=error.message || 'The request could not be completed. Your draft is retained.';}
  showMessages();
}
async function loadCases() {
  const result=await api('/cases');cases=result.cases || [];renderCases();
}
function renderCases() {
  const selected=cases.filter(needsReview);
  $('queue-count').textContent=String(selected.length);
  $('case-list-title').textContent=activeView==='queue'?'Review queue':'Cases';
  const parent=$('case-list');parent.replaceChildren();
  const visible=activeView==='queue'?selected:cases;
  if(!visible.length)empty(parent,activeView==='queue'?'No cases awaiting review.':'No cases yet. Start with a new case.');
  for(const item of visible){
    const id=item.case_id || item.snapshot?.case_id;
    const b=button('',()=>selectCase(id),'case-item'+(session.selectedId===id?' selected':''));
    b.dataset.caseId=id;b.append(node('strong',id),node('p',`Order ${item.snapshot?.links?.order_id || item.links?.order_id || '—'}`),node('span',human(item.states?.lifecycle || 'new'),'tag'));
    if(session.selectedId===id)b.setAttribute('aria-current','true');parent.append(b);
  }
}
function captureDrafts() {
  if(!session.selectedId)return;
  session.setDraft('evidence',{text:$('evidence-text').value,kind:$('evidence-kind').value,channel:$('evidence-channel').value,sender:$('evidence-sender').value,file:$('evidence-file').files?.[0] || session.getDraft('evidence').file,eventId:session.getDraft('evidence').eventId || uid('event'),occurredAt:session.getDraft('evidence').occurredAt || new Date().toISOString(),asset:session.getDraft('evidence').asset});
  session.setDraft('proposal',{type:$('action-type').value,start:$('slot-start').value,end:$('slot-end').value,refs:[...document.querySelectorAll('[name="evidence-ref"]:checked')].map(e=>e.value)});
  session.setDraft('review',{note:$('review-note').value,consent:$('customer-consent').checked});
}
function restoreDrafts(detail) {
  const e=session.getDraft('evidence'),p=session.getDraft('proposal'),r=session.getDraft('review');
  $('evidence-text').value=e.text || '';$('evidence-kind').value=e.kind || 'message';$('evidence-channel').value=e.channel || 'chat';
  // A File cannot be assigned back to a native input. Keep its retained object in the session.
  $('evidence-file').value='';
  $('action-type').value=p.type || 'reschedule_delivery';$('slot-start').value=p.start || '';$('slot-end').value=p.end || '';
  $('review-note').value=r.note || '';$('customer-consent').checked=Boolean(r.consent);
  $('evidence-references').replaceChildren();
  updateFormVisibility();
}
async function selectCase(id) {
  captureDrafts();await perform(()=>session.select(id));renderCases();
  if(session.detail)history.replaceState(null,'',`#case=${encodeURIComponent(session.selectedId)}`);
}
function updateFormVisibility() {
  const media=$('evidence-kind').value!=='message';$('file-label').hidden=!media;
  const retained=session.getDraft('evidence').file;$('retained-file').textContent=retained?`Selected source retained: ${retained.name}`:'';
  $('evidence-text').required=!media;
  $('evidence-file').accept=$('evidence-kind').value==='photo'?'image/png,image/jpeg':'audio/mpeg,audio/wav,audio/mp4,audio/webm';
  const reschedule=$('action-type').value==='reschedule_delivery';$('reschedule-fields').hidden=!reschedule;
  $('slot-start').required=reschedule;$('slot-end').required=reschedule;
}
function renderDetail() {
  showMessages();renderCases();
  const detail=session.detail;
  $('case-detail').hidden=!detail;$('empty-state').hidden=Boolean(detail);
  if(!detail){modelPoller.watch({caseId:null,generation:session.generation,jobs:[]});return;}
  const snapshot=detail.snapshot;
  const changed=renderedCase!==detail.case_id;
  if(changed){renderedCase=detail.case_id;restoreDrafts(detail);}
  $('case-title').textContent=detail.case_id;
  $('case-order').textContent=`Order ${snapshot.links.order_id}`;
  $('case-meta').textContent=`Revision ${snapshot.revision} · ${snapshot.links.customer_id} · ${snapshot.events.length} evidence event${snapshot.events.length===1?'':'s'}`;
  const states=$('case-states');states.replaceChildren();
  for(const key of ['lifecycle','evidence','analysis','decision','action']){const d=node('div',undefined,'state');d.append(node('dt',human(key)),node('dd',human(detail.states[key])));states.append(d);}
  const sender=$('evidence-sender'),currentSender=changed?session.getDraft('evidence').sender:sender.value;sender.replaceChildren();
  for(const id of snapshot.participants){const o=node('option',id);o.value=id;sender.append(o);}sender.value=currentSender && snapshot.participants.includes(currentSender)?currentSender:snapshot.links.customer_id;
  renderEvidence(detail);renderDecisions(detail);renderHistory(detail);renderJobs(detail);renderCaseCommunications(detail);
  for(const selector of ['#create-case-form button','#evidence-form button','#proposal-form button','#analyze-case','#refresh-case'])document.querySelector(selector).disabled=session.busy;
  $('run-model').disabled=session.busy || !$('model-profile').value || capabilities?.models?.enabled!==true;
}
function renderEvidence(detail) {
  const parent=$('evidence-list'),refs=$('evidence-references');parent.replaceChildren();
  const checked=new Set(renderedCase===detail.case_id?[...refs.querySelectorAll('input:checked')].map(e=>e.value):[]);
  for(const id of session.getDraft('proposal').refs || [])checked.add(id);
  refs.replaceChildren();$('evidence-count').textContent=String(detail.snapshot.events.length);
  if(!detail.snapshot.events.length){empty(parent,'No evidence yet. Add the original request to begin.');empty(refs,'Add evidence before proposing a delivery change.');}
  for(const event of detail.snapshot.events){
    const item=node('article',undefined,'evidence-item');item.dataset.eventId=event.event_id;
    item.append(node('p',`${human(event.kind)} · ${event.sender_id} · ${human(event.channel)}`,'source'),node('p',event.text || 'Source media; no extracted text.','evidence-text'),node('p',`${event.event_id} · ${stamp(event.occurred_at)}`,'hint'));
    if(event.media){
      const asset=detail.assets.find(a=>a.asset_id===event.media.asset_id) || event.media;
      const url=`/api/platform/cases/${encodeURIComponent(detail.case_id)}/assets/${encodeURIComponent(event.media.asset_id)}`;
      const link=node('a',`Open source · ${asset.filename || human(event.kind)}`);link.href=url;link.target='_blank';link.rel='noopener';item.append(link);
      if(event.kind==='photo'){const img=node('img');img.src=url;img.alt='Source evidence photo';img.loading='lazy';item.append(img);}
      else {const audio=node('audio');audio.src=url;audio.controls=true;audio.preload='none';item.append(audio);}
      item.append(node('p',`Stored source · ${event.media.size_bytes.toLocaleString('en-GB')} bytes · SHA-256 ${event.media.sha256.slice(0,12)}…`,'hint'));
      const mode=event.kind==='photo'?'image_analysis':'asr',available=capabilities?.media?.[mode]?.enabled===true;
      const process=button(event.kind==='photo'?'Analyze image':'Transcribe audio',()=>perform(async()=>{await session.mutate(`assets/${encodeURIComponent(event.media.asset_id)}/process`,{mode});},'Source processing request completed. Check the analysis result.' ));
      process.disabled=session.busy || !available;process.title=available?'Process this source with the configured provider':'Processing is not configured';item.append(process);
      const runs=(detail.media_runs || []).filter(run=>run.asset_id===event.media.asset_id);
      item.append(node('p',runs.length?`Latest processing: ${human(runs.at(-1).status)}`:asset.processing?.status?`Processing: ${human(asset.processing.status)}`:'Not analyzed · source evidence only','hint'));
      for(const run of runs)renderMediaRun(item,run,event.media,detail);
    }
    parent.append(item);
    const label=node('label',undefined,'check'),check=node('input');check.type='checkbox';check.name='evidence-ref';check.value=event.event_id;check.checked=checked.has(event.event_id);label.append(check,node('span',`${event.event_id} · ${(event.text || human(event.kind)).slice(0,80)}`));refs.append(label);
  }
}
function renderMediaRun(parent, input, asset, detail) {
  const run=normalizeMediaRun(input);
  const block=node('section',undefined,'derived-evidence');block.dataset.mediaRunId=run.run_id;
  block.append(node('h4',`${run.mode==='asr'?'Audio transcript':'Image analysis'} · ${human(run.status)}`));
  block.append(node('p','Derived provider output. The original source above is unchanged. Human review is required.','hint'));
  const bound=run.source_sha256===asset.sha256;
  block.append(node('p',bound?`Source hash matches stored asset · ${run.source_sha256.slice(0,12)}…`:'Source hash mismatch. This result cannot be used as evidence.','hint'));
  if(run.validation){
    const validation=run.validation;
    const pieces=[`Validation: ${human(validation.method)}`];
    if(validation.width && validation.height)pieces.push(`${validation.width} × ${validation.height} pixels`);
    if(validation.content_decoded)pieces.push('Content decoded');
    if(validation.duration_seconds!==undefined)pieces.push(`${validation.duration_seconds} seconds`);
    if(validation.audio_streams!==undefined)pieces.push(`${validation.audio_streams} audio stream${validation.audio_streams===1?'':'s'}`);
    if(validation.sha256_verified)pieces.push('SHA-256 verified');
    block.append(node('p',pieces.join(' · '),'hint'));
  }
  if(run.output_text)block.append(node('pre',run.output_text,'derived-text'));
  if(run.error)block.append(node('p',typeof run.error==='string'?run.error:human(run.error.code),'hint'));
  if(run.receipt){const receipt=node('details');receipt.append(node('summary','Provider receipt'),node('pre',JSON.stringify(run.receipt,null,2)));block.append(receipt);}
  if(run.status==='succeeded' && typeof run.output_text==='string' && run.output_text.trim()){
    const label=node('label',undefined,'check'),check=node('input');check.type='checkbox';check.checked=mediaReviewed.has(run.run_id);check.disabled=!bound;
    check.addEventListener('change',()=>{if(check.checked)mediaReviewed.add(run.run_id);else mediaReviewed.delete(run.run_id);});
    label.append(check,node('span','I reviewed this output against the original source.'));block.append(label);
    const use=button('Use reviewed text',()=>perform(async()=>{
      const text=reviewedMediaMessage(run,mediaReviewed.has(run.run_id));
      const snapshot=session.detail.snapshot;
      if(!mediaDraftEvents.has(run.run_id))mediaDraftEvents.set(run.run_id,{event_id:uid('reviewed'),occurred_at:new Date().toISOString(),channel:'internal',sender_id:snapshot.links.operator_id,recipient_ids:snapshot.participants.filter(p=>p!==snapshot.links.operator_id),kind:'message',text,media:null});
      await session.mutate('events',{expected_revision:snapshot.revision,event:mediaDraftEvents.get(run.run_id)});
      await loadCases();
    },'Reviewed output appended as an internal operator message. The original source is unchanged.'));
    let alreadyUsed=false;
    try{const text=reviewedMediaMessage(run,true);alreadyUsed=detail.snapshot.events.some(e=>e.kind==='message' && e.channel==='internal' && e.text===text);}catch{}
    use.disabled=session.busy || !bound || alreadyUsed;
    if(alreadyUsed)use.textContent='Reviewed text added';block.append(use);
  }
  parent.append(block);
}
function renderDecisions(detail) {
  const parent=$('decision-list');parent.replaceChildren();
  if(!detail.decisions.length)empty(parent,'No proposal yet. Analyze the case or add an operator proposal.');
  const latest=detail.decisions.at(-1);
  for(const decision of [...detail.decisions].reverse()){
    const item=node('article',undefined,'decision-item');item.dataset.decisionId=decision.decision_id;
    const reviews=detail.reviews.filter(r=>r.decision_id===decision.decision_id),review=reviews.at(-1);
    const receipts=detail.actions.filter(a=>a.decision_id===decision.decision_id);
    const current=decision.revision===detail.snapshot.revision && decision.snapshot_hash===detail.snapshot.snapshot_hash && decision===latest;
    const supported=decision.action?.type==='reschedule_delivery';
    item.append(node('h4',human(decision.action?.type)),node('p',`${human(decision.kind)} · revision ${decision.revision} · ${decision.decision_id}`));
    if(decision.action?.slot_start)item.append(node('p',`${stamp(decision.action.slot_start)} → ${stamp(decision.action.slot_end)}`));
    const checks=node('div',undefined,'checks');
    if(Array.isArray(decision.checks))for(const check of decision.checks)checks.append(node('span',typeof check==='string'?human(check):`${human(check.code || check.name || check.check)}: ${human(check.status ?? check.passed ?? check.ok)}`,'tag'));
    else if(decision.checks)for(const [key,value] of Object.entries(decision.checks))checks.append(node('span',`${human(key)}: ${human(value)}`,'tag'));
    item.append(checks);
    if(!current)item.append(node('p','Superseded or stale. Create a proposal against the current evidence.','hint'));
    if(review)item.append(node('p',`${review.verdict==='approve'?'Approved':'Rejected'} by local operator${review.note?` · ${review.note}`:''}`));
    if(!supported)item.append(node('p','This action is for human follow-up. Sandbox execution is unavailable.','hint'));
    const actions=node('div',undefined,'actions');
    for(const verdict of ['approve','reject']){
      const b=button(human(verdict),()=>perform(async()=>{captureDrafts();if(!$('review-note').value.trim())throw Error('Add a review note explaining your decision.');if(verdict==='approve' && supported && !$('customer-consent').checked)throw Error('Confirm customer consent before approving a delivery change.');await session.mutate('reviews',{decision_id:decision.decision_id,verdict,note:$('review-note').value,customer_consent_confirmed:$('customer-consent').checked});await loadCases();},`Proposal ${verdict==='approve'?'approved':'rejected'}.`),verdict==='approve'?'secondary':'danger');
      b.dataset.action=verdict;b.disabled=session.busy || !current || !canReview(decision,verdict) || receipts.length>0;actions.append(b);
    }
    const execute=button(receipts.length?'View sandbox receipt':'Execute in sandbox',()=>receipts.length?item.querySelector('.receipt').scrollIntoView({behavior:'smooth',block:'center'}):perform(async()=>{const result=await session.mutate('execute',{decision_id:decision.decision_id});await loadCases();notice=`Sandbox receipt recorded. External effects: ${result.external_effects ?? 0}.`;renderDetail();}),'primary');
    execute.dataset.action='execute';execute.disabled=session.busy || !supported || (!receipts.length && (!current || review?.verdict!=='approve'));actions.append(execute);item.append(actions);
    for(const receipt of receipts){const r=node('div',undefined,'receipt');r.append(node('strong','Sandbox action verified'),node('p',`Receipt ${receipt.action_id || receipt.receipt_id || receipt.id || decision.decision_id}`),node('p',`Sandbox effects: ${receipt.sandbox_effects ?? 1} · External effects: ${receipt.external_effects ?? detail.external_effects}`));const more=node('details');more.append(node('summary','Receipt details'),node('pre',JSON.stringify(receipt,null,2)));r.append(more);item.append(r);}
    parent.append(item);
  }
}
function renderHistory(detail) {
  const parent=$('case-history');parent.replaceChildren();
  const entries=[...detail.snapshot.events.map(e=>({time:e.occurred_at,title:`Evidence added · ${human(e.kind)}`,text:e.text || e.event_id})),...detail.decisions.map(d=>({time:d.created_at,title:`${human(d.kind)} proposal · ${human(d.action?.type)}`,text:`${d.decision_id} · revision ${d.revision}`})),...detail.reviews.map(r=>({time:r.created_at,title:`Proposal ${r.verdict==='approve'?'approved':'rejected'}`,text:r.note || r.decision_id})),...detail.actions.map(a=>({time:a.created_at,title:'Sandbox action verified',text:`${a.action_id || a.receipt_id || a.decision_id} · external effects: ${a.external_effects ?? 0}`}))];
  for(const run of detail.media_runs || [])entries.push({time:run.created_at || run.finished_at,title:`${run.mode==='asr'?'Audio transcription':'Image analysis'} · ${human(run.status)}`,text:`Asset ${run.asset_id} · run ${run.run_id} · human review required`});
  entries.sort((a,b)=>String(b.time||'').localeCompare(String(a.time||'')));
  if(!entries.length)empty(parent,'Case created. The first evidence event will appear here.');
  for(const entry of entries){const item=node('article',undefined,'history-item');item.append(node('h4',entry.title),node('time',stamp(entry.time)),node('p',entry.text));parent.append(item);}
}
function renderJobs(detail) {
  const parent=$('model-jobs'),openInspectors=new Set();
  if(parent.dataset.caseId===detail.case_id)for(const card of parent.children){
    if(card.dataset.jobId)for(const inspector of card.querySelectorAll('details[data-inspector][open]'))openInspectors.add(JSON.stringify([card.dataset.jobId,inspector.dataset.inspector]));
  }
  parent.replaceChildren();parent.dataset.caseId=detail.case_id;
  modelPoller.watch({caseId:['cases','queue'].includes(activeView)?detail.case_id:null,generation:session.generation,jobs:detail.model_jobs || []});
  for(const entry of detail.model_jobs || []){
    const id=entry.run_id || entry.job_id || entry.id,job=entry,view=modelStatusView(job,detail.snapshot);const item=node('div',undefined,'job-item');item.dataset.runId=id || '';item.dataset.jobId=id || '';
    item.append(node('strong',`Model run · ${human(view.transport)}`,'model-transport'),node('p',id || 'Run recorded'));
    const revision=job.source?.revision ?? job.step_index ?? job.revision;
    item.append(node('p',`Input revision ${revision ?? 'unknown'} · ${view.current?'Current evidence':'Stale or unverified input'}`,'model-binding'));
    item.append(node('p',`Coordination: ${view.coordination?human(view.coordination):'Not available for the current evidence'}`,'model-coordination'));
    if(view.waitingFor.length)item.append(node('p',`Waiting for: ${view.waitingFor.join(', ')}`,'model-waiting'));
    if(view.proposedAction){item.append(node('p',`Proposed action: ${human(view.proposedAction.type)}${view.proposedAction.target_actor_id?` → ${view.proposedAction.target_actor_id}`:''}`,'model-action'));item.append(node('p',view.proposedAction.description,'hint'));}
    const count=value=>value===null?'not reported':String(value);
    item.append(node('p',`Dispatch attempts: ${count(view.dispatchAttempts)} · Automatic retries: ${count(view.automaticRetries)} · Operational effects: ${count(view.operationalEffects)}`,'model-counters'));
    if(view.operationalEffects>0)item.append(node('p','Reported effects require operator investigation. No action was triggered by observation.','model-warning'));
    if(job.receipt)item.append(node('p',`Provider: ${job.receipt.provider || 'not reported'} · requested model: ${job.receipt.requested_model || 'not reported'} · observed model: ${job.receipt.observed_model || 'not reported'}`));
    else item.append(node('p','Provider receipt not yet available.'));
    item.append(node('p',job.evaluation==null?'Evaluation unavailable: no reference label is supplied.':'Evaluation record available; this does not establish calibrated accuracy.','hint'));
    if(job.candidate){const more=node('details');more.dataset.inspector='proposal';more.open=openInspectors.has(JSON.stringify([id,'proposal']));more.append(node('summary',view.current?'Model proposal (requires review)':'Historical or unverified model proposal'),node('pre',JSON.stringify(job.candidate,null,2)));item.append(more);}
    const raw=node('details');raw.dataset.inspector='run';raw.open=openInspectors.has(JSON.stringify([id,'run']));raw.append(node('summary','Full model run and receipt'),node('pre',JSON.stringify(job,null,2)));item.append(raw);
    if(job.error)item.append(node('p',typeof job.error==='string'?job.error:JSON.stringify(job.error)));
    const polling=modelPoller.getState(id);
    if(polling?.status==='observing')item.append(node('p','Observing status every 2 seconds · read-only','model-poll-status hint'));
    if(polling?.status==='paused')item.append(node('p',`Observation paused: ${polling.error} Use Refresh run to resume.`,'model-poll-status model-warning'));
    if(id)item.append(button('Refresh run',()=>perform(()=>session.reload())));parent.append(item);
  }
}
function communicationReceipt(receipt,{allowRetry=false}={}) {
  const item=node('article',undefined,'communication-receipt');item.dataset.receiptId=receipt.receipt_id;
  item.append(node('span',human(receipt.status),`tag ${receipt.status==='accepted'?'positive':'pending'}`),node('h4',`${human(receipt.channel)} · ${receipt.connector_id}`),node('p',`Delivery ${receipt.delivery_id}`),node('p',`Receipt ${receipt.receipt_id}`,'hint'));
  if(receipt.reason)item.append(node('p',`Reason: ${human(receipt.reason)}`,'communication-reason'));
  if(receipt.case_id)item.append(node('p',`Case ${receipt.case_id} · revision ${receipt.revision ?? 'not reported'}`));
  item.append(node('p',`Source: ${human(receipt.source)} · ${stamp(receipt.received_at)}`,'hint'));
  if(receipt.raw_sha256)item.append(node('p',`Canonical envelope SHA-256: ${receipt.raw_sha256}`,'hint'));
  if(receipt.event_ids?.length)item.append(node('p',`Evidence events: ${receipt.event_ids.join(', ')}`,'hint'));
  if(receipt.provenance){const details=node('details');details.append(node('summary','Source provenance'),node('pre',JSON.stringify(receipt.provenance,null,2)));item.append(details);}
  if(receipt.status==='accepted' && receipt.case_id){const open=button('Open case',()=>{document.querySelector('[data-view="cases"]').click();selectCase(receipt.case_id);});open.disabled=communications.busy;item.append(open);}
  if(allowRetry && receipt.status==='quarantined'){
    const retry=button('Retry quarantined import',()=>perform(()=>writeCommunication(()=>communications.retry(receipt.receipt_id))));retry.dataset.action='retry';retry.disabled=communications.busy || preparingImport;item.append(retry);
  }
  return item;
}
function renderCaseCommunications(detail) {
  const parent=$('case-communications');parent.replaceChildren();
  if(!detail.communications?.length)return;
  const details=node('details');details.append(node('summary',`Inbound source provenance · ${detail.communications.length}`));
  for(const receipt of detail.communications)details.append(communicationReceipt(receipt));parent.append(details);
}
function renderCommunications() {
  const value=communications.value,busy=communications.busy || preparingImport;
  $('communications-loading').textContent=communications.loading?'Refreshing local inbox…':value?'Local receipt history. No automatic provider activity.':'Open Communications to load the local inbox.';
  const select=$('communication-connector'),selected=select.value;select.replaceChildren(node('option','Select a configured connector'));select.firstChild.value='';
  const connectors=$('communication-connectors');connectors.replaceChildren();
  for(const connector of value?.connectors || []){
    const option=node('option',`${connector.id} · ${human(connector.channel)}`);option.value=connector.id;option.disabled=connector.configured!==true;select.append(option);
    const card=node('article',undefined,'card');card.append(node('h3',human(connector.channel)),node('p',connector.id),node('span','Provider disconnected','tag'),node('p',`${connector.route_count ?? 0} configured routes · ${connector.contact_count ?? 0} mapped contacts`),node('p','Trusted local mappings only. No mailbox or account connection.','hint'));connectors.append(card);
  }
  select.value=selected;
  if(value && !value.connectors?.length)empty(connectors,'No inbound connectors configured. Configure trusted routes outside this UI.');
  for(const field of $('communication-form').querySelectorAll('input,textarea,select,button'))field.disabled=busy;
  $('communication-import').disabled=busy || !select.value;
  $('refresh-communications').disabled=busy || communications.loading;
  const email=$('communication-format').value==='eml';$('communication-email-fields').hidden=!email;$('communication-json-fields').hidden=email;
  $('communication-json').required=!email;
  for(const id of ['communication-delivery','communication-conversation','communication-file'])$(id).required=email;
  const parent=$('communication-receipts');parent.replaceChildren();const receipts=value?.receipts || [];
  $('communication-count').textContent=String(receipts.length);
  if(value && !receipts.length)empty(parent,'No inbound deliveries yet. Import a source envelope to begin.');
  for(const receipt of receipts)parent.append(communicationReceipt(receipt,{allowRetry:true}));
  const last=communications.lastReceipt;
  $('communication-outcome').textContent=last?`${human(last.status)} · receipt ${last.receipt_id}${last.reason?` · ${human(last.reason)}`:''}. Source input retained.`:'';
}
async function writeCommunication(action) {
  captureDrafts();const receipt=await action();
  const refreshes=[['inbox',communications.load()]];
  if(receipt?.status==='accepted'){
    refreshes.push(['case list',loadCases()]);
    if(session.selectedId===receipt.case_id)refreshes.push(['selected case',session.reload()]);
  }
  const outcomes=await Promise.allSettled(refreshes.map(([,promise])=>promise));
  const failed=refreshes.filter((_,index)=>outcomes[index].status==='rejected').map(([label])=>label);
  if(failed.length)throw Error(`${human(receipt.status)} receipt ${receipt.receipt_id} is saved. Refresh failed for: ${failed.join(', ')}. Use the corresponding Refresh control; do not re-import. Your source input is retained.`);
  return receipt;
}
function renderCapabilities() {
  const select=$('model-profile');select.replaceChildren(node('option','No model selected'));select.firstChild.value='';
  for(const model of capabilities?.models?.profiles || []){const available=capabilities?.models?.enabled===true && model.available;const option=node('option',`${model.label || model.id}${available?'':' · unavailable'}`);option.value=model.id;option.disabled=!available;select.append(option);}
  select.disabled=capabilities?.models?.enabled!==true;
  $('run-model').disabled=!select.value || capabilities?.models?.enabled!==true;
  const parent=$('integration-list');parent.replaceChildren();
  for(const adapter of capabilities?.adapters || []){const item=node('article',undefined,'card');item.append(node('h3',adapter.label || human(adapter.id)),node('span',human(adapter.status),'tag'),node('p',`Mode: ${human(adapter.mode)}`));parent.append(item);}
  for(const [key,value] of Object.entries(capabilities?.media || {})){const item=node('article',undefined,'card');item.append(node('h3',human(key)),node('span',human(value.status || (value.enabled?'available':'not_configured')),'tag'),node('p',value.enabled?'Configured processing is available from source evidence.':'No configured provider. Source evidence remains unprocessed.'));parent.append(item);}
}
document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>{
  activeView=b.dataset.view;document.querySelectorAll('[data-view]').forEach(n=>n.classList.toggle('active',n===b));
  $('integrations-view').hidden=activeView!=='integrations';$('communications-view').hidden=activeView!=='communications';$('cases-view').hidden=!['cases','queue'].includes(activeView);
  $('page-title').textContent=activeView==='communications'?'Every message, traceable.':activeView==='integrations'?'Connected, with control.':activeView==='queue'?'Decisions that need you.':'A clear next step.';
  renderCases();if(session.detail)renderJobs(session.detail);
  if(activeView==='communications')perform(()=>communications.load());
}));
$('refresh-communications').addEventListener('click',()=>perform(()=>communications.load()));
for(const id of ['communication-format','communication-connector'])$(id).addEventListener('change',renderCommunications);
$('communication-form').addEventListener('submit',event=>{event.preventDefault();perform(async()=>{
  if(preparingImport || communications.busy)return;
  const connector=$('communication-connector').value;
  if(!connector)throw Error('Select a configured connector.');
  const input={format:$('communication-format').value,jsonText:$('communication-json').value,deliveryId:$('communication-delivery').value,conversationId:$('communication-conversation').value,file:$('communication-file').files?.[0]};
  preparingImport=true;renderCommunications();
  try {const envelope=await communicationEnvelope(input);await writeCommunication(()=>communications.import(connector,envelope));}
  finally{preparingImport=false;renderCommunications();}
});});
$('refresh-list').addEventListener('click',()=>perform(loadCases));
$('refresh-case').addEventListener('click',()=>perform(async()=>{captureDrafts();await session.reload();await loadCases();},'Case refreshed. Your drafts are retained.'));
for(const id of ['evidence-form','proposal-form'])$(id).addEventListener('input',captureDrafts);
for(const id of ['review-note','customer-consent'])$(id).addEventListener('input',captureDrafts);
$('evidence-kind').addEventListener('change',updateFormVisibility);$('action-type').addEventListener('change',updateFormVisibility);
$('evidence-file').addEventListener('change',()=>{const draft=session.getDraft('evidence');session.setDraft('evidence',{...draft,file:$('evidence-file').files?.[0],asset:null});captureDrafts();updateFormVisibility();});
$('model-profile').addEventListener('change',()=>{$('run-model').disabled=!$('model-profile').value || capabilities?.models?.enabled!==true;});
$('create-case-form').addEventListener('submit',event=>{event.preventDefault();perform(async()=>{
  const customer=$('customer-id').value.trim(),operator=$('operator-id').value.trim();
  if(customer===operator)throw Error('Customer and operator IDs must be different.');
  const body={case_id:$('case-id').value.trim(),links:{order_id:$('order-id').value.trim(),customer_id:customer,operator_id:operator},participants:[customer,operator],language:'en'};
  const signature=JSON.stringify(body);if(createAttempt?.signature!==signature)createAttempt={signature,key:uid('create')};
  const result=await api('/cases',{method:'POST',body,idempotencyKey:createAttempt.key});createAttempt=null;
  await loadCases();await selectCase(result.case?.case_id || body.case_id);$('create-case-panel').open=false;
},'Case created. Add evidence to begin.');});
$('evidence-form').addEventListener('submit',event=>{event.preventDefault();perform(async()=>{
  captureDrafts();const id=session.selectedId,draft=session.getDraft('evidence'),snapshot=session.detail.snapshot;
  let media=null;
  if(draft.kind!=='message'){
    const file=draft.file;if(!file)throw Error('Choose a source file before adding media evidence.');
    const allowed=draft.kind==='photo'?['image/png','image/jpeg']:['audio/mpeg','audio/wav','audio/mp4','audio/webm'];
    if(!allowed.includes(file.type))throw Error('Unsupported source format. Choose PNG/JPEG or supported MPEG, WAV, MP4 or WebM audio.');
    if(!file.size || file.size>(draft.kind==='photo'?10:25)*1024*1024)throw Error(`The source must be non-empty and no larger than ${draft.kind==='photo'?10:25} MiB.`);
    if(draft.asset)media=draft.asset;
    else {const result=await session.mutate('assets',file,{raw:true,signature:`${draft.eventId}:${file.name}:${file.size}:${file.lastModified}`,headers:{'Content-Type':file.type,'X-Filename':encodeURIComponent(file.name)}});media=result.asset || result.media || result;session.drafts.set(`${id}:evidence`,{...draft,asset:media});}
    if(session.selectedId!==id)return;
  } else if(!draft.text.trim())throw Error('Add the original source text.');
  await session.mutate('events',{expected_revision:snapshot.revision,event:{event_id:draft.eventId,occurred_at:draft.occurredAt,channel:draft.channel,sender_id:draft.sender,recipient_ids:snapshot.participants.filter(p=>p!==draft.sender),kind:draft.kind,text:draft.text || null,media}});
  if(session.selectedId===id){session.setDraft('evidence',{});$('evidence-text').value='';$('evidence-file').value='';updateFormVisibility();}
  await loadCases();
},'Evidence saved to the case.');});
$('analyze-case').addEventListener('click',()=>perform(async()=>{const s=session.detail.snapshot;await session.mutate('analyze',{expected_revision:s.revision,snapshot_hash:s.snapshot_hash,mode:'deterministic'});await loadCases();},'Analysis recorded. Review the proposed next step.'));
$('run-model').addEventListener('click',()=>perform(async()=>{const s=session.detail.snapshot;await session.mutate('model-runs',{expected_revision:s.revision,snapshot_hash:s.snapshot_hash,model_profile_id:$('model-profile').value});await loadCases();renderDetail();},'Model run requested. Status is observed without submitting another run.'));
$('proposal-form').addEventListener('submit',event=>{event.preventDefault();perform(async()=>{
  captureDrafts();const s=session.detail.snapshot,p=session.getDraft('proposal');const action={type:p.type};
  if(p.type==='reschedule_delivery'){
    const start=new Date(p.start),end=new Date(p.end);
    if(!p.start || !p.end || !Number.isFinite(start.getTime()) || !Number.isFinite(end.getTime()))throw Error('Choose a valid start and end time.');
    if(start<=new Date() || end<=start || end-start>8*3600000)throw Error('Choose a future delivery window of no more than 8 hours.');
    if(!p.refs.length)throw Error('Select the evidence supporting this delivery change.');
    Object.assign(action,{slot_start:start.toISOString(),slot_end:end.toISOString(),address_change:false});
  }
  await session.mutate('decisions',{expected_revision:s.revision,snapshot_hash:s.snapshot_hash,action,evidence_event_ids:p.refs});await loadCases();
},'Operator proposal saved. Review it before sandbox execution.');});

await perform(async()=>{
  const results=await Promise.allSettled([loadCases(),api('/capabilities')]);
  if(results[1].status==='fulfilled'){capabilities=results[1].value;renderCapabilities();}
  else {$('model-profile').replaceChildren(node('option','Availability could not be loaded'));throw results[1].reason;}
  if(results[0].status==='rejected')throw results[0].reason;
  const hash=new URLSearchParams(location.hash.slice(1)),id=hash.get('case');
  if(id && cases.some(c=>c.case_id===id))await session.select(id);
});
