# Scoped ownership decision inventory refinement

9 October 2026. Internal prerequisite of the approved Task8 recorded-decision execution requirement, not a new logistics action, disclosure route or fresh user-reviewed design. Consumer implementation remains gated on independently Approved context consumers and this separate storage gate.

## Exact seam

Add `CaseStore.decision_record(binding: RequestBinding, decision_id: Identifier) -> OperatorDecisionSubmissionV1` using existing private OwnershipStore composition. Decision identifiers/replay checks are case-scoped; a global decision_id-only lookup must not choose a foreign case or generation. Require the complete immutable binding and a single exact recorded decision in that scope, validating existing tagged events, payload/source/original/index associations and hashes. Missing, malformed, foreign, ambiguous or corrupted inventory fails closed. Reject untyped binding/identifier and wrong creator thread before inventory reads. Return the strict detached immutable original submission, not a newly valid GateDecision or a reconstructed current grant.

The getter is trusted-host local inventory, not caller authentication, current source attestation, disclosure permission, consumption or expiry extension. It remains readable as historical inventory after lawful consumption/stop/expiry; it performs no source calls, writes, budget changes, phase/wait/owner mutation or implicit consumption. Current public callers never submit the returned record as permission. Gateway authenticates fresh source scope first, compares exact recorded scope, and uses recorded expiry to constrain the later physical boundary. Existing begin_dispatch still atomically validates and consumes the actual original. All schema, shared wire models and existing getter/consumption semantics remain unchanged.

## Bounded ownership and evidence

Separate three-file stage only: journal.py public delegate, ownership_store.py validated scoped getter, NEW test_ownership_decision_inventory.py. No SQL schema migration, new event producer or source/profile/process/fixture changes. Tests use explicitly synthetic existing public storage setup; they do not establish actual source authentication/native custody. Cover exact immutable result/reopen, case/generation separation with same ID, missing/invalid/duplicate/corrupt event denial, wrong thread, and no mutation/debit/source entry on historical consumed/stopped/expired lookup. Corruption controls must be labeled temporary durable-data fault injection, not an ordinary caller exploit.

Behavioral TDD, coherent named source/test manifest, exact scoped commit and DIFFERENT NONAUTHOR spec/quality review are required before the later nine-file ownership consumer stage. No implementation receipt follows from this document; fullTask8/10/M1, native delegation, target grants, initial activation and stopped current-confirmation remain separate gates.
