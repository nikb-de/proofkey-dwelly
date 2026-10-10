"""Scripted local-operator HTTP replay; no model or authentic Dispatch calls."""
import argparse
import hashlib
import json
import sys
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
import uuid

from .scenarios import prepare_terms_demo
from tools.dwelly_service.cases import _canonical


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _origin(value):
    if type(value) is not str or any(char.isspace() for char in value):
        raise ValueError('invalid_loopback_origin')
    try:
        parsed = urlsplit(value)
        valid = (parsed.scheme == 'http' and parsed.hostname in ('127.0.0.1', 'localhost', '::1')
                 and parsed.username is None and parsed.password is None
                 and parsed.path in ('', '/') and not parsed.query and not parsed.fragment
                 and (parsed.port is None or 1 <= parsed.port <= 65535))
    except ValueError:
        valid = False
    if not valid:
        raise ValueError('invalid_loopback_origin')
    return value.rstrip('/')


class _Client:
    def __init__(self, origin):
        self.origin = origin
        self.opener = build_opener(ProxyHandler({}), _NoRedirect())
        self.steps = []
        self.run_id = uuid.uuid4().hex

    def request(self, name, path, body=None, statuses=(200,)):
        headers = {}
        data = None
        if body is not None:
            data = json.dumps(body, ensure_ascii=False, allow_nan=False).encode('utf-8')
            headers = {'Content-Type': 'application/json', 'X-ProofKey-Request': 'platform-v1',
                       'Idempotency-Key': f'demo-{self.run_id}-{len(self.steps)}'}
        method = 'POST' if body is not None else 'GET'
        request = Request(self.origin + path, data=data, headers=headers, method=method)
        try:
            response = self.opener.open(request, timeout=15)
        except HTTPError as error:
            response = error
        with response:
            raw = response.read(4 * 1024 * 1024)
            try:
                result = json.loads(raw)
            except (ValueError, UnicodeError):
                result = {'error': {'code': 'non_json_response'}}
            status = response.status
        self.steps.append({'name': name, 'method': method, 'path': path, 'status': status,
                           'request_headers': headers, 'request': body, 'response': result})
        if status not in statuses:
            raise ValueError(f'http_status_{status}')
        return status, result


