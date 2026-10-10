"""Build source-only public briefs from this repository; no external atlas required."""
from pathlib import Path
from source import load_case

OUT = Path(__file__).resolve().parents[1] / 'briefs'
OUT.mkdir(exist_ok=True)
for number in range(1, 51):
    cid = f'{number:03d}'
    c = load_case(cid)
    folder = Path(c['folder'])
    (OUT / f'{cid}.md').write_text(c['card'] + '\n\n' + (folder / 'history.md').read_text())
print('Built 50 public source briefs.')
