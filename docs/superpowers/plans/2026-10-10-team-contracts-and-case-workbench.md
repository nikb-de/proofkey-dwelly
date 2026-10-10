# Team contracts and case workbench implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give UI, E2E and evaluation contributors a shared versioned contract and add genuine browser-local case and file intake to the supplied Right onTime design.

**Architecture:** Keep the original six-case simulator separate. A local workbench stores declarations, append-only events and real attachment Blobs in IndexedDB; a contract pack distinguishes existing service APIs from target analysis/asset/operation APIs. No runtime authorisation, provider call or real booking is introduced.

**Tech Stack:** Static HTML/CSS/JavaScript, IndexedDB, browser Web Crypto, Node test runner/Playwright, Python unittest, JSON Schema 2020-12, OpenAPI 3.1.

**Spec:** `openspec/changes/archive/2026-10-10-team-contracts-and-case-workbench/design.md` and living specifications `openspec/specs/team-backend-contract/spec.md` / `openspec/specs/local-case-workbench/spec.md`.

## Global constraints

- Existing IDs match `[A-Za-z0-9][A-Za-z0-9_-]{0,63}`; source revisions start at zero.
- Keep `runtime/src`, pinned runtime fixtures and service authentication/Origin checks unchanged.
- Preserve source design and all historical receipts; new tests write to new output paths or isolated copies.
- PNG/JPEG limit is 10 MiB; MPEG/WAV/MP4/WebM audio limit is 25 MiB. Invalid bytes never become ready evidence.
- Persist actual committed Blobs atomically with metadata; do not store base64 in the simulator's localStorage.
- UI copy is English. Keep the supplied Forest identity and original SVG/font assets.
- Saving a file is not uploading to a server, analysing it, authorising an action or verifying an outcome.
- No live providers, external publishing, secrets in browser code, or changes to `docs/dataset-drafts/`.

## Review focus

- Malicious title/message/filename: rendered as text, not executable HTML.
- Reload and quota/transaction failure: either durable bytes plus metadata or a visible unsaved draft, never a false success.
- Late evidence: new revision supersedes pending decisions, never silently retries an uncertain effect.
- Empty/corrupt/mislabelled/oversized files: rejected before commit; image decode failure cannot be treated as evidence.
- Dataset labels/future transitions: evaluator-only records cannot enter model-visible input or grant authority.

## Execution authority

The user explicitly requested autonomous implementation and parallel independent work. Continue without intermediate sign-off; this overrides the default approval pauses and serial-dispatch preference, not security/publishing boundaries. Tasks 1 and 2 have disjoint owned paths; task 3 is controller-owned documentation, and task 4 reviews integration.

### Task 1: Executable contract pack

**Files:** Create `contracts/v1/schemas/`, `contracts/v1/examples/`, `contracts/v1/test_contracts.py`; controller owns `contracts/v1/README.md`, `openapi.json` and `state-machines.json`.

**Interfaces:** Consume actual `CaseStore` declarations/events/snapshots. Publish schemas for these and separate versioned decision input/label/episode/transition/run, asset and analysis records. Examples must include a valid zero-based case and an evaluator-only label. Do not change service code.

- [x] Write tests before schemas: a valid fixture must load, revision -1 and undeclared fields must fail, correct CaseStore snapshot hash must validate, and labels must fail when inserted into input.

```python
def test_revision_is_zero_based(self):
    valid = self.example('decision-input')
    valid['source']['revision'] = -1
    self.assert_invalid('decision-input', valid)
```

- [x] Run `python -m unittest discover -s contracts/v1 -p 'test_*.py' -v`; retain the expected missing-schema/red result.
- [x] Implement closed versioned JSON Schemas, positive/negative examples and tests against actual CaseStore. Use an available standards-compliant validator; do not create a partial validator advertised as JSON Schema.
- [x] Pin provenance, revision/hash linkage, review status and typed transition conditions. Do not encode guessed business policy as permission.
- [x] Run the full contract suite and service tests; report commands, counts and any excluded checks.
- [x] Commit only owned contract schema/example/test files; provide a written report and review diff.

