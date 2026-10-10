# Coordination UI: real browser, HTTP and PostgreSQL verification

Clean full run passed on 2026-10-10 against `http://127.0.0.1:8105`, with real headless Google Chrome, the real Team and customer applications, and PostgreSQL schema `proofkey_live_e2e_20261010`.

Machine-readable evidence: [full report](real-e2e-1791642200227-2331def1/report.json).

## Scope and result

- Two newly created, uniquely named synthetic cases; 13 actual UI command submissions, all HTTP 200; 51 direct HTTP checks or fixture writes; nine screenshots.
- Customer path: initialize, request cancellation, confirm cancellation using correlated Dispatch source, record complete offer, customer checkbox and atomic local acceptance, request booking, confirm booking using correlated Dispatch source.
- Separate sourced-consent path: initialize, request cancellation, confirm cancellation, record offer, record sourced consent, escalate.
- Every UI command was followed by a fresh real HTTP case read. Checks covered incremented version, audit event, canonical revision/hash, source/evidence IDs, local sandbox metadata and unconfirmed physical delivery. The atomic acceptance added exactly two canonical revisions and retained the exact offer ID/hash, simulated source event, and unauthenticated-customer qualification.
- Read-only direct PostgreSQL queries confirmed every stored version and exact equality of the latest aggregate and canonical snapshot with HTTP. Both cases have zero model links. Browser network interception permitted only same-origin reads and owned-case coordination POSTs; it fulfilled no HTTP response. No blocked requests or browser errors occurred.
- Team and customer screenshots were taken at desktop and 390px. Both mobile pages had no document horizontal overflow. Customer offer and final-status screenshots and Team screenshots were visually inspected; local-preview and physical-delivery qualifications remain visible.

| Case | Final phase | Versions | Canonical revision / event count | Model links |
| --- | --- | --- | --- | --- |
| `coord-ui-1791642200227-2331def1-customer` | `booking_confirmed` | 1–7 | 12 / 12 | 0 |
| `coord-ui-1791642200227-2331def1-sourced` | `escalated` | 1–6 | 10 / 10 | 0 |

All audits attribute commands to configured local principal `local-operator`; that label is not identity authentication. The dates, actors, order identifiers, source messages and carrier readbacks are explicitly synthetic. Model calls: zero. External business effects: zero. Physical delivery: not confirmed. Success establishes a local workflow, not carrier participation or real customer consent.

## Screenshots

- [Team: offer desktop](real-e2e-1791642200227-2331def1/team-awaiting-consent-desktop.png)
- [Team: offer mobile](real-e2e-1791642200227-2331def1/team-awaiting-consent-mobile.png)
- [Customer: offer desktop](real-e2e-1791642200227-2331def1/customer-awaiting-consent-desktop.png)
- [Customer: offer mobile](real-e2e-1791642200227-2331def1/customer-awaiting-consent-mobile.png)
- [Customer: acceptance saved](real-e2e-1791642200227-2331def1/customer-acceptance-saved-mobile.png)
- [Team: pending booking](real-e2e-1791642200227-2331def1/team-booking-pending-desktop.png)
- [Team: confirmed local booking](real-e2e-1791642200227-2331def1/team-booking-confirmed-desktop.png)
- [Customer: confirmed local booking](real-e2e-1791642200227-2331def1/customer-booking-confirmed-mobile.png)
- [Team: escalation](real-e2e-1791642200227-2331def1/team-escalated-desktop.png)

## Reproduction

`platform-ui/tests/coordination-real-e2e.mjs` skips by default. Set `PROOFKEY_COORDINATION_REAL_E2E=1` and optionally `PROOFKEY_BASE_URL` to a loopback HTTP origin. The test creates fresh cases only; it performs no cleanup or existing-case mutation. Browser and fixture writes are scoped to test-owned cases. Direct PostgreSQL verification additionally requires `PROOFKEY_E2E_DATABASE_URL`, `PROOFKEY_E2E_DATABASE_SCHEMA`, and a `PROOFKEY_E2E_PYTHON` executable with psycopg installed. The database URL is validated as loopback and is not written to the report.

The successful command used local Python `/tmp/proofkey-postgres-tests-20261010/bin/python`, schema `proofkey_live_e2e_20261010`, and the controller-supplied localhost PostgreSQL connection. `node --check` passed, and invocation without the opt-in flag printed SKIP without creating a case.

## Harness debugging retained for transparency

Four initial runs failed for harness navigation reasons; their JSON reports and available failure screenshots remain in sibling run directories. Two used the mocked test's `/team` route instead of the real `/` route; one redundantly selected initialize and collapsed its setup form; one reused the same URL without a reload after fixture ingestion and therefore inspected the old snapshot. The corrected harness explicitly reloads and uses real page controls. No application code was changed to make these tests pass, and no failed UI command was replaced with an API command.

The fourth run's owned case was resumed successfully in `real-e2e-1791642167266-570d71e5` before the clean full run. Across all harness attempts, seven synthetic cases were created and retained: three with only a source event, the resumed complete customer case, its sourced-consent companion, and the two clean full-run cases above. Existing non-test cases were untouched.
