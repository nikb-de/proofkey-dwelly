"""Разметка варианта с усложнением контекста: собирает annot/<variant>.json из разметки родительского
публичного кейса и авторских правок варианта (шум / пропуск / длинная история).
Использование: python3 case-state-widget/pipeline/scaffold_augmentation.py 001-A1 012-A1 019-A1 [--force]
Пишет annot/<variant>.json только если файла ещё нет (или с --force). Источники вариантов лежат в
data/context-augmentations-001-050/<NNN>/<A#-TAG>/ (index.md + history.md)."""
import copy
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from source import load_case

W = Path(__file__).resolve().parents[1]


def load_parent(parent):
    return json.load(open(W / 'annot' / f'{parent}.json'))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def step(parent_step, event_id):
    s = copy.deepcopy(parent_step)
    s['event_id'] = event_id
    return s


def replace_ids(text, mapping):
    return re.sub(r'\b\d{3}\b', lambda m: mapping.get(m.group(0), m.group(0)), text)


def remap(st, mapping):
    for f in st.get('facts_upsert', []):
        src = f.get('source') or {}
        if src.get('type') == 'message' and src.get('id') in mapping:
            src['id'] = mapping[src['id']]
    for r in st.get('requests_upsert', {}).values():
        if r.get('evidence_event_ids'):
            r['evidence_event_ids'] = [mapping.get(x, x) for x in r['evidence_event_ids']]
    for c in st.get('criteria_met', []):
        c['evidence_event_ids'] = [mapping.get(x, x) for x in c['evidence_event_ids']]
    for n in st.get('annotations_add', []):
        if n.get('before_message_id') in mapping:
            n['before_message_id'] = mapping[n['before_message_id']]
        if n.get('source_event_ids'):
            n['source_event_ids'] = [mapping.get(x, x) for x in n['source_event_ids']]
        if n.get('title'):
            n['title'] = replace_ids(n['title'], mapping)
        if n.get('text'):
            n['text'] = replace_ids(n['text'], mapping)
    if st.get('result') and st['result'].get('evidence_event_ids'):
        st['result']['evidence_event_ids'] = [mapping.get(x, x) for x in st['result']['evidence_event_ids']]
    return st


def base_annot(parent, cid, title, explanation, extra_limits):
    a = copy.deepcopy(parent)
    a['case_id'] = cid
    a['title'] = title
    a['initial_explanation'] = explanation
    a['limits'] = list(parent['limits']) + extra_limits
    a['steps'] = []
    return a


def provenance(cid, source_path, parent, complication, tag, label, expected_decision):
    folder = Path(load_case(cid)['folder'])
    return {
        'type': 'synthetic_context_augmentation',
        'noise': True,
        'repository': 'nikb-de/proofkey-dwelly',
        'source_path': source_path,
        'variant_id': cid,
        'derived_from_case': parent,
        'complication': complication,
        'complication_tag': tag,
        'label': label,
        'expected_decision': expected_decision,
        'source_sha256': {'index.md': sha256(folder / 'index.md'), 'history.md': sha256(folder / 'history.md')},
    }


