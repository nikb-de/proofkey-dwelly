# Delivery terms coordination — verification

Date: 2026-10-10. Scope: local PostgreSQL/HTTP backend, not production or a live-LLM evaluation.

## Implemented

- Additive platform migration 1 → 2 with old snapshots and idempotency receipts preserved.
- Seven-step main-case replay: initialize, cancellation request, cancellation confirmation, replacement offer, explicit consent, booking request, booking confirmation.
- Current revision/hash and workflow version preconditions; body-bound idempotency; atomic canonical audit plus aggregate writes.
- Complete offer terms include slot, handover, required attendance and charge. New offer invalidates old consent; intervening source events block booking with stale consent.
- Local readbacks require Dispatch routing and exact request/hash correlation. Physical delivery stays `not_confirmed`.
- Dedicated English coordination/freshness states; current legacy decisions keep their existing priority.
- Frozen source, explicit date/directory adaptation, no authored labels or future events in an earlier inference snapshot.

## Review and regression

Independent read-only review found two concrete issues during implementation:

1. The replay trusted its last POST instead of checking the final persisted GET.
2. A large evidence list could exceed the canonical audit text limit; escalation reasoning was not copied into model-visible audit context.

Both have dedicated regression coverage. The reviewer re-ran the original corrupted-final-readback probe and confirmed it now fails closed. No remaining P1/P2 finding was identified in the reviewed scope.

| Final verification | Result |
| --- | --- |
| Platform + analysis + model tests | 319 tests and 344 subtests passed in 49.46 seconds; [JUnit receipt](pytest-final.xml) |
| Frontend suite with browser flags enabled | 70 passed, 0 failed, 0 skipped; 17.05 seconds |
| Full primary-case local HTTP smoke | 46 requests with expected status; revision 21, workflow version 7, `booking_confirmed` |
| Source integrity | Frozen SHA-256 unchanged |
| Existing local service | Migrated and restarted at `127.0.0.1:8105` with the same database, provider settings and budget scope |
| Persistence after restart | 36 pre-existing cases retained; one new demo case; model jobs unchanged at 42 |
| New provider calls / external business effects | 0 / 0 |

The retained [local smoke receipt](local-smoke.json) records exact request IDs, offer hash, final snapshot hash and before/after counts. The new case is `terms-main-backend-20261010`. Its 21 events are 11 source messages, one labelled source-context event, seven command audits and two explicitly synthetic Dispatch readbacks. It confirms local coordination, not physical delivery. The future-dated derivative uses anchor `2026-10-10`; the frozen source remains historical.

Frontend checks protect the existing UI and ran before the local server restart. They do not prove that new coordination-specific UI controls exist; wiring those controls remains listed below.

The old active model configuration was deliberately retained on restart. The separately verified current-candidate configuration is `tools/dwelly_analysis/model-profiles.current.json`; selecting it and collecting real provider receipts is a distinct next step. No old model result is attributed to a new model.

## Reproduce

Set `PROOFKEY_TEST_DATABASE_URL` to an isolated local PostgreSQL database and run:

```sh
PYTHONPATH=.:tools:runtime/src:runtime/tests python -m pytest --import-mode=importlib \
  tools/dwelly_platform/tests tools/dwelly_analysis/tests tools/dwelly_model/tests -q
```

The tests create and remove unique test schemas. They do not invoke paid providers. Actual provider accuracy, customer identity and carrier participation remain unverified by these tests.

The runnable script and field-level API contract are documented in [delivery-terms-coordination-v1.md](../../api/delivery-terms-coordination-v1.md).

## Remaining work

- Wire model proposals and the customer/team UI to the new coordination commands. The new backend replay is scripted, not autonomous LLM reasoning.
- Record the 50-second mobile flow after UI and model validation. No video is claimed here.
- Replace configured local actor identities with authenticated upstream identity and signed operational readbacks before real-world use.
- Current model profiles are a separately selectable candidate configuration; official-documentation and loader checks do not establish API access or workload quality.
