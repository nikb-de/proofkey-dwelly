# Transactional Model Analysis Implementation Plan

> **For agentic workers:** Use Superpowers TDD and subagent-driven development. The user's explicit parallel/autonomous instruction overrides sequential implementation and repeated approval prompts. File ownership is disjoint; root integrates and independently reviews.

**Goal:** Run actual provider models from the existing analysis UI with durable PostgreSQL receipts and no duplicate automatic dispatch.
**Architecture:** Evidence projection -> atomic job/budget reservation -> leased single dispatch -> durable response -> strict local validation -> atomic terminal result -> polling UI. Offline v1 remains unchanged.
**Tech Stack:** Existing Python/psycopg stack, existing provider transports, vanilla JS and Node/browser tests.
**Spec:** `openspec/changes/archive/2026-10-10-transactional-model-analysis/design.md`.

## Global Constraints
- Preserve raw data and existing contracts; no author references in model prompts.
- No business effects, automatic retries, cloud deployment or key exposure.
- PostgreSQL for model jobs. Explicit startup opt-in. Maximum USD25 per provider/model per configured experiment scope; retained conservative reservations, not provider billing caps.
- Preserve user-owned untracked `docs/dataset-drafts/`. No main merge or force-push.
- Root uses Python `/tmp/proofkey-postgres-tests-20261010/bin/python` with local test DSN `postgresql://postgres@127.0.0.1:63119/proofkey` for PostgreSQL tests.

## Review Focus
- Two concurrent identical submissions must reserve and dispatch once.
- A crash after dispatch cannot cause an automatic provider retry.
- A durable response can be reparsed after restart without another call.
- Stale browser POST/poll results cannot overwrite new case/step/profile.
- Invalid model output must retain failure/receipt evidence without inventing success.

### Task 1: Dedicated model adapter
**Owner:** model implementer. **Files:** `tools/dwelly_analysis/model.py`, `model-profiles.example.json`, `tests/test_model.py`.
**Interfaces:** `load_profiles(path)` -> dict `{profiles:[{id,label,config}],budget_per_model_usd,max_output_tokens,timeout_seconds}`; `public_profiles(settings)` -> list of `{id,label,provider,model,available,reason}`; `prepare(input)` -> `(system,prompt)`; `request(input,profile,max_output_tokens,timeout)` -> allowlisted response dict containing text/provider/requested_model/observed_model/usage/request_id/latency_ms (no raw_response); `parse(input,response)` -> candidate with host-owned schema/hash/mode/counters; `receipt(response,profile)` -> allowlisted metadata; `reservation(input,profile,max_output_tokens)` -> positive Decimal estimate using UTF-8 byte upper bound plus512 framing tokens and configured prices.
- [x] Add failing tests for unknown IDs, extra output fields, waiting/completed consistency, quoted JSON, invalid evidence, profile validation, unavailable credentials and captured prompt sentinel exclusion.
- [x] Implement strict profile validation, a bounded evidence-only JSON prompt and exact candidate fields. Reuse `providers.complete`; no retries or references. Candidate next action types: `wait`, `request_information`, `request_readback`, `propose_forwarding`, `operator_review`, `none`. Completed requires `none`, null target, empty waiting; unknown requires operator_review; waiting requires wait plus visible targets. Require cited visible evidence for non-unknown state. Do not assert semantic correctness from schema validity.
- [x] Fresh tests and report red/green evidence; no live calls or edits outside owned files.

