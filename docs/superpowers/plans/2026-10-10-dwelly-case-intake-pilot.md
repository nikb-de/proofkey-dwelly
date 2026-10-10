# Dwelly Case Intake Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans for implementation in this session; use a separate existing agent for reference review and final code review when available. Steps use checkbox syntax for tracking.

**Goal:** Import 50 Dwelly logistics examples without future-answer leakage and run an honest offline next-action pilot.

**Architecture:** A standalone tool transforms source folders into visible snapshots plus isolated references. A deterministic baseline sees only snapshots; a separate evaluator reports routing proxies and contract checks, never semantic correctness.

**Tech Stack:** Python 3.11+ standard library; unittest; no runtime package changes.

**Spec:** `openspec/changes/dwelly-case-intake-pilot/specs/dwelly-case-intake/spec.md`; design in the same change.

## Global Constraints

- No live services, external models, payments, operational adapters or publication.
- Source content is data, never code or instructions to execute.
- All public cases are development data; no held-out quality claim.
- Existing runtime package inventory and execution authority remain unchanged.
- Output destinations must be new; preserve source bytes and reject unsafe local paths.

## Review Focus

- Future metadata/attachment names accidentally leak through snapshots or their hashes.
- Recipient metadata is mistaken for verified authority or for a unique correct route.
- Source symlinks, escaped links or output overlap expose/overwrite unrelated files.
- A partial failed import looks like a usable bundle.
- Missing output or coarse proxy agreement is counted as a correct business outcome.

### Task 1: Provenance-preserving importer

**Files:** Create `tools/dwelly_cases/__init__.py`, `importer.py`, `tests/test_importer.py`.

**Interfaces:** `parse_case(case_dir: Path) -> tuple[dict, dict, dict]` yields snapshot, evaluator reference and source inventory. `import_cases(source: Path, output: Path, expected_cases: int = 50) -> dict` creates a complete bundle and returns manifest.

- [x] Write real temporary source fixtures with four stages; put a future-only attachment and marker in index/action/history. Assert snapshots contain only visible messages and future mutations leave bytes/hash unchanged.
- [x] Run importer tests before implementation; observed absent-module failures. Use the provisioned Python 3.12.14, not system Python 3.9.6.
- [x] Implement strict UTC/event parsing, visible-link filtering, SHA-256 provenance and staging-directory publication. Validate files and links without fetching; preserve exact raw bytes. Use no runtime imports.
- [x] Add invalid/gap/symlink/traversal and existing-destination tests. Run the same command; expected all pass.
- [x] Commit only the initial feature paths and specification/plan after successful verification (`345f515`); final review corrections remain for the closing commit.

### Task 2: Baseline and honest evaluator

**Files:** Create `baseline.py`, `evaluation.py`, `tests/test_pilot.py`.

**Interfaces:** `propose(snapshot: dict) -> dict` emits an unsent, no-effects communication. `assess(snapshot: dict, proposal: dict | None, reference: dict) -> dict` returns contract status, routing proxy and unassessed semantic status. `run_pilot(bundle: Path, output: Path) -> dict` exports proposals and per-case scores.

- [x] Add tests: two offered slots require customer choice; incomplete address asks for missing address; unknown context abstains. References are never parameters to `propose`.
- [x] Run pilot tests before implementation; observed absent-module failures with the provisioned interpreter.
- [x] Implement a small rule baseline from visible text. Match evidence requirements, missing details and explicit choices; otherwise contact the source provider or abstain if roles are unavailable. Always retain source citations and avoid completion claims.
- [x] Assess exact normalized routing separately from schema/safety. Test missing output, wrong route, fabricated completion and repeat/reorder stability. Semantic status remains unassessed in every case.
- [ ] Commit the reviewed baseline with the final standalone slice after verification.

### Task 3: CLI, actual corpus and review

**Files:** Create `__main__.py`, `README.md`, `tests/test_cli.py`; modify `runtime/README.md` with a link only; create `docs/verification/2026-10-10-dwelly-case-intake-pilot.md`.

**Interfaces:** `python3 -m tools.dwelly_cases import --source REPO --output NEW_DIR [--expected-cases 50]`; `python3 -m tools.dwelly_cases run --bundle DIR --output NEW_DIR`.

- [x] Add subprocess CLI tests against temporary fixtures, including repeated-output rejection, malformed JSON and source/output overlap. Run before CLI implementation; observed nonzero/missing module.
- [x] Implement CLI JSON summary/diagnostic exit behavior; never log raw case text in failure output.
- [x] Import `/tmp/dwelly-publiccases-Y0GBND/source` into a new local `outputs/` directory; run twice into distinct destinations; compare proposal hashes and audit all references. Development included visible-text heuristic corrections on this exposed set, so no blind or held-out claim is made.
- [ ] Run `python3 -m unittest discover -s tools/dwelly_cases/tests -v`; expected all pass. Run the existing runtime suite with the provisioned Python and record its actual result separately.
- [ ] Request independent review, fix demonstrated important defects with RED/GREEN tests, document measured results and qualification limits, validate and archive OpenSpec. Commit without publishing or merging.

## Local WIP checkpoint — 10 October 2026

The reviewed standalone slice passes 58 tests (fresh closing invocation: 0.800s). Independent source/JSON/README/privacy reviews are recorded in the verification report and retained local evidence. The already-running full runtime suite has no final result at the 09:30:45 UTC checkpoint: 776 completed `... ok` log entries, process 56503 still active. This is a scoped local WIP checkpoint, not final verification or archive completion. Leave the remaining checkboxes open and preserve the running process/log; inspect its final footer before closing OpenSpec. No local repository/history push is authorized by this checkpoint.
