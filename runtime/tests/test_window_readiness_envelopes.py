"""Direct source/adapter evidence only; no candidate engine execution."""
import copy
from contextlib import contextmanager
from datetime import timedelta
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from proofkey.adapters import scheduling
from proofkey.adapters.world import SimulatedWorld
from proofkey.clock import SyntheticReplayClock
from proofkey.contracts import EffectIntent, ReadRequest, ReadTarget
from proofkey.profiles import load_profile
from proofkey.source_retained_state import SourceRetainedStateFailure
from proofkey.verifier import verify
from support import build_test_runtime, make_binding, make_intent, make_request
from support_synthetic_provisioning import cj, context
from support_window_readiness import candidate_case_data


def raw(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')


def read_envelope(value='S0', *, reference='e', body_refs=None):
    stamp = '2026-10-08T10:00:00+00:00'
    return {'contract': 'synthetic-scheduling-envelope-v1', 'http_status': 200,
        'operation': 'list_permitted_slots', 'body': {
            'operation': 'list_permitted_slots', 'object_id': 'O1',
            'observations': [{'authority': 'scheduling', 'fact': 'slot', 'object_id': 'O1',
                'value': value, 'revision': 'v1', 'provider_at': stamp,
                'observed_at': stamp, 'evidence_ref': reference}],
            'provider_request_id': None, 'action_id': None, 'fingerprint': None,
            'stage': 'observed', 'nonexecution': {'status': 'unknown', 'basis': None, 'evidence_ref': None},
            'as_of': stamp, 'evidence_refs': ['body-e'] if body_refs is None else body_refs}}


def original_request(intent, purpose='reconcile'):
    return ReadRequest(case_id=intent.binding.case_id, object_id=intent.binding.object_id,
        caller_id='U1', proof_reference='synthetic-proof', purpose=purpose, deadline=intent.deadline,
        target=ReadTarget(kind='original_effect', operation=intent.operation,
            generation=intent.binding.generation, action_id=intent.action_id,
            provider_key=intent.provider_key, fingerprint=intent.argument_fingerprint))


class DecoderTests(unittest.TestCase):
    def decode(self, envelope):
        return scheduling._decode_scheduling_read(raw(envelope), 'list_permitted_slots')

    def rejects(self, value):
        with self.assertRaisesRegex(scheduling._SchedulingEnvelopeError, '^synthetic_envelope_unavailable$'):
            scheduling._decode_scheduling_read(value, 'list_permitted_slots')

    def test_conjunctive_limits_and_repeated_evidence(self):
        good = read_envelope(body_refs=['same'] * 127)
        self.assertEqual(len(self.decode(good).evidence_refs), 127)
        good['body']['evidence_refs'].append('same')
        self.rejects(raw(good))
        encoded = raw(read_envelope())
        scheduling._decode_scheduling_read(encoded + b' ' * (262144 - len(encoded)), 'list_permitted_slots')
        self.rejects(encoded + b' ' * (262145 - len(encoded)))
        # A passing byte bound never excuses an excessive reference bound.
        self.rejects(raw(read_envelope(reference='e' * 1025)))

    def test_depth_and_arbitrary_json_values(self):
        for depth in (12, 13):
            value = {'arbitrary-key': 'x' * 4096} if depth == 0 else 'leaf'
            for _ in range(depth):
                value = [value]
            if depth == 12:
                self.assertEqual(self.decode(read_envelope(value)).observations[0].value, value)
            else:
                self.rejects(raw(read_envelope(value)))
        value = {'any': ['x' * 4096, True, None, 123.5]}
        self.assertEqual(self.decode(read_envelope(value)).observations[0].value, value)
        self.decode(read_envelope('quoted } ] { [ \\"'))

    def test_observation_limit_also_counts_evidence(self):
        value = read_envelope(body_refs=[])
        observation = value['body']['observations'][0]
        value['body']['observations'] = [copy.deepcopy(observation) for _ in range(128)]
        self.assertEqual(len(self.decode(value).observations), 128)
        # 129 observations necessarily also violate the 128 evidence-occurrence bound.
        value['body']['observations'].append(observation)
        self.rejects(raw(value))

    def test_unicode_codepoint_limit_independent_of_bytes(self):
        for character in ('x', '界', '😀'):
            self.assertEqual(self.decode(read_envelope(reference=character * 1024)).observations[0].evidence_ref,
                             character * 1024)
            self.rejects(raw(read_envelope(reference=character * 1025)))

    def test_every_required_key_and_unknown_schema_key(self):
        for path in ((), ('body',), ('body', 'observations', 0), ('body', 'nonexecution')):
            base = read_envelope()
            node = base
            for part in path:
                node = node[part]
            for key in list(node):
                with self.subTest(path=path, missing=key):
                    bad = copy.deepcopy(base)
                    target = bad
                    for part in path:
                        target = target[part]
                    del target[key]
                    self.rejects(raw(bad))
            node['unexpected'] = None
            self.rejects(raw(base))

    def test_duplicate_keys_at_every_schema_level(self):
        encoded = raw(read_envelope())
        for old, new in ((b'"contract":', b'"contract":"other","contract":'),
                         (b'"object_id":"O1","observations"', b'"object_id":"O1","object_id":"O1","observations"'),
                         (b'"authority":', b'"authority":"scheduling","authority":'),
                         (b'"status":"unknown"', b'"status":"unknown","status":"unknown"')):
            self.rejects(encoded.replace(old, new, 1))

    def test_invalid_encoding_json_and_scalar_types(self):
        encoded = raw(read_envelope())
        for value in (b'', bytearray(encoded), encoded + b'{}', b'\xff', b'[]', b'null',
                      encoded.replace(b'"S0"', b'NaN'), encoded.replace(b'"S0"', b'Infinity'),
                      encoded.replace(b'"S0"', b'-Infinity'), encoded.replace(b'"S0"', b'1e999')):
            self.rejects(value)
        fields = [((), 'http_status', [True, '200', 200.0, 201, [], {}]),
                  ((), 'contract', ['unknown', None]), ((), 'operation', ['read_schedule']),
                  (('body',), 'as_of', [0, True, '2026-10-08T10:00:00', [], {}]),
                  (('body',), 'fingerprint', ['A' * 64, 'a' * 63, 5]),
                  (('body',), 'evidence_refs', [{}, [3], [' ']]),
                  (('body',), 'observations', [{}]),
                  (('body', 'nonexecution'), 'status', ['proven', True]),
                  (('body', 'observations', 0), 'provider_at', [3, '2026-10-08', {}, []])]
        for path, key, values in fields:
            for value in values:
                with self.subTest(path=path, key=key, value=value):
                    bad = read_envelope()
                    node = bad
                    for part in path:
                        node = node[part]
                    node[key] = value
                    self.rejects(raw(bad))
        for path, keys in ((('body',), ('operation', 'object_id', 'provider_request_id', 'action_id', 'stage')),
                           (('body', 'observations', 0), ('authority', 'fact', 'object_id', 'revision', 'evidence_ref')),
                           (('body', 'nonexecution'), ('basis', 'evidence_ref'))):
            for key in keys:
                for value in (0, True, [], {}, '', ' ', '界' * 1025):
                    bad = read_envelope()
                    node = bad
                    for part in path:
                        node = node[part]
                    node[key] = value
                    self.rejects(raw(bad))

    def test_source_owned_original_operation_and_nonexecution_evidence(self):
        envelope = read_envelope(body_refs=['e'] * 126)
        envelope['operation'] = 'read_schedule'
        body = envelope['body']
        body['operation'] = 'reschedule'
        body['nonexecution'] = {'status': 'proven', 'basis': 'terminal-contract', 'evidence_ref': 'proof'}
        result = scheduling._decode_scheduling_read(raw(envelope), 'read_schedule')
        self.assertEqual((result.operation, result.nonexecution.status), ('reschedule', 'proven'))
        body['evidence_refs'].append('e')
        with self.assertRaises(scheduling._SchedulingEnvelopeError):
            scheduling._decode_scheduling_read(raw(envelope), 'read_schedule')

    def test_dispatch_requires_complete_valid_200_acknowledgement(self):
        envelope = {'contract': 'synthetic-scheduling-envelope-v1', 'http_status': 200,
            'operation': 'reschedule', 'body': {'status': 'acknowledged', 'provider_request_id': 'source-id',
                                             'evidence_refs': ['source-proof'], 'reason': None}}
        self.assertEqual(scheduling._decode_scheduling_dispatch(raw(envelope)).provider_request_id, 'source-id')
        variants = []
        for key, values in (('status', ['rejected', 'outcome_unknown', 'business_failed', 'bogus']),
                            ('provider_request_id', [None, '', 'x' * 1025]),
                            ('evidence_refs', [[], ['x'] * 129]), ('reason', ['x' * 1025, 4])):
            for value in values:
                bad = copy.deepcopy(envelope)
                bad['body'][key] = value
                variants.append(raw(bad))
        for status in (429, 503, True, '200'):
            bad = copy.deepcopy(envelope)
            bad['http_status'] = status
            variants.append(raw(bad))
        for key in envelope['body']:
            bad = copy.deepcopy(envelope)
            del bad['body'][key]
            variants.append(raw(bad))
        variants += [b'not json', raw(envelope) + b' ' * 262144]
        for encoded in variants:
            result = scheduling._decode_scheduling_dispatch(encoded)
            self.assertEqual((result.status, result.provider_request_id, list(result.evidence_refs), result.reason),
                             ('outcome_unknown', None, [], 'synthetic_envelope_unresolved'))


class SourceTests(unittest.TestCase):
    def fresh_intent(self, profile='flat-window-readiness-v1', exact=False):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        request = make_request(kind='reschedule_exact', consent_mode='exact_slot', arguments={'slot': 'S1'}) if exact else None
        fx = build_test_runtime(temporary.name, profile_name=profile, request=request)
        self.addCleanup(fx.store.close)
        intent = make_intent(binding=None if request is None else make_binding(request),
            profile_version=fx.profile.version, process_version='v1' if exact or profile != 'flat-window-readiness-v1' else 'v2-window-readiness',
            expected_revisions=fx.world.material_revisions(), ownership_state_revision='v1',
            ownership_epoch=0, arguments={'slot': 'S1'}, postcondition={'slot': 'S1'})
        return fx, intent

    def rows(self, fx, table):
        with fx.world._connect() as connection:
            return [dict(row) for row in connection.execute('SELECT * FROM ' + table)]

    def test_candidate_provider_v2_success(self):
        fx, intent = self.fresh_intent()
        reply = fx.world.bundle().scheduling.reschedule(intent)
        self.assertEqual(reply.status, 'acknowledged')
        self.assertEqual(fx.world.effect_count('reschedule'), 1)
        self.assertTrue(reply.provider_request_id.startswith('provider:window-envelope-v1:'))
        self.assertEqual(verify(intent, fx.world.bundle().scheduling.read_schedule(original_request(intent)), profile=fx.profile).status,
                         'verified')

    def test_http200_business_failure_is_not_terminal(self):
        fx, intent = self.fresh_intent()
        fx.world.set_fault('reschedule', 'http200_business_failed')
        encoded = fx.world._dispatch_scheduling_raw(intent)
        decoded = json.loads(encoded)
        self.assertEqual((decoded['http_status'], decoded['body']['status']), (200, 'business_failed'))
        result = scheduling._decode_scheduling_dispatch(encoded)
        self.assertEqual((result.status, result.provider_request_id, list(result.evidence_refs), result.reason),
                         ('outcome_unknown', None, [], 'synthetic_envelope_unresolved'))
        self.assertEqual(self.rows(fx, 'effects'), [])
        self.assertEqual(self.rows(fx, 'final_rejections'), [])
        self.assertEqual(verify(intent, fx.world.bundle().scheduling.read_schedule(original_request(intent)), profile=fx.profile).status,
                         'outcome_unknown')

    def test_raw_dispatch_and_independent_original_outcomes(self):
        for fault, raw_status, count, final in (('none', 'acknowledged', 1, 'verified'),
                ('timeout_before', 'outcome_unknown', 0, 'outcome_unknown'),
                ('timeout_after', 'outcome_unknown', 1, 'verified'),
                ('business_rejection', 'rejected', 0, 'rejected'),
                ('final_rejection_unknown', 'outcome_unknown', 0, 'rejected')):
            with self.subTest(fault=fault):
                fx, intent = self.fresh_intent()
                fx.world.set_fault('reschedule', fault)
                with patch.object(fx.world, '_dispatch', side_effect=AssertionError('typed dispatch used')):
                    encoded = fx.world._dispatch_scheduling_raw(intent)
                self.assertEqual(json.loads(encoded)['body']['status'], raw_status)
                self.assertEqual(scheduling._decode_scheduling_dispatch(encoded).status,
                                 'acknowledged' if fault == 'none' else 'outcome_unknown')
                self.assertEqual(fx.world.effect_count('reschedule'), count)
                with patch.object(fx.world, '_read', side_effect=AssertionError('typed read used')):
                    reply = fx.world.bundle().scheduling.read_schedule(original_request(intent))
                self.assertEqual(verify(intent, reply, profile=fx.profile).status, final)

    def test_window_terminal_is_joined_without_legacy_knob(self):
        fx, intent = self.fresh_intent()
        fx.world.set_fault('reschedule', 'final_rejection_unknown')
        self.assertEqual(fx.world.bundle().scheduling.reschedule(intent).status, 'outcome_unknown')
        reply = fx.world.bundle().scheduling.read_schedule(original_request(intent))
        self.assertEqual(reply.nonexecution.status, 'proven')
        self.assertTrue(reply.provider_request_id.startswith('provider:window-envelope-v1:'))
        self.assertEqual(verify(intent, reply, profile=fx.profile).status, 'rejected')

    def test_version_consent_and_source_slot_fences(self):
        for change in ('exact-consent', 'goods-v2', 'service-v2', 'stale', 'non-S0', 'exact-window'):
            with self.subTest(change=change):
                fx, intent = self.fresh_intent()
                if change in ('exact-consent', 'non-S0', 'stale'):
                    fx.world.mutate('customer.consent_mode' if change == 'exact-consent' else 'scheduling.slot',
                                    'exact_slot' if change == 'exact-consent' else 'S2')
                    if change != 'stale':
                        intent = EffectIntent.model_validate({**intent.model_dump(), 'expected_revisions': fx.world.material_revisions()})
                if change in ('goods-v2', 'service-v2'):
                    intent = make_intent(operation='register_goods_refusal' if change == 'goods-v2' else 'register_service_refusal',
                        profile_version='v1.3', process_version='v2-window-readiness',
                        expected_revisions=fx.world.material_revisions())
                if change == 'exact-window':
                    intent = EffectIntent.model_validate({**intent.model_dump(), 'process_version': 'v1'})
                result = fx.world._dispatch(intent.operation, intent)
                self.assertEqual(result.status, 'rejected')
                self.assertEqual(self.rows(fx, 'effects'), [])
                self.assertEqual(self.rows(fx, 'final_rejections'), [])

    def test_direct_legacy_reference_domain_contrast(self):
        for profile in ('flat-v1.3', 'flat-window-readiness-v1'):
            for length in (1024, 1025):
                fx, intent = self.fresh_intent(profile)
                request = ReadRequest(case_id='C1', object_id='O1', caller_id='U1', proof_reference='synthetic-proof',
                    purpose='authority', deadline=intent.deadline,
                    target=ReadTarget(kind='authority_facts', authority='scheduling', facts=['slot']))
                with fx.world._connect() as connection:
                    connection.execute("UPDATE facts SET evidence_ref=? WHERE identity='scheduling.slot'", ('x' * length,))
                if profile == 'flat-window-readiness-v1' and length == 1025:
                    with self.assertRaises(scheduling._SchedulingEnvelopeError):
                        fx.world.bundle().scheduling.list_permitted_slots(request)
                else:
                    self.assertEqual(len(fx.world.bundle().scheduling.list_permitted_slots(request).observations[0].evidence_ref), length)
                self.assertEqual(self.rows(fx, 'effects'), [])

    def test_original_full_join_and_corrupt_source_fields(self):
        for table in ('effects', 'final_rejections'):
            for field in ('account_id', 'case_id', 'object_id', 'operation', 'generation',
                          'action_id', 'provider_key', 'fingerprint', 'identity_hash',
                          'namespace', 'digest', 'time-type', 'time-naive', 'time-future'):
                with self.subTest(table=table, field=field):
                    fx, intent = self.fresh_intent()
                    if table == 'final_rejections':
                        fx.world.set_fault('reschedule', 'final_rejection_unknown')
                    fx.world.bundle().scheduling.reschedule(intent)
                    row = self.rows(fx, table)[0]
                    column = {'namespace': 'request_id', 'digest': 'request_id', 'time-type': 'created_at',
                              'time-naive': 'created_at', 'time-future': 'created_at'}.get(field, field)
                    value = {'namespace': 'provider:broken:' + 'a' * 64,
                             'digest': row['request_id'][:-1] + ('a' if row['request_id'][-1] != 'a' else 'b'),
                             'identity_hash': 'b' * 64, 'fingerprint': 'a' * 64,
                             'time-type': sqlite3.Binary(b'2026-10-08T10:00:00Z'),
                             'time-naive': '2026-10-08T10:00:00', 'time-future': '2026-10-09T10:00:00Z'}.get(field, 'different')
                    with fx.world._connect() as connection:
                        connection.execute('UPDATE ' + table + ' SET ' + column + '=?', (value,))
                    corrupted = self.rows(fx, table)
                    reply = fx.world.bundle().scheduling.read_schedule(original_request(intent))
                    self.assertEqual(verify(intent, reply, profile=fx.profile).status, 'outcome_unknown')
                    self.assertEqual(reply.nonexecution.status, 'unknown')
                    self.assertEqual(self.rows(fx, table), corrupted)

    def test_original_effect_and_terminal_coexistence_is_unknown(self):
        fx, intent = self.fresh_intent()
        fx.world.bundle().scheduling.reschedule(intent)
        fields = 'account_id,provider_key,case_id,object_id,operation,generation,action_id,fingerprint,identity_hash,request_id,created_at'
        with fx.world._connect() as connection:
            connection.execute('INSERT INTO final_rejections SELECT ' + fields + ' FROM effects')
        reply = fx.world.bundle().scheduling.read_schedule(original_request(intent))
        self.assertEqual(reply.nonexecution.status, 'unknown')
        self.assertEqual(verify(intent, reply, profile=fx.profile).status, 'outcome_unknown')

    def test_dispatch_does_not_adopt_contradictory_original(self):
        fx, intent = self.fresh_intent()
        fx.world.bundle().scheduling.reschedule(intent)
        fields = 'account_id,provider_key,case_id,object_id,operation,generation,action_id,fingerprint,identity_hash,request_id,created_at'
        with fx.world._connect() as connection:
            connection.execute('INSERT INTO final_rejections SELECT ' + fields + ' FROM effects')
        result = json.loads(fx.world._dispatch_scheduling_raw(intent))['body']
        self.assertEqual(result['reason'], 'idempotency_conflict')
        self.assertEqual(len(self.rows(fx, 'effects')), 1)

    def test_terminal_rejects_wrong_profile_version_before_namespace(self):
        fx, intent = self.fresh_intent()
        fx.world.set_fault('reschedule', 'final_rejection_unknown')
        intent = EffectIntent.model_validate({**intent.model_dump(), 'profile_version': 'v1.2'})
        result = fx.world._dispatch_scheduling_raw(intent)
        self.assertEqual(json.loads(result)['body']['status'], 'rejected')
        self.assertEqual(self.rows(fx, 'final_rejections'), [])

    def test_duplicate_join_guard_with_schema_constraint_and_query_seam(self):
        for table in ('effects', 'final_rejections'):
            fx, intent = self.fresh_intent()
            if table == 'final_rejections':
                fx.world.set_fault('reschedule', 'final_rejection_unknown')
            fx.world.bundle().scheduling.reschedule(intent)
            with self.assertRaises(sqlite3.IntegrityError):
                with fx.world._connect() as connection:
                    connection.execute('INSERT INTO ' + table + ' SELECT * FROM ' + table)
            connect = fx.world._connect

            class DuplicateRows:
                def __init__(self, connection):
                    self.connection = connection

                def execute(self, sql, params=()):
                    result = self.connection.execute(sql, params)
                    if sql.startswith('SELECT * FROM ' + table + ' WHERE account_id=? AND case_id=?'):
                        rows = result.fetchall()
                        class Rows:
                            def fetchall(self):
                                return rows + rows
                        return Rows()
                    return result

            @contextmanager
            def duplicate_connection():
                with connect() as connection:
                    yield DuplicateRows(connection)

            with patch.object(fx.world, '_connect', duplicate_connection):
                reply = fx.world.bundle().scheduling.read_schedule(original_request(intent))
            self.assertEqual(verify(intent, reply, profile=fx.profile).status, 'outcome_unknown')

    def test_original_acl_early_faults_and_purpose_independence(self):
        for fault in ('none', 'timeout_before', 'timeout_after', 'business_rejection', '429', 'acl'):
            fx, intent = self.fresh_intent()
            fx.world.set_fault('reschedule', 'final_rejection_unknown')
            fx.world.bundle().scheduling.reschedule(intent)
            if fault == 'acl':
                with fx.world._connect() as connection:
                    connection.execute("UPDATE scopes SET readers='{}'")
            else:
                fx.world.set_fault('read_schedule', fault)
            for purpose in ('reconcile', 'operator_packet', 'arbitrary-purpose'):
                reply = fx.world.bundle().scheduling.read_schedule(original_request(intent, purpose))
                self.assertEqual(reply.nonexecution.status, 'proven' if fault == 'none' else 'unknown')

    def test_same_key_reuse_conflict_and_invalid_saved_identity(self):
        for table in ('effects', 'final_rejections'):
            fx, intent = self.fresh_intent()
            if table == 'final_rejections':
                fx.world.set_fault('reschedule', 'final_rejection_unknown')
            first = json.loads(fx.world._dispatch_scheduling_raw(intent))['body']
            stored = self.rows(fx, table)
            repeated = json.loads(fx.world._dispatch_scheduling_raw(intent))['body']
            self.assertEqual(repeated['provider_request_id'], first['provider_request_id'])
            self.assertEqual(self.rows(fx, table), stored)
            conflict = EffectIntent.model_validate({**intent.model_dump(), 'deadline': intent.deadline + timedelta(seconds=1)})
            result = json.loads(fx.world._dispatch_scheduling_raw(conflict))['body']
            self.assertEqual(result['reason'], 'idempotency_conflict')
            with fx.world._connect() as connection:
                connection.execute('UPDATE ' + table + " SET request_id='provider:broken'")
            result = json.loads(fx.world._dispatch_scheduling_raw(intent))['body']
            self.assertEqual(result['reason'], 'idempotency_conflict')
            self.assertEqual(len(self.rows(fx, table)), 1)

    def test_request_id_collision_across_each_source_table(self):
        for table in ('effects', 'final_rejections'):
            fx, intent = self.fresh_intent()
            if table == 'final_rejections':
                fx.world.set_fault('reschedule', 'final_rejection_unknown')
            fx.world.bundle().scheduling.reschedule(intent)
            row = self.rows(fx, table)[0]
            # Keep the colliding row under a different legal composite primary key.
            with fx.world._connect() as connection:
                connection.execute('UPDATE ' + table + " SET provider_key='other-key'")
            if table == 'effects':
                fx.world.mutate('scheduling.slot', 'S0')
            intent = EffectIntent.model_validate({**intent.model_dump(), 'expected_revisions': fx.world.material_revisions()})
            with patch('proofkey.adapters.world._window_original_request_id', return_value=row['request_id']):
                result = json.loads(fx.world._dispatch_scheduling_raw(intent))['body']
            self.assertEqual(result['reason'], 'idempotency_conflict')
            self.assertEqual(len(self.rows(fx, table)), 1)
            self.assertEqual(self.rows(fx, 'final_rejections' if table == 'effects' else 'effects'), [])

    def test_typed_routes_and_legacy_terminal_knob(self):
        for profile, exact in (('flat-v1.3', False), ('flat-v1.3', True), ('flat-window-readiness-v1', True)):
            fx, intent = self.fresh_intent(profile, exact=exact)
            fx.world.set_fault('reschedule', 'final_rejection_unknown')
            with patch.object(fx.world, '_dispatch_scheduling_raw', side_effect=AssertionError('raw exact dispatch')):
                result = fx.world.bundle().scheduling.reschedule(intent)
            self.assertEqual(result.status, 'outcome_unknown')
            if profile == 'flat-v1.3':
                with patch.object(fx.world, '_read_scheduling_raw', side_effect=AssertionError('raw legacy read')):
                    reply = fx.world.bundle().scheduling.read_schedule(original_request(intent))
            else:
                reply = fx.world.bundle().scheduling.read_schedule(original_request(intent))
            self.assertEqual(reply.nonexecution.status, 'unknown')
            fx.world.set_fault('read_schedule', 'terminal_not_executed')
            reply = fx.world.bundle().scheduling.read_schedule(original_request(intent))
            self.assertEqual(reply.nonexecution.status, 'proven')

    def test_all_candidate_reads_use_raw_and_preserve_error_boundary(self):
        fx, intent = self.fresh_intent()
        request = ReadRequest(case_id='C1', object_id='O1', caller_id='U1', proof_reference='synthetic-proof',
            purpose='authority', deadline=intent.deadline,
            target=ReadTarget(kind='authority_facts', authority='scheduling', facts=['slot']))
        with patch.object(fx.world, '_read', side_effect=AssertionError('typed candidate read')):
            self.assertEqual(fx.world.bundle().scheduling.list_permitted_slots(request).observations[0].value, 'S0')
        with patch.object(fx.world, '_read_scheduling_raw', side_effect=RuntimeError('secret raw payload')):
            with self.assertRaisesRegex(scheduling._SchedulingEnvelopeError, '^synthetic_envelope_unavailable$'):
                fx.world.bundle().scheduling.read_schedule(original_request(intent))
        with patch.object(fx.world, '_dispatch_scheduling_raw', side_effect=RuntimeError('secret raw payload')):
            self.assertEqual(fx.world.bundle().scheduling.reschedule(intent).reason, 'synthetic_envelope_unresolved')

    def test_direct_committed_effect_survives_unreadable_original(self):
        for corrupt in ('malformed', 'over-bound'):
            fx, intent = self.fresh_intent()
            self.assertEqual(fx.world.bundle().scheduling.reschedule(intent).status, 'acknowledged')
            stored = self.rows(fx, 'effects')
            encoded = fx.world._read_scheduling_raw('read_schedule', original_request(intent))
            if corrupt == 'malformed':
                encoded = b'{malformed'
            else:
                value = json.loads(encoded)
                value['body']['observations'][0]['evidence_ref'] = 'x' * 1025
                encoded = raw(value)
            with patch.object(fx.world, '_read_scheduling_raw', return_value=encoded):
                with self.assertRaises(scheduling._SchedulingEnvelopeError):
                    fx.world.bundle().scheduling.read_schedule(original_request(intent))
            self.assertEqual(self.rows(fx, 'effects'), stored)
            self.assertEqual(len([c for c in fx.world.calls if c.purpose == 'dispatch']), 1)


class CaptureTests(unittest.TestCase):
    def fresh_source(self, *, terminal=False, profile='flat-window-readiness-v1', exact=False):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        request, source = candidate_case_data()
        if exact:
            request = type(request).model_validate({**request.model_dump(), 'kind': 'reschedule_exact',
                                                    'consent_mode': 'exact_slot', 'arguments': {'slot': 'J06-S3'}})
            from proofkey.identity import request_fingerprint
            source['facts']['customer.consent_mode']['value'] = 'exact_slot'
            source['facts']['customer.request_fingerprint']['value'] = request_fingerprint(request)
        clock = SyntheticReplayClock()
        world = SimulatedWorld(Path(folder.name) / 'world.sqlite', 'unused',
            profile=load_profile(profile), clock=clock, fixture_bytes=cj(source))
        intent = make_intent(binding=make_binding(request), profile_version='v1.3',
            process_version='v1' if exact or profile != 'flat-window-readiness-v1' else 'v2-window-readiness',
            expected_revisions=world.material_revisions(), ownership_state_revision='v1', ownership_epoch=0,
            arguments={'slot': 'J06-S3'}, postcondition={'slot': 'J06-S3'})
        if terminal:
            world.set_fault('reschedule', 'final_rejection_unknown')
        world.bundle().scheduling.reschedule(intent)
        return world, clock, 'final_rejections' if terminal else 'effects'

    def rows(self, world, table):
        with world._connect() as connection:
            return [dict(row) for row in connection.execute('SELECT * FROM ' + table)]

    def test_retained_capture_accepts_window_exact_and_legacy_outcomes(self):
        for terminal in (False, True):
            for profile, exact in (('flat-window-readiness-v1', False), ('flat-window-readiness-v1', True), ('flat-v1.3', False)):
                with self.subTest(terminal=terminal, profile=profile, exact=exact):
                    world, clock, table = self.fresh_source(terminal=terminal, profile=profile, exact=exact)
                    self.assertEqual(len(self.rows(world, table)), 1)
                    before = self.rows(world, table)
                    snapshot = world.capture_retained_state(execution=context(clock), clock=clock)
                    self.assertEqual(dict(snapshot.table_counts)[table], 1)
                    self.assertEqual(self.rows(world, table), before)

    def test_retained_capture_rejects_corrupt_join_digest_and_namespace_without_repair(self):
        for terminal in (False, True):
            for field in ('account_id', 'provider_key', 'case_id', 'object_id', 'operation', 'generation',
                          'action_id', 'fingerprint', 'identity_hash', 'request_id', 'namespace'):
                with self.subTest(terminal=terminal, field=field):
                    world, clock, table = self.fresh_source(terminal=terminal)
                    column = 'request_id' if field == 'namespace' else field
                    value = 'b' * 64 if field in ('fingerprint', 'identity_hash') else 'corrupted'
                    if field == 'request_id':
                        old = self.rows(world, table)[0]['request_id']
                        value = old[:-1] + ('a' if old[-1] != 'a' else 'b')
                    with world._connect() as connection:
                        connection.execute('UPDATE ' + table + ' SET ' + column + '=?', (value,))
                    before = self.rows(world, table)
                    with self.assertRaises(SourceRetainedStateFailure):
                        world.capture_retained_state(execution=context(clock), clock=clock)
                    self.assertEqual(self.rows(world, table), before)
if __name__ == '__main__':
    unittest.main()
