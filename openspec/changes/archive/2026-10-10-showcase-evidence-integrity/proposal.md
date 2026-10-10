## Why

The replay builder currently trusts copied input hashes and event IDs without checking the complete model input. It also accepts coordination from after a scene's cutoff, so inconsistent capture records can pass the source-backed replay boundary.

## What Changes

- Check recorded snapshot content and complete model inputs against canonical hashes and the existing pure platform projection.
- Bind coordination to its recorded historical snapshot, allowing legitimate older coordination while rejecting future state, future nested records, unknown evidence and changed offer terms.
- Preserve the output for the existing authoritative captures and add offline regression tests.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `product-case-showcase`: require complete evidence integrity and historical coordination bindings before producing a replay bundle.

## Impact

Only `tools/dwelly_platform/showcase.py`, its unit tests and this specification change. No database, provider, transport, UI or capture artifact changes are required.
