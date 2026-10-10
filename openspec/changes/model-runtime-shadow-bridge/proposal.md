## Why

The model service produces unsent contact drafts, while the operational harness constructs deterministic actions against a simulated world. There is no authenticated, provenance-preserving connection between them; adding real APIs or media processing without that boundary would conflate suggestions, evidence and authority.

## What Changes

- Introduce a separately invoked, read-only shadow bridge for completed model results and host-supplied runtime bindings.
- Preserve the original draft, snapshot, receipt provenance and case-scoped citations; record explicit rejection or missing mappings.
- Prove that shadow import cannot call models, run workflows, change runtime checkpoints or dispatch effects.
- Document the subsequent typed-planner, native-adapter, multimodal and cloud milestones without declaring them implemented.
- Keep the existing service API and contact-draft schema unchanged. This increment is preparation for operational connection, not completion of it.

## Capabilities

### New Capabilities

- `model-runtime-shadow-bridge`: Idempotent, provenance-preserving shadow import with no operational authority.

### Modified Capabilities

None. The existing parallel model service remains a draft-only service; existing synthetic runtime admission remains unchanged.

## Impact

New optional bridge package/CLI, bridge tests and reviewable shadow records. The runtime environment requires its own dependencies; the existing model-only Docker image must not silently acquire an executable runtime. No external provider, new paid invocation, deployment, real integration or business action is enabled by this proposal.
