"""Разбирает готовый JSON виджета на компактную разметку annot/<id>.json (эталоны 002 и 002-N4).
Использование: python3 pipeline/decompile.py <file.json> [<id>]"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from source import load_case

W = Path(__file__).resolve().parents[1]
KNOWN = {'case_id', 'our_actor_id', 'client_actor_id', 'actors', 'goal', 'agent_state', 'success_criteria', 'intake',
         'blocker', 'facts', 'requests', 'decision', 'status', 'next_step', 'result', 'annotations', 'conversations',
         'messages', 'attachments', 'limits', 'prior_success_criteria'}
src = Path(sys.argv[1])
d = json.load(open(src))
init = d['initial_state']
cid = sys.argv[2] if len(sys.argv) > 2 else init['case_id']
meta = {e['id']: e['meta'] for e in load_case(cid)['events']}
final = d['steps'][-1]['state_after'] if d['steps'] else init
aliases = {}
for m in final['messages']:
    aliases.setdefault(m['from_actor'], set()).add(meta[m['event_id']]['From'])
    tos = [x.strip() for x in meta[m['event_id']]['To'].split(';')]
    ids = [m['to_actor']] + list(m.get('copy_to') or m.get('to_actors') or [])
    for aid, name in zip(ids, tos):
        aliases.setdefault(aid, set()).add(name)
lang = 'ru' if any('body_ru' in m for m in final['messages']) else 'en'
annot = {
    'case_id': cid, 'lang': lang, 'title': d['title'], 'initial_explanation': d.get('initial_explanation', ''),
    'our_actor_id': init['our_actor_id'], 'client_actor_id': init.get('client_actor_id'),
    'actors': {aid: {'name': a['name'], 'organization': a.get('organization'), 'role': a['role'],
                     'responsibility': a.get('responsibility'), 'from_start': aid in init['actors'],
                     'source_names': sorted(aliases.get(aid, []))}
               for aid, a in final['actors'].items()},
    'goal': init['goal'],
    'limits': list(init.get('limits', [])),
    'intake': None,
    'initial': {'blocker': init.get('blocker'), 'facts': init.get('facts', []),
                'success_criteria': [{'id': c['id'], 'description': c['description']} for c in init['success_criteria']],
                'agent_state': init['agent_state'], 'status': init.get('status', 'not_started'),
                'next_step': init.get('next_step'), 'requests': init.get('requests', {}),
                'decision': init.get('decision'), 'annotations': init.get('annotations', []),
                'state_set': {k: v for k, v in init.items() if k not in KNOWN}},
    'steps': []}
if d.get('provenance'):
    annot['provenance'] = d['provenance']
seen_attachments = set()
for step in d['steps']:
    for attachment in step['state_after'].get('attachments', []):
        key = json.dumps(attachment, sort_keys=True)
        if key not in seen_attachments:
            seen_attachments.add(key)
            annot.setdefault('source_attachments', []).append({'event_id': step['event']['id'], 'attachment': attachment})
prev = init
for s in d['steps']:
    sa, ev = s['state_after'], s['event']
    msg = next(m for m in sa['messages'] if m['event_id'] == ev['id'])
    st = {'event_id': ev['id'], 'label': ev.get('label', ev['title']), 'title': ev['title'],
          'explanation': s['explanation'], 'conversation_id': msg.get('conversation_id', 'main')}
    pf = {f['id']: f for f in prev.get('facts', [])}
    st['facts_upsert'] = [f for f in sa.get('facts', []) if pf.get(f['id']) != f]
    st['requests_upsert'] = {k: v for k, v in sa.get('requests', {}).items() if prev.get('requests', {}).get(k) != v}
    pc = {c['id']: c for c in prev['success_criteria']}
    st['criteria_add'] = [{'id': c['id'], 'description': c['description']} for c in sa['success_criteria'] if c['id'] not in pc]
    retired = set(pc) - {c['id'] for c in sa['success_criteria']}
    if retired:
        st['criteria_retire'] = sorted(retired)
    st['criteria_met'] = [{'id': c['id'], 'evidence_event_ids': c['evidence_event_ids']}
                          for c in sa['success_criteria'] if c['status'] == 'met' and pc.get(c['id']) != c]
    st['agent_state'] = sa['agent_state']
    for k in ('blocker', 'status', 'next_step', 'result'):
        st[k] = sa.get(k)
    if sa.get('decision') != prev.get('decision'):
        st['decision'] = sa.get('decision')
    pa = {a['id']: a for a in prev.get('annotations', [])}
    st['annotations_add'] = [a for a in sa.get('annotations', []) if pa.get(a['id']) != a]
    st['state_set'] = {k: v for k, v in sa.items() if k not in KNOWN and prev.get(k) != v}
    if sa.get('goal') != prev.get('goal'):
        st['state_set']['goal'] = sa['goal']
    if sa.get('intake') and not annot['intake']:
        annot['intake'] = {'summary': sa['intake']['summary'], 'note': sa['intake'].get('note'),
                           'context_message_id': sa['intake'].get('context_message_id')}
    elif sa.get('intake') and prev.get('intake'):
        upd = {k: v for k, v in sa['intake'].items() if k != 'escalated_at' and prev['intake'].get(k) != v}
        if upd:
            st['intake_update'] = upd
    annot['steps'].append(st)
    prev = sa
out = W / 'annot' / f'{cid}.json'
out.write_text(json.dumps(annot, ensure_ascii=False, indent=1) + '\n')
print(f'wrote {out} ({out.stat().st_size} bytes, lang={lang})')
