"""Pinned dataset input extraction through real persistence backends."""
from copy import deepcopy
from datetime import datetime, timezone
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid

from tools.dwelly_service.cases import CaseError, CaseStore, _canonical
from tools.dwelly_service.store import JobStore
from tools.dwelly_service.tests.test_cases import declaration, event

try:
    export_module = importlib.import_module('tools.dwelly_service.dataset_export')
except ModuleNotFoundError:
    export_module = None

DSN = os.environ.get('PROOFKEY_TEST_DATABASE_URL')


class DatasetExportTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(export_module, 'dataset export adapter must exist')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name).resolve() / 'state'
        self.owner = JobStore(self.state)
        self.addCleanup(self.owner.close)
        self.store = CaseStore(self.owner)
        self.zero, _ = self.store.create('create-1', declaration())
        self.one, _ = self.store.append('demo-1', 'append-1', event())
        later = event('event-2', 1)
        later['event']['occurred_at'] = '2026-10-11T10:00:00Z'
        self.store.append('demo-1', 'append-2', later)
        self.options = dict(case_id='demo-1', revision=1, expected_snapshot_hash=self.one['snapshot_hash'],
            input_id='input-1', provenance=dict(source_kind='synthetic', source_id='fixture-1',
            collected_at='2026-10-10T10:00:00Z'), as_of='2026-10-10T11:00:00Z')

    def export(self, **overrides):
        return export_module.export_decision_input(self.store, **{**self.options, **overrides})

    def test_pinned_revision_excludes_later_evidence_and_has_closed_keyset(self):
        value = self.export()
        self.assertEqual(set(value), {'schema_version', 'visibility', 'input_id', 'source', 'snapshot', 'provenance'})
        self.assertEqual(value['schema_version'], 'proofkey-decision-input-v1')
        self.assertEqual(value['visibility'], 'model_visible')
        self.assertEqual(value['snapshot'], self.one)
        self.assertEqual(value['source'], dict(case_id='demo-1', revision=1, snapshot_hash=self.one['snapshot_hash']))
        self.assertEqual(value['provenance'], self.options['provenance'])
        value['provenance']['source_id'] = 'changed'
        self.assertEqual(self.options['provenance']['source_id'], 'fixture-1')
        value['snapshot']['events'].clear()
        self.assertEqual(self.store.get('demo-1', 1), self.one)

    def test_hash_and_revision_are_mandatory_and_exact(self):
        for overrides in [dict(expected_snapshot_hash='0' * 64), dict(expected_snapshot_hash=None),
                          dict(revision=None), dict(revision=-1), dict(revision=True), dict(input_id='bad id')]:
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                self.export(**overrides)
        missing = dict(self.options)
        del missing['revision']
        with self.assertRaises(TypeError):
            export_module.export_decision_input(self.store, **missing)

    def test_future_evidence_and_naive_cutoff_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'evidence_after_as_of'):
            self.export(as_of='2026-10-10T09:59:59Z')
        for cutoff in ['2026-10-10T11:00:00', datetime(2026, 10, 10, 11)]:
            with self.subTest(cutoff=cutoff), self.assertRaises(ValueError):
                self.export(as_of=cutoff)
        self.assertEqual(self.export(as_of=datetime(2026, 10, 10, 11, tzinfo=timezone.utc))['snapshot'], self.one)

    def test_provenance_is_closed_and_matches_schema_semantics(self):
        for change in [dict(source_kind='postgres'), dict(source_id=''), dict(collected_at='2026-10-10'),
                       dict(collected_at='2026-10-10T10:00:00'), dict(collected_at='2026-02-30T10:00:00Z'),
                       dict(expected_disposition='hold'), dict(outbox={})]:
            value = {**self.options['provenance'], **change}
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.export(provenance=value)
        value = dict(self.options['provenance'])
        del value['source_id']
        with self.assertRaises(ValueError):
            self.export(provenance=value)
        for kind in ['local_fixture', 'synthetic', 'human_authored', 'imported']:
            self.assertEqual(self.export(provenance={**self.options['provenance'], 'source_kind': kind})['provenance']['source_kind'], kind)
        with self.assertRaises(TypeError):
            self.export(expected_disposition='hold')

    def test_corrupted_stored_history_and_forbidden_snapshot_fields_are_rejected(self):
        with self.owner._connect() as connection:
            snapshot = deepcopy(self.zero)
            snapshot['expected_disposition'] = 'hold'
            connection.execute('UPDATE case_snapshots SET snapshot=? WHERE revision=0', (_canonical(snapshot),))
        with self.assertRaises(CaseError):
            self.export()

    def test_cli_rejects_sqlite_without_recovering_running_job(self):
        job, _ = self.owner.submit('benchmark-job', {'mode': 'dry_run'})
        with self.owner._connect() as connection:
            connection.execute("UPDATE jobs SET status='running' WHERE job_id=?", (job['job_id'],))
        self.owner.close()
        output = Path(self.temp.name) / 'input.json'
        args = [sys.executable, '-m', 'tools.dwelly_service.dataset_export', '--backend', 'sqlite',
            '--sqlite-state', str(self.state), '--output', str(output), '--case-id', 'demo-1', '--revision', '1',
            '--expected-snapshot-hash', self.one['snapshot_hash'], '--input-id', 'input-1', '--source-kind', 'synthetic',
            '--source-id', 'fixture-1', '--collected-at', '2026-10-10T10:00:00Z', '--as-of', self.options['as_of']]
        result = subprocess.run(args, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(output.exists())
        import sqlite3
        with sqlite3.connect(str(self.state / 'queue.sqlite3')) as connection:
            self.assertEqual(connection.execute('SELECT status FROM jobs WHERE job_id=?', (job['job_id'],)).fetchone()[0], 'running')

    def test_callable_does_not_mutate_running_benchmark_job(self):
        job, _ = self.owner.submit('benchmark-job', {'mode': 'dry_run'})
        with self.owner._connect() as connection:
            connection.execute("UPDATE jobs SET status='running' WHERE job_id=?", (job['job_id'],))
        before = self.owner.get(job['job_id'])
        self.export()
        self.assertEqual(self.owner.get(job['job_id']), before)

    def test_exclusive_output_is_private_and_rejects_symlinks(self):
        output = Path(self.temp.name) / 'input.json'
        export_module._write_exclusive(output, self.export())
        self.assertEqual(output.stat().st_mode & 0o777, 0o600)
        original = output.read_bytes()
        with self.assertRaises(FileExistsError):
            export_module._write_exclusive(output, self.export())
        self.assertEqual(output.read_bytes(), original)
        link = Path(self.temp.name) / 'link.json'
        link.symlink_to(output)
        with self.assertRaises(OSError):
            export_module._write_exclusive(link, self.export())
        self.assertEqual(output.read_bytes(), original)

    def test_failed_write_removes_only_its_partial_output(self):
        output = Path(self.temp.name) / 'input.json'
        actual_write = os.write
        calls = []
        def interrupted_write(fd, data):
            if calls:
                raise OSError('simulated disk write failure')
            calls.append(True)
            return actual_write(fd, data[:3])
        with patch.object(export_module.os, 'write', side_effect=interrupted_write):
            with self.assertRaises(OSError):
                export_module._write_exclusive(output, self.export())
        self.assertFalse(output.exists())

    def test_failed_write_preserves_concurrent_replacement(self):
        output = Path(self.temp.name) / 'input.json'
        def replaced_output(fd, data):
            output.unlink()
            output.write_bytes(b'other writer')
            raise OSError('simulated replacement during write')
        with patch.object(export_module.os, 'write', side_effect=replaced_output):
            with self.assertRaises(OSError):
                export_module._write_exclusive(output, self.export())
        self.assertEqual(output.read_bytes(), b'other writer')

    @unittest.skipUnless(DSN, 'set PROOFKEY_TEST_DATABASE_URL for PostgreSQL parity')
    def test_postgres_sqlite_exact_export_parity(self):
        import psycopg
        from psycopg import sql
        from tools.dwelly_service.postgres import PostgresCaseStore, migrate
        schema = 'test_export_' + uuid.uuid4().hex
        def cleanup():
            with psycopg.connect(DSN, autocommit=True) as connection:
                connection.execute(sql.SQL('DROP SCHEMA IF EXISTS {} CASCADE').format(sql.Identifier(schema)))
        self.addCleanup(cleanup)
        migrate(DSN, schema=schema)
        postgres = PostgresCaseStore(DSN, schema=schema, max_size=1)
        self.addCleanup(postgres.close)
        postgres.create('create-1', declaration())
        postgres.append('demo-1', 'append-1', event())
        later = event('event-2', 1)
        later['event']['occurred_at'] = '2026-10-11T10:00:00Z'
        postgres.append('demo-1', 'append-2', later)
        result = export_module.export_decision_input(postgres, **self.options)
        self.assertEqual(_canonical(result).encode('utf-8'), _canonical(self.export()).encode('utf-8'))
        self.assertEqual(len(postgres.analysis_jobs('demo-1')), 3)
        output = Path(self.temp.name) / 'postgres-input.json'
        args = [sys.executable, '-m', 'tools.dwelly_service.dataset_export', '--output', str(output),
            '--case-id', 'demo-1', '--revision', '1', '--expected-snapshot-hash', self.one['snapshot_hash'],
            '--input-id', 'input-1', '--source-kind', 'synthetic', '--source-id', 'fixture-1',
            '--collected-at', '2026-10-10T10:00:00Z', '--as-of', self.options['as_of']]
        completed = subprocess.run(args, env={**os.environ, 'PROOFKEY_DATABASE_URL': DSN,
            'PROOFKEY_DATABASE_SCHEMA': schema}, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual(json.loads(output.read_bytes()), result)
        completed = subprocess.run(args, env={**os.environ, 'PROOFKEY_DATABASE_URL': DSN,
            'PROOFKEY_DATABASE_SCHEMA': schema}, capture_output=True, text=True)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn('output_exists', completed.stderr)


if __name__ == '__main__':
    unittest.main()
