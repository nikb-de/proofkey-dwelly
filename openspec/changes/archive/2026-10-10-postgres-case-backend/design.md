# Design

## Intent and authorization
User approved PostgreSQL locally and Cloud SQL PostgreSQL as the shared target, and requested autonomous parallel implementation. Existing instructions explicitly waive repeated stage approvals. This is an architectural increment, not a migration of the entire benchmark runtime.

## Decision
Create a separate case-only PostgreSQL service. Reuse `CaseStore` validation and canonical snapshot construction with a small transaction hook instead of forking the business rules. Store canonical JSON as TEXT to preserve exact hashing semantics. Transactions use a namespace-scoped advisory lock for bounded v1 writes (256 cases, 128 events each), consistent reads and a bounded connection pool. This deliberately prioritizes correctness over high write throughput; PostgreSQL remains multi-process accessible.

Use explicit, versioned SQL migrations. `PostgresCaseStore(database_url, *, schema='public', min_size=0, max_size=4)` does not provision a database or run migrations implicitly. `migrate(database_url, *, schema='public')` applies idempotently. Both validate schema identifiers and sanitize exposed errors.

New revisions write their snapshot, head, idempotency record and analysis outbox in one transaction. An intent is unique per `(case_id, revision)`, carries the immutable snapshot hash, and has `pending`, `leased`, or `completed` status. Workers claim using `FOR UPDATE SKIP LOCKED`, an opaque lease token and database-time expiry. Acknowledgement requires a current unexpired token. Expired leases may be reclaimed. This guarantees fenced acknowledgement, NOT exactly-once external effects. No worker is connected and no model result is invented.

The HTTP service reuses strict case body/error handling but exposes only health, capabilities, create/read/append, and read-only analysis-job status. It has no legacy `/v1/jobs`, provider, filesystem or execution endpoints. It requires an operator token, rejects browser Origin headers, validates Host against explicit allowed hosts, and emits content-free errors. `healthz` is liveness; `readyz` checks storage. Public Cloud Run deployment remains disabled in this increment; private authenticated ingress and operational hardening remain explicit prerequisites.

## Interfaces
- `PostgresCaseStore.create(key, body) -> (snapshot, created)`
- `PostgresCaseStore.append(case_id, key, body) -> (snapshot, created)`
- `PostgresCaseStore.get(case_id, revision=None) -> snapshot`
- `PostgresCaseStore.check_ready()`; `close()`
- `PostgresCaseStore.analysis_jobs(case_id) -> list` (safe public metadata only)
- `PostgresCaseStore.claim_analysis(worker_id, *, lease_seconds=60) -> dict | None`
- `PostgresCaseStore.ack_analysis(job_id, lease_token) -> bool`
- CLI `python -m tools.dwelly_service.case_api migrate|serve`, configuration via `PROOFKEY_DATABASE_URL`, `PROOFKEY_DATABASE_SCHEMA`, `PROOFKEY_SERVICE_TOKEN`, `PROOFKEY_ALLOWED_HOSTS`, `PROOFKEY_DB_POOL_MAX`, `HOST`, `PORT`.

## Boundaries and rollout
Use PostgreSQL 17.11 in local Docker; target the same schema on Cloud SQL PostgreSQL, with deployed compatibility still to be verified. Keep existing SQLite data untouched; no automatic transfer. Photos/audio are metadata only. Existing browser UI is not connected. The dataset JSON format and source mode remain v1 local fixtures. A persistent outbox is not automatic case analysis.

## Verification
Real PostgreSQL tests for idempotency, competing writes, hash parity, rollback, restart, pool capacity and lease fencing. Real HTTP tests for auth/origin/host guards and frozen payloads. Compose smoke creates and appends a case, checks revision zero, retries and restart persistence. Existing SQLite and contract suites remain green.

## Dataset tooling adjustment
Keeping the JSON contract stable does not make the extraction tooling unchanged. Add `export_decision_input(store, *, case_id, revision, expected_snapshot_hash, input_id, provenance, as_of)` and a PostgreSQL-only CLI. It reads a specified immutable revision, checks its expected hash and occurrence-time cutoff, then produces exactly `proofkey-decision-input-v1`. It never exports labels, criteria or leases, never opens SQLite JobStore in the CLI (opening it triggers recovery), and writes new private files exclusively. The callable accepts an already-owned SQLite or PostgreSQL store. A late/backdated event requires a trusted observation receipt for complete temporal leakage protection; v1 has none. Export is not a complete labelled dataset, model runner adapter or training run.
