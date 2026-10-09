# Independent review of the synthetic factory registration plan

Reviewed: 2026-10-09. Read-only review of `docs/superpowers/plans/2026-10-09-synthetic-factory-registration.md`, the matching OpenSpec design/spec/tasks, actual factory implementation and `test_adaptation_factory.py`. No tests, providers, installation, Git mutation, or plan edits were performed. Only this review file was created.

## Recommendation

The registration design is aligned with the approved narrow scope. **Formal implementation-plan approval should await the concrete verification-lane corrections F1–F3 below.** They do not require expanding the feature or changing its trust model. F4 is a small clarification that should be included while revising the plan. Do not reopen the already accepted principle of an opt-in immutable synthetic registration.

The plan correctly preserves the historical constants/default recipe, introduces no activation/actual-review authority, binds explicit registration identity into proposal and staged-manifest hashes, and requires the existing non-v1/pending-intent denials to survive. It also correctly separates a fresh-process evidence manifest from existing factory receipt schemas and disclaims full runtime closure. Six current file hashes were checked directly during this review and match all six literals at plan lines 65–70; this is a static byte check, not behavior qualification.

## Findings

### F1 — P1: Reject optimized Python before assertion-based business evidence

**Location:** plan lines 130–134 and both test commands at 105–107 / 138–140. Actual seam: `runtime/tests/test_adaptation_factory.py:96` (`executed_cases`).

The planned explicit supported-control flow reuses existing test behavior. `executed_cases` verifies the important rejection, queue-only, content-stored, wrong-identity and readiness invariants using Python `assert` statements at lines 123, 129, 132, 135, 144 and 152–155. It then emits every returned case with `result="passed"` at 146–158. Under an optimized interpreter these assertions can be omitted while those passed labels are still constructed. `-B` only controls bytecode writes; it does not require optimization level zero. The proposed same-interpreter re-exec also does not specify treatment of `PYTHONOPTIMIZE`.

**Effect:** the verification lane could create a passing synthetic regression artifact without having evaluated its business assertions. This contradicts the spec's requirement that current evidence match observed execution, even under the plan's trusted-test (non-hostile) scope.

**Minimal correction:** explicitly reject `sys.flags.optimize != 0` in both qualifier entry and child before importing tests; remove `PYTHONOPTIMIZE` from the child's documented environment and record the effective optimization level. Add a negative subprocess test using `-O`/`PYTHONOPTIMIZE=1` that produces only an invalid/failed record and no passing artifact. Alternatively convert the reused helper's checks into explicit checks that cannot be compiled away, with focused tests; the preflight rejection is smaller and avoids broad helper changes. The focused/full-suite commands should also run with optimization disabled.

### F2 — P2: Define the broader snapshot and join actual imported code to it

**Location:** plan lines 123–134, especially “capture tracked runtime source/test/profile/fixture bytes” and “verify their module origins and retained object identities.” Design lines 61–75 require a selected snapshot, imported identity and observed broader inventory.

Two implementation-critical details remain unspecified:

1. A tracked-files-only inventory can omit the newly created `qualify_factory.py`, `test_factory_qualification.py` or other new helpers when the lane runs before their commit. The plan creates those files in Task 2 and does not require committing before Task 2 verification. Such files execute but would not be covered by the described snapshot.
2. Checking only the six pinned modules and the top-level test module origins does not identify the factory code, contracts, journal, `support`, or `test_packet_source` actually imported. The current test imports all of those. A selected-tree disk inventory cannot by itself attribute another installed/PYTHONPATH module to the selected tree. This is the same disk-versus-loaded-code distinction that the plan is trying to protect.

**Effect:** a “current-source” manifest can describe selected tree bytes while omitting newly executed files or loading some relevant code from elsewhere. This does not require hostile mutation; a stale editable install or ordinary path collision is enough.

