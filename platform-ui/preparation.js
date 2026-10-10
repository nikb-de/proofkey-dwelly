import {createAPI} from './session.js';
import {SURFACES,CAPABILITY_VERSION,PROFILE_VERSION,createProfile,profileDocument,saveProfile,loadProfile,readEnvironment,runPreflight} from './preparation-model.js';

const $=id=>document.getElementById(id);
const api=createAPI();
const storage={getItem:key=>globalThis.localStorage.getItem(key),setItem:(key,value)=>globalThis.localStorage.setItem(key,value)};
let environment=null,report=null,reading=false,dirty=false;
const human=value=>String(value ?? 'unknown').replaceAll('_',' ');
const element=(tag,text,className)=>{const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(className)node.className=className;return node;};
const badge=(text,status)=>element('span',text,`tag ${status || ''}`);

function notice(message,error=false) {
  const node=$('preparation-notice');node.textContent=message;node.hidden=!message;
  node.classList.toggle('error',error);node.setAttribute('role',error?'alert':'status');
}
function getProfile() {
  return {name:$('profile-name').value,process_type:$('process-type').value,acknowledgement:$('acknowledgement').value,
    readback_required:$('readback-required').checked,mappings:Object.fromEntries(SURFACES.map(({id})=>[id,$(`mapping-${id}`).value]))};
}
function setProfile(profile) {
  $('profile-name').value=profile.name;$('process-type').value=profile.process_type;
  $('acknowledgement').value=profile.acknowledgement;$('readback-required').checked=profile.readback_required;
  for (const {id} of SURFACES) $(`mapping-${id}`).value=profile.mappings[id];
  dirty=false;$('draft-state').textContent='Loaded browser draft';invalidateReport();preview();
}
function preview() {
  try {$('profile-preview').textContent=JSON.stringify(profileDocument(getProfile()),null,2);}
  catch (error) {$('profile-preview').textContent=error.message;}
}
function invalidateReport() {
  report=null;$('preflight-results').replaceChildren();$('preflight-counts').hidden=true;
  $('preflight-status').textContent='Not run for the current draft and environment.';
}
function buildMappings() {
  for (const surface of SURFACES) {
    const row=element('div',undefined,'mapping-field'),heading=element('div');
    const label=element('label',surface.label);label.htmlFor=`mapping-${surface.id}`;
    heading.append(label,element('p',surface.description,'field-help'));
    const input=element('input');input.id=`mapping-${surface.id}`;input.name=`mapping_${surface.id}`;
    input.type='text';input.maxLength=240;input.autocomplete='off';input.placeholder='Mapping reference';
    row.append(heading,input);$('mapping-fields').append(row);
  }
}
function renderEnvironment() {
  const caps=environment?.capabilities,caseList=environment?.cases?.cases;
  const facts=$('environment-facts');facts.replaceChildren();
  const data=[['Execution mode',caps?human(caps.execution_mode):'Unavailable',caps?'Service-reported environment; no activation from this screen.':'Refresh to retry the capability read.'],
    ['Operator identity',caps?human(caps.authentication):'Unknown','Local access is not production customer authentication.'],
    ['Case service',Array.isArray(caseList)?`${caseList.length} case${caseList.length===1?'':'s'} readable`:'Read unavailable',Array.isArray(caseList)?'Read-only case summaries; no source content fetched.':environment?.errors?.cases || 'The service has not returned a valid case list.']];
  for (const [label,value,description] of data) {
    const card=element('article',undefined,'fact');card.append(element('p',label,'meta'),element('strong',value),element('p',description,'meta'));facts.append(card);
  }
  $('environment-meta').textContent=`${environment?.checked_at?'Read at '+new Date(environment.checked_at).toLocaleTimeString():''}${caps?' · Contract: '+(caps.schema_version || 'unknown'):' · Capabilities unavailable: '+(environment?.errors?.capabilities || 'No valid response')}`;
  const adapters=$('adapter-list');adapters.replaceChildren();
  for (const surface of SURFACES) {
    const adapter=Array.isArray(caps?.adapters)?caps.adapters.find(item=>item?.id===surface.id):null;
    const card=element('article',undefined,'adapter'),top=element('div',undefined,'adapter-top');
    top.append(element('h3',surface.label),badge(human(adapter?.status || 'unknown'),adapter?.status));
    card.append(top,element('p',adapter?`Mode: ${human(adapter.mode)}`:'Not reported by the service.'));adapters.append(card);
  }
  const services=$('service-capabilities');services.replaceChildren();
  const profiles=Array.isArray(caps?.models?.profiles)?caps.models.profiles:[];
  const servicesData=[['Models',caps?.models?`Service enabled: ${caps.models.enabled===true?'yes':'no'}. ${profiles.length} profile(s) reported. Provider access and permission to run must be checked separately.`:'No model capability response.'],
    ['Media',caps?.media?Object.entries(caps.media).map(([key,value])=>`${human(key)}: ${human(value?.status || (value?.enabled===true?'enabled':'not configured'))}`).join(' · ') || 'No media capabilities reported.':'No media capability response.'],
    ['Communications',caps?.communications?`Provider connections: ${caps.communications.provider_connections===true?'reported available':caps.communications.provider_connections===false?'none':'unknown'}. Outbound enabled: ${caps.communications.outbound_enabled===true?'yes':caps.communications.outbound_enabled===false?'no':'unknown'}. Local ingress does not establish a live provider connection.`:'No communication capability response.']];
  for (const [label,description] of servicesData) {const card=element('article');card.append(element('h3',label),element('p',description));services.append(card);}
}
async function refresh() {
  reading=true;$('refresh-environment').disabled=true;$('run-preflight').disabled=true;
  $('environment-meta').textContent='Reading current capabilities and case summaries…';invalidateReport();
  try {environment=await readEnvironment(api);renderEnvironment();}
  finally {reading=false;$('refresh-environment').disabled=false;$('run-preflight').disabled=false;}
}
function renderReport() {
  const counts=$('preflight-counts');counts.replaceChildren();counts.hidden=false;
  const labels={passed:'Passed',fail:'Failed',unknown:'Unknown',not_configured:'Not configured'};
  for (const [status,count] of Object.entries(report.counts)) counts.append(badge(`${count} ${labels[status].toLowerCase()}`,status));
  const parent=$('preflight-results');parent.replaceChildren();
  for (const check of report.checks) {
    const row=element('article',undefined,'check');row.append(element('h3',check.label),badge(labels[check.status],check.status),element('p',check.detail));parent.append(row);
  }
  $('preflight-status').textContent=`Local checks completed at ${new Date(report.checked_at).toLocaleTimeString()}. ${report.counts.fail+report.counts.unknown+report.counts.not_configured?'Review the unresolved items below.':'Review scope and limitations below.'}`;
}
buildMappings();
$('profile-form').addEventListener('input',()=>{dirty=true;$('draft-state').textContent='Unsaved local draft';notice('');invalidateReport();preview();});
$('profile-form').addEventListener('change',()=>{dirty=true;$('draft-state').textContent='Unsaved local draft';invalidateReport();preview();});
$('profile-form').addEventListener('submit',event=>{
  event.preventDefault();const result=saveProfile(storage,getProfile());
  if(result.ok){dirty=false;$('draft-state').textContent='Saved in this browser';notice('Draft saved in this browser. The running service has not changed.');}
  else notice(result.error,true);
});
$('load-profile').addEventListener('click',()=>{
  const result=loadProfile(storage);
  if(!result.ok){notice(result.error,true);return;}
  if(!result.profile){notice('There is no saved draft in this browser. Your current edits are still here.');return;}
  if(dirty && !globalThis.confirm('Replace the current unsaved edits with the saved browser draft?'))return;
  setProfile(result.profile);notice('Saved browser draft loaded. Run a new local preflight for this draft.');
});
$('refresh-environment').addEventListener('click',async()=>{if(!reading)await refresh();});
$('run-preflight').addEventListener('click',async()=>{
  if(reading)return;
  await refresh();report=runPreflight(getProfile(),environment);renderReport();
});
$('export-profile').addEventListener('click',()=>{
  try {
    const document=profileDocument(getProfile());
    const handoff={...document,exported_at:new Date().toISOString(),preflight:report,
      contract:{profile:PROFILE_VERSION,expected_capabilities:CAPABILITY_VERSION},
      limitations:['Local draft only; no runtime activation.','Mapping references are not validated external connections.','No live integration test or full regression has been run.','No external action, communication or physical delivery is confirmed.']};
    const blob=new Blob([JSON.stringify(handoff,null,2)+'\n'],{type:'application/json'});
    const url=URL.createObjectURL(blob),link=element('a');link.href=url;link.download='right-ontime-integration-draft.json';
    documentElementDownload(link);setTimeout(()=>URL.revokeObjectURL(url),1000);
    notice('Draft JSON download requested. The profile has not been activated.');
  } catch(error) {notice(`Could not export the draft. ${error.message} Your edits are still here.`,true);}
});
function documentElementDownload(link) {document.body.append(link);link.click();link.remove();}
const saved=loadProfile(storage);
if(saved.ok && saved.profile)setProfile(saved.profile);
else {setProfile(createProfile());$('draft-state').textContent='Unsaved local draft';if(!saved.ok)notice(saved.error,true);}
preview();await refresh();
