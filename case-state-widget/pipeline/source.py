"""Источник кейсов: публичные (HackatonPublicCases/Delivery & Logistics/NNN) и негативные ветки
(proofkey-dwelly/data/negative-branches-001-050/<folder из index.csv>). Парсит index.md и history.md."""
import csv, json, os, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = Path(os.environ.get('PROOFKEY_PUBLIC', str(ROOT / 'data' / 'dwelly-public-cases' / 'raw' / 'Delivery & Logistics')))
REPO = Path(os.environ.get('PROOFKEY_REPO', str(ROOT)))
NEG = REPO / 'data' / 'negative-branches-001-050'
CONTEXT = REPO / 'data' / 'training-context-cases'
AUG = Path(os.environ.get('PROOFKEY_AUG', str(REPO / 'data' / 'context-augmentations-001-050')))
ATLAS = Path(os.environ.get('PROOFKEY_ATLAS', str(ROOT / 'outputs' / 'ontology-explorer' / 'dist' / 'data.json')))

EVENT_RE = re.compile(r'<a id="event-(\d+)"></a>\s*\n## (.+?) — event \1\n(.*?)(?=\n<a id="event-|\Z)', re.S)
META_RE = re.compile(r'- \*\*(.+?):\*\* (.*)')


def parse_history(text):
    events = []
    for m in EVENT_RE.finditer(text):
        eid, ts, rest = m.group(1), m.group(2).strip(), m.group(3)
        meta, body = {}, []
        for line in rest.strip('\n').split('\n'):
            mm = META_RE.match(line)
            if mm and not body:
                meta[mm.group(1)] = mm.group(2).strip()
            elif body or line.strip():
                body.append(line)
        events.append({'id': eid, 'timestamp': ts, 'meta': meta, 'body': '\n'.join(body).strip()})
    return events


def parse_details(text):
    sec = re.search(r'## Case details\n(.*?)(?=\n## |\Z)', text, re.S)
    return {m.group(1): m.group(2).strip() for m in META_RE.finditer(sec.group(1) if sec else '')}


def folder_for(ref):
    if re.fullmatch(r'\d{3}(?:-N\d)?-A1-(?:NOISE|MISSING|LONG)', ref):
        folder = CONTEXT / 'sources' / ref
        if not (folder / 'history.md').is_file():
            raise FileNotFoundError(f'context case {ref} not found')
        return folder, 'training_context'
    if re.fullmatch(r'\d{3}', ref):
        return PUBLIC / ref, 'public'
    if re.fullmatch(r'\d{3}-N\d', ref):
        with open(NEG / 'index.csv', newline='') as f:
            for row in csv.DictReader(f):
                if row['branch'] == ref:
                    return NEG / row['folder'], 'negative'
        raise FileNotFoundError(f'ветка {ref} не найдена в {NEG / "index.csv"}')
    if re.fullmatch(r'\d{3}-A\d', ref):
        with open(AUG / 'index.csv', newline='') as f:
            for row in csv.DictReader(f):
                if row['variant'] == ref:
                    return AUG / row['folder'], 'augmentation'
        raise FileNotFoundError(f'вариант {ref} не найден в {AUG / "index.csv"}')
    raise ValueError(f'непонятный идентификатор кейса {ref!r} (ожидается 001, 001-N1 или 001-A1)')


def load_case(ref):
    folder, kind = folder_for(ref)
    card = (folder / 'index.md').read_text()
    history = (folder / 'history.md').read_text()
    events = parse_history(history)
    details = parse_details(card)
    title = re.match(r'# Case [\w-]+: (.+)', card).group(1).strip()
    attachments, ru = [], {}
    if kind == 'public' and ATLAS.exists():
        c = next((x for x in json.load(open(ATLAS))['cases'] if x['id'] == ref), None)
        if c:
            ru = {e['id']: e.get('messageRu') for e in c['events']}
            attachments = [{'name': x['name'], 'type': x['type'], 'url': x['sourceUrl']} for x in c['attachments']]
    for e in events:
        e['body_ru'] = ru.get(e['id'])
    return {'id': ref, 'kind': kind, 'folder': str(folder), 'title': title, 'details': details,
            'events': events, 'attachments': attachments, 'card': card}


if __name__ == '__main__':
    import sys
    c = load_case(sys.argv[1])
    print(json.dumps({k: v for k, v in c.items() if k != 'card'}, ensure_ascii=False, indent=1)[:3000])