**Minimal correction:** define a deterministic bounded inventory that includes the required new files regardless of Git tracking, all files in the declared runtime/test/profile/fixture scope, and metadata such as the selected fixture/pyproject/lock if claimed. Exclude output roots, environments, bytecode and generated state explicitly. Preserve path→hash entries and the inventory digest before/after; any added/removed/changed relevant file invalidates the lane. Make the child establish canonical absolute selected source/test paths. Record and verify the origins of every loaded `proofkey.*` module and relevant local test/helper module against that inventory (at minimum factory proposal/release, contracts, identity, journal, `support`, `test_packet_source`, the selected test modules, and the six implementations). Record third-party origins/version observations separately without claiming complete dependency closure. Continue to reject a preloaded pinned module and changed retained identities.

This is local provenance for fixed trusted code, not a request for a hostile-code sandbox, function-level attestation, or full transitive closure.

### F3 — P2: Specify an exact non-recursive inner test inventory and success gate

**Location:** plan lines 126–142: the new qualification tests cover script execution, while the script is to “run the complete factory modules once.”

The plan creates `test_factory_qualification.py`, then refers to the complete factory modules without naming the inner suite. A natural broad discovery of `test_factory*.py` would run qualification tests that invoke the same script again; collecting all newly named factory modules is therefore potentially recursive. The plan also does not explicitly make missing/zero tests, skips or an incomplete discovered inventory invalidate the current-source manifest. Since the lane's role is stronger than merely returning unittest's normal success flag, an accidentally empty/partial suite cannot provide its advertised coverage.

**Minimal correction:** name the inner suite as `test_adaptation_factory` plus `test_factory_registration` only. Run `test_factory_qualification` in the outer focused/full-suite invocation, never inside its own child qualifier. Record the exact discovered test IDs and outcomes for the inner suite, require the legacy 20 test IDs to be present, require every declared new registration test to be present, and require no failure/error/skip/unexpected success before finalizing. Avoid duplicating a fragile hard-coded total for future new tests; the stable legacy ID subset plus explicit module inventory and discovered ID manifest is sufficient. Add a test proving the child suite excludes the qualification module and that absent/zero-test suites fail closed.

### F4 — P2 clarification: Keep legacy vector construction separate from behavioral helpers

**Location:** plan lines 48–50 and 101–103. Design lines 89–96.

The desired legacy vector scope is correct, but “build fixed supported-control material with current unchanged factory code” does not state which helper path is allowed. Current `reviewed()` calls `evidence()`; `evidence()` calls `executed_cases()` unless explicit cases are supplied. Reusing those helpers to generate a serialization-only vector would execute current behavior while associating historical adapter-source blobs with the resulting default-path proposal. Labeling the final vector serialization-only limits the public claim, but the generation recipe should make the separation explicit and reproducible.

**Minimal correction:** specify that legacy vector generation must supply literal fixed regression/case hashes, timestamp, approval, runner identity and pending inventory as serialization inputs, and must not call `executed_cases`, `evidence` without explicit cases, or `reviewed`. The golden test must exercise `implementation_registration=None` explicitly. Preserve the full input fixtures needed to regenerate its expected canonical bytes, and distinguish them from artifacts of the current explicit-registration behavioral lane. The current lane may use real local behavior; the legacy lane only checks byte compatibility.

## Additional practicality notes, not approval blockers

