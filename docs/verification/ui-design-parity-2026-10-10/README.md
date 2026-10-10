# Right onTime UI revision and verification

Date: 10 October 2026. Local integrated platform, not a production deployment.

## What changed

- Customer follows the approved source composition: 640px shell, forest order header, parcel context, one card, two in-card progress bars and compact help/status/stop controls. Internal event IDs and the mandatory timestamp/evidence form are removed from the customer task.
- A current recorded offer supplies its own window and evidence references. Missing options show an explicit empty state. Price, availability and booking remain unconfirmed; no reference fixture data was copied into real cases.
- Team has a distinct current-proposal card, a 290px task-oriented case rail, readable Task control/Activity text, and visible header status. Existing model, media, evidence, approval and sandbox controls remain available.
- Stale recovery now returns to current offers instead of rebinding old terms. Same-snapshot supersession observed during preflight blocks submission. Previously dispatched uncertain requests retain their original payload/key; definite 4xx failures cannot use that recovery exception.
- The navigation test now uses a bounded request wait and setup cleanup. An earlier parallel run hung at an unbounded test wait and was explicitly interrupted; four diagnostic reproductions and the standalone test did not establish a production race. The final complete run used serial test execution.

The original final HTML package under `design/right-ontime/prototype` was the visual reference. This restores its composition and hierarchy, not its simulated bookings or invented sample fields.

## Verified

| Check | Result | Scope |
|---|---|---|
| Final frontend suite | **70/70 passed, 0 skipped** | All browser flags enabled; [complete log](frontend-tests-final.txt) |
| Backend/model suites | **256 tests + 323 subtests passed** | `dwelly_platform`, `dwelly_analysis`, `dwelly_model`, PostgreSQL; no production backend changes in this revision |
| Product HTTP journey | Passed after the stale-offer fix | Recorded offer → customer preference → operator approval → sandbox receipt → new evidence invalidates current status |
| Core HTTP journey | Passed | Create case, text/photo sources, deterministic assessment, consent, sandbox execution, reload |
| Media journey | Passed | Real PNG/WAV validation, separate derived result, explicit adoption, corruption rejection; test provider, not live vision/ASR |
| Communications journey | Passed | Email/transcript/recording import, quarantine/recovery, deduplication and safe text; no external accounts |
| Model UI journey | Passed | 16 authored cutoffs + UI probes, 18 scripted dispatches; simulated transport, not accuracy evidence |
| Independent UI review | Passed after one fix round | Original stale-offer rebind defect reproduced and fixed; narrow test-harness rereview accepted |

The product journey created `product-1791640729081` in disposable schema `proofkey_ui_parity_20261010` at port 8116. Other media/communication/model scripts used and cleaned their own test schemas. Earlier development verification also created synthetic case `product-1791640543220` in the existing local 8105 service, including one local sandbox action; it was retained. None of these were external operational effects or paid provider calls.

Run the frontend with `PROOFKEY_PLAYWRIGHT_MODULE`, `PROOFKEY_CHROME_PATH`, `PROOFKEY_CUSTOMER_BROWSER=1`, and `PROOFKEY_CUSTOMER_URL` configured, then `node --test --test-concurrency=1 --test-timeout=90000 platform-ui/tests/*.test.mjs`. Backend command: `PYTHONPATH=.:tools:runtime/src:runtime/tests PROOFKEY_TEST_DATABASE_URL=<local DSN> python -m pytest --import-mode=importlib tools/dwelly_platform/tests tools/dwelly_analysis/tests tools/dwelly_model/tests -q`.

## Rendered evidence

Fresh screenshots of the user's selected case, without writes:

- [Customer desktop](screenshots/current-customer-desktop.png) · [Customer mobile](screenshots/current-customer-mobile.png)
- [Team desktop](screenshots/current-team-desktop.png)

Controlled fixture screenshots with real local fonts and assets:

- [Customer offer review](screenshots/customer-offer-review-desktop.png) · [Customer status mobile](screenshots/customer-offer-status-mobile.png)
- [Customer empty state](screenshots/customer-empty-desktop.png) · [empty state mobile](screenshots/customer-empty-mobile.png)
- [Team current proposal](screenshots/team-current-proposal-desktop.png) · [stale proposal mobile](screenshots/team-stale-mobile.png)

Desktop, mobile, empty, offer, review and status renders were inspected. Rendered tests cover original dimensions/hierarchy, long IDs, stale reselection, exact evidence/slot binding, safe source text and no 390px document overflow. These are technical checks, not user acceptance or full accessibility certification.

## Parallel live LLM result

The [separate immutable live report](../platform-live-e2e-2026-10-10-rerun/README.md) covers **15 actual API dispatches, 13 retained responses and 12 valid candidates**, across OpenAI, Anthropic and Gemini. All **36 stale/replay assertions** passed. No failed request was automatically retried; no model issued an operational action.

This is **not a correctness pass**. OpenAI produced a rejected state/action combination and an unsupported gate-release claim; OpenAI and Claude disagreed with author state labels on team cases; Gemini produced two incomplete responses. Only three of the 286 team cutoffs were selected, and labels remain unvalidated. Additional conservative reservations were **$0.323108**, not an invoice total. See the report for separate denominators, model identities, raw evidence, and single-assessor semantic notes.

## Limits retained

- This remains a trusted-local-operator preview, not authenticated customer access or cloud production.
- Help, alternate-date and stop controls disclose their operator boundary; they do not create support messages or cancel bookings/jobs.
- The server's revision/hash contract cannot atomically block an offer replacement between the final GET and POST if it leaves the source snapshot unchanged. This revision guards changes visible during preflight; an atomic offer-ID precondition needs a separate backend contract change.
- No live image/ASR call, external carrier, real email/phone connection or physical delivery was tested here.
- Existing unrelated provider fixes were left intact and outside the UI commit scope.
