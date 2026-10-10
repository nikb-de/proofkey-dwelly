# PostgreSQL backend integration receipt

Date: 2026-10-10. Base commit: `db01cad`. Scope: local PostgreSQL case API, transactional outbox, pinned model-input extraction and their compatibility with the existing source packages. No provider call, fine-tuning run, cloud deployment or real operational action was made.

## Final related-source regression

```sh
PROOFKEY_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:63119/proofkey \
PYTHONPATH=tools:runtime/src:runtime/tests \
/tmp/proofkey-postgres-tests-20261010/bin/python -m pytest --import-mode=importlib \
  tools/dwelly_service/tests tools/dwelly_cases/tests tools/dwelly_model/tests \
  tools/dwelly_bridge/tests contracts/v1 datasets/team-handoff-v1/tests \
  tests/test_dataset_export.py -q --durations=5
```

Observed: **375 passed, 487 subtests passed, zero skipped, 41.94 seconds**. The test database is a disposable local PostgreSQL instance; the URL contains no private credentials. Tests isolate their own schemas. Coverage includes existing service/importer/model/bridge tests, the canonical contracts and team dataset validator, new PostgreSQL HTTP/storage tests and all 11 exporter tests. The model tests do not constitute a paid-provider or semantic-quality assessment.

`python3 datasets/team-handoff-v1/scripts/validate.py` separately passed: 9 inputs, 9 labels, 3 episodes, 0 transitions, all 9 rows assistant-authored drafts and **0 human-reviewed eligible rows**. `git diff --exit-code -- contracts/v1/schemas datasets/team-handoff-v1` returned zero: their tracked files are unchanged. The dataset is structurally valid, not certified ground truth.

## Earlier commands and limits

An earlier related-source command without `tools` on `PYTHONPATH` produced 344 passes, 30 skips and one failure: a spawned process could not import `dwelly_bridge`. Adding the declared source paths fixed that environment error; the final command above has no skips or failures. No application change was made to mask it.

A broader command also including all `runtime/tests` was interrupted after 859 passes and that same import failure (264.29 seconds). It is **not a completed full-runtime regression**. Bare repository-root collection is also unsuitable here because archived repositories under `outputs/` duplicate test names. Neither run is reported as green.

Independent review found a P2 database-log disclosure path. It was reproduced with fake values, fixed with early connection validation and scoped log redaction, and independently retested. See [review](postgres-independent-review.md) and [store evidence](postgres-store-report.md).

The final image/restart/source-hash receipt is maintained separately in [deployment verification](postgres-deploy-report.md). It verifies local Linux ARM64 Docker, not Cloud SQL, AMD64 or production ingress. The [export receipt](postgres-export-report.md) documents pinned-revision byte parity and the absence of trusted observation timestamps.

## Handoff boundary

- Dataset authors keep the existing JSON/JSONL and label contracts.
- Backend-dependent tooling uses pinned revision/hash extraction and real PostgreSQL integration tests.
- Connecting the revision worker, recording complete model-run provenance, labelled bulk export, media storage and the UI BFF remain separate work.
- The existing SQLite benchmark stays local-only. No automatic data migration occurred.
