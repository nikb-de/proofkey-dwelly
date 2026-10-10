import './viewer.js';

async function requestJSON(path, options = {}) {
  const response = await fetch(path, {cache:'no-store', ...options});
  if (!response.ok) throw new Error(`Local service returned HTTP ${response.status}.`);
  return response.json();
}

/** Selection generations guard every asynchronous write, including failed requests. */
export class AnalysisSession {
  constructor({request=requestJSON, onChange=()=>{}, onDocument=()=>{}}={}) {
    this.request=request; this.onChange=onChange; this.onDocument=onDocument;
    this.selection=0; this.documents=0; this.runs=0;
    this.state={catalog:[],capabilities:null,caseId:null,stepIndex:0,documentReady:false,step:null,run:null,pending:null,error:''};
  }
  emit() { this.onChange(this.state); }
  async start() {
    this.state.pending='catalog'; this.emit();
    try {
      const [catalog,capabilities]=await Promise.all([this.request('/api/catalog'),this.request('/api/capabilities')]);
      this.state.catalog=catalog.cases; this.state.capabilities=capabilities;
      this.state.pending=null; this.emit();
      if(catalog.cases.length) await this.selectCase(catalog.cases[0].id);
    } catch(error) {this.state.pending=null;this.state.error=error.message;this.emit();}
  }
  async selectCase(caseId) {
    const generation=++this.documents; ++this.selection; ++this.runs;
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
    const generation=++this.selection; ++this.runs;
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
  async analyze() {
    if(!this.state.step||this.state.pending)return;
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
}

const json=value=>JSON.stringify(value,null,2);
function downloadJSON(value,name) {
  if(!value)return;
  const url=URL.createObjectURL(new Blob([json(value)+'\n'],{type:'application/json'}));
  const link=document.createElement('a');link.href=url;link.download=name;link.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}

export function mountAnalysis(root=document) {
  const el=id=>root.getElementById(id), viewer=el('source-viewer');let catalogRendered=false;
  const session=new AnalysisSession({onDocument:doc=>viewer.load(doc),onChange:state=>{
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
    el('error').textContent=state.error;el('error').hidden=!state.error;
    el('status').textContent=state.pending?({catalog:'Loading catalog…',case:'Loading source document…',step:'Projecting evidence…',run:'Running offline baseline…'}[state.pending]):state.run?'Analysis record saved. No messages sent or business actions executed.':state.step?'Evidence ready for offline analysis.':'Choose a source case.';
    el('analyze').disabled=!state.step||!!state.pending;
    el('input-json').textContent=state.step?json(state.step.input):'Evidence input will appear here.';
    el('input-hash').textContent=state.step?.input.input_hash??'No input selected';
    el('reference-json').textContent=state.step?json(state.step.reference):'Author reference will appear here.';
    el('source-json').textContent=state.step?json(state.step.source):'Source binding will appear here.';
    el('candidate-json').textContent=state.run?json(state.run.candidate):'Run the offline baseline to create a candidate.';
    el('comparison-json').textContent=state.run?json(state.run.evaluation):'No comparison yet.';
    el('run-id').textContent=state.run?`Saved run: ${state.run.run_id}`:'No run for this selection';
    el('candidate-state').textContent=state.run?`Inferred state: ${typeof state.run.candidate.state==='string'?state.run.candidate.state:json(state.run.candidate.state)}`:'Awaiting analysis';
    el('download-input').disabled=!state.step;el('download-reference').disabled=!state.step;el('download-source').disabled=!state.step;el('download-run').disabled=!state.run;
    el('capabilities-json').textContent=state.capabilities?json(state.capabilities):'Loading local capabilities…';
  }});
  el('case-select').addEventListener('change',event=>session.selectCase(event.target.value));
  viewer.addEventListener('stepchange',event=>session.selectStep(event.detail.index));
  el('step-select').addEventListener('change',event=>viewer.goToStep(Number(event.target.value)));
  el('analyze').addEventListener('click',()=>session.analyze());
  for(const [id,key] of [['download-input','input'],['download-reference','reference'],['download-source','source']])el(id).addEventListener('click',()=>downloadJSON(session.state.step?.[key],`${session.state.caseId}-step-${session.state.stepIndex}-${key}.json`));
  el('download-run').addEventListener('click',()=>downloadJSON(session.state.run,`${session.state.run?.run_id??'analysis'}-run.json`));
  session.start();return session;
}

if(typeof document!=='undefined'&&document.getElementById('analysis-app'))mountAnalysis();
