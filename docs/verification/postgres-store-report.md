# PostgreSQL case store verification

Date: 2026-10-10. Scope: PostgreSQL storage, shared case revision hook, migration and durable analysis intents. No cloud resource, provider call, external effect, or SQLite migration was performed.

## Implementation

- `tools/dwelly_service/postgres.py` exposes the specified case store, explicit migration, readiness, bounded pool and fenced lease interfaces.
- `tools/dwelly_service/migrations/001_case_backend.sql` stores canonical snapshots and request bodies as TEXT. It constrains revision identity, snapshot references and outbox status/lease shape.
- `tools/dwelly_service/cases.py` adds only a default no-op `_after_revision` hook, called after a newly inserted revision and idempotency record but before transaction commit. PostgreSQL inserts the matching outbox intent in that transaction.
- Writes use a namespace-specific PostgreSQL transaction advisory lock. Reads use repeatable-read transactions. Separate processes can share the database, but writes within one schema serialize at the current bounded v1 scale.
- Outbox records must match validated immutable snapshot history before exposure or claim. Leases use database time, opaque tokens, expiration, and token-fenced acknowledgement. These are durable intents, not an exactly-once execution guarantee or a connected worker.

## TDD evidence

1. Before implementation, the initial seven real-PostgreSQL tests failed with `PostgreSQL case storage must be implemented` (7 failed).
2. After implementation and correction of the test fixture's macOS symlink path, those seven tests passed alongside the existing SQLite case tests (26 passed, 100 subtests).
3. Self-review found that an altered outbox hash could be exposed or claimed. The added `test_outbox_corruption_cannot_be_exposed_or_claimed_as_valid_work` failed with `CaseError not raised` before the integrity check was added, then passed.
4. The final storage suite includes 13 real-PostgreSQL tests (13 passed, 14 subtests). It covers byte-for-byte SQLite snapshot TEXT parity; exact retries and restart; concurrent appends; independent pools and separate Python processes; atomic rollback on outbox failure; expired/reclaimed token fencing; distinct claims; bounded pool exhaustion; explicit/idempotent migration; rejected invalid configuration/leases; closed storage; and corrupt history/outbox handling.

## Reproduction

The disposable test database ran from cached `postgres:17.11-bookworm` with loopback-only networking and local trust authentication. The test interpreter was `/tmp/proofkey-postgres-tests-20261010/bin/python`, using `psycopg==3.3.6`, `psycopg-pool==3.3.3`, and `pytest==9.1.1`. This temporary tooling environment does not establish the deployment dependency lock's qualification.

```sh
PROOFKEY_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:63119/proofkey \
  /tmp/proofkey-postgres-tests-20261010/bin/python -m pytest -q \
  tools/dwelly_service/tests/test_postgres_store.py
```

Tests create uniquely named database schemas and drop only their own schemas on cleanup. The container is retained while coordinator HTTP integration tests use the same database.

`git diff --check` passed after the storage changes.

The entire current service test directory also passed against the disposable database: `python -m pytest -q tools/dwelly_service/tests` reported **83 passed, 175 subtests passed in 33.15s**, including existing SQLite service/case tests and the coordinator's new PostgreSQL HTTP tests.

## Broad-suite boundary

A requested bare repository-root `python -m pytest -q` run stopped at collection with 979 errors: archived repositories under `outputs/` duplicated test module names; this temporary interpreter also lacked `jsonschema` and the runtime source import path. This run executed no tests and is not a green regression result. Canonical source directories and the configured runtime import path must be used for broad regression. The coordinator owns the full integration and deployment evidence.

## Review follow-up: content-free database logging

Independent review reproduced a raw connection-string leak from background `psycopg.pool` warnings. A new regression failed before the fix because a deliberately fake `sentinel_private_password` appeared in captured logs. The cause was worker-side connection exception formatting occurring before the CLI's sanitized exception handling.

The fix parses connection settings synchronously before workers start, and adds a narrowly scoped log filter for named ProofKey pool threads and the calling context of this store's database operations. Diagnostics retain severity and occurrence using `proofkey_database_pool_event`; connection arguments, exception text and stack details are removed. Other pools' logging remains unchanged. The filter covers connection, reconnect, scheduler, transaction cleanup and close paths, including late worker messages. It does not globally disable or lower PostgreSQL logging.

After the fix, the store/logging suite reported **16 passed, 16 subtests passed in 2.65s**. Tests capture real refused loopback connection/reconnect/timeout/close behavior and broken-connection cleanup, verify that endpoint and dummy credential markers do not appear, and assert that an unrelated PostgreSQL warning still appears unchanged. Malformed connection strings and unknown URI options are covered. The default interpreter without optional PostgreSQL dependencies reported **2 logging tests skipped**, while an explicit test DSN continues to require the dependencies.

The CLI `serve` reproducer with the fake malformed password now exits 2 and emits only `{"error": "case_service_start_failed"}`. The `migrate` command with a fake unknown URI option has the same content-free result.

Final review-fix service regression: `PROOFKEY_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:63119/proofkey /tmp/proofkey-postgres-tests-20261010/bin/python -m pytest -q tools/dwelly_service/tests` reported **87 passed, 177 subtests passed in 35.96s**. `git diff --check` remained clean. The deployment agent was asked to rebuild Compose with this fix; its separate receipt establishes image verification.
