# Transactional model analysis — verification

Date: 2026-10-10. Base: `e106935` on `codex/proofkey-runtime`. This is a local integration delivery, not production or model-quality certification.

## Delivered

- The existing analysis UI supports configured OpenAI, Anthropic and Gemini profiles; offline remains the default.
- New model requests go through the loopback API into PostgreSQL: frozen evidence/profile/prompt, idempotency key, atomic retained budget reservation, leased dispatch, durable response, validated candidate and atomic result publication.
- Provider text and metadata are stored before local validation. Invalid output keeps a failed record and available receipt; there is no silent baseline substitution.
- Lost POST acknowledgement replays the same key. Accepted work resumes by GET after reload, including when its configured profile no longer has credentials. No automatic provider retry occurs after a possibly dispatched request.
- UI shows job state separately from candidate state, requested/observed model identity, nested usage, timestamps and transaction details. Source timeline stays aligned with restored evidence cutoffs.

## Verification evidence

| Check | Result |
|---|---|
| Focused analysis package with real PostgreSQL | 81 passed, 111 subtests passed. |
| Full selected backend/contracts/dataset regression | 492 passed, 758 subtests passed in 57.95s. |
| JavaScript unit/regression suite | 42 passed. |
| Existing browser suite | 11 groups, all 16 source snapshots; zero browser errors/external requests. |
| Model lifecycle browser suite | 10 groups using explicitly simulated endpoints; zero actual provider calls. |
| Combined UI → real API → real PostgreSQL | 6 groups using a simulated provider transport; single dispatch marker, bound downloaded/read-back result, nested token rendering, reload GET recovery and mobile layout. Nonzero restored step/source alignment also asserted. |
| Independent review | Transaction, model and integration reviews; all reproduced findings fixed and rechecked. |
| Live provider canaries | **NOT_RUN: local OpenAI/Anthropic/Gemini credentials unavailable.** |
| Cloud/IAM/Secret Manager mutations | **NONE.** |

Raw browser receipts and screenshots are in [the evidence directory](transactional-model-analysis-2026-10-10/). They explicitly identify simulated providers. The fake provider request IDs and token counts in those screenshots are test data, not actual provider participation.

Full Python command (local test DSN supplied through `PROOFKEY_TEST_DATABASE_URL`):

```sh
PYTHONPATH=tools:runtime/src:runtime/tests python -m pytest --import-mode=importlib \
  tools/dwelly_service/tests tools/dwelly_cases/tests tools/dwelly_model/tests \
  tools/dwelly_bridge/tests tools/dwelly_analysis/tests contracts/v1 \
  datasets/team-handoff-v1/tests tests/test_dataset_export.py tests/test_cloud_case_smoke.py -q
```

Review fixes included: explicit null timeout rejection; context-independent upward-rounded reservation estimates; replay before credential admission; stop checks before transport; above-cap rejection as budget exhaustion; correct nested usage display; saved-job recovery with unavailable credentials; and restored source-viewer step synchronization.

## Reproduce

See [model operations and API contract](../model-analysis-operations.md) for real opt-in startup, credential handling and job semantics. The existing offline path remains:

```sh
python -m tools.dwelly_analysis serve --port 8093
node --test case-state-widget/tests/*.test.mjs
```

For the integration fixture, supply a **test** PostgreSQL DSN in `PROOFKEY_TEST_DATABASE_URL`, then run:

```sh
python -m tools.dwelly_analysis.tests.browser_fixture_server
```

In a second shell with Playwright and Chrome configured:

```sh
node case-state-widget/tests/postgres-browser-qa.mjs
```

The fixture uses port8094 and a dedicated test schema, and substitutes the transport in-process. The browser script refuses profiles other than `browser-fixture` / `SIMULATED-NOT-A-PROVIDER`. It cannot be used as evidence that a provider responded. Stop this fixture after testing; the user workbench is port8093.

## Remaining boundaries

- Live provider smoke, semantic evaluation and human-label calibration remain unverified. The 16 snapshots are related development examples, not independent held-out gold cases.
- Completely deleted profile configurations cannot currently be restored through the UI; their frozen jobs remain available by the API. Unavailable credentials on an existing profile do not prevent UI recovery.
- No execution adapters, refunds, rescheduling, media analysis or Cloud SQL case-outbox dispatch are enabled by this change. These model outputs are proposals with zero business effects.
- The service is loopback-only, not authenticated multi-tenant production. Model jobs use local PostgreSQL in this verification; production identity, Secret Manager and cloud worker lifecycle require a separate deployment change.
- Reservations use configured price assumptions, not a provider billing guarantee. The 660-second lease does not make socket timeout an end-to-end wall-clock deadline. Unknown outcomes retain reservations and are never automatically resent.
