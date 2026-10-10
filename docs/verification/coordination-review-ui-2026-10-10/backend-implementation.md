# Task 1 — Backend implementation report

Implemented in `tools/dwelly_platform/coordination.py`; tests added in `tools/dwelly_platform/tests/test_coordination_review.py`.

## Behavior

- `coordination_command(case_id, key, body, model_resolver=None)` accepts paired `model_run_id` and `model_review_note` on existing commands except initialization. Local acceptance cannot attach model context.
- Model resolution takes place within the locked transaction after saved-request replay and snapshot/workflow-version checks. Missing/pending/failed jobs and unknown resolver exceptions are sanitized; mismatched case/revision/hash/frozen inputs are rejected. Gold references are prohibited. Generic candidate schema is revalidated locally and selected command evidence must be a subset of candidate evidence. Existing command/actor/freshness checks still determine admissibility; model prose never selects or authorizes a typed command.
- Compact `model_context` records run/input/candidate hashes, source revision/hash and explicit human review note. Notes are nonblank and at most 1000 raw characters; the combined canonical audit must also fit the existing 4096-character limit.
- `record_local_acceptance` requires exact current offer/hash, explicit boolean acknowledgement, awaiting-consent phase and unexpired terms. It atomically appends a labelled simulated customer message and consent audit. Consent revision matches the final audit revision (+2 source revisions), exact replay adds nothing, and fresh duplicate requests are phase-blocked. Simulation provenance declares unauthenticated local preview. External effects stay zero and physical delivery stays unconfirmed.

## Verification

- TDD initial run: 25 failures, 2 passes before implementation, exposing missing callback/command behavior.
- Additional raw-whitespace note-bound test observed failing before its implementation fix.
- Final scoped regression command:

```sh
PYTHONPATH=.:tools:runtime/src:runtime/tests PROOFKEY_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:63119/proofkey /tmp/proofkey-postgres-tests-20261010/bin/python -m pytest --import-mode=importlib tools/dwelly_platform/tests/test_coordination_review.py tools/dwelly_platform/tests/test_coordination.py tools/dwelly_platform/tests/test_coordination_safety.py tools/dwelly_platform/tests/test_coordination_projection.py tools/dwelly_platform/tests/test_coordination_http.py tools/dwelly_platform/tests/test_models.py -q
```

Result: **70 passed, 13 subtests passed** in 14.74 seconds. This includes 31 new review/acceptance cases, real PostgreSQL rollback injection after the synthetic event, exact replay, stale context, source policy and bounded audit checks. `git diff --check` passed for owned files.

Repository-wide pytest was started per TDD instructions, then interrupted at controller request because discovery includes copied historical trees: **79 passed, 127 subtests passed**, no failures observed before interruption. This is not a complete repository-wide result. The controller owns final required platform/analysis/model-root verification and integration/browser review.

## Boundaries

No paid/live provider calls, external messaging, commits, or provider-file edits. This report concerns backend behavior, not authenticated customer identity or physical delivery. Existing dirty provider work and other agents' files were preserved.
