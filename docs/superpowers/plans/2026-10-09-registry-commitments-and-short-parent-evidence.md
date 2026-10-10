# Registry Commitments and Short-Parent Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox syntax for tracking.

**Goal:** Close J22/J32 without widening runtime authority, then freeze evidence for the approved named-provider reassessment.

**Architecture:** A validated public projection replaces private inventory coupling. Real-engine tests cover the existing final-observation phase with a short residual parent window.

**Tech Stack:** Existing Python 3.12.14, standard library/unittest, existing isolated environment. No new dependencies.

**Spec:** archived at `openspec/changes/archive/2026-10-09-registry-commitments-and-short-parent-evidence/specs/`, with living requirements in `openspec/specs/`; approved design at `docs/verification/judge-remediation-2026-10-09/next-cycle-design.md`.

## Global Constraints

- Preserve canonical wire bytes, registry digest recipes, exactly-one-release composition, original execution authority and uncertain-effect retention.
- Return exact built-in tuples and strings, not release objects, resource paths, authority handles or full declaration bytes.
- Validate the actual current retained records; no stale independent cache concealing replacement of `_releases`.
- At most 32 records, nonempty bytes with at most 8 MiB per release and 32 MiB total before parsing any envelope; sorted unique matching outer/embedded IDs.
- No engine, profile, process, permission, activation, migration, provider or storage-schema change. J32 is test-only unless a newly reproduced defect is first escalated.
- Root owns commits and runs the final full suite once. Authors run focused tests, preserve raw evidence under this plan's workspace, and never dispatch subagents. Do not read/write another SDD workspace except the explicitly referenced existing Python interpreter.
- Do not stage `outputs/` broadly; historical receipts and five-provider results are immutable.

## Review Focus

1. Replaced valid envelopes must not evade owner entry checks (Task 1).
2. Bounds must precede parse, including corruption of frozen internals (Task 1).
3. Multi-release route inventories must not widen host composition (Task 1).
4. Byte/digest compatibility must survive inventory migration (Task 1).
5. Outer parent rejection must not mask an incorrectly generous phase (Task 2).

## Task 1: Public inventory and admission migration

**Files:** Modify `runtime/src/proofkey/registered_releases.py`, `runtime/src/proofkey/host_admission.py`, `runtime/src/proofkey/admission_routes.py`, `runtime/tests/test_release_route_foundation.py`, `runtime/tests/test_host_admission.py`.

**Interfaces:** Produce `ReleaseRegistryV1.commitments(self) -> tuple[tuple[str, str], ...]`. Consumers: `validate_composition`, `RegisteredAdmissionOwner.__init__/check`, `AdmissionRouteStoreV1.__init__`. Existing helpers `registration_inputs`, `registry_at`, `literal_envelope`, `rehash`, `fixture`, `context`, `paced_clock` remain available.

- [x] **Step 1: Capture deliberate missing-contract RED.** In `test_release_route_foundation.py`, assert callable `getattr(registry_at(root), 'commitments', None)` before calling it. Add behavior tests for deterministic exact tuple/string projection, sorted two-release inventory via `dataclasses.replace(artifact, release_id='L2')`, detached old snapshot, invalid exact types and malformed/empty/oversized/duplicate/unsorted/relabeled records using controlled `object.__setattr__`. Envelopes are built by the existing independent literal fixture for expected digests; do not derive the expected projection through `commitments()` or the serializer under test.

```python
self.assertTrue(callable(getattr(registry, 'commitments', None)))
expected = (('L1', literal_envelope(root)['artifact_hash']),)
self.assertEqual(registry.commitments(), expected)
self.assertIs(type(registry.commitments()), tuple)
```

- [x] **Step 2: Implement projection using existing validation.** Exact self/container/pair/ID/bytes checks and all count/byte bounds precede parsing. Then validate each `RegisteredReleaseV1(raw)`, check outer/embedded identity, sorted uniqueness, return fresh tuples with the actual artifact hash. Use existing checked exception conventions; do not change old serializers, hashes, `resolve()` unknown-ID behavior or resource semantics.

```python
@_checked
def commitments(self) -> tuple[tuple[str, str], ...]:
    _require(type(self) is ReleaseRegistryV1)
    records = self._releases
    _sequence(records, 32, minimum=1, tuple_only=True)
    total = 0
    for pair in records:
        _require(type(pair) is tuple and len(pair) == 2)
        _id(pair[0])
        _require(type(pair[1]) is bytes)
        total += len(pair[1])
        _require(0 < len(pair[1]) <= 8 * _MIB and total <= 32 * _MIB, 'limit')
    names = tuple(name for name, raw in records)
    _require(names == tuple(sorted(set(names))))
    result = []
    for name, raw in records:
        release = RegisteredReleaseV1(raw)
        _require(_parse(raw)['release_id'] == name)
        result.append((name, release.artifact_hash))
    return tuple(result)
```

Use the existing checked error conventions. Review the concrete implementation against the helper contracts before copying; the spec, not this illustrative spelling, is binding.

