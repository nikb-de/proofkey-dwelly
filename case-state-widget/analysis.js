import './viewer.js';

async function requestJSON(path, options = {}) {
  const response = await fetch(path, {cache:'no-store', ...options});
  if (!response.ok) {
    const error=new Error(`Local service returned HTTP ${response.status}.`);
    error.status=response.status;
    throw error;
  }
  return response.json();
}

const TERMINAL=new Set(['succeeded','failed','outcome_unknown']);
const MODEL_STATUSES=new Set(['queued','running','response_received',...TERMINAL]);
const RECOVERY_KEY='proofkey.analysis.pending.v1';
const browserStorage=()=>{try{return globalThis.sessionStorage??null}catch{return null}};
function readRecovery(storage) {
  try {
    const value=JSON.parse(storage?.getItem(RECOVERY_KEY)??'null');
    if(value?.version===1&&['caseId','profileId','key'].every(key=>typeof value[key]==='string'&&value[key].length>0&&value[key].length<=256)
      &&Number.isInteger(value.stepIndex)&&value.stepIndex>=0&&(value.runId===null||typeof value.runId==='string'))return value;
  } catch {}
  return null;
}

/** Selection generations guard every asynchronous write, including failed requests. */
export class AnalysisSession {
  constructor({request=requestJSON, onChange=()=>{}, onDocument=()=>{}, onRestoredStep=()=>{}, schedule=(fn,delay)=>setTimeout(fn,delay), cancel=id=>clearTimeout(id),
    makeKey=()=>globalThis.crypto.randomUUID(), pollDelay=1000, storage=browserStorage()}={}) {
    this.request=request; this.onChange=onChange; this.onDocument=onDocument;this.onRestoredStep=onRestoredStep;
    this.schedule=schedule;this.cancel=cancel;this.makeKey=makeKey;this.pollDelay=pollDelay;this.storage=storage;
    this.pollTimer=null;this.modelContext=null;
    this.selection=0; this.documents=0; this.runs=0;
    this.state={catalog:[],capabilities:null,caseId:null,stepIndex:0,documentReady:false,step:null,run:null,pending:null,error:'',
      profileId:'offline',modelProfiles:[],modelsEnabled:false,modelAvailabilityReason:'Loading model profiles…',connectionError:'',recovery:readRecovery(storage)};
  }
  emit() { this.onChange(this.state); }
  invalidateRun() {
    ++this.runs;
    if(this.pollTimer!==null)this.cancel(this.pollTimer);
    this.pollTimer=null;this.modelContext=null;
    this.state.connectionError='';
  }
  remember(context,runId=null) {
    const value={version:1,caseId:context.caseId,stepIndex:context.stepIndex,profileId:context.profile.id,key:context.key,runId};
    this.state.recovery=value;
    try{this.storage?.setItem(RECOVERY_KEY,JSON.stringify(value))}catch{}
  }
  forget(context) {
    if(this.state.recovery?.key!==context.key)return;
    this.state.recovery=null;
    try{this.storage?.removeItem(RECOVERY_KEY)}catch{}
  }
  async loadModelProfiles() {
    let models;
    try{models=await this.request('/api/model-profiles')}
    catch{models={enabled:false,profiles:[],reason:'Model service unavailable; offline analysis remains available.'}}
    this.state.modelsEnabled=models.enabled===true;
    this.state.modelProfiles=Array.isArray(models.profiles)?models.profiles:[];
    this.state.modelAvailabilityReason=models.enabled?'Choose an available configured model.':(models.reason??'Model execution is not enabled on this local service.');
    this.emit();
  }
  async start() {
    this.state.pending='catalog'; this.emit();
    this.loadModelProfiles();
    try {
      const [catalog,capabilities]=await Promise.all([this.request('/api/catalog'),this.request('/api/capabilities')]);
      this.state.catalog=catalog.cases; this.state.capabilities=capabilities;
      this.state.pending=null; this.emit();
      if(catalog.cases.length) await this.selectCase(catalog.cases[0].id);
    } catch(error) {this.state.pending=null;this.state.error=error.message;this.emit();}
  }
  async selectCase(caseId) {
    const generation=++this.documents; ++this.selection; this.invalidateRun();
    Object.assign(this.state,{caseId,stepIndex:0,documentReady:false,step:null,run:null,pending:'case',error:''});this.emit();
    try {
      const result=await this.request(`/api/cases/${encodeURIComponent(caseId)}`);
      if(generation!==this.documents)return;
      this.onDocument(result.document);
      this.state.documentReady=true;
      await this.selectStep(0);
    } catch(error) {
      if(generation!==this.documents)return;
      this.state.pending=null;this.state.error=error.message;this.emit();
    }
  }
  async selectStep(index) {
    if(!this.state.documentReady||!Number.isInteger(index)||index<0)return;
    const generation=++this.selection; this.invalidateRun();
    const caseId=this.state.caseId;
    Object.assign(this.state,{stepIndex:index,step:null,run:null,pending:'step',error:''});this.emit();
    try {
      const result=await this.request(`/api/cases/${encodeURIComponent(caseId)}/steps/${index}`);
      if(generation!==this.selection)return;
      this.state.step=result;this.state.pending=null;this.emit();
    } catch(error) {
      if(generation!==this.selection)return;
      this.state.pending=null;this.state.error=error.message;this.emit();
    }
  }
  selectProfile(id) {
    if(id!=='offline'&&(!this.state.modelsEnabled||!this.state.modelProfiles.some(profile=>profile.id===id&&profile.available)))return false;
    if(id===this.state.profileId)return true;
    this.invalidateRun();this.state.profileId=id;this.state.run=null;this.state.error='';
    if(['run','model-submit','model-poll'].includes(this.state.pending))this.state.pending=null;
    this.emit();return true;
  }
  async analyze() {
    if(!this.state.step||this.state.pending)return;
    if(this.state.profileId!=='offline') {
      if(this.modelContext&&!TERMINAL.has(this.state.run?.status)) {
        if(!this.state.run)return this.submitModel(this.modelContext);
        return;
      }
      const profile=this.state.modelProfiles.find(item=>item.id===this.state.profileId&&item.available);
      if(!this.state.modelsEnabled||!profile)return;
      const context={generation:++this.runs,selection:this.selection,caseId:this.state.caseId,stepIndex:this.state.stepIndex,
        inputHash:this.state.step.input.input_hash,profile:{...profile},key:this.makeKey(),runId:null};
      this.modelContext=context;this.state.run=null;this.remember(context);
      return this.submitModel(context);
    }
    const generation=++this.runs, selection=this.selection;
    const {caseId,stepIndex,step}=this.state;
    this.state.pending='run';this.state.run=null;this.state.error='';this.emit();
    try {
      const result=await this.request('/api/runs',{method:'POST',headers:{'Content-Type':'application/json','X-ProofKey-Request':'analysis-v1'},body:JSON.stringify({case_id:caseId,step_index:stepIndex,expected_input_hash:step.input.input_hash,mode:'offline'})});
      if(generation!==this.runs||selection!==this.selection)return;
      this.state.run=result;this.state.pending=null;this.emit();
    } catch(error) {
      if(generation!==this.runs||selection!==this.selection)return;
      this.state.pending=null;this.state.error=error.message;this.emit();
    }
  }
  current(context) {return context===this.modelContext&&context.generation===this.runs&&context.selection===this.selection;}
  acceptModel(result,context) {
    if(result?.schema_version!=='proofkey-model-job-v1'||!MODEL_STATUSES.has(result.status)||typeof result.run_id!=='string'
      ||result.case_id!==context.caseId||result.step_index!==context.stepIndex||result.input_hash!==context.inputHash
      ||result.input?.input_hash!==context.inputHash||result.mode!=='model'||result.model_profile_id!==context.profile.id
      ||result.transaction?.idempotency_key!==context.key||result.transaction?.automatic_retries!==0||result.transaction?.operational_effects!==0
      ||(context.runId!==null&&result.run_id!==context.runId)
      ||(result.receipt&&(result.receipt.provider!==context.profile.provider||result.receipt.requested_model!==context.profile.model))
      ||(result.status==='succeeded'&&(!result.candidate||result.candidate.input_hash!==context.inputHash))) {
      const error=new Error('Model result identity or evidence binding mismatch. No result was attached.');error.bindingMismatch=true;throw error;
    }
    context.runId=result.run_id;this.state.run=result;this.state.pending=null;this.state.error='';this.state.connectionError='';
    if(TERMINAL.has(result.status))this.forget(context);
    else this.remember(context,result.run_id);
    this.emit();
    if(!TERMINAL.has(result.status))this.pollTimer=this.schedule(async()=>{this.pollTimer=null;await this.pollModel(context)},this.pollDelay);
  }
  modelError(error,context) {
    if(!this.current(context))return;
    this.state.pending=null;
    if(error.bindingMismatch)this.state.error=error.message;
    else this.state.connectionError=error.message;
    this.emit();
  }
  async submitModel(context) {
    if(!this.current(context))return;
    this.state.pending='model-submit';this.state.error='';this.state.connectionError='';this.emit();
    try {
      const result=await this.request('/api/model-runs',{method:'POST',headers:{'Content-Type':'application/json','X-ProofKey-Request':'analysis-v1','Idempotency-Key':context.key},
        body:JSON.stringify({case_id:context.caseId,step_index:context.stepIndex,expected_input_hash:context.inputHash,mode:'model',model_profile_id:context.profile.id})});
      if(this.current(context))this.acceptModel(result,context);
    } catch(error){this.modelError(error,context)}
  }
  async pollModel(context) {
    if(!this.current(context)||!context.runId||TERMINAL.has(this.state.run?.status))return;
    this.state.pending='model-poll';this.emit();
    try {
      const result=await this.request(`/api/model-runs/${encodeURIComponent(context.runId)}`);
      if(this.current(context))this.acceptModel(result,context);
    } catch(error){this.modelError(error,context)}
  }
  async reconnect() {
    const context=this.modelContext;
    if(!context||this.state.pending||TERMINAL.has(this.state.run?.status))return;
    if(this.pollTimer!==null)this.cancel(this.pollTimer);
    this.pollTimer=null;
    return context.runId?this.pollModel(context):this.submitModel(context);
  }
  async resumeLast() {
    const recovery=this.state.recovery;
    if(!recovery||this.state.pending)return;
    const profile=this.state.modelProfiles.find(item=>item.id===recovery.profileId);
    if(!this.state.catalog.some(item=>item.id===recovery.caseId)||!profile) {
      this.state.error='The saved analysis selection is unavailable on this service.';this.emit();return;
    }
    const originalProfile=this.state.profileId;
    const loading=this.selectCase(recovery.caseId),documentGeneration=this.documents,runGeneration=this.runs;
    await loading;
    if(!this.state.documentReady||this.documents!==documentGeneration||this.state.profileId!==originalProfile
      ||this.state.stepIndex!==0||this.runs!==runGeneration+1)return;
    if(recovery.stepIndex!==0){
      const selecting=this.selectStep(recovery.stepIndex),selectionGeneration=this.selection;
      await selecting;
      if(this.selection!==selectionGeneration||this.state.profileId!==originalProfile)return;
    }
    if(!this.state.step)return;
    // A saved request can be read/replayed without admitting a new paid run.
    // Availability gates Analyze, but must not hide an already accepted result.
    if(this.state.profileId!==recovery.profileId){
      this.invalidateRun();this.state.profileId=recovery.profileId;this.state.run=null;this.state.error='';this.emit();
    }
    this.onRestoredStep(recovery.stepIndex);
    const context={generation:++this.runs,selection:this.selection,caseId:recovery.caseId,stepIndex:recovery.stepIndex,
      inputHash:this.state.step.input.input_hash,profile:{...profile},key:recovery.key,runId:recovery.runId};
    this.modelContext=context;
    return this.reconnect();
  }
}

