# Task12B4c — Same-parent engine injection and status/debt summary

This is the binding successor contract after independent12B4a and12B4b Spec/Quality approval. Preparation is not implementation GO. Existing richer current-output-reference summary remains a separate missing gate; this stage supplies only authenticated status/debt and actual last-entry notes.

## Exact ownership

The implementer owns only:

- Existing `runtime/src/proofkey/engine.py`.
- NEW `runtime/src/proofkey/processing_summary.py`.
- NEW `runtime/tests/test_engine_processing.py`.
- NEW `runtime/tests/test_processing_summary.py`.

No gateway/journal/catalog/planner/B4b/contract/helper/profile/fixture/old-test edits. Root owns formal/plan/ledger and commits. Same original author owns any correction; a different nonauthor supplies separate Spec and Quality gates. WholeTask12, fresh text/media engine integration, live providers and readiness are not implied.

## Same fixed public parent, not a new gateway

Preserve every existing WorkflowEngine constructor argument/default and add keyword-only `processing=None`. Non-None must have exact ProcessingOrchestrator type. When gateway is omitted, select the SAME already constructed `processing.parent_gateway`; when supplied, require object identity with that parent. Do not construct a replacement gateway or service.

Before any SQLite/source entry, verify public `processing.store is store`, `processing.clock is clock`, `processing.catalog is evidence`, and parent store/clock/profile semantic equality/bundle identity. Recheck these fixed associations at public entry. Expose read-only `engine.processing`; engine/gateway/consumer remain creator-thread and nonreentrant. No duck typing, provider callback, new execution scope, changed captured_at/monotonic anchor or private consumer/service entry methods.

Trusted host explicitly constructs `ActionGateway(..., processing_allowances=recipe.allowances)` before consumer/engine composition. There is no public allowance getter: do not inspect/change private gateway allowances or add an API to force equality. Misconfigured host allowances deny through actual reservation rather than being repaired/funded. Original journal-admitted balances, shared debts and structured max_planner_calls=0 stay authoritative. Newer/larger recipes never upgrade an already admitted case.

Preserve existing planner/evidence parameters' current meaning. An empty immutable planning-registration tuple is a lawful composition configuration, not an invocation grant. It still obeys the approved B4b recipe rule requiring an enabled planning role: fixtures explicitly configure that role beside extraction. This configuration neither creates a campaign nor overrides the structured case's original max_planner_calls=0.

## Structured positive versus missing text gate

With the injected consumer, an actual structured-only reschedule still follows source-derived deterministic proposal and existing gateway policy/authorization/postcondition gates. It creates no processing ID, invocation, model receipt or planner debit. Original source slot/window/capacity/status/inventory/destination, consent, ownership, stop, migration and effect predicates still govern.

Narrative/evidence input remains explicitly unavailable in fresh run/recover/reply. This stage does NOT automatically call `plan_prepared`, create/register a campaign, rebuild an evidence checkpoint, substitute a prepared fixture, infer permission from membership, or widen permit hashes. The independently approved B4b prepared component positive is not a later fresh engine.run content positive: subsequent authentication/material accounting changes the envelope/checkpoint. A separately specified preparation/continuation or prospective-manifest boundary is still required.

## Closed pure summary projections

NEW companion exports frozen, slotted classes with these exact fields; reject mutable aliases and unknown fields:

```python
ProcessingAttemptSummaryV1(
    invocation_id: str,
    role: extraction | transcription | planning,
    reservation_status: consumed | completed | failed | outcome_unknown,
    receipt_status: completed | failed | outcome_unknown | unavailable | None,
    mode: intake_only | deterministic | recorded_replay | replay |
          synthetic | actual | unavailable | None,
    reserved_usage: tuple[tuple[str, float], ...],
    worst_case_cost: float,
    case_debit: int, role_debit: int, campaign_debit: int)

ProcessingEntryNoteV1(
    kind: unavailable | recorded_replay,
    reason: input_unavailable | permit_unavailable | processing_interrupted |
            output_rejected | publication_unavailable | None)

ProcessingSummaryV1(
    binding_bytes: bytes,
    as_of: datetime,
    attempts: tuple[ProcessingAttemptSummaryV1, ...],
    entry_local: tuple[ProcessingEntryNoteV1, ...])
```

Binding bytes are detached canonical COMPLETE current RequestBinding JSON, max65536 bytes, revalidated with actual public RequestBinding schema. Use existing Identifier semantics (nonempty/nonblank, not an invented preexisting length cap). Role/status/mode/reason enums and field types are exact; no bool-as-int accounting, nonfinite/negative number, duplicate or unsorted usage unit. Usage is detached sorted distinct finite nonnegative floats with existing unit identifiers; worst-case cost finite nonnegative float. Each durable reservation carries exact case/role/campaign unit debits1. No receipt means modeNone and receipt_statusNone with reservation_status consumed; saved unavailable receipt keeps reservation_status failed and receipt_status unavailable. Validate terminal reservation/receipt pair consistency. Entry-local is at most one exact note; recorded_replay has reasonNone, unavailable has an enumerated non-None reason. as_of must be a fresh timezone-aware UTC datetime, not a readability stamp.

