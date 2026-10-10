# J05 Task 5 pre-freeze code checkpoint

Status: **DONE_WITH_CONCERNS — pre-freeze source checkpoint ready for independent review; final qualification pending.**

This is not Task 5 completion, a final source freeze, or a qualification receipt. The final fixture intentionally does not exist. No full discovery or final positive lane execution was attempted.

## Commits and scope

- Assigned comparison base: `32729dccc61ee3e7ce548e91ca4a0b7a14d137c1`.
- Controller's reviewed receipt-grouping amendment: `a3f2c63d562e64549198185687e52f43e249eab0`.
- This worker's implementation checkpoint: `676a65af8fc2536eba70d35f636bf9a268d114c6` (`test: add explicit J05 source qualification lanes before freeze`).
- Report is committed separately after that implementation checkpoint so the implementation commit is named without a self-reference.
- Worktree: `/Users/nbk/.codex/worktrees/proofkey-runtime/Pitch project`.
- Interpreter: `.superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python`.
- Execution environment: `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=runtime/src:runtime/tests`; standalone scripts derive the source paths themselves.

Eight external source files are owned by this checkpoint:

1. `runtime/tests/support_factory_lanes.py` — fixed J05 fixture loader, exact six-path current comparison registration, explicit immutable contexts.
2. `runtime/tests/test_adaptation_factory.py` — required keyword registration arguments; lazy comparison registration in every affected behavioral call.
3. `runtime/tests/test_factory_registration.py` — current comparison assertions and separately retained historical serialization digest/vector checks.
4. `runtime/tests/test_factory_current_v1.py` — four explicit current/historical/default comparison tests.
5. `runtime/scripts/qualify_factory.py` — closed legacy/current selectors, complete current package/resource preflight, source/import identity, sorted exact-ID selection, per-test raw result records, nonrecursive child guards, shared artifact validation.
6. `runtime/scripts/qualify_window_readiness.py` — fixed eight-module J05 source-only runner, full source registration, explicit eight-group receipts, full planned-ID digest, captured fit gate, bound staging artifacts.
7. `runtime/tests/test_factory_qualification.py` — explicit current lane in positives/adversarial runs, successful untouched controls, exact fixture ID expectations, existing-ID mutation seams, default legacy/unknown-lane negatives, separate added-module/added-test cases.
8. `runtime/tests/test_window_readiness_evidence.py` — outer-only J05/bounded guard tests and copied-root adversarial cases.

No package modules, resources, old fixtures/vectors, producer helper, stop-v2 tests, implementation pins, task status, living specs or archive state were changed by this worker. The controller separately made the grouping documentation amendment above. `git diff --exit-code BASE -- runtime/src runtime/profiles runtime/tests/fixtures/factory-current-registration-v1.json runtime/tests/fixtures/factory-legacy-vectors-v1.json runtime/tests/test_observed_stop_v2.py runtime/tests/support_window_readiness.py` exited 0.

Historical fixture SHA-256 remains `6dfa8a42dbf22bce5c6ecb94cfe3de40d88b2ec00ba4cbadeeb513b703e0be8f`; historical vector SHA-256 remains `bed676874ec36d8e0673654aa56a1ecd5104831ae4c72fcbc1962117656a1d14`. AST/source inspection confirmed the complete `test_legacy_serialization_matches_prechange_literal_vectors` method is byte-identical to BASE and both behavioral modules contain zero implicit `factory_for`/`reviewed` calls.

## Evidence location and verification

All retained new evidence is in the fresh parent:

`/Users/nbk/.codex/worktrees/proofkey-runtime/Pitch project/outputs/window-readiness-final-6lO88JFq`

The parent contains earlier attempt logs, final bounded logs, explicit pre-freeze invalid runner manifests, the candidate test-ID list, and the receipt-ceiling discovery/adjudication note. Its test-ID JSON is labelled **pre-freeze review candidate, not expected pins** and includes no implementation hashes.

### Fresh bounded green checks

