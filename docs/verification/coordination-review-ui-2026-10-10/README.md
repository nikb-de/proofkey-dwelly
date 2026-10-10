# Coordination review and customer preview — verification

## Implemented boundary

- Team: phase-specific local coordination commands, complete terms/evidence review, snapshot-bound acknowledgement, optional current succeeded model-run context and explicit human review note.
- Customer: full offer, separate consent/booking/delivery status, explicitly simulated local acceptance and immutable retry after uncertain outcomes.
- Backend: strict advisory model binding, transactional simulated evidence plus consent audit, normal source/actor/correlation policy still enforced. No schema reset or destructive migration.
- Runtime: local service on port 8105, PostgreSQL schema `proofkey_live_e2e_20261010`; existing cases/model jobs retained.

## Evidence

Controller regression run:

```sh
PYTHONPATH=.:tools:runtime/src:runtime/tests \
PROOFKEY_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:63119/proofkey \
/tmp/proofkey-postgres-tests-20261010/bin/python -m pytest --import-mode=importlib \
  tools/dwelly_platform/tests tools/dwelly_analysis/tests tools/dwelly_model/tests -q
```

Result: **353 passed, 344 subtests passed**. This includes actual HTTP, PostgreSQL, atomic rollback, replay, stale model/offer/source rejection and a controlled model-transport test. The controlled transport exercises the real durable worker and source binding, but does not measure model quality or spend provider credits.

Final frontend regression run with installed Chrome, Playwright and all optional browser gates: **91 passed, zero skipped, zero failed**. The separate Team panel/full-app browser script also verifies compact audit summaries and raw-source navigation.

## Independent review

The independent reviewer identified defects in the model evidence field name, retry key retention, customer refresh/readback handling, and a nested database-pool acquisition. All were fixed with regression tests. Model context now reads the persisted job without a second case-pool acquisition; binding is validated against the snapshot already locked by the command. The real-HTTP regression succeeds with a one-connection case pool. Scoped re-review approved the implementation with no remaining P1/P2 findings. Review does not certify live model quality, authenticated customer identity, carrier participation or production deployment.

## Reproducible real-browser run

`platform-ui/tests/coordination-real-e2e.mjs` is an opt-in test against a local service. It creates explicitly synthetic fresh cases, drives real Team/Customer controls, verifies resulting HTTP state and retains screenshots. It must not be pointed at a production service. Set `PROOFKEY_COORDINATION_REAL_E2E=1`; the default is skip. Failed harness attempts are retained separately and are not counted as successful end-to-end evidence.

The clean complete run passed: **2 fresh cases, 13 UI commands, 51 HTTP checks/fixture writes, 9 screenshots**, no browser errors or mobile horizontal overflow. Read-only PostgreSQL checks matched all persisted versions and final canonical snapshots exactly. See [real E2E summary](real-e2e-summary.md) and [complete trace](real-e2e-1791642200227-2331def1/report.json).

Demo links while the local service is running:

- Team: `http://127.0.0.1:8105/#case=coord-ui-1791642200227-2331def1-customer`
- Customer: `http://127.0.0.1:8105/customer.html?case=coord-ui-1791642200227-2331def1-customer`

Existing model jobs stayed at 36 succeeded / 3 failed / 3 outcome_unknown; none were added by this verification. The service was restarted after confirming there were no active jobs. Existing cases were preserved; the seven explicitly synthetic harness cases are documented in the E2E summary.

## Limits

No paid model calls were made for this change. Provider access and semantic outcome quality are not established by these checks. Local acceptance explicitly simulates customer evidence; no customer authentication or real carrier/messenger integration is added. `booking_confirmed` is a correlated local readback, never proof of physical delivery. No remote push or cloud deployment is included.
