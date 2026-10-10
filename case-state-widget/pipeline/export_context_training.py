"""Export the three standalone context cases as evidence-only training pairs."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.dwelly_analysis import model, widget

DATA = ROOT / 'data/training-context-cases'


def export():
    index = json.loads((DATA / 'index.json').read_text())
    pairs, bindings = [], []
    for entry in index['cases']:
        cid = entry['case_id']
        document = json.loads((ROOT / f'case-state-widget/cases/{cid}.json').read_text())
        if document['steps'][-1]['event']['id'] != entry['cutoff_event_id']:
            raise ValueError(f'{cid}: cutoff mismatch')
        value = widget.project(document, len(document['steps']), cid)
        value.pop('author_limits', None)
        value.pop('input_hash')
        value['input_hash'] = widget.canonical_hash(value)
        widget.validate_input(value)
        target_path = DATA / f'targets/{cid}.json'
        target = json.loads(target_path.read_text())
        model.parse(value, {'text':json.dumps(target)})  # Local validation only.
        input_path = DATA / f'agent_inputs/{cid}.json'
        input_path.parent.mkdir(parents=True, exist_ok=True)
        input_path.write_text(json.dumps(value, ensure_ascii=False, indent=1)+'\n')
        pairs.append({'input':value,'target':target})
        bindings.append({
            'case_id':cid, 'family_id':entry['family_id'],
            'input_hash':value['input_hash'],
            'input_sha256':hashlib.sha256(input_path.read_bytes()).hexdigest(),
            'target_sha256':hashlib.sha256(target_path.read_bytes()).hexdigest(),
            'label_status':entry['label_status'],
        })
    (DATA / 'training.jsonl').write_text(''.join(json.dumps(p,ensure_ascii=False)+'\n' for p in pairs))
    (DATA / 'manifest.json').write_text(json.dumps({
        'schema_version':'proofkey-training-context-manifest-v1',
        'case_count':len(pairs),'cases':bindings,
        'split_rule':'Keep each original case and all its descendants in one split.',
        'input_rule':'Only input is sent to the model; target is separate supervision.',
        'provenance':'Team-generated synthetic training cases; assistant-authored draft labels.',
    },ensure_ascii=False,indent=1)+'\n')
    print(f'Exported {len(pairs)} training pairs; local input and target validation passed.')


if __name__ == '__main__':
    export()
