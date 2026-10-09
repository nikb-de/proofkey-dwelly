# Synthetic Factory Registration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore current-source factory regression coverage without changing historical evidence or granting activation authority.

**Architecture:** An optional immutable trusted-host registration binds exact source pins and synthetic provenance to new proposals and staged manifests. A separate fresh-process verification lane binds current execution evidence to the inspected snapshot. The historical default remains byte-compatible.

**Tech Stack:** Existing Python 3.12 runtime, dataclasses, SHA-256, unittest, existing isolated API-test environment; no new dependencies.

**Spec:** `openspec/specs/synthetic-factory-registration/spec.md`. Completed change and design: `openspec/changes/archive/2026-10-09-synthetic-factory-implementation-registration/`.

**Completion:** Implemented in `94b0eec` and `ecf36ac`; independently reviewed; 1,685 complete-suite tests passed. See [verification record](../../verification/2026-10-09-factory-registration.md). This closes the approved leaf, not the wider remediation program.

## Global Constraints

- Preserve `REGISTERED_IMPLEMENTATIONS`, `REGISTERED_SUPPLEMENT_HASH` and all None/default canonical byte recipes.
- This registration is trusted host configuration, never authority supplied by case content, candidate material, environment variables or an LLM.
- Exact class/container/string types; six exact historical logical paths; lowercase 64-hex digests; ID pattern `[a-z0-9][a-z0-9._-]{0,127}`; provenance `local_controlled_synthetic`.
- Explicit path only: at most 2 MiB per source and 12 MiB total. Canonical order is sorted logical path.
- No engine, adapter, profile, process, permission, activation, migration, actual-review or provider behavior change. No live calls, installations, global monkeypatch or rewritten historical receipts.
- New outputs are synthetic and do not establish full runtime closure, an authentic human review, new-process dispatch or a timed adaptation pass.
- The qualification child MUST have `sys.flags.optimize == 0`; reject inherited optimized mode and remove `PYTHONOPTIMIZE` from the fresh child's environment. Otherwise the existing behavioral helper's `assert` checks disappear.
- Root owns commits and final full-suite verification. Authors run focused tests, preserve raw results and do not dispatch subagents.

## Review Focus

1. Registration alias/mutation/subclass attacks cannot change retained authority.
2. Every material-resolution call and staging uses the same registration.
3. Equal bytes under another ID cannot reuse proposal/regression/review evidence.
4. Literal current pins are independent from supplied material; legacy golden vectors cannot masquerade as current behavior.
5. Disk identity cannot substitute for loaded-module identity; a fresh-process manifest binds exact generated artifact bytes and failures.

## Task 1: Immutable opt-in registration, provenance binding and real factory tests

**Files:**
- Modify `runtime/src/proofkey/factory/proposal.py`
- Modify `runtime/src/proofkey/factory/release.py`
- Modify `runtime/src/proofkey/factory/__init__.py`
- Modify `runtime/tests/test_adaptation_factory.py`
- Create `runtime/tests/test_factory_registration.py`
- Create `runtime/tests/fixtures/factory-current-registration-v1.json`
- Create `runtime/tests/fixtures/factory-legacy-vectors-v1.json`

**Interfaces:**
- Export `SyntheticImplementationRegistration(registration_id: str, provenance: str, implementations: tuple[tuple[str, str], ...])` as a frozen/slotted dataclass.
- Append `FactoryContext.implementation_registration: SyntheticImplementationRegistration | None = None`.
- `_material_proposal(material, implementation_registration=None)` receives the normalized host registration. All four existing call sites must pass it consistently.
- Current test helper `factory_for` accepts an explicit registration override including None; its default uses the independently fixed fixture. `current_registration()` loads literals, never hashes material to create expected authority.

- [x] **Step 1: Capture historical reference vectors before implementation and record baseline RED.**

Use `git show 336b0bb0f9b9e2b6118c34de825200c80764fd2e:runtime/src/proofkey/<path>` to recover the six historical source blobs into memory for serialization-only input. Build fixed supported-control material with current unchanged factory code; capture the full canonical proposal body, proposal hash, regression/approval inputs and staged manifest/receipt bytes. Supply fixed synthetic regression rows directly via `evidence(..., cases=...)`, and construct the approval/review event explicitly. Do not call `reviewed()` or the default `evidence()` for historical vectors: both would execute current behavior against historical material. Store literal vectors with source commit and an explicit `serialization_only` scope. No historical execution claim. The golden test must compare fixed values, not recompute its expectation from the implementation under test.

