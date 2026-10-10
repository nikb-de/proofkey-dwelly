# PostgreSQL Case Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Execute the disjoint tasks in parallel as expressly requested; do not overwrite another task's files.

**Goal:** A runnable PostgreSQL case backend compatible with the frozen team dataset and ready for subsequent private Cloud SQL deployment work.

**Architecture:** Separate case-only API from the legacy local benchmark worker. Reuse canonical case validation; persist immutable snapshots and a transactional, leased analysis outbox in PostgreSQL. Local Docker uses the same database engine as the cloud target.

**Tech Stack:** Python 3.12+, PostgreSQL 17.11, psycopg 3, psycopg_pool, stdlib HTTP, Docker Compose.

**Spec:** `openspec/specs/postgres-case-backend/spec.md`; proposal/design history is archived under `openspec/changes/archive/`.

## Global Constraints
- No paid resources, provider calls, real external effects, secret disclosure or automatic SQLite migration.
- Preserve v1 snapshots, hashes, errors, limits and dataset files byte-for-byte.
- Migrations are explicit; pool maximum defaults to 4; canonical JSON is TEXT.
- Outbox completion requires current unexpired lease token; it is not exactly-once external execution.
- Existing local benchmark service is not made cloud-safe by this increment.

## Review Focus
- Simultaneous retries and appends must not create duplicate revisions or intents.
- A failed outbox insert must roll back the whole case transaction.
- A dead worker's lease must not complete a reclaimed intent.
- Invalid inputs and database failures must not expose a DSN, token or case text.
- Dataset hash parity and revision history must survive process/service restart.

### Task 1: PostgreSQL store and transactional outbox
**Owner:** postgres_store.
**Files:** new `tools/dwelly_service/postgres.py`, `tools/dwelly_service/migrations/001_case_backend.sql`, `tools/dwelly_service/tests/test_postgres_store.py`; minimal hook in `tools/dwelly_service/cases.py` if required.
**Interfaces:** exact signatures in the design. Do not inherit filesystem JobStore or port the legacy worker.
- [x] Write and run failing real-PG tests: `create`, exact retry, competing append, canonical parity, restart, rollback and fenced leases.
- [x] Implement explicit migration and pooled PostgreSQL transactions; reuse validation via a narrow SQL adapter and `_after_revision` hook if necessary.
- [x] Verify the tests against a disposable local PostgreSQL database; record commands and counts.
- [x] Review task diff and fix important findings.

### Task 2: Deployment bundle
**Owner:** postgres_deploy.
**Files:** `Dockerfile.case-api`, `Dockerfile.case-api.dockerignore`, `compose.postgres.yaml`, `.env.postgres.example`, `requirements-postgres.lock`, `deploy/postgres/README.md`, `deploy/postgres/smoke.py`.
**Interfaces:** `python -m tools.dwelly_service.case_api migrate|serve`; config names from design. Bind host API to loopback, DB not published. API depends on successful migration.
- [x] Verify local Docker and choose cached pinned PostgreSQL 17.11; do not touch unrelated containers.
- [x] Add reproducible build, migration service, persistent database and safe env example; exclude real `.env` and unrelated raw data from image context.
- [x] Run smoke with synthetic case IDs, exact retries and historical reads; restart API and prove persistence.
- [x] Document Cloud SQL connection/pooling setup separately from unimplemented managed ingress and workers.

### Task 3: Case API and integration
**Owner:** coordinator.
**Files:** `tools/dwelly_service/case_api.py`, `tools/dwelly_service/tests/test_postgres_http.py`, `docs/architecture/postgres-case-backend.md`, targeted README/architecture updates.
**Interfaces:** `create_case_server(store, *, token, host='127.0.0.1', port=8080, allowed_hosts=None)`; `main(argv=None)` for CLI.
- [x] Write HTTP tests before implementation: auth/host/origin, exact create/append/read, errors, pending outbox metadata and no `/v1/jobs` route.
- [x] Add explicit migrate/serve CLI and case-only handler; storage exceptions become content-free 503 responses.
- [x] Run new real-PG suites, all existing service/contract/dataset tests and Compose smoke.
- [x] Request independent review; fix important findings, record remaining boundaries and archive OpenSpec.

## Execution record
- The user explicitly requested parallel implementation and previously asked not to stop for repeated stage confirmations. Spec/plan are recorded before product edits.
- The existing managed worktree `codex/proofkey-runtime` is reused; `docs/dataset-drafts/` remains untouched.
- Final related-source regression: 375 tests and 487 subtests passed. Final frozen Docker image: 45/45 smoke checks, with source hashes matched before/after both restart paths. Independent review's database-log disclosure finding was fixed and rechecked.
- The interrupted full-runtime run is not claimed as a completed regression. See `docs/verification/postgres-integration-report.md` for exact commands and limits.

### Task 4: Backend-neutral model-input extraction
**Owner:** dataset_validator.
**Files:** `tools/dwelly_service/dataset_export.py`, `tests/test_dataset_export.py`, verification report.
**Interfaces:** `export_decision_input(store, *, case_id, revision, expected_snapshot_hash, input_id, provenance, as_of)`; PostgreSQL CLI uses private env credentials and exclusive mode-0600 output.
- [x] Verify RED then GREEN for explicit old revision after a new event, stale hash, future cutoff, closed provenance and SQLite/PostgreSQL exact parity.
- [x] Verify exporter never opens the SQLite recovery owner, never changes running jobs, never overwrites files, and safely removes only its own incomplete output.
- [x] Document source adapter versus unchanged semantic contract; do not label this model training or complete temporal leakage prevention.