const json=value=>JSON.stringify(value,null,2);
const STATUS_LABELS={queued:'Queued',running:'Running',response_received:'Response received',succeeded:'Succeeded',failed:'Failed',outcome_unknown:'Outcome unknown'};
function renderReceipt(element,run) {
  element.replaceChildren();
  const receipt=run?.receipt,transaction=run?.transaction;
  if(!transaction)return;
  const display=value=>value===null||value===undefined?'Not reported':String(value);
  const rows=[['Requested model',receipt?.requested_model],['Observed model',receipt?.observed_model],['Provider',receipt?.provider],
    ['Provider request ID',receipt?.request_id],['Input tokens',receipt?.usage?.input_tokens],['Output tokens',receipt?.usage?.output_tokens],
    ['Latency (ms)',receipt?.latency_ms],['Reserved USD',transaction.reserved_usd],['Budget scope',transaction.budget_scope],
    ['Dispatch attempts',transaction.dispatch_attempts],['Automatic retries',transaction.automatic_retries],['Business effects',transaction.operational_effects],
    ['Created',run.created_at],['Started',run.started_at],['Finished',run.finished_at]];
  for(const [label,value] of rows){const term=document.createElement('dt'),detail=document.createElement('dd');term.textContent=label;detail.textContent=display(value);element.append(term,detail)}
}
function downloadJSON(value,name) {
  if(!value)return;
  const url=URL.createObjectURL(new Blob([json(value)+'\n'],{type:'application/json'}));
  const link=document.createElement('a');link.href=url;link.download=name;link.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}

