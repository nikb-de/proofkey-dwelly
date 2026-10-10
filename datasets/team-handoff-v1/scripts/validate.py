#!/usr/bin/env python3
"""Offline structural and consistency validation; never certifies annotation quality."""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys

try:
    from jsonschema import Draft202012Validator, FormatChecker
    from referencing import Registry, Resource
except ImportError:
    print(json.dumps(dict(valid=False, errors=['Missing dependency: install requirements.txt with pip.'])))
    sys.exit(1)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate JSON key: ' + key)
        result[key] = value
    return result


def parse(raw):
    return json.loads(raw, object_pairs_hook=unique_object,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('nonfinite JSON number')))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def timestamp(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(result.tzinfo is not None and result.utcoffset() is not None, 'timestamp must have timezone')
    return result


def safe_path(root, name):
    path = PurePosixPath(name)
    require(not path.is_absolute() and '..' not in path.parts and '\\' not in name,
            'unsafe relative path: ' + name)
    resolved = (root / path).resolve()
    require(resolved.is_relative_to(root), 'path escapes dataset: ' + name)
    require(resolved.is_file(), 'missing file: ' + name)
    return resolved


def validate(root):
    root = Path(root).resolve()
    schemas = {}
    registry = Registry()
    for path in sorted((root / 'schemas').glob('*.schema.json')):
        schema = parse(path.read_text(encoding='utf-8'))
        Draft202012Validator.check_schema(schema)
        schemas[path.name] = schema
        registry = registry.with_resource(schema['$id'], Resource.from_contents(schema))
    validators = {name: Draft202012Validator(schema, registry=registry, format_checker=FormatChecker())
                  for name, schema in schemas.items()}

    def check(value, name):
        require(name in validators, 'missing local schema: ' + name)
        error = next(validators[name].iter_errors(value), None)
        require(error is None, name + ': ' + (error.message if error else ''))

    rows = []
    for number, raw in enumerate((root / 'manifest.jsonl').read_text(encoding='utf-8').splitlines(), 1):
        require(bool(raw.strip()), 'blank manifest row: ' + str(number))
        row = parse(raw)
        check(row, 'manifest.schema.json')
        rows.append(row)
    require(rows, 'dataset is empty')
    inputs, labels, episodes, criteria = {}, {}, {}, {}
    seen_paths, referenced, split_groups, snapshots = {}, set(), {}, {}
    eligible = 0

    def split_group(kind, identity, split):
        key = (kind, identity)
        require(key not in split_groups or split_groups[key] == split, 'cross-split leakage: ' + kind + ' ' + str(identity))
        split_groups[key] = split

    for row in rows:
        loaded = {}
        for kind, name in row['files'].items():
            path = safe_path(root, name)
            require(path not in seen_paths or (kind == 'episode' and seen_paths[path] == kind),
                    'duplicate or reused file: ' + name)
            seen_paths[path] = kind
            referenced.add(path)
            raw = path.read_bytes()
            require(hashlib.sha256(raw).hexdigest() == row['sha256'][kind], 'file hash mismatch: ' + name)
            loaded[kind] = parse(raw.decode('utf-8'))
            schema_name = {'input': 'decision-input', 'label': 'decision-label', 'episode': 'episode', 'criteria': 'criteria'}[kind]
            check(loaded[kind], schema_name + '.schema.json')
        inp, label, criterion, episode = (loaded[key] for key in ('input', 'label', 'criteria', 'episode'))
        iid, lid, eid = inp['input_id'], label['label_id'], episode['episode_id']
        require(iid == row['input_id'] == label['input_id'] == criterion['input_id'], 'input IDs do not align')
        require(eid == row['episode_id'], 'episode ID does not align')
        require(iid not in inputs and lid not in labels, 'duplicate input or label ID')
        require(eid not in episodes or episodes[eid] == episode, 'duplicate episode ID with different content')
        inputs[iid], labels[lid], criteria[iid], episodes[eid] = inp, label, criterion, episode
        source, snapshot = inp['source'], inp['snapshot']
        require(source == label['source'] == criterion['source'], 'source triples do not align')
        require(source == {key: snapshot[key] for key in ('case_id', 'revision', 'snapshot_hash')}, 'snapshot/source mismatch')
        digest = hashlib.sha256(canonical({k: v for k, v in snapshot.items() if k != 'snapshot_hash'}).encode()).hexdigest()
        require(digest == snapshot['snapshot_hash'], 'canonical snapshot hash mismatch')
        require(snapshot['revision'] == len(snapshot['events']), 'revision/event count mismatch')
        key = (source['case_id'], source['revision'])
        require(key not in snapshots or snapshots[key] == snapshot, 'conflicting case revision')
        snapshots[key] = snapshot
        participants = set(snapshot['participants'])
        require({snapshot['links']['customer_id'], snapshot['links']['operator_id']} <= participants, 'linked identity missing from participants')
        as_of = timestamp(row['as_of'])
        event_ids = set()
        for event in snapshot['events']:
            require(event['event_id'] not in event_ids, 'duplicate event ID')
            event_ids.add(event['event_id'])
            require({event['sender_id'], *event['recipient_ids']} <= participants, 'event references unknown participant')
            require(timestamp(event['occurred_at']) <= as_of, 'event occurs after as_of')
        require(set(criterion['required_evidence_ids']) <= event_ids, 'required evidence is not visible')
        require(label['expected_disposition'] in criterion['acceptable_dispositions'], 'label disposition not acceptable')
        require(episode['case_id'] == source['case_id'] and iid in episode['input_ids'] and lid in episode['label_ids'], 'episode missing row membership or wrong case')
        review = label['review']
        if row['annotation_status'] == 'human_reviewed':
            require(review['status'] == 'reviewed' and review['reviewer_id'] and review['reviewed_at'], 'human_reviewed lacks completed review')
            timestamp(review['reviewed_at'])
            eligible += not bool(row['exclusions'])
        elif row['annotation_status'] == 'rejected':
            require(review['status'] == 'rejected', 'rejected row lacks rejected review')
        else:
            require(review['status'] in ('unreviewed', 'in_review'), 'draft row cannot claim completed review')
        for kind, identity in [('family', row['family_id']), ('case', source['case_id']), ('episode', eid),
                               ('source', (inp['provenance']['source_kind'], inp['provenance']['source_id']))]:
            split_group(kind, identity, row['split'])

    for (case_id, revision), snapshot in snapshots.items():
        if revision:
            previous = snapshots.get((case_id, revision - 1))
            require(previous is not None, 'missing previous revision: ' + case_id + ' ' + str(revision - 1))
            require(snapshot['previous_snapshot_hash'] == previous['snapshot_hash'], 'broken previous snapshot hash chain')
            require(canonical(snapshot['events'][:-1]) == canonical(previous['events']), 'mutated event history')
            for field in ('case_id', 'links', 'participants', 'language'):
                require(snapshot[field] == previous[field], 'mutated case declaration: ' + field)

    transitions = {}
    for path in sorted((root / 'examples/transitions').glob('*.json')):
        checked = safe_path(root, str(path.relative_to(root)))
        value = parse(checked.read_text(encoding='utf-8'))
        check(value, 'transition.schema.json')
        tid = value['transition_id']
        require(tid not in transitions, 'duplicate transition ID')
        transitions[tid] = value
        require(value['episode_id'] in episodes, 'transition references missing episode')
        ep = episodes[value['episode_id']]
        require(tid in ep['transition_ids'], 'orphan transition')
        for field in ('from_input_id', 'to_input_id'):
            require(value[field] in ep['input_ids'], 'transition references missing input')
        for condition in value['conditions']:
            source_input = inputs.get(value['from_input_id'])
            require(source_input is not None, 'transition input missing')
            if condition['type'] == 'source_matches':
                require(condition['source'] == source_input['source'], 'transition source mismatch')
            if condition['type'] == 'evidence_present':
                require(set(condition['event_ids']) <= {e['event_id'] for e in source_input['snapshot']['events']}, 'transition evidence missing')
    for episode in episodes.values():
        require(set(episode['input_ids']) <= inputs.keys(), 'episode has dangling input reference')
        require(set(episode['label_ids']) <= labels.keys(), 'episode has dangling label reference')
        require(set(episode['transition_ids']) <= transitions.keys(), 'episode has dangling transition reference')
        require(all(inputs[i]['source']['case_id'] == episode['case_id'] for i in episode['input_ids']), 'episode includes wrong case')
        require(all(labels[l]['input_id'] in episode['input_ids'] for l in episode['label_ids']), 'episode label/input membership mismatch')
    for folder in ('inputs', 'labels', 'criteria', 'episodes'):
        for path in (root / 'examples' / folder).rglob('*.json'):
            require(path.resolve() in referenced, 'orphan file: ' + str(path.relative_to(root)))
    return dict(valid=True, rows=len(rows), inputs=len(inputs), labels=len(labels), episodes=len(episodes),
                transitions=len(transitions), eligible_reviewed_rows=eligible,
                splits=dict(Counter(row['split'] for row in rows)),
                annotation_statuses=dict(Counter(row['annotation_status'] for row in rows)),
                limitations=['Annotation quality and human identity are not verified.',
                             'occurred_at is checked against as_of; observed_at is absent from the input contract.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', nargs='?', default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    try:
        report = validate(args.root)
    except Exception as error:
        print(json.dumps(dict(valid=False, errors=[str(error)])))
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
