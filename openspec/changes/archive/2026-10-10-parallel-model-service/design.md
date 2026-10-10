## Context and approved scope

User approved parallel service implementation and preparation for Google Cloud on 2026-10-10. Existing `tools/dwelly_model` emits unsent contact proposals; `runtime/` is a separate local operational harness. This change connects neither to real business effects. Existing linked worktree: `codex/proofkey-runtime`.

## Decisions

1. Keep a single coordinator as owner of file writes, reservations and result aggregation. Only immutable provider calls execute in a bounded thread pool. Validate global concurrency 1..16 and per-provider concurrency 1..8; defaults remain serial for direct callers, service uses 4/2. Stable task order determines admission, not response arrival.
2. Preserve all-proposals-frozen before any reference access in evaluation mode. Proposal-only mode never opens evaluation files, never calls judges, and is the default service workflow. Evaluations are explicit jobs, not a prerequisite for returning a proposal.
3. Add cooperative cancellation. Stop new admissions, drain in-flight HTTP calls, retain reservations, persist received results and terminal cancelled status. No automatic retry, no assertion that cancellation revoked an already sent call.
4. Share a BudgetLedger path across local service jobs. Prefix ledger request identities by an experiment namespace; identical provider/model seats share one cap across submissions and restarts. Experiment receipts remain local to their output. Changed caps fail closed. This is configured conservative admission, not provider billing enforcement.
5. A single-operator local service uses authenticated HTTP and SQLite with one active job at a time; concurrency is inside each job. Commit idempotent submissions before acknowledging; use only server-fixed bundle/config paths, no client-supplied paths or secrets. State lives on a persistent POSIX directory. A process lock excludes competing service owners. Current startup must explicitly enable live execution before any queued live job is claimed; otherwise it stays queued and does not block eligible offline work.
6. On restart, queued jobs remain runnable. Previously running jobs reconcile terminal evidence or become interrupted, never automatically replaying paid calls. Cancellation does not equate to refund. Polling returns progress counts and sanitized errors, not raw provider payloads. Authenticated proposal readback exposes bounded validated unsent drafts in stable case order; incomplete files are not exposed. Limit pending jobs to 256, preserve idempotent reads at capacity, and surface a failed worker as unhealthy rather than accepting unserviceable work.
7. Cloud preparation targets Cloud Run Jobs, not an ephemeral HTTP queue. Deployment template is offline-only with one task, no retries, explicit resource/time bounds. Local service refuses managed Cloud Run environments. Live cloud execution is unavailable until externally durable budget/dispatch claims and artifacts are implemented and verified. No resources are created now.

## Boundaries

Deterministic: ingestion, snapshot boundary, hashing, queue, admission, schema checks, permission policies, reconciliation and reporting. Nondeterministic: interpretation and proposed contact/action text; judge assessments. Business dispatch remains outside this service. Six local simulated adapter surfaces are not six production integrations.

## Risks and verification

Use event-controlled fake transports for overlap/barrier/cancellation tests, real local HTTP/SQLite for API and recovery tests, and network-disabled Docker smoke runs. Preserve existing 60 model tests and 58 case tests. Do not start the unrelated long-running runtime suite again. Cloud documentation must distinguish prepared, locally tested, deployed and provider-verified states.

## Deferred work

External cloud transactional job/budget storage, GCS artifact lifecycle, IAM integration, provider rate-limit adaptation, multi-tenant identity, real operational adapters, human authorization UI, calibrated semantic improvements and LLM-to-runtime action mapping are separate changes.
