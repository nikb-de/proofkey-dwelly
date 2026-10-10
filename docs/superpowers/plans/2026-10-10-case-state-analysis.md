# Case-state Analysis Implementation Plan

> **For agentic workers:** Use Superpowers TDD and independent review. The user explicitly requests parallel work; disjoint file ownership permits independent implementation without shared edits.

**Goal:** Integrate the supplied development data and a separate, honest local analysis workbench.
**Architecture:** Hash-checked sources → step evidence projection → offline baseline → immutable local run; author references remain a separate comparison input. Browser source timeline is reused, with hardened imports.
**Tech Stack:** Python standard library, plain JS/Web Components, existing Node/Python test runtimes. No new dependencies or cloud changes.
**Spec:** `openspec/changes/case-state-analysis-workbench/design.md` and delta specification.

## Global Constraints
- No paid model calls, cloud mutation, secret exposure or weakening of the existing Case API.
- Raw source JSON is unchanged; source commit is `8fbcd1fb633efa248e4045765a7854138118127d`.
- All imported annotations are `author_labels_unvalidated`, split `development`.
- Existing frozen `contracts/v1` is unchanged; no forced conversion of incompatible widget records.
- Preserve user-owned `docs/dataset-drafts/`.

## Review Focus
- Future labels/actor responsibilities must not change input hashes or inference.
- Unknown channel outcome must not produce resend or completion.
- Rejected/deep imports must not replace the last valid view.
- Foreign-origin writes and arbitrary paths must fail; no token reaches the UI.
- Late asynchronous responses must not overwrite a newly selected step.

### Task 1: Data projection and analysis core
**Owner:** data implementer. **Files:** `tools/dwelly_analysis/{__init__,catalog,widget,baseline,evaluation}.py`, `tools/dwelly_analysis/tests/test_core.py`, `datasets/case-state-widget-v1/manifest.json`.
**Interfaces:** `catalog.load_catalog()` returns public metadata list; `catalog.get_document(case_id)` returns validated detached document; `widget.project(document, step_index, case_id)` returns the closed input envelope in the design; `widget.reference(document, step_index, projection)` returns evaluator-only expectation; `baseline.analyze(input)` returns candidate; `evaluation.compare(candidate, reference)` returns mechanical comparison.
- [x] Write tests with literal expected states: 002 step3 waits for recipient; step4 proposes forwarding; N4 step5 requests readback, step6 waits, step7 infers completed; start/unknown abstain.
- [x] Run `python -m unittest tools.dwelly_analysis.tests.test_core -v` and record expected missing-module failure before implementation.
- [x] Implement strict source validation, projection, reference and manifest hashing; no baseline access to full document/reference.
- [x] Test sentinel exclusion, stable input after future/reference changes, malformed/deep values, source hash mismatch and every supplied step; rerun the suite.

### Task 2: Loopback service, artifacts and export CLI
**Owner:** coordinator. **Files:** `tools/dwelly_analysis/{server,__main__}.py`, `tools/dwelly_analysis/tests/test_server.py`, `contracts/analysis-v1/README.md`, `docs/analysis-workbench.md`.
**Consumes:** Task1 functions above. Run envelope fields: schema_version `proofkey-analysis-run-v1`, run_id, case_id, step_index, mode `offline`, input_hash, input, candidate, reference, evaluation, source (document hash/commit/family), live_calls0, operational_effects0.
- [x] Write HTTP tests using real loopback requests and temporary run directories: valid run/readback/restart, wrong hash409, live mode400, invalid Host/Origin403, missing custom header403, traversal404, run cap429.
- [x] Run tests to observe missing service, then implement fixed routes/static allowlist, private exclusive artifact writes and sanitized errors.
- [x] CLI `serve --port 8093 [--runs-dir PATH]`; CLI `export --output PATH` exclusively writes separate inputs/references and a development manifest, no overwrite.
- [x] Verify export rereads and all API tests; leave cloud case service untouched.

### Task 3: Hardened widget and analysis UI
**Owner:** UI implementer. **Files:** `case-state-widget/viewer.js`, `analysis.html`, `analysis.js`, `analysis.css`, `tests/integration.test.mjs` and a browser QA script. `app.js` was additionally updated to enforce the raw-input size bound before parsing; raw source JSON is not edited.
**Consumes:** API design paths; catalog `{cases:[{id,title,steps,family_id,qualification}]}`; GET case `{case_id,document}`; GET step `{input,reference,source}`; POST run returns full run envelope.
- [x] Write failing import tests for string source_event_ids, excessive depth and completed-with-pending criteria; existing valid sources must pass.
- [x] Harden validation and preserve the old view on any rejected load. Avoid prototype pollution and unsafe HTML.
- [x] Build English analysis shell with case selector, source timeline, evidence input, offline run, separate reference and downloads. POST exact ID/index/hash/offline plus `X-ProofKey-Request: analysis-v1`.
- [x] Use request generation counters so old fetch/run results never replace current selection; render errors accessibly.
- [x] Run Node tests and actual desktop/mobile browser flow; save QA evidence without model calls.

### Task 4: Integration review and handoff
- [x] Independently review all new code for input/reference isolation and browser/security boundary; fix confirmed findings with regression tests.
- [x] Run related Python suites, supplied/new Node tests, browser smoke, OpenSpec strict validation and diff checks.
- [x] Link documentation from root README, record exact data/test counts and limitations; archive the completed OpenSpec change and commit task-owned files only.
