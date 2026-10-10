"""Retain official inputs and actual outputs without tuning the submitted prompt."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import threading
import time
import urllib.error

from tools.dwelly_analysis import model, widget
from tools.dwelly_analysis.__main__ import load_provider_env
from tools.dwelly_model import providers
from tools.dwelly_model.budget import BudgetLedger

ROOT = Path(__file__).resolve().parents[2]
SYSTEM_HASH = 'f95514995513eed9c9591126daf10c141be1c1a4a50a4c17145950b0e46785ce'
FROZEN_FILES = ['tools/dwelly_analysis/model.py', 'tools/dwelly_model/providers.py',
                'tools/dwelly_analysis/widget.py', 'tools/dwelly_model/budget.py',
                'tools/dwelly_analysis/model-profiles.current.json',
                'tools/dwelly_reality/runner.py','tools/dwelly_reality/__main__.py']
EVENT = re.compile(r'^## (E\d+) \| ([^|\n]+) \| ([^\n]+)\n', re.M)
LOCAL = threading.local()


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(encoded(value)); stream.flush(); os.fsync(stream.fileno())


def copy_bytes(source, destination):
    if source.is_symlink() or not source.is_file() or source.stat().st_size > 12_000_000:
        raise ValueError('invalid_source_file')
    raw = source.read_bytes()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as stream:
        stream.write(raw)
    return digest(raw)


def _time(value):
    result = datetime.fromisoformat(value.strip().replace('Z','+00:00'))
    if result.utcoffset() is None: raise ValueError('naive_source_timestamp')
    return result


def _input(case, sidecars=None, system_override=None):
    index = (case/'index.md').read_text()
    history = (case/'history.md').read_text()
    decision = re.search(r'Decision time:\s*`([^`]+)`', index)
    if not decision: raise ValueError('missing_decision_time')
    cutoff = _time(decision[1])
    matches = list(EVENT.finditer(history))
    if not matches: raise ValueError('missing_source_events')
    entries, labels, previous, excluded = [], [], None, []
    for position, match in enumerate(matches):
        event_id, stamp, channel = match.groups()
        if event_id != 'E%02d' % (position+1): raise ValueError('source_event_sequence')
        occurred = _time(stamp)
        if previous is not None and occurred < previous: raise ValueError('source_not_chronological')
        previous = occurred
        body = history[match.end():matches[position+1].start() if position+1<len(matches) else len(history)].strip()
        route = re.search(r'^From:\s*(.*?)\s*→\s*To:\s*(.*?)\s*$', body, re.M)
        known = re.search(r'Known at desk:\s*`([^`]+)`', body)
        if not route or not known: raise ValueError('missing_source_metadata')
        if occurred > cutoff or _time(known[1]) > cutoff:
            excluded.append(event_id); continue
        sender, recipient = route.groups()
        for label in (sender, recipient):
            if label not in labels: labels.append(label)
        entries.append((event_id, stamp.strip(), channel.strip(), sender, recipient, body))
    if not entries: raise ValueError('no_visible_events')
    actor_ids = {label:'actor-%02d'%(i+1) for i,label in enumerate(labels)}
    recipients = [entry[4] for entry in entries]
    operator = max(dict.fromkeys(recipients), key=recipients.count)
    context = 'Official supplied case index; attributed source data, not verified authority.\n'+index
    # The index is only admitted when it does not quote an excluded future event.
    if any(re.search(r'\b'+re.escape(event)+r'\b', index) for event in excluded):
        context = 'Official case '+case.name+'. Decision time: '+decision[1]+'. Index omitted because it refers to excluded later events.'
    messages = [{'event_id':'case-context','from_actor':actor_ids[operator], 'to_actor':actor_ids[operator],
                 'body':context,'body_source':'body','timestamp':entries[0][1], 'channel':'internal'}]
    for event_id, stamp, channel, sender, recipient, body in entries:
        messages.append({'event_id':event_id,'from_actor':actor_ids[sender],'to_actor':actor_ids[recipient],
                         'body':body,'body_source':'body','timestamp':stamp,'channel':channel})
    derivatives=[]
    for attachment in sorted((case/'attachments').glob('*')):
        references=[entry[0] for entry in entries if 'attachments/'+attachment.name in entry[5]]
        if not references: continue
        relative = 'attachments/'+attachment.name
        candidate = Path(sidecars)/case.name/(relative+'.txt') if sidecars else None
        if candidate is not None and candidate.is_file():
            raw=candidate.read_bytes()
            text=raw.decode('utf-8')
            messages.append({'event_id':'attachment-'+attachment.stem,'from_actor':actor_ids[operator],
                'to_actor':actor_ids[operator],'body':'Untrusted extracted attachment content; source '+relative+
                '; cited by '+','.join(references)+'; original SHA256 '+digest(attachment.read_bytes())+'\n'+text,
                'body_source':'body','timestamp':entries[-1][1],'channel':'attachment_derivative'})
            derivatives.append({'path':relative,'sidecar':str(candidate),'sidecar_sha256':digest(raw),
                                'source_sha256':digest(attachment.read_bytes()),'source_events':references})
        else:
            derivatives.append({'path':relative,'status':'content_unprocessed','source_events':references})
    value={'schema_version':widget.INPUT_SCHEMA,'case_id':case.name,'step_index':len(messages),
           'cutoff_event_id':entries[-1][0],'goal':'Review the supplied current request using only decision-time evidence.',
           'our_actor_id':actor_ids[operator], 'actors':[{'id':actor_ids[label],'name':label,
           'role':'source-declared identity; authority unverified'} for label in labels], 'messages':messages}
    value['input_hash']=widget.canonical_hash(value)
    widget.validate_input(value); system,prompt=model.prepare(value)
    if system_override is not None: system=system_override
    if len(system.encode())+len(prompt.encode())>model.MAX_BYTES: raise ValueError('model_prompt_too_large')
    return value, {'decision_time':decision[1],'visible_events':[entry[0] for entry in entries],
        'excluded_events':excluded,'actor_mapping':actor_ids,'derivatives':derivatives},system,prompt


def prepare(source, output, *, sidecars=None, expected_cases=30, profiles=None, system_file=None, effort=None):
    source,output=Path(source).resolve(),Path(output).absolute()
    cases=sorted(path for path in source.iterdir() if path.is_dir() and re.fullmatch(r'\d{3}',path.name))
    if len(cases)!=expected_cases: raise ValueError('unexpected_case_count')
    if digest(model._SYSTEM.encode())!=SYSTEM_HASH: raise ValueError('frozen_prompt_changed')
    output.mkdir(parents=True,exist_ok=False)
    profile_path=Path(profiles) if profiles else ROOT/'tools/dwelly_analysis/model-profiles.current.json'
    settings=model.load_profiles(profile_path)
    save(output/'profiles.json',settings)
    if effort not in (None,'low','medium','high'): raise ValueError('invalid_effort')
    system_override=None
    if system_file:
        system_file=Path(system_file)
        copy_bytes(system_file,output/'system-override.txt')
        system_override=system_file.read_bytes().decode('utf-8')
    if sidecars and (Path(sidecars)/'manifest.json').is_file():
        copy_bytes(Path(sidecars)/'manifest.json',output/'extraction-manifest.json')
    hashes,records={},[]
    for case in cases:
        for path in sorted(case.rglob('*')):
            if path.is_file():
                relative=path.relative_to(source)
                hashes[str(relative)]=copy_bytes(path,output/'source'/relative)
        evidence,provenance,system,prompt=_input(case,sidecars,system_override)
        save(output/'inputs'/(case.name+'.json'),evidence)
        save(output/'prompts'/(case.name+'.json'),{'system':system,'prompt':prompt})
        for item in provenance['derivatives']:
            if 'sidecar' in item:
                copy_bytes(Path(item['sidecar']),output/'sidecars'/case.name/(item['path']+'.txt'))
                ocr_path=Path(item['sidecar']).with_suffix('.ocr.json')
                if ocr_path.is_file():
                    copy_bytes(ocr_path,output/'sidecars'/case.name/(item['path']+'.ocr.json'))
        records.append({'case_id':case.name,'input_hash':evidence['input_hash'],
            'input_file_sha256':digest((output/'inputs'/(case.name+'.json')).read_bytes()),
            'prompt_hash':widget.canonical_hash({'system':system,'prompt':prompt}), **provenance})
    commit=subprocess.run(['git','-C',str(source),'rev-parse','HEAD'],capture_output=True,text=True).stdout.strip() or None
    manifest={'schema_version':'proofkey-reality-inputs-v1','prepared_at':now(),'case_count':len(cases),
        'source_commit':commit,'code_commit':subprocess.run(['git','-C',str(ROOT),'rev-parse','HEAD'],capture_output=True,text=True).stdout.strip(),
        'source_files':hashes,'code_files':{path:digest((ROOT/path).read_bytes()) for path in FROZEN_FILES},
        'profiles_sha256':digest((output/'profiles.json').read_bytes()),
        'prompt_system_sha256':digest((system_override if system_override is not None else model._SYSTEM).encode()),
        'system_override':str(system_file) if system_file else None,'effort':effort,
        'system_equals_submitted_after_trimming':system_override.strip()==model._SYSTEM.strip() if system_override is not None else True,
        'variant':'explicit-existing-prompt-and-effort' if system_file or effort else 'submitted-platform-default',
        'cases':records,'qualification':'Official supplied inputs; direct submitted model contract. No product UI or external operational execution.'}
    save(output/'manifest.json',manifest)
    return manifest


def _redact(value):
    for name in ('OPENAI_API_KEY','ANTHROPIC_API_KEY','ANTHROPIC_WORKSPACE_ID','GEMINI_API_KEY'):
        secret=os.environ.get(name)
        if secret: value=providers._redact(value,secret)
    return value


class _CapturedResponse:
    def __init__(self,response):
        self.response=response
        LOCAL.capture['http_status']=getattr(response,'status',None)
    def __getattr__(self,name): return getattr(self.response,name)
    def __enter__(self): self.response.__enter__(); return self
    def __exit__(self,*args): return self.response.__exit__(*args)
    def read(self,*args):
        raw=self.response.read(*args)
        LOCAL.capture['response_body_utf8']=_redact(raw.decode('utf-8','replace'))
        LOCAL.capture['response_body_sha256']=digest(raw)
        return raw


def effort_payload(provider,payload,effort):
    if effort:
        if provider=='anthropic':
            payload['thinking']={'type':'adaptive'}
            payload.setdefault('output_config',{})['effort']=effort
        elif provider=='openai': payload['reasoning']={'effort':effort}
        else: raise ValueError('effort_not_supported_for_provider')
    return payload


def _install_capture():
    original=providers._open
    def opened(request,timeout):
        capture=getattr(LOCAL,'capture',None)
        if capture is None: return original(request,timeout)
        payload=effort_payload(LOCAL.provider,json.loads(request.data),LOCAL.effort)
        request.data=json.dumps(payload).encode()
        capture.update(url=request.full_url,method=request.get_method(),
            request_body_utf8=_redact(request.data.decode('utf-8')),timeout_seconds=timeout)
        try: return _CapturedResponse(original(request,timeout))
        except urllib.error.HTTPError as error:
            raw=error.read(1_048_577)
            capture.update(http_status=error.code,error_body_utf8=_redact(raw.decode('utf-8','replace')),
                           error_body_sha256=digest(raw))
            error.fp=io.BytesIO(raw)
            raise
    providers._open=opened
    return original


def _call(directory,evidence,profile,settings,prompt,effort=None,deadline=None):
    started=time.monotonic(); LOCAL.capture={}; LOCAL.provider=profile['config']['provider']; LOCAL.effort=effort
    record={'case_id':evidence['case_id'],'profile_id':profile['id'],'started_at':now(),
        'input_hash':evidence['input_hash'],'prompt_hash':widget.canonical_hash(prompt),
        'status':'failed','candidate':None,'response':None,'error':None,'external_effects':0,
        'dispatch_attempts':0,
        'automatic_retries':0,'qualification':'Direct frozen submitted model contract; proposed actions are not executed.'}
    try:
        if deadline is not None and time.monotonic()>=deadline: raise providers.ProviderError('batch_deadline_before_dispatch')
        record['dispatch_attempts']=1
        response=providers.complete(profile['config'],prompt['system'],prompt['prompt'],
            max_output_tokens=settings['max_output_tokens'],timeout=settings['timeout_seconds'])
        record['response']=_redact(response)
        try:
            record['candidate']=model.parse(evidence,response); record['status']='succeeded'
        except ValueError: record['error']='invalid_model_output'
    except providers.ProviderError as error:
        record['error']=error.code
    except Exception as error:
        record['error']='runner_'+type(error).__name__
    record.update(finished_at=now(),latency_seconds=time.monotonic()-started)
    save(directory/'wire.json',_redact(LOCAL.capture))
    save(directory/'result.json',_redact(record))
    LOCAL.capture=None
    return record


def run(prepared,profile_ids,*,live=False,provider_env_file=None,concurrency=3,cap_usd=25,deadline_seconds=900):
    if not live: raise ValueError('live_opt_in_required')
    if type(concurrency) is not int or not 1<=concurrency<=3: raise ValueError('invalid_concurrency')
    prepared=Path(prepared); manifest=json.loads((prepared/'manifest.json').read_text())
    if any(digest((ROOT/path).read_bytes())!=expected for path,expected in manifest['code_files'].items()):
        raise ValueError('frozen_code_changed')
    if digest((prepared/'profiles.json').read_bytes())!=manifest['profiles_sha256']: raise ValueError('profiles_changed')
    settings=model.load_profiles(prepared/'profiles.json')
    profiles={profile['id']:profile for profile in settings['profiles']}
    if len(set(profile_ids))!=len(profile_ids) or any(key not in profiles for key in profile_ids): raise ValueError('unknown_profile')
    if provider_env_file: load_provider_env(provider_env_file)
    started=time.monotonic(); results=[]; skipped=[]; original=None
    with BudgetLedger(prepared/'budget.jsonl',cap_usd) as budget:
        original=_install_capture()
        try:
            with ThreadPoolExecutor(max_workers=concurrency) as pool:
                futures=[]
                for profile_id in profile_ids:
                    profile=profiles[profile_id]
                    for item in manifest['cases']:
                        case_id=item['case_id']; key=profile_id+':'+case_id
                        directory=prepared/'runs'/profile_id/case_id
                        if (directory/'intent.json').exists() or key in budget.reservations:
                            skipped.append({'case_id':case_id,'profile_id':profile_id,'reason':'prior_intent_never_retried'}); continue
                        if time.monotonic()-started>=deadline_seconds:
                            skipped.append({'case_id':case_id,'profile_id':profile_id,'reason':'deadline'}); continue
                        raw=(prepared/'inputs'/(case_id+'.json')).read_bytes()
                        if digest(raw)!=item['input_file_sha256']: raise ValueError('input_changed')
                        evidence=json.loads(raw); system,prompt=model.prepare(evidence)
                        if manifest.get('system_override'):
                            system=(prepared/'system-override.txt').read_bytes().decode('utf-8')
                        if digest(system.encode())!=manifest['prompt_system_sha256']: raise ValueError('system_changed')
                        prompt={'system':system,'prompt':prompt}
                        if widget.canonical_hash(prompt)!=item['prompt_hash']: raise ValueError('prompt_changed')
                        unavailable=model._unavailable(profile['config'])
                        if unavailable: raise ValueError(unavailable)
                        reservation=budget.reserve(profile['config'],system,prompt['prompt'],settings['max_output_tokens'],key)
                        save(directory/'intent.json',{'at':now(),'case_id':case_id,'profile_id':profile_id,
                            'request_key':key,'reservation':reservation,'input_hash':evidence['input_hash'],
                            'prompt_hash':item['prompt_hash'],'profile':profile,'automatic_retries':0,
                            'effort':manifest.get('effort'),'variant':manifest.get('variant')})
                        futures.append((key,pool.submit(_call,directory,evidence,profile,settings,prompt,manifest.get('effort'),started+deadline_seconds)))
                for key,future in futures:
                    record=future.result(); response=record['response'] or {}
                    budget.record_outcome(key,record['status'],response.get('input_tokens'),response.get('output_tokens'))
                    results.append(record)
        finally:
            if original is not None: providers._open=original
        summary={'at':now(),'calls':sum(r['dispatch_attempts'] for r in results),'scheduled_attempts':len(results),'succeeded':sum(r['status']=='succeeded' for r in results),
                 'failed':sum(r['status']!='succeeded' for r in results),'skipped':skipped,'budget':budget.summary(),
                 'elapsed_seconds':time.monotonic()-started,'external_effects':0}
    save(prepared/('run-summary-'+str(time.time_ns())+'.json'),summary)
    return summary


def _quote(value):
    return '\n'.join('> '+line for line in str(value).splitlines())+'\n'


def format_answer(case_id,record,item):
    candidate=record.get('candidate')
    action=candidate.get('next_action',{}) if candidate else {}
    answer='# ANSWER — '+case_id+'\n\n'
    answer+='## Input received\n\n[Case index](SOURCE/index.md) · [History](SOURCE/history.md) · [Exact model input](INPUT.json) · [Input inventory](PROVENANCE.json)\n\n'
    answer+='Input SHA256: `'+item['input_hash']+'`.\n\n'
    for derivative in item.get('derivatives',[]):
        if 'sidecar' in derivative:
            answer+='- [Extracted '+derivative['path']+'](EXTRACTIONS/'+derivative['path']+'.txt) — unverified extraction.\n'
        else: answer+='- '+derivative['path']+' — content unprocessed.\n'
    answer+='\n## Decision (proposed)\n\n'
    answer+=_quote(action.get('description','No accepted model output.'))
    answer+='\nState: `'+str(candidate.get('state'))+'`.\n' if candidate else '\nState: unavailable.\n'
    answer+='\n## Actions actually taken\n\nProvider dispatch attempts: '+str(record.get('dispatch_attempts','not recorded'))+'. Model analysis only. Business operations executed: 0.\n\n'
    answer+='## Escalation\n\n'
    answer+=_quote(action.get('description')) if action.get('type')=='operator_review' else 'No explicit operator-review action was proposed in the accepted output.\n'
    answer+='\n## Missing information and conflicts\n\n'
    uncertainties=candidate.get('uncertainty',[]) if candidate else []
    answer+='\n'.join(_quote(value) for value in uncertainties) if uncertainties else 'No uncertainty text was retained.\n'
    answer+='\n## Errors and final observed status\n\nStatus: `'+record['status']+'`. Error: `'+str(record.get('error'))+'`.\n\n'
    answer+='[Retained call result](SOURCE_RESULT.json)'
    if record['status']!='missing': answer+=' · [Wire trace](WIRE.JSON) · [Dispatch intent](INTENT.JSON)'
    answer+='\n\n'
    answer+='## Exact retained candidate\n\n```json\n'+json.dumps(candidate,ensure_ascii=False,indent=2)+'\n```\n'
    return answer


def export(prepared,output,profile_id):
    prepared,output=Path(prepared),Path(output)
    manifest=json.loads((prepared/'manifest.json').read_text())
    output.mkdir(parents=True,exist_ok=False)
    for item in manifest['cases']:
        case_id=item['case_id']; directory=output/case_id; directory.mkdir()
        path=prepared/'runs'/profile_id/case_id/'result.json'
        record=json.loads(path.read_text()) if path.exists() else {'status':'missing','candidate':None,'error':'no_retained_result','response':None,'dispatch_attempts':0}
        candidate=record.get('candidate')
        answer=format_answer(case_id,record,item)
        rationale={'evidence_event_ids':candidate.get('evidence_event_ids',[]) if candidate else [],
                   'uncertainty':candidate.get('uncertainty',[]) if candidate else []}
        reasoning='# REASONING — '+case_id+'\n\nThe submitted model contract has no rationale field. These are only its recorded evidence references and uncertainty; no reasoning is reconstructed.\n\n```json\n'+json.dumps(rationale,ensure_ascii=False,indent=2)+'\n```\n'
        evidence=json.loads((prepared/'inputs'/(case_id+'.json')).read_text())
        by_id={message['event_id']:message for message in evidence['messages']}
        for event_id in rationale['evidence_event_ids']:
            message=by_id.get(event_id)
            if message is not None:
                source_link='SOURCE/index.md' if event_id=='case-context' else 'SOURCE/history.md'
                reasoning+='\n## '+event_id+' — [source]('+source_link+')\n\n'+_quote(message['body'])
        (directory/'ANSWER.md').write_text(answer); (directory/'REASONING.md').write_text(reasoning)
        save(directory/'SOURCE_RESULT.json',record)
        save(directory/'PROVENANCE.json',{**item,'source_commit':manifest['source_commit'],
            'code_commit':manifest['code_commit'],'code_files':manifest['code_files'],
            'source_files':{key:value for key,value in manifest['source_files'].items() if key.startswith(case_id+'/')}})
        copy_bytes(prepared/'inputs'/(case_id+'.json'),directory/'INPUT.json')
        for source in (prepared/'source'/case_id).rglob('*'):
            if source.is_file(): copy_bytes(source,directory/'SOURCE'/source.relative_to(prepared/'source'/case_id))
        for source in (prepared/'sidecars'/case_id).rglob('*'):
            if source.is_file(): copy_bytes(source,directory/'EXTRACTIONS'/source.relative_to(prepared/'sidecars'/case_id))
        for name in ('wire.json','intent.json'):
            source=prepared/'runs'/profile_id/case_id/name
            if source.exists(): copy_bytes(source,directory/name.upper())
    save(output/'MANIFEST.json',manifest)
    if (prepared/'extraction-manifest.json').exists():
        copy_bytes(prepared/'extraction-manifest.json',output/'EXTRACTION_MANIFEST.json')
    return {'exported_cases':len(manifest['cases']),'profile_id':profile_id,'external_effects':0}
