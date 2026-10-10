export const PROFILE_VERSION = 'right-ontime-integration-profile-v1';
export const CAPABILITY_VERSION = 'proofkey-platform-capabilities-v1';
export const STORAGE_KEY = 'right-ontime.integration-profile.v1';
export const SURFACES = Object.freeze([
  {id:'cases',label:'Case records',description:'The source record and its revision.'},
  {id:'delivery',label:'Delivery operations',description:'Delivery status and carrier-side actions.'},
  {id:'scheduling',label:'Scheduling',description:'Available windows and booking outcomes.'},
  {id:'returns',label:'Returns',description:'Refusals, return records and handoff.'},
  {id:'messaging',label:'Customer messaging',description:'Communication records and acknowledgements.'},
  {id:'operator',label:'Operator inbox',description:'Human review and exception ownership.'},
]);
const isObject = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const text = (value,max) => typeof value === 'string' && value.length <= max && !/[\u0000-\u001f\u007f]/.test(value);

export function createProfile() {
  return {name:'',process_type:'reschedule',acknowledgement:'receipt_only',readback_required:true,
    mappings:Object.fromEntries(SURFACES.map(surface=>[surface.id,'']))};
}

export function validateProfile(profile,{requireMappings=true}={}) {
  if (!isObject(profile)) return [{field:'profile',message:'The profile must be an object.'}];
  const errors=[];
  if (!text(profile.name,100) || !profile.name.trim()) errors.push({field:'name',message:'Add a profile name of up to 100 characters.'});
  if (!['reschedule','refusal'].includes(profile.process_type)) errors.push({field:'process_type',message:'Choose reschedule or refusal.'});
  if (!['receipt_only','explicit_confirmation','source_readback'].includes(profile.acknowledgement)) errors.push({field:'acknowledgement',message:'Choose an acknowledgement meaning.'});
  if (typeof profile.readback_required!=='boolean') errors.push({field:'readback_required',message:'Choose whether source readback is required.'});
  for (const surface of SURFACES) {
    const value=profile.mappings?.[surface.id];
    if (!isObject(profile.mappings) || !text(value,240) || (requireMappings && !value.trim())) {
      errors.push({field:`mappings.${surface.id}`,message:`${surface.label}: add a mapping reference of up to 240 characters.`});
    }
  }
  return errors;
}

export function profileDocument(profile) {
  const errors=validateProfile(profile,{requireMappings:false});
  if (errors.length) throw Error(errors[0].message);
  return {schema_version:PROFILE_VERSION,status:'local_draft',runtime_activation:false,
    profile:{name:profile.name,process_type:profile.process_type,acknowledgement:profile.acknowledgement,
      readback_required:profile.readback_required,mappings:Object.fromEntries(SURFACES.map(({id})=>[id,profile.mappings[id]]))}};
}

export function saveProfile(storage,profile) {
  try {
    const serialized=JSON.stringify(profileDocument(profile));
    storage.setItem(STORAGE_KEY,serialized);
    if (storage.getItem(STORAGE_KEY)!==serialized) throw Error('Storage did not retain the draft.');
    return {ok:true};
  } catch (error) {
    return {ok:false,error:`Could not save the browser draft. ${error.message || 'Browser storage is unavailable.'} Your current edits are still here.`};
  }
}

export function loadProfile(storage) {
  try {
    const raw=storage.getItem(STORAGE_KEY);
    if (raw===null) return {ok:true,profile:null};
    const document=JSON.parse(raw);
    if (document?.schema_version!==PROFILE_VERSION || document.status!=='local_draft' || document.runtime_activation!==false) throw Error('Unsupported profile format.');
    return {ok:true,profile:profileDocument(document.profile).profile};
  } catch (error) {
    return {ok:false,error:`Could not load the browser draft. ${error.message || 'Browser storage is unavailable.'} Your current edits are still here.`};
  }
}

export async function readEnvironment(api) {
  const results=await Promise.allSettled([
    api('/capabilities',{method:'GET'}),api('/cases',{method:'GET'}),
  ]);
  const environment={capabilities:null,cases:null,errors:{},checked_at:new Date().toISOString()};
  ['capabilities','cases'].forEach((key,index)=>{
    const result=results[index];
    if (result.status==='fulfilled') environment[key]=result.value;
    else environment.errors[key]=result.reason?.message || 'Read failed.';
  });
  return environment;
}

export function runPreflight(profile,environment) {
  const caps=environment?.capabilities,checks=[];
  const add=(id,label,status,detail)=>checks.push({id,label,status,detail});
  const errors=validateProfile(profile);
  add('profile','Profile completeness',errors.length?'fail':'passed',errors.length?errors.map(error=>error.message).join(' '):'The six mapping references and process settings are present. References have not been resolved against external systems.');
  add('version','Capability contract',!caps?'unknown':caps.schema_version===CAPABILITY_VERSION?'passed':'fail',!caps?'The capability response is unavailable.':`Reported: ${caps.schema_version || 'no version'}. Expected: ${CAPABILITY_VERSION}.`);
  add('cases','Case service read',Array.isArray(environment?.cases?.cases)?'passed':'fail',Array.isArray(environment?.cases?.cases)?`Read ${environment.cases.cases.length} local case summaries. This does not verify upstream source readback.`:environment?.errors?.cases || 'No valid case list was returned.');
  add('mode','Execution environment',!caps?'unknown':caps.execution_mode==='local_sandbox'?'passed':'fail',!caps?'The environment mode is unavailable.':`Reported mode: ${caps.execution_mode || 'unknown'}. This profile remains a browser-local draft.`);
  const versionSupported=caps?.schema_version===CAPABILITY_VERSION;
  for (const surface of SURFACES) {
    const mapping=profile?.mappings?.[surface.id],adapter=Array.isArray(caps?.adapters)?caps.adapters.find(item=>item?.id===surface.id):null;
    let status='unknown',detail='This adapter was not reported by a supported capability response.';
    if (typeof mapping!=='string' || !mapping.trim()) {status='not_configured';detail='No local mapping reference has been entered.';}
    else if (versionSupported && adapter) {
      status=['connected','sandbox'].includes(adapter.status)?'passed':adapter.status==='not_connected'?'fail':adapter.status==='not_configured'?'not_configured':'unknown';
      detail=`Reported adapter: ${adapter.status || 'unknown'} · ${adapter.mode || 'unknown mode'}. ${status==='passed'?'Local capability availability only; the mapping reference has not been verified.':'The local draft cannot make this adapter available.'}`;
    }
    add(`mapping.${surface.id}`,surface.label,status,detail);
  }
  const readbackRequired=profile?.readback_required===true || profile?.acknowledgement==='source_readback';
  add('source_readback','Upstream source readback',readbackRequired?'unknown':'not_configured',readbackRequired?'Required by this profile. These read-only endpoints do not prove readback from the original carrier or communication system. Verify it during a separate integration review.':'Not required by this draft. Upstream source readback has not been checked.');
  return {scope:'local_read_only',runtime_activation:false,checked_at:environment?.checked_at || null,
    checks,counts:Object.fromEntries(['passed','fail','unknown','not_configured'].map(status=>[status,checks.filter(check=>check.status===status).length]))};
}
