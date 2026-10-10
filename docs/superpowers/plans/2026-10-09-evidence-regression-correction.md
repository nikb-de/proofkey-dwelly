# Evidence Regression Correction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Correct the baseline test without changing production intake behavior.

**Architecture:** The existing engine and real catalog are the system under
test. Separate unavailable processing from denied evidence; test recovery and
the absence of processing/accounting/effects in both paths.

**Tech Stack:** Python 3.12, unittest, existing synthetic local runtime.

**Spec:** `openspec/specs/evidence-regression-expectations/spec.md` and
`openspec/changes/archive/2026-10-09-correct-evidence-regression-expectations/design.md`.

## Global Constraints

- Modify executable code only in `runtime/tests/test_engine_processing.py`.
- No changes to production code, access checks, factory pins or archived evidence.
- Use real catalog registration; do not fake successful admission or processing.
- All test data are synthetic; no providers, installations, servers or network.
- Retain immutable original request identity and zero processing/effect checks.
- Controller owns Git commits and the one final full-suite run; implementer runs focused suites only.

## Review Focus

- Well-formed missing IDs must be separate from malformed IDs.
- Access denial must use a real registered record with rejected scope.
- Recovery may authorize case observation, never rejected evidence access.
- Valid evidence must prove real stored bytes, not merely a mocked call.
- Test loops must identify the failed scenario using `subTest`.

### Task 1: Correct unavailable-processing and denied-evidence regression cases

**Files:**
- Modify: `runtime/tests/test_engine_processing.py`
- Read: `runtime/tests/test_engine_fresh_intake.py:396` (real catalog fixture)
- Read: `openspec/changes/proofkey-v21-harness-contracts/fresh-original-intake.md`

**Interfaces:**
- Consumes: `EngineFixture.fixture(request)`, `compose(fx, allowances)`,
  `fx.catalog.register(path, case_id, source, scope)`, real engine run/recover.
- Produces: independent positive and denied-reference tests; no runtime API.

- [x] **Step 1: Reproduce RED before changing the existing test.**

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=runtime/src:runtime/tests /Users/nbk/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -B -m unittest test_engine_processing.EngineProcessingInjectionTests.test_text_evidence_and_recovery_do_not_call_prepared_consumer -v
```

Expected: `AssertionError: 'denied' != 'authorized'` for malformed reference.

- [x] **Step 2: Split positive and negative cases.**

Keep a narrative case. Add a real registered original by writing synthetic bytes
to a temporary fixture file and registering it with `allowed_actors=['U1']` and
`scope_id='saved-scope'`. Bind its returned ID to a new request, update
`fx.request` and the world's request fingerprint before run. Assert original
bytes through the real catalog and saved request through the store.

For each of `unavailable-artifact`, `artifact-` plus 32 zeros (well-formed but
missing), and a real record whose scope ID is added to `fx.revoked`, require:

```python
self.assertEqual(result.model_dump(mode='json'),
    CaseResult(status='denied', correlation_id='C1', reason='denied').model_dump(mode='json'))
```

Run and recovery under a `plan_prepared` trap must not enter it. Use `subTest`
labels. Assert zero processing attempts, zero planner calls and zero reschedule
effects. Fresh run is denied; existing recovery performs no intake and returns
authorized case observation with unavailable media/processing, empty effects
and evidence refs. Trap catalog `get`, `read_original` and
`register_saved_narrative` during recovery to prove this is not evidence access.
Retain the original saved request identity. Both positive cases must check
unavailable processing in the saved checkpoint and unavailable media.

- [x] **Step 3: Run GREEN with focused coverage.**

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=runtime/src:runtime/tests /Users/nbk/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -B -m unittest test_engine_processing test_engine_fresh_intake -v
```

Expected: no failures/errors/skips. If another failure occurs, report exact
selector and output; do not broaden source edits.

- [x] **Step 4: Self-review and report.**

Write the full report to the dispatched report path with RED/GREEN output,
command, counts, files and limitations. Do not commit; controller reviews and
commits the exact test diff. The final full-suite run uses the existing isolated
API environment, and remaining factory failures must remain explicit.
