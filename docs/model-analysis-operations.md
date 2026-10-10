# Model analysis operations

This workbench serves a loopback-only UI at `http://127.0.0.1:8093`. Model analysis uses PostgreSQL for jobs, reservations and receipts. The existing offline baseline remains available without PostgreSQL or provider credentials. Cloud deployment is deferred; this guide does not establish a deployed Cloud Run service.

Current handoff status: required local provider credentials are unavailable; live provider verification is **NOT_RUN**. Configured profiles or a running UI do not prove a successful provider call.

Verification receipts, reviewed fixes and remaining limits are in [the implementation verification](verification/transactional-model-analysis-2026-10-10.md). If a profile is removed entirely from configuration, recover its old job through `GET /api/model-runs/{run_id}`; the current UI only restores profiles still advertised by the service.

## Local startup

Use the repository's Python environment with its PostgreSQL dependencies installed. Start a local PostgreSQL database and prepare a trusted server-side model profile file, using [the example](../tools/dwelly_analysis/model-profiles.example.json) as its structure. Check model IDs, configured price assumptions, token limits and credentials before enabling paid requests.

The model flags below are implemented; inspect them with `python -m tools.dwelly_analysis serve --help`. Set `PROOFKEY_ANALYSIS_DATABASE_URL` through your trusted local secret loader; its value is a local PostgreSQL DSN. The command receives the database variable's name, never its value:

```sh
: "${PROOFKEY_ANALYSIS_DATABASE_URL:?Set a local PostgreSQL DSN in this environment}"
python -m tools.dwelly_analysis serve \
  --port 8093 \
  --runs-dir ./outputs/analysis-runs \
  --allow-live \
  --model-config ./tools/dwelly_analysis/model-profiles.example.json \
  --provider-env-file .env \
  --database-url-env PROOFKEY_ANALYSIS_DATABASE_URL \
  --database-schema proofkey_analysis \
  --budget-scope local-development-2026-10-10 \
  --migrate-model-jobs
```

`--allow-live` explicitly enables paid model work. `--model-config` selects trusted profiles; it is not an arbitrary browser input. `--database-schema` isolates model tables from the case-store schema. `--budget-scope` selects the persistent experiment budget: keep it unchanged on restart. Changing scope creates a separate allowance. `--migrate-model-jobs` explicitly applies the versioned model tables; after initial setup, omit it unless applying a reviewed migration. Offline run files use `--runs-dir`; model jobs live in PostgreSQL.

`--provider-env-file .env` reads four allowlisted names only: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `ANTHROPIC_WORKSPACE_ID`, and `GEMINI_API_KEY`. It parses assignments as data, never sources the file or executes shell substitutions. Other names are ignored; the database DSN must already be in the process environment. Existing environment values take precedence. Omit this option when a trusted launcher already supplies provider variables. Keep the optional file private and untracked.

Keep the profile file free of secret values. Its provider/model names, environment-variable names, profile IDs, limits and price assumptions are configuration. Never paste a DSN or key into browser fields, URL parameters, receipts, checked-in JSON or shell command arguments.

## Public API for clients

All routes are on the loopback origin. Writes require `Content-Type: application/json` and `X-ProofKey-Request: analysis-v1`; model submission additionally requires one `Idempotency-Key` header. Generate one key per intentional run and reuse it after an uncertain POST acknowledgement. There is no automatic retry endpoint.

| Route | Response |
|---|---|
| `GET /api/model-profiles` | `{enabled, profiles:[{id,label,provider,model,available,reason}]}`; no credentials or environment-variable names. |
| `GET /api/cases/{id}/steps/{index}` | `{input,reference,source}`; obtain the exact input hash here. |
| `POST /api/model-runs` | `202` for a new job, `200` for identical replay; returns the job envelope below. |
| `GET /api/model-runs/{run_id}` | `200` with the same envelope at its current durable state. Poll this accepted ID. |

The POST body accepts exactly these fields; the profile ID must come from the advertised profiles:

```json
{
  "case_id": "case-002",
  "step_index": 3,
  "expected_input_hash": "<64-character hash from the selected step>",
  "mode": "model",
  "model_profile_id": "openai-gpt-4-1-mini"
}
```

The following type notation lists the complete public envelope. `input`, `reference`, and `source` are frozen copies from the selected-step response; the reference remains unvalidated author data and is never sent to the model.

