## Context

Status: proposed design, not implementation. Source review: 2026-10-10, starting commit `3b4ef53`.

| Current component | Observed boundary |
| --- | --- |
| Model service | Calls the model runner; returns `proposed_unsent` contact drafts, not runtime operations. |
| Workflow engine | Stores an optional planner but does not invoke it; builds operations deterministically. |
| Runtime factory | Creates `SimulatedWorld`; supported registration and processing paths contain synthetic-only constraints. |
| Six adapter surfaces | Typed protocols plus simulator implementations, not native API integrations. |
| Media | Model service sends metadata only; separate runtime contains partial synthetic processing contracts. |
| Evaluation data | Imported 50-case manifest has six attachments, zero visible at the frozen cutoff and no audio. |

Evidence: `tools/dwelly_model/semantic.py`, `tools/dwelly_service/worker.py`, `runtime/src/proofkey/{engine,host,ports}.py`, `runtime/src/proofkey/processing_orchestration.py`, and `outputs/dwelly-intake-2026-10-10-final/manifest.json`.

## Goals / Non-Goals

**This increment:** establish a trustworthy model-to-runtime identity/evidence boundary and an executable no-effects shadow path.

**Not this increment:** actual runtime planner invocation, native connector qualification, image/ASR calls, automatic refunds, cloud deployment, or proof of business correctness. A recorded shadow draft is not an actionable runtime plan.

## Decisions

### 1. Preserve the contact draft; do not cast it into an operation

Use an optional companion CLI/package that reads completed, bounded artifacts. Its record binds source job/case, snapshot hash, proposal hash, receipt hash, processing provenance and a trusted host-supplied runtime identity/checkpoint. Return `shadow_recorded`, `unmapped` or `rejected`, with stable reasons. It creates no `EffectIntent` and calls no workflow/gateway/adapter.

This is preferable to inserting an automatic callback in the existing worker: contact kinds such as `request_customer_choice` are not the runtime operation `reschedule`, and a person's name in a conversation is not an authenticated principal. Event references are scoped by snapshot and case, not treated as runtime authority references.

Importing a previous live response is historical replay/readback, not a new runtime provider invocation. Preserve both original provenance and current import mode. A missing binding or receipt stays missing; do not manufacture one from narrative text.

Read source artifacts only from a configured service-owned root. Verify the job/spec, saved producer request, response receipt and parsed proposal link to one attempt and exact snapshot; a pile of independently valid hashes is insufficient. Offline baselines instead carry an explicit snapshot/version/proposal linkage with no invented provider receipt. An unsupported legacy artifact set is rejected until its producer linkage is established.

Resolve host identity through an injected, read-only host-owned resolver, not CLI-supplied mapping JSON. It checks caller scope and persisted case/object/principal/request, request/consent revisions, generation, checkpoint and profile/process/policy versions. Record the checked state and time. A later state change invalidates assumptions; even a successful association never grants dispatch authority. Until this resolver exists, report `unmapped`.

### 2. Deliver the operational connection in a separate, mandatory next milestone

After shadow identity is proven, specify a distinct typed runtime-planning output over a frozen evidence envelope and authoritative observations. Reuse bounded planner/receipt ideas, but introduce an explicit actual-processing admission path instead of relabelling existing synthetic paths. Add a policy-only preview before any effect path.

The model proposes the next step and identifies uncertainty. Deterministic code resolves allowed IDs/options and checks current identity, consent, ownership, revision, process state and limits. Missing facts lead to clarification or operator review. Human approval is an additional control, not a replacement for these checks. Only a later qualified sandbox path can create durable intent, dispatch and verify the original effect.

### 3. Develop three streams in parallel after the envelope contract is agreed

| Stream | First useful delivery | Acceptance gate |
| --- | --- | --- |
| Model/runtime | Shadow import, then typed proposal and policy preview for rescheduling and goods refusal | Exact source/binding lineage; incorrect or unknown authority cannot produce an executable action. |
| Native adapters | Read-only case/principal connector for one named system; then sandbox scheduling | Exact IDs/revisions, explicit capabilities, idempotency and original-effect lookup; no mixing real facts with simulated authority. |
| Media | Bounded PNG/JPEG vision extraction and a declared audio/ASR route | Real bytes produce cited claims/transcripts; unsupported, uncertain and failed inputs remain explicit. |

All six logical surfaces remain in the architecture. They need not be six vendors. Expand delivery, returns, messaging and operator connectors only once their concrete API and authority semantics are known. Sequential reads do not reproduce the simulator's atomic cross-authority conditional write; unsupported guarantees must block execution or require a reviewed narrower protocol.

### 4. Evidence extraction is not authority

Freeze source availability at the decision cutoff. Preserve original/derivative hashes, source event, transformations, extractor/model identity and receipt. Use real regions/timestamps or explicit unknown locators. Do not infer speaker identity, consent, delivery completion or ownership from a photo/transcript. External media processing requires approved data scope and budget; current text redaction is not image/audio sanitization.

Before reusing extraction publication, reconcile the current source-hash versus claim-hash mismatch: `providers/anthropic.py` hashes claim text into `EvidenceAssertion.content_hash`, while `evidence/catalog.py` requires the original artifact hash. Validate the whole extractor-to-publication path, not its units separately.

### 5. Cloud readiness is a separate deployment gate

Keep local development while specifying external durable job claims, budgets, evidence storage, secrets and authentication for cloud workers. Do not copy the current SQLite/flock service onto ephemeral cloud storage and declare it ready. Existing cloud configuration is an offline smoke template, not the operational service.

## Risks / Trade-offs

- Shadow import could be mistaken for operational integration → label its result non-executable and test zero effect calls.
- A connector can return data without proving permission or atomicity → qualify individual capabilities and keep unsupported operations disabled.
- Three models can agree on a wrong conclusion → deterministic safety tests plus independent human-reviewed semantic cases; judges are advisory.
- Existing public media arrives after the cutoff → add separately versioned authorized cases; do not move the cutoff to improve scores.

## Migration Plan

Add the bridge as opt-in with unchanged service behavior. Test synthetic fixtures and explicitly labelled replay without provider calls. Then review a separate typed-planner milestone. Removing/disabling the bridge leaves runtime state untouched. Archive this change only after its own implementation and verification, not merely after validating this document.

## Open Questions / Team Inputs

1. Name the first case-system provider and supply API documentation, redacted examples and sandbox scope; credentials go through the private secret store, never chat or Git.
2. Supply the exact rescheduling/refusal authority rules, escalation owner and approval limits. Refund/coverage decisions remain out of executable scope until separately specified.
3. Supply authorized media available at the decision point and human-reviewed expected behavior. Aim for 10–20 evaluation cases and 10–20 independent live-like cases, versioned separately from the already-seen 50 examples.
4. Choose media providers/formats/languages and approved external data scope before actual extraction calls; do not assume a subscription implies an API route.
5. Confirm cloud project/region and permitted resources before any deployment. None is required for the local shadow increment.