Run existing `test_adaptation_factory` before edits and save its actual errors. Add a behavioral test for explicit registration accepting current literal-pinned material. Before implementation, test the absent API with `getattr` and an assertion, so RED is a deliberate missing-feature assertion, not a loader failure:

```python
import proofkey.factory as factory_api
self.assertIsNotNone(getattr(factory_api, 'SyntheticImplementationRegistration', None))
```

- [x] **Step 2: Add the fixed current registration fixture and validation cases.**

Fixture ID: `synthetic-factory-current-69738ea-v1`; provenance: `local_controlled_synthetic`. Use these independently observed literals, checking their correspondence to current bytes without replacing them if drift is found:

```json
{
  "adapters/operator.py": "3bb88235beadb76d2edc7df7b2abf2bc238cd59429ea53e13f791b1e2fa3a911",
  "adapters/world.py": "c14e5c7de9beed90592851b01b8b336e9be506f4cf922179173319fd7c042b00",
  "verifier.py": "4b2aec813c49357026af396c549cada52889343b8c44a90c49d470d5eb5f4de2",
  "packet_contracts.py": "aa4db417d8cfcbf84421ad15734cb954e0abf767acd920e04efae11b68a6ceeb",
  "process.py": "9aab2b58826fe6d23e4f54f4e3a39a67a46767f0e5f61321dd91555cf90b8d09",
  "profiles.py": "ee38eece0dae3dcdfb7aba4bb8d2397bee0ddee574d86223574979b74126306e"
}
```

New tests must cover None rejecting current bytes; unchanged historical vectors; valid explicit material; reordered pins; malformed/empty/oversize ID; wrong provenance; subclasses; lists/dicts/nested mutable aliases; duplicate/missing/extra/relative/absolute alias paths; invalid hash; one-byte source drift; missing/extra/duplicate source; explicit source size ceilings. Expected error for invalid registration is `invalid_implementation_registration`, mismatch is `unsupported_adapter_implementation`, oversize is `material_limit_exceeded`.

- [x] **Step 3: Implement the bounded immutable host value and thread it through all resolution paths.**

```python
@dataclass(frozen=True, slots=True)
class SyntheticImplementationRegistration:
    registration_id: str
    provenance: str
    implementations: tuple[tuple[str, str], ...]
```

Validate before material normalization in `AdaptationFactory.__init__`; retain a detached sorted tuple of exact immutable primitives. With None, execute the old checks/body unchanged. With an explicit registration, bound and hash exact source bytes and compare the complete observed map with registered pins; no partial matches.

Only on the explicit path add this exact object to the internal proposal body:

```python
pins = [{"path": path, "sha256": digest} for path, digest in sorted(registration.implementations)]
registration_body = {
    "registration_id": registration.registration_id,
    "provenance": registration.provenance,
    "inventory_sha256": sha256(canonical(pins)).hexdigest(),
}
```

Copy that resolved body's `implementation_registration` object into the staged manifest before calculating release hash. Do not rebuild it from caller data. Preserve every existing denial, including non-v1 dispatch and pending-intent staging.

- [x] **Step 4: Prove cross-registration separation and current behavioral coverage.**