def run_terms_demo(base_url, case_id, anchor_date):
    """Create a fresh case and exercise all seven coordination transitions.

    All source events remain unchanged. Two separately labelled pseudo-Dispatch
    readbacks bind original messages 003/011 to generated local request tokens.
    Existing cases are rejected, including partially completed previous demos.
    """
    origin = _origin(base_url)
    prepared = prepare_terms_demo(case_id, anchor_date)
    client = _Client(origin)
    _, capabilities = client.request('capabilities', '/api/platform/capabilities')
    coordination = capabilities.get('coordination', {})
    if not (capabilities.get('execution_mode') == 'local_sandbox'
            and type(capabilities.get('external_effects')) is int and capabilities['external_effects'] == 0
            and coordination.get('enabled') is True and coordination.get('mode') == 'local_sandbox'
            and type(coordination.get('external_effects')) is int and coordination['external_effects'] == 0):
        raise ValueError('unsafe_platform_capabilities')
    path = '/api/platform/cases/' + case_id
    status, _ = client.request('check_new_case', path, statuses=(200, 404))
    if status != 404:
        raise ValueError('case_already_exists')
    client.request('create_case', '/api/platform/cases', prepared['declaration'], statuses=(201,))
    source_events = {event['event_id']: event for event in prepared['events']}
    phases = []
    state = None
    appended_events = []

    def append(event):
        _, current = client.request('head_before_' + event['event_id'], path)
        result = client.request('append_' + event['event_id'], path + '/events',
                                {'expected_revision': current['case']['snapshot']['revision'], 'event': event})
        appended_events.append(event)
        return result

    def command(name, **parameters):
        nonlocal state
        _, current = client.request('head_before_' + name, path)
        snapshot = current['case']['snapshot']
        version = current['case']['coordination']['version'] if current['case']['coordination'] else 0
        _, result = client.request(name, path + '/coordination', {
            'command': name, 'expected_revision': snapshot['revision'], 'snapshot_hash': snapshot['snapshot_hash'],
            'expected_workflow_version': version, **parameters})
        state = result['coordination']
        if state['mode'] != 'local_sandbox' or state['external_effects'] != 0:
            raise ValueError('unsafe_coordination_response')
        phases.append(state['phase'])
        return state

    def readback(source_id, kind):
        pending = state['pending_request']
        payload = {'qualification': 'scripted_local_attestation_not_authentic_dispatch',
                   'transport': 'local_fixture_no_message_sent', 'source_event_id': source_id,
                   'request_id': pending['request_id'], 'operation': kind,
                   'source_text': source_events[source_id]['text']}
        if kind == 'booking':
            payload['terms_hash'] = pending['terms_hash']
        event = {'event_id': 'demo-readback-' + source_id, 'occurred_at': source_events[source_id]['occurred_at'],
                 'channel': 'email', 'sender_id': 'dispatch', 'recipient_ids': ['coordinator'],
                 'kind': 'message', 'text': json.dumps(payload, ensure_ascii=False), 'media': None}
        append(event)
        return event['event_id']

    append(source_events['source-context'])
    append(source_events['001'])
    command('initialize', dispatch_actor_id='dispatch', original_booking=prepared['original_booking'])
    command('request_cancellation', evidence_event_ids=['001'])
    append(source_events['002'])
    append(source_events['003'])
    evidence = readback('003', 'cancellation')
    command('confirm_cancellation', request_id=state['pending_request']['request_id'], evidence_event_ids=[evidence])
    for event_id in ('004', '005', '006', '007'):
        append(source_events[event_id])
    command('record_offer', terms=prepared['offered_terms'], evidence_event_ids=['007'])
    append(source_events['008'])
    append(source_events['009'])
    offer = state['offer']
    command('record_consent', offer_id=offer['offer_id'], terms_hash=offer['terms_hash'], evidence_event_ids=['009'])
    command('request_booking', offer_id=offer['offer_id'], terms_hash=offer['terms_hash'])
    append(source_events['010'])
    append(source_events['011'])
    evidence = readback('011', 'booking')
    command('confirm_booking', request_id=state['pending_request']['request_id'],
            terms_hash=offer['terms_hash'], evidence_event_ids=[evidence])
    _, final = client.request('final_case', path)
    try:
        final_case = final['case']
        snapshot = final_case['snapshot']
        events = snapshot['events']
        indexed = {event['event_id']: event for event in events}
        audit_ids = {'coord-' + audit['audit_id'] for audit in state['audit_history']}
        expected_ids = {event['event_id'] for event in appended_events} | audit_ids
        digest = hashlib.sha256(_canonical({key: value for key, value in snapshot.items()
                                           if key != 'snapshot_hash'}).encode('utf-8')).hexdigest()
        consistent = (
            final_case['coordination'] == state
            and state['phase'] == 'booking_confirmed'
            and state['physical_delivery'] == 'not_confirmed'
            and state['mode'] == 'local_sandbox'
            and type(state['external_effects']) is int and state['external_effects'] == 0
            and type(snapshot['revision']) is int and snapshot['revision'] == state['revision'] == len(events)
            and snapshot['snapshot_hash'] == state['snapshot_hash'] == digest
            and len(indexed) == len(events) and set(indexed) == expected_ids
            and all(indexed[event['event_id']] == event for event in appended_events)
            and all(indexed[event_id]['channel'] == 'internal' for event_id in audit_ids)
        )
    except (KeyError, TypeError, ValueError):
        consistent = False
    if not consistent:
        raise ValueError('inconsistent_final_readback')
    return {'case_id': case_id, 'base_url': origin, 'mode': 'backend_scripted_operator_e2e',
            'qualification': 'local_operator_attestations_not_llm_output_or_authentic_dispatch',
            'model_calls': 0, 'external_effects': 0, 'phase': state['phase'],
            'physical_delivery': state['physical_delivery'], 'phase_trace': phases,
            'coordination': state, 'provenance': prepared['provenance'],
            'final_revision': final['case']['snapshot']['revision'],
            'final_snapshot_hash': final['case']['snapshot']['snapshot_hash'], 'http_steps': client.steps}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--case-id', required=True)
    parser.add_argument('--anchor-date', required=True, help='YYYY-MM-DD replacing the source initial date')
    args = parser.parse_args()
    try:
        result = run_terms_demo(args.base_url, args.case_id, args.anchor_date)
    except (ValueError, OSError) as error:
        print(json.dumps({'error': str(error)}), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
