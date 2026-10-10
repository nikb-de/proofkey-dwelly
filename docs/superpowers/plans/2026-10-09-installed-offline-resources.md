# Installed Offline Resources Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Repair installation of the existing offline runtime and retain real outside-checkout evidence for the two fixed synthetic cases.

**Architecture:** Package byte-identical copies of existing data and change only the two built-in path roots. Keep host pinned reads, writable state and process authority unchanged. Verify ordinary installed filesystem packages, not zipped executables.

**Tech Stack:** Python 3.12.14, setuptools 84.0.0, existing exact runtime/API dependencies, unittest, wheel/sdist archive inspection, fresh venv and no-index installation.

**Spec:** `openspec/changes/archive/2026-10-09-installed-offline-resources/design.md` and `specs/installed-offline-resources/spec.md` in the same child. User approved this bounded design and execution on 2026-10-09. This plan elaborates the approved workflow without new interfaces or authority.

## Global Constraints

- Worktree: `/Users/nbk/.codex/worktrees/proofkey-runtime/Pitch project`; no edits to original checkout.
- Ordinary filesystem-installed wheel on observed macOS arm64 / CPython 3.12 only; no Linux/Windows/frozen-executable qualification.
- Exactly ten built-in profiles, two fixed host fixtures and the existing schema; unchanged canonical bytes, named-profile allowlist, release IDs, fingerprints and process semantics.
- Preserve `_pinned`, separate writable state, historical factory constants/vectors and unavailable `verify_release`.
- Acquire only the four approved missing pinned artifacts. Other locked wheels come from exact matching cache bodies. No upgrade or network dependency resolution, providers, public server, publication or submission.
- Use the existing source-test interpreter `.superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python`. Set `PYTHONDONTWRITEBYTECODE=1`, `PYTHONNOUSERSITE=1`; source tests use `PYTHONPATH=runtime/src:runtime/tests`.
- Root owns documentation, artifact execution and final verification. The implementation worker owns the listed Task 1 source/test files. No other worker edits them.

## Review Focus

- An unrelated working directory contains fake `profiles/` or `fixtures/`: installed built-ins must ignore it (Task 1 relocated-package regression, Task 2 actual installed probe).
- A packaged host file is missing, tampered, symlinked or hardlinked: existing host validation fails closed (Task 1 isolated copy tests).
- Historical factory serialization is replayed after path repair: bytes and historical pins remain unchanged (Task 1 existing factory-registration tests).
- The wheel or sdist accidentally includes a database, environment, private output or unplanned data: inspect exact archive membership, not only presence of expected files (Task 2).
- An exit-zero run has no verified business effects or writes under site-packages: independent persisted readback and before/after package inventory must catch it (Task 2).

---

### Task 1: Package resources and repair built-in roots

**Files:**
- Modify: `runtime/pyproject.toml`, `runtime/src/proofkey/profiles.py`, `runtime/src/proofkey/host.py`.
- Create: `runtime/MANIFEST.in`, `runtime/src/proofkey/resources/profiles/*.json` (the ten existing files), `runtime/src/proofkey/resources/fixtures/{packet-world-v1.json,host-goods-world-v1.json}`.
- Create: `runtime/tests/test_installed_resources.py`.
- Modify current identity only: `runtime/tests/fixtures/factory-current-registration-v1.json`, `runtime/scripts/qualify_factory.py`, current-ID literals in `runtime/tests/test_factory_registration.py`.

**Interfaces:** Preserve `load_profile(path)`, `ProfileRegistry.builtin(resource_root)` and every public signature. The worker produces an unpacked package containing the data needed by those existing interfaces.

- [x] **Step 1 — RED.** Add tests that copy only `runtime/src/proofkey` into a temporary isolated site-packages directory, start a child with that directory as its only project `PYTHONPATH`, and run from a different CWD containing conflicting fake profile/fixture files. The child must load all ten built-ins, inspect both host releases and initialize/close a fresh `CaseStore`. Before the fix, assert a nonzero child is reported as a test failure with captured stderr. Add literal expected inventory/hash checks plus isolated missing/tampered/symlink/hardlink host resource checks. Do not mutate source fixtures or bypass `_pinned`.

```python
child = subprocess.run([sys.executable, '-B', '-c', probe], cwd=unrelated,
    env={**safe_env, 'PYTHONPATH': str(isolated_site), 'PYTHONNOUSERSITE': '1',
         'PYTHONDONTWRITEBYTECODE': '1'}, capture_output=True, text=True, timeout=60)
self.assertEqual(child.returncode, 0, child.stderr)
```

Run with the source-test interpreter: `-B -m unittest discover -s runtime/tests -p test_installed_resources.py -v`. Retain complete RED output in the plan workspace. This is relocated-source regression evidence, explicitly not an installed-wheel receipt.

- [x] **Step 2 — minimal repair.** Copy resource content using apply_patch-generated additions, preserving exact bytes. Set the two built-in roots to `Path(__file__).resolve().parent / "resources"`. In `profiles.py` keep `/ "profiles" / name`; in `host.py` use `/ "profiles"` and `/ "fixtures" / fixture` without the development layer. Leave schema loading unchanged. Add explicit setuptools package-data paths for schema, profiles and two fixtures; constrain discovered packages to `proofkey*`. Add a deliberate MANIFEST listing owned packaging/docs, Python source and those data; exclude tests, caches, local state, environments and private outputs. Avoid a new resource module.

