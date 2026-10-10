# Task 3 — Customer coordination UI

Implemented in `platform-ui/customer-coordination.js`, with the coordination branch in `customer.js` and scoped styles in `customer.css`. Existing `customer-model.js` and `customer.html` did not need changes; legacy decisions remain on their existing branch.

The new branch displays complete terms (UTC display plus original explicit offsets, handover, required attendance, charge in currency and exact minor units), stored offer identity/hash, record freshness, consent freshness, pending local requests, booking receipts and physical delivery unconfirmed. Current consent after a booking request/confirmation is labelled as recorded for that local booking, rather than falsely invalidated by the booking audit itself. Only ready-to-book consent is labelled fresh for a new booking request.

Acceptance requires an explicit checkbox and posts only `record_local_acceptance` with the exact revision, snapshot hash, workflow version, offer ID, terms hash and `acknowledged:true`. The UI describes the action as operator-assisted local preview and simulated acceptance with no authenticated customer identity. Rendering, loading, checkbox changes and current-term review do not write. Inflight duplicates are blocked. An uncertain outcome retains the immutable request and key even after a newer read. A definite HTTP 4xx clears the pending request and requires another review; a conflict also refreshes current state while retaining the original binding. Returned receipts must have exactly two added canonical revisions, matching offer/hash, next workflow version, sandbox metadata, and consent `mode:local_preview_simulation` / `authenticated:false`. The latest case is fetched afterward; a failed read leaves the saved receipt explicitly separate from unknown current status. Older overlapping refreshes cannot overwrite a newer read or a mutation.

## Verification

- TDD: the initial six behavior tests failed before production implementation; the overlap protection and stronger receipt tests were also observed failing before fixes.
- `PROOFKEY_CUSTOMER_BROWSER=1 node --test platform-ui/tests/customer-coordination-browser.test.mjs platform-ui/tests/customer-coordination.test.mjs`: 9 pass, 0 fail, 0 skip.
- `node --test platform-ui/tests/*.test.mjs`: latest run 88 total, 75 pass, 0 fail, 13 optional browser tests skipped. Counts include concurrent Team additions in the shared worktree.
- The isolated Chrome browser test uses actual repository JS, CSS, fonts and brand assets plus controlled HTTP fixtures. It checks no writes on render/checkbox/refresh, exact acceptance POST, receipt display, legacy branch retention, safe hostile text rendering, and no horizontal overflow at 390px.
- Visually inspected the rendered 390px acceptance screenshot after correcting the fixture server to serve the same design assets as the actual platform server. Forest/neutral layout, readable complete terms and checkbox/button were intact.
- Screenshots: `customer-coordination-mobile.png`, `customer-coordination-booking-mobile.png`, `customer-coordination-desktop.png` alongside this report.

## Integration handoff

New public static asset required: `/customer-coordination.js` → `platform-ui/customer-coordination.js`. No other new runtime assets. Tests add `customer-coordination.test.mjs` and `customer-coordination-browser.test.mjs`; the browser test runs its own temporary loopback static server and does not require port 8105 or a provider call. Real backend HTTP route/restart/integration verification remains with Task 4. No commits, no paid calls, no external messages or booking actions were performed.

## Independent-review corrections

Reproduced and fixed regressed post-acceptance GET readback: a receipt at revision 6 followed by GET revision 4 formerly set `statusConfirmed=true`. It now retains the receipt, keeps status unverified, and refuses the old head. Same-revision readback must match its hash; later workflow versions must retain the exact acceptance audit identity/version/revision in history. A later valid matching read restores confirmed status. Unverified screens label the terms as last-read and do not call the old head current. Existing request-generation guards also invalidate refresh requests that predate a submission.

Centralized both legacy Check status and Refresh status through the shared case-loading branch. If Team initializes coordination while a legacy customer page is open, a normal status refresh now enters coordination without a full page reload. The browser regression was demonstrated failing against the former Check status callback, then passing after restoration of the fix. The post-acceptance readback regression likewise failed before the guard was added.

Latest focused verification: `PROOFKEY_CUSTOMER_BROWSER=1 node --test platform-ui/tests/customer-coordination-browser.test.mjs platform-ui/tests/customer-coordination.test.mjs` — 10 pass, 0 fail, 0 skip. Controller owns the final whole-repository rerun.