No nested mutable receipt/request/output retained. No output, assertions, transcript, proposal, freeform receipt reason/error, authority observation, input/output hash or reference, artifact ID/path, endpoint, campaign/permit, proof/approval, prompt, requested/observed model identity or inferred provider participation. Invocation IDs identify durable rows only, never artifact locators or permission. Worst-case reserved debt is not actual spend or model success.

Projection may reject malformed/corrupt selected inventory entirely; never filter a bad row, return a partial list or drop none/failed/unknown/unavailable rows. Preserve all insertion-ordered original `store.processing_attempts` rows, not alphabetical IDs or latest-success-only. Avoid invented stricter total-row cap that silently truncates actual lawful history.

## Authenticated inspection entry

Public signature is `WorkflowEngine.processing_summary(case_id, auth, *, execution=None) -> ProcessingSummaryV1 | CaseResult`.

Use existing `_execution_scope` / `_entry_scope`, original gateway timing and exact captured host deadline. Strict valid case identifier plus typed revalidated AuthContext precede store/source inspection. Find the current saved binding, then ACTUAL PUBLIC `gateway.authenticate_control(binding, auth, purpose='recorded_state')`; use its returned checkpoint AFTER current-source control-read accounting. Only then read all `store.processing_attempts(authenticated.binding)`, detach/validate the entire inventory, take original clock UTC sample, and recheck current binding/fixed associations/original timing before returning. No private journal projection, integrity-hash authorization substitute or original-scope bypass.

Stopped recorded state may remain inspectable through this existing control gate; summary cannot reopen processing. Missing/foreign case, wrong proof, changed source identity/authorization, corruption, expiry/reversed clock, thread or recursive entry returns the existing generic public denied CaseResult only. A malformed input uses correlation `invalid-request`; a valid input keeps that case ID. Public denial includes only status/correlation/generic reason, no counts/content/internal exception or partial projection.

Actual fresh authentication can debit original control-read tool/time budget and source pressure. Do not claim whole checkpoint/SQL immutability. Preserve exact invocation/role/campaign/effect debt and receipt history; record the actual tool-read increment in tests. No invocation/processor/ID-factory call, new artifact/publication, receipt mutation, refund/retry, or saved CaseResult is allowed in summary.

Catalog revocation neither authorizes output nor hides status/debt. Status-only summary performs NO catalog resolve/read/publication/ACL operation and exposes no catalog-derived locator. Compare real catalog bytes before/after; do not use mutating `publish_processing_output` or infer private marker paths/IDs. Current output-reference authorization and durable entry-local history are explicitly missing, not completed by this summary.

## Actual last workflow-entry note, not synthetic durable history

Retain one in-memory last run/recover/reply entry note keyed by its exact current completed binding, only from an actually observed unavailable input or true replay return. It is not a ProcessingReceipt, permission, lifetime audit or history reconstructed from checkpoint.processing_status. Clear at a new workflow entry/denial; no stale prior-binding disclosure. Summary itself must neither synthesize nor clear it. Reconstructed engine starts with entry_local=() even if saved checkpoint says unavailable. A later actual workflow entry may legitimately produce a new note. Actual replay note is recorded_replay, not a claim that a model entered.

## Required finite TDD and verification

Use two self-contained public real synthetic fixture scaffolds in the plan: structured reschedule same-parent/noID/retained old caps, and public journal ordered five-status debt/privacy/current source authentication/catalog revocation/restart-empty notes. They are future test designs until actual RED/GREEN execution; public journal producers do not prove processor/publication participation.

Add narrowly relevant constructor/mutable alias/foreign store-clock-catalog-gateway/profile-bundle/thread/reentrant guards; structured authority and recipe mismatch negatives; text/evidence no-entry; summary auth/stop/current identity/expiry/reversal/corrupt later row/no partial list; closed pure projection errors and local actual/restart notes. Preserve original artifacts and caps. No broad old API/V2/driver/full-suite repeats merely for review.

Fresh actual source/data/import/read/interpreter/platform closure must be recorded and frozen before root's separate finite final cohort GO. Observer/audit limits disclosed; no test-root-only pinning. Root independently reads original raw results and runs proportional NEW checks under same held dependencies, exact4 commits, then different-nonauthor Spec/Quality gate. No Python3.11/wheel/native/paid/provider/network/server/activation/custody/drill/end-to-end10min claims.
