## Scope and chosen format

This is an authoring and structural-validation handoff, not a training job or a scored benchmark. One decision is an exact canonical case revision. Model input uses `proofkey-decision-input-v1`; labels and episodes retain their existing closed schemas. Detailed semantic criteria are an evaluator-only sidecar, never new fields inside backend snapshots.

The manifest binds input, label, criteria and episode paths plus exact file-byte hashes, family ID, split, origin, cutoff and annotation status. Synthetic seeds remain development/unreviewed. Related revisions, branches and source families must not cross splits. An as-of cutoff does not invent the server receive timestamps missing from current contracts; availability is a curator responsibility.

## Validation boundary

Validate local JSON schemas, exact source triples and canonical snapshot hashes, full revision prefixes, participants and evidence references, files and inventory, family/source split isolation, and human-review consistency. Reject path traversal and network schema resolution. Validation success does not establish label correctness, lawful data collection, real-world authority, media understanding, or model quality.

## Examples and handoff

Use three independently authored fictional source families: rescheduling, damaged-goods refusal, ambiguous booking acknowledgement. Supply R0/R1/R2 for each and compare every generated snapshot with actual CaseStore behavior in isolated temporary storage. Include no actual media and no completed model-run receipts.

The canonical schemas are copied exactly from `contracts/v1/schemas/`; a future backend/model adapter remains separately required. Existing `docs/dataset-drafts/` are preserved, not converted by renaming fields. ZIP distribution excludes user drafts, secrets, caches and raw private material, and includes exact-file integrity metadata.
