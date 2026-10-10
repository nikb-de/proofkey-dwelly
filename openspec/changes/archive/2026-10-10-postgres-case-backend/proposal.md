# PostgreSQL case backend

## Why
The shared team service must not depend on a process-owned SQLite file. We need one relational source of truth across API instances and durable case-revision work without changing the released training/evaluation format.

## What Changes
- Add a PostgreSQL-backed case API, distinct from the legacy local benchmark service.
- Preserve all v1 case validation, snapshots, hashes, errors, optimistic revisions and idempotency.
- Atomically enqueue an analysis intent for every new revision, with fenced expiring leases for future workers.
- Provide local PostgreSQL Docker Compose, explicit migrations and Cloud SQL connection guidance.
- Keep media bytes, real analysis/execution, IAM ingress and deployment provisioning outside this increment.

## Capabilities
### New Capabilities
- `postgres-case-backend`: durable shared case state and leased analysis outbox.

## Impact
New database dependency and separate service entrypoint; existing SQLite benchmark, schemas and dataset kit remain compatible. No paid resources or provider calls are made.
