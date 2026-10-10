## Why

Fourteen current AdaptationFactory tests supply current checkout bytes to a
historical immutable six-file registration. Five files changed since its source
commit `336b0bb0f9b9e2b6118c34de825200c80764fd2e`, so factory construction denies
the material before testing regression, approval and staging behavior. Replacing
the old hashes would erase historical identity; accepting self-computed expected
hashes would bypass the independent admission boundary.

Status: design and corrected written implementation plan accepted by the user
on 2026-10-09 ("подтверждаю"). The bounded implementation, independent reviews,
fresh-process captures and complete 1,685-test suite are complete. See
`docs/verification/2026-10-09-factory-registration.md`. This establishes only
the stated local synthetic scope, not production qualification or activation.

## What Changes

- Add a trusted-host-only immutable synthetic implementation registration to
  FactoryContext, explicitly selected by current synthetic tests.
- Preserve historical default constants and byte recipes.
- Bind the selected registration identity to proposals and staged simulations.
- Pin a separate current-source fixture and verify its correspondence to the
  actual imported implementation before creating behavioral receipts.
- Retain unavailable activation, migration, changed-process dispatch, actual
  review and measured adaptation claims.

## Capabilities

### New Capabilities

- `synthetic-factory-registration`: bounded current-source test registration,
  separate from historical identity and production qualification.

### Modified Capabilities

None. The earlier registered-release-routes stage remains unchanged and does
not retroactively establish current factory qualification.

## Impact

Proposed code surface: factory/proposal.py, factory/release.py, factory/__init__.py,
test_adaptation_factory.py, a fixed test registration fixture and focused tests.
No engine/adapter/profile/permission changes, provider calls or live activation.
