# PostgreSQL backend and dataset compatibility

## What is implemented

The separate case API stores cases, canonical immutable revisions, request idempotency and a transactional analysis outbox in PostgreSQL. Local development uses PostgreSQL in Docker; Cloud SQL for PostgreSQL is the chosen deployment target, **not a deployed service**. Start with [the runnable setup](../../deploy/postgres/README.md).

```text
Trusted client -> Case API -> PostgreSQL transaction
                              + case head
                              + immutable snapshot
                              + idempotency record
                              + pending analysis intent

Pinned revision -> dataset export -> model-visible JSON
Pending intent  - - > future revision-analysis worker
```

Each new revision and its intent commit together or neither commits. Exact retries return the original revision without another intent. The v1 capacity limits remain 256 cases and 128 events per case. Write transactions currently serialize per schema using a database advisory lock: safe for the bounded team pilot, not a high-throughput claim. Each process defaults to a four-connection pool.

## API

| Route | Result |
|---|---|
| `GET /healthz` | Process liveness; no credentials required |
| `GET /readyz` | Storage readiness; no credentials required |
| `GET /v1/capabilities` | Explicit implemented/disabled features |
| `POST /v1/cases` | Existing v1 declaration; requires `Idempotency-Key` |
| `POST /v1/cases/{id}/events` | Existing v1 append request and expected revision |
| `GET /v1/cases/{id}?revision=N` | Exact immutable snapshot; omission reads current head |
| `GET /v1/cases/{id}/analysis-jobs` | Safe metadata only: no lease secrets or model results |

All application routes require an operator bearer token and exact allowed Host authority. Requests with any browser Origin are rejected. A token does not implement multi-user ownership or tenant authorization. The UI therefore still needs its authenticated BFF; do not put this token into browser code.

Outbox states are `pending -> leased -> completed`; expired leases can be reclaimed. Completion requires the current unexpired token. These are **delivery-of-work states**, not proof that analysis ran or a business outcome happened. No worker is connected yet. Canonical snapshot fields remain `pending_not_started`, `authorization=unverified`, `operational_effects=0`.

## What changes for training and evals

| Layer | Migration impact |
|---|---|
| Team-authored JSON/JSONL and annotation schemas | Unchanged; do not relabel existing examples |
| Source read/export | New PostgreSQL adapter; explicitly pin case ID, revision and expected snapshot hash |
| Model-visible input | Same `proofkey-decision-input-v1`, without labels, criteria or outbox metadata |
| Semantic expected outcomes / judge rubrics | Still reviewed separately; a storage migration provides no new ground truth |
| Integration/replay tests | Exercise PostgreSQL transactions, retries, lease expiry and crash/restart |
| Online worker and model runner | Not connected by this increment; old benchmark input format is not silently converted |

[`dataset_export.py`](../../tools/dwelly_service/dataset_export.py) provides a backend-neutral `export_decision_input()` adapter and a PostgreSQL CLI. It requires an explicit source revision and expected hash; a newly arrived message cannot silently change that input. It rejects included events later than `as_of`. V1 does not record trusted `received_at`, so **this is not complete point-in-time observation proof**: a backdated late message still requires an independently frozen revision or source receipt. Provenance is caller-declared, not authenticated merely by export.

Use `python -m tools.dwelly_service.dataset_export --help` for exact flags. Credentials come from `PROOFKEY_DATABASE_URL`, never command arguments. Exports are private exclusive-create files; they are individual model inputs, not complete labelled dataset packages. Add labels/criteria and family-level splits through the existing [team dataset workflow](../../datasets/team-handoff-v1/README.md). No training, paid model call, or judge assessment occurs during export.

### Remaining evaluation-tooling work

The new source adapter is not a completed training/evaluation pipeline. Before evaluating the connected worker, add a runner that consumes these frozen inputs and records the input hash, code/pipeline version, model/prompt configuration and database migration version in a separate run artifact. Keep infrastructure results (retries, leases, restart recovery) separate from semantic results (correct action, evidence, authority and non-fabrication). Identical input bytes establish adapter parity, not identical nondeterministic model answers or correct decisions.

The team can continue authoring the existing JSON/JSONL fixtures and labels now. No fine-tuning job, online data collection, labelled bulk export or Cloud SQL E2E run is implemented by this change. If the case state machine, evidence representation or permission semantics change later, revise and version those contracts explicitly; do not call that a transparent database migration.

## What stays separate

- Legacy SQLite benchmark queue, budget ledger and file artifacts: retained untouched, local-only.
- Browser IndexedDB: local drafts and bytes, not the shared source of truth.
- Real photo/audio storage and processing: not implemented here; event media fields remain metadata.
- Action permissions, live courier integrations and payout/refund execution: not enabled.
- Cloud Run/Cloud SQL provisioning, IAM/BFF, managed ingress, backup/restore and production monitoring: not deployed. The managed-cloud execution guard remains in place.

## Verification

See [store verification](../verification/postgres-store-report.md), [deployment verification](../verification/postgres-deploy-report.md), [dataset boundary review](../verification/postgres-dataset-contract-review.md), and [export verification](../verification/postgres-export-report.md). These distinguish PostgreSQL behavior and structural compatibility from real-world decision quality.
