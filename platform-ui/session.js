const requestId = () => globalThis.crypto?.randomUUID?.() || `request-${Date.now()}-${Math.random().toString(16).slice(2)}`;

const pendingModelStates = new Set(['queued','running','response_received']);

export function modelStatusView(job, snapshot) {
  const source=job.source, input=job.input, candidate=job.candidate;
  const hash=value=>typeof value==='string' && /^[a-f0-9]{64}$/.test(value);
  const current=Boolean(source?.kind==='platform_case' && job.case_id===snapshot.case_id &&
    source.case_id===snapshot.case_id && source.revision===snapshot.revision &&
    hash(snapshot.snapshot_hash) && source.snapshot_hash===snapshot.snapshot_hash &&
    input?.case_id===snapshot.case_id && input.step_index===snapshot.revision &&
    hash(job.input_hash) && input.input_hash===job.input_hash &&
    (!candidate || (candidate.schema_version==='proofkey-step-candidate-v1' && candidate.input_hash===job.input_hash)));
  const visible=current && job.status==='succeeded' && candidate;
  const counter=value=>Number.isInteger(value) && value>=0?value:null;
  return {current,transport:job.status || 'unavailable',coordination:visible?candidate.state:null,
    waitingFor:visible && Array.isArray(candidate.waiting_for)?candidate.waiting_for.filter(v=>typeof v==='string'):[],
    proposedAction:visible?candidate.next_action:null,
    dispatchAttempts:counter(job.transaction?.dispatch_attempts),
    automaticRetries:counter(job.transaction?.automatic_retries),
    operationalEffects:counter(job.transaction?.operational_effects)};
}

export class ModelPoller {
  constructor({api,onUpdate=()=>{},onError=()=>{},intervalMs=2000,maxPolls=120,
    schedule=globalThis.setTimeout.bind(globalThis),cancel=globalThis.clearTimeout.bind(globalThis)}) {
    this.api=api;this.onUpdate=onUpdate;this.onError=onError;
    this.intervalMs=Math.min(30000,Math.max(1000,intervalMs));
    this.maxPolls=Math.min(300,Math.max(1,maxPolls));
    this.schedule=schedule;this.cancel=cancel;this.records=new Map();this.epoch=0;this.key=null;this.disposed=false;
  }
  watch({caseId,generation,jobs=[]}) {
    if(this.disposed)return;
    const key=caseId?`${caseId}:${generation}`:null;
    if(this.key!==key){this.stop();this.key=key;}
    if(!caseId)return;
    const ids=new Set(jobs.map(job=>job.run_id || job.job_id).filter(Boolean));
    for(const [id,record] of this.records)if(!ids.has(id)){this.cancel(record.timer);this.records.delete(id);}
    for(const job of jobs){
      const id=job.run_id || job.job_id;if(!id)continue;
      const existing=this.records.get(id);
      if(!pendingModelStates.has(job.status)){
        if(existing){this.cancel(existing.timer);existing.status='done';}
        continue;
      }
      if(existing)continue;
      const record={id,caseId,epoch:this.epoch,status:'observing',attempts:0,error:'',timer:null};
      this.records.set(id,record);this.queue(record);
    }
  }
  getState(id) {const record=this.records.get(id);return record?{status:record.status,error:record.error,attempts:record.attempts}:null;}
  active(record) {return !this.disposed && record.epoch===this.epoch && this.records.get(record.id)===record;}
  queue(record) {record.timer=this.schedule(()=>this.poll(record),this.intervalMs);}
  async poll(record) {
    if(!this.active(record) || record.status!=='observing')return;
    record.timer=null;record.attempts++;
    try {
      const job=await this.api(`/model-runs/${encodeURIComponent(record.id)}`,{method:'GET'});
      if(!this.active(record) || record.status!=='observing')return;
      if(job.run_id!==record.id || job.case_id!==record.caseId)throw Error('Model response does not match the selected case and run.');
      const pending=pendingModelStates.has(job.status);
      if(!pending)record.status='done';
      else if(record.attempts>=this.maxPolls){record.status='paused';record.error='Observation limit reached. Refresh run to continue.';}
      this.onUpdate(job,{caseId:record.caseId,runId:record.id});
      if(this.active(record) && record.status==='observing')this.queue(record);
    } catch(error) {
      if(!this.active(record))return;
      record.status='paused';record.error=error.message || 'Model observation failed.';
      this.onError(error,{caseId:record.caseId,runId:record.id});
    }
  }
  retry(id) {
    const record=this.records.get(id);
    if(!record || this.disposed)return;
    this.cancel(record.timer);record.error='';record.attempts=0;record.status='observing';this.queue(record);
  }
  stop() {this.epoch++;for(const record of this.records.values())this.cancel(record.timer);this.records.clear();this.key=null;}
  dispose() {this.stop();this.disposed=true;}
}