def build_001a1():
    p = load_parent('001')
    a = base_annot(
        p, '001-A1', '001-A1 · Delivery window change (noise)',
        p['initial_explanation'] + ' In this variant the escalation arrives as two informal fragments with an unrelated aside; the desk still has everything needed to offer the slots.',
        ['Do not act on the aside about the neighbour or mirror the informal register.'])
    mapping = {'003': '004', '004': '005', '005': '006'}

    s1 = step(p['steps'][0], '001')

    s2 = step(p['steps'][1], '002')
    s2['title'] = 'Vessa asks to move the morning delivery, informally'
    s2['explanation'] = ('Vessa confirms in an informal first fragment that the morning slot does not work and asks to move the lamp. '
                         "We already have dispatch's options, so we can offer them.")
    s2['facts_upsert'] = [f for f in s2['facts_upsert'] if f['id'] != 'f8']

    s3 = {
        'event_id': '003',
        'label': 'Client addendum',
        'title': 'Second fragment: thread instruction and an aside',
        'explanation': ("A second fragment carries the channel instruction and an aside about a neighbour's parcel. "
                        'It adds no case facts and requires no separate action; the next step stays the same.'),
        'conversation_id': 'client',
        'facts_upsert': [{'id': 'f8', 'text': 'The recipient asks us to keep messages in the order-linked thread.',
                          'source': {'type': 'message', 'id': '003'}}],
        'requests_upsert': {},
        'criteria_met': [],
        'agent_state': copy.deepcopy(s2['agent_state']),
        'blocker': s2['blocker'],
        'status': 'escalated',
        'next_step': copy.deepcopy(s2['next_step']),
        'result': None,
        'annotations_add': [{
            'id': 'noise-fragment', 'kind': 'context',
            'title': 'What the second fragment adds',
            'text': ('The fragment repeats the channel request and adds an unrelated aside about a neighbour. '
                     'It carries no case facts and no new request; the desk continues with the same next step.'),
            'before_message_id': '003', 'source_event_ids': ['003'],
        }],
    }

    s4 = remap(step(p['steps'][2], '004'), mapping)
    s5 = remap(step(p['steps'][3], '005'), mapping)
    s6 = remap(step(p['steps'][4], '006'), mapping)

    a['steps'] = [s1, s2, s3, s4, s5, s6]
    a['provenance'] = provenance('001-A1', 'data/context-augmentations-001-050/001/A1-SLOPPY_NOISE',
                                 '001', 'noise', 'A1-SLOPPY_NOISE', 'sloppy fragmentary correspondence', 'ASK_CUSTOMER')
    return a


