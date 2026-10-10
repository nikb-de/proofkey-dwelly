## Why
The product currently has disconnected intake, simulated operations and evaluation screens. Engineers and operators need a single durable case workspace that distinguishes evidence, model proposals, deterministic policy, human review and verified effects.

## What Changes
- Introduce a same-origin local platform with PostgreSQL cases, private media, immutable decisions, reviews and a transactional sandbox scheduler.
- Present separate lifecycle, evidence, analysis, decision and action states, including stale revision detection.
- Connect existing optional model jobs to user-created cases without invented reference labels.
- Keep evaluations secondary and preserve the frozen case and analysis contracts.

## Capabilities
### New Capabilities
- `unified-case-platform`: durable case operations and primary operator UI.
### Modified Capabilities
None. Existing analysis semantics remain compatible; unlabeled platform inputs explicitly omit comparisons.

## Impact
New `tools/dwelly_platform`, `platform-ui`, and `contracts/platform-v1` modules, plus a narrowly scoped optional-reference change in the existing model worker. No cloud deployment, credentials changes, real business effects or paid calls are part of this change.
