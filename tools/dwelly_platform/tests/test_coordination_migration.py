"""Upgrade a real pre-coordination database without deleting case history."""
import os
from pathlib import Path
import uuid

import psycopg
from psycopg import sql
import pytest

from tools.dwelly_service import postgres
from tools.dwelly_service.tests.test_cases import declaration, event
from tools.dwelly_platform import store as platform


@pytest.fixture
def legacy_database():
    dsn = os.environ.get('PROOFKEY_TEST_DATABASE_URL')
    if not dsn:
        pytest.skip('real PostgreSQL required')
    schema = 'coord_upgrade_' + uuid.uuid4().hex
    postgres.migrate(dsn, schema=schema)
    try:
        with psycopg.connect(dsn) as connection:
            postgres._search_path(connection, schema)
            connection.execute('CREATE TABLE platform_schema_migrations (version INTEGER PRIMARY KEY)')
            path = Path(platform.__file__).parent / 'migrations' / '001_platform.sql'
            connection.execute(path.read_text(encoding='utf-8'))
            connection.execute('INSERT INTO platform_schema_migrations VALUES (1)')
        yield dsn, schema
    finally:
        with psycopg.connect(dsn) as connection:
            connection.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))


def test_v1_upgrade_preserves_history_and_request_receipts(legacy_database):
    dsn, schema = legacy_database
    old = postgres.PostgresCaseStore(dsn, schema=schema)
    old.create('create-before-upgrade', declaration())
    old.append('demo-1', 'event-before-upgrade', event())
    before = old.get('demo-1')
    old.close()
    platform.migrate(dsn, schema=schema)
    platform.migrate(dsn, schema=schema)
    upgraded = platform.PlatformStore(dsn, schema=schema)
    try:
        assert upgraded.get('demo-1') == before
        assert upgraded.coordination_detail('demo-1') is None
        assert upgraded.detail('demo-1')['states']['coordination'] == 'not_initialized'
        # The old idempotency receipt remains usable after both migrations.
        upgraded.append('demo-1', 'event-before-upgrade', event())
        assert upgraded.get('demo-1') == before
        with upgraded._transaction() as connection:
            versions = connection.execute('SELECT version FROM platform_schema_migrations ORDER BY version').fetchall()
            assert [row[0] for row in versions] == [1, 2]
            assert connection.execute('SELECT count(*) FROM platform_coordination').fetchone()[0] == 0
    finally:
        upgraded.close()


def test_unknown_platform_schema_version_is_rejected(legacy_database):
    dsn, schema = legacy_database
    with psycopg.connect(dsn) as connection:
        postgres._search_path(connection, schema)
        connection.execute('INSERT INTO platform_schema_migrations VALUES (99)')
    with pytest.raises(platform.PlatformError, match='platform_storage_error'):
        platform.migrate(dsn, schema=schema)
