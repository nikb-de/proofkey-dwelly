# Task 2 — Team coordination review UI

Implemented in the assigned worktree, without commits or edits to session.js, customer assets, server.py, or existing tests.

## Delivered

- `platform-ui/coordination.js`: pure phase/terms/evidence projection, strict explicit command builder, snapshot/workflow/offer/request/field-bound review attestation, current succeeded model context gate, and guarded mutation controller.
- `platform-ui/coordination-panel.js`: dedicated Team card, eight existing commands by phase, exact terms and source review, optional paired model run/note, pending local requests, local receipts, stale state, and frozen-request retry.
- `platform-ui/coordination.css`: forest/neutral card styling, wrapping identifiers, readable mobile layout.
- `platform-ui/app.js`, `index.html`, `product.js`: card integration, coordination-aware case summary, optional distinct Dispatch ID at case creation. Initialization is collapsed for legacy cases and never invents participants.
- New tests: `platform-ui/tests/coordination.test.mjs`, `platform-ui/tests/coordination-panel-e2e.mjs`.

The Team form does not expose `record_local_acceptance`. `record_consent` requires qualifying sourced customer evidence. All initial loads, renders, model inspection and command previews remain read-only. Model output never selects or submits a command automatically.

## Review and retry guarantees

The review attestation covers case ID, current revision/hash, workflow version, current offer ID/hash, pending request ID, selected command, terms, source IDs, initialization fields, escalation reason, and optional model reference/note. Field edits clear the checkbox; new snapshots invalidate it while retaining the draft. Source evidence is checked for declared actor, routing, receipt order, used IDs, and exact readback correlation. The server remains authoritative for policy, complete candidate schema validation, clock checks and transactions.

Only a current succeeded model result can be attached; evidence is checked against canonical candidate `evidence_event_ids`, and the human note is capped at 1000 characters.

The controller prevents concurrent submissions. Uncertain failures preserve both immutable body and original session idempotency key, including the important case where POST succeeds but its follow-up GET fails. HTTP 4xx failures release the attempted request and retain operator fields for renewed review. No silent rebasing is performed during uncertain replay.

## Verification

- TDD: observed missing-helper/panel failures, then green implementation. Additional failing regressions demonstrated silent review rebinding and POST-success/GET-failure key loss before their fixes.
- `node --test platform-ui/tests/coordination.test.mjs`: 11 passed.
- `node platform-ui/tests/coordination-panel-e2e.mjs`: passed. Controlled HTTP fixture exercised actual panel/session and full app mounting, escaped source HTML, complete charge/attendance display, explicit review, exact sourced-consent body, 409 draft retention, new-head review invalidation, and 390px layout. One intentional controlled POST; no provider calls.
- Full frontend suite with `PROOFKEY_PLAYWRIGHT_MODULE` and `PROOFKEY_CHROME_PATH` set: 91 tests, 85 passed, 6 skipped, 0 failed. Counts include concurrently added Customer tests present at verification time. The six skipped tests use a separate optional browser gate.
- An initial browser-enabled suite attempt without `PROOFKEY_CHROME_PATH` produced five launch failures because Playwright's bundled browser was absent. Rerunning with installed Google Chrome passed all enabled tests.
- `git diff --check` and Node syntax checks for app/coordination/panel passed.
- Read-only real service check at `http://127.0.0.1:8105`, case `terms-main-backend-20261010`: no page errors, no write requests, and no horizontal overflow at 390px. Desktop and mobile screenshots were visually inspected. The final booking display clearly separates the saved local receipt from physical delivery, with consent recorded for that local booking.

## Evidence and integration implications

Latest controlled UI screenshots: `/var/folders/z3/7xw9ny8s7nl3hg_zdw7_8_5r0000gn/T/proofkey-coordination-team-RFOs2F/`.

Real-service screenshots: `/var/folders/z3/7xw9ny8s7nl3hg_zdw7_8_5r0000gn/T/team-real-7kgLEh/desktop.png` and `mobile.png`.

The controller must serve `/coordination.js`, `/coordination-panel.js`, `/coordination.css`; old full-app browser fixture maps must also supply them. Root was notified and updated these separately. This task did not claim backend command acceptance from isolated fixture tests; root integration verification owns PostgreSQL/HTTP command semantics and end-to-end eight-command replay. No live inference or external carrier action was performed.

## Follow-up readability review

Coordinated cases now show the actionable coordination next step in Summary instead of the latest source JSON. Activity summarizes an internal coordination audit only when its event ID, sender and parsed identity/command/version/source revision match the persisted coordination audit history, with sandbox metadata and known phase/command values. The concise entry retains a source-event button that opens the unchanged raw record in Sources. Unknown or unbound JSON and legacy source summaries retain their original rendering.

The browser regression first failed on the raw JSON summary, then passed after the fix. It verifies concise summary/activity, no `attestation_scope` or raw JSON in the bound audit entry, raw-source preservation through the event link, and unchanged legacy behavior. The updated browser script, all 11 pure coordination tests and `git diff --check` passed.
