# Unified platform verification — 2026-10-10

## Outcome and scope

The local case platform joins canonical PostgreSQL cases, immutable decisions, human reviews, deterministic sandbox rescheduling, optional model jobs and explicit photo/ASR processing. The main UI is `http://127.0.0.1:8095/`; evaluations remain a separate workspace at port 8093.

This is **local integration evidence**, not production readiness or model-quality evidence. No paid provider call, real carrier operation, message, payment, deployment or public push was performed by this change. Provider keys were unavailable to the running process; all three case-model profiles reported `missing_api_key`. Media dispatch is disabled by default.

## Verification results

| Check | Observed result |
|---|---|
| Selected canonical Python regression roots | 568 tests and 789 subtests passed |
| Platform and existing widget JavaScript | 52 tests passed |
| Actual HTTP + PostgreSQL case browser flow | Passed |
| Actual HTTP + PostgreSQL media browser flow | Passed; 2 test-provider dispatches, 0 live calls |
| Independent scoped code review | Initial findings fixed and re-reviewed; no remaining scoped blocker |
| OpenSpec and whitespace checks | Passed before archive; final validation recorded with this change |

Python covers the canonical platform, case API/storage, model and analysis services, shadow bridge, frozen contracts and dataset handoff. Archived source copies under `outputs/` are intentionally excluded; running bare pytest over those copies causes duplicate-module collection, not evidence about the canonical implementation.

```sh
PROOFKEY_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:63119/proofkey \
PYTHONPATH=.:tools:runtime/src:runtime/tests \
python -m pytest --import-mode=importlib \
  tools/dwelly_platform/tests tools/dwelly_service/tests tools/dwelly_cases/tests \
  tools/dwelly_model/tests tools/dwelly_bridge/tests tools/dwelly_analysis/tests \
  contracts/v1 datasets/team-handoff-v1/tests \
  tests/test_dataset_export.py tests/test_cloud_case_smoke.py -q

node --test platform-ui/tests/session.test.mjs case-state-widget/tests/*.test.mjs
node platform-ui/tests/e2e.mjs
PROOFKEY_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:63119/proofkey \
PYTHONPATH=.:tools:runtime/src node platform-ui/tests/media-e2e.mjs
```

Use the environment's Python, Playwright and Chrome paths; browser tests accept `PROOFKEY_TEST_PYTHON`, `PROOFKEY_PLAYWRIGHT_MODULE`, `PROOFKEY_CHROME_PATH` and `PROOFKEY_BASE_URL` overrides. `python-junit.xml` records the final repeated Python run.

## Browser evidence

The case flow creates `ui-1791636586853`, appends text and a photo, runs deterministic analysis, proposes a bounded future slot, records explicit consent review, executes a local sandbox booking once and verifies the retained receipt after reload. It also checks inert HTML-like source text and mobile overflow. The synthetic case remains in the local demo schema; it is not a real customer case.

- [Case workspace — desktop](case-workspace-desktop.png)
- [Case workspace — mobile](case-workspace-mobile.png)

The media flow uses actual PNG/WAV bytes, Pillow decoding, ffprobe inspection, HTTP, PostgreSQL and the real MediaService. **Only the external provider is replaced with an explicitly named test double.** It checks source hashes, validation, separate derived output, provider receipt, mandatory operator review before adoption, internal-event provenance, reload, rejection of corrupt media, retained drafts and inert HTML-like output. Its isolated test schema was removed and absence verified.

- [Media review — desktop](media-review-desktop.png)
- [Media review — mobile](media-review-mobile.png)

Screenshots include deliberate negative cases: visible `invalid_media` and script-like text are expected test evidence, not generated customer data or executed code. Desktop screenshots were inspected visually; automated mobile checks found no horizontal overflow.

## Review findings addressed

Domain, model/media and UI implementation were delegated in parallel with separate file ownership; an independent reviewer assessed their integration. The controller reconciled interfaces and ran the aggregate verification. PostgreSQL sandbox execution was chosen instead of treating the legacy SQLite fixtures as authority. These choices accelerate the local integration but do not connect a real carrier or publish the branch.

- Current model admission now holds the canonical case lock through durable job admission. Historical replay cannot create a replacement job.
- Text and media share a durable budget bucket and admission lock; media conservatively reserves USD25 per provider/model/experiment. Rollback, restart and precision regressions are covered.
- Non-executable operator follow-ups do not masquerade as execution-ready actions; blocked proposals can still be rejected.
- Media results match the actual provider envelope and require explicit review before they become internal evidence.
- Database/internal errors map to sanitized `503 platform_unavailable`; known invalid input/conflicts retain explicit public codes. Non-string exceptions cannot crash that mapping.

## Remaining boundaries

- Live case reasoning, image interpretation and transcription quality have not been validated here.
- Image generation is reserved for a separate eval workflow; no generator was added to operational cases.
- The local operator is trusted; participant declarations are not authenticated customer identity or verified consent.
- Only sandbox rescheduling executes. Refund, refusal/return and address-change paths do not cause external effects.
- Current caps are local admission reservations, not provider-side billing guarantees. Media permits only one new request per model/experiment under the full USD25 reservation.
- Raw media is stored in local PostgreSQL. Authenticated tenancy, production object storage/retention, malware policy, bounded production workers and real adapter readback remain deployment prerequisites.
- A browser aborting an HTTP read can produce a BrokenPipe diagnostic from the standard-library server; the observed case was a cancelled read, not an action failure. This local server is not the production HTTP layer.
- Existing user files in `docs/dataset-drafts/` were not modified or included in this change.

## Specification

Living requirements: `openspec/specs/unified-case-platform/spec.md`.
Implementation record: `openspec/changes/archive/2026-10-10-unified-case-platform/`.
Operational guide: [platform-operations](../../platform-operations.md).
API and dataset boundaries: [platform-v1](../../../contracts/platform-v1/README.md).
