# Explicit synthetic factory registration — verification record

Date: 9 October 2026. Status: **complete and archived**. Only this bounded factory-registration leaf is complete; the parent programs remain open.

## Scope and candidate

The user approved the two-task implementation plan (historical worklog retained in Git history). Runtime candidate: `ecf36ac` on `codex/proofkey-runtime`, in the existing linked worktree. The primary checkout was not modified.

| Commit | Change |
| --- | --- |
| `825e054` | Recorded the approved execution plan. |
| `94b0eec` | Added immutable, opt-in six-source registration; preserved the historical default and serialization vectors. |
| `ecf36ac` | Added the fixed fresh-process qualifier, exact test accounting, artifact capture and bounded launcher. |

The explicit registration is trusted host configuration, not case input, a dynamic import, or model-generated authority. Its inventory is detached and sorted; exact types, path set, SHA-256 values, provenance, identity and byte limits are validated. It binds proposal and staged-manifest identity consistently. The default `None` path retains historical pins and byte recipes.

## Recorded evidence

Evidence root: [outputs/proofkey-factory-registration-2026-10-09/](../../outputs/proofkey-factory-registration-2026-10-09/).

| Observation | Actual result | Scope |
| --- | --- | --- |
| Original focused baseline | 21 tests; 14 errors at historical pin admission | Preserved RED, not a passing result |
| New registration tests before implementation | 16 assertion failures | Deliberate contract RED |
| Task 1 focused run | 37 tests, 30.023s, OK | All 21 original factory tests plus 16 registration tests |
| Task 2 pre-alias/pre-timeout run | 58 tests, 361.736s, OK | Historical intermediate tree, not final-tree proof |
| Final timeout-tree delta | Six checks, 33.348s, OK | Includes a fresh 37-test inner lane and exact artifact joins |
| Root direct final-code lane | 37 tests, 30.196s, OK | Retained `current-source/`; no outer-module recursion |
| Root independent retained-byte readback | 26/26 checks passed | Standard library only; no factory/qualifier import |
| Complete final-code runtime suite | 1,685 tests, 742.788s, OK | Zero failures, errors, skips or warnings; all 1,685 verbose success positions are unique |
| Post-README final snapshot | 37 tests, 31.264s, OK; 26/26 readback checks passed | Retained `current-source-final/`; only `runtime/README.md` differs from the first snapshot |

The root lane retained 246 before/after runtime-file hashes, 28 pre-test and 37 post-test project-local imports, and eight canonical artifacts. Its execution ID is `synthetic-factory-ee79dbcdb503468f840bc0fd498fd1a9`; its manifest SHA-256 is `004ca8f75b5a091caa97db693a47178cc10025ec6441ad1c782c198fbdafdf08`.

After updating only the runtime README, a second retained lane verified all 246 current files and the same 37 tests again. Its execution ID is `synthetic-factory-b4da2ecf00614e168eba353dc5259677`; manifest SHA-256 is `869fae364229d018bd2ca48d1b1043c467872d941955d1c6bd5d9f1564135fa8`. Both captures and their independent readbacks are preserved. No source/test/script file changed after the full-suite run.

The eight artifacts are the supported proposal, executed regression, simulated approval, review packet, staged manifest and staged receipt, plus the non-v1 proposal and unavailable regression. The independent checker verifies their raw hashes and canonical bytes, proposal/regression/stage joins, execution IDs, fixed registration and source inventory. The supported result remains `staged_simulation`; the non-v1 result remains `regression_unavailable`.

The current fixture SHA-256 is `61add6613a70c2dba9dd02a97f1bd6c8be7842491a293a23f77d9f45ae559dec`. The historical vector fixture SHA-256 is `bed676874ec36d8e0673654aa56a1ecd5104831ae4c72fcbc1962117656a1d14`. Historical blobs were serialized and compared, not executed or relabeled as current behavior.

