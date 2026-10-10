"""Компилирует разметку annot/<id>.json + исходник кейса в полный JSON виджета cases/<id>.json.
Использование: python3 pipeline/compile.py 001 002-N4 ...   (без аргументов — все annot/*.json)
Разметка с "lang": "en" собирается без body_ru (английский текст сообщений уже в body)."""
import copy, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from source import load_case, REPO

W = Path(__file__).resolve().parents[1]
EMPTY_DECISION = {'required': False, 'question': None, 'options': [], 'decision_maker': None,
                  'selected_option': None, 'reason': None}
STEP_KEYS = {'event_id', 'label', 'title', 'explanation', 'conversation_id', 'body_ru', 'facts_upsert',
             'requests_upsert', 'criteria_add', 'criteria_met', 'agent_state', 'blocker', 'status', 'next_step',
             'result', 'decision', 'annotations_add', 'state_set', 'intake_update', 'criteria_retire'}


class CompileError(Exception):
    pass


def upsert(items, item):
    for i, x in enumerate(items):
        if x.get('id') == item.get('id'):
            items[i] = copy.deepcopy(item)
            return
    items.append(copy.deepcopy(item))


def compile_case(a):
    cid = a['case_id']
    c = load_case(cid)
    details, lang, us = c['details'], a.get('lang', 'ru'), a['our_actor_id']
    all_actors, alias = {}, {}
    for aid, ad in a['actors'].items():
        all_actors[aid] = {'name': ad['name'], 'organization': ad.get('organization'), 'role': ad['role'],
                           'is_us': aid == us, 'responsibility': ad['responsibility']}
        for n in ad.get('source_names', []):
            if alias.get(n, aid) != aid:
                raise CompileError(f'{cid}: source_name {n!r} указан у двух участников')
            alias[n] = aid
    if us not in all_actors:
        raise CompileError(f'{cid}: our_actor_id {us!r} нет среди actors')

    def resolve(s):
        s = s.strip()
        if s not in alias:
            raise CompileError(f'{cid}: участник {s!r} из From/To не сопоставлен ни с одним actors[*].source_names')
        return alias[s]

    def ensure_actor(state, aid):
        if aid is None or aid in state['actors']:
            return
        if aid not in all_actors:
            raise CompileError(f'{cid}: участник {aid!r} не объявлен в actors')
        state['actors'][aid] = copy.deepcopy(all_actors[aid])

    init = a['initial']
    state = {
        'case_id': cid, 'our_actor_id': us, 'client_actor_id': a.get('client_actor_id'),
        'actors': {aid: copy.deepcopy(ad) for aid, ad in all_actors.items()
                   if a['actors'][aid].get('from_start', aid in (us, a.get('client_actor_id')))},
        'goal': a['goal'],
        'agent_state': copy.deepcopy(init['agent_state']),
        'success_criteria': [{'id': x['id'], 'description': x['description'], 'status': 'pending',
                              'evidence_event_ids': []} for x in init['success_criteria']],
        'intake': None, 'blocker': init.get('blocker'),
        'facts': copy.deepcopy(init.get('facts', [])),
        'requests': copy.deepcopy(init.get('requests', {})),
        'decision': copy.deepcopy(init.get('decision') or dict(EMPTY_DECISION, required=None)),
        'status': init.get('status', 'not_started'), 'next_step': init.get('next_step'), 'result': None,
        'annotations': copy.deepcopy(init.get('annotations', [])), 'conversations': {}, 'messages': []}
    limits = [x for x in a.get('limits', []) if isinstance(x, str) and x.strip()]
    if limits:
        state['limits'] = list(limits)
    for k, v in init.get('state_set', {}).items():
        state[k] = copy.deepcopy(v)
    pending_attachments = [] if a.get('source_attachments') else copy.deepcopy(c['attachments'])
    scheduled_attachments = copy.deepcopy(a.get('source_attachments', []))
    out = {'schema_version': 'case-step-viewer/1.0', 'title': a['title'],
           'initial_explanation': a['initial_explanation']}
    if a.get('provenance'):
        out['provenance'] = copy.deepcopy(a['provenance'])
    out['initial_state'] = state
    out['steps'] = []
    events = {e['id']: e for e in c['events']}
    ids = [e['id'] for e in c['events']]
    got = [s['event_id'] for s in a['steps']]
    if got != ids:
        raise CompileError(f'{cid}: steps должны покрывать события {ids} по порядку, получено {got}')
    context_event = next((e for e in c['events'] if e['meta'].get('Stage') == 'Context'), c['events'][0])
    created, escalated = details.get('Created'), details.get('Escalated')
    parent_details = load_case(cid.split('-')[0])['details'] if c['kind'] == 'negative' else details
    retained = int(a.get('provenance', {}).get('diverges_after_event',
                   len(a.get('provenance', {}).get('retained_public_events', []))))
    intake_overrides = {}
    for st in a['steps']:
        extra = set(st) - STEP_KEYS
        if extra:
            raise CompileError(f'{cid}: шаг {st["event_id"]}: неизвестные ключи {sorted(extra)}')
        e = events[st['event_id']]
        m = e['meta']
        state = copy.deepcopy(state)
        frm = resolve(m['From'])
        tos = [resolve(x) for x in re.split(r';\s*', m['To'])]
        for aid in [frm] + tos:
            ensure_actor(state, aid)
        for r in st.get('requests_upsert', {}).values():
            for k in ('from_actor', 'to_actor', 'responsible_actor'):
                ensure_actor(state, r.get(k))
        for w in st.get('agent_state', {}).get('waiting_for', []):
            ensure_actor(state, w.get('actor_id'))
        for holder, key in ((st.get('next_step'), 'responsible_actor'), (st.get('result'), 'confirmed_by'),
                            (st.get('decision'), 'decision_maker')):
            if holder:
                ensure_actor(state, holder.get(key))
        conv = st['conversation_id']
        msg = {'conversation_id': conv, 'event_id': e['id'], 'timestamp': e['timestamp'], 'from_actor': frm,
               'to_actor': tos[0], 'channel': m.get('Channel'), 'body': e['body']}
        if lang != 'en':
            msg['body_ru'] = st.get('body_ru') or e.get('body_ru') or e['body']
        if len(tos) > 1:
            msg['copy_to'] = tos[1:]
        state['messages'].append(msg)
        if conv not in state['conversations']:
            parts = list(dict.fromkeys([frm] + tos))
            state['conversations'][conv] = {'participants': ([us] if us in parts else []) + [p for p in parts if p != us],
                                            'channel': m.get('Channel')}
        else:
            cv = state['conversations'][conv]
            for p_ in [frm] + tos:
                if p_ not in cv['participants']:
                    cv['participants'].append(p_)
            if m.get('Channel') and m['Channel'] != cv['channel']:
                cv.setdefault('other_channels', [])
                if m['Channel'] not in cv['other_channels']:
                    cv['other_channels'].append(m['Channel'])
        hit = [x for x in pending_attachments if x['name'] in e['body']]
        if not hit and st['event_id'] == c['events'][-1]['id']:
            hit = list(pending_attachments)  # ни одно событие не ссылается по имени — показать хотя бы на последнем шаге
        if hit:
            state['attachments'] = state.get('attachments', []) + hit
            pending_attachments = [x for x in pending_attachments if x not in hit]
        scheduled = [x['attachment'] for x in scheduled_attachments if x['event_id'] == e['id']]
        if scheduled:
            state['attachments'] = state.get('attachments', []) + scheduled
        if a.get('intake') and st['event_id'] >= context_event['id']:
            ik = a['intake']
            intake_escalated = parent_details.get('Escalated') if int(e['id']) <= retained else escalated
            state['intake'] = {'created_at': created,
                               'escalated_at': intake_escalated if (intake_escalated and e['timestamp'] >= intake_escalated) else None,
                               'source': {'type': 'case_card', 'id': cid},
                               'context_message_id': ik.get('context_message_id') or context_event['id'],
                               'summary': ik['summary'], 'note': ik.get('note')}
            intake_overrides.update(copy.deepcopy(st.get('intake_update', {})))
            state['intake'].update(copy.deepcopy(intake_overrides))
        for f in st.get('facts_upsert', []):
            upsert(state['facts'], f)
        for k, v in st.get('requests_upsert', {}).items():
            state['requests'][k] = copy.deepcopy(v)
        retire = set(st.get('criteria_retire', []))
        if retire:
            active = {x['id'] for x in state['success_criteria']}
            if not retire <= active:
                raise CompileError(f'{cid}: unknown criteria to retire: {sorted(retire - active)}')
            retired = [copy.deepcopy(x) for x in state['success_criteria'] if x['id'] in retire]
            for x in retired:
                x['retired_at_event'] = e['id']
                x['reason'] = 'Outside this negative branch coordination task; not marked as achieved.'
            state.setdefault('prior_success_criteria', []).extend(retired)
            state['success_criteria'] = [x for x in state['success_criteria'] if x['id'] not in retire]
        for x in st.get('criteria_add', []):
            if any(y['id'] == x['id'] for y in state['success_criteria']):
                raise CompileError(f'{cid}: шаг {e["id"]}: критерий {x["id"]} уже есть')
            state['success_criteria'].append({'id': x['id'], 'description': x['description'], 'status': 'pending',
                                              'evidence_event_ids': []})
        for cm in st.get('criteria_met', []):
            for x in state['success_criteria']:
                if x['id'] == cm['id']:
                    x['status'] = 'met'
                    x['evidence_event_ids'] = list(cm['evidence_event_ids'])
                    break
            else:
                raise CompileError(f'{cid}: шаг {e["id"]}: критерий {cm["id"]} не объявлен')
        state['agent_state'] = copy.deepcopy(st['agent_state'])
        for k in ('blocker', 'status', 'next_step', 'result'):
            if k in st:
                state[k] = copy.deepcopy(st[k])
        if 'decision' in st:
            state['decision'] = copy.deepcopy(st['decision'])
        elif state['decision'].get('required') is None:
            state['decision'] = dict(EMPTY_DECISION)
        for n in st.get('annotations_add', []):
            upsert(state.setdefault('annotations', []), n)
        for k, v in st.get('state_set', {}).items():
            state[k] = copy.deepcopy(v)
        ev = {'id': e['id'], 'type': 'message_sent' if frm == us else 'message_received', 'label': st['label'],
              'title': st['title'], 'timestamp': e['timestamp'], 'actor_id': frm, 'message_id': e['id']}
        out['steps'].append({'event': ev, 'explanation': st['explanation'], 'state_after': state})
    return out