export function mountAnalysis(root=document) {
  const el=id=>root.getElementById(id), viewer=el('source-viewer');let catalogRendered=false,profilesRendered='',syncingViewer=false;
  const session=new AnalysisSession({onDocument:doc=>viewer.load(doc),onRestoredStep:index=>{
    syncingViewer=true;
    try{viewer.goToStep(index)}finally{syncingViewer=false}
  },onChange:state=>{
    if(!catalogRendered&&state.catalog.length){
      for(const item of state.catalog){const option=document.createElement('option');option.value=item.id;option.textContent=item.title;el('case-select').append(option)}
      catalogRendered=true;
    }
    el('case-select').value=state.caseId??'';el('case-select').disabled=!state.catalog.length;
    const selected=state.catalog.find(item=>item.id===state.caseId);
    if(el('step-select').dataset.case!==state.caseId){
      el('step-select').replaceChildren();
      for(let i=0;i<=(selected?.steps??0);i++){const option=document.createElement('option');option.value=i;option.textContent=i===0?'0 · Initial evidence':`${i} · After source event`;el('step-select').append(option)}
      el('step-select').dataset.case=state.caseId??'';
    }
    el('step-select').value=state.stepIndex;el('step-select').disabled=!state.documentReady;
    viewer.hidden=!state.documentReady;
    el('selection-label').textContent=selected?`Step ${state.stepIndex} / ${selected.steps} · Family: ${selected.family_id} · Development examples`:'';
    const model=state.profileId!=='offline',profile=state.modelProfiles.find(item=>item.id===state.profileId),job=state.run?.mode==='model'?state.run:null;
    const pendingJob=job&&!TERMINAL.has(job.status),candidate=state.run?.candidate;
    const profilesKey=json([state.modelsEnabled,state.modelProfiles]);
    if(profilesRendered!==profilesKey){
      const offline=document.createElement('option');offline.value='offline';offline.textContent='Offline baseline · no model call';el('engine-select').replaceChildren(offline);
      for(const item of state.modelProfiles){const option=document.createElement('option');option.value=item.id;option.textContent=`${item.label} · ${item.provider} / ${item.model}${item.available?'':` · Unavailable (${item.reason??'not configured'})`}`;option.disabled=!state.modelsEnabled||!item.available;el('engine-select').append(option)}
      profilesRendered=profilesKey;
    }
    el('engine-select').value=state.profileId;el('engine-select').disabled=!state.capabilities;
    el('execution-tag').textContent=model?'Local · Provider model':'Local · Offline baseline';
    el('boundary-title').textContent=model?'Model analysis · 0 business effects.':'Offline analysis · 0 model calls.';
    el('run-title').textContent=model?'Run model analysis':'Run offline analysis';
    el('engine-note').textContent=model?(profile?.available?
      `Uses ${profile.provider} / ${profile.model}. Each new run reserves budget. Requests are never retried automatically.`:
      `${profile?.provider??'The configured provider'} / ${profile?.model??state.profileId} is unavailable (${profile?.reason??'not configured'}). Saved analyses can still be viewed; new model runs are disabled.`):
      `The deterministic fixture baseline uses only the evidence above. ${state.modelsEnabled?'Configured provider models are available in the selector.':state.modelAvailabilityReason}`;
    el('error').textContent=state.error;el('error').hidden=!state.error;
    const loading={catalog:'Loading catalog…',case:'Loading source document…',step:'Projecting evidence…',run:'Running offline baseline…','model-submit':'Submitting model analysis…'};
    const lifecycle={queued:'Request recorded. Waiting for model execution.',running:'Running model analysis…',response_received:'Provider response received. Validating and saving the result…',
      succeeded:'Analysis record saved. No messages sent or business actions executed.',failed:'Analysis failed. The saved record contains the failure details.',
      outcome_unknown:'The provider outcome is unknown. This request will not be retried automatically.'};
    el('status').textContent=loading[state.pending]??(job?lifecycle[job.status]:state.run?'Analysis record saved. No messages sent or business actions executed.':state.step?`Evidence ready for ${model?'model':'offline'} analysis.`:'Choose a source case.');
    el('analyze').disabled=!state.step||!!state.pending||!!pendingJob||!!state.connectionError||(model&&(!state.modelsEnabled||!profile?.available));
    el('analyze').textContent=model?(job?'Start new analysis · model':'Analyze this step · model'):'Analyze this step · offline';
    el('connection-warning').hidden=!state.connectionError;
    el('connection-message').textContent=state.connectionError?(job?`Connection interrupted. Last acknowledged status: ${STATUS_LABELS[job.status]}. ${state.connectionError}`:
      `Submission acknowledgement was not received. Reconnect reuses the original request key. ${state.connectionError}`):'';
    el('reconnect').textContent=job?'Reconnect to this analysis':'Recover this submission';el('reconnect').disabled=!!state.pending;
    el('resume-panel').hidden=!state.recovery||!!session.modelContext;el('resume-last').disabled=!!state.pending;
    el('input-json').textContent=state.step?json(state.step.input):'Evidence input will appear here.';
    el('input-hash').textContent=state.step?.input.input_hash??'No input selected';
    el('reference-json').textContent=state.step?json(state.step.reference):'Author reference will appear here.';
    el('source-json').textContent=state.step?json(state.step.source):'Source binding will appear here.';
    el('candidate-title').textContent=model?'Model result':'Baseline result';
    el('candidate-json').textContent=candidate?json(candidate):job&&TERMINAL.has(job.status)?'No valid candidate was produced. Inspect the saved error and transaction details.':model?'No valid candidate is available yet.':'Run the offline baseline to create a candidate.';
    el('comparison-json').textContent=state.run?.evaluation?json(state.run.evaluation):'No comparison yet.';
    el('run-id').textContent=state.run?`Saved run: ${state.run.run_id}`:'No run for this selection';
    el('candidate-state').textContent=candidate?`Inferred state: ${typeof candidate.state==='string'?candidate.state:json(candidate.state)}`:job?'No inferred state yet':'Awaiting analysis';
    el('job-status').hidden=!job;el('job-status').textContent=job?STATUS_LABELS[job.status]:'';el('job-status').dataset.status=job?.status??'';
    el('job-error').hidden=!job?.error;el('job-error').textContent=job?.error?`Error: ${typeof job.error==='string'?job.error:[job.error.code,job.error.phase].filter(Boolean).join(' · ')}`:'';
    el('transaction-details').hidden=!job;renderReceipt(el('receipt-summary'),job);
    el('transaction-json').textContent=job?json({transaction:job.transaction,receipt:job.receipt}):'';
    el('download-input').disabled=!state.step;el('download-reference').disabled=!state.step;el('download-source').disabled=!state.step;el('download-run').disabled=!state.run;
    el('capabilities-json').textContent=state.capabilities?json(state.capabilities):'Loading local capabilities…';
  }});
  el('case-select').addEventListener('change',event=>session.selectCase(event.target.value));
  viewer.addEventListener('stepchange',event=>{if(!syncingViewer)session.selectStep(event.detail.index)});
  el('step-select').addEventListener('change',event=>viewer.goToStep(Number(event.target.value)));
  el('analyze').addEventListener('click',()=>session.analyze());
  el('engine-select').addEventListener('change',event=>session.selectProfile(event.target.value));
  el('reconnect').addEventListener('click',()=>session.reconnect());
  el('resume-last').addEventListener('click',()=>session.resumeLast());
  for(const [id,key] of [['download-input','input'],['download-reference','reference'],['download-source','source']])el(id).addEventListener('click',()=>downloadJSON(session.state.step?.[key],`${session.state.caseId}-step-${session.state.stepIndex}-${key}.json`));
  el('download-run').addEventListener('click',()=>downloadJSON(session.state.run,`${session.state.run?.run_id??'analysis'}-run.json`));
  session.start();return session;
}

if(typeof document!=='undefined'&&document.getElementById('analysis-app'))mountAnalysis();