export function needsReview(item) {
  return item.states?.lifecycle !== 'resolved' && (
    ['in_review','awaiting_approval','ready'].includes(item.states?.lifecycle) ||
    ['proposed','blocked','approved'].includes(item.states?.decision));
}

export function normalizeMediaRun(run) {
  return {...run,source_sha256:run.source_sha256 || run.asset_sha256,output_text:run.output_text || run.output?.text || run.text};
}

export function canReview(decision, verdict) {
  if(verdict==='reject')return true;
  if(['operator_review','request_information'].includes(decision.action?.type))return true;
  return decision.action?.type==='reschedule_delivery' && !decision.checks?.some(c=>c.passed===false);
}

export function reviewedMediaMessage(input, reviewed) {
  const run=normalizeMediaRun(input);
  if(!reviewed)throw Error('Confirm you reviewed this derived text before using it.');
  if(run.status!=='succeeded' || typeof run.output_text!=='string' || !run.output_text.trim())throw Error('Successful processing with non-empty text is required.');
  const label=run.mode==='asr'?'ASR':'image analysis';
  const text=`[Operator-reviewed ${label} of asset ${run.asset_id} SHA256 ${run.source_sha256}]\n${run.output_text}`;
  if(text.length>4096)throw Error('Reviewed source text exceeds the 4096-character event limit.');
  return text;
}

export function createAPI(fetcher = globalThis.fetch.bind(globalThis)) {
  return async (path, options = {}) => {
    const {method = 'GET', body, idempotencyKey, headers = {}, raw = false} = options;
    const requestHeaders = {...headers};
    if (method !== 'GET') {
      requestHeaders['X-ProofKey-Request'] = 'platform-v1';
      requestHeaders['Idempotency-Key'] = idempotencyKey || requestId();
      if (!raw) requestHeaders['Content-Type'] = 'application/json';
    }
    const response = await fetcher(`/api/platform${path}`, {method, headers:requestHeaders, cache:'no-store', body:body === undefined ? undefined : raw ? body : JSON.stringify(body)});
    const value = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(typeof value.error === 'string' ? value.error : value.error?.code || value.message || `Request failed (HTTP ${response.status})`);
      error.status = response.status; throw error;
    }
    return value;
  };
}

export class PlatformSession {
  constructor(api, onChange = () => {}) {
    this.api=api; this.onChange=onChange; this.selectedId=null; this.detail=null;
    this.error=''; this.generation=0; this.drafts=new Map(); this.pending=new Map(); this.busy=false;
  }
  notify() { this.onChange(this); }
  getDraft(name) { return this.drafts.get(`${this.selectedId}:${name}`) || {}; }
  setDraft(name, value) { this.drafts.set(`${this.selectedId}:${name}`,value); }
  async select(id) {
    const generation=++this.generation;
    if (id !== this.selectedId) this.detail=null;
    this.selectedId=id; this.error=''; this.notify();
    try {
      const value=await this.api(`/cases/${encodeURIComponent(id)}`);
      if (generation===this.generation) {this.detail=value.case || value; this.error=''; this.notify();}
      return value;
    } catch(error) {
      if (generation===this.generation) {this.error=error.message; this.notify();}
      throw error;
    }
  }
  async reload() { if(this.selectedId) return this.select(this.selectedId); }
  async mutate(route, body, options={}) {
    const id=this.selectedId, generation=this.generation;
    if (!id) throw Error('Select a case first.');
    const signature=`${id}:${route}:${options.signature || JSON.stringify(body)}`;
    const key=this.pending.get(signature) || requestId(); this.pending.set(signature,key);
    this.busy=true; this.error=''; this.notify();
    try {
      const result=await this.api(`/cases/${encodeURIComponent(id)}/${route}`,{...options,method:'POST',body,idempotencyKey:key});
      this.pending.delete(signature);
      if(generation===this.generation && id===this.selectedId) await this.reload();
      return result;
    } catch(error) {
      if(generation===this.generation && id===this.selectedId) {
        if(error.status===409) {this.pending.delete(signature);try {await this.reload();} catch { /* Keep the original failure. */ }}
        this.error=error.message;this.notify();
      }
      throw error;
    } finally {this.busy=false;this.notify();}
  }
}
