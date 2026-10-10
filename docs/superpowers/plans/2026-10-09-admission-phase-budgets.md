# Admission Phase Budgets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete final observation after a slow valid registered run without
extending original authority or renewing per-operation timeouts.

**Architecture:** Retain the ingress cutoff and exact parent identity. Derive
one parent-clipped final phase after engine return; thread it through captures,
route join and claim write. Leave uncertainty and accounting unchanged.

**Tech Stack:** Python, stdlib unittest/SQLite, existing runtime only.

**Spec:** `openspec/specs/registered-admission-timing/spec.md`; archived design:
`openspec/changes/archive/2026-10-09-registered-admission-phase-budgets/design.md`.

## Global Constraints

- Original parent context and durable timing remain unchanged.
- Initial controls retain original-start five-second ceiling.
- One final phase is at most five seconds and either original remaining bound.
- No repeated execution, debt reset, recovery, provider calls or dependency changes.
- Only product module `host_admission.py` and its test module may change.
- Frozen assessment at `8e8c9f9` is historical; never rebuild it from fixed code.

## Review Focus

- A real effect completed after five seconds must not create a false pending claim.
- Individually fast final operations must not renew a shared phase timeout.
- UTC/monotonic drift must not extend original parent authority.
- Mutation of original context or resource association must still deny access.
- Late persistence failure must not erase imported debt or invite engine replay.

## Task 1: Separate final observation from ingress timing

**Files:** Modify `runtime/src/proofkey/host_admission.py`;
test `runtime/tests/test_host_admission.py`.

**Interfaces:** Consume existing `ExecutionContext`, real registered fixture and
`RegisteredAdmissionOwner.run`. Produce internal phase derivation and shared
phase plumbing only; all public method signatures and durable schema remain.

- [x] Read the spec/design and prior real probe report. The probe is evidence,
  not a test substitute. Use the fixture from `test_host_admission.py` with real
  factory, engine, stores and actual reschedule effect.
- [x] Write RED: advance only the trusted synthetic pacing clock so actual
  engine work finishes beyond five seconds inside a 120-second parent. Assert
  returned authorized/verified result, one effect, observed claim/route,
  unchanged durable parent timing and successful clean reopen. For example,
  the final checks must include literal outcomes:

  ```python
  self.assertEqual(result.status, 'authorized')
  self.assertEqual(claim.state, 'admission_observed')
  self.assertEqual(route.state, 'admission_observed')
  ```

  Follow real result interfaces, not copied mock output. Record failing command
  and original output before changing product code.
- [x] Implement a small internal helper deriving a final phase after checking
  original parent/identity. Compute a finite duration bounded by 5 and both
  original remaining clocks; never use a new 120-second window. Separate the
  identity/parent guard from the ingress-only cutoff. Keep durable execution
  serialization from the original object. Pass one phase object through all
  final capture/join/write operations; recheck parent around publication.
- [x] Add behavior regressions for original parent expiry, total phase
  exhaustion (each stage individually below 5), backwards UTC/monotonic,
  changed original context, and late failure retaining effect/debt. Use narrow
  clock/persistence boundary faults; do not replace the engine with a stub.
  Existing ingress expiry and association tests must continue to pass.
- [x] Run focused RED/GREEN with the qualified interpreter and no bytecode:

  ```sh
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=runtime/src:runtime/tests /Users/nbk/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -B -m unittest discover -s runtime/tests -p test_host_admission.py -v
  ```

- [x] Self-review. Run full runtime discovery once on final candidate with the
  same environment and `-m unittest discover -s runtime/tests -v`. Preserve raw
  output. Existing baseline has 17 failed/error selectors: do not hide, fix by
  repinning, or label whole suite green. Compare selector sets against
  `outputs/proofkey_runtime_panel_2026-10-09/test_evidence.json`.
- [x] Write full report with actual RED/GREEN/full commands, outputs, changed
  files, self-review and caveats. Root owns commits, final review, spec updates
  and archive. Do not spawn subagents or modify Git. Independent reviewers get
  this brief, your report and a frozen diff.

## Controller completion

Verify changed files and focused test result; independent spec/quality review
before integration. Resolve important findings via original author and scoped
re-review. Record full-suite status truthfully, synchronize docs and archive
only this leaf OpenSpec change. No merge/push/publication or provider regrade.

Completed in `15453e1`: module 34/34, root regressions 3/3, independent review
PASS. Full runtime 1,622 tests / 1 failure + 16 errors; same 17 prior selectors,
not a green suite. One minor short-positive-parent boundary test is deferred.
The timing leaf was archived; the parent project and branch remain open.
