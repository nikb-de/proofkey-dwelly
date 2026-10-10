"""Заготовка разметки негативной ветки: наследует шаги позитивного кейса до точки расхождения, добавляет
стубы для хвостовых событий, provenance и brief ветки. Использование: python3 pipeline/scaffold_negative.py 001-N3 [...]
Пишет annot/<branch>.json только если файла ещё нет (или с --force), и briefs/<branch>.md всегда."""
import copy, csv, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from source import load_case, NEG

W = Path(__file__).resolve().parents[1]
TODO = 'TODO'


def rows():
    with open(NEG / 'index.csv', newline='') as f:
        return {r['branch']: r for r in csv.DictReader(f)}


def boundaries(card):
    m = re.search(r'## Boundaries and remaining work\n(.*?)(?=\n## |\Z)', card, re.S)
    return m.group(1).strip() if m else ''


def scaffold(bid, force=False):
    row = rows()[bid]
    parent = bid[:3]
    pos_path = W / 'annot' / f'{parent}.json'
    if not pos_path.exists():
        raise SystemExit(f'{bid}: нет позитивной разметки annot/{parent}.json — сначала разметить {parent}')
    pos = json.load(open(pos_path))
    c = load_case(bid)
    keep = int(row['insert_after'])
    inherited = [s for s in pos['steps'] if int(s['event_id']) <= keep]
    tail = [e for e in c['events'] if int(e['id']) > keep]
    draft = {
        'case_id': bid, 'lang': 'en',
        'title': f'{bid} · {TODO}: short name of what went wrong',
        'initial_explanation': pos['initial_explanation'],
        'our_actor_id': pos['our_actor_id'], 'client_actor_id': pos.get('client_actor_id'),
        'actors': copy.deepcopy(pos['actors']),
        'goal': pos['goal'],
        'limits': [f'{TODO}: ' + boundaries(c['card'])],
        'intake': copy.deepcopy(pos.get('intake')),
        'initial': copy.deepcopy(pos['initial']),
        'provenance': {
            'type': 'synthetic_negative_branch', 'repository': 'nikb-de/proofkey-dwelly',
            'source_path': f"data/negative-branches-001-050/{row['folder']}",
            'branch_id': bid, 'derived_from_case': parent,
            'retained_public_events': [s['event_id'] for s in inherited],
            'diverges_after_event': row['insert_after'],
            'failure_mode': row['failure_mode'], 'expected_decision': row['expected_decision'],
            'workflow_sheet': row['sheet'], 'branch_label': row['label'],
        },
        'steps': copy.deepcopy(inherited) + [{
            'event_id': e['id'], 'label': TODO, 'title': TODO, 'explanation': TODO, 'conversation_id': TODO,
            'facts_upsert': [], 'requests_upsert': {}, 'criteria_add': [], 'criteria_met': [],
            'agent_state': {'status': 'ready', 'waiting_for': [], 'next_action': TODO},
            'blocker': TODO, 'status': TODO, 'next_step': None, 'result': None, 'annotations_add': [],
        } for e in tail],
    }
    if pos.get('source_attachments'):
        draft['source_attachments'] = [copy.deepcopy(x) for x in pos['source_attachments']
                                       if int(x['event_id']) <= keep]
    out = W / 'annot' / f'{bid}.json'
    if out.exists() and not force:
        print(f'{bid}: annot уже есть, не трогаю (--force чтобы перезаписать)')
    else:
        out.write_text(json.dumps(draft, ensure_ascii=False, indent=1) + '\n')
        print(f'{bid}: annot/{bid}.json — унаследовано {len(inherited)} шагов, хвост {len(tail)} событий ({row["failure_mode"]}, expected {row["expected_decision"]})')
    # brief ветки
    L = [f"# Branch {bid} — {c['title']}", '',
         f"Failure mode: **{row['failure_mode']}** · expected desk decision: **{row['expected_decision']}** (workflow sheet {row['sheet']}) · diverges after event {row['insert_after']} · label: {row['label']}", '',
         f"Inherited steps {', '.join(s['event_id'] for s in inherited)} are copied from annot/{parent}.json and must stay as they are. Annotate only events {', '.join(e['id'] for e in tail)}.", '',
         '## Branch card (index.md, verbatim)', '', c['card'], '', '## Branch events (history.md, verbatim)', '']
    for e in c['events']:
        m = e['meta']
        L += [f"### Event {e['id']} — {e['timestamp']}" + ('  (inherited)' if int(e['id']) <= keep else '  (BRANCH)'),
              f"- Stage: {m.get('Stage')} · Channel: {m.get('Channel')}", f"- From: `{m.get('From')}`", f"- To: `{m.get('To')}`",
              f"- Text: {e['body']}", '']
    (W / 'briefs' / f'{bid}.md').write_text('\n'.join(L))
    return draft


if __name__ == '__main__':
    force = '--force' in sys.argv
    ids = [a for a in sys.argv[1:] if not a.startswith('--')]
    for bid in ids:
        scaffold(bid, force)