- [x] **Step 3 — current registration.** Compute the changed `profiles.py` SHA-256 and update only that entry in the current registration fixture. Give the current fixture a fresh descriptive ID `synthetic-factory-installed-resources-v1`, updating its exact expected literals in the qualifier and tests. Recompute the current registration `inventory_sha256` golden expectation in `test_factory_registration.py` from the documented canonical identity serialization. Do not alter `factory/proposal.py` historical constants, the legacy vectors or any previously retained output.

```python
digest = hashlib.sha256((root / 'runtime/src/proofkey/profiles.py').read_bytes()).hexdigest()
# The current fixture changes to digest; historical vectors remain byte-identical.
```

- [x] **Step 4 — GREEN.** Run new tests plus `test_profiles`, `test_engine_profile_contracts`, `test_host`, `test_host_admission`, `test_factory_registration`, `test_adaptation_factory`, `test_cli_parity`, `test_api_parity` and `test_release_manifest`. Inspect errors; do not weaken security or unavailability assertions. Root runs one final full suite, so worker must not duplicate that expensive run.
- [x] **Step 5 — reviewable commit.** Read own diff, hash-check every packaged resource against canonical originals, retain test commands/results, and commit only Task 1 files. Produce a report with changed files, RED/GREEN evidence, historical hash preservation and limitations. Root requests separate spec/quality review before Task 2 closes.

### Task 2: Verify real distributions and publish scoped evidence

**Files:**
- Create private evidence and verifier under `outputs/proofkey-installation-2026-10-09/` only.
- Update: `runtime/README.md`, `docs/verification/judge-remediation-2026-10-09/{README.md,support-matrix.md}`, child tasks and a new `docs/verification/2026-10-09-installed-resources.md`.

**Interfaces:** Consume Task 1 source tree and exact dependency artifact receipt. Produce factual build/install/test receipts; do not implement a new public release verifier.

- [x] **Step 1 — exact artifacts.** Validate all 19 runtime wheels against lock hashes and the separately pinned backend against official artifact metadata. Record actual target tags. Create task-owned build and installed venvs with system site disabled. Install build backend with `--no-index --no-deps`; the pinned setuptools backend is invoked directly, so no extra build frontend dependency is needed.

```python
for hook in ("build_wheel", "build_sdist"):
    code = f"from setuptools.build_meta import {hook}; import sys; {hook}(sys.argv[1])"
    subprocess.run([build_python, "-B", "-c", code, str(artifact_dir)], cwd=stage, check=True)
```

Each backend hook runs in a separate process: the installed backend mutates process arguments. The first diagnostic attempt that combined hooks is retained as a harness failure, not a product result.

- [x] **Step 2 — distributions.** Build from a new copied/staged runtime tree to keep source free of egg-info/build debris. Read wheel ZIP and sdist tar membership; check every expected source/data/license byte, no duplicate paths/traversal/symlinks or unexpected private files. Rebuild a wheel from the unpacked sdist using the same pinned backend; compare semantic member inventory and resource/source content rather than ZIP timestamps. Record all archive hashes.
- [x] **Step 3 — clean installation.** Install the locked closure using `--no-index --find-links <wheelhouse> --require-hashes -r <lock>` then the built wheel with `--no-index --no-deps`. Run `pip check`. Use an unrelated private CWD with `PYTHONPATH` absent and user site disabled. Record `sys.executable`, package metadata versions, `proofkey.__file__`, relevant module origins, `sys.path` and site-packages before/after hashes. All ProofKey imports must be inside the installed environment, not checkout or copied source.
- [x] **Step 4 — public execution/readback.** Implement a private evidence script with literal canonical window/goods requests from `test_cli.py`/`test_api_boundary.py`, not imported test helpers. Run the console script and `-m proofkey.cli` in separate fresh roots. Exercise `run_command`/`HostDispatcher` and `create_app`/`TestClient` with explicit trusted composition. For each require authorized result, expected verified effects (`reschedule`:1; goods refusal and return:1 each), original request, export file hashes and an observed successful owner close. Use `CaseStore(release.resource_root / "journal.sqlite")` and `SimulatedWorld(release.resource_root / "world.sqlite", release.fixture_path, profile=release.validate(), clock=clock)` for post-exit readback, following the existing public parity test. Capture exceptions/nonzero exits and all attempted positions, never infer business success from exit alone. Resource shadow and missing/tampered-copy probes are separate and must not mutate the installed package under positive execution.
- [x] **Step 5 — final regression.** Root freezes runtime source hashes, runs the full `unittest discover -s runtime/tests -v` once with raw stdout/stderr and actual time/exit, and compares source hashes afterward. Run `runtime/scripts/qualify_factory.py --help`, then the exact documented qualifier into a new output directory; verify manifest/artifact hashes and 37 planned tests. Keep any failure visible.
- [x] **Step 6 — docs and review.** Report exact target, installed route, artifact/effect results and residual gates. Update J13 only if all its exit evidence exists; J14 stays open. Request whole-change review, resolve verified findings, validate OpenSpec strictly, archive this completed child only if requirements pass, and preserve all evidence. No branch push/merge/publication.

## Completion receipt — 2026-10-09

Completed and archived. Full suite: 1,696/1,696 in 888.324s at frozen `8e655ec`, 260 files and HEAD unchanged. Final installed candidate `5bc38c8` changes only README and passed all 8/8 positions; the other 259 runtime files match the tested tree. Qualifier: 37/37, same executable/resource bytes. Independent final review: C0/I0/M0. See `docs/verification/2026-10-09-installed-resources.md` and `outputs/proofkey-installation-2026-10-09/implementation-review/`. J13 only is closed; J14, broader integration, native/human/platform/rights gates remain open. No merge, push or external publication was performed.
