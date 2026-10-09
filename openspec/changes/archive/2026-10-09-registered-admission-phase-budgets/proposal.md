## Why

The five-provider review exposed an operational defect: a real registered run
completed after 12.100011 seconds inside its original 120-second parent cap,
but final admission observation inherited the original start-plus-five-second
cutoff and failed. Its effect remained and its sealed claim blocked reopen.

## What Changes

- Define five seconds as a control-phase ceiling, not an engine execution cap.
- Retain the caller's immutable parent context and original durable timing.
- Derive one bounded final-observation phase, shared by captures, B3 join and
  final claim persistence, without renewing time at each operation.
- Preserve uncertainty, debt and real effects when either bound expires.

## Capabilities

### New Capabilities

- `registered-admission-timing`: parent-bounded final observation for registered
  synthetic execution. This narrow capability is not a new activation path.

### Modified Capabilities

None in the current living-spec directory (it does not yet exist). The broader
`proofkey-v21-harness-contracts` change remains unfinished and is not archived.

## Impact

Only `runtime/src/proofkey/host_admission.py` and its tests need product changes.
No dependency, public host API, engine, accounting, schema or recovery change.
The original five-provider packet remains frozen at `8e8c9f9`; the fix is a
post-assessment development result, not an automatically regraded snapshot.
