## Context

At base `71b4cd4`, `CliReceiptV1` groups a command/batch receipt and optional shutdown. Nested results report effect verification but do not retain a transport-dispatch receipt or original AuthorityReadback. Host start precedes authentication. Identifiers are unrestricted strings, so even case IDs and operation names can contain secrets.

## Goals / Non-Goals

**Goals:** provide a deterministic, bounded, correlated receipt view; preserve negative/pending states; omit raw content and identifiers; demonstrate the existing offline path with a short guide.

**Non-Goals:** prove receipt authenticity, reconstruct a total event order, observe native dispatch, inspect files/journals, change the default CLI, enable registered controls, or claim human usability/production qualification.

## Decisions

1. **Pure projection with a stdin-only adapter.** `execution_trace.py` owns parse/validation/projection/formatting; `trace.py` only reads a bounded stdin stream and writes one requested rendering. This avoids a new file walker, output publisher, live collector or runtime owner. Raw run/readback combinations are deferred: their correlation needs a separately reviewed join, and shutdown has no run ID. Only the existing exact CLI envelope is accepted.
2. **Receipt-reported semantics.** Show input admission, host start/outcome, returned result-access status, per-effect reported original verification, publication, consumed export and shutdown independently. Always show `transport_dispatch: unknown`, `original_readback_observation: not_observed`, `publication_files_checked: false`, and `provenance: unverified_receipt_projection`. A parseable forged receipt is still not execution attestation.
3. **Local tokens, no hashes of arbitrary identifiers.** Deterministic first-occurrence aliases correlate run/release/case/command/effect identities within one trace. Do not expose raw IDs, operation names, paths, hashes, timestamps, rationale, arguments, policy/evidence refs, postconditions or free-text failures. Durations, booleans, ordinals, counts and closed enums are sufficient. Tokens are not cross-trace IDs or a cryptographic anonymization claim.
4. **Hard bounds, fail closed.** Input bytes <= 1,048,576; JSON depth <= 64; at most 128 batch positions, 256 effects per position, 4,096 total effects, and 50,000 visited input nodes. Rendered UTF-8 output <= 262,144 bytes. Reject invalid UTF-8, duplicate JSON keys, nonfinite numbers, exceeded bounds, wrong exact input types and forged model instances with one safe error code, without reflecting input. No truncation that loses denominator members.
5. **Revalidation before projection.** Walk declared model fields (not serializers that hide invalid denied-result fields), with exact known model/container/scalar types and cycle/depth/node guards; validate the detached tree against `CliReceiptV1`. Do not invoke arbitrary subclass serialization. Validate command/run release, mode and clock correspondence and unique command IDs for positions. Do not falsely correlate shutdown to a specific business result; it is only grouped by the envelope.
6. **Outcome-first documentation.** One rescheduling example, exact capture/render commands, a small static diagram, receipt interpretation, recovery cautions and links to goods/refusal and trusted new-case routes. Keep actual fresh execution separate from a human onboarding claim.

## Risks / Trade-offs

- Aggregate receipts cannot prove dispatch or current files → permanently explicit unknown/unobserved labels in this version.
- Tokens still reveal counts and equality → state the limited redaction scope; do not call it anonymization.
- Bounds reject some large legitimate captures → return a closed failure, preserve source, and do not silently summarize an incomplete denominator.
- Detached validation may expose inherited schema quirks → test real command and batch receipts in addition to hostile in-memory objects.
- Existing fixed implementation pins omit these detached modules → no runtime-authority pin changes; trace output never grants authority.

## Migration Plan

Additive modules only; remove the renderer/guide links to roll back. Existing stdout and persisted receipts remain byte-contract compatible. No data migration, repinning, activation or old-root rewriting.

## Open Questions

None block this leaf. Current inventory readback joins, trace attestation and transport event receipts remain separately scoped work, not implicit future support.
