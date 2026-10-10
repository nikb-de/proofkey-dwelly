## Why

Registered execution can run a trusted synthetic case but cannot yet stop it through the same authority boundary. A narrowly versioned same-owner stop is the first useful control capability without assuming safe restart, re-admission or arbitrary continuation.

## What Changes

- Add explicit `fixed-synthetic-observed-stop-v2` trusted preparation alongside unchanged default v1 behavior.
- Bind v2 to an exact expanded first-party inventory and fresh roots; do not update old markers or reviews.
- Mint a private stop capability only after successful observed admission in the current owner/clock.
- Route same-owner stop through current source authentication and the existing durable wait-fencing operation.
- Keep registered recover, reply, transfer, reopened-owner controls and post-deadline guarantees unsupported.

## Capabilities

### New Capabilities
- `observed-route-stop-v2`: bounded same-owner stop capability, original identity/debt/deadline continuity and local acceptance evidence.

### Modified Capabilities
- `trusted-replay-case-provisioning`: explicit trusted v2 factory selection and narrowly versioned stop support; the default fixed-synthetic-v1 family and its denials remain intact.

## Impact

Scoped changes to host admission, trusted provisioning, host routing, and engine/gateway entry tagging; new tests and a trusted-library example. Existing persisted schemas and default wire commands remain unchanged. Newly pinned code requires new artifacts, review grants and private roots. No live providers, customer contact, money execution or general activation. J07 remains partial until independently specified recover/reply and continuation work is completed.
