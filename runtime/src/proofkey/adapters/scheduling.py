"""Scoped scheduling port for the independent simulated provider."""
from datetime import datetime
import json
import re

from pydantic import TypeAdapter

from ..contracts import AuthorityReadback, DispatchResult, EffectIntent, ReadRequest, Timestamp
from ..profiles import is_window_readiness_profile


class _SchedulingEnvelopeError(ValueError):
    def __init__(self, *args):
        super().__init__('synthetic_envelope_unavailable')


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise _SchedulingEnvelopeError()
        result[key] = value
    return result


def _keys(value, expected):
    if type(value) is not dict or set(value) != set(expected.split()):
        raise _SchedulingEnvelopeError()


def _string(value, *, nullable=False, identifier=True, hashed=False):
    if value is None and nullable:
        return
    if (type(value) is not str or len(value) > 1024
            or (identifier and not value.strip())
            or (hashed and re.fullmatch('[0-9a-f]{64}', value) is None)):
        raise _SchedulingEnvelopeError()


def _timestamp(value, *, nullable=False):
    if value is None and nullable:
        return
    if type(value) is not str:
        raise _SchedulingEnvelopeError()
    TypeAdapter(Timestamp).validate_python(value, strict=True)


def _references(value):
    if type(value) is not list:
        raise _SchedulingEnvelopeError()
    for item in value:
        _string(item)


def _reject_constant(value):
    raise _SchedulingEnvelopeError()


def _decode_envelope(raw: bytes, operation: str) -> dict:
    """Check the complete finite wire domain before any public model exists."""
    try:
        if type(raw) is not bytes or not 0 < len(raw) <= 262144:
            raise _SchedulingEnvelopeError()
        text = raw.decode('utf-8', errors='strict')
        depth, quoted, escaped = 0, False, False
        for character in text:
            if quoted:
                if escaped:
                    escaped = False
                elif character == '\\':
                    escaped = True
                elif character == '"':
                    quoted = False
            elif character == '"':
                quoted = True
            elif character in '[{':
                depth += 1
                if depth > 16:
                    raise _SchedulingEnvelopeError()
            elif character in ']}':
                depth -= 1
        envelope = json.loads(text, object_pairs_hook=_pairs, parse_constant=_reject_constant)
        _keys(envelope, 'contract http_status operation body')
        if (type(envelope['http_status']) is not int or envelope['http_status'] not in {200, 429, 503}
                or envelope['contract'] != 'synthetic-scheduling-envelope-v1'
                or envelope['operation'] != operation):
            raise _SchedulingEnvelopeError()
        body = envelope['body']
        if operation == 'reschedule':
            _keys(body, 'status provider_request_id evidence_refs reason')
            if body['status'] not in ('acknowledged', 'rejected', 'outcome_unknown', 'business_failed'):
                raise _SchedulingEnvelopeError()
            _string(body['provider_request_id'], nullable=True)
            _string(body['reason'], nullable=True, identifier=False)
            _references(body['evidence_refs'])
            evidence_count = len(body['evidence_refs'])
        elif operation in ('read_schedule', 'list_permitted_slots'):
            _keys(body, 'operation object_id observations provider_request_id action_id fingerprint stage nonexecution as_of evidence_refs')
            for key in ('operation', 'object_id', 'stage'):
                _string(body[key])
            for key in ('provider_request_id', 'action_id'):
                _string(body[key], nullable=True)
            _string(body['fingerprint'], nullable=True, hashed=True)
            _timestamp(body['as_of'])
            _references(body['evidence_refs'])
            observations = body['observations']
            if type(observations) is not list or len(observations) > 128:
                raise _SchedulingEnvelopeError()
            for observation in observations:
                _keys(observation, 'authority fact object_id value revision provider_at observed_at evidence_ref')
                for key in ('authority', 'fact', 'object_id', 'revision', 'evidence_ref'):
                    _string(observation[key])
                _timestamp(observation['provider_at'], nullable=True)
                _timestamp(observation['observed_at'])
            proof = body['nonexecution']
            _keys(proof, 'status basis evidence_ref')
            if proof['status'] not in ('unknown', 'proven'):
                raise _SchedulingEnvelopeError()
            _string(proof['basis'], nullable=True)
            _string(proof['evidence_ref'], nullable=True)
            evidence_count = len(body['evidence_refs']) + len(observations) + int(proof['evidence_ref'] is not None)
        else:
            raise _SchedulingEnvelopeError()
        if evidence_count > 128:
            raise _SchedulingEnvelopeError()
        # Public validation is last; it also rejects overflow-to-infinity JSON
        # numbers and validates arbitrary JsonValue content without narrowing it.
        if operation == 'reschedule':
            if body['status'] != 'business_failed':
                DispatchResult.model_validate(body)
        else:
            AuthorityReadback.model_validate(body)
        return envelope
    except (ValueError, TypeError, KeyError, RecursionError, OverflowError):
        raise _SchedulingEnvelopeError() from None


def _unresolved_dispatch():
    return DispatchResult(status='outcome_unknown', provider_request_id=None,
                          evidence_refs=[], reason='synthetic_envelope_unresolved')


def _decode_scheduling_dispatch(raw: bytes) -> DispatchResult:
    try:
        envelope = _decode_envelope(raw, 'reschedule')
        body = envelope['body']
        if (envelope['http_status'] == 200 and body['status'] == 'acknowledged'
                and body['provider_request_id'] is not None and body['evidence_refs']):
            return DispatchResult.model_validate(body)
    except _SchedulingEnvelopeError:
        pass
    return _unresolved_dispatch()


def _decode_scheduling_read(raw: bytes, operation: str) -> AuthorityReadback:
    envelope = _decode_envelope(raw, operation)
    if envelope['http_status'] != 200:
        raise _SchedulingEnvelopeError()
    return AuthorityReadback.model_validate(envelope['body'])


class SchedulingAdapter:
    def __init__(self, world):
        self._world = world

    def list_permitted_slots(self, request: ReadRequest) -> AuthorityReadback:
        if is_window_readiness_profile(self._world._profile):
            return self._read_raw('list_permitted_slots', request)
        return self._world._read("list_permitted_slots", request)

    def read_schedule(self, request: ReadRequest) -> AuthorityReadback:
        if is_window_readiness_profile(self._world._profile):
            return self._read_raw('read_schedule', request)
        return self._world._read("read_schedule", request)

    def _read_raw(self, operation, request):
        try:
            return _decode_scheduling_read(self._world._read_scheduling_raw(operation, request), operation)
        except Exception:
            raise _SchedulingEnvelopeError() from None

    def reschedule(self, intent: EffectIntent, *, deadline: datetime | None = None) -> DispatchResult:
        if is_window_readiness_profile(self._world._profile) and intent.process_version == 'v2-window-readiness':
            try:
                return _decode_scheduling_dispatch(self._world._dispatch_scheduling_raw(intent, deadline=deadline))
            except Exception:
                return _unresolved_dispatch()
        return self._world._dispatch("reschedule", intent, deadline=deadline)
