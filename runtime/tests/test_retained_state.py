"""Complete private retained images on synthetic journals, never activation evidence."""
from dataclasses import replace, FrozenInstanceError
from datetime import timedelta
import importlib
import json
from hashlib import sha256
from pathlib import Path
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Event

from proofkey.execution import ExecutionContext
from proofkey.journal import CaseStore, JournalFailure
from support import NOW, DEADLINE, make_auth, make_binding, make_checkpoint, make_request, make_intent, make_result, make_fixture_campaign


TABLES = (
    ('admission_accounts', ('claimed_case_id', 'account_json', 'revision'), ('claimed_case_id',)),
    ('admission_attempts', ('attempt_id', 'claimed_case_id', 'dedup_hash', 'attempt_json', 'state'), ('attempt_id',)),
    ('admission_audit', ('sequence', 'claimed_case_id', 'event_json'), ('sequence',)),
    ('admission_entries', ('entry_id', 'attempt_id', 'claimed_case_id', 'charge_generation', 'lease_json', 'state'), ('entry_id',)),
    ('audit', ('sequence', 'case_id', 'event_json'), ('sequence',)),
    ('campaigns', ('permit_hash', 'campaign_id', 'permit_json', 'consumed_json', 'revision'), ('permit_hash',)),
    ('cases', ('case_id', 'checkpoint_json', 'revision'), ('case_id',)),
    ('entries', ('entry_id', 'case_id', 'generation', 'kind', 'subject_id', 'lease_json', 'state'), ('entry_id',)),
    ('intents', ('action_id', 'case_id', 'generation', 'fingerprint', 'intent_json', 'dispatch_state', 'verification_json'), ('action_id',)),
    ('invocations', ('invocation_id', 'case_id', 'generation', 'role', 'permit_hash', 'reservation_json', 'state', 'receipt_json'), ('invocation_id',)),
    ('original_requests', ('case_id', 'generation', 'request_json'), ('case_id', 'generation')),
    ('requests', ('case_id', 'generation', 'binding_json', 'versions_json', 'stop_requested', 'request_id', 'request_revision', 'consent_revision', 'fingerprint'), ('case_id', 'generation')),
    ('results', ('case_id', 'generation', 'result_json'), ('case_id', 'generation')),
    ('schema_meta', ('version',), ()),
    ('transfers', ('transfer_id', 'case_id', 'generation', 'transfer_json', 'state'), ('transfer_id',)),
    ('waits', ('question_id', 'case_id', 'generation', 'wait_json'), ('question_id',)),
)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')


class Clock:
    def __init__(self):
        self.utc, self.tick = NOW, 100.0

    def now(self):
        return self.utc

    def monotonic(self):
        return self.tick

    def advance(self, seconds):
        self.utc += timedelta(seconds=seconds)
        self.tick += seconds


class ForwardConnection:
    """Forward real SQLite operations; barriers/observations exist only in tests."""
    def __init__(self, db, after=None):
        self.actual, self.after = db, after
        self.sql, self.steps, self.intervals, self.chunks = [], 0, [], []
        self.handler_active = False
        self.metadata_rows = 0

    def __getattr__(self, name):
        return getattr(self.actual, name)

    def execute(self, sql, parameters=()):
        self.sql.append(sql)
        cursor = self.actual.execute(sql, parameters)
        if self.after:
            self.after(sql)
        if 'substr(CAST(' in sql:
            row = cursor.fetchone()
            self.chunks.append(len(row[0]))
            return OneRow(row)
        if sql.startswith('SELECT rowid,') and 'FROM sqlite_master' not in sql:
            return ForwardRows(cursor, self)
        return cursor

    def set_progress_handler(self, callback, interval):
        self.handler_active = callback is not None
        if callback is None:
            return self.actual.set_progress_handler(None, interval)
        self.steps = 0
        self.intervals.append(interval)
        def forward():
            self.steps += interval
            return callback()
        return self.actual.set_progress_handler(forward, interval)


class OneRow:
    def __init__(self, row):
        self.row = row

    def fetchone(self):
        return self.row


class ForwardRows:
    def __init__(self, cursor, connection):
        self.cursor, self.connection = cursor, connection

    def __iter__(self):
        for row in self.cursor:
            self.connection.metadata_rows += 1
            yield row


class RetainedStateTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / 'journal.sqlite'
        self.store = CaseStore(self.path)
        self.addCleanup(lambda: self.store.close())
        self.clock = Clock()

    def module(self):
        return importlib.import_module('proofkey.retained_state')

    def capture(self, **kwargs):
        execution = kwargs.pop('execution') if 'execution' in kwargs else ExecutionContext.capture(self.clock.utc + timedelta(seconds=5), self.clock)
        return self.store.capture_retained_state(execution=execution, clock=self.clock, **kwargs)

    def beforeimage(self):
        with sqlite3.connect(self.path) as db:
            schema = [list(row) for row in db.execute("SELECT type,name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name")]
            tables = []
            for name, columns, keys in TABLES:
                sql = 'SELECT ' + ','.join(columns) + ' FROM ' + name
                if keys:
                    sql += ' ORDER BY ' + ','.join(keys)
                tables.append(dict(name=name, columns=list(columns), rows=[list(row) for row in db.execute(sql)]))
            return dict(domain='case-store-retained-state-v1', schema_version=1, schema=schema, tables=tables)

    def test_empty_image_contains_all_tables_actual_schema_and_single_version_row(self):
        expected = self.beforeimage()
        result = self.capture()
        self.assertEqual(result.payload, canonical(expected))
        self.assertEqual(result.total_rows, 1)
        self.assertEqual(result.table_counts, tuple((name, int(name == 'schema_meta')) for name, _, _ in TABLES))
        self.assertEqual(result.schema_hash, sha256(canonical(expected['schema'])).hexdigest())
        self.assertEqual(result.content_hash, sha256(result.payload).hexdigest())
        self.assertEqual(self.beforeimage(), expected)

    def test_nullable_primary_key_ties_preserve_complete_multiplicity_and_reopen_identity(self):
        # Break caught: rejecting, dropping or physically ordering permitted NULL-key ties.
        expected_rows = [[None, None, 0], [None, None, 10], [None, None, 2],
                         [None, None, 2], ['', None, 3], ['A', None, 9]]
        first = None
        physical = [[None, None, 2], ['A', None, 9], [None, None, 10],
                    [None, None, 2], ['', None, 3], [None, None, 0]]
        for order in (physical, list(reversed(physical))):
            with self.subTest(order=order):
                with sqlite3.connect(self.path) as db:
                    db.execute('DELETE FROM cases')
                    db.executemany('INSERT INTO cases VALUES(?,?,?)', order)
                before = self.beforeimage()
                expected = json.loads(canonical(before))
                next(table for table in expected['tables'] if table['name'] == 'cases')['rows'] = expected_rows
                limits = self.module().RetainedStateLimitsV1(max_rows=7, max_payload_bytes=len(canonical(expected)))
                self.store._db = ForwardConnection(self.store._db)
                try:
                    result = self.capture(limits=limits)
                except JournalFailure as error:
                    self.fail('Permitted complete NULL-key image denied: ' + str(error))
                self.assertEqual(result.payload, canonical(expected))
                self.assertEqual(result.total_rows, 7)
                self.assertEqual(dict(result.table_counts)['cases'], 6)
                self.assertEqual(json.loads(result.payload)['tables'][6]['rows'].count([None, None, 2]), 2)
                self.assertEqual(self.beforeimage(), before)
                if first is None:
                    first = result
                self.assertEqual((result.payload, result.content_hash), (first.payload, first.content_hash))
                for field in ('max_rows', 'max_payload_bytes'):
                    with self.assertRaisesRegex(JournalFailure, '^retained_state_limit$'):
                        self.capture(limits=replace(limits, **{field: getattr(limits, field) - 1}))
                self.assertFalse(self.store._db.in_transaction)
                self.assertFalse(self.store._db.handler_active)
                self.assertIsNone(self.store._execution)
                self.assertEqual(self.store._db.execute('PRAGMA busy_timeout').fetchone()[0], 10000)
                self.store.close()
                self.store = CaseStore(self.path)
                reopened = self.capture()
                self.assertEqual((reopened.payload, reopened.content_hash), (first.payload, first.content_hash))

    def test_detached_nullable_tie_order_and_nonnull_duplicate_identities(self):
        # Break caught: nullable tie rejection, noncanonical ties or nonNULL duplicate admission.
        base = self.capture()
        def detached(rows):
            data = json.loads(base.payload)
            next(table for table in data['tables'] if table['name'] == 'cases')['rows'] = rows
            payload = canonical(data)
            counts = tuple((name, len(rows) if name == 'cases' else count) for name, count in base.table_counts)
            return replace(base, payload=payload, content_hash=sha256(payload).hexdigest(),
                           table_counts=counts, total_rows=1 + len(rows))
        valid = [[None, None, 0], [None, None, 10], [None, None, 2], [None, None, 2], ['A', None, 9]]
        try:
            result = detached(valid)
        except ValueError:
            self.fail('Detached canonical NULL-key multiplicity denied')
        self.assertEqual(json.loads(result.payload)['tables'][6]['rows'], valid)
        self.assertEqual(result.total_rows, 6)
        for rows in (
            [[None, None, 2], [None, None, 10]],
            [['A', None, 9], [None, None, 0]],
            [['A', None, 0], ['A', None, 0]],
            [['A', None, 0], ['A', None, 1]],
        ):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                detached(rows)

    def test_limits_reject_bool_zero_nonfinite_and_raised_ceilings(self):
        cls = self.module().RetainedStateLimitsV1
        for field, values in (
            ('max_rows', (True, 0, -1, 4097, 1.0)),
            ('max_row_bytes', (True, 0, 262145)),
            ('max_payload_bytes', (True, 0, 4194305)),
            ('max_sqlite_steps', (True, 0, 1000001)),
            ('max_capture_seconds', (True, 0.0, -1.0, 5.1, float('nan'), float('inf'), 1)),
        ):
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    cls(**{field: value})

    def populate(self):
        from proofkey.contracts import BudgetLedger, RoleAllowance, InvocationRequest, ProcessorIdentity, ProcessingReceipt, VerificationResult, WaitState, TransferIntent
        for case in ('C1', 'C2'):
            request = make_request(case_id=case, narrative='Original \\ " words\nКот😀\x00', evidence_ids=['original-evidence'])
            binding = make_binding(request=request)
            budget = BudgetLedger(case_id=case, deadline=DEADLINE,
                role_allowances={'extraction': RoleAllowance(max_invocations=3, max_cost=6.0, usage_allowances={'tokens': 60.0})})
            self.store.admit(binding, request, make_checkpoint(binding=binding, budget=budget))
        binding = self.store.checkpoint('C1').binding
        intent = make_intent(binding=binding)
        self.store.prepare(intent)
        lease = self.store.begin_dispatch(intent, NOW)
        self.store.record_verification(intent.action_id, VerificationResult(status='outcome_unknown'))
        self.store.save_result(make_result(binding=binding))
        self.store.save_wait(WaitState(question_id='question-old', binding=binding, origin='start', next_gate='resume',
            recipient='U1', owner_state_revision='state-1', awaited_fields=['slot'], expires_at=DEADLINE,
            budget=self.store.checkpoint('C1').budget))
        self.store.save_transfer(TransferIntent(transfer_id='transfer-old', binding=binding, case_id='C1', packet_id='packet-1',
            packet_hash='3' * 64, packet_revision='v1', expected_owner='agent', expected_state_revision='state-1',
            expected_epoch=0, target_owner='operator', expires_at=DEADLINE), 'pending')
        self.store.set_stop('C1', 'G1')
        new_request = make_request(request_id='REQ2', request_revision='v2', narrative='explicit successor')
        new_binding = make_binding(request=new_request, generation='G2', supersedes_generation='G1')
        self.store.bind(new_binding)
        self.store.save_request(new_binding, new_request)
        self.store.save_checkpoint(make_checkpoint(binding=new_binding, next_gate='original-successor-gate',
            budget=self.store.checkpoint('C1').budget))
        grant = make_fixture_campaign()
        self.store.register_campaign(grant)
        identity = ProcessorIdentity(case_id='C2', generation='G1', role='extraction', campaign_id=grant.campaign_id,
            permit_hash=grant.permit_hash, input_hashes=grant.input_hashes, provider=grant.provider, model=grant.model,
            endpoint=grant.endpoint, prompt_hash='2' * 64, version='v1', profile_version='v1', process_version='v1', deadline=DEADLINE)
        self.store.reserve_invocation(InvocationRequest(identity=identity, invocation_id='unknown-invocation',
            requested_usage={'tokens': 20.0}, worst_case_cost=2.0), NOW)
        self.store.record_processing('unknown-invocation', ProcessingReceipt(invocation_id='unknown-invocation', role='extraction',
            provider=grant.provider, requested_model=grant.model, prompt_hash=identity.prompt_hash, version='v1',
            input_hashes=grant.input_hashes, mode='synthetic', status='outcome_unknown', latency_seconds=0.0,
            usage={}, processed_at=NOW))
        settled = self.store.begin_read('C2', NOW)
        self.store.finish_entry(settled.entry_id, 1.25)
        from proofkey.budget import BudgetExceeded
        overrun = self.store.begin_read('C2', NOW)
        with self.assertRaises(BudgetExceeded):
            self.store.finish_entry(overrun.entry_id, overrun.reserved_seconds + 1)
        for case, elapsed in (('NO-CASE-active', None), ('NO-CASE-settled', 2.5), ('NO-CASE-overrun', 11.0)):
            attempt = self.store.start_admission('attempt-' + case, make_auth(), make_request(case_id=case), NOW, DEADLINE)
            entry = self.store.begin_admission_read(attempt.attempt_id, NOW)
            if elapsed is not None:
                if elapsed > entry.reserved_seconds:
                    with self.assertRaises(BudgetExceeded):
                        self.store.finish_admission_read(entry.entry_id, elapsed)
                else:
                    self.store.finish_admission_read(entry.entry_id, elapsed)
        return lease

    def test_full_original_history_and_case_less_accounting_preserved_without_refund(self):
        lease = self.populate()
        expected = self.beforeimage()
        result = self.capture()
        self.assertEqual(json.loads(result.payload), expected)
        self.assertEqual(result.payload, canonical(expected))
        self.assertEqual(self.beforeimage(), expected)
        rows = {table['name']: table['rows'] for table in expected['tables']}
        self.assertEqual(len(rows['cases']), 2)
        self.assertEqual(len(rows['admission_accounts']), 3)
        self.assertEqual({row[6] for row in rows['entries']}, {'active', 'settled', 'overrun'})
        self.assertEqual({row[5] for row in rows['admission_entries']}, {'active', 'settled', 'overrun'})
        self.assertEqual(self.store.entry(lease.entry_id).state, 'active')
        self.assertTrue(self.store.generation_stop(self.store.request_bindings('C1')[0]).requested)
        self.assertEqual(self.store.campaign_usage(rows['campaigns'][0][0])['cost'], 2.0)
        self.assertEqual(rows['invocations'][0][6], 'outcome_unknown')
        self.assertIsNotNone(rows['invocations'][0][7])

    def test_snapshot_rejects_noncanonical_incomplete_and_inconsistent_private_data(self):
        result = self.capture()
        malformed = json.loads(result.payload)
        malformed['tables'].pop()
        for changes in (
            {'kind': 'approved'}, {'schema_version': True}, {'schema_hash': '0' * 64},
            {'payload': bytearray(result.payload)}, {'content_hash': '0' * 64}, {'total_rows': True},
            {'table_counts': list(result.table_counts)}, {'total_rows': 99},
            {'table_counts': tuple((name, 4) for name, _, _ in TABLES)},
            {'payload': canonical(malformed), 'content_hash': sha256(canonical(malformed)).hexdigest()},
            {'captured_at': NOW.replace(tzinfo=None)}, {'finished_at': NOW - timedelta(seconds=1)},
            {'elapsed_seconds': float('nan')}, {'elapsed_seconds': True}, {'elapsed_seconds': 5.1},
        ):
            with self.subTest(changes=tuple(changes)), self.assertRaises(ValueError):
                replace(result, **changes)
        with self.assertRaises(FrozenInstanceError):
            result.payload = b'other'

    def seed(self, narrative='seed'):
        request = make_request(narrative=narrative)
        binding = make_binding(request=request)
        self.store.admit(binding, request, make_checkpoint(binding=binding))

    def assert_restored(self, prior):
        self.assertFalse(self.store._db.in_transaction)
        self.assertIsNone(self.store._execution)
        self.assertEqual(self.store._db.execute('PRAGMA busy_timeout').fetchone()[0], prior)
        if isinstance(self.store._db, ForwardConnection):
            self.assertFalse(self.store._db.handler_active)
        self.assertIsNotNone(self.store.checkpoint('C1'))
        self.store.consume('C1', 'tool_calls', 1, NOW)

    def test_exact_encoded_rows_payload_and_rows_boundaries_include_escaping(self):
        self.seed(('a' * 4095 + '😀Кот\x00\\"\b\f\n\r\t' + ''.join(chr(i) for i in range(32))) * 2)
        expected = self.beforeimage()
        row_size = max(len(canonical(row)) for table in expected['tables'] for row in table['rows'])
        row_size = max(row_size, *(len(canonical(row)) for row in expected['schema']))
        row_count = sum(len(table['rows']) for table in expected['tables'])
        payload_size = len(canonical(expected))
        limits = self.module().RetainedStateLimitsV1(max_rows=row_count, max_row_bytes=row_size, max_payload_bytes=payload_size)
        self.store._db = ForwardConnection(self.store._db)
        self.assertEqual(self.capture(limits=limits).payload, canonical(expected))
        self.assertTrue(self.store._db.chunks)
        self.assertLessEqual(max(self.store._db.chunks), 4096)
        for field in ('max_rows', 'max_row_bytes', 'max_payload_bytes'):
            with self.subTest(field=field):
                prior = self.store._db.execute('PRAGMA busy_timeout').fetchone()[0]
                before = self.beforeimage()
                limits = self.module().RetainedStateLimitsV1(
                    max_rows=sum(len(table['rows']) for table in before['tables']),
                    max_row_bytes=max(len(canonical(row)) for table in before['tables'] for row in table['rows']),
                    max_payload_bytes=len(canonical(before)))
                with self.assertRaisesRegex(JournalFailure, '^retained_state_limit$'):
                    self.capture(limits=replace(limits, **{field: getattr(limits, field) - 1}))
                self.assertEqual(self.beforeimage(), before)
                self.assert_restored(prior)

    def test_oversized_scalar_denied_before_full_schema_or_model_materialization(self):
        self.seed()
        with sqlite3.connect(self.path) as db:
            original = db.execute('SELECT request_json FROM original_requests').fetchone()[0]
            db.execute('UPDATE original_requests SET request_json=?', ('secret-' + 'x' * 262144,))
        before = self.beforeimage()
        observed = ForwardConnection(self.store._db)
        self.store._db = observed
        with self.assertRaisesRegex(JournalFailure, '^retained_state_limit$') as caught:
            self.capture()
        self.assertIsNone(caught.exception.__cause__)
        self.assertFalse(any(sql.startswith('SELECT type,name,sql') and 'WHERE rowid=?' not in sql for sql in observed.sql))
        self.assertFalse(any(sql == 'PRAGMA integrity_check' for sql in observed.sql))
        self.assertFalse(any(sql.startswith('SELECT case_id,generation,request_json') for sql in observed.sql))
        self.assertEqual(self.beforeimage(), before)
        with sqlite3.connect(self.path) as db:
            db.execute('UPDATE original_requests SET request_json=?', (original,))
        self.assert_restored(10000)

    def test_actual_wal_writer_commit_between_table_reads_returns_wholly_before_then_after(self):
        self.seed()
        before = self.beforeimage()
        ready, write, committed = Event(), Event(), Event()
        def writer():
            other = CaseStore(self.path)
            try:
                ready.set()
                if not write.wait(2):
                    raise AssertionError('writer was not signalled')
                other.consume('C1', 'tool_calls', 1, NOW)
                request = make_request(case_id='C2')
                binding = make_binding(request=request)
                other.admit(binding, request, make_checkpoint(binding=binding))
                committed.set()
            finally:
                other.close()
        fired = False
        def after(sql):
            nonlocal fired
            if 'FROM admission_entries' in sql and not fired:
                fired = True
                self.assertTrue(self.store._db.in_transaction)
                write.set()
                self.assertTrue(committed.wait(2), 'actual WAL writer failed to commit within reader snapshot')
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(writer)
            self.assertTrue(ready.wait(2))
            self.store._db = ForwardConnection(self.store._db, after)
            result = self.capture()
            future.result(timeout=2)
        self.assertTrue(fired)
        self.assertEqual(result.payload, canonical(before))
        after_image = self.beforeimage()
        self.assertNotEqual(before, after_image)
        self.assertEqual(self.capture().payload, canonical(after_image))

    def test_real_sqlite_step_ceiling_and_storage_failure_restore_after_expiry(self):
        self.seed()
        observed = ForwardConnection(self.store._db)
        self.store._db = observed
        self.capture()
        self.assertTrue(observed.intervals, 'capture must install real SQLite progress handler')
        self.assertTrue(all(1 <= interval <= 1000 for interval in observed.intervals))
        cold_count = observed.steps
        self.capture()
        count = observed.steps
        print('REAL_SQLITE_CALLBACK_COUNTS cold=' + str(cold_count) + ' warmed=' + str(count))
        limits = self.module().RetainedStateLimitsV1(max_sqlite_steps=count)
        self.capture(limits=limits)
        self.assertEqual(observed.steps, count)
        before = self.beforeimage()
        with self.assertRaisesRegex(JournalFailure, '^retained_state_limit$'):
            self.capture(limits=replace(limits, max_sqlite_steps=count - 1))
        self.assertEqual(self.beforeimage(), before)
        self.assert_restored(10000)
        before = self.beforeimage()
        with self.assertRaisesRegex(JournalFailure, '^retained_state_limit$'):
            self.capture(limits=replace(limits, max_sqlite_steps=1))
        self.assertEqual(self.beforeimage(), before)
        self.assert_restored(10000)
        def fail(sql):
            if 'FROM cases' in sql:
                self.clock.advance(5)
                raise sqlite3.OperationalError('private-secret /unsafe/path SQL')
        observed.after = fail
        before = self.beforeimage()
        with self.assertRaisesRegex(JournalFailure, '^retained_state_storage$') as caught:
            self.capture()
        self.assertIsNone(caught.exception.__cause__)
        observed.after = None
        self.assertEqual(self.beforeimage(), before)
        self.assert_restored(10000)

    def test_original_time_scope_and_regression_deny_without_renewal(self):
        self.seed()
        before = self.beforeimage()
        for duration in (0, 6):
            execution = ExecutionContext.capture(self.clock.utc + timedelta(seconds=duration), self.clock)
            with self.subTest(duration=duration), self.assertRaisesRegex(JournalFailure, '^retained_state_(timeout|scope)$'):
                self.capture(execution=execution)
        original = ExecutionContext.capture(self.clock.utc + timedelta(seconds=5), self.clock)
        self.clock.advance(2)
        result = self.capture(execution=original)
        self.assertEqual(result.captured_at, original.captured_at)
        self.assertEqual(result.elapsed_seconds, 2.0)
        self.clock.advance(3)
        with self.assertRaisesRegex(JournalFailure, '^retained_state_timeout$'):
            self.capture(execution=original)
        self.assertEqual(self.beforeimage(), before)
        for attribute, value in (('tick', original.captured_monotonic - 1), ('utc', original.captured_at - timedelta(seconds=1)), ('tick', float('nan'))):
            self.clock = Clock()
            execution = ExecutionContext.capture(NOW + timedelta(seconds=5), self.clock)
            setattr(self.clock, attribute, value)
            with self.subTest(attribute=attribute), self.assertRaisesRegex(JournalFailure, '^retained_state_invalid$'):
                self.capture(execution=execution)
        self.clock = Clock()
        execution = ExecutionContext.capture(NOW + timedelta(seconds=5), self.clock)
        with self.store.execution_scope(execution, self.clock):
            with self.assertRaisesRegex(JournalFailure, '^retained_state_scope$'):
                self.capture()
        self.store._db.execute('BEGIN')
        with self.assertRaisesRegex(JournalFailure, '^retained_state_scope$'):
            self.capture()
        self.assertTrue(self.store._db.in_transaction)
        self.store._db.execute('ROLLBACK')
        with ThreadPoolExecutor(max_workers=1) as pool:
            with self.assertRaisesRegex(JournalFailure, '^retained_state_scope$'):
                pool.submit(self.capture).result()
        self.assert_restored(10000)

    def test_row_count_stops_at_one_detection_row_before_validation(self):
        self.seed()
        observed = ForwardConnection(self.store._db)
        self.store._db = observed
        before = self.beforeimage()
        with self.assertRaisesRegex(JournalFailure, '^retained_state_limit$'):
            self.capture(limits=self.module().RetainedStateLimitsV1(max_rows=1))
        self.assertEqual(observed.metadata_rows, 2)
        self.assertNotIn('PRAGMA integrity_check', observed.sql)
        self.assertEqual(self.beforeimage(), before)
        self.assert_restored(10000)

    def test_bad_clock_and_forged_integer_payload_deny_finite_invalid(self):
        self.seed()
        result = self.capture()
        malformed = json.loads(result.payload)
        cases = next(table for table in malformed['tables'] if table['name'] == 'cases')
        cases['rows'][0][2] = 1 << 80
        payload = canonical(malformed)
        with self.assertRaises(ValueError):
            replace(result, payload=payload, content_hash=sha256(payload).hexdigest())
        execution = ExecutionContext.capture(NOW + timedelta(seconds=5), self.clock)
        for bad in (object(), type('BadClock', (), {'now': lambda self: (_ for _ in ()).throw(RuntimeError('secret clock payload')), 'monotonic': lambda self: 100.0})()):
            with self.subTest(clock=type(bad).__name__):
                with self.assertRaises(Exception) as caught:
                    self.store.capture_retained_state(execution=execution, clock=bad)
                self.assertIs(type(caught.exception), JournalFailure)
                self.assertEqual(str(caught.exception), 'retained_state_invalid')
                self.assertIsNone(caught.exception.__cause__)
        self.assert_restored(10000)

    def test_corrupt_schema_json_orphans_and_scalar_types_deny_without_repair(self):
        self.seed()
        with sqlite3.connect(self.path) as db:
            original = db.execute('SELECT request_json FROM original_requests').fetchone()[0]
        for raw in ('{malformed-secret', '{"duplicate":1,"duplicate":2}', '[' * 1500 + '0' + ']' * 1500, '{"value":NaN}', sqlite3.Binary(b'secret-binary')):
            with self.subTest(raw_type=type(raw).__name__):
                with sqlite3.connect(self.path) as db:
                    db.execute('UPDATE original_requests SET request_json=?', (raw,))
                before = self.beforeimage()
                with self.assertRaisesRegex(JournalFailure, '^retained_state_invalid$') as caught:
                    self.capture()
                self.assertIsNone(caught.exception.__cause__)
                self.assertEqual(self.beforeimage(), before)
                with sqlite3.connect(self.path) as db:
                    db.execute('UPDATE original_requests SET request_json=?', (original,))
                self.assert_restored(10000)
        for bad_sql, restore_sql in (
            ('CREATE TABLE extra_secret(value TEXT)', 'DROP TABLE extra_secret'),
            ('ALTER TABLE cases ADD COLUMN extra_secret TEXT', 'ALTER TABLE cases DROP COLUMN extra_secret'),
            ('UPDATE schema_meta SET version=2', 'UPDATE schema_meta SET version=1'),
            ('DELETE FROM schema_meta', 'INSERT INTO schema_meta VALUES(1)'),
            ('UPDATE cases SET revision=1.5', 'UPDATE cases SET revision=0'),
            ("UPDATE requests SET request_id='secret-foreign-index'", "UPDATE requests SET request_id='REQ1'"),
            ("INSERT INTO original_requests VALUES('ORPHAN','G1','{}')", "DELETE FROM original_requests WHERE case_id='ORPHAN'"),
        ):
            with self.subTest(sql=bad_sql.split()[0]):
                with sqlite3.connect(self.path) as db:
                    db.execute(bad_sql)
                before = self.beforeimage()
                with self.assertRaisesRegex(JournalFailure, '^retained_state_invalid$'):
                    self.capture()
                self.assertEqual(self.beforeimage(), before)
                with sqlite3.connect(self.path) as db:
                    db.execute(restore_sql)
                self.assert_restored(10000)

    def test_expiry_at_preflight_validation_encoding_commit_and_late_regression_restores(self):
        self.seed()
        for phase in ('schema', 'preflight', 'validation', 'encoding', 'commit', 'regression'):
            with self.subTest(phase=phase):
                self.clock = Clock()
                fired = False
                def after(sql):
                    nonlocal fired
                    hit = {
                        'schema': 'FROM sqlite_master' in sql,
                        'preflight': sql.startswith('SELECT rowid,') and 'FROM cases' in sql,
                        'validation': sql == 'PRAGMA integrity_check',
                        'encoding': sql.startswith('SELECT question_id,case_id,generation,wait_json FROM waits'),
                        'commit': sql == 'COMMIT',
                        'regression': sql.startswith('SELECT rowid,') and 'FROM cases' in sql,
                    }[phase]
                    if hit and not fired:
                        fired = True
                        if phase == 'regression':
                            self.clock.tick -= .1
                        else:
                            self.clock.advance(5)
                actual = self.store._db.actual if isinstance(self.store._db, ForwardConnection) else self.store._db
                self.store._db = ForwardConnection(actual, after)
                before = self.beforeimage()
                reason = 'invalid' if phase == 'regression' else 'timeout'
                with self.assertRaisesRegex(JournalFailure, '^retained_state_' + reason + '$'):
                    self.capture()
                self.assertTrue(fired)
                self.store._db.after = None
                self.assertEqual(self.beforeimage(), before)
                self.assert_restored(10000)

    def test_reopen_stable_hash_public_mutation_changes_data_and_closed_scope_denies(self):
        self.seed()
        first = self.capture()
        self.store.close()
        with self.assertRaisesRegex(JournalFailure, '^retained_state_scope$'):
            self.capture()
        self.clock.advance(1)
        self.store = CaseStore(self.path)
        second = self.capture()
        self.assertEqual((first.payload, first.content_hash, first.schema_hash), (second.payload, second.content_hash, second.schema_hash))
        self.assertNotEqual(first.captured_at, second.captured_at)
        self.store.set_stop('C1', 'G1')
        third = self.capture()
        self.assertNotEqual(third.content_hash, second.content_hash)
        self.assertEqual(third.payload, canonical(self.beforeimage()))

    def test_registered_ownership_audit_retains_originals_and_all_debt(self):
        from ownership_support import Harness
        from proofkey.ownership import OwnershipService
        with tempfile.TemporaryDirectory() as folder:
            h = Harness(folder)
            self.addCleanup(h.store.close)
            OwnershipService(h.profile, h.bundle, h.store, h.clock, gateway=h.gateway).transfer_result(h.transfer(), h.auth)
            old_store, old_path = self.store, self.path
            try:
                self.store, self.path = h.store, h.journal_path
                before = self.beforeimage()
                result = self.capture()
                self.assertEqual(result.payload, canonical(before))
                self.assertEqual(self.beforeimage(), before)
                audit_rows = next(table for table in before['tables'] if table['name'] == 'audit')['rows']
                self.assertTrue(any(json.loads(row[2]).get('ownership_event') for row in audit_rows))
                self.assertTrue(next(table for table in before['tables'] if table['name'] == 'transfers')['rows'])
            finally:
                self.store, self.path = old_store, old_path

    def test_actual_sql_text_nul_and_split_utf8_preserved_at_exact_row_payload_ceiling(self):
        # A checkpoint-free row is permitted by the fixed schema and existing complete validator.
        text = 'a' * 4095 + '😀\x00Кот' + ''.join(chr(i) for i in range(32)) + '\\"'
        with sqlite3.connect(self.path) as db:
            db.execute('INSERT INTO cases VALUES(?,NULL,?)', (text, (1 << 63) - 1))
        before = self.beforeimage()
        row = next(table for table in before['tables'] if table['name'] == 'cases')['rows'][0]
        self.assertIn('\x00', row[0])
        self.assertEqual(row[2], (1 << 63) - 1)
        self.store._db = ForwardConnection(self.store._db)
        limits = self.module().RetainedStateLimitsV1(max_rows=2, max_row_bytes=len(canonical(row)), max_payload_bytes=len(canonical(before)))
        self.assertEqual(self.capture(limits=limits).payload, canonical(before))
        self.assertIn(4096, self.store._db.chunks)
        for field in ('max_row_bytes', 'max_payload_bytes'):
            with self.subTest(field=field), self.assertRaisesRegex(JournalFailure, '^retained_state_limit$'):
                self.capture(limits=replace(limits, **{field: getattr(limits, field) - 1}))
        self.assertEqual(self.beforeimage(), before)
        self.assertFalse(self.store._db.in_transaction)
        self.assertFalse(self.store._db.handler_active)
        self.store.close()
        self.store = CaseStore(self.path)
        self.assertEqual(self.capture().payload, canonical(before))

    def test_snapshot_rejects_rehashed_foreign_ddl_and_foreign_columns(self):
        result = self.capture()
        print('ACTUAL_CANONICAL_SCHEMA_SHA256 ' + result.schema_hash)
        for part in ('schema', 'columns'):
            changed = json.loads(result.payload)
            if part == 'schema':
                changed['schema'][0][2] += ' /* foreign-secret-DDL */'
            else:
                changed['tables'][0]['columns'][0] = 'foreign-column'
            payload = canonical(changed)
            with self.subTest(part=part), self.assertRaises(ValueError):
                replace(result, payload=payload, schema_hash=sha256(canonical(changed['schema'])).hexdigest(), content_hash=sha256(payload).hexdigest())

    def test_cached_extra_column_cannot_hide_behind_restored_schema_sql(self):
        self.seed()
        db = self.store._db
        original_sql = db.execute("SELECT sql FROM sqlite_master WHERE name='cases'").fetchone()[0]
        db.execute('ALTER TABLE cases ADD COLUMN hidden_retained_secret TEXT')
        extended_sql = db.execute("SELECT sql FROM sqlite_master WHERE name='cases'").fetchone()[0]
        try:
            db.execute('PRAGMA writable_schema=ON')
            db.execute("UPDATE sqlite_master SET sql=? WHERE name='cases'", (original_sql,))
            db.execute('PRAGMA writable_schema=OFF')
            self.assertEqual(len(db.execute('PRAGMA table_info(cases)').fetchall()), 4)
            with self.assertRaisesRegex(JournalFailure, '^retained_state_invalid$'):
                self.capture()
        finally:
            db.execute('PRAGMA writable_schema=ON')
            db.execute("UPDATE sqlite_master SET sql=? WHERE name='cases'", (extended_sql,))
            db.execute('PRAGMA writable_schema=OFF')
            db.execute('ALTER TABLE cases DROP COLUMN hidden_retained_secret')
        self.assert_restored(10000)


if __name__ == '__main__':
    unittest.main()