```ts
type ModelJob = {
  schema_version: "proofkey-model-job-v1";
  run_id: string;
  status: "queued" | "running" | "response_received" | "succeeded" | "failed" | "outcome_unknown";
  case_id: string; step_index: number; input_hash: string;
  mode: "model"; model_profile_id: string;
  input: object; reference: object;
  source: {source_sha256: string; source_commit: string; family_id: string; qualification: string};
  candidate: {
    schema_version: "proofkey-step-candidate-v1"; input_hash: string; mode: "model";
    state: "unknown" | "ready" | "acting" | "waiting" | "completed";
    waiting_for: string[];
    next_action: {type: "wait" | "request_information" | "request_readback" | "propose_forwarding" | "operator_review" | "none";
                  target_actor_id: string | null; description: string};
    evidence_event_ids: string[]; uncertainty: string[];
    live_calls: 1; operational_effects: 0; physical_delivery: "not_inferred";
  } | null;
  evaluation: {
    schema_version: "proofkey-step-comparison-v1"; input_hash: string;
    state_agreement: boolean; wait_target_agreement: boolean;
    qualification: "mechanical_comparison_only"; accuracy_score: null;
  } | null;
  receipt: {
    model_profile_id: string; provider: string; requested_model: string;
    observed_model: string | null; request_id: string | null; latency_ms: number;
    usage: {input_tokens: number | null; output_tokens: number | null};
  } | null;
  error: {phase: "dispatch" | "validation"; code: string} | null;
  created_at: string; started_at: string | null; finished_at: string | null;
  transaction: {
    idempotency_key: string; attempt_id: string; dispatch_attempts: 0 | 1;
    automatic_retries: 0; operational_effects: 0; reserved_usd: number;
    budget_scope: string; prompt_hash: string; profile_hash: string;
  };
};
```

Treat `candidate`, `evaluation`, and `receipt` as nullable, including on failure. Unknown model identity/usage stays `null`, not zero or an inferred value. `409` indicates a changed key/body, hash or budget policy; `429` indicates queue/budget exhaustion; `403` means model execution is disabled; `503` can indicate unavailable credentials or storage. Error bodies contain a bounded `error` code. A failed poll must not trigger another submission.

## Status and transaction guarantees

| Status | Meaning and recovery |
|---|---|
| `queued` | Job and conservative reservation committed; no dispatch yet. |
| `running` | Worker holds a database-time lease. The dispatch counter distinguishes claimed work from a request that may have been sent. |
| `response_received` | Provider response is durable; recovery may run local validation only. |
| `succeeded` | Validated candidate and terminal status committed together. This does not establish semantic correctness. |
| `failed` | Request or validation failed; receipt evidence and reservation remain. |
| `outcome_unknown` | A dispatched attempt lacks a durable response. Inspect it; no automatic resend occurs. |

Identical requests with the same idempotency key return one job; a changed request conflicts. Submission reserves budget in the same transaction as the job. Each experiment scope has a cap of at most USD25 **per provider/model**, shared by profile aliases. Reservations are retained after failure or uncertainty. They are conservative admission estimates, not provider billing caps or refunds.

An expired lease before dispatch permits reclaiming work. After the dispatch marker, missing response evidence becomes unknown. Current lease tokens fence response/result writes; terminal records cannot be overwritten through the API. The marker proves possible dispatch, not exactly-once provider execution. Do not automatically retry unknown outcomes or create a new key merely because polling failed.

The worker uses a **660-second lease**: the maximum configured transport timeout of 600 seconds plus a 60-second allowance, including for frozen jobs submitted under older configuration. There is no guaranteed wall-clock completion time: a socket timeout does not establish a total end-to-end deadline. Expired result writes are fenced, and the current store has no heartbeat interface. A candidate proposes analysis only: operational effects remain zero.

## Future Cloud Run and Secret Manager plan — not implemented

Before a cloud deployment, implement authenticated ingress/BFF, durable worker lifecycle, Cloud SQL connectivity, IAM, migrations and operational monitoring. The loopback UI is not a public service. Local PostgreSQL tests do not verify these cloud controls.

| Material | Local handling | Future cloud handling |
|---|---|---|
| Provider API-key values | Process environment or the restricted private provider file | Separate Secret Manager secrets. |
| Anthropic workspace value | `ANTHROPIC_WORKSPACE_ID` through the same private channel | Secret Manager if required by the profile. |
| Database password or authenticated DSN | Process environment named by `--database-url-env`; not loaded by `--provider-env-file` | Secret Manager, with a separate database access policy. |
| Provider/model/profile IDs, prices, limits, budget scope, environment-variable names | Reviewed configuration; these names are not credentials | Versioned deployment/profile configuration. |

Store provider API keys and database passwords or the complete sensitive DSN in Secret Manager. Attach a dedicated Cloud Run service identity; grant `roles/secretmanager.secretAccessor` on each required secret, not a blanket project grant. Use the attached identity rather than exporting a service-account key. Google documents the secret integration and secret-level access controls in [Configure secrets for services](https://docs.cloud.google.com/run/docs/configuring/services/secrets) and [Manage access to secrets](https://docs.cloud.google.com/secret-manager/docs/manage-access-to-secrets).

Map secrets into server-side environment variables named by the public configuration. Pin numeric secret versions for environment injection: Cloud Run resolves these values at instance startup. Rotate by selecting reviewed versions in a new revision. Pin the application image digest and profile/prompt version alongside that revision; record identifiers without exposing values. The service identity is distinct from the deployer's identity; see [Configure service identity](https://docs.cloud.google.com/run/docs/configuring/services/service-identity).

No Secret Manager resources, IAM grants, Cloud Run deployments or service-account keys are created by this change.
