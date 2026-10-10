# Baseline corrections — 9 October 2026

## Result

The failing-selector set decreased from **17 to 14**. The complete suite is
**not green**. No production runtime code changed in this correction.

| Check | Observed result |
| --- | --- |
| Intake/processing focused suite | 39 tests, passed, 9.371s |
| Existing isolated API environment | 24 tests, passed, 20.181s |
| Independent narrow-change review | Spec PASS; quality PASS; no actionable findings |
| Full runtime at `9c1ea1cda990f27c7b1cc0814946414df812f862` | 1,646 tests, 14 errors, 396.912s |
| Baseline comparison | No added failing selectors; three removed |
| Source stability | 227 inventoried source/test/profile/fixture files unchanged during full run |

## What changed

`runtime/tests/test_engine_processing.py` previously expected both a valid
narrative and the malformed ID `unavailable-artifact` to be authorized. The
runtime correctly denied the malformed reference. The replacement tests
separate a narrative, a real authorized catalog original, and malformed,
well-formed missing and genuinely revoked-scope originals. Fresh invalid inputs
must return the complete generic denial. Real original bytes and persisted
request identity are checked; prepared processing, planner calls and business
effects remain absent.

The two API loader errors were environment selection, not defects repaired in
API code. The already existing isolated CPython 3.12.14 environment contains all
19 pinned API distributions; its dependency check and all 24 API tests passed.
No installation or server was needed. The final complete run used that same
environment, so it executed API tests instead of reporting missing Starlette.

## Decision made during the fix

Keep existing recovery semantics. The original-intake specification explicitly
says recovery does not implicitly repeat intake. An authorized **case**
observation with unavailable media does not authorize access to denied
**evidence**. The first draft wrongly expected recovery itself to be denied.
The corrected regression traps catalog reads/registration and prepared
processing during recovery, and asserts no exposed evidence, effects or grants.
If the intended product policy should instead deny that case observation, it
requires a separate reviewed behavior change; these tests do not implement it.

## Fourteen remaining errors

Every remaining error is in `test_adaptation_factory` and stops at
`unsupported_adapter_implementation` before its behavioral assertions. The
historical six-file source pins match commit
`336b0bb0f9b9e2b6118c34de825200c80764fd2e`; five differ from current source.
Neither replacing historical hashes nor deriving trusted hashes from submitted
material is an acceptable way to make these tests pass.

The proposed `synthetic-factory-implementation-registration` change retains
historical defaults and adds a separately pinned, explicitly synthetic trusted
host registration. Its identity binds new artifacts; fresh-process evidence
must match source and exact receipt bytes. Independent design review accepted
the revised proposal, but **user design approval and implementation remain
pending**. No current factory qualification is established by this proposal.

## Reproduce and inspect

From the worktree root, with the existing private environment:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=runtime/src:runtime/tests .superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python -B -m unittest discover -s runtime/tests -v
```

Captured evidence: `outputs/proofkey-baseline-fixes-2026-10-09/` contains author
and review reports, API environment identity, factory investigation/design
review, and `full-suite/` with exact command, raw stdout/stderr, before/after
inventories and the selector comparison receipt. This observed source inventory
is not a complete transitive execution closure, fresh-install proof or live
provider assessment.

Full stderr SHA-256:
`f322e7459602aa355d615c8b8ef1680bfa4352d5a5ba3b2047ebabfe6e391f91`.

Only the completed test-correction leaf is archived. The wider harness change,
whole-branch review, current factory qualification and event readiness remain
open. The previous five-provider packet and ZIP remain unchanged; no judge
scores were rerun or increased. No merge, push, provider call, installation,
activation, publication or submission occurred.
