# Time-bounded model choice — 10 October 2026

Selected fallback: **Claude Sonnet 5.5, high effort, existing eval baseline prompt**.

This is a conservative retained baseline, **not an eval winner or a production-qualified model**. Partial high scores come from small unflagged subsets and must not be presented as overall accuracy. The benchmark remains running with one shared $75 ledger and at most four in-flight provider calls. Unavailable outputs remain visible as skips, never passes.

## Actual deployment state

Read-only Google Cloud inspection found one London Cloud Run service, `proofkey-case-api`. Traffic remains 100% on revision `proofkey-case-api-00002`; `proofkey-case-api-00003` is a candidate-tag revision. The deployed image is the private case API, not a model worker. `tools/dwelly_model/cloud_guard.py` explicitly rejects live execution under Cloud Run markers.

No cloud deployment, traffic migration, IAM change, secret change or guard bypass was performed. This decision receipt is documentation, **not an automatically consumed runtime configuration**.

## Required before promoting the model

1. Connect a supported model worker to durable cloud admission, budgets and case results without bypassing the managed-cloud guard.
2. Verify the selected prompt/output contract against the platform consumer. The independent eval contract is not assumed to be a drop-in application contract.
3. Run authenticated case-to-model-to-result smoke checks and policy-denial tests on a no-traffic candidate.
4. Promote only after explicit quality/operational acceptance; retain the current revision for rollback.

The current-profile and managed-cloud guard suites passed five local tests during this inspection. These tests do not establish production or full-product readiness.
