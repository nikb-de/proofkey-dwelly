# Independent PostgreSQL case backend review

Date: 2026-10-10. Baseline: `db01cad`. Reviewed the uncommitted implementation directly in the `proofkey-runtime` worktree, including the final PostgreSQL-only dataset export CLI and subsequent logging fix. This review made no implementation changes, provider calls, or cloud changes. The focused re-review ran an existing test that creates and removes its own disposable local PostgreSQL schema.

## Code quality findings

### Resolved P2: Background connection warnings bypassed error sanitization

Original location: `tools/dwelly_service/postgres.py:84-86` before the fix (pool construction), affecting both `tools/dwelly_service/case_api.py:213` and `tools/dwelly_service/dataset_export.py:115-116`. Current fix: `postgres.py:26-60`, `:73-93`, `:115-155`, `:165-169`.

Before the fix, `ConnectionPool` connected and reconnected in background workers whose `psycopg.pool` logger formatted the original connection exception before the store caught and replaced the eventual error. The sanitized CLI JSON therefore did not prevent connection-string content from appearing in process/container logs. A malformed secret configuration could expose the supplied value; valid connections that failed also disclosed endpoint details. The deployment guide explicitly recommends inspecting these logs.

Confirmed using the installed `psycopg-pool==3.3.3` and synthetic input only: call `case_api.main(['serve'])` with `PROOFKEY_DATABASE_URL='sentinel_private_password'` and a synthetic valid service token, capturing the pool logger. The command returns 2 and emits `{"error": "case_service_start_failed"}`, but first emits this warning repeatedly:

```text
error connecting in 'pool-3': missing "=" after "sentinel_private_password" in connection info string
```

A second synthetic malformed URI echoed its unknown query parameter. A loopback-only connection-refused probe emitted its host/port. No real credentials were used, and malformed inputs did not establish any database connection.

Resolution independently checked: malformed connection strings now fail synchronously before pool creation. A logging filter replaces payloads and clears exception/stack fields for scoped caller-side database operations and uniquely named pool worker/scheduler threads. Migration, transaction borrow/return, and pool close use the scope. The pinned synchronous psycopg/psycopg-pool sources use the covered logger names and worker names. Unrelated database log records outside these scopes remain intact.

Independent re-review ran the two `PostgresLoggingTests` and `PostgresStoreTests::test_broken_connection_cleanup_does_not_log_connection_details`: **3 passed, 2 subtests passed in 2.10s**. These exercise malformed configuration, real loopback connection failure/reconnection timeout, constructor cleanup, and a real PostgreSQL connection closed during a caller transaction. Captured DEBUG/WARNING output contains only the generic service event for scoped operations. Repeating the original malformed-DSN probe through both `serve` and `migrate` returned exit code 2 with only `{"error": "case_service_start_failed"}`. No sentinel appeared.

No unresolved concrete P1/P2 defect was identified in the reviewed implementation. Logging coverage is verified against the pinned dependency versions; dependency upgrades must retain the regression checks. This is not a production-readiness certification.

## Specification compliance

- **Revision atomicity and retries:** compliant by code inspection. The shared five-line hook runs after snapshot/head/request writes but inside the existing transaction (`cases.py:258-278`, `:280-304`). PostgreSQL inserts its outbox intent through that hook (`postgres.py:171-173`). A schema-scoped transaction advisory lock serializes writers; repeatable-read read transactions keep head/history consistent (`postgres.py:138-155`). Existing exact-request replay returns its original stored revision before another append is made (`cases.py:234-256`, `:288-290`).
- **Lease fencing:** compliant by code inspection. Claim uses row locking and an opaque fresh token; expiry and acknowledgement use database time (`postgres.py:196-231`). Acknowledgement requires leased status, matching token, and unexpired lease. Public job output excludes lease/worker fields and checks snapshot correspondence (`postgres.py:175-194`). These guarantees do not imply exactly-once provider execution.
- **Explicit migration and bounded database connections:** compliant by inspection. The constructor checks readiness rather than migrating. Migration is explicit and transactionally versioned (`postgres.py:73-93`, `:115-136`, `:157-163`). Pool connections and waiting borrowers are bounded. The global write lock is the documented throughput tradeoff, not an accidental concurrency regression.
- **API boundary:** case requests require a bearer token, exact allowed Host, and absent Origin (`case_api.py:59-70`). HTTP routing exposes cases, capabilities and read-only intent status without a worker or legacy execution endpoint. Liveness/readiness are distinct. Startup and bind-failure ownership are consistent with the supplied-store API (`case_api.py:160-184`, `:223-227`). The original background logging sanitization gap is resolved as documented above.
- **Frozen dataset contract:** no canonical schema or dataset JSON changes were present in the baseline diff. The only tracked change under `contracts/v1` was explanatory README text. Export constructs the six-field existing decision-input envelope, pins revision and hash, and rejects occurrence times after the cutoff (`dataset_export.py:38-68`). The CLI opens PostgreSQL only; callers can supply an already-owned SQLite store without benchmark recovery. Its exclusive 0600 writer rejects overwrite/symlink targets and attempts to remove its own partial output on failure (`dataset_export.py:71-94`, `:109-133`). The documented absence of trusted observation time limits claims about backdated/late evidence.
- **Local/cloud scope:** Compose publishes only the loopback API port, publishes no PostgreSQL port, and orders API start after explicit migration (`compose.postgres.yaml:16-60`). The image starts only the case API. Cloud Run startup is explicitly rejected; the Cloud SQL material describes future prerequisites and does not provision resources. This review does not establish Cloud SQL compatibility through execution.

## Evidence and limits

Read the OpenSpec design and delta requirements, complete storage/API/migration/export implementations, deployment configuration and smoke script, new store/HTTP/export tests, and the existing shared case validation and retry implementation. Ran `git diff --check` successfully and the targeted synthetic connection-error probes described above. No broad test suite was rerun by this reviewer.

The coordinator originally supplied passing evidence for 13 real-PostgreSQL storage tests, 8 HTTP tests, 11 exporter tests, and 45 Compose smoke checks across API/database restarts; after the logging fix, the storage agent reported 16 storage/logging tests passing. Those full-suite results are supplied evidence, not independently rerun test results. Only the three focused logging tests and CLI probes above were rerun independently. Broad source-suite verification and OpenSpec archival remain the coordinator's responsibility. Formal task checkboxes were still open when initially inspected; their final state is outside this review's completion claim.
