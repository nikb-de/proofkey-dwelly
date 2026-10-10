## 1. PostgreSQL store
- [x] 1.1 Add versioned migrations and bounded pooled store with existing v1 semantics.
- [x] 1.2 Atomically enqueue revisions and add fenced outbox claims/acknowledgements.
- [x] 1.3 Verify on real PostgreSQL including concurrency, rollback and restart.

## 2. Case-only API
- [x] 2.1 Add separate authenticated case API and explicit migrate/serve CLI.
- [x] 2.2 Verify strict inputs, error sanitization and preserved HTTP contract.

## 3. Local deployment and handoff
- [x] 3.1 Add isolated Compose, narrow image, pinned dependencies and configuration example.
- [x] 3.2 Verify create/append/read/retry/restart smoke; document Cloud SQL boundary.
- [x] 3.3 Run regression and independent review; archive this change.

## 4. Dataset adapter compatibility
- [x] 4.1 Add pinned-revision model-input export with private exclusive file output.
- [x] 4.2 Verify real SQLite/PostgreSQL parity, stale hashes, cutoff and no benchmark recovery.
