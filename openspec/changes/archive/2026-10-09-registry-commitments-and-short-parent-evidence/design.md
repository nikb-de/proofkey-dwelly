# Approved design

The binding design is `docs/verification/judge-remediation-2026-10-09/next-cycle-design.md`, approved by the user before implementation.

`ReleaseRegistryV1.commitments()` returns exact built-in tuples of `(release_id, artifact_hash)` strings. Validate the actual retained records before projecting them, with count and byte bounds before parsing. Canonical release validation and matching outer/embedded IDs prevent a public inventory from hiding malformed or swapped internals. No independent cache is permitted to conceal replacement of retained records.

Admission composition consumes a single commitment matching its binding. The owner stores a detached snapshot and compares a fresh validated inventory at entry. The route store resolves the public inventory and cross-checks each resolved identity and hash; its existing persisted registry digest format and canonical raw releases remain unchanged.

The timing work changes tests only. Use the real engine and persistence, injecting trusted test-clock progression at engine return. Parent capture at tick 100, deadline 220: tick 216/UTC offset +2 is UTC-limited; tick 218/offset -2 is monotonic-limited. Each leaves two seconds. Forwarding spies preserve all real side effects and verify one shared phase. Expiry at final write must fail closed while retaining the already-made effect and imported account.

On-demand envelope validation adds bounded parse cost on a hot path. Record focused timing and full-suite evidence; do not replace mutation detection with a stale cache to improve performance. Existing synthetic evidence remains synthetic.
