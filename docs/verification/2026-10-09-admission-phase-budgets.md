# Registered admission phase budgets — verification

Local implementation commit: `15453e1`.
Assessed pre-fix snapshot: `8e8c9f92c07e9e32e35134962d4b6df6d8648be3`.

## Scope and result

A real engine run could finish after five seconds but inside its original
parent cap, then fail outer admission observation and retain a blocking sealed
claim. Initial controls still use their original-start five-second cutoff.
The fix derives one separate final-observation phase, at most five seconds
and both original remaining parent bounds. Captures, route join and claim
write share it. Original authority, durable timing, debt and effects are not
reset; no engine retry, new profile or recovery path is added.

## Evidence

- Original controlled reproduction: engine verified a reschedule at
  12.100011 seconds, with 107.899989 seconds left of its 120-second parent;
  outer call timed out, one effect remained, and a sealed claim blocked reopen.
- TDD RED: 34 tests, one expected error and one failure.
- Focused GREEN: 34 tests, 49.499 seconds, OK.
- Independent root check of the three added real-component regression tests:
  3 tests, 18.331 seconds, OK.
- Independent nonauthor review: spec and quality PASS, no Critical/Important
  issue. One minor follow-up: directly test a still-positive parent remainder
  shorter than five seconds. Current code clips both clocks; tests cover full
  parent expiry, backward clocks, context mutation and shared-phase exhaustion.
- Full runtime: 1,622 tests, 365.898 seconds, **1 failure and 16 errors**.
  Exact selector-set comparison against the previous captured full run:
  17 prior, 17 current, no added or removed selectors. The suite is not green.
- Whitespace check passed; only the two scoped product/test paths changed.

Source SHA-256:

```text
b227f63ea290b355fd5cad16ac4e7ccc612b07101c31356d6116755d7eb505ed  runtime/src/proofkey/host_admission.py
b589e728ffb65d306af41ed157e18989d885141009405ce8933ccbcb12792061  runtime/tests/test_host_admission.py
```

Full output SHA-256:
`23001179fa7f356a81d92bec701120748b064b6b15f610d728e63ec39e445f30`.
Raw outputs, comparator, author and review reports are retained in
`.superpowers/sdd/2026-10-09-admission-phase-budgets/` and copied to
`outputs/proofkey_runtime_panel_2026-10-09/evidence/fix/`.

## Decisions and remaining limits

The five-second control requirement is interpreted per phase while the original
parent remains an absolute cap. If this interpretation changes, the leaf spec
and phase tests require revision; the implementation does not grant new parent
time. Narrow integration is accepted with the unchanged known failing-selector
set, not as evidence that untested behavior or the complete runtime is correct.

The five-provider scores were not rerun or increased after this fix. The
`proofkey-v21-harness-contracts` parent change and whole development branch
remain open. No provider integration, actual human approval, protected holdout,
cross-platform installation, full-suite qualification or event submission is
established by this work. Only the completed timing leaf is archived.
