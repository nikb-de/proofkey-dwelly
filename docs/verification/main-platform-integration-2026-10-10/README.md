# Main/platform integration verification

## Scope and source identity

- Platform parent: `65648beff413b02171121913da94f79abda12064`.
- Original team parent: `da1d17b322bf18a2d522e1061cb02fe0729639cb`.
- Latest team source incorporated: `4fa3f4d0196db82e0816909590d176b0eb0c4e5e`.
- Two-parent integration commit: `4260af2`; latest team merge: `9871a5d`.

The first preservation audit compared all 1,113 main-only files against their original blobs. After incorporating the later team commit, a fresh Git-blob comparison verified all **1,161 main-only files**, with zero missing or changed files; all 51 current authored JSON files match that commit byte-for-byte. The legacy manifest is unchanged. The pinned team manifest has SHA-256 `195aee1ce0675d874e065b7369607a2d65e7c218e7a0027a1524a3de03863880`.

The combined catalog has 54 documents: 51 team documents (50 grouped source families; 286 cutoffs) and three legacy fixtures (16 cutoffs). These counts are not independent examples or evidence of model accuracy. All labels remain unvalidated development annotations.

## Integration changes

- Preserved the GitHub library, search/filter/pagination and server endpoints.
- Preserved the platform runtime, PostgreSQL stores, communications intake, media controls and bounded model runner.
- Added namespaced, pinned team sources alongside legacy fixtures; default export remains legacy, with explicit `--group team` and `--group all`.
- Preserved copied recipients and selected author limits as untrusted evidence. Author limits do not grant execution authority.
- Kept source-only, library and analysis entry points separate. The analysis source viewer does not call the library or model APIs.
- Selected-case analysis revalidates its own source hash and schema, without rescanning every unrelated case on each cutoff.

## Review findings resolved

1. JavaScript accepted numeric copied actor IDs and rejected empty arrays inconsistently with Python/schema. It now requires known string IDs and permits an empty list.
2. The merged source viewer imported a library module graph through the analysis server. Dedicated static-only source assets restore the existing route.
3. Six current cases contain incoming mail addressed to someone else with our actor explicitly copied. Both validators now recognize that observed incoming direction without relaxing outgoing rules.
4. Revalidating the whole expanded catalog for every selected step made exports unnecessarily expensive. Selected metadata lookup retains the selected source validation and avoids unrelated-file dependence.

## Browser and E2E evidence

- [Analysis browser receipt](analysis-browser/receipt.json): 118 selections, covering all 16 legacy cutoffs and first/last states for all 51 team cases; all 54 IDs covered. No page errors, external requests, model calls or operational effects. Includes stale-response protection, N4 readback, source rollback, downloads and mobile layout.
- Communications E2E: real HTTP/PostgreSQL, six canonical events and six retained receipts; MIME/image, transcript, recording, quarantine/retry, conflict retention and deduplication. Zero provider calls. Test schema removed.
- Media E2E: real PNG/WAV validation, explicit processing and human review, derived evidence and persistence; two in-process scripted provider dispatches. Zero live calls. Test schema removed.
- Case-model E2E: 16 legacy authored cutoffs through external CLI and real HTTP, queue/state/polling/reload/stale-result/unknown-outcome checks; 18 scripted dispatches, zero live calls and zero business effects. Test schema removed.
- Final Node/widget/platform suite: 79 passed, zero failed.

Final stable-tree Python integration: **778 tests and 797 subtests passed**, zero failures (115.98 seconds). This included the configured real local PostgreSQL paths, platform/service/case/model/bridge/analysis/E2E/communications suites, v1 contracts, team handoff and export/cloud-smoke tests. Command:

```sh
PROOFKEY_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:63119/proofkey \
PYTHONPATH=.:tools:runtime/src:runtime/tests \
/tmp/proofkey-postgres-tests-20261010/bin/python -m pytest --import-mode=importlib \
  tools/dwelly_platform/tests tools/dwelly_service/tests tools/dwelly_cases/tests \
  tools/dwelly_model/tests tools/dwelly_bridge/tests tools/dwelly_analysis/tests \
  tools/dwelly_e2e/tests tools/dwelly_channels/tests contracts/v1 \
  datasets/team-handoff-v1/tests tests/test_dataset_export.py tests/test_cloud_case_smoke.py -q
```

The additional full legacy runtime sweep was still running when the owner explicitly requested immediate merge. It is **not a completed verification or a merge gate**; no full-runtime success is claimed. The relevant backend, frontend, selected-source and browser integration checks above are complete. Live LLM quality validation is still separate. Earlier runs during integration are not counted as final: one loaded pre-fix export code and failed the old count; another was interrupted when replaced by the stable-tree run.

## Decisions

Disjoint widget and Python work ran in parallel, with only the coordinator committing. Team sources are namespaced rather than replacing legacy fixtures. Empty copied-recipient lists remain valid according to the published schema. Incoming CC is evidence, never authority. Browser QA samples first/last team states to remain below the local 256-run store; Python checks every cutoff. No production deployment, credentials change, paid provider call or logistics action was performed.
