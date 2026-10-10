# Team contracts and local workbench — verification

Date: 2026-10-10. Contract implementation `8a96e88`, corrections `90e2b13`; workbench `75511d8`, corrections `5b0d18e`. Local-only work. No provider calls, carrier actions, external deployment, push or publication.

## Delivered

- Versioned [contract pack](../../contracts/v1/README.md): eight JSON Schemas, connected two-revision example, negative examples, existing-case OpenAPI and separate target interfaces.
- [State/storage architecture](../architecture/team-contract-v1.md): immutable input, media validation/extraction, revision-bound analysis and operation outcome projections kept separate.
- [Local workbench](../../design/right-ontime/prototype/intake.html): create/list cases, choose participants and actual source recipients/time, append text/photo/audio, validate and persist real bytes, preview committed evidence, export API-shaped metadata.
- Supplied six-case simulator retained. Source ZIP and all 53 original manifest hashes verified before changes. Original manifest and evidence remain historical, not reused as the new extension's test receipt.

## Fresh controller checks

| Scope | Result |
|---|---|
| `contracts/v1/test_contracts.py` | 20 passed, 0.125s |
| All service tests | 63 passed, 31.532s |
| All model tests | 74 passed, 0.565s |
| All source-importer tests | 58 passed, 0.703s |
| Intake model unit tests after final code fix | 4 passed, no skips |
| `check-intake.mjs` after final code fix | Passed creation, real PNG persistence/reload, invalid input, safe text, keyboard, 360px and missing-case checks |
| `check-intake-storage.mjs` after final code fix | Passed actual WAV bytes/reload, stale/duplicate/orphan/missing-asset rejection, transaction rollback, quota, retained drafts, removal and export |
| `check-intake-recovery.mjs` after final code fix | 3 named checks passed: create/read failure, append/read failure, exact recipient subset/empty export |
| Three original prototype suites | 41 + 68 + 23 passed, each `errors: []` |

Original suites ran against a fresh copy of the updated prototype at `/private/tmp/proofkey-design-regression.fNwQ8C/prototype`, preserving supplied receipts. The final workbench correction changes only intake-specific files; it does not change original demo sources or tests. These numbers are software checks, not logistics outcome accuracy.

### Reproduce

```sh
python3 -B -W error::ResourceWarning -m unittest discover -s contracts/v1 -p 'test_*.py' -v
python3 -B -W error::ResourceWarning -m unittest discover -s tools/dwelly_service/tests -p 'test_*.py' -q
```

Contract tests require the two pinned test-only packages in `contracts/v1/requirements-test.txt`. No new production dependency was added. Node tests run from `design/right-ontime/prototype`:

```sh
node --test tools/intake-model.test.mjs
node tools/check-intake.mjs
node tools/check-intake-storage.mjs
node tools/check-intake-recovery.mjs
```

Set `PLAYWRIGHT_PACKAGE_JSON` to an installed Playwright package file and `CHROMIUM_EXECUTABLE_PATH` if needed. The controller used the bundled Playwright and `chromium_headless_shell-1243` executable; tests block HTTP(S) and use isolated browser contexts. The original three scripts write into `evidence/`, so run those only from a copied prototype directory.

## Independent review

Two independent Codex review scopes, **not a multi-provider judge panel**:

1. Contract review found three P2 defects: accepted source timestamps rejected by schema; failure states requiring invented successful-file metadata; completed analysis permitting missing result references. All were reproduced, corrected and approved on scoped re-review. A connected two-revision example also replaced the disconnected example-only gap.
2. Workbench/final integration review found two P2 defects: committed writes misreported as failed when the following read failed, and recipients silently inferred from all other participants. Both were reproduced, corrected and approved on scoped re-review. The controller completed all three recovery checks with exit 0 after that fix. Task 2 and final additive integration gates are approved within the stated local-only boundary.

## Visual checks

Controller inspected actual desktop and 360px renders, including the local image preview and final recipient controls. No clipped content or horizontal overflow was observed in those views. This is not a complete assistive-technology accessibility audit.

- [Desktop](../../outputs/right-ontime-intake-2026-10-10/desktop.png)
- [360px mobile](../../outputs/right-ontime-intake-2026-10-10/mobile-360.png)

The screenshots show generated test PNG bytes, not a real delivery. `tools/capture-intake.mjs` reproduces them. Output files are local verification artifacts and may be ignored by Git.

## Explicit remaining boundaries

- Files and cases remain in this browser's IndexedDB, not a server or shared CRM. Browser clearing can destroy local data. Uncommitted drafts survive a failed save in the current page, not a refresh.
- Current backend accepts declared media metadata only. Browser-to-server authentication, a BFF and private blob storage remain target interfaces, not installed services. No Origin/authentication checks were weakened.
- New revisions do not yet trigger model analysis. OCR/ASR/vision, model-to-runtime operational wiring and real logistics adapters remain disconnected. No model quality or production readiness follows from these tests.
- Positive media fixtures cover PNG and WAV. JPEG/MPEG/MP4/WebM paths are implemented, but positive codec coverage is not claimed; browser decoding must succeed or the file remains rejected.
- Case rules inferred from training data remain unapproved proposals. No labels, raw messages or uploads can authorise an action.
- The earlier full runtime suite had two closure failures, separately fixed and rerun successfully; [its exact limited rerun scope](model-runtime-shadow-bridge-2026-10-10.md) remains distinct from this UI/contract work. No new full-runtime-suite pass is claimed.
