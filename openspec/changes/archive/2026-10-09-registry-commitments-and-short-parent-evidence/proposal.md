# Public registry commitments and short-parent evidence

## Why

J22 identifies representation coupling between registry ownership and admission consumers. J32 identifies missing positive evidence when final observation has less than five seconds of parent authority. The approved next-cycle design bounds both changes and preserves all current safety semantics.

## What Changes

- Add a validated, detached public commitment inventory and migrate admission consumers.
- Exercise the existing final phase with both UTC-limited and monotonic-limited two-second remainders, including expiry before persistence.
- Preserve current wire bytes, digest recipes, exactly-one-release composition, original authority and uncertain-effect retention.

## Capabilities

### New Capabilities
- `release-registry-commitments`: public immutable validated inventory.

### Modified Capabilities
- `registered-admission-timing`: explicit positive short-parent scenarios; no intended production timing change.

## Impact

Three runtime source modules and two test modules. No storage migration, dependency change, live provider, permission expansion or new supported process. Reassessment is a separate evidence operation, not runtime authority.