Command (recorded verbatim with complete output in `approved-grouping-bounded-tests.log`):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=runtime/src:runtime/tests .superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python -B -m unittest test_window_readiness_evidence.WindowReadinessEvidenceTests test_factory_current_v1.CurrentSourceV1ComparisonTests.test_default_registration_rejects_current_source test_factory_current_v1.CurrentSourceV1ComparisonTests.test_historical_registration_rejects_current_source test_factory_registration.FactoryRegistrationTests.test_historical_fixture_serialization_digest test_factory_registration.FactoryRegistrationTests.test_legacy_serialization_matches_prechange_literal_vectors test_factory_registration.FactoryRegistrationTests.test_none_keeps_historical_admission_and_rejects_current_bytes test_factory_qualification.FactoryQualificationTests.test_default_lane_rejects_changed_current_source test_factory_qualification.FactoryQualificationTests.test_unknown_lane_rejected_before_execution -v
```

Result: exit 0; **18 tests, 18 passed, zero skips or expected failures**, unittest duration 2.961 seconds. These checks cover default/old-registration denial, historical serialization, independent literal closure, closed selection, exact accounting, real subprocess launch-count audit, nested entry rejection, and all-record receipt grouping. They do not stand in for the unexecuted final positive suite.

`git diff --check` and `git diff --cached --check` exited 0. All eight owned Python files were compiled from their bytes using `compile(..., 'exec')` with no cache writes. Unit imports also compiled the final grouping/runner changes.

### Deliberately retained missing-fixture REDs

Command (complete output in `approved-grouping-pending-fixture-reds.log`):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=runtime/src:runtime/tests .superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python -B -m unittest test_factory_current_v1.CurrentSourceV1ComparisonTests.test_fixed_current_lane_executes_supported_v1 test_factory_current_v1.CurrentSourceV1ComparisonTests.test_comparison_identity_does_not_claim_historical_source test_factory_qualification.FactoryQualificationTests.test_inner_suite_is_non_recursive_and_complete test_window_readiness_evidence.WindowReadinessRunnerTests.test_exact_j05_execution_and_bound_artifacts -v
```

Result: exit 1; **4 tests, 2 failures and 2 errors**, all explicitly caused by `fixed fixture unavailable: final J05 freeze pending`; unittest duration 0.709 seconds. Exact cases:

- `CurrentSourceV1ComparisonTests.test_fixed_current_lane_executes_supported_v1`
- `CurrentSourceV1ComparisonTests.test_comparison_identity_does_not_claim_historical_source`
- `FactoryQualificationTests.test_inner_suite_is_non_recursive_and_complete`
- `WindowReadinessRunnerTests.test_exact_j05_execution_and_bound_artifacts`

No skipped/expected-failure decoration or workaround fixture masks these gates. All other fixed-fixture-dependent positives/adversarial cases remain unexecuted and pending; no all-green discovery claim is made.

