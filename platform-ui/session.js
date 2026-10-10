const requestId = () => globalThis.crypto?.randomUUID?.() || `request-${Date.now()}-${Math.random().toString(16).slice(2)}`;

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
