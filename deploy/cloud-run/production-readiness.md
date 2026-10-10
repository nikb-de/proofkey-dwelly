# Private case API: production readiness handoff

Status on 10 October 2026: **private case-storage pilot deployed and verified**. Local baseline is `3d08cd3` plus the reviewed explicit cloud profile. This release is not the complete ProofKey product. The [final cloud receipt](../../docs/verification/cloud-case-pilot-2026-10-10.md) records the image, accepted revision, live checks, backup and limits.

The user confirmed project `genaide`, region `europe-west2` (London), and an infrastructure budget of **£200/month**. That budget is a spending constraint, not evidence that a proposed configuration fits it. Billing alerts are notifications, not a hard spending cap; resource sizing and explicit capacity limits still need review.

## Scope and observed blockers

The pilot may store immutable case revisions, append events and record pending analysis intents through `tools.dwelly_service.case_api`. The model worker, UI/BFF, media processing and real operational adapters are unconnected. Pending analysis does not mean a model ran; API success does not mean a logistics action happened. The separate synthetic runtime source exists in [`runtime/`](../../runtime/README.md), but is not connected to this case API.

The initial preflight failed with `invalid_grant`. After the user completed login, fresh checks confirmed project `genaide` is ACTIVE, billing is enabled, and no Cloud SQL instances, London Cloud Run services or London registry repositories existed. Required APIs were then enabled under the user's deployment authorization. This later successful inventory supersedes the initial unknown state.

The original blockers and their current dispositions are:

- Local mode still rejects managed markers. Explicit `cloud-run-case-v1` permits only the intended case service/migration paths; unsupported model/runtime guards remain intact.
- Cloud mode binds to `0.0.0.0` and consumes the platform port; local mode remains loopback-only.
- Cloud mode validates explicit exact DNS authorities, with and without a port. Host, Origin and application bearer checks remain enforced.
- A Linux `amd64` image was built, imported successfully, pushed by immutable digest and executed on Cloud Run. The live acceptance evidence is recorded separately from local image checks.

The final regression run passed **411 tests and 647 subtests**, with real local PostgreSQL. Five cloud smoke runs passed 100 assertions on one synthetic case, including fresh-revision and rollback checks. Live IAM, application authentication, database connectivity and restricted database-role checks passed. Independent reviews have no open findings. These results do not certify disaster recovery, model quality or complete-product readiness.

## Provisioning decision and spend controls

