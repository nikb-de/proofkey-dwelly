# Design

## Selected approach
Reuse existing non-retrying HTTPS provider transports, not the incompatible legacy benchmark runner. Use PostgreSQL for new analysis jobs and budgets, not the browser or another SQLite database. Preserve the existing offline `/api/runs` contract. A new `/api/model-runs` API carries asynchronous model work. These are model proposals, never operational instructions.

## Model boundary
Only `proofkey-step-input-v1` enters the prompt. The dedicated prompt treats transcript/goals/roles as untrusted evidence, not instructions or verified authorization. The model supplies exactly state, wait targets, proposed next action, evidence IDs and concise uncertainty; the host validates enums, IDs and consistency and supplies hashes, mode, provider identity and zero operational effects. A failed model call or invalid candidate never silently becomes a baseline result. Store received text and allowlisted metadata privately before local parsing; never send author references to providers.

## Durable lifecycle
`queued -> running -> response_received -> succeeded`; known errors become `failed`, dispatched requests with missing responses become `outcome_unknown`. Input, reference, source, profile and prompt identities are frozen at submission. Atomic store admission fingerprints the full initial specification. Client replay binds the same scope, case, step, input hash and profile ID to that original job, even after credential removal or server configuration change; a changed client selection conflicts. Reserve conservative cost in the same PostgreSQL transaction as creating the job; retain reservations on all outcomes. Buckets are scoped by experiment and provider/model, with a cap no larger than USD25. Price estimates are configured assumptions, not actual bills.

Claims have server-time leases and tokens. A dispatch marker is committed before the single HTTP invocation. Expired non-dispatched work may be reclaimed; expired dispatched work with no response must not call the provider again. Durable responses may resume local validation only. Response and final-result writes require the active unexpired token. Store result + terminal status atomically. Bound concurrent calls to three total and one per provider profile. Never claim exactly-once external execution.

## API and UI
`GET /api/model-profiles` returns only public model IDs, names and availability. `POST /api/model-runs` requires the existing same-origin write header plus `Idempotency-Key`, and body `{case_id,step_index,expected_input_hash,mode:"model",model_profile_id}`. New requests return202, identical replay200, conflict409, disabled/unavailable403/503, capacity/budget429. `GET /api/model-runs/{id}` returns `proofkey-model-job-v1` with run ID, status, frozen selection/input/reference/source, nullable candidate/comparison/receipt, timestamps, sanitized error and transaction metadata; no credentials, DSN or lease token.

The UI keeps offline selected by default, advertises enabled models, and shows durable job status separately from inferred candidate state. It polls the same accepted job, never resubmits on a polling error. An unacknowledged POST retry reuses its key. Case/step/profile changes invalidate stale responses without cancelling paid work. Show request/observed model, tokens, latency, reservation, attempt and idempotency IDs, and unknown outcome prominently. Never display missing usage as zero or label author agreement as model accuracy.

## Configuration and verification
Startup requires explicit `--allow-live`, a server-owned profile file, database URL via environment, schema and budget scope. Existing environment keys stay server-side. No credentials in browser/config/API receipts. Migrate only the explicitly configured analysis schema; do not modify cloud resources in this change. Offline startup needs no PostgreSQL or provider keys.

Tests cover label leakage, malformed output, unavailable profiles, concurrent duplicate submissions, budget races, crash before/after dispatch and after durable response, lease fencing, restart/readback, sanitized errors, stale UI polling and model details. Initial live smoke is one call per available configured provider on synthetic evidence; no automatic retry or expanded benchmark.
