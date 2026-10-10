# Team handoff: independent evaluation and real examples

Status: awaiting team input. No fabricated live data or claimed untouched holdout.

## Requested contributions

1. **10–20 evaluation cases**, independently written/reviewed and not used to tune prompts. Include rescheduling, refusal/returns, incomplete evidence, authority gaps, unsafe requests and legitimate operator escalation. Keep related cases in the same source group.
2. **10–20 real examples**, with permission and provenance, minimized/redacted before any external API submission. These are separate from synthetic examples; do not assume that providing a file authorizes sending it to three providers.

Deliver the existing `dwelly-snapshot-v1` JSON format (see public `agent/` examples). Preserve source/event IDs, UTC record timestamps, exact visible text, source references, cutoff and content hash. Keep the expected next action and later outcome in a separate evaluator-only record, never in the model input.

For each case provide a ledger entry with case_id, origin, synthetic/real classification, independence_group, split, tags, source permission, redaction status, required next action, acceptable alternatives, required details, prohibited actions, authority requirements, evidence references and reviewer status. Missing facts stay unknown; reviewers may mark a case ambiguous or exclude it with a reason.

For real data, use pseudonyms consistently; remove email addresses, phone numbers, full addresses, account numbers, secrets and unnecessary identifiers. Keep the mapping outside the repository. Record whether placeholders preserve the information needed for the task. Do not fabricate consent, identity verification or execution receipts.

## Review protocol

Freeze test cases before prompt/model selection. No team reviewer is available yet: retain `human_review_status: pending` and treat all model scores as provisional. Review critical failures and disagreements first, then a sample of agreements to catch shared mistakes. Run known-good, clearly wrong and insufficient-evidence controls through each judge, repeat identical bytes and inspect verdict flips. Scores must not authorize business effects.

There is no universal release threshold inferred from model consensus. The initial source release is experimental; a later quality claim requires reviewed labels, independent cases and a documented acceptance decision.
