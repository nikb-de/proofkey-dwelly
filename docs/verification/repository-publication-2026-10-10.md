# Repository publication verification — 10 October 2026

## Published scope

Branch: `codex/proofkey-main-integration`. The publication includes the pending product/coordination commits, the clean mobile showcase and its two 40-second films, original model/case receipts, provider-envelope correction, tests and archived specifications. The publication inventory is in [PUBLICATION.md](../demos/2026-10-10-case-001-terms/PUBLICATION.md).

No merge into `main`, deployment or new model call is part of this publication. Local intermediate/rejected media and runtime state are not included. Historical failures in the selected evaluation evidence remain visible.

## Completed checks

- Current backend/model/analysis suites: **390 passed, 384 subtests passed**, with local PostgreSQL enabled; zero failures or skips.
- UI suite with Chrome/browser checks enabled: **100 passed**, zero failures or skips.
- Independent replay-integrity review: no remaining actionable findings in the reviewed scope. New rejection regressions were observed failing before implementation, then passing.
- Both presentation bundles rebuild byte-for-byte from the original successful capture reports after the validator hardening.
- Both films fully decode and retain the published SHA-256 values; each has 1,200 frames, 30 fps, 1080×1920, and exactly 40 seconds.
- Selected changes and the four pending commits were scanned for credential patterns; no matching live credential was found. This is not a claim of exhaustive secret detection.
- `git diff --cached --check` passed. Media and raw EML have binary attributes so source bytes and CRLF are preserved.

Backend command:

```sh
PROOFKEY_TEST_DATABASE_URL='<disposable local PostgreSQL DSN>' \
PYTHONPATH=.:tools:runtime/src python -m pytest --import-mode=importlib -q \
  tools/dwelly_platform/tests tools/dwelly_model/tests tools/dwelly_analysis/tests
```

UI command (set the installed Playwright module and Chrome paths for your machine):

```sh
PROOFKEY_CUSTOMER_BROWSER=1 PROOFKEY_CUSTOMER_URL=http://127.0.0.1:8111 \
node --test --test-concurrency=1 --test-timeout=90000 platform-ui/tests/*.test.mjs
```

## Broader runtime audit is not complete

The repository-wide four-worker run was interrupted after **1,046 passed, 1,100 subtests passed and two failures**:

- `runtime/tests/test_host_admission.py::HostAdmissionTests::test_fresh_case_seals_full_actual_route_before_atomic_debt_import`
- `runtime/tests/test_host_admission.py::HostAdmissionTests::test_goods_case_uses_same_seal_protocol`

An immediate sequential run of those exact two tests passed (**2 passed in 15.93 seconds**). The runtime source, tests and fixtures have no changes relative to the publication's starting HEAD. Inspection found a five-second real-time admission-control deadline that can explain the failure under load, but the original exception was not captured, so this is a probable timing explanation, not a proven fix. Runtime production code was not changed to suppress it.

A follow-up broader run excluding that file was also stopped before completion to keep this publication bounded. Neither interrupted run is represented as a full-suite pass. The full historical runtime remains a separate validation task; the completed checks above cover the changed product, provider and presentation modules.

To reproduce the broader audit:

```sh
PROOFKEY_TEST_DATABASE_URL='<disposable local PostgreSQL DSN>' \
PYTHONPATH=.:tools:runtime/src:runtime/tests \
python -m pytest --import-mode=importlib -n 4 --dist loadfile -q
```

The optional parallel runner needs `pytest-xdist`. For deadline-sensitive failures, repeat their exact node IDs sequentially before classifying them as regressions. These local checks do not establish production readiness, current provider quality or real carrier execution.
