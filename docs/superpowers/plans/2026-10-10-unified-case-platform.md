# Unified Case Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox syntax for tracking.

**Goal:** Join durable case creation, evidence, versioned decisions, human review and sandbox execution in one product UI.
**Architecture:** Add a same-origin Python platform BFF with a PostgresCaseStore extension; retain canonical snapshots and existing model worker. Use a no-build UI sharing the existing visual language.
**Tech Stack:** Python standard-library HTTP, psycopg, PostgreSQL, browser ES modules, pytest and Playwright.
**Spec:** `openspec/changes/archive/2026-10-10-unified-case-platform/design.md` and `openspec/specs/unified-case-platform/spec.md`.

**Status (2026-10-10):** Tasks 1–5 implemented and reviewed. Local PostgreSQL and browser acceptance passed; live provider quality, production deployment and native external integrations remain out of scope. See `docs/verification/platform-ui-2026-10-10/README.md` for the exact verification scope and final OpenSpec archive location.

## Global Constraints
- Frozen v1 case snapshots never become execution authority. External business effects remain zero.
- All decisions/reviews bind case ID, revision and snapshot hash; new evidence invalidates admission.
- Only local sandbox rescheduling executes, after explicit human consent attestation and deterministic checks.
- No paid requests, credentials mutation, cloud deployment, public push or changes to `docs/dataset-drafts/`.
- UI and API use English; progress updates to the user use Russian.

## Review Focus
- Same revision but wrong hash must fail just like stale revisions (Task 1).
- Concurrent duplicate execution must create one sandbox effect (Task 1).
- Cross-case media/job retrieval must fail (Tasks 1, 2, 4).
- Stale async responses must not overwrite a newly selected case (Task 3).
- Missing reference labels must never be displayed as correctness evidence (Task 2).

### Task 1: Durable platform domain
**Files:** Create `tools/dwelly_platform/{__init__,store,domain}.py`, `tools/dwelly_platform/migrations/001_platform.sql`, `tools/dwelly_platform/tests/test_store.py`.
**Interfaces:** `migrate(database_url,schema)`. `PlatformStore` inherits canonical methods and provides `list_cases()`, `detail(case_id)`, `analyze(case_id,key,body)`, `propose(case_id,key,body)`, `review(case_id,key,body)`, `execute(case_id,key,body)`, `put_asset(case_id,key,mime,filename,data)`, `get_asset(case_id,asset_id)`, `link_model(case_id,revision,snapshot_hash,job_id)`. Return detail dictionaries for mutation methods except assets; asset insertion returns `{asset_id,sha256,mime_type,size_bytes}`.
- [x] Write tests before implementation using real PostgreSQL unique schemas. Expected: create/append preserves v1, empty analysis requests info; wrong revision/hash fails; unknown evidence fails; same-address future 2-hour slot with approval/consent executes once; stale approval cannot execute; unsupported refund is blocked; media signature/cross-case/cap checked.
```python
detail = store.propose('case1', 'proposal1', {'expected_revision': 1, 'snapshot_hash': snapshot['snapshot_hash'], 'action': {'type':'reschedule_delivery','slot_start':start,'slot_end':end,'address_change':False}, 'evidence_event_ids':['event1']})
decision_id = detail['decisions'][-1]['decision_id']
store.review('case1','review1',{'decision_id':decision_id,'verdict':'approve','note':'Consent checked locally','customer_consent_confirmed':True})
first = store.execute('case1','execute1',{'decision_id':decision_id})
second = store.execute('case1','execute2',{'decision_id':decision_id})
assert first['actions'] == second['actions']
assert first['external_effects'] == 0
```
- [x] Run tests, record RED; implement transactional store/domain; run tests GREEN. Report changed files and exact results; do not commit shared worktree.

### Task 2: Evidence-only model bridge
**Files:** Create `tools/dwelly_platform/models.py`, `tools/dwelly_platform/tests/test_models.py`; modify only optional-reference handling in `tools/dwelly_analysis/worker.py`.
**Interfaces:** `project_snapshot(snapshot)->step-input`, `ModelBridge(store,runtime)`, `.submit(case_id,key,body)->job`, `.get(job_id)->job`, `.profiles()->capability`. Calls store.link_model after durable submission, idempotent replay repairs missing link. Runtime is optional; absent means explicit model_execution_disabled.
- [x] Add RED tests: projection retains case event IDs and participants, excludes authority and decisions; media body says content unprocessed; reference null returns evaluation null; binding mismatch rejects; job links can only reference correct revision/hash.
```python
selected = {'input': project_snapshot(snapshot), 'reference': None,
            'source': {'kind':'platform_case','snapshot_hash':snapshot['snapshot_hash']}}
assert selected['input']['case_id'] == snapshot['case_id']
assert selected['reference'] is None
```
- [x] Implement bridge without live requests; run its tests and existing model worker regression tests; report evidence and concerns.

