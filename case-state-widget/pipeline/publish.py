"""Копирует собранные cases/<id>.json в командный репозиторий case-state-widget/cases/<id>.json (плоская раскладка,
которую читает виджет через GitHub API). Использование: python3 pipeline/publish.py 001 002 002-N4 (без аргументов — все)."""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from source import REPO

W = Path(__file__).resolve().parents[1]
DEST = REPO / 'case-state-widget' / 'cases'
CYR = re.compile('[А-Яа-яЁё]')


def main(argv):
    ids = argv or sorted(p.stem for p in (W / 'cases').glob('*.json') if re.fullmatch(r'\d{3}(-N\d)?', p.stem))
    DEST.mkdir(parents=True, exist_ok=True)
    bad = 0
    for cid in ids:
        text = (W / 'cases' / f'{cid}.json').read_text()
        data = json.loads(text)
        if data['initial_state']['case_id'] != cid:
            print(f'SKIP {cid}: case_id в файле = {data["initial_state"]["case_id"]}'); bad += 1; continue
        if CYR.search(text):
            print(f'SKIP {cid}: в файле осталась кириллица (нужна английская сборка)'); bad += 1; continue
        (DEST / f'{cid}.json').write_text(text)
        print(f'{DEST.relative_to(REPO)}/{cid}.json  ({len(data["steps"])} steps, {len(text)//1024} KB)')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