def build_012a1():
    p = load_parent('012')
    a = base_annot(
        p, '012-A1', '012-A1 · Replacement slot after a vehicle breakdown (noise)',
        p['initial_explanation'] + " In this variant the escalation omits the recipient's availability, so the desk asks for it before contacting dispatch.",
        ['Do not request a rebooking before the recipient states availability.'])

    s1 = step(p['steps'][0], '001')

    s2 = step(p['steps'][1], '002')
    s2['title'] = 'Fenn asks for a replacement slot without stating availability'
    s2['explanation'] = ('Fenn asks to arrange a replacement slot but does not say when they can receive. '
                         'The availability is the missing prerequisite, so the next step is a question to Fenn.')
    s2['facts_upsert'] = [f for f in s2['facts_upsert'] if f['id'] == 'f6']
    r0 = copy.deepcopy(p['steps'][1]['requests_upsert']['r0'])
    s2['requests_upsert'] = {
        'r0': r0,
        'r1': {
            'type': 'information', 'from_actor': 'coordinator', 'to_actor': 'recipient', 'responsible_actor': 'recipient',
            'purpose': "Get the recipient's availability for the replacement attempt.",
            'expected_response': 'A day and a time range when the recipient can receive the parcel.',
            'status': 'planned', 'response': None, 'evidence_event_ids': ['002'],
        },
    }
    s2['agent_state'] = {'status': 'ready', 'waiting_for': [],
                         'next_action': 'Ask Fenn for the day and time range when they can receive the parcel.'}
    s2['blocker'] = "No replacement attempt is scheduled; the recipient's availability is not known."
    s2['status'] = 'escalated'
    s2['next_step'] = {'type': 'information', 'responsible_actor': 'recipient', 'request_id': 'r1',
                       'description': 'Wait for Fenn to state availability.'}

    s3 = {
        'event_id': '003',
        'label': 'Our question',
        'title': 'We ask Fenn when they can receive',
        'explanation': ('Fenn did not state when they can receive, so we ask for the missing availability before any rebooking request. '
                        'Now we wait for the reply.'),
        'conversation_id': 'client',
        'facts_upsert': [],
        'requests_upsert': {
            'r1': {
                'type': 'information', 'from_actor': 'coordinator', 'to_actor': 'recipient', 'responsible_actor': 'recipient',
                'purpose': "Get the recipient's availability for the replacement attempt.",
                'expected_response': 'A day and a time range when the recipient can receive the parcel.',
                'status': 'awaiting_response', 'response': None, 'evidence_event_ids': ['002', '003'],
            },
        },
        'criteria_met': [],
        'agent_state': {
            'status': 'waiting',
            'waiting_for': [{'actor_id': 'recipient', 'request_id': 'r1', 'expected': 'A day and a time range for the replacement attempt'}],
            'next_action': 'Once Fenn replies, ask dispatch to rebook and confirm a specific window and any charge.',
        },
        'blocker': "The recipient's availability is not known; no replacement attempt is scheduled.",
        'status': 'awaiting_response',
        'next_step': {'type': 'information', 'responsible_actor': 'recipient', 'request_id': 'r1',
                      'description': 'Wait for Fenn to state availability.'},
        'result': None,
        'annotations_add': [],
    }

    s4 = {
        'event_id': '004',
        'label': 'Client reply',
        'title': 'Fenn states availability for 14 February afternoon',
        'explanation': ('Fenn is free on 2026-02-14 in the afternoon. Only dispatch can book the replacement, '
                        'so the next step is a rebooking request to dispatch with that availability.'),
        'conversation_id': 'client',
        'facts_upsert': [{'id': 'f7', 'text': 'The recipient is free on 2026-02-14 in the afternoon.',
                          'source': {'type': 'message', 'id': '004'}}],
        'requests_upsert': {
            'r1': {
                'type': 'information', 'from_actor': 'coordinator', 'to_actor': 'recipient', 'responsible_actor': 'recipient',
                'purpose': "Get the recipient's availability for the replacement attempt.",
                'expected_response': 'A day and a time range when the recipient can receive the parcel.',
                'status': 'answered', 'response': '2026-02-14 in the afternoon', 'evidence_event_ids': ['002', '003', '004'],
            },
            'r2': {
                'type': 'action', 'from_actor': 'coordinator', 'to_actor': 'dispatch', 'responsible_actor': 'dispatch',
                'purpose': 'Rebook DL-012 after the confirmed breakdown for 2026-02-14 afternoon, and confirm a specific available window and any charge.',
                'expected_response': 'A specific available window and any charge.',
                'status': 'planned', 'response': None, 'evidence_event_ids': ['004'],
            },
        },
        'criteria_met': [],
        'agent_state': {'status': 'ready', 'waiting_for': [],
                        'next_action': 'Ask dispatch to rebook DL-012 for 2026-02-14 afternoon and to confirm a specific window and any charge.'},
        'blocker': 'No replacement attempt is scheduled; Fenn is free on 2026-02-14 in the afternoon.',
        'status': 'escalated',
        'next_step': {'type': 'action', 'responsible_actor': 'dispatch', 'request_id': 'r2',
                      'description': 'Rebook DL-012 for 2026-02-14 afternoon and confirm a specific window and any charge.'},
        'result': None,
        'annotations_add': [],
    }

    s5 = remap(step(p['steps'][3], '005'), {'004': '005'})
    s5['requests_upsert'] = {
        'r0': {**copy.deepcopy(p['steps'][3]['requests_upsert']['r0']), 'evidence_event_ids': ['002', '005']},
        'r2': {**copy.deepcopy(p['steps'][3]['requests_upsert']['r1']), 'evidence_event_ids': ['004', '005']},
        'r3': {**copy.deepcopy(p['steps'][3]['requests_upsert']['r2']), 'evidence_event_ids': ['005']},
    }
    s5['next_step'] = {**s5['next_step'], 'request_id': 'r3'}
    s5['criteria_met'] = [{'id': 'c1', 'evidence_event_ids': ['005']}]
    s5['annotations_add'] = [{
        'id': 'missing-rebook-request', 'kind': 'gap',
        'title': 'Between 004 and 005 · our rebooking request to dispatch',
        'text': ('Fenn stated availability in 004. We then had to pass it to dispatch and request a specific window and any charge; '
                 'that request and the wait are not recorded as separate events. Dispatch\'s 005 message confirms the booking.'),
        'before_message_id': '005', 'source_event_ids': ['004', '005'],
        'implied_action': {
            'from_actor': 'coordinator', 'to_actor': 'dispatch', 'type': 'action',
            'purpose': 'Rebook DL-012 for 2026-02-14 afternoon and confirm a specific window and any charge.',
        },
    }]

    s6 = remap(step(p['steps'][4], '006'), {'004': '005', '005': '006'})
    s6['requests_upsert'] = {
        'r3': {**copy.deepcopy(p['steps'][4]['requests_upsert']['r2']), 'evidence_event_ids': ['005', '006']},
    }

    a['steps'] = [s1, s2, s3, s4, s5, s6]
    a['provenance'] = provenance('012-A1', 'data/context-augmentations-001-050/012/A2-MISSING_DETAIL',
                                 '012', 'missing_detail', 'A2-MISSING_DETAIL', 'missing prerequisite detail', 'ASK_CUSTOMER')
    return a