### Task 2: Local case and evidence workbench

**Files:** Create `design/right-ontime/prototype/intake.html`, `assets/intake-model.js`, `assets/intake-store.js`, `assets/intake-ui.js`, `assets/intake.css`, `tools/check-intake.mjs` and unit tests. Modify only minimal navigation in `index.html`/`assets/app.js`, plus new README for intake. Do not overwrite original evidence or manifest.

**Interfaces:** Declarations/events use the existing closed backend fields. Local records may wrap UI metadata separately. `window.ProofKeyIntake` (or explicitly documented module exports) exposes validation/store functions for browser tests. Use a new IndexedDB name/version; never reset simulator storage. Export declaration and ordered append payloads separately from local attachment manifest.

- [x] Write pure tests first for declaration/event validation, metadata mapping and file limits; run to the expected missing-feature failure.

```javascript
assert.throws(() => validateDeclaration({...validDeclaration, case_id: '<script>'}));
assert.throws(() => validateFileMetadata({type:'image/png', size:0}));
```

- [x] Implement the pure model and test it. Add browser failing checks for creation, real photo persistence/reload and corrupt photo rejection before implementing store/UI.
- [x] Implement atomic IndexedDB case/event/asset storage, SHA-256 and image decode; native audio preview must not imply transcription. Limit browser storage to a documented bounded total and fail transactionally.
- [x] Implement accessible create-case and add-evidence forms, explicit per-file validation/status, staged removal, preview cleanup, case list/detail/missing-case screen, immutable committed history, and JSON export. Prevent duplicate submit and preserve failed drafts.
- [x] Keep original demos unchanged; add a clearly separate Local intake navigation link. No fetch/Bearer key or fabricated analysis/execution result.
- [x] Run new unit/browser tests: valid image/audio, unsupported/empty/large/corrupt content, duplicate files/IDs, reload, quota/storage failure, HTML injection, missing case, keyboard and 360px layout. Run all three original suites from an isolated copied prototype.
- [x] Commit only owned design files; report exact tests and limitations.

### Task 3: Architecture, API availability and team handoff

**Files:** Create `contracts/v1/README.md`, `openapi.json`, `state-machines.json`, `docs/architecture/team-contract-v1.md`, `design/right-ontime/IMPORT-PROVENANCE.md`; update root README with entry links.

**Interfaces:** Task 1 schema filenames are stable: `local-case.schema.json`, `decision-input.schema.json`, `decision-label.schema.json`, `episode.schema.json`, `transition.schema.json`, `decision-run.schema.json`, `asset.schema.json`, `analysis.schema.json`. Target path definitions are under `x-target-interfaces`, never ordinary OpenAPI `paths`.

- [x] Verify all 53 supplied file hashes before changes; preserve ZIP hash and source commit in import provenance.
- [x] Write four small diagrams and transition tables separating source revisions, media, analysis and operations. Explain restart, idempotency, late results, ownership, storage and cancellation.
- [x] Describe current endpoints exactly; missing list/upload/analysis/approval/execution interfaces must be visibly target-only, with proposed request/response contracts and extension points.
- [x] Provide parallel work assignments and acceptance checks for UI, backend and E2E/evals, including source revision/hash and no-future-evidence boundaries.
- [x] Parse JSON and check schema references; audit prose claims against implementation. Add root entry links without changing existing deliverable claims.

### Task 4: Independent review and completion

**Files:** `docs/verification/team-contract-workbench-2026-10-10.md`, OpenSpec task checkboxes and archive; fixes in the responsible owned paths.

- [x] Review task 1 and task 2 diffs independently for spec compliance and quality. Handle important findings with test-first fixes and scoped re-review.
- [x] Run fresh contract, intake, original design and affected service tests. Inspect actual desktop/mobile renders; note exact unavailable checks rather than infer success.
- [x] Validate OpenSpec strictly, archive this completed additive scope and verify archived/living specs. Target backend work stays explicitly unimplemented.
- [x] Commit the verified local changes and give the user clickable entry points, test results and remaining backend gaps. Do not push or publish.
