# Case-state analysis workbench — verification

## Scope and source

Local development integration of the colleague's case-state widget, pinned to `nikb-de/proofkey-dwelly@8fbcd1fb633efa248e4045765a7854138118127d`. Three raw JSON files remain byte-for-byte identical to the fetched source. Local viewer code is intentionally hardened. The [manifest](../../datasets/case-state-widget-v1/manifest.json) retains upstream source hashes.

The [workbench](../analysis-workbench.md) combines a fixed catalog, step-bound evidence projection, separate author references, limited deterministic baseline, local run persistence, and dataset export. The interface runs at `http://127.0.0.1:8093`. This is not a deployment to Cloud Run, a new model experiment, or a connection to the existing Cloud SQL outbox.

## Verification results

| Check | Observed result |
| --- | --- |
| Existing and new Python regression suite, local PostgreSQL included | **439 passed, 705 subtests passed**, exit 0 |
| Node integration and original widget tests | **19 passed, 0 failed**: 17 integration tests plus 2 original test files |
| Actual Chrome browser checks | **11 check groups passed**, all **16** catalog snapshots analyzed |
| Browser exceptions / external requests | **0 / 0** |
| Export readback | 16 input/reference pairs matched current projections and file SHA-256 hashes |
| Source JSON comparison | All 3 files unchanged |
| Independent review | Three correctness findings fixed; focused re-review found no residual actionable blocker |

Fresh combined Python command (local test database, no production access):

```sh
PROOFKEY_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:63119/proofkey \
PYTHONPATH=tools:runtime/src:runtime/tests \
/tmp/proofkey-postgres-tests-20261010/bin/python -m pytest --import-mode=importlib \
  tools/dwelly_service/tests tools/dwelly_cases/tests tools/dwelly_model/tests \
  tools/dwelly_bridge/tests tools/dwelly_analysis/tests contracts/v1 \
  datasets/team-handoff-v1/tests tests/test_dataset_export.py tests/test_cloud_case_smoke.py -q
```

Node command: `node --test case-state-widget/tests/*.test.mjs`.

Browser harness: `case-state-widget/tests/browser-qa.mjs`, with installed Chrome and the bundled Playwright module. See the retained [browser receipt](case-state-analysis-2026-10-10/receipt.json), [desktop view](case-state-analysis-2026-10-10/desktop-results.png), and [mobile view](case-state-analysis-2026-10-10/mobile-results.png). Desktop source/results and mobile source/results were visually inspected.

Browser checks include input/reference separation; run JSON download; N4 readback rather than resend; delayed case, step and run responses; HTTP failure; escaped hostile text; rollback after rejected imports or rendering failure; oversized paste/file rejection; default source JSON loading; and 390px mobile layout without horizontal overflow.

## Review corrections

- Shared viewer rejects completed states with empty criteria or a pending next action, and rejects outgoing self-messages. Three added tests were observed failing before the fix and passing afterward.
- Completion inference now matches the entire supported message grammar. Ten explicit contradictory/unsupported-message checks failed before the fix and pass afterward; normal and N4 affirmative fixtures remain supported.
- The standalone viewer's default JSON route returned 503 because raw bytes were re-serialized as JSON. A regression reproduced 503, then passed with 200 after raw-byte response handling was fixed. Browser QA verifies the default load as well as local imports.

## Limits that remain

Sixteen snapshots comprise one related logistics case family plus a UI fixture. They are not 16 independent outcomes, human-reviewed labels or held-out evaluation data. Every exported row is development-only and ineligible for training promotion.

The baseline is fixture-bounded, not an LLM or general logistics policy engine. Literal state/wait-target agreement is not semantic accuracy. Its `completed` means inferred coordination-goal completion, never verified delivery or business execution. All analysis runs have zero provider calls and zero operational effects.

Local checksummed run files provide corruption detection and readback, not signed evidence or protection from a local writer who can recompute hashes. The loopback service is not an authenticated multi-user internet service. Existing model-provider transports, operational adapters and private cloud case storage remain separate; wiring them to this new contract requires an explicit adapter and tests.
