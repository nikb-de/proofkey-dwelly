"""Build source-grounded negative annotations, retaining the reviewed parent prefix.

The authored histories provide the actual messages. This compiler annotates their
coordination scope without manufacturing a delivery, refund or operator decision.
Run from any directory: python3 case-state-widget/pipeline/annotate_negative.py.
The hand-reviewed 002-N4 reference is preserved.
"""
import copy
import csv
import hashlib
import json
import re
import sys
from pathlib import Path
from source import load_case, NEG
from scaffold_negative import scaffold

W = Path(__file__).resolve().parents[1]

# Policy rules are intentionally general: branch-specific values first appear
# at their source event, rather than leaking through initial limits or criteria.
RULES = {
 'ASK_CUSTOMER': ('decision', 'Obtain the authorised party’s precise choice or missing detail.',
                  'The authorised party supplies the requested choice or detail, directly or as explicitly reported by the responsible service.',
                  'Do not choose for the customer or treat a choice as a confirmed booking.'),
 'GET_OPTIONS': ('information', 'Obtain current permitted options from the responsible service.',
                 'The responsible party states the current options or confirms the permitted terms; acceptance and execution remain separate.',
                 'Do not act on obsolete options or carry consent over to a new offer.'),
 'VERIFY_FIRST': ('verification', 'Establish the saved outcome before repeating an uncertain action.',
                  'The record owner confirms the saved outcome of the first attempt, including whether another action is needed.',
                  'Do not repeat the action or claim success before checking the saved state.'),
 'ESCALATE_OPERATOR': ('action', 'Refer the unresolved issue to its authorised operator.',
                       'The responsible operator acknowledges the referral or provides a scoped instruction; registration is not a substantive decision.',
                       'Do not grant yourself operator authority or treat registration as a decision.'),
 'WAIT_WITH_DEADLINE': ('confirmation', 'Send one reminder with the recorded deadline and consequence.',
                       'The requested party replies, or the record owner confirms the deadline outcome without an assumed booking.',
                       'Do not treat a reminder or silence as consent, a booking or execution.'),
 'DECLINE_EXPLAIN': ('information', 'Explain the policy boundary and the permitted next step.',
                    'The policy boundary is communicated and acknowledged, or the responsible party confirms a permitted alternative.',
                    'Do not promise or perform the prohibited request.'),
 'RECORD_STOP': ('action', 'Record the stop and establish what was already executed.',
                 'The responsible owner confirms the stop and the current state; completed actions are not assumed undone.',
                 'Do not start further actions or assume that a stop undoes an executed action.'),
 'RECORD_REFUSAL': ('action', 'Record the declined physical attempt and obtain its evidence.',
                    'The responsible owner confirms the refusal record and its scope; return authority and refund remain separate.',
                    'Do not turn a refused attempt into a return authorisation, receipt or refund.'),
 'RESOLVE_DUPLICATE': ('action', 'Link duplicate requests and retain one operational record.',
                       'The owner confirms that the duplicate is linked or closed and only one operational request or change remains.',
                       'Do not create a second operational change, booking, charge or credit.'),
 'SEPARATE_AUTHORITY': ('verification', 'Use the authorised party or verified channel to establish authority.',
                        'The authorised party clarifies the instruction or authority, or the unauthorised service confirms it has acted on nothing.',
                        'Do not act on unverified authority or disclose protected details to an unverified party.'),
 'RECONCILE_CONFLICT': ('verification', 'Keep both records and request evidence from their owner.',
                       'The responsible owner supplies the requested evidence or source clarification; any unresolved discrepancy remains explicit.',
                       'Do not erase either conflicting record or infer a finding before the owner supplies evidence.'),
 'REQUEST_ACTION': ('action', 'Request the specific permitted action from its responsible owner.',
                    'The responsible owner confirms the requested scoped action or supplies the requested record; downstream execution is separate.',
                    'Do not claim downstream execution from a request, allocation or registration.'),
}


def section(card, name):
    m = re.search(r'^## ' + re.escape(name) + r'\n(.*?)(?=\n## |\Z)', card, re.S | re.M)
    return m.group(1).strip() if m else ''