### Task 3: Primary platform UI
**Files:** Create `platform-ui/{index.html,app.js,session.js,style.css}`, `platform-ui/tests/session.test.mjs`.
**Interfaces:** Exact routes and envelope fields in design; fetch API and keep user drafts on failure; refresh detail after writes. Static brand resources use `/brand/` and `/fonts/`; eval link `/evals/`.
- [x] Write RED Node tests for session selection race, revision conflict draft retention, error handling and reload. Browser QA in Task 4 tests rendered actions.
```javascript
const session = new PlatformSession(api);
await session.select('case1');
assert.equal(session.detail.case_id, 'case1');
```
- [x] Build English responsive UI: sidebar Cases/Review queue/Integrations/Evaluations; create form; evidence list and text/file upload; five state axes; deterministic analysis; optional model selection/run; operator reschedule/refund/return proposals; approve/reject with consent; explicit sandbox execute; immutable history. No HTML injection; no secrets or fake status.
- [x] Run Node tests and report changed files plus any unresolved API assumptions.

### Task 4: Same-origin integration and verification
**Files:** Create `tools/dwelly_platform/{server,__main__}.py`, `tools/dwelly_platform/tests/test_server.py`, `platform-ui/tests/e2e.mjs`; create `docs/platform-operations.md`, `contracts/platform-v1/README.md`.
**Interfaces:** Implement spec routes, strict Host/Origin/length/duplicate-key checks, mutation marker and idempotency, safe error mapping. CLI `python -m tools.dwelly_platform serve --port 8095 --database-url-env PROOFKEY_PLATFORM_DATABASE_URL --schema proofkey_platform --migrate`; optional existing model runtime requires explicit --allow-live.
- [x] Write RED API tests: cross-site writes rejected, create+append+analysis+proposal+review+execute flow, invalid JSON/MIME, duplicate execution, cross-case assets and no-store headers.
- [x] Implement server/CLI, preserving existing 8093 eval service. Serve UI root and optional `/evals/` redirect to local analysis service. No silent provider opt-in.
- [x] Run `PYTHONPATH=tools:runtime/src /tmp/proofkey-postgres-tests-20261010/bin/python -m pytest tools/dwelly_platform/tests -q` with real PG test env; run Node tests and existing backend/model regressions.
- [x] Run Playwright against actual local service: create case, append HTML-like text, upload PNG, inspect states, run deterministic checks, propose safe slot, approve consent, execute once, reload, append new evidence, confirm old action cannot authorize a new one. Rendered desktop/mobile screenshots were inspected; stale-action rejection is covered by PostgreSQL tests rather than this browser script.
- [x] Independent review; fix substantive findings with regressions; update verification record and archive OpenSpec. Keep local working service visible to user; disclose no live-model/OCR/production certification.

### Task 5: Explicit media processing controls (user extension)
**Files:** Create `tools/dwelly_platform/media.py`, `tools/dwelly_platform/tests/test_media.py`; Task 4 connects optional MediaService. Task 3 owns controls.
**Interfaces:** `migrate_media(store)`, `MediaService(store,provider=None,budget_scope='platform-media',reservation_usd='25',cap_usd='25')`; `.capabilities()`, `.list(case_id)`, `.process(case_id,asset_id,key,{'mode':'image_analysis'|'asr'})`. `OpenAIMediaProvider` is explicitly configured and off by default. Results contain run ID, mode, status, source hash, validation, output text, human-review requirement and provider receipt, never execution authority.
- [x] Write RED tests for source/hash binding, empty output, corrupt images/audio, replay without redispatch, cross-case access and disabled provider. Use injected provider only for tests; real image decode/audio inspection remain actual.
```python
first = media.process('case1', asset_id, 'media1', {'mode':'image_analysis'})
second = media.process('case1', asset_id, 'media1', {'mode':'image_analysis'})
assert first == second
assert first['human_review'] == 'required'
assert first['source_sha256'] == asset['sha256']
```
- [x] Implement immutable processing and validate at most 16 MP images / 600 seconds of audio; time out audio inspection after 10 seconds. Reserve full USD25 cap per model/scope before dispatch; no automatic resend of running/unknown records. Persist results independently, no implicit source-event append.
- [x] Run focused media tests and HTTP/browser processing controls checks. Document provider configuration, conservative one-request cap and remaining live-verification limits.