def main(argv):
    if not argv:
        print('укажите номера кейсов: python3 pipeline/compile.py 001 002-N4 ...  (или --all для всех annot/*.json)')
        return 2
    ids = sorted(p.stem for p in (W / 'annot').glob('*.json')) if argv == ['--all'] else argv
    ok = True
    for cid in ids:
        try:
            a = json.load(open(W / 'annot' / f'{cid}.json'))
            out = compile_case(a)
            repo_schema = REPO / 'case-state-widget' / 'schema.json'
            schema_path = repo_schema if repo_schema.exists() else W / 'schema.json'
            if schema_path.exists():
                try:
                    import jsonschema
                    jsonschema.validate(out, json.load(open(schema_path)))
                except ImportError:
                    pass
                except jsonschema.ValidationError as err:
                    raise CompileError(f'{cid}: не проходит schema.json виджета: {err.message} (путь {list(err.absolute_path)})')
            (W / 'cases' / f'{cid}.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n')
            print(f'OK   {cid} -> cases/{cid}.json ({len(out["steps"])} шагов, lang={a.get("lang", "ru")})')
        except (CompileError, KeyError, TypeError, ValueError, FileNotFoundError, json.JSONDecodeError) as err:
            ok = False
            print(f'FAIL {cid}: {type(err).__name__}: {err}')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
