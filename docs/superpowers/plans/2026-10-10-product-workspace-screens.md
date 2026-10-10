# Product workspace screens implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox syntax for tracking.

**Goal:** Bring the approved Right onTime product design onto the existing integrated backend.
**Architecture:** Three independent frontend surfaces reuse the existing platform API and safety gates. Static routes are integrated separately; no database or execution-policy changes.
**Tech Stack:** Vanilla ES modules, HTML/CSS, Python HTTP server, PostgreSQL, Node tests and Playwright.
**Spec:** `openspec/changes/product-workspace-screens/specs/product-workspace/spec.md`

## Global Constraints
- English UI; original Forest/paper/brass design and existing brand/fonts.
- Preserve canonical contracts, revision binding, approval requirements, source provenance and idempotency.
- No new paid model calls, automatic execution, external messaging, invented slots/prices, or authenticated-customer claims.
- No changes to unrelated existing dirty files; do not commit until coordinator integration review.
- Every mutation error retains the user draft. All source text is untrusted.

## Review Focus
- Stale case snapshot must not become an approved action (Customer tests).
- Long IDs and empty cases must fit the screen (Team browser checks).
- An action receipt is not physical delivery or external booking (Team/Customer tests).
- localStorage failure must not report a saved draft (Preparation tests).
- Capability availability must not imply runtime activation (Preparation tests).

### Task 1: Team workspace
**Files:** `platform-ui/index.html`, `platform-ui/app.js`, `platform-ui/style.css`, new `platform-ui/product.js`, `platform-ui/tests/product.test.mjs`.
**Consumes:** Existing `session.js` API and unchanged case detail structure.
**Produces:** `/` product UI; links `/customer.html?case=<id>` and `/preparation.html`; Summary/Requests/Sources tabs with all existing controls retained in appropriate sections.
- [x] Write failing Node tests for case filtering/counters and safe summary/request derivation. Run `node --test platform-ui/tests/product.test.mjs`.
- [x] Implement helpers and restyle/restructure Team to original `design/right-ontime/prototype/team.html`. Read current app before changing it. Use data from backend, not fixture text. Keep current selector IDs wherever possible for regression tests.
- [x] Add readable next-step summary, real owner ID, event/activity and request status cards. Mark internal requests as internal and external communication as unsent unless a persisted receipt proves otherwise.
- [x] Run `node --test platform-ui/tests/*.test.mjs`; report all failures.

### Task 2: Customer journey
**Files:** new `platform-ui/customer.html`, `customer.js`, `customer.css`, `customer-model.js`, `platform-ui/tests/customer.test.mjs`.
**Consumes:** `createAPI` from `session.js`; `/cases/:id`, `/cases/:id/decisions`; query `?case=`.
**Produces:** Case-bound operator-assisted customer preview, window entry/selection from actual existing proposals, review step, explicit submit and persisted status.
- [x] Write failing Node tests for window validation, stale snapshot rejection and honest receipt/status rendering; run the test file.
- [x] Implement a three-step Choose window / Review / Status journey in the reference style. Price and carrier availability remain unknown unless backed by records. With no case, provide a case picker, not a fabricated demo.
- [x] Submit `{expected_revision,snapshot_hash,action:{type:'reschedule_delivery',slot_start,slot_end,address_change:false},evidence_event_ids}` through existing API, never `/reviews` or `/execute`. Require supporting source evidence. Keep draft on failure; prohibit double submit; preserve idempotency key on uncertain retry. User identity is not authenticated.
- [x] Refresh status explicitly; display only matching current records and retain link `/#case=<id>`. Run Node tests.

### Task 3: Preparation
**Files:** new `platform-ui/preparation.html`, `preparation.js`, `preparation.css`, `preparation-model.js`, `platform-ui/tests/preparation.test.mjs`.
**Consumes:** read-only `/capabilities`, `/cases`; original reference preparation screen.
**Produces:** Four clear steps: environment, local profile draft, preflight checks, handoff/export. Links back to Team.
- [x] Write failing tests for six adapter surfaces, invalid profile input, storage failure, and no runtime activation claims; run the test file.
- [x] Implement service/capability cards, editable local profile (name, process type reschedule/refusal, acknowledgement semantics, readback requirement, mappings for six surfaces), browser-local save/load and JSON download. No secrets fields, no arbitrary URL fetch or activation API.
- [x] Preflight uses current capabilities, version marker, required mapping completeness and source-readback availability; distinguish fail/unknown/not configured from passed. Never label this full regression or live integration testing.
- [x] Run Node tests; report files and limitations.

### Task 4: Integration and verification
**Files:** `tools/dwelly_platform/server.py`, `tools/dwelly_platform/tests/test_product_routes.py`, documentation.
**Consumes:** Tasks 1–3 assets.
**Produces:** Working local routes and verification receipt.
- [x] Add failing HTTP route tests to the existing PostgreSQL fixture and assert HTML/script types plus no path traversal. Run them before route implementation.
- [x] Explicitly allowlist new static assets, restart only port 8105 with its existing schema and budget scope.
- [x] Run all frontend tests and platform backend tests. Browser-test Team, Customer proposal/status and Preparation save/export; check 1440/390px overflow and console errors. No paid model calls.
- [x] Independent code/spec review, fix findings, update living specs and archive.