Tests compare proposal/stage hashes under two IDs with identical pins; reject each other's proposals, regression bindings and simulated-review evidence in both directions. Verify prepare/resolve/check/stage all use one registration and returned material cannot mutate it. Add an explicit golden digest vector for the registration object. Existing 21 factory tests must reach their intended assertions; do not weaken reason checks or skip any test.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=runtime/src:runtime/tests .superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python -B -m unittest test_factory_registration test_adaptation_factory -v
```

- [x] **Step 5: Self-review and report, then root obtains independent review and commits.**

Report exact commands, raw RED/GREEN paths, counts, source fixture checks, historical vector provenance, changed files and any limits. No broader source requalification claim. Root's independent reviewer checks both the diff and relevant semantic changes from historical to current six-source inventory; record what was inspected and what remains outside scope.

## Task 2: Fresh-process current-source evidence and complete qualification baseline

**Files:**
- Create `runtime/scripts/qualify_factory.py`
- Create `runtime/tests/test_factory_qualification.py`
- Modify test-only helpers in `runtime/tests/test_adaptation_factory.py` only if needed for exact artifact capture.
- Root writes `docs/verification/2026-10-09-factory-registration.md` after actual results.

**Interfaces:**
- `qualify_factory.py --output ABSOLUTE_NEW_DIRECTORY` runs one fixed synthetic factory lane; no arbitrary module, provider, registration or code argument.
- Factored preflight accepts only a selected repository root and the fixed fixture; reject preloaded pinned modules before import. Output is a new directory; no overwrite/recovery of an existing result.
- Output schema: `status`, `registration`, `python`, `distributions`, `source_before`, `source_after`, `source_stable`, `imports`, `tests`, `artifacts`, `limitations`. Artifacts retain raw canonical bytes plus SHA-256, kind, proposal hash, regression execution ID when present, and stage hash when present.
- Inner suite is exactly `test_adaptation_factory` plus `test_factory_registration`. The outer `test_factory_qualification` module is NEVER loaded by this child. Collect the full inner test-ID inventory before execution; require all IDs to run once, zero skips, zero expected failures, zero unexpected successes, zero errors and zero failures before reporting success.

- [x] **Step 1: Add failing preflight, import-identity and capture tests.**

Cover preloaded module (including an object claiming the correct `__file__`), wrong local module origin, optimized interpreter, changed pinned source, changed broader inventory including added/untracked executing files, skipped/omitted/duplicate test ID, failure during tests, missing artifact and existing output directory. Negative tests must not mutate the checkout or generate fake passing receipts. Use temporary copies for controlled source drift. Show that a disk hash match does not bless a previously loaded module.

```python
def test_optimized_child_cannot_emit_pass(self):
    result = self.run_lane(extra_python_args=("-O",))
    self.assertNotEqual(result.returncode, 0)
    self.assertEqual(self.read_manifest(result)["status"], "invalid")

def test_inner_suite_is_non_recursive_and_complete(self):
    result = self.run_lane()
    manifest = self.read_manifest(result)
    self.assertEqual(manifest["tests"]["planned_ids"], manifest["tests"]["executed_ids"])
    self.assertTrue(all("test_factory_qualification" not in name
                        for name in manifest["tests"]["executed_ids"]))
    self.assertEqual(manifest["tests"]["skipped"], [])
```

These two test helpers belong to the new qualification test class; `run_lane` launches the declared current interpreter and `read_manifest` reads its result directory. A failed launch without a manifest is itself failed capture, never a pass.

- [x] **Step 2: Implement one bounded fresh-process lane using existing test behaviors.**

Bootstrap with standard library only. Reject optimized invocation, then re-execute in the same declared interpreter using `-B`, no `PYTHONOPTIMIZE`, and a newly empty private `-X pycache_prefix=...` directory before importing runtime/tests. Assert the child's optimization flag is zero before any helper runs. Verify fixed six pins and capture the runtime source/test/profile/fixture inventory, including new or untracked files, the qualifier itself and its registration/golden fixtures; do not use `git ls-files` alone. Reject symlinked/aliased inventory entries and keep paths relative to the selected root. Assert pinned modules are absent.

Then load exactly the two inner factory test modules, retain their complete test-ID inventory, and check the origins and retained object identities of the six pinned modules plus all loaded project-local modules (including factory, contracts, support and test helpers) against inventoried files under the selected root. External dependencies belong in the declared distribution inventory, not the local-source closure claim. Run every planned inner test exactly once and require no omissions/skips. Execute a supported-control flow explicitly to retain its exact proposal, regression, simulated approval, review packet and staged manifest bytes with one unique execution ID. It remains synthetic, not actual human approval. The separately exercised non-v1 candidate must remain unavailable.

After execution, repeat the entire file inventory and local import-origin/identity checks, including files/modules added during execution. Finalize a successful manifest only after all checks and test-ID accounting pass; on failure emit an explicit invalid/failed record without a qualification claim. Bind exact emitted artifacts into the manifest. File/module checks are evidence for trusted fixed tests, not hostile-code isolation or proof against invisible transient in-process mutation.

- [x] **Step 3: Focused tests, independent review, root full suite.**

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=runtime/src:runtime/tests .superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python -B -m unittest test_factory_qualification test_factory_registration test_adaptation_factory -v
```

Root runs the new script into a fresh output directory and checks exact bytes/manifest joins. Root then freezes the candidate and runs the complete runtime suite once with the existing isolated API environment, collecting raw output and pre/post inventory. A green suite closes only the baseline item, not adaptation, install, human review or the wider project.

- [x] **Step 4: Record limitations, archive only the completed registration leaf.**

Preserve the original five-provider bundle and historical factory constants. Archive the leaf only after tests/review/manifest verification complete; keep the broader judge-remediation and harness changes open. Return exact local commits, evidence paths and the next unresolved J-IDs. No merge, push, publication or provider regrade.