def actor_for(a, name):
    name = name.strip()
    for aid, actor in a['actors'].items():
        if name in actor.get('source_names', []):
            return aid
    lower = name.lower()
    if any(x in lower for x in ('unknown sender', 'unregistered', 'unverified', 'not on the', 'sender signing', 'person answering', 'sender stating')):
        role = 'unverified_sender'
    elif any(x in lower for x in ('system', 'automatic', 'auto-', 'form', 'queue', 'portal')):
        role = 'system'
    elif 'supervisor' in lower or 'operator' in lower:
        role = 'operator'
    elif 'driver' in lower:
        role = 'driver'
    elif 'billing' in lower:
        role = 'billing'
    elif 'recipient' in lower:
        role = 'recipient'
    elif 'customer' in lower:
        role = 'customer'
    else:
        role = 'service'
    aid = 'branch_' + role
    n = 2
    while aid in a['actors']:
        aid = 'branch_' + role + '_' + str(n)
        n += 1
    parts = name.split(', ', 1)
    organization = parts[1] if len(parts) > 1 and parts[1] in ('Plover Arc Logistics', 'Rivet Delivery Desk', 'Tallowmere Goods', 'Arcloom Components') else None
    a['actors'][aid] = {
        'name': parts[0] if organization else name, 'organization': organization,
        'role': role, 'from_start': False, 'source_names': [name],
        'responsibility': ('Authority is unverified; this message does not authorise action or disclosure.'
                           if role == 'unverified_sender' else
                           'Report or handle the state within the scope stated in the source message; no wider authority is inferred.'),
    }
    return aid


def fact(fid, text, eid):
    return {'id': fid, 'text': text, 'source': {'type': 'message', 'id': eid}}


def evidence_facts(a, e, prefix):
    # Attribute each statement, including disputed or unverified claims.
    name = a['actors'][actor_for(a, e['meta']['From'])]['name']
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', e['body'])
    if a['case_id'] == '003-N2' and prefix == 'branch_report':
        sentences = ['The recipient offered a permanent access code and asked for an unattended doorstep delivery; neither instruction is authorised.']
    return [fact(f'{prefix}_{i+1}', f'{name} reports: {s}', e['id']) for i, s in enumerate(sentences) if s.strip()]


def gap(gid, eid, sender, target, kind, purpose, text):
    return {'id': gid, 'kind': 'gap', 'title': 'Unrecorded intermediate action',
            'text': text, 'before_message_id': eid, 'source_event_ids': [eid],
            'implied_action': {'from_actor': sender, 'to_actor': target, 'type': kind, 'purpose': purpose}}


def snapshot_prefix(parent, keep):
    criteria = {x['id']: dict(x, status='pending', evidence_event_ids=[]) for x in parent['initial']['success_criteria']}
    requests = copy.deepcopy(parent['initial'].get('requests', {}))
    for s in parent['steps'][:keep]:
        requests.update(copy.deepcopy(s.get('requests_upsert', {})))
        for x in s.get('criteria_add', []):
            criteria[x['id']] = dict(x, status='pending', evidence_event_ids=[])
        for x in s.get('criteria_met', []):
            criteria[x['id']].update(status='met', evidence_event_ids=x['evidence_event_ids'])
    return list(criteria.values()), requests


def inherited_gap_updates(parent, keep, event):
    notes = {}
    for s in parent['steps'][:keep]:
        for note in s.get('annotations_add', []):
            notes[note['id']] = copy.deepcopy(note)
    updates = []
    for n in notes.values():
        if n['kind'] == 'gap' and not n.get('before_message_id'):
            n.update(kind='context', title='Unrecorded parent action', before_message_id=event['id'],
                     text='A separate record of this parent action is absent. The branch does not by itself establish that it occurred. The next action is now the scoped branch response. ' + n['text'])
            updates.append(n)
    return updates