The full-suite receipt records exact HEAD `ecf36acdb3ebad7a33ef2257adb583356934c0ff` before and after, 236 unchanged inventoried files, exit zero and no timeout. Wall time was 744.012 seconds; unittest time was 742.788 seconds. Raw stderr SHA-256 is `b9c156f1ea56e2a78e836a851e9a6c9f2106cef218c0293c898d4e39512af9c9`; stdout SHA-256 is `91a0334c44ce0ec9a994c1e78f5bea48dc05e8e8767f8de63ac2a5dc44de5b48`. Root independently reread both hashes, identical before/after inventory bytes and 1,685 unique verbose successful selectors. A green exit alone was not used as the entire check.

## Verification environment and commands

Existing isolated interpreter: `.superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python`, CPython 3.12.14 on macOS arm64. Existing dependency check: no broken requirements. No dependencies were installed.

From the linked worktree, using a new absolute output path each time:

```sh
.superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python -B \
  runtime/scripts/qualify_factory.py --output ABSOLUTE_NEW_OUTPUT_DIRECTORY
```

The public qualifier accepts no arbitrary code/module/provider/registration arguments. It rejects optimized Python, removes inherited optimization, uses disabled bytecode writes and a new empty private cache, and checks source pins and loaded-module identities. Its child cutoff is 300 seconds; timeout produces an invalid manifest and retained child output, never a successful qualification.

The root complete-suite recorder invokes:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 \
PYTHONPATH=runtime/src:runtime/tests \
.superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python -B \
  -m unittest discover -s runtime/tests -v
```

Raw command/environment, output, before/after inventories and receipt are retained under `full-suite/`. The full-suite inventory covers runtime source, tests, profiles, fixtures, scripts and root configuration/lock/JSON/SQL files; it is narrower than the qualifier's all-non-cache-runtime-file inventory. Neither is a complete transitive environment closure.

## Independent review

- Task 1: spec PASS, quality Approved; no actionable findings.
- Six historical/current pinned sources: no static blocker for this exact controlled synthetic use; explicit transitive-scope omissions retained.
- Task 2: spec PASS, quality Approved; no actionable findings.
- Whole approved leaf: spec PASS, quality Approved, no blocking findings. The reviewer independently checked retained source hashes, import identities, all eight artifact hashes and the 37-test log. This does not substitute for the unfinished program's whole-change audit.

Raw implementation RED/GREEN logs, the historical capture script, both task reviews, the six-source semantic audit and final leaf review are retained under `review-and-development/` in the evidence root. Earlier reports describe their actual review-time snapshot and pending gates; this record supplies the later completion evidence without rewriting those reports.

## Execution rulings

1. Root, not each task author, runs the final complete suite. Authors run focused checks; root full verification remains mandatory before closure.
2. Preserve all **21** existing factory tests; the plan's initial count of 20 was corrected without removing or weakening a test.
3. Bound the qualifier child at **300 seconds**. A genuinely slower valid run is recorded invalid and requires a reviewed bound change. This cutoff is not the business deadline or the 600-second adaptation target.

## Explicit limits and follow-on work

This is local controlled synthetic evidence with simulated approval. It establishes neither actual human release approval, authentication, hostile-code isolation, complete runtime/dependency closure, activation/migration, provider participation, native integrations, changed-process dispatch nor a timed adaptation drill. Before/after checks do not detect invisible transient in-process mutation.

Original five-provider scores and evidence are unchanged; no new score is inferred. **J01 and J02 are closed on their narrow criteria**, giving six closed and 26 open items in the [complete register](judge-remediation-2026-10-09/README.md). Broader J27/J30 audits, J22 public commitment inventory, J32 short-parent timing coverage, packaging/integration and all human/external gates remain open. Only the completed factory-registration leaf may be archived; both parent changes remain open.

The validated OpenSpec archive is 2026-10-09-synthetic-factory-implementation-registration (historical worklog retained in Git history). Its four requirements are now in the [living specification](../../openspec/specs/synthetic-factory-registration/spec.md). Neither `proofkey-v21-harness-contracts` nor `judge-remediation-program` was archived.
