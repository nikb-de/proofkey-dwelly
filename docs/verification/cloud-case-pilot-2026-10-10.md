# Private case-storage pilot — 10 October 2026

## Scope and outcome

The **case-storage API is deployed to Google Cloud and functionally verified using synthetic data**. It is not the complete ProofKey product. Browser integration, media upload/processing, model consumption of the outbox, real integrations and multi-user case authorization remain unconnected.

- Project / region: `genaide` / `europe-west2`.
- Service: `proofkey-case-api`.
- Private API: `https://proofkey-case-api-wlxgug626a-nw.a.run.app`.
- Additional observed origin: `https://proofkey-case-api-156744085541.europe-west2.run.app`.
- Accepted/rollback revision: `proofkey-case-api-00002` at 100%; separately tested fresh revision `proofkey-case-api-00003` remains tagged `candidate` at 0%.
- IAM remains enabled. There are no `allUsers` or `allAuthenticatedUsers` invoker bindings. Only the deploying user's explicit invoker binding is present. The application bearer token is a second, independent requirement.

Final control-plane readback at `2026-10-10T12:17:05Z` confirms `Ready=True` and `RoutesReady=True`, with revision 00002 receiving 100% of default traffic. The transient `AssigningTraffic` state during rollback resolved before handoff.

## Immutable release identity

Image: `europe-west2-docker.pkg.dev/genaide/proofkey/case-api@sha256:9e53394d896b6db76e61597d973b91afc851c705f61639ae1682a3500e1f032e`.

Architecture: Linux AMD64. The image was built, locally imported/executed and independently read back from Artifact Registry. Case API source SHA-256: `8e9f7815b9a919b6d51cf89c0aaec3dba9161f6f28ed70d8ae56ed0f77f69d5f`, based on `3d08cd3` plus the reviewed cloud profile. The model worker is not in this image.

## Live verification

| Check | Observed result |
| --- | --- |
| Explicit Cloud Run migration | `proofkey-case-migrate-6f7q8`: completed successfully, one successful task, zero configured retries |
| Database role isolation | Eight checks passed: runtime identity, non-admin flags, no schema/database CREATE, migration version 1, rejected DDL, DELETE and snapshot UPDATE |
| Candidate revision 00002 | 20 synthetic HTTPS checks passed |
| Default route on revision 00002 | 20 repeat/idempotency checks passed |
| Fresh candidate revision 00003 | 20 repeat/history checks passed; request logs identify revision 00003 |
| Default route after promotion to 00003 | 20 repeat/history checks passed |
| Default route after rollback to 00002 | 20 repeat/history checks passed |
| IAM / application / Origin denials | Each smoke verifies no IAM is denied, missing/wrong app token returns 401, and Origin returns 403 |
| Analysis and operational state | Two pending outbox rows for revisions 0 and 1; no model run, runtime binding, authorization assertion or external effect |

All five smoke runs used the same explicitly synthetic case, `smoke-cloud-20261010`. Replayed writes returned the original immutable results. **100 live assertions are not 100 independent business cases**, and are not a model-quality evaluation.

The source regression command, with real local PostgreSQL, completed with **411 passed and 647 subtests passed**. This includes the 17 offline cloud-smoke tests. It covers the listed related source suites, not the entire repository or production load/security testing:

```sh
PROOFKEY_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:63119/proofkey \
PYTHONPATH=tools:runtime/src:runtime/tests \
/tmp/proofkey-postgres-tests-20261010/bin/python -m pytest --import-mode=importlib \
  tools/dwelly_service/tests tools/dwelly_cases/tests tools/dwelly_model/tests \
  tools/dwelly_bridge/tests contracts/v1 datasets/team-handoff-v1/tests \
  tests/test_dataset_export.py tests/test_cloud_case_smoke.py -q
```

## Storage, secrets and cost

Cloud SQL instance `proofkey-case-pg`: PostgreSQL 17 Enterprise, regional HA, `db-custom-1-3840`, 20 GB SSD, storage auto-growth capped at 50 GB. Cloud SQL connector required, no authorized public networks, deletion protection enabled. It has a public connection address for the authenticated connector; this is **not a private-IP/VPC deployment**.

Seven retained automated backups and seven-day PITR are configured. On-demand backup `1791634467660` completed successfully at `2026-10-10T12:15:58.971Z`, after the synthetic case was written. **No backup restore or HA failover drill was run.** HA configuration is not evidence of a measured recovery time.

Runtime and migration use distinct database roles and service accounts. Secret Manager holds separate runtime/migration DSNs and the application token, all pinned to version 1. Runtime has SELECT plus the required INSERT/UPDATE permissions, not schema ownership, DELETE or snapshot UPDATE. The administrator credential is not attached to either workload.

Cloud Run is bounded to minimum 0 / maximum 1 instance, concurrency 8, one CPU, 512 MiB, pool maximum 4. Temporary revision overlap is included in operational headroom; the scaling limit is not a financial guarantee.

The project-scoped **£200/month alert-only budget** was created and read back: 50%, 90%, 100% current spend and 100% forecast, gross of credits, default billing recipients enabled. The catalog-derived CPU/RAM baseline is approximately £89.21/month at 730 hours, excluding storage, backups, Cloud Run, registry, network and taxes. Cloud SQL incurs charges while idle. Alerts do not enforce a spending cap or prove that an email was delivered.

## Deployment issue resolved

External `/healthz` returned Google HTML 404 before application routing, including from a diagnostic Cloud Run job. Testing only that path initially misdiagnosed the service as unreachable. `/readyz` and actual API routes did reach the application. Google's [reserved URL path limitation](https://docs.cloud.google.com/run/docs/known-issues#reserved_url_paths) explains the conflict. The smoke now uses authenticated `/v1/capabilities`; the internal loopback liveness probe remains unchanged and passed in Cloud Run. No IAM weakening or image change was needed.

## Re-run safely

Use the checked-in [cloud smoke CLI](../../deploy/cloud-run/smoke_case.py) with an explicitly synthetic case ID. Fetch the application token into an environment variable from Secret Manager; do not print it or commit it. The CLI privately obtains the current user's Google ID token and uses separate authentication headers. Use `--expect-existing` when repeating the recorded case after a deployment. It refuses redirects and unrelated target origins/paths.

Opening the service in an ordinary browser is not a UI demo: it requires authenticated invocation and has no connected frontend. No colleague IAM grants were inferred from GitHub usernames.

## Still not established

Complete-product readiness; semantic model quality; connected browser/BFF; media storage or processing; an outbox consumer; real logistics integrations; per-case multi-user authorization; sustained load/penetration testing; backup restore/failover recovery; hard financial capping. Training/eval JSON contracts were not changed by the backend deployment, and no existing SQLite data was migrated.