def annotate(row, refresh=False):
    bid, keep = row['branch'], int(row['insert_after'])
    if bid == '002-N4':
        scaffold(bid)
        return  # Preserve the reviewed reference.
    if (W / 'annot' / f'{bid}.json').exists() and not refresh:
        return  # Normal runs never overwrite an edited annotation.
    parent = json.loads((W / 'annot' / (bid[:3] + '.json')).read_text())
    a = scaffold(bid)
    c = load_case(bid)
    new, sent, final = c['events'][keep:]
    for e in c['events']:
        for name in [e['meta']['From'], *e['meta']['To'].split(';')]:
            actor_for(a, name)
    us = a['our_actor_id']
    target = actor_for(a, sent['meta']['To'].split(';')[0])
    reporter = actor_for(a, final['meta']['From'])
    req_type, purpose, criterion, limit = RULES[row['expected_decision']]
    if row['expected_decision'] == 'ASK_CUSTOMER' and not re.search(r'\b(?:choose|choice|accept|decline|would you like|do you.*want|which (?:slot|window|option))\b', sent['body'], re.I):
        req_type = 'information'
    if row['expected_decision'] == 'WAIT_WITH_DEADLINE' and target == a.get('client_actor_id'):
        req_type = 'decision' if re.search(r'\b(?:choose|choice|accept|option)\b', sent['body'], re.I) else 'information'
    if bid == '047-N1':
        req_type = 'information'
    if row['expected_decision'] == 'SEPARATE_AUTHORITY' and re.search(r'please (?:do not|confirm you|accept only)', sent['body'], re.I):
        req_type = 'action'
    expected_action = section(c['card'], 'Next action at escalation').split('\n\n')[0]
    forbidden = section(c['card'], 'Boundaries and remaining work').removeprefix('Must not: ').strip()
    forbidden = re.sub(r'\bdo not\s+', '', forbidden, flags=re.I)
    known_text = ' '.join(e['body'] + ' ' + e['timestamp'] for e in c['events'][:keep+1])
    known_tokens = set(re.findall(r'\b[a-z]{1,5}-\d[\w-]*\b|\b\d+[a-z]\b|\b\d{2,}(?:[:.]\d+)?\b', known_text.lower()))
    forbidden = re.sub(r'\b[a-z]{1,5}-\d[\w-]*\b|\b\d+[a-z]\b|\b\d{2,}(?:[:.]\d+)?\b',
                       lambda m: m.group() if m.group().lower() in known_tokens else 'the unconfirmed value', forbidden, flags=re.I)
    if bid == '043-N1':
        forbidden = 'Enter standard pallet dimensions and an estimated weight without the shipper’s measurements.'
    a['title'] = f"{bid} · {row['label']}"
    a['provenance']['annotation_method'] = 'Source-grounded rule annotation with explicit branch coordination scope.'
    a['provenance']['source_sha256'] = {
        'index.md': hashlib.sha256((Path(c['folder']) / 'index.md').read_bytes()).hexdigest(),
        'history.md': hashlib.sha256((Path(c['folder']) / 'history.md').read_bytes()).hexdigest(),
    }
    a['limits'] = list(dict.fromkeys(parent.get('limits', []) + [limit]))
    criteria, inherited_requests = snapshot_prefix(parent, keep)
    # Retain achieved criteria. Unachieved parent outcomes are open work outside
    # this alternative coordination task, never fabricated as successes.
    retired = [x['id'] for x in criteria if x['status'] == 'pending']
    rid = 'branch_request'
    request = {'type': req_type, 'from_actor': us, 'to_actor': target,
               'responsible_actor': target, 'purpose': expected_action,
               'expected_response': criterion, 'status': 'planned', 'response': None,
               'evidence_event_ids': [new['id']]}
    decision = {'required': True, 'question': 'Which response is permitted after this development?',
                'options': [
                    {'id': row['expected_decision'].lower(), 'action': expected_action, 'allowed': True,
                     'reason': 'This follows the recorded policy and addresses the new escalation.'},
                    {'id': 'prohibited_action', 'action': forbidden, 'allowed': False,
                     'reason': 'The branch card expressly prohibits this action.'}],
                'decision_maker': us, 'selected_option': None, 'reason': None}
    new_step = a['steps'][keep]
    new_step.update(label='New escalation', title=row['label'],
        explanation=purpose + ' ' + limit, conversation_id='client' if actor_for(a, new['meta']['From']) == a.get('client_actor_id') else 'branch_service',
        facts_upsert=evidence_facts(a, new, 'branch_report'),
        requests_upsert={rid: copy.deepcopy(request)}, criteria_retire=retired,
        criteria_add=[{'id': 'branch_resolution', 'description': criterion}],
        agent_state={'status': 'ready', 'waiting_for': [], 'next_action': expected_action},
        blocker='The new escalation requires a scoped response. ' + new['body'],
        status='verification_required' if req_type == 'verification' else 'action_required',
        next_step={'type': 'action', 'responsible_actor': us, 'request_id': rid, 'description': expected_action},
        decision=copy.deepcopy(decision),
        intake_update={'source': {'type': 'negative_branch', 'id': bid}, 'summary': purpose,
                       'note': 'This is the alternative coordination task. Original outstanding outcomes remain open outside its completion scope.'},
        state_set={'goal': purpose})
    new_step['annotations_add'] = inherited_gap_updates(parent, keep, new) + [{'id': 'branch_scope', 'kind': 'context', 'title': 'Alternative completion scope',
        'text': 'Completion covers this branch’s coordination task only. Unmet parent criteria remain in prior_success_criteria; none is treated as achieved.',
        'before_message_id': new['id'], 'source_event_ids': [new['id']]}]
    if row['expected_decision'] == 'VERIFY_FIRST':
        new_step['requests_upsert']['branch_attempt'] = {
            'type': 'action', 'from_actor': us, 'to_actor': target, 'responsible_actor': target,
            'purpose': 'Record the submission or operation reported as uncertain in this message, separately from downstream execution.',
            'expected_response': 'The record owner states whether this submission or operation saved.',
            'status': 'outcome_unknown', 'response': None, 'evidence_event_ids': [new['id']]}
    # The error/receipt often discloses an unrecorded relay after the customer's
    # choice. Keep that relay as a gap, never as an invented chat message.
    last_parent = c['events'][keep - 1]
    if actor_for(a, last_parent['meta']['From']) != us and row['expected_decision'] in ('VERIFY_FIRST', 'RECONCILE_CONFLICT', 'ASK_CUSTOMER', 'RECORD_STOP'):
        if re.search(r'\byour (?:request|booking|correction|email|relay|submission|message|update)\b', new['body'], re.I):
            destination = actor_for(a, new['meta']['From'])
            if a['actors'][destination]['role'] == 'system':
                destination = target
            new_step['annotations_add'].append(gap('branch_preceding_relay', new['id'], us, destination,
                'action', 'Relay the confirmed instruction to its responsible service.',
                'This message reports an earlier desk submission or relay. Its separate outgoing record is absent; the message does not establish a successful outcome.'))
    request.update(status='awaiting_response', evidence_event_ids=[new['id'], sent['id']])
    selected = copy.deepcopy(decision)
    selected.update(selected_option=row['expected_decision'].lower(), reason='The recorded outgoing message takes this permitted response.')
    action_step = a['steps'][keep + 1]
    action_step.update(label='Desk response', title=purpose.rstrip('.'),
        explanation='The desk sends the recorded response. ' + limit,
        conversation_id='client' if target == a.get('client_actor_id') else 'branch_service',
        requests_upsert={rid: copy.deepcopy(request)},
        agent_state={'status': 'waiting', 'waiting_for': [{'actor_id': target, 'request_id': rid, 'expected': criterion}],
                     'next_action': 'Record the reply or scoped confirmation before closing this branch.'},
        blocker='The scoped reply or confirmation has not yet been recorded.',
        status='awaiting_verification' if req_type == 'verification' else 'awaiting_decision' if req_type == 'decision' else 'awaiting_response' if req_type == 'information' else 'awaiting_confirmation',
        next_step={'type': req_type, 'responsible_actor': target, 'request_id': rid, 'description': criterion},
        decision=selected)
    # An explanation or authority refusal is already communicated in this
    # message. It is not an invented request for the recipient to acknowledge.
    declarative = row['expected_decision'] == 'DECLINE_EXPLAIN' and '?' not in sent['body'] and not re.search(r'please (?:reserve|confirm|send)', sent['body'], re.I)
    inform_only = bid in ('018-N2', '042-N2', '047-N3', '050-N5')
    if declarative or inform_only:
        action_step['requests_upsert'][rid].update(status='answered', response=sent['body'])
        action_step['agent_state'] = {'status': 'ready', 'waiting_for': [],
            'next_action': 'Record any incoming follow-through within its stated scope; do not initiate a prohibited change.',
            'note': 'The outgoing record communicates a boundary or notification. No unrecorded request or acknowledgement is assumed.'}
        action_step['status'] = 'in_progress'
        action_step['blocker'] = None
        action_step['next_step'] = None
    response = copy.deepcopy(request)
    response.update(status='completed' if req_type == 'action' else 'answered', response=final['body'],
                    evidence_event_ids=[new['id'], sent['id'], final['id']])
    if reporter != target:
        response['responded_by'] = reporter
    no_reply = row['expected_decision'] == 'WAIT_WITH_DEADLINE' and re.search(r'\b(?:no (?:\w+ ){0,3}(?:reply|acceptance|apartment|choice|mandate|appointment|confirmation)|nobody answered|nothing.*by)\b', final['body'], re.I)
    if no_reply:
        response.update(status='superseded', response='The record owner confirms the deadline outcome; no answer or consent from the silent party is inferred.')
        response.pop('responded_by', None)
    final_step = a['steps'][keep + 2]
    terminal_decision = copy.deepcopy(selected)
    terminal_decision.update(required=False, reason='The follow-through confirms this scoped response. It does not imply the original task or downstream work is complete.')
    final_step.update(label='Scoped confirmation', title='Follow-through confirms the branch outcome',
        explanation='Record what the responding party actually confirms. ' + final['body'],
        conversation_id='client' if reporter == a.get('client_actor_id') else 'branch_service',
        facts_upsert=evidence_facts(a, final, 'branch_outcome'),
        requests_upsert={rid: response}, criteria_met=[{'id': 'branch_resolution', 'evidence_event_ids': [sent['id'], final['id']]}],
        agent_state={'status': 'completed', 'waiting_for': [], 'next_action': None,
                     'note': 'Only this alternative coordination task is complete. The follow-through defines the confirmed outcome and its remaining work; archived parent criteria describe the earlier scope.'},
        blocker=None, status='completed', next_step=None,
        result={'summary': final['body'], 'confirmed_by': reporter, 'evidence_event_ids': [final['id']],
                'remaining_work': 'Parent criteria are historical snapshots at the scope change. The follow-through states what remains; these boundaries still apply: ' + section(c['card'], 'Boundaries and remaining work')},
        decision=terminal_decision)
    if row['expected_decision'] == 'VERIFY_FIRST':
        attempt = copy.deepcopy(new_step['requests_upsert']['branch_attempt'])
        attempt.update(status='answered', response=final['body'],
                       evidence_event_ids=[new['id'], final['id']])
        if reporter != target:
            attempt['responded_by'] = reporter
        final_step['requests_upsert']['branch_attempt'] = attempt
    if reporter != target and not no_reply:
        final_step['annotations_add'].append(gap('branch_followthrough_relay', final['id'], us, reporter,
            'action', 'Pass the relevant verified instruction or request to the party reporting the follow-through.',
            'The follow-through is from a different party than the recorded desk response. An intermediate exchange or service-to-service relay is absent; only the final reporter’s stated outcome is confirmed.'))
        if req_type == 'decision' or (row['expected_decision'] == 'SEPARATE_AUTHORITY' and target == a.get('client_actor_id')):
            final_step['annotations_add'].append(gap('branch_missing_authorised_reply', final['id'], target, us,
                'decision' if req_type == 'decision' else 'verification',
                'Supply the authorised choice or verification before the responsible service acts.',
                'The authorised party’s separate reply is not recorded here. The service’s follow-through is indirect evidence; no extra customer message has been added.'))
        elif row['expected_decision'] == 'GET_OPTIONS':
            final_step['annotations_add'].append(gap('branch_missing_options_reply', final['id'], target, us,
                'information', 'Supply the current permitted options before they are relayed to the decision owner.',
                'The service’s options reply is not recorded separately. The decision owner’s later report is indirect evidence of the options and relay; no extra service message has been added.'))
    if declarative and reporter != target:
        final_step['annotations_add'][-1]['text'] = 'The service reports follow-through after a policy explanation addressed to another party. The notification or relay to this service is absent; no extra desk message has been added.'
    # Previous outstanding requests are not silently completed by branch closure.
    # A historical unknown outcome remains unknown unless specifically modelled.
    (W / 'annot' / f'{bid}.json').write_text(json.dumps(a, ensure_ascii=False, indent=1) + '\n')


def main():
    (W / 'briefs').mkdir(exist_ok=True)
    rows = list(csv.DictReader((NEG / 'index.csv').open(newline='')))
    for row in rows:
        annotate(row, refresh='--refresh' in sys.argv[1:])
    print(f'Covered {len(rows)} branches; preserved existing annotations unless --refresh was explicitly supplied. 002-N4 is always preserved.')


if __name__ == '__main__':
    main()