- [x] **Step 3: Migrate consumers and exercise their real outcomes.** Composition requires `len(commitments)==1` and the binding ID/hash match; retain public resolution and every existing executable/resource/review check. Owner stores detached commitments and compares a newly validated projection on entry, with exact registry type guard. Route store resolves every public commitment, cross-checks actual ID/hash, retains `_registered` and current digest recipe. No production private consumer remains outside the registry module.

Add two-release host rejection before effect, valid-envelope substitution after owner creation before new claim/debt/effect, invalid mutation denial, unknown-ID regression, and route stored raw/digest equivalence against independent fixture expectations. Preserve existing admission tests. Failure assertions inspect actual domain failures and durable absence/retention, not only mocked call counts.

- [x] **Step 4: Focused GREEN, cost observation, self-review and report.** Use the command below with `test_release_route_foundation test_host_admission`; retain stdout/stderr, timing and exact counts. Measure bounded repeated projection on representative one- and two-release fixtures without imposing an invented performance SLO. Include RED/GREEN, byte/hash evidence, limits, files changed and concerns in the task report. Root reviews and commits this task before Task 2.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=runtime/src:runtime/tests .superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python -B -m unittest test_release_route_foundation test_host_admission -v
```

## Task 2: Real short-parent evidence and candidate verification

**Files:** Modify `runtime/tests/test_host_admission.py` only. Root later records `docs/verification/2026-10-09-registry-commitments.md` and updates the remediation index after verification.

**Interfaces:** Existing `paced_clock(after_engine)`, `context`, `fixture`, real `_images`, `AdmissionRouteStoreV1.observe_admitted`, `_ClaimStore.write`. Task 1 changes no timing signature.

- [x] **Step 1: Add positive real-component tests.** Capture parent at tick 100 with 120 seconds. At real engine return set the test-clock state to `(216,+2)` and `(218,-2)` for UTC/monotonic limiting respectively. Both give a two-second phase. Forwarding spies call real methods and capture the context passed to final images, route observation and final claim write. Assert shared object, literal duration/cutoffs for each clock, unchanged parent, original durable timing, observed route and claim, and exactly one effect.

```python
def after_engine(state):
    state.update(tick=216.0, utc_offset=2.0)
# Expected captured UTC is epoch + 118s, monotonic 216; each phase deadline is +2s.
# The second case is tick=218/offset=-2: UTC epoch +116s, monotonic 218, also +2s.
```

- [x] **Step 2: Add expiry at real final persistence.** For both cases advance tick exactly two seconds immediately before forwarding the final `_ClaimStore.write` call. Expect timeout, observed route, `binding_sealed` claim, retained imported account and exactly one effect. Inspect actual stores; do not replace returned observations or results.

- [x] **Step 3: Prove sensitivity without changing production timing.** The new tests are characterization of correct existing behavior, not an invented bugfix RED. Run a temporary test-local mutation control that wraps `_observation_context` to grant five seconds; demonstrate the explicit phase assertions fail, then restore patch context and run GREEN. Preserve negative-control output and label it as test sensitivity, not baseline production failure.

- [x] **Step 4: Focused run and report.** Run the command below, retain raw output and report exact counts, clock arithmetic, persistence evidence and limits. Root commits after independent review. No source timing changes.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=runtime/src:runtime/tests .superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python -B -m unittest test_host_admission -v
```

- [x] **Step 5: Root-only final gate.** Run the complete runtime suite once on a frozen candidate with before/after source inventories and raw receipt. Run the current-source `qualify_factory.py` into a new directory and read back its manifest/artifact hashes. Obtain one whole-package review. Record limitations, mark J22/J32 only if their criteria are met, and use OpenSpec archive for this completed leaf. Do not archive umbrella changes. Freeze the next five-provider packet separately with no old scores or supplied answers.

## Completion evidence

Candidate `40138e1` passed 1,693 runtime tests in 888.064 test seconds with unchanged HEAD and all 246 runtime files. The fresh-process qualifier passed all 37 planned IDs, with all eight artifact hashes independently checked. The task reviews and final bounded architecture review were clean after the zero-byte preflight fix. OpenSpec archive completed; strict validation passed all six current items.

The fresh packet was reconstructed byte-for-byte: 327,124 bytes, SHA-256 `16544b8aba044168403910de948da22f04e1ef97493d2ce2a9b158da7def717c`. All five named seats answered; four were structurally eligible and AGY's invalid output shape remains uncorrected. Thirty findings were source-adjudicated; none reproduced a J22/J32 defect. No follow-up runtime change or second paid panel was justified.

Reports and raw/sanitized evidence: `outputs/proofkey_runtime_panel_2026-10-09_r2/`. The intact SDD workspace is preserved there as `implementation-review/`. Full report: `reports/ASSESSMENT.md`. Failed author assertions and the deliberate test mutation remain evidence, not erased or relabeled. Only J22/J32 close in this cycle; maximum-envelope performance, installed integration, process adaptation, protected evaluation and human/provider gates remain open.