### Task 2: PostgreSQL model job store
**Owner:** transaction implementer. **Files:** `tools/dwelly_analysis/jobs.py`, `migrations/001_model_jobs.sql`, `tests/test_jobs.py`.
**Interfaces:** `migrate(dsn,schema="proofkey_analysis")`; `AnalysisJobStore(dsn,schema="proofkey_analysis")`; `submit(key,spec,reservation,cap,scope)` -> `(row,created)`; `get(job_id)` -> internal row; `claim_next(lease_seconds=120,max_running=3,per_profile=1)` -> row orNone; `mark_dispatched(job_id,token)` -> bool; `record_response(job_id,token,response)` -> bool; `finish(job_id,token,result=None,error=None,status="succeeded")` -> bool; `recover_expired()`; `close()`.
**Rows:** job_id, spec, status, lease_token (internal only), attempt_id, dispatch_attempts, response, result, error, created_at, started_at, finished_at, reserved_usd. Spec includes input,reference,source,profile,settings,profile_hash,prompt_hash,budget_key (provider:model). Use states queued/running/response_received/succeeded/failed/outcome_unknown. Cap bucket key is scope+budget_key, not client profile alias.
- [x] Add failing real-PostgreSQL tests in unique temporary schemas for atomic deduplication/conflict, budget exhaustion/race, distinct claims/concurrency cap, token fencing, expiry before and after dispatch, response recovery, terminal immutability and reopen/readback.
- [x] Implement explicit migration and transactions using database time. Do not reuse incompatible benchmark tables. Preserve reservations on all outcomes; fail closed on cap changes. Enforce<=25 cap and bounded positive reservations. Claim response_received jobs for local parse only; dispatched missing response becomes outcome_unknown.
- [x] Record test results; no cloud access, no provider calls, no edits outside owned files.

### Task 3: Model UI
**Owner:** UI implementer. **Files:** `case-state-widget/analysis.{html,css,js}`, `tests/model-ui.test.mjs`, `tests/model-browser-qa.mjs`; preserve old tests.
**API:** GET `/api/model-profiles` -> `{enabled,profiles:[{id,label,provider,model,available,reason}]}`. POST `/api/model-runs` body exact `{case_id,step_index,expected_input_hash,mode:"model",model_profile_id}` and headers `X-ProofKey-Request:analysis-v1`, `Idempotency-Key:<uuid>` ->202 new/200 replay. GET `/api/model-runs/{id}` ->public job.
**Public job:** schema_version proofkey-model-job-v1, run_id,status,case_id,step_index,input_hash,mode model,model_profile_id,input,reference,source,candidate/evaluation nullable,receipt nullable,error nullable,created_at,started_at,finished_at,transaction `{idempotency_key,attempt_id,dispatch_attempts,automatic_retries:0,operational_effects:0,reserved_usd,budget_scope,prompt_hash,profile_hash}`. Status response_received is nonterminal; terminal succeeded/failed/outcome_unknown.
- [x] Add failing tests for profile switching, accepted job polling, stale poll/POST/error, same-key retry after lost POST acknowledgment, retained job on polling failure, nullable failed result and model identity mismatch rejection.
- [x] Add offline-default selector, explicit model action, durable lifecycle and compact transaction details. Reconnect polls accepted run; unknown outcome never auto-resubmits. Generate a new key for an intentional new run only. Preserve offline API tests and source/reference separation.
- [x] Run Node tests; browser harness must mock only provider/network lifecycle when testing UI, label simulated receipts and never claim live verification from mocks.

### Task 4: Root service/worker integration and delivery
**Owner:** coordinator. **Files:** `tools/dwelly_analysis/{server,__main__,worker}.py`, `tests/test_model_service.py`, docs and spec.
- [x] Write failing tests for disabled-by-default model endpoints, trusted profiles only, exact request/key/hash validation, worker success/failure/response recovery and no provider resend after dispatch.
- [x] Wire new routes and public job projection without changing offline routes. Worker persists response before parse, then stores candidate/comparison atomically. Bound3 threads, preserve unknown outcomes and sanitized failures. Startup options `--allow-live --model-config PATH --database-url-env NAME --database-schema NAME --budget-scope NAME --migrate-model-jobs`; existing offline flags unchanged. DB URL and keys remain environment-only.
- [x] Load only explicitly trusted private provider env assignments for local canary launch without echoing values; do not execute env files as shell code. Credential preflight found no available provider, so real canaries were NOT_RUN and remain deferred until keys are supplied. No provider identity, charge or semantic outcome is claimed.
- [x] Independently review actual diff, run combined Python/Node/real browser QA, record exact results and limits, update team docs, archive OpenSpec, commit. Keep cloud deployment separate.

## Completion evidence
Implementation and independent review completed locally. See `docs/verification/transactional-model-analysis-2026-10-10.md`: 492 Python tests, 42 JavaScript tests, real UI/API/PostgreSQL fixture, and explicitly simulated provider transport. Cloud deployment and real provider validation remain outside this completed implementation slice.
