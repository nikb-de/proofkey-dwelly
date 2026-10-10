# Unified case platform: local integrated vertical slice

## Intent and scope
The user prioritizes integration, adaptation and reliable case handling, and has explicitly requested autonomous parallel implementation. This is the first integrated platform slice, not a production-readiness claim. Existing runtime and evaluation tools remain available; no secrets, cloud settings or public branches are changed.

## Choice
Extend the current Python/PostgreSQL system with a small same-origin BFF and a no-build product UI. A wholesale SPA rewrite adds build/deployment work without improving case semantics; extending only the eval screen perpetuates the scope error. Use the existing Right onTime colors/layout as the visual basis, but not its localStorage simulator state.

## Data and boundaries
- Preserve `dwelly-local-case-v1` verbatim. Add tables in its configured schema for decisions, reviews, actions, private asset bytes and model-job links, using a separate migration marker.
- `PlatformStore(PostgresCaseStore)` inherits canonical create/append/get. Platform writes use the same database advisory lock and transaction, validating current revision/hash inside the lock.
- Decisions are append-only JSON records with `decision_id`, `case_id`, `revision`, `snapshot_hash`, `kind` (`deterministic`, `operator`, `model`), `action`, `checks`, `evidence_event_ids`, `created_at`. Action objects use `type`, and optional reschedule `slot_start`, `slot_end`, `address_change`.
- Reviews are immutable, generated from the trusted local operator identity rather than the claimed event sender. Approval is a local human attestation, not verification of a real customer's identity.
- Sandbox reschedules are committed atomically with their receipt in PostgreSQL, not sent to any real carrier. Separate `sandbox_effects` from `external_effects: 0`. Existing complex runtime adapters remain disconnected and are shown as such.
- Private PNG/JPEG (10 MiB) and supported audio (25 MiB) bytes are stored as bounded BYTEA in this local slice; 100 MiB/case cap. This deliberately avoids a nontransactional filesystem/DB split. Production object storage and tenant authentication are a later deployment prerequisite.
- Model jobs reuse existing budget/idempotency/fencing implementation with an evidence-only snapshot projection and `reference: null`; evaluation is null, not a manufactured gold label. Model proposals never become execution permissions.

## Local API v1
All state-changing JSON requests require `X-ProofKey-Request: platform-v1` and `Idempotency-Key`. Same-origin checks and strict loopback Host prevent cross-site requests. No arbitrary CORS. All responses use `Cache-Control: no-store`.

| Route | Request / result |
|---|---|
| GET `/api/platform/cases` | `{cases:[detail-summary]}` |
| POST `/api/platform/cases` | exact canonical declaration; `{case:detail}` |
| GET `/api/platform/cases/{id}` | detail with snapshot, states, decisions, reviews, actions, assets, model_jobs |
| POST `/api/platform/cases/{id}/events` | canonical `{expected_revision,event}`; updated detail |
| POST `/api/platform/cases/{id}/decisions` | `{expected_revision,snapshot_hash,action,evidence_event_ids}`; operator proposal |
| POST `/api/platform/cases/{id}/analyze` | `{expected_revision,snapshot_hash,mode:'deterministic'}`; deterministic decision |
| POST `/api/platform/cases/{id}/reviews` | `{decision_id,verdict:'approve'|'reject',note,customer_consent_confirmed:boolean}` |
| POST `/api/platform/cases/{id}/execute` | `{decision_id}`; same decision replay returns original receipt |
| POST `/api/platform/cases/{id}/assets` | raw bytes, Content-Type and X-Filename; returns canonical media descriptor |
| GET `/api/platform/cases/{id}/assets/{asset_id}` | private bytes, nosniff, safe disposition |
| POST `/api/platform/cases/{id}/model-runs` | `{expected_revision,snapshot_hash,model_profile_id}`; existing model job envelope |
| GET `/api/platform/model-runs/{id}` | existing model envelope |
| GET `/api/platform/capabilities` | origin mode, provider availability, six adapter surfaces and honest status |

Case detail schema: `{schema_version:'proofkey-platform-case-v1',case_id,snapshot,states,decisions,reviews,actions,assets,model_jobs,external_effects:0}`. States include lifecycle (`new`, `awaiting_information`, `in_review`, `awaiting_approval`, `ready`, `resolved`, `escalated`), evidence (`empty`, `text_available`, `media_unprocessed`, `mixed`), analysis (`not_started`, `current`, `stale`, `running`, `failed`, `outcome_unknown`), decision (`none`, `proposed`, `blocked`, `approved`, `rejected`, `superseded`), action (`none`, `verified`). Projection never rewrites history.

## Deterministic policy
Empty cases request information. Evidence-bearing cases require operator review unless a bounded operator reschedule proposal is supplied. Reschedule checks require referenced evidence IDs, explicit `address_change:false`, timezone-aware future timestamps, end after start and duration at most 8 hours. Approval of a reschedule requires consent attestation. Unknown/refund/return actions cannot execute. All admission and action replay checks are in the database transaction.

## Verification and non-goals
Test canonical revision conflicts, stale approvals, concurrent duplicate execution, cross-case assets/model jobs, unsafe MIME, HTML-like text, unavailable models, source-only prompts, explicit missing reference, browser refresh and full create/evidence/decision/review/sandbox path. No real booking, financial movement, calibrated model accuracy, GCS, tenant authentication or Cloud Run rollout is claimed.

## User extension: photo analysis and ASR
After upload, separate controls explicitly request `image_analysis` or `asr` at `/api/platform/cases/{id}/assets/{asset_id}/process`. A separate processing table stores source hash, mode, status, validation and immutable result plus provider receipt. Processing does not mutate source events or confer authority; extracted content requires human review. Pillow validates image decode and a 16-megapixel limit; audio inspection is time-bounded with a 600-second limit. Missing validation dependency or provider is fail-closed. Network ambiguity is outcome_unknown without automatic replay; abandoned running media records expire conservatively after 300 seconds and late publication is fenced. Local server media execution requires separate `--allow-media` opt-in and configured provider key; no paid call is executed during verification. A conservative reservation of the full USD25 model/experiment cap admits at most one new media request for each model and experiment scope until an explicit accounting policy is added. The CLI shares the text model budget ledger with media so model overlap cannot reset that cap. Synthetic image generation is a separate evals concern, not offered as operational evidence.
