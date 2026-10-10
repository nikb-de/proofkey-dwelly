from contextlib import closing
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import sqlite3
import tempfile
import unittest
from dataclasses import replace
from datetime import tzinfo
import os
import threading

from proofkey.adapters.world import SimulatedWorld
from proofkey.execution import ExecutionContext
from proofkey.profiles import load_profile
from proofkey.retained_state import RetainedStateLimitsV1
from proofkey.source_retained_state import (
    SourceRetainedStateFailure, SourceRetainedStateSnapshotV1,
)

ROOT = Path(__file__).resolve().parents[1]
TABLES = ('effects', 'facts', 'final_rejections', 'metadata',
          'pressure', 'reservations', 'scopes')

class Clock:
    def __init__(self):
        self.utc = datetime(2026, 10, 8, 10, tzinfo=timezone.utc)
        self.tick = 100.0
    def now(self):
        return self.utc
    def monotonic(self):
        return self.tick

def tag(value):
    if value is None:
        return ['null']
    if type(value) is str:
        return ['text', value]
    if type(value) is int:
        return ['integer', str(value)]
    if type(value) is float and math.isfinite(value):
        return ['real', value.hex()]
    raise AssertionError('Unexpected fixture SQL value')

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')

def stored(path):
    # Independent test-only logical inventory; never the product encoder.
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
        schema = sorted([list(row) for row in db.execute(
            'SELECT type,name,tbl_name,sql FROM sqlite_master')])
        tables = []
        for name in TABLES:  # fixed trusted test identifiers
            columns = [row[1] for row in db.execute('PRAGMA table_info(' + name + ')')]
            rows = [[tag(value) for value in row]
                    for row in db.execute('SELECT * FROM ' + name)]
            tables.append({'name': name, 'columns': columns,
                           'rows': sorted(rows, key=canonical)})
        return {'schema': schema, 'tables': tables}

class SourceRetainedStateTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / 'world.sqlite'
        self.clock = Clock()
        self.profile = load_profile('flat-v1.4')
        self.fixture = ROOT / 'fixtures/development/ownership-world-v1.json'
        self.raw = json.loads(self.fixture.read_text(encoding='utf-8'))
        self.world = SimulatedWorld(self.path, self.fixture,
                                    profile=self.profile, clock=self.clock)
        self.execution = ExecutionContext.capture(
            self.clock.now() + timedelta(seconds=30), self.clock)

    def test_complete_lossless_real_null_ties_and_no_mutation(self):
        account = self.profile.capabilities['reschedule'].shared_limits.account_id
        value = math.nextafter(0.1, 1.0)
        readers = '{ "U1": "synthetic-proof", "OP1": "synthetic-operator-proof", "OP2": "synthetic-target-proof" }'
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('INSERT INTO pressure VALUES(?,?,?,?,?)',
                       (account, 3, 2, '[ 0.1 ]', value))
            db.executemany('INSERT INTO reservations VALUES(?,?,?)',
                           [(None, account, value), (None, account, value),
                            (None, account, 0.1)])
            db.execute('UPDATE scopes SET readers=? WHERE case_id=? AND object_id=?',
                       (readers, 'C1', 'O1'))
            db.execute('UPDATE facts SET value=? WHERE identity=?',
                       ('  "safe"  ', 'delivery.risk'))
        before = stored(self.path)
        image = self.world.capture_retained_state(
            execution=self.execution, clock=self.clock)
        self.assertIsInstance(image, SourceRetainedStateSnapshotV1)
        body = json.loads(image.payload)
        self.assertEqual(body['domain'], 'synthetic-world-retained-state-v1')
        self.assertEqual(body['format_version'], 1)
        self.assertEqual(body['context']['profile'], self.profile.model_dump(mode='json'))
        self.assertEqual(body['context']['fixture'], self.raw)
        self.assertEqual(body['context']['as_of'], self.raw['as_of'])
        self.assertEqual(body['schema'], before['schema'])
        self.assertEqual(body['tables'], before['tables'])
        self.assertEqual(image.content_hash, sha256(image.payload).hexdigest())
        self.assertEqual(image.schema_hash, sha256(canonical(body['schema'])).hexdigest())
        tables = {table['name']: table for table in body['tables']}
        ties = tables['reservations']['rows']
        self.assertEqual(len(ties), 3)
        self.assertEqual(ties.count([['null'], ['text', account], ['real', value.hex()]]), 2)
        self.assertIn(['real', value.hex()], tables['pressure']['rows'][0])
        self.assertEqual(len(body['schema']), 14)
        self.assertEqual(sum(row[0] == 'index' and row[3] is None
                             for row in body['schema']), 7)
        self.assertEqual(image.table_counts,
                         tuple((table['name'], len(table['rows'])) for table in body['tables']))
        self.assertEqual(image.total_rows, sum(count for _, count in image.table_counts))
        self.assertEqual(self.world.calls, ())
        self.assertEqual(stored(self.path), before)
        again = self.world.capture_retained_state(
            execution=self.execution, clock=self.clock)
        self.assertEqual(again.payload, image.payload)

    def test_every_table_semantic_corruption_is_rejected_without_repair(self):
        corruptions = (
            ("UPDATE metadata SET value='wrong' WHERE key='fixture'", ()),
            ("UPDATE scopes SET readers='[]'", ()),
            ("UPDATE scopes SET readers='{\"U1\":\" \"}'", ()),
            ("UPDATE scopes SET principal_id=NULL", ()),
            ("UPDATE facts SET revision=NULL WHERE identity='delivery.risk'", ()),
            ("UPDATE facts SET identity='unqualified' WHERE identity='delivery.risk'", ()),
            ("UPDATE facts SET value='NaN' WHERE identity='delivery.risk'", ()),
            ("UPDATE facts SET value='{}' WHERE identity='case.binding'", ()),
            ("UPDATE facts SET value='{}' WHERE identity='operator.ownership_grant'", ()),
            ("INSERT INTO effects(account_id) VALUES('unknown')", ()),
            ("INSERT INTO final_rejections(account_id) VALUES('unknown')", ()),
            ("INSERT INTO pressure VALUES(NULL,1,2,'[true]',0.0)", ()),
            ("INSERT INTO pressure VALUES(NULL,-1,2,'[]',0.0)", ()),
            ("INSERT INTO reservations VALUES(NULL,NULL,NULL)", ()),
        )
        for index, (sql, arguments) in enumerate(corruptions):
            with self.subTest(sql=sql):
                path = self.path.with_name('corrupt-' + str(index) + '.sqlite')
                world = SimulatedWorld(path, self.fixture, profile=self.profile, clock=self.clock)
                with closing(sqlite3.connect(path)) as db, db:
                    db.execute(sql, arguments)
                before = stored(path)
                with self.assertRaises(SourceRetainedStateFailure) as failure:
                    world.capture_retained_state(execution=self.execution, clock=self.clock)
                self.assertEqual(failure.exception.code, 'invalid')
                self.assertEqual(str(failure.exception), 'invalid')
                self.assertEqual(stored(path), before)

    def test_opaque_revoked_expired_state_is_retained_not_repaired(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.executemany('INSERT INTO metadata VALUES(?,?)',
                           [(None, '{broken'), (None, '{broken'), ('', ' opaque '), ('future', 'NaN')])
            db.execute("UPDATE scopes SET readers='{}'")
            db.execute("UPDATE facts SET value='\"revoked\"' WHERE identity='customer.consent'")
            db.execute("INSERT INTO facts VALUES('orphan','O2','extension.unknown','null','old','e')")
            db.executemany('INSERT INTO pressure VALUES(?,?,?,?,?)',
                           [(None, 0, 99, '[ -10, 2, 2 ]', -1.0)] * 2)
            db.executemany('INSERT INTO reservations VALUES(?,?,?)', [(None, None, -1.0)] * 2)
        before = stored(self.path)
        image = self.world.capture_retained_state(execution=self.execution, clock=self.clock)
        self.assertEqual(json.loads(image.payload)['tables'], before['tables'])
        self.assertEqual(stored(self.path), before)

    def test_pure_snapshot_rejects_rehashed_invalid_context_and_semantics(self):
        image = self.world.capture_retained_state(execution=self.execution, clock=self.clock)
        mutations = ('profile', 'fixture_version', 'metadata', 'readers')
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                body = json.loads(image.payload)
                if mutation == 'profile':
                    body['context']['profile'] = {}
                elif mutation == 'fixture_version':
                    body['context']['fixture']['version'] = 'unknown'
                    body['context']['fixture_hash'] = sha256(canonical(body['context']['fixture'])).hexdigest()
                else:
                    name = 'metadata' if mutation == 'metadata' else 'scopes'
                    table = next(item for item in body['tables'] if item['name'] == name)
                    if mutation == 'metadata':
                        row = next(row for row in table['rows'] if row[0] == ['text', 'fixture'])
                        row[1] = ['text', 'wrong']
                    else:
                        table['rows'][0][3] = ['text', '[]']
                    table['rows'].sort(key=canonical)
                payload = canonical(body)
                with self.assertRaises(ValueError):
                    replace(image, payload=payload, content_hash=sha256(payload).hexdigest())

    def test_corrupt_semantic_json_and_tight_row_limit_fail_without_mutation(self):
        pristine = stored(self.path)
        with self.assertRaises(SourceRetainedStateFailure) as limited:
            self.world.capture_retained_state(execution=self.execution, clock=self.clock,
                                              limits=RetainedStateLimitsV1(max_rows=1))
        self.assertEqual(limited.exception.code, 'limit')
        self.assertEqual(stored(self.path), pristine)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('UPDATE facts SET value=? WHERE identity=?',
                       ('{"duplicate":1,"duplicate":2}', 'delivery.risk'))
        corrupt = stored(self.path)
        with self.assertRaises(SourceRetainedStateFailure) as invalid:
            self.world.capture_retained_state(execution=self.execution, clock=self.clock)
        self.assertEqual(invalid.exception.code, 'invalid')
        self.assertEqual(stored(self.path), corrupt)
        self.assertEqual(self.world.calls, ())

    def test_original_anchor_timeout_and_two_clock_reversal_are_closed(self):
        for utc_delta, mono_delta, expected in ((6, 0, 'timeout'), (0, 6, 'timeout'),
                                                (-1, 0, 'invalid'), (0, -1, 'invalid')):
            with self.subTest(utc=utc_delta, monotonic=mono_delta):
                clock = Clock()
                clock.utc += timedelta(seconds=utc_delta)
                clock.tick += mono_delta
                with self.assertRaises(SourceRetainedStateFailure) as failure:
                    self.world.capture_retained_state(execution=self.execution, clock=clock)
                self.assertEqual(failure.exception.code, expected)
        clock = Clock()
        clock.utc += timedelta(seconds=4)
        clock.tick += 4
        image = self.world.capture_retained_state(execution=self.execution, clock=clock)
        self.assertEqual(image.captured_at, self.execution.captured_at)
        self.assertEqual(image.elapsed_seconds, 4.0)

    def test_exact_row_and_payload_limits_and_vm_failure_leave_source_unchanged(self):
        before = stored(self.path)
        baseline = self.world.capture_retained_state(execution=self.execution, clock=self.clock)
        row_bytes = max(len(canonical(row)) for table in before['tables'] for row in table['rows'])
        limits = RetainedStateLimitsV1(max_rows=baseline.total_rows, max_row_bytes=row_bytes,
                                      max_payload_bytes=len(baseline.payload))
        self.assertEqual(self.world.capture_retained_state(execution=self.execution, clock=self.clock,
                                                         limits=limits).payload, baseline.payload)
        for limited in (replace(limits, max_rows=limits.max_rows - 1),
                        replace(limits, max_row_bytes=row_bytes - 1),
                        replace(limits, max_payload_bytes=len(baseline.payload) - 1),
                        RetainedStateLimitsV1(max_sqlite_steps=1)):
            with self.subTest(limited=limited):
                with self.assertRaises(SourceRetainedStateFailure) as failure:
                    self.world.capture_retained_state(execution=self.execution, clock=self.clock, limits=limited)
                self.assertEqual(failure.exception.code, 'limit')
                self.assertEqual(stored(self.path), before)

    def test_every_table_schema_change_is_rejected(self):
        changes = ['ALTER TABLE ' + name + ' ADD COLUMN extra TEXT' for name in TABLES]
        changes += ['CREATE TABLE extra(value TEXT)', 'CREATE INDEX extra ON facts(identity)',
                    'CREATE VIEW extra AS SELECT * FROM facts',
                    'CREATE TRIGGER extra AFTER INSERT ON metadata BEGIN SELECT 1; END',
                    'DROP TABLE reservations']
        for index, sql in enumerate(changes):
            with self.subTest(sql=sql):
                path = self.path.with_name('schema-' + str(index) + '.sqlite')
                world = SimulatedWorld(path, self.fixture, profile=self.profile, clock=self.clock)
                with closing(sqlite3.connect(path)) as db, db:
                    db.execute(sql)
                with self.assertRaises(SourceRetainedStateFailure) as failure:
                    world.capture_retained_state(execution=self.execution, clock=self.clock)
                self.assertEqual(failure.exception.code, 'invalid')

    def test_later_huge_cell_preflight_precedes_corrupt_original_model(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("INSERT INTO metadata VALUES('ownership_original:corrupt','{broken')")
            db.execute('INSERT INTO reservations VALUES(?,?,?)', ('x' * 262145, None, 0.0))
        before = stored(self.path)
        with self.assertRaises(SourceRetainedStateFailure) as failure:
            self.world.capture_retained_state(execution=self.execution, clock=self.clock)
        self.assertEqual(failure.exception.code, 'limit')
        self.assertEqual(stored(self.path), before)

    def test_unicode_nul_escaped_byte_limits_are_exact(self):
        text = '😀\x00"\\\n' * 800
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('INSERT INTO metadata VALUES(?,?)', ('opaque', text))
        expected_size = max(len(canonical(row)) for table in stored(self.path)['tables'] for row in table['rows'])
        self.world.capture_retained_state(execution=self.execution, clock=self.clock,
                                         limits=RetainedStateLimitsV1(max_row_bytes=expected_size))
        with self.assertRaises(SourceRetainedStateFailure) as failure:
            self.world.capture_retained_state(execution=self.execution, clock=self.clock,
                limits=RetainedStateLimitsV1(max_row_bytes=expected_size - 1))
        self.assertEqual(failure.exception.code, 'limit')

    def test_missing_replaced_and_symlink_files_are_not_created_or_followed(self):
        saved = self.path.with_name('saved.sqlite')
        self.path.rename(saved)
        with self.assertRaises(SourceRetainedStateFailure) as failure:
            self.world.capture_retained_state(execution=self.execution, clock=self.clock)
        self.assertEqual(failure.exception.code, 'storage')
        self.assertFalse(self.path.exists())
        self.path.symlink_to(saved)
        with self.assertRaises(SourceRetainedStateFailure):
            self.world.capture_retained_state(execution=self.execution, clock=self.clock)
        self.path.unlink()
        replacement = SimulatedWorld(self.path, self.fixture, profile=self.profile, clock=self.clock)
        with self.assertRaises(SourceRetainedStateFailure):
            self.world.capture_retained_state(execution=self.execution, clock=self.clock)
        replacement.capture_retained_state(execution=self.execution, clock=self.clock)

    def test_creator_thread_and_reentrant_capture_are_rejected(self):
        failures = []
        def foreign():
            try:
                self.world.capture_retained_state(execution=self.execution, clock=self.clock)
            except SourceRetainedStateFailure as failure:
                failures.append(failure.code)
        thread = threading.Thread(target=foreign)
        thread.start()
        thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(failures, ['scope'])
        base = self.clock
        world, execution = self.world, self.execution
        class Reentrant:
            nested = False
            def now(inner):
                if not inner.nested:
                    inner.nested = True
                    try:
                        world.capture_retained_state(execution=execution, clock=base)
                    except SourceRetainedStateFailure as failure:
                        failures.append(failure.code)
                return base.now()
            def monotonic(inner):
                return base.monotonic()
        self.world.capture_retained_state(execution=self.execution, clock=Reentrant())
        self.assertEqual(failures, ['scope', 'scope'])

    def test_busy_rollback_database_fails_and_releases_capture_guard(self):
        with closing(sqlite3.connect(self.path, timeout=0)) as writer:
            writer.execute('BEGIN EXCLUSIVE')
            with self.assertRaises(SourceRetainedStateFailure) as failure:
                self.world.capture_retained_state(execution=self.execution, clock=self.clock)
            self.assertEqual(failure.exception.code, 'storage')
            writer.rollback()
        self.world.capture_retained_state(execution=self.execution, clock=self.clock)

    def test_pure_projection_numeric_aliases_and_mutable_timezone_detach(self):
        image = self.world.capture_retained_state(execution=self.execution, clock=self.clock)
        for patch in ({'format_version': True}, {'total_rows': True}, {'elapsed_seconds': float('nan')},
                      {'payload': bytearray(image.payload)}, {'table_counts': list(image.table_counts)},
                      {'finished_at': image.finished_at + timedelta(seconds=6)}):
            with self.subTest(patch=tuple(patch)):
                with self.assertRaises(ValueError):
                    replace(image, **patch)
        class MutableZone(tzinfo):
            offset = timedelta(hours=1)
            def utcoffset(self, dt):
                return self.offset
            def dst(self, dt):
                return timedelta(0)
        zone = MutableZone()
        moment = datetime(2026, 10, 8, 11, tzinfo=zone)
        detached = replace(image, captured_at=moment, finished_at=moment)
        zone.offset = timedelta(hours=2)
        self.assertEqual(detached.captured_at, image.captured_at)
        self.assertIs(detached.captured_at.tzinfo, timezone.utc)
        self.assertIs(detached.finished_at.tzinfo, timezone.utc)

    def test_pure_projection_preserves_distant_utc_microseconds(self):
        image = self.world.capture_retained_state(execution=self.execution, clock=self.clock)
        cases = (
            (datetime(2500, 1, 1, 0, 0, 0, 123456, tzinfo=timezone.utc),
             datetime(2500, 1, 1, 0, 0, 0, 123456, tzinfo=timezone.utc)),
            (datetime(2500, 1, 1, 1, 0, 0, 123456,
                      tzinfo=timezone(timedelta(hours=1))),
             datetime(2500, 1, 1, 0, 0, 0, 123456, tzinfo=timezone.utc)),
            (datetime(9999, 12, 31, 23, 59, 59, 999999, tzinfo=timezone.utc),
             datetime(9999, 12, 31, 23, 59, 59, 999999, tzinfo=timezone.utc)),
        )
        for supplied, expected in cases:
            with self.subTest(supplied=supplied):
                try:
                    detached = replace(image, captured_at=supplied, finished_at=supplied)
                except ValueError as error:
                    self.fail('Lawful aware datetime was rejected: ' + str(error))
                self.assertEqual(detached.captured_at, expected)
                self.assertEqual(detached.finished_at, expected)
                self.assertIs(detached.captured_at.tzinfo, timezone.utc)
                self.assertIs(detached.finished_at.tzinfo, timezone.utc)

    def test_capture_preserves_distant_original_anchor_microseconds(self):
        expected = datetime(2500, 1, 1, 0, 0, 0, 123456, tzinfo=timezone.utc)
        self.clock.utc = expected
        execution = ExecutionContext.capture(expected + timedelta(seconds=30), self.clock)
        self.assertEqual(execution.captured_at, expected)
        image = self.world.capture_retained_state(execution=execution, clock=self.clock)
        self.assertEqual(image.captured_at, expected)
        self.assertEqual(image.finished_at, expected)

    def test_public_pending_accepted_rejected_history_and_inverse_joins(self):
        from test_ownership_source import synthetic_fixture, effect_for
        from support import make_auth
        for status in ('pending', 'accepted', 'rejected'):
            with self.subTest(status=status):
                raw = synthetic_fixture(self.profile, direct_accept=status == 'accepted')
                path = self.path.with_name(status + '.sqlite')
                world = SimulatedWorld(path, self.fixture, profile=self.profile, clock=self.clock,
                                       fixture_bytes=json.dumps(raw).encode())
                effect = effect_for(raw, self.profile, world.material_revisions())
                if status == 'rejected':
                    world.set_fault('transfer_owner', 'business_rejection')
                result = world.bundle().operator.transfer_owner(effect,
                    auth=make_auth(caller_id='OP1', proof_reference='synthetic-operator-proof'))
                self.assertEqual(result.status, 'rejected' if status == 'rejected' else 'acknowledged')
                before = stored(path)
                image = world.capture_retained_state(execution=self.execution, clock=self.clock)
                self.assertEqual(json.loads(image.payload)['tables'], before['tables'])
                metadata = next(table for table in json.loads(image.payload)['tables'] if table['name'] == 'metadata')
                originals = [json.loads(row[1][1]) for row in metadata['rows']
                             if row[0][0] == 'text' and row[0][1].startswith('ownership_original:')]
                self.assertEqual(len(originals), 1)
                self.assertEqual(originals[0]['receipt']['kind'], 'transfer_' + status + '_v1')
                self.assertEqual(stored(path), before)
                with closing(sqlite3.connect(path)) as db, db:
                    db.execute("DELETE FROM metadata WHERE key LIKE 'ownership_original:%'")
                with self.assertRaises(SourceRetainedStateFailure) as failure:
                    world.capture_retained_state(execution=self.execution, clock=self.clock)
                self.assertEqual(failure.exception.code, 'invalid')

    def test_registered_like_aliases_reject_but_legacy_extension_is_opaque(self):
        for index, key in enumerate(('ownershipXoriginal:alias', 'OWNERSHIP_ORIGINAL:alias')):
            with self.subTest(key=key):
                path = self.path.with_name('alias-' + str(index) + '.sqlite')
                world = SimulatedWorld(path, self.fixture, profile=self.profile, clock=self.clock)
                with closing(sqlite3.connect(path)) as db, db:
                    db.execute('INSERT INTO metadata VALUES(?,?)', (key, '{opaque'))
                with self.assertRaises(SourceRetainedStateFailure) as failure:
                    world.capture_retained_state(execution=self.execution, clock=self.clock)
                self.assertEqual(failure.exception.code, 'invalid')
        legacy = SimulatedWorld(self.path.with_name('legacy.sqlite'), ROOT / 'fixtures/development/world.json',
                                profile=load_profile('flat-v1'), clock=self.clock)
        path = self.path.with_name('legacy.sqlite')
        with closing(sqlite3.connect(path)) as db, db:
            db.execute("INSERT INTO metadata VALUES('ownershipXoriginal:alias','{opaque')")
        image = legacy.capture_retained_state(execution=self.execution, clock=self.clock)
        self.assertEqual(json.loads(image.payload)['tables'], stored(path)['tables'])

    def test_wal_writer_pair_is_one_old_snapshot_then_one_new_snapshot(self):
        # Only this test selects WAL; production capture never changes journal mode.
        with closing(sqlite3.connect(self.path)) as db, db:
            self.assertEqual(db.execute('PRAGMA journal_mode=WAL').fetchone()[0], 'wal')
            db.execute("INSERT INTO pressure VALUES('snapshot',1,1,'[]',0.0)")
        requested, committed = threading.Event(), threading.Event()
        errors = []
        def writer():
            try:
                if not requested.wait(2):
                    raise AssertionError('Snapshot did not reach the writer barrier')
                with closing(sqlite3.connect(self.path, timeout=1)) as db, db:
                    db.execute("UPDATE facts SET value='\"unsafe\"' WHERE identity='delivery.risk'")
                    db.execute("UPDATE pressure SET used=2 WHERE account_id='snapshot'")
            except BaseException as error:
                errors.append(error)
            finally:
                committed.set()
        thread = threading.Thread(target=writer)
        thread.start()
        base = self.clock
        class SnapshotClock:
            count = 0
            def now(inner):
                inner.count += 1
                if inner.count == 1000:
                    requested.set()
                    if not committed.wait(2):
                        raise AssertionError('WAL writer failed to commit')
                return base.now()
            def monotonic(inner):
                return base.monotonic()
        try:
            old = self.world.capture_retained_state(execution=self.execution, clock=SnapshotClock())
        finally:
            requested.set()
            thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        new = self.world.capture_retained_state(execution=self.execution, clock=self.clock)
        def pair(image):
            tables = {item['name']: item for item in json.loads(image.payload)['tables']}
            risk = next(row[3][1] for row in tables['facts']['rows'] if row[2] == ['text', 'delivery.risk'])
            used = next(row[1][1] for row in tables['pressure']['rows'] if row[0] == ['text', 'snapshot'])
            return risk, used
        self.assertEqual(pair(old), ('"safe"', '1'))
        self.assertEqual(pair(new), ('"unsafe"', '2'))

    def test_finished_time_uses_final_sample_and_invalid_clock_is_finite_failure(self):
        world = SimulatedWorld(self.path.with_name('time-legacy.sqlite'),
            ROOT / 'fixtures/development/world.json', profile=load_profile('flat-v1'), clock=self.clock)
        start = self.clock.utc
        class Advancing:
            n = 0
            last = start
            def now(inner):
                inner.n += 1
                inner.last = start + timedelta(microseconds=inner.n)
                return inner.last
            def monotonic(inner):
                return 100.0 + inner.n / 1000000
        clock = Advancing()
        image = world.capture_retained_state(execution=self.execution, clock=clock)
        self.assertEqual(image.finished_at, clock.last)
        self.assertEqual(image.elapsed_seconds, clock.monotonic() - self.execution.captured_monotonic)
        with self.assertRaises(SourceRetainedStateFailure) as failure:
            world.capture_retained_state(execution=self.execution, clock=object())
        self.assertEqual(failure.exception.code, 'invalid')

    def test_mutated_limit_cannot_upgrade_hard_ceiling(self):
        world = SimulatedWorld(self.path.with_name('limit-legacy.sqlite'),
            ROOT / 'fixtures/development/world.json', profile=load_profile('flat-v1'), clock=self.clock)
        world.capture_retained_state(execution=self.execution, clock=self.clock)
        limits = RetainedStateLimitsV1()
        object.__setattr__(limits, 'max_rows', 999999)
        with self.assertRaises(SourceRetainedStateFailure) as failure:
            world.capture_retained_state(execution=self.execution, clock=self.clock, limits=limits)
        self.assertEqual(failure.exception.code, 'invalid')

    def test_giant_unselected_cell_in_each_table_is_bounded_before_semantics(self):
        statements = (
            'INSERT INTO effects(observations) VALUES(?)',
            "UPDATE facts SET evidence_ref=? WHERE identity='delivery.risk'",
            'INSERT INTO final_rejections(created_at) VALUES(?)',
            "INSERT INTO metadata VALUES('opaque',?)",
            'INSERT INTO pressure(ticks) VALUES(?)',
            'INSERT INTO reservations(token) VALUES(?)',
            'UPDATE scopes SET readers=?',
        )
        for index, sql in enumerate(statements):
            with self.subTest(table=TABLES[index]):
                path = self.path.with_name('giant-' + str(index) + '.sqlite')
                world = SimulatedWorld(path, self.fixture, profile=self.profile, clock=self.clock)
                with closing(sqlite3.connect(path)) as db, db:
                    db.execute(sql, ('x' * 262145,))
                before = stored(path)
                with self.assertRaises(SourceRetainedStateFailure) as failure:
                    world.capture_retained_state(execution=self.execution, clock=self.clock)
                self.assertEqual(failure.exception.code, 'limit')
                self.assertEqual(stored(path), before)

    def test_context_stays_original_after_fixture_file_and_caller_profile_change(self):
        path = self.path.with_name('context.sqlite')
        fixture = self.path.with_name('original.json')
        fixture.write_text(json.dumps(self.raw))
        profile = load_profile('flat-v1.4')
        world = SimulatedWorld(path, fixture, profile=profile, clock=self.clock)
        fixture.write_text('{replaced')
        object.__setattr__(profile, 'profile_id', 'different-caller-profile')
        body = json.loads(world.capture_retained_state(execution=self.execution, clock=self.clock).payload)
        self.assertEqual(body['context']['fixture'], self.raw)
        self.assertEqual(body['context']['profile'], self.profile.model_dump(mode='json'))

    def test_blob_and_nonfinite_sql_values_are_invalid_not_coerced(self):
        for index, sql, arguments in (
                (0, "INSERT INTO metadata VALUES('blob',?)", (b'x',)),
                (1, 'INSERT INTO pressure VALUES(NULL,0,0,\'[]\',?)', (float('inf'),)),
                (2, 'INSERT INTO reservations VALUES(NULL,NULL,?)', (float('-inf'),))):
            with self.subTest(index=index):
                path = self.path.with_name('scalar-' + str(index) + '.sqlite')
                world = SimulatedWorld(path, self.fixture, profile=self.profile, clock=self.clock)
                with closing(sqlite3.connect(path)) as db, db:
                    db.execute(sql, arguments)
                with self.assertRaises(SourceRetainedStateFailure) as failure:
                    world.capture_retained_state(execution=self.execution, clock=self.clock)
                self.assertEqual(failure.exception.code, 'invalid')

    def test_tight_row_limit_does_not_treat_schema_sql_as_a_table_row(self):
        path = self.path.with_name('schema-row-limit.sqlite')
        world = SimulatedWorld(path, ROOT / 'fixtures/development/world.json',
                               profile=load_profile('flat-v1'), clock=self.clock)
        before = stored(path)
        row_limit = max(len(canonical(row)) for table in before['tables'] for row in table['rows'])
        image = world.capture_retained_state(execution=self.execution, clock=self.clock,
                                            limits=RetainedStateLimitsV1(max_row_bytes=row_limit))
        self.assertEqual(json.loads(image.payload)['schema'], before['schema'])

    def test_ordered_marker_roundtrip_rejects_rehashed_semantics_and_nonidempotence(self):
        from proofkey.adapters.ownership import SyntheticOwnershipFixtureV1
        from test_ownership_source import synthetic_fixture
        image = self.world.capture_retained_state(execution=self.execution, clock=self.clock)
        body = json.loads(image.payload)
        table = next(item for item in body['tables'] if item['name'] == 'metadata')
        raw = next(row[1][1] for row in table['rows'] if row[0] == ['text', 'ownership_fixture'])
        reconstructed = SyntheticOwnershipFixtureV1.model_validate(
            body['context']['fixture']['ownership_authority']).model_dump_json()
        self.assertNotEqual(raw, reconstructed)
        self.assertEqual(json.loads(raw), json.loads(reconstructed))
        wrong = SyntheticOwnershipFixtureV1.model_validate(
            synthetic_fixture(self.profile, direct_accept=True)['ownership_authority']).model_dump_json()
        for changed in (' ' + raw, wrong):
            with self.subTest(kind='whitespace' if changed.startswith(' ') else 'different-valid-fixture'):
                damaged = json.loads(image.payload)
                table = next(item for item in damaged['tables'] if item['name'] == 'metadata')
                row = next(row for row in table['rows'] if row[0] == ['text', 'ownership_fixture'])
                row[1][1] = changed
                table['rows'].sort(key=canonical)
                payload = canonical(damaged)
                with self.assertRaises(ValueError):
                    replace(image, payload=payload, content_hash=sha256(payload).hexdigest())

    def test_pure_original_deadline_and_profile_are_bound_not_just_self_consistent(self):
        from test_ownership_source import effect_for
        from support import make_auth
        from proofkey.contracts import EffectIntent
        from proofkey.identity import fingerprint
        effect = effect_for(self.raw, self.profile, self.world.material_revisions())
        self.assertEqual(self.world.bundle().operator.transfer_owner(effect,
            auth=make_auth(caller_id='OP1', proof_reference='synthetic-operator-proof')).status, 'acknowledged')
        image = self.world.capture_retained_state(execution=self.execution, clock=self.clock)
        for mutation in ('original_deadline', 'profile_identity'):
            with self.subTest(mutation=mutation):
                body = json.loads(image.payload)
                if mutation == 'profile_identity':
                    profile = body['context']['profile']
                    profile['profile_id'] = 'foreign-profile'
                    profile['release_hash'] = fingerprint({key: value for key, value in profile.items() if key != 'release_hash'})
                else:
                    tables = {table['name']: table for table in body['tables']}
                    row = next(row for row in tables['metadata']['rows']
                               if row[0][1].startswith('ownership_original:'))
                    record = json.loads(row[1][1])
                    record['effect']['deadline'] = '2026-10-08T11:00:00Z'
                    changed = EffectIntent.model_validate(record['effect'])
                    row[1][1] = json.dumps(record)
                    tables['metadata']['rows'].sort(key=canonical)
                    tables['effects']['rows'][0][8][1] = fingerprint(changed.model_dump(mode='json'))
                payload = canonical(body)
                with self.assertRaises(ValueError):
                    replace(image, payload=payload, content_hash=sha256(payload).hexdigest())

    def test_pure_registered_like_newline_alias_is_not_opaque(self):
        image = self.world.capture_retained_state(execution=self.execution, clock=self.clock)
        body = json.loads(image.payload)
        table = next(table for table in body['tables'] if table['name'] == 'metadata')
        table['rows'].append([['text', 'ownership\noriginal:alias'], ['text', '{opaque']])
        table['rows'].sort(key=canonical)
        counts = tuple((table['name'], len(table['rows'])) for table in body['tables'])
        payload = canonical(body)
        with self.assertRaises(ValueError):
            replace(image, payload=payload, content_hash=sha256(payload).hexdigest(),
                    table_counts=counts, total_rows=image.total_rows + 1)

    def test_finite_large_integer_ticks_are_preserved(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('INSERT INTO pressure VALUES(?,?,?,?,?)',
                       (None, 0, 0, json.dumps([10 ** 400]), 0.0))
        image = self.world.capture_retained_state(execution=self.execution, clock=self.clock)
        self.assertEqual(json.loads(image.payload)['tables'], stored(self.path)['tables'])

    def test_pure_projection_rejects_subclasses_duplicate_payload_and_numeric_spellings(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("INSERT INTO pressure VALUES('test',0,0,'[]',0.0)")
        image = self.world.capture_retained_state(execution=self.execution, clock=self.clock)
        class Alias(SourceRetainedStateSnapshotV1):
            pass
        with self.assertRaises(ValueError):
            Alias(**{field: getattr(image, field) for field in image.__dataclass_fields__})
        for raw in (b'{"domain":"wrong",' + image.payload[1:], b'\xff'):
            with self.subTest(raw=raw[:25]):
                with self.assertRaises(ValueError):
                    replace(image, payload=raw, content_hash=sha256(raw).hexdigest())
        for tag in (['integer', '+0'], ['integer', '-0'], ['integer', str(2 ** 64)],
                    ['real', '0x0p+0'], ['real', 'inf']):
            with self.subTest(tag=tag):
                body = json.loads(image.payload)
                table = next(table for table in body['tables'] if table['name'] == 'pressure')
                table['rows'][0][1] = tag
                payload = canonical(body)
                with self.assertRaises(ValueError):
                    replace(image, payload=payload, content_hash=sha256(payload).hexdigest())

    def test_faulting_clock_does_not_disclose_raw_exception(self):
        class Faulting:
            def now(self):
                raise RuntimeError('private-clock-detail')
            def monotonic(self):
                return 100.0
        with self.assertRaises(SourceRetainedStateFailure) as failure:
            self.world.capture_retained_state(execution=self.execution, clock=Faulting())
        self.assertEqual(str(failure.exception), 'invalid')

    def test_expiry_during_read_connection_cleanup_returns_no_image(self):
        from unittest.mock import patch
        connect = sqlite3.connect
        clock = self.clock
        class DelayedClose(sqlite3.Connection):
            def close(inner):
                super().close()
                clock.utc += timedelta(seconds=5)
                clock.tick += 5
        def opening(*args, **kwargs):
            return connect(*args, **kwargs, factory=DelayedClose)
        before = stored(self.path)
        with patch('sqlite3.connect', opening):
            with self.assertRaises(SourceRetainedStateFailure) as failure:
                self.world.capture_retained_state(execution=self.execution, clock=clock)
        self.assertEqual(failure.exception.code, 'timeout')
        self.assertEqual(stored(self.path), before)

    def test_general_effect_history_survives_current_revocation_and_rejects_overlap(self):
        from support import make_intent
        effect = make_intent(profile_version=self.profile.version,
                             expected_revisions=self.world.material_revisions())
        result = self.world.bundle().scheduling.reschedule(effect)
        self.assertEqual(result.status, 'acknowledged')
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("UPDATE scopes SET readers='{}'")
            db.execute("UPDATE facts SET value='\"revoked\"' WHERE identity='customer.consent'")
            db.execute("UPDATE facts SET value='\"unsafe\"' WHERE identity='delivery.risk'")
            db.execute("UPDATE facts SET value='\"future-generation\"' WHERE identity='case.generation'")
        before = stored(self.path)
        image = self.world.capture_retained_state(execution=self.execution, clock=self.clock)
        self.assertEqual(json.loads(image.payload)['tables'], before['tables'])
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('INSERT INTO final_rejections SELECT account_id,provider_key,case_id,object_id,operation,'
                       'generation,action_id,fingerprint,identity_hash,request_id,created_at FROM effects')
        corrupt = stored(self.path)
        with self.assertRaises(SourceRetainedStateFailure) as failure:
            self.world.capture_retained_state(execution=self.execution, clock=self.clock)
        self.assertEqual(failure.exception.code, 'invalid')
        self.assertEqual(stored(self.path), corrupt)

    def test_registered_namespace_preserves_nul_key_not_selected_by_sql_like(self):
        key = 'ownership\x00original:opaque'
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('INSERT INTO metadata VALUES(?,?)', (key, '{opaque'))
            self.assertEqual(db.execute("SELECT count(*) FROM metadata WHERE key LIKE 'ownership_original:%'").fetchone()[0], 0)
        image = self.world.capture_retained_state(execution=self.execution, clock=self.clock)
        self.assertEqual(json.loads(image.payload)['tables'], stored(self.path)['tables'])

    def test_pure_projection_rejects_duplicate_nonnull_primary_keys(self):
        from support import make_auth
        from test_ownership_source import synthetic_fixture, effect_for
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("INSERT INTO metadata VALUES('opaque-key','raw opaque value')")
            db.execute("INSERT INTO pressure VALUES('opaque-account',0,0,'[]',0.0)")
            db.execute("INSERT INTO reservations VALUES('opaque-token',NULL,0.0)")
        image = self.world.capture_retained_state(execution=self.execution, clock=self.clock)
        examples = [(name, image) for name in ('facts', 'metadata', 'pressure', 'reservations', 'scopes')]
        for status, name in (('pending', 'effects'), ('rejected', 'final_rejections')):
            raw = synthetic_fixture(self.profile)
            world = SimulatedWorld(self.path.with_name('duplicate-' + status + '.sqlite'),
                self.fixture, profile=self.profile, clock=self.clock,
                fixture_bytes=json.dumps(raw).encode())
            effect = effect_for(raw, self.profile, world.material_revisions())
            if status == 'rejected':
                world.set_fault('transfer_owner', 'business_rejection')
            outcome = world.bundle().operator.transfer_owner(effect,
                auth=make_auth(caller_id='OP1', proof_reference='synthetic-operator-proof'))
            self.assertEqual(outcome.status, 'rejected' if status == 'rejected' else 'acknowledged')
            examples.append((name, world.capture_retained_state(execution=self.execution, clock=self.clock)))
        for name, original in examples:
            with self.subTest(table=name):
                body = json.loads(original.payload)
                table = next(item for item in body['tables'] if item['name'] == name)
                row = next(row for row in table['rows'] if name != 'metadata' or row[0] == ['text', 'opaque-key'])
                table['rows'].append(list(row))
                table['rows'].sort(key=canonical)
                payload = canonical(body)
                counts = tuple((item['name'], len(item['rows'])) for item in body['tables'])
                with self.assertRaises(ValueError):
                    replace(original, payload=payload, content_hash=sha256(payload).hexdigest(),
                            table_counts=counts, total_rows=sum(count for _, count in counts))

    def test_close_failure_after_success_is_finite_and_releases_guard(self):
        from unittest.mock import patch
        connect = sqlite3.connect
        for error_type, code in ((sqlite3.OperationalError, 'storage'), (RuntimeError, 'invalid')):
            world = SimulatedWorld(self.path.with_name('close-success-' + code + '.sqlite'),
                self.fixture, profile=self.profile, clock=self.clock)
            world.capture_retained_state(execution=self.execution, clock=self.clock)
            class FailedClose(sqlite3.Connection):
                def close(inner):
                    super().close()
                    raise error_type('private-close-detail')
            def opening(*args, **kwargs):
                return connect(*args, **kwargs, factory=FailedClose)
            error = None
            with patch('sqlite3.connect', opening):
                try:
                    world.capture_retained_state(execution=self.execution, clock=self.clock)
                except Exception as caught:
                    error = caught
            with self.subTest(error_type=error_type.__name__, check='finite'):
                self.assertIsInstance(error, SourceRetainedStateFailure)
                self.assertEqual(error.code, code)
                self.assertEqual(str(error), code)
            with self.subTest(error_type=error_type.__name__, check='released'):
                self.assertIsInstance(world.capture_retained_state(execution=self.execution, clock=self.clock),
                                      SourceRetainedStateSnapshotV1)

    def test_close_failure_after_rejection_is_finite_and_releases_guard(self):
        from unittest.mock import patch
        connect = sqlite3.connect
        for error_type, code in ((sqlite3.OperationalError, 'storage'), (RuntimeError, 'invalid')):
            world = SimulatedWorld(self.path.with_name('close-rejection-' + code + '.sqlite'),
                self.fixture, profile=self.profile, clock=self.clock)
            world.capture_retained_state(execution=self.execution, clock=self.clock)
            class FailedClose(sqlite3.Connection):
                def close(inner):
                    super().close()
                    raise error_type('private-close-detail')
            def opening(*args, **kwargs):
                return connect(*args, **kwargs, factory=FailedClose)
            error = None
            with patch('sqlite3.connect', opening):
                try:
                    world.capture_retained_state(execution=self.execution, clock=self.clock,
                                                limits=RetainedStateLimitsV1(max_rows=1))
                except Exception as caught:
                    error = caught
            with self.subTest(error_type=error_type.__name__, check='finite'):
                self.assertIsInstance(error, SourceRetainedStateFailure)
                self.assertEqual(error.code, code)
                self.assertEqual(str(error), code)
            with self.subTest(error_type=error_type.__name__, check='released'):
                self.assertIsInstance(world.capture_retained_state(execution=self.execution, clock=self.clock),
                                      SourceRetainedStateSnapshotV1)
