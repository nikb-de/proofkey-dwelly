## Why

Colleagues need a shareable dataset authoring format now, while UI/backend integration proceeds separately. Earlier rich decision-episode drafts use incompatible revision semantics and cannot be presented as backend-ready inputs.

## What Changes

- Package unchanged canonical v1 input/label/episode schemas with examples, English instructions and a Russian team brief.
- Add evaluator-only criteria and manifest sidecars, with a standalone offline validator.
- Supply three synthetic development families, immutable revision chains, explicit draft reviews, and an integrity-checked ZIP.

## Capabilities

### New Capabilities
- `team-dataset-handoff`: portable, validated authoring package with clear model/evaluator separation.

### Modified Capabilities
None. Existing backend contracts remain byte-identical.

## Impact

New `datasets/team-handoff-v1/` directory and generated distribution archive only. No backend, model runner, provider, real customer data, or operational action is changed.
