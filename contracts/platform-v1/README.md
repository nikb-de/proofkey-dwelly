# Platform API v1

The canonical input remains `contracts/v1`: declarations and append-only events, unchanged. Platform projections are separate `proofkey-platform-case-v1` records with `snapshot`, `states`, `decisions`, `reviews`, `actions`, `assets`, `model_jobs`, `media_runs` (when configured), and `external_effects:0`.

Routes and request bodies are described in the [platform operations guide](../../docs/platform-operations.md); [living requirements](../../openspec/specs/unified-case-platform/spec.md) define the required behavior.

[states.schema.json](states.schema.json) is the machine-readable projection contract. [state-machines.json](state-machines.json) describes the independent transitions and admission guards; the deterministic runtime remains the authority for actual transitions, not a model-written status string.

All writes require `X-ProofKey-Request: platform-v1` and an `Idempotency-Key`, within the trusted same-origin loopback boundary. State-changing body references are checked against the current case revision/hash, except exact replay of already admitted work. JSON creation returns `{case:...}`; mutations return current `{case:...}`; media upload returns `{asset:{asset_id,sha256,mime_type,size_bytes}}`; model submission returns the original `proofkey-model-job-v1` envelope. Errors are `{error:{code:"english_machine_code"}}` and never raw database/provider exceptions.

## Dataset boundary

Use the unchanged canonical snapshots/events for team training/eval source data. Keep model suggestions, human reviews and receipts in separate fields/splits; never feed a target answer back into the model evidence projection. Original media is referenced by immutable asset ID and hash. A reviewed derivative is an internal operator message referencing its source, not a change to the customer's original message.

Model run success, deterministic schema validation, and sandbox success are different labels. None is automatically human-validated training gold. `evaluation:null` is intentional for user-created cases without a validated reference.
