import json, sys
a = json.load(open(sys.argv[1])); b = json.load(open(sys.argv[2]))
diffs = []
def walk(x, y, p):
    if type(x) != type(y): diffs.append((p, x, y)); return
    if isinstance(x, dict):
        for k in sorted(set(x) | set(y)):
            if k not in x or k not in y: diffs.append((p + '/' + k, x.get(k, '<absent>'), y.get(k, '<absent>')))
            else: walk(x[k], y[k], p + '/' + k)
    elif isinstance(x, list):
        if len(x) != len(y): diffs.append((p + '/len', len(x), len(y))); return
        for i, (u, v) in enumerate(zip(x, y)): walk(u, v, f'{p}/{i}')
    elif x != y: diffs.append((p, x, y))
walk(a, b, '')
print(f'{len(diffs)} differences: {sys.argv[1]} vs {sys.argv[2]}')
for p, x, y in diffs[:30]: print(' ', p, '|', json.dumps(x, ensure_ascii=False)[:100], '->', json.dumps(y, ensure_ascii=False)[:100])