def build_019a1():
    p = load_parent('019')
    a = base_annot(
        p, '019-A1', '019-A1 · Weather suspends the route (noise)',
        p['initial_explanation'] + ' In this variant four earlier resolved or non-actionable events precede the weather thread; they must not change the decision.',
        ['Do not reopen earlier resolved threads or act on notifications for other shipments.'])
    a['actors']['notifications'] = {
        'name': 'Notification services', 'organization': 'Plover Arc Logistics', 'role': 'notification_services',
        'responsibility': 'Sends notifications for separate shipments.', 'from_start': False,
        'source_names': ['Notification services, Plover Arc Logistics'],
    }
    a['intake']['context_message_id'] = '005'
    initial_agent_state = copy.deepcopy(p['initial']['agent_state'])
    initial_blocker = p['initial']['blocker']

    noise = [
        ('001', 'Dispatch note', 'Earlier dispatch record check closed',
         'An earlier dispatch note closes a record check. It adds nothing pending and requires no action.', 'dispatch'),
        ('002', 'Client note', 'Doorbell fixed, nothing to action',
         'A client note about a building fix. It is FYI only and requires no action.', 'client'),
        ('003', 'Notification', 'Separate shipment DL-233 notification',
         'A notification for a different shipment. It requires no desk action and is not part of DL-019.', 'notifications'),
        ('004', 'Client note', 'Neighbour parcel sorted, nothing to action',
         'Another FYI note; nothing to action, nothing that changes the case.', 'client'),
    ]
    steps = []
    for i, (eid, label, title, explanation, conv) in enumerate(noise):
        s = {
            'event_id': eid, 'label': label, 'title': title, 'explanation': explanation,
            'conversation_id': conv, 'facts_upsert': [], 'requests_upsert': {}, 'criteria_met': [],
            'agent_state': copy.deepcopy(initial_agent_state), 'blocker': initial_blocker,
            'result': None, 'annotations_add': [],
        }
        if i == 0:
            s['status'] = 'context_received'
        steps.append(s)

    mapping = {'001': '005', '002': '006', '003': '007', '004': '008', '005': '009'}
    s5 = remap(step(p['steps'][0], '005'), mapping)
    s5['annotations_add'] = [{
        'id': 'earlier-threads-closed', 'kind': 'context',
        'title': 'Earlier threads closed',
        'text': ('Events 001-004 are earlier threads that are resolved or need no action; the weather thread starts here.'),
        'before_message_id': '005', 'source_event_ids': ['001', '002', '003', '004'],
    }]
    s6 = remap(step(p['steps'][1], '006'), mapping)
    s7 = remap(step(p['steps'][2], '007'), mapping)
    s8 = remap(step(p['steps'][3], '008'), mapping)
    s9 = remap(step(p['steps'][4], '009'), mapping)

    a['steps'] = steps + [s5, s6, s7, s8, s9]
    a['provenance'] = provenance('019-A1', 'data/context-augmentations-001-050/019/A3-LONG_HISTORY',
                                 '019', 'long_history', 'A3-LONG_HISTORY', 'long history with irrelevant events', 'REQUEST_ACTION')
    return a


BUILDERS = {'001-A1': build_001a1, '012-A1': build_012a1, '019-A1': build_019a1}

if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    force = '--force' in sys.argv
    for cid in args:
        out = W / 'annot' / f'{cid}.json'
        if out.exists() and not force:
            print(f'{cid}: annot уже есть, не трогаю (--force чтобы перезаписать)')
            continue
        annot = BUILDERS[cid]()
        out.write_text(json.dumps(annot, ensure_ascii=False, indent=1) + '\n')
        print(f'{cid}: annot/{cid}.json — {len(annot["steps"])} шагов, происхождение {annot["provenance"]["complication"]}')
