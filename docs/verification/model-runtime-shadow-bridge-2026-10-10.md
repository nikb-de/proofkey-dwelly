# Local model/runtime shadow bridge — verification

Verified on 2026-10-10, original implementation through `0e8e170`, with the package-isolation correction through `56da15b`. Python 3.12. Local-only; no provider calls, customer actions, deployment or remote publication.

## Delivered

- Strict read-only validation of completed service snapshots, drafts and producer receipts.
- Optional runtime-owned resolver checks exact identity, revisions, current checkpoint, versions and caller scope.
- Durable private shadow records with retry identity, conflict rejection and zero business effects.
- CLI deliberately has no resolver injection or user-supplied runtime authority; normal CLI result is `unmapped`.

## Original delivery verification

| Suite | Result |
| --- | --- |
| `tools/dwelly_bridge/tests` with runtime on PYTHONPATH |82 passed, no skips, 2.146s |
| Runtime `test_shadow_binding test_journal test_contracts test_execution_context_storage` |114 passed, 2.159s |
| Existing model tests |74 passed, 0.715s |
| Existing case-import tests |58 passed, 0.902s |
| Existing service tests |25 passed, 9.686s |

All commands used `-B -W error::ResourceWarning -m unittest`. For bridge/runtime tests the interpreter was the existing environment `.superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python` and `PYTHONPATH=runtime/src:runtime/tests`. Other suites used `python3.12`. Exact portable commands are in `tools/dwelly_bridge/README.md`.

These are 353 test executions across the listed suites, not semantic-case accuracy measurements. The older full runtime suite subsequently finished with 1,963 tests and two package-closure failures. That historical run was not a pass and was not duplicated.

## Package-isolation correction

The optional resolver initially expanded the runtime's registered 86-file package to 87 files. `f9e34cd` moved it to `tools/dwelly_bridge/runtime_binding.py` without changing the frozen package, its fixture or any registered hash. Review then caught that its tests still depended on root-directory imports; `56da15b` moved all 28 tests alongside the companion and added a standalone runtime-discovery regression. The regression was observed failing before the test move and passing afterward. Independent rereview accepted the correction with no remaining findings.

Fresh controller results after the correction:

| Check | Result |
| --- | --- |
| All bridge tests with optional runtime | 112 passed, no skips, 2.222s |
| Bridge with `-S` and no `PYTHONPATH` | 112 collected: 82 executed, 30 explicit optional-runtime skips; 1.482s |
| `test_journal test_contracts test_execution_context_storage`, launched from `runtime/` | 86 passed, no skips, 1.440s |
| Unmodified canonical qualification control | 156/156 passed; `source_stable=true` |
| Original two failed qualification tests, session 17076 | 2 passed, 816.825s, exit 0 |

Both original failed qualification tests now pass. Their canonical source-hold phase completed before the runtime test file was moved; subsequent qualification ran in isolated copied roots. Exact command and output: [session 17076 log](../../outputs/proofkey-shadow-package-isolation-2026-10-10/original-two-tests-session-17076.log). No new full-suite pass is claimed. The current portable bridge commands are in `tools/dwelly_bridge/README.md`; the old `test_shadow_binding` path above describes the original delivery only.

## Review and fixes

Task reviews accepted source, resolver, storage and CLI. Storage review found invalid persisted timestamp values bypassing fingerprint exclusions; fixed and re-reviewed in `8d8c559`. Whole-change independent review found SQLite could create WAL sidecars even with `mode=ro`. Fixed in `0e8e170` by rejecting unsupported journal-format headers before SQLite opens; two real-database regressions verify identical source paths/hashes and no output on rejection. Narrow rereview accepted the fix with no remaining findings. Review receipts and exact diffs remain in the private `.superpowers/sdd/2026-10-10-model-runtime-shadow-bridge/` workspace.

## Not established

No executable model plan, real authentication, native adapter, media understanding, cloud readiness or calibrated business correctness. Runtime fixture identities are synthetic. Locally consistent provider receipts are not external attestations. Successful import never grants permission to reschedule, message, refund or pay.
