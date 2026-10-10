# Coordination Review UI Implementation Plan

**Goal:** Connect the persisted terms workflow to model-assisted Team review and a complete mobile customer preview.
**Spec:** openspec/specs/coordination-review-ui/spec.md (change archived at openspec/changes/archive/2026-10-10-coordination-review-ui)
**Architecture:** Extend the existing local coordination aggregate, keeping generic model candidates advisory. No automatic command construction from prose. PostgreSQL is the transactional authority; HTML/JS are projections.
**Global constraints:** English states; no paid provider calls; no real external effects; preserve dirty provider changes; preserve existing non-coordination UI. No implicit push/deployment.

## Task 1 — Backend (parallel)
Own tools/dwelly_platform/coordination.py and new tests/test_coordination_review.py (do not change existing tests owned elsewhere).
- Write failing PostgreSQL tests before production changes.
- Add optional paired model_run_id/model_review_note, only on commands other than initialize/record_local_acceptance. Callback signature coordination_command(case_id,key,body,model_resolver=None). Resolve after replay and optimistic checks, inside transaction.
- Validate succeeded exact case/revision/snapshot and frozen input binding; no reference labels; candidate schema/evidence; selected evidence must be a subset of model evidence when attached. Persist compact provenance in audit under model_context. Keep existing evidence gates independent.
- Add record_local_acceptance {offer_id,terms_hash,acknowledged:true}, only awaiting_consent. Append explicitly labelled simulated customer evidence then normal consent audit in one transaction. consent.created_revision must match final audit revision. Replays must not append again; changed offer/snapshot rejected atomically.
- Model context failure codes invalid_model_context (400), model_context_unavailable/model_context_stale (409).

## Task 2 — Team UI (parallel)
Own platform-ui/app.js,index.html,product.js and new coordination.js,coordination-panel.js,coordination.css and named coordination frontend tests. Do not edit session.js, customer files, server.py or existing unrelated tests.
- Reuse createAPI and PlatformSession.mutate. Add card that fits current forest/neutral design. A pure helper projects phases/terms; dedicated controller handles full command form, explicit review checkbox, source evidence and optional current succeeded model run + human review note.
- Every command uses current snapshot and workflow version. Submission disabled during flight; preserve exact failed request/key for uncertain replay rather than silently rebasing. Show structured terms, offer ID/hash, pending request, consent freshness, local receipts and no-delivery warning.
- Do not offer record_local_acceptance in Team: sourced record_consent remains available. Render all eight existing commands phase-appropriately. New case form supports optional declared dispatch ID; never invent participant for existing cases.
- Current succeeded model candidate may prepare review context only; operator still chooses command and fields.
- Keep all textContent-safe and read-only render. Include pure and browser tests where feasible; tell controller new static files/fixture maps needed.

## Task 3 — Customer UI (parallel)
Own platform-ui/customer.js,customer-model.js,customer.html,customer.css and new customer-coordination.js and named customer coordination tests. No Team/shared/server edits.
- Cases with coordination use a separate branch/session, leaving legacy decisions unchanged.
- Display full current offer, attendance requirement (not observed presence), handover, price/currency, freshness, recorded consent, pending/local booking and physical-not-confirmed state.
- Explicit acknowledgement records record_local_acceptance via existing createAPI. Explain this is an operator-assisted local preview, not authenticated customer identity. Preserve frozen payload/key on uncertain retry, re-fetch after success, fail stale safely.
- No writes from rendering/load. Escape data. Mobile 390px no overflow; reuse existing design.

## Task 4 — Controller integration and review
Own server.py, new HTTP tests, docs/specs and integration verification. Expose new command/callback/errors/assets. Verify real HTTP route with a controlled model transport, not paid inference. Test stale/current proposals, read-only UI, atomic acceptance, no premature booking, correlated final readback, idempotency and rollback. Run all scoped backend and frontend tests, inspect actual browser screenshots, commission independent review. Archive OpenSpec after completion; commit only owned task changes.

## Completed verification

All four tasks completed. Final backend regression: 353 passed, 344 subtests; final frontend regression: 91 passed, zero skipped. Independent review approved after source-binding, retry/readback, refresh and single-connection pool fixes. Clean real UI/HTTP/PostgreSQL run: two fresh synthetic cases, 13 UI commands covering all nine command types, 51 checks/fixture writes and nine screenshots. Details: docs/verification/coordination-review-ui-2026-10-10/README.md. No paid inference, carrier effects, push or cloud deployment performed.
