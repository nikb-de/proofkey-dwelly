## Why

Full runtime regression revealed that adding the optional shadow resolver inside `proofkey` violates its registered 86-file source closure. All original hashes remain correct. The resolver must remain optional without silently repinning approved implementation inventories.

## What Changes

Move the new resolver to `tools.dwelly_bridge.runtime_binding`, update its imports and callers, and add a closure-preflight regression. Preserve the original package, registered hashes, strict origin/closure checks and behavior of the read-only resolver.

## Capabilities

### Modified Capabilities
- `model-runtime-shadow-bridge`: optional binding implementation belongs to the companion package, outside the frozen runtime source closure.

## Impact

The new unreleased resolver import path changes. No existing runtime module behavior, registered profile or source pin changes. No provider calls, execution authority or business effects are introduced.
