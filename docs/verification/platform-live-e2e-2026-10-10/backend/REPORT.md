# Backend state and transaction verification

Result: **307 passed, 42 subtests passed, zero failures or skips**, in 67.17 seconds. Tested commit: `8f6a530f9503e9ae30fbadcaef96033b317fa6ff`. Machine-readable receipt: [junit.xml](junit.xml).

This run used real local PostgreSQL at `127.0.0.1:63119/proofkey`, with each database fixture creating a unique schema and cleaning it up. Model and media transports were injected fixtures; loopback HTTP was used for route checks. Provider credential variables were removed for the command. No paid/live provider call was made and no application code was changed.

| Area | Tests | Evidence checked |
|---|---:|---|
| Platform store, HTTP, model bridge, media | 75 | Immutable history; revision/hash binding; stale/superseded action rejection; operator consent; private case-bound assets; atomic booking/receipt rollback; concurrent execution replay; model admission lock against concurrent append; injected media processing, expiry and no redispatch |
| Durable analysis jobs and model service | 31 | Atomic budget reservations; body-bound idempotency; distinct concurrent claims; dispatch token ownership; response persistence; expired dispatched jobs become unknown; parse-only recovery; lost acknowledgement replay without credentials |
| Channels | 102 | Typed envelopes and routing; bounded quarantine; origin/header boundaries; one receipt/event for parallel duplicate delivery; atomic multievent/asset/outbox promotion; rollback on partial promotion; retained source hash checks |
| E2E cases/checks/runner/recovery | 99 | Sixteen legacy cutoffs; wrong input/evidence/target and premature completion rejected; immutable job replay; strict dispatch count; source tampering rejected; queue reconstruction and durable-response recovery; no retry after dispatched unknown outcome |

## State-integrity findings

No confirmed regression was found. `PlatformStore.admit_model` holds the canonical case transaction across job admission and rejects changed revision/hash. The race test verifies a concurrent append waits for admission to commit, and a new stale submission queues no job. Historical model replay is body/snapshot-bound and repairs a missing link using the existing job.

The supported booking execution remains explicitly `postgres_sandbox`: its receipt records `sandbox_effects=1`, `external_effects=0`, and says no carrier was contacted. The transaction tests insert an intentional receipt failure and verify zero bookings, actions and execution-request receipts before retry; four concurrent executions produce one booking. Unsupported/refund/unsafe actions remain blocked; stale or superseded approvals cannot execute.

Model/media unknown outcomes remain unknown. Expired dispatched jobs do not redispatch; a stored response is parsed without another transport call. Expired media results cannot be overwritten by late success. Channel promotion rollback keeps partial events/assets/outbox entries from surviving a failed batch, and identical concurrent redelivery resolves to one receipt and event.

## Scope and limits

This is backend evidence for local PostgreSQL transactions and loopback routes. Runner HTTP-double tests are transport-contract checks, not a live provider experiment. Recovery tests reconstruct runtime objects and inject lease expiry; they do not prove literal machine-crash behavior or third-party billing/delivery guarantees. No customer identity verification, carrier execution, paid model quality, or production readiness is inferred. Root owns real-model verification and broader browser flows.

## Reproduction

Run from the repository root, using the isolated local test database:

```sh
env -u OPENAI_API_KEY -u ANTHROPIC_API_KEY -u GEMINI_API_KEY -u ANTHROPIC_WORKSPACE_ID \
  PROOFKEY_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:63119/proofkey \
  PYTHONPATH=.:tools:runtime/src:runtime/tests \
  /tmp/proofkey-postgres-tests-20261010/bin/python -m pytest \
  tools/dwelly_platform/tests tools/dwelly_analysis/tests/test_jobs.py \
  tools/dwelly_analysis/tests/test_model_service.py tools/dwelly_channels/tests \
  tools/dwelly_e2e/tests --import-mode=importlib -q \
  --junitxml=docs/verification/platform-live-e2e-2026-10-10/backend/junit.xml
```