- The plan's fixed six logical paths, strict immutable registration normalization, explicit-path-only byte limits, sorted canonical pin digest, four `_material_proposal` call sites, and staged-manifest binding correspond to the actual code. The public `AdaptationProposal` need not gain a registration field if its hash binds the internal body as specified. Avoid changing wire schemas merely to expose redundant metadata.
- `factory_for(..., registration=None)` must distinguish omitted from explicit None with a private sentinel; otherwise the proposed default-current fixture helper can accidentally hide the historical-default test. This should be a small helper detail, not a runtime API expansion.
- The evidence helper currently uses the fixed execution ID `synthetic-local-execution-1` and fixed `NOW`. The explicit qualifier flow needs to pass its unique execution ID and separately retain actual capture UTC/monotonic observations. Existing deterministic unit tests may retain fixed timestamps. A synthetic approval should remain visibly synthetic, even if the capture timestamp is real.
- Name the negative non-v1 artifact explicitly as unavailable/rejected with its observed reason and no staged output. Its regression receipt must not be relabeled passed merely because the expected-denial test passes.
- The fresh child can remain a narrow standard-library launcher; there is no need to introduce a generic plugin runner, install dependencies, or accept arbitrary module/registration arguments. A declared finite child timeout and complete stdout/stderr capture would make failure reporting more reliable, but do not call that hard hostile-I/O isolation.
- The registration ID's `69738ea` label and the design's earlier `f220de2` observation are not inherently a hash mismatch: all current literal pins matched this static check. The final report should record the actual checked snapshot and refrain from interpreting the ID suffix as a complete-source qualification.

## Suggested approval checklist after revision

1. F1–F3 are written into the plan with concrete negative tests and no expansion of runtime authority; F4's legacy-only recipe is unambiguous.
2. Task 1 retains all legacy/default and current behavior assertions, uses detached explicit registration consistently, and never executes adapter source supplied in `ProposalMaterial`.
3. Task 2 reports exact selected/imported source scope, exact inner test IDs, real result-artifact byte hashes, and invalidates failures without overwriting historical evidence.
4. Claims remain: local controlled synthetic behavior and staged simulation only. No authentic human review, new-process dispatch, clean install, complete runtime closure, provider participation, or timed adaptation is inferred from this leaf.

Once corrected, the plan is practical for the intended two-step leaf. The architecture does not need redesign; approval should be for this limited implementation and verification scope, not for broader judge remediation completion.

## Resolution recheck — 2026-10-09

Re-read only the revised plan and matching OpenSpec design/delta against F1–F4. No implementation, test, provider, install or source-code change was performed. This dated section supersedes the earlier recommendation to await plan correction; the original findings remain as the review history.

| Finding | Resolution in the revised documents | Status |
| --- | --- | --- |
| F1: optimized assertions | Plan global constraints and Task 2 Step 2 now reject optimized invocation, remove `PYTHONOPTIMIZE`, require the child optimization flag to be zero before helpers, and add an optimized-child negative test. The design requires zero optimization in launcher/child; the delta forbids successful evidence when assertions are disabled. | Resolved at plan/spec level. |
| F2: snapshot and import origin | Plan Task 2 Steps 1–2 include added/untracked executing files, the qualifier and fixed fixtures; reject aliases; inventory before/after; and verify origins/retained identities for all loaded project-local modules, including factory/contracts/support/test helpers. External dependencies are reported separately. The design and delta preserve these boundaries. | Resolved at plan/spec level. |
| F3: recursive or incomplete suite | The plan names exactly `test_adaptation_factory` and `test_factory_registration` as the inner suite, excludes `test_factory_qualification`, records the full planned/executed IDs and requires each once with no skip/expected failure/unexpected success/error/failure. Negative tests cover omission/duplication/skip; Task 1 still requires all existing 20 tests to reach their assertions. | Resolved at plan/spec level. |
| F4: historical serialization path | Plan Task 1 Step 1 now supplies fixed regression rows via explicit `cases`, constructs approval/review inputs directly, and forbids `reviewed()` and default `evidence()` for historical vectors. Matching design text preserves fixed historical inputs as serialization-only. The existing None/default preservation requirements retain the historical path. | Resolved at plan/spec level. |

**No remaining blocker from this four-finding recheck.** The limited implementation plan is ready for formal approval. This is document-level resolution only: the implementation must still demonstrate these gates, preserve explicit-None behavior, capture real execution artifacts, pass the prescribed tests and receive independent code review. It grants no code qualification, actual human review, deployment, provider, installation or broader project-completion status.
