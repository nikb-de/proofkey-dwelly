# Case-model E2E and state controls

## Why
The integrated platform has no live browser/model evidence on the authored case timelines. Existing green infrastructure tests and the older 50-case CLI experiment do not establish that chain. The user explicitly requests E2E plus state and execution control, with autonomous parallel implementation.

## What changes
- Replay the three existing source documents as independently bound decision-time cases, preserving source goal, actors, text and cutoff provenance without feeding author labels to inference.
- Add a bounded API E2E runner and a browser E2E on real PostgreSQL. Separate live provider results, scripted transport fixtures and unavailable runs.
- Assert expected coordination state/wait target, no premature completion, current revision/hash, durable result, same-key recovery and zero unauthorized effects.
- Expose coordination state and read-only model-job monitoring in the platform UI without granting model output execution authority.

## Impact
New development-only replay/evaluation tooling; small additive UI controls. Frozen case v1, operational policy and real adapters are unchanged. API calls require explicit live mode and available credentials; existing USD25 per-provider/model/experiment maximum remains binding.
