# Right onTime product workspace — verification

Date: 2026-10-10. Scope: product screens on the existing local PostgreSQL-backed platform, not cloud deployment or provider accuracy certification.

## Delivered

| Screen | Implemented behaviour | Boundary |
| --- | --- | --- |
| Team `/` | Case search/filter/counters; Summary / Requests / Sources; ownership, next step and activity; existing evidence, model, review and execution controls | Source IDs are retained; case titles are presentation-only; no invented outcomes |
| Customer `/customer.html?case=…` | Choose a requested window, review supporting evidence, submit a revision-bound proposal, read current status | Operator-assisted preview, not customer authentication; no approval or execution from Customer |
| Preparation `/preparation.html` | Current capabilities, six adapter mappings, process/acknowledgement/readback settings, browser-local save/load and JSON export, read-only preflight | Drafts do not activate runtime profiles or connect external systems |

Original visual reference: `design/right-ontime/prototype` (Forest/paper/brass, Manrope/Inter). Actual backend records are used; prototype simulation behaviour is not imported.

## Verification

- Frontend suite with all browser checks enabled: **60/60 passed, no skips**. This includes Customer, Team navigation, polling, source import, storage and stale-replay regressions.
- Backend platform suite: **90 tests and 31 subtests passed** against PostgreSQL, including **15 new product-route checks**. New static files are explicitly allowlisted; traversal and unlisted files remain unavailable.
- Product browser E2E: **passed** against a separate PostgreSQL test schema. Customer preference created exactly one proposal, no review/action. Explicit Team review and execution created one sandbox receipt; later evidence invalidated its current status without deleting history.
- Existing core browser E2E: **passed** for creation, text/photo evidence, deterministic assessment, proposal, consent review, execution, readback and mobile layout.
- Existing media browser E2E: **passed** for PNG/WAV validation, explicit extraction, hash-bound derived results, human adoption, reload, corrupt-file rejection and draft retention. Vision/ASR used a clearly labelled test provider, not paid live services.
- Existing communications browser E2E: **passed**, covering imports, quarantine, recovery, deduplication, source provenance and draft retention.
- Existing model browser E2E: **passed**, 16 authored cutoffs plus UI probes, 18 scripted model dispatches. Transport was simulated; no live-provider accuracy claim. Verified waiting/unknown/stale states, immutable receipts and no automatic retries.
- Desktop and 390px mobile layouts: checked on all three screens; no document overflow or browser exceptions. Separate regression uses maximum-length 64-character case/order IDs.
- New preparation E2E saved/reloaded/exported a six-mapping profile and ran preflight using GET requests only. Export contains `runtime_activation:false` and `status:local_draft`.

## Review fixes

1. A pending/failed case selection could leave the Customer link pointing at the previous case. It now follows the selected case immediately; delayed and failed reads are covered.
2. An immutable cached POST replay could overwrite newer same-revision case state. Mutation recovery is now separate from current-state readback; failed readback shows an unknown current status without resubmitting.
3. Long valid order IDs could overflow Customer mobile layout. All case-strip metadata wraps.
4. Historical sandbox receipts no longer override the next step after new evidence.

Three independent component reviews and one final integration review completed. The navigation and Customer retry/mobile findings were fixed, regression-tested and scoped-reviewed; final integration review reported no new important findings. Reviews were code/spec inspections, not additional live-provider evaluations.

## Screenshots

- [Team desktop](screenshots/team-desktop.png) / [mobile](screenshots/team-mobile.png)
- [Customer review](screenshots/customer-review.png) / [mobile status](screenshots/customer-mobile-status.png)
- [Preparation desktop](screenshots/preparation-desktop.png) / [mobile](screenshots/preparation-mobile.png)

Screenshots use synthetic test cases. The development service remains on port 8105 with its existing data and budget scope. No new paid model calls, carrier actions, payments or outbound communications were made for this revision.

## Reproduce

Use the repository's configured Python environment with `PYTHONPATH=.:tools:runtime/src:runtime/tests` and a disposable PostgreSQL `PROOFKEY_TEST_DATABASE_URL`.

```sh
python -m pytest --import-mode=importlib -q tools/dwelly_platform/tests
node --test platform-ui/tests/*.test.mjs
```

Set `PROOFKEY_PLAYWRIGHT_MODULE` and `PROOFKEY_CHROME_PATH` to enable the browser unit/regression checks. Set `PROOFKEY_CUSTOMER_BROWSER=1` and `PROOFKEY_CUSTOMER_URL` to a running local platform for the long-ID test. The five real HTTP browser scripts are `platform-ui/tests/{product-e2e,e2e,media-e2e,communications-e2e,case-model-e2e}.mjs`; product/core use `PROOFKEY_BASE_URL` (use a disposable test service). Other scripts create and clean their own isolated schemas.

## Still outside this revision

Authenticated customer accounts, cloud deployment, external connector activation, outbound messaging, real carrier availability/pricing and physical delivery confirmation remain unimplemented. Customer and Preparation labels make these limits explicit. Live text-model controls and their previous receipts are retained, not newly evaluated by this UI revision.
