# Platform UI controls verification — 2026-10-10

All four existing platform browser E2E workflows passed on the merged working tree. The 28 targeted UI/session/polling/communications tests passed with zero skips. No product source was changed. The tests used real local HTTP and PostgreSQL, isolated schemas and ephemeral ports; no new live provider call was made by this verification.

## Results

| Workflow | Result | Evidence and boundary |
| --- | --- | --- |
| Core case controls | PASS, 11 named checks | Create case; add text/photo; deterministic analysis; bounded reschedule proposal; explicit consent/approval; one sandbox execution; receipt, reload, inert source text, mobile layout. Port 59280. |
| Media controls | PASS, 12 named checks | Real PNG/WAV parsing, image/ASR buttons, separate derived output, explicit human review before adoption, source hashes, reload, corrupt-media error and draft retention. Exactly 2 `test-provider` dispatches, 0 live calls. |
| Communications controls | PASS, 15 named checks | JSON/MIME/transcript/audio imports; quarantine; explicit retry; trusted test-route recovery; deduplication; conflicting redelivery; preserved drafts; provenance and mobile layout. 6 canonical events and 6 receipts; 0 providers. |
| Model controls | PASS, 6 named checks plus 16 CLI cutoffs | Real HTTP/PostgreSQL/worker with `SIMULATED` external transport. Run button, queued/running-to-result polling, inspector stays open, reload without resubmission, new evidence makes old result stale, uncertain outcome stays terminal, selection via case-list button, zero effects and mobile layout. 18 scripted dispatches, 0 live calls. |
| Targeted UI tests | PASS, 28/28; 0 skipped | Includes actual browser DOM tests for polling inspectors, case selection, preserving drafts, stale responses, current/late failures, explicit retry and communications errors. |
| Additional read-only controls | PASS, 3 checks | Unconfigured model button disabled; resolved case excluded from review queue; integrations display disabled providers without any POST or external request. |

The core schema `platform_controls_ui_6704edc4425845bb93cac655e81821c3` was dropped and absence confirmed after the tests. Media, communications and model fixtures also confirmed their own randomly named schemas were dropped; see their database reports. All servers started by this verification were stopped. Existing ports 8095 and the coordinator's 8105 were not stopped or reconfigured.

## Commands

Shared environment: `PROOFKEY_TEST_DATABASE_URL` pointed to the authorized loopback PostgreSQL database; `PROOFKEY_TEST_PYTHON=/tmp/proofkey-postgres-tests-20261010/bin/python`; `PROOFKEY_PLAYWRIGHT_MODULE=/Users/nbk/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs`; `PROOFKEY_CHROME_PATH=/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`; `PYTHONPATH=.:tools:runtime/src`.

```sh
PROOFKEY_BASE_URL=http://127.0.0.1:59280 PROOFKEY_QA_DIR=docs/verification/platform-live-e2e-2026-10-10/ui/core node platform-ui/tests/e2e.mjs
PROOFKEY_MEDIA_PORT=0 PROOFKEY_QA_DIR=docs/verification/platform-live-e2e-2026-10-10/ui/media node platform-ui/tests/media-e2e.mjs
PROOFKEY_QA_DIR=docs/verification/platform-live-e2e-2026-10-10/ui/communications node platform-ui/tests/communications-e2e.mjs
PROOFKEY_QA_DIR=docs/verification/platform-live-e2e-2026-10-10/ui/model node platform-ui/tests/case-model-e2e.mjs
node --test platform-ui/tests/session.test.mjs platform-ui/tests/polling.test.mjs platform-ui/tests/communications.test.mjs
```

The core server used `migrate`, `PlatformStore`, and `create_server(port=0)` with no provider installed. Other E2E scripts launched their existing test fixtures, each in its own schema. `PROOFKEY_MEDIA_PORT=0` prevented collision with existing services.

## Screenshots and retained receipts

- [Core desktop](core/desktop.png), [core mobile](core/mobile.png), [disabled integrations](core/integrations-disabled.png).
- [Media desktop](media/desktop.png), [media mobile](media/mobile.png), [media database report](media/database-report.json).
- [Communications desktop](communications/desktop.png), [communications mobile](communications/mobile.png), [summary](communications/summary.json), [database report](communications/database-report.json).
- [Model stale result](model/desktop-stale.png), [model uncertain outcome](model/mobile-unknown.png), [browser report](model/browser-report.json), [database report](model/database-report.json), [CLI report](model/runner/report.json).

Desktop core/media/communications screenshots were visually inspected. Expected negative-test states include `invalid_media`, quarantined malformed audio, inert script-like source text and a terminal unknown provider outcome; these are passing guardrail tests.

## Separate read-only inspection of existing live receipts

The coordinator separately ran live providers on port 8105. This verification only read existing case/job records and opened receipt details. A browser request guard rejected non-GET/HEAD requests; no write was attempted. No run button was clicked.

- Claude canary `e2e-claude-canary-1010-case-002-s0`: succeeded transport; provider `anthropic`; requested/observed `claude-sonnet-4-6`; request `req_011CftePJg86xxV9ZeVaCao6`; UI correctly labels revision-1 result stale against current revision 2.
- Gemini canary `e2e-gemini-2-5-flash-canary-1010-case-002-s0`: succeeded transport; provider `gemini`; requested/observed `gemini-2.5-flash`; request `Oz_KarfoINn5nsEPuZ73oA4`; same correct stale binding. The coordinator confirmed both are intentional later-evidence probes, not unexpected failures.
- Current Claude case `e2e-claude-full-1010-case-002-s3`: API `analysis=current`; UI `Input revision 4 · Current evidence` and `Coordination: Waiting`; request `req_011CfteRxWFKruWHv86EuqU9`. No actions or external effects.

All inspected jobs displayed their actual receipt and counters (1 dispatch, 0 automatic retries, 0 operational effects). No page errors occurred. Screenshots: [Claude stale](live-claude-read-only.png), [Gemini stale](live-gemini-read-only.png), [Claude current](live-claude-current-read-only.png).

## Failures and limits

No confirmed product defect was found in the exercised controls. The first ad-hoc live inspection attempted to switch an already loaded page by changing only its URL fragment and timed out waiting for the second case. The application initializes from the fragment but uses case-list controls for later selections; the supplied E2E already documents this constraint. Fresh-page inspection passed, and the case-list selection control passed in the model E2E. No source change was made for this harness issue.

The live receipt inspection is display/binding evidence, not model-quality or production-readiness evidence. No failed live-provider receipt was present in the three selected records; simulated uncertain/error outcomes and UI error rendering were tested separately. No real courier, payment, outbound message, phone call or new paid model request was initiated by these checks.