- Cloud SQL: PostgreSQL 17, Enterprise, regional HA, `db-custom-1-3840`, 20 GB SSD, automatic growth bounded at 50 GB, seven retained backups and seven-day PITR, deletion protection, required Cloud SQL connector and no authorized public networks.
- Cloud Run: private IAM invocation plus a separate application token, minimum zero / maximum one service instance, concurrency eight, one CPU / 512 MiB, database pool maximum four. Rolling-revision overlap still requires connection headroom.
- Separate migration/runtime database roles, service accounts and version-pinned secrets. No provider credentials or model runtime are included.
- Created a project-scoped **£200/month alert-only budget**, gross of credits, at 50%, 90%, 100%, plus 100% forecast. Default billing recipients remain enabled. This does not enforce a spending cap or guarantee email delivery.
- The official GBP catalog returned regional London PostgreSQL CPU at £0.074711489/hour and RAM at £0.012665519/GiB-hour. At 730 hours, one CPU plus 3.75 GiB is approximately **£89.21/month before storage, backups, Cloud Run, registry, network and taxes**. This is an estimate, not an invoice or hard maximum. [Cloud SQL pricing](https://cloud.google.com/sql/pricing).

Source references: [`case_api.py`](../../tools/dwelly_service/case_api.py), [`Dockerfile.case-api`](../../Dockerfile.case-api), [`PostgreSQL deployment guide`](../postgres/README.md). The existing [`Cloud Run Job template`](README.md) is an offline model-harness smoke, not a case-API deployment manifest.

## Completed provisioning gates

1. Login restored, billing/access verified and empty target inventory checked before creation.
2. Configuration selected within the confirmed budget estimate, with bounded compute/storage and an alert-only budget. Model-provider spend is absent from this pilot.
3. IAM-private invocation, separate application authentication, Cloud SQL connector and separate database/service identities verified. This is a public-routable IAM-protected endpoint, not private-IP networking.
4. The deploying user's explicit invocation grant and synthetic data scope were used. No colleague grants, real customer data or real actions were inferred.

## Staged release gates

| Gate | Required work | Exit evidence |
| --- | --- | --- |
| 1. Restore cloud visibility | Reauthenticate; verify access to `genaide` / `europe-west2`, billing, APIs and existing resources through read-only checks. | Successful, redacted inventory and selected resources with current estimates within £200/month. |
| 2. Implement a scoped cloud profile | Add explicit support for the private case API and separate migration entrypoint. Preserve local defaults and denial of unsupported managed model/runtime paths. Specify bind/port, exact Host/proxy handling, request limits, shutdown and health behavior. | Focused tests exercise cloud admission, denied unsupported paths, allowed/denied Host values, probes and shutdown. Both intended entrypoints run under real platform environment markers without bypassing them. |
| 3. Define identities and secrets | Require Cloud Run IAM invocation and application authentication. Resolve header compatibility because the application currently consumes `Authorization` for its bearer token. Use Secret Manager with restricted identities and explicit secret versions; grant Cloud SQL connectivity only where needed. Separate migration and runtime service accounts and database roles. | Unauthenticated and wrong-identity requests fail; an approved caller passes both authentication layers. Runtime role has only required data permissions and cannot run schema changes. Secrets are absent from image, repository and logs. |
| 4. Prepare durable storage and capacity | Select Cloud SQL connection method and schema. The image has no Cloud SQL Python connector or IAM database-token refresh. Set bounded service instances, concurrency and per-process pools. Count overlapping revisions, migration connections and administrative headroom. Define backup retention, restore procedure and recovery objectives. | Connection budget fits the selected database: pool maximum × processes × maximum instances, plus overlap and operational headroom. A restore drill verifies retained data and records measured recovery results. |
| 5. Build and qualify the release | Build the case-API image for Linux `amd64`, record immutable image/base digests, run it against PostgreSQL and review the private deployment configuration. Keep migrations as an explicit release step before traffic. | Target-architecture startup and migration evidence, reviewed configuration, dependency evidence and an identified rollback image. No claim of cloud acceptance from an ARM64 build. |
| 6. Deploy and accept the private pilot | After the preceding gates, provision the approved resources and deploy privately. Run synthetic create/append/read, idempotency, immutable-history, pending-intent and restart checks through the deployed route. Exercise IAM/app-auth denials, database interruption, connection limits, revision rollback and recovery. | Exact deployed revision/image, successful smoke and negative checks, content-free logs, data surviving restart, and verified rollback/restore. A pending intent remains explicitly unprocessed. |

The local [`smoke.py`](../postgres/smoke.py) accepts loopback HTTP origins only. Do not present it as a cloud test or loosen it implicitly; create a reviewed cloud-specific smoke path that preserves synthetic IDs and credential redaction. `/healthz` is process liveness; `/readyz` checks database access. Both remain subject to the current Host policy.

Reviewed deployment templates and the staged workflow are in [case-release.md](case-release.md). The private pilot passed live acceptance. A successful backup was created, but restore/failover drills, sustained load/security tests and full-product integration remain open; the staged gates above describe the broader readiness standard, not an all-green certification.

## Pilot acceptance is not full-product acceptance

Passing these gates qualifies only the private case-storage API and its pending-intent outbox. Connecting UI/BFF, a durable model worker with provider budget admission, media storage/processing, multi-user authorization and live adapters each needs separate design and verification. Neither the pilot nor the synthetic runtime establishes real logistics execution, semantic model quality or production readiness of the complete product.