Two standalone **pre-freeze negative probes** also ran, each exiting 1 in approximately 0.2 seconds:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 .superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python -B runtime/scripts/qualify_factory.py --lane current-source-v1-comparison-v1 --output '/Users/nbk/.codex/worktrees/proofkey-runtime/Pitch project/outputs/window-readiness-final-6lO88JFq/prefreeze-current-v1'
PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 .superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python -B runtime/scripts/qualify_window_readiness.py --output '/Users/nbk/.codex/worktrees/proofkey-runtime/Pitch project/outputs/window-readiness-final-6lO88JFq/prefreeze-j05'
```

Both retained manifests have `status=invalid`, the explicit selected lane, `role=child`, one launcher child event, the missing-fixture reason, and empty tests/imports/artifacts. They issued no qualification or staging receipt. These probes are not the final lanes.

### Development RED/GREEN history and corrections

Initial new API tests exposed missing lane/expected-ID arguments and the absent new runner. An initial test imported the stop-v2 tuple from the wrong module; that test setup error was corrected to `host_admission`. A mixed-module run exposed the preloaded-module guard preceding a missing-fixture test; the test now uses a fresh subprocess. Static closure checks initially overreached into CLI `main` and unrelated, unselected workflow TestCases; the check now permits the known `proofkey.cli.main` entry and examines selected tests plus imported helper code without selecting unrelated TestCases. Subsequent bounded closure checks pass.

Self-review found the unchanged factory ceiling: `factory/proposal.py:178-181` rejects more than 128 required receipt cases, while full J05 selection has 156 tests. The worker stopped before changing granularity; the controller adjudicated and committed the precise eight-group contract. A bounded test failed before grouping existed and now passes against the approved implementation. No factory/schema/cap changed.

## Exact execution versus receipt grouping

Candidate enumeration (not the final fixture) currently contains:

| Lane | Selected test count | Module breakdown |
| --- | ---: | --- |
| Current v1 comparison | 42 | adaptation 21, registration 17, current-v1 4 |
| J05 | 156 | window registration 15, envelopes 28, engine 24, composition 18, adaptation 21, factory registration 17, current-v1 4, observed-stop-v2 29 |

The J05 receipt has exactly eight `module:<name>` required cases in literal module order. Each hash covers canonical JSON of that module's complete ordered `{case_id, output_hash, raw_utf8}` records. Every raw record must hash correctly and parse to a canonical matching passed test result. Missing/extra/reordered/duplicate/failed records and empty/unknown groups deny. The complete expected sorted ID list is separately committed by `planned_test_ids_sha256` in proposal tests JSON. **156 executed tests is not relabelled as eight tests.** Manifest denominators are explicit.

The fixture remains the exact five-key design: registration, candidate file hash, six-file comparison digest, current-v1 IDs, J05 IDs. No worker generated that fixture or any final expected package hashes.

## Outcome boundaries at this checkpoint

### Default v1

Affirmative negative passed: invoking the script without `--lane` rejects changed source with `pinned source mismatch`, empty behavioral artifacts, and unchanged old fixture selection. Explicit None and old historical registrations likewise reject current source. Literal historical vector reconstruction still passes.

### Current-source v2

The unchanged stop-v2 test module is included in the proposed exact J05 suite. It has not been executed by this worker during this checkpoint. Its historical tuple and equality test are unchanged; no historical executable qualification is inferred.

### Candidate in-domain behavior

The fixed runner is implemented, but its final positive path remains pending the independently reviewed fixture. This worker makes no new candidate business-behavior pass claim from missing-fixture runs.

### Candidate out-of-domain denials

The selected envelope/engine modules contain the producer's existing negative checks. They have not been rerun here as final J05 evidence. The scope remains all conjunctive limits: complete UTF-8 at most 262144 bytes, container depth at most 16 with root object at 1, observations at most 128, identifiers/revisions/reason at most 1024 Unicode code points, and at most 128 evidence occurrences counting repeats. No fallback, truncation, relaxed bound, observation/effect deletion, resend or undo is introduced.

### Calls, active time and tool time

No final fit result was measured here. The J05 runner will require captured real `J05_TIMING` records for both library and CLI, 15 calls in each existing positive scenario, no more than 120 active seconds, no more than 10 elapsed seconds per tool, and positive remaining parent time. Missing or failed fit remains an explicit blocker. Bounds are not raised. All-source final behavior must still establish the full gate.

### Unchanged goods/other paths

The existing current-v1 behavioral controls are selected explicitly. Their final positive execution remains pending the fixed comparison registration. Default source denial and serialization checks alone do not prove those positives.

## Self-review and remaining gates

Checked now: external-only scope; required explicit contexts; fixed current loader; old fixture/vector preservation; 86-name literal closure; fixed nonrecursive module tuples; exact sorting/coverage checks; no load_tests discovery; child-role/launcher-count audit; source/import identity and drift accounting; raw per-test output grouping; distinct test/group denominators; unavailable old non-v1 candidate retained; no fixture synthesis from submitted material.

Still required, in order:

1. Independent code review of this checkpoint and the controller's grouping amendment; address any findings.
2. Controller-directed final freeze: independently review/fix the exact 86 hashes, candidate resource/profile/process/policy commitments, six-file digest, and complete sorted 42/156 test-ID lists into the fixed five-key fixture.
3. Focused current-v1/J05 positives and all copied-root adversarial cases, including optimization, source drift/aliasing, import/helper replacement, binding/hash/registration changes, test addition/omission/skip/failure, receipt mutation and missing artifacts. Most of these deliberately require a successful untouched current control and have not executed before freeze.
4. Required all-green full discovery, then final standalone current-v1/J05 lanes on frozen source with complete evidence. No final full discovery was run here.
5. Independent final evidence review, child-only strict OpenSpec validation, and controller-owned status/archive work. Parent J05 and historical acceptance remain open.

The scripts' source/import accounting describes observed local source and installed distribution identity, not hostile-code isolation or complete transitive runtime closure.

## Historical pending-state gate and exclusions

Historical pending preservation remains **unqualified**. The known completed-only J06 pair is the executable `/private/tmp/proofkey-j06-0yc_36hd/installed-env/bin/python` with original root `/private/tmp/proofkey-j06-installed-80e0d6f-attempt5/probe/library-window/case-feb2ba2f2de14021894506f99484d9c8`. Current availability, authority and deadline support remain unestablished. This worker did not open, execute, copy, repin or reuse either root.

A completed phase with processing_status=pending, a fresh fixture, relocated package, copied root or recreated grant cannot establish pending preservation. Only separately authorized evidence from an independently identified already-pending original pair can change that conclusion.

No installation, network, native HTTP, live provider, actual human approval, activation, migration, retained resolver or completed timed drill occurred. Current-source task completion cannot close that historical gate or parent J05.
