# Private case API release

These templates prepare the case-storage API for `genaide` in `europe-west2`. The approved infrastructure budget is **GBP 200/month**. A template, successful local tests, or a built image does not establish a deployed service, IAM enforcement, Cloud SQL connectivity, least-privilege database grants, recovery, or cost compliance. The release coordinator owns the live inventory and acceptance record; this document records the reusable configuration and local checks.

The API stores immutable case revisions and pending analysis intents. It has no running model worker, media processor, UI/BFF, or operational adapter. `managed_cloud_enabled: true` means that the explicit `cloud-run-case-v1` profile is selected, not that a cloud deployment or worker has been verified.

The first private case pilot was subsequently deployed and verified. Its exact live results, accepted revision and limitations are in the [10 October cloud receipt](../../docs/verification/cloud-case-pilot-2026-10-10.md). The instructions below remain the reusable release procedure; they are not all claims of completed testing.

## Render the configuration

Use [`case-service.template.yaml`](case-service.template.yaml) and [`case-migration.template.yaml`](case-migration.template.yaml) with the image built from [`Dockerfile.case-api`](../../Dockerfile.case-api). Keep rendered copies outside the repository. The `REPLACE_*` values are deliberately invalid deployment inputs; reject any remaining placeholder before applying a rendered file.

| Value | Required choice |
| --- | --- |
| Project and region | `genaide` and `europe-west2`; resolve and verify the project number. |
| Image | The same reviewed Linux `amd64` image for both entrypoints, using an Artifact Registry `@sha256:` digest with exactly 64 lowercase hexadecimal digits. No tag-only image reference. |
| Revisions and traffic | A unique candidate revision name prefixed by the service name, and the observed accepted revision for updates; retain accepted traffic at 100% and tag the candidate at 0%. |
| Runtime identity | Dedicated service account in `genaide`; only runtime DSN and app-token secret access, plus required Cloud SQL connection permission. |
| Migration identity | A different service account and database role; only migration DSN secret access, plus required Cloud SQL connection permission. |
| Secret versions | Positive numeric Secret Manager versions, never `latest`; runtime and migration DSNs must be different secrets and database credentials. |
| Application token | Independent random secret containing at least 32 printable ASCII characters, excluding whitespace; supplied only to the runtime through its version-pinned secret. |
| Database schema | One reviewed schema shared by both entrypoints; keep the runtime database role unable to create schemas or alter tables. |
| Cloud SQL attachment | The observed `genaide:europe-west2:INSTANCE` connection name, identical in both templates and in both private DSNs. |
| Allowed hosts | Initially `localhost:8080,127.0.0.1:8080`; later add only the observed service and candidate-tag DNS authorities, with no scheme, path, whitespace or wildcard. |

The runtime template has min instances `0`, max instances `1` at service and revision scope, HTTP concurrency `8`, a four-connection process pool, one CPU and `512Mi` memory. The migration is one task, parallelism one, zero retries, a 600-second timeout, one CPU and `512Mi`; it does not receive the application token and opens a direct migration connection. Both explicitly select the case profile. Cloud Run's service/job YAML fields are documented in the [Cloud Run YAML reference](https://docs.cloud.google.com/run/docs/reference/yaml/v1).

`ingress: all` allows the gateway to be reached by approved callers; it does not grant invocation. The template explicitly leaves the Cloud Run invoker IAM check enabled. Separately verify the effective service policy contains only approved invokers and no `allUsers` or `allAuthenticatedUsers` grant. Do not use an unauthenticated deployment flag. [Invoker IAM configuration](https://docs.cloud.google.com/run/docs/authenticating/public).

The service template is an **update** shape: its explicit `spec.traffic` pins 100% to `REPLACE_ACCEPTED_REVISION` and gives the new `REPLACE_CANDIDATE_REVISION` the `candidate` tag with 0%. Resolve the accepted revision from the live service and preserve its traffic while testing the tag URL. Do not omit `spec.traffic` or substitute `latestRevision: true` for the accepted revision: that can move the default route to an unqualified candidate.

For **first creation only**, first confirm that the service does not exist. There is no accepted revision to pin. Keep the runtime allowlist restricted to `localhost:8080,127.0.0.1:8080`, retain private IAM, and replace the entire traffic block in the private rendered copy with:

```yaml
traffic:
  - revisionName: REPLACE_CANDIDATE_REVISION
    percent: 100
    tag: candidate
```

This first bootstrap has no preceding production traffic; its application rejects external hosts until the observed hostname is explicitly configured. Every later update must use the accepted-revision 100% / candidate 0% shape. Before moving traffic after acceptance, inspect and name the exact tested revision; do not implicitly route to whichever revision becomes latest. [Cloud Run traffic and revision routing](https://docs.cloud.google.com/run/docs/rollouts-rollbacks-traffic-migration).

## Database credentials and socket

Each DSN secret contains libpq connection settings for its own database role and the socket directory `/cloudsql/genaide:europe-west2:INSTANCE`. The Python driver adds the PostgreSQL socket filename. The complete socket path must fit the platform length limit. The attachment uses Cloud Run's built-in Cloud SQL connection support; the image does not include a separate Python connector or refresh IAM database tokens. Verify the instance network and certificate configuration for this connection method before release. [Cloud SQL Unix socket connection guide](https://docs.cloud.google.com/sql/docs/postgres/connect-run).

The runtime identity needs Cloud SQL connection permission and access to only its two secrets. Its database role needs schema usage, migration-version reads, and the table operations used by case creation, append and read. It must not own the schema, run migrations, create tables, or inherit the migration role. The migration identity needs only its migration secret and the privileges required by the shipped migration. Verify these permissions with the actual runtime credentials; separate secret names alone do not prove privilege separation.

Do not print DSNs, tokens, rendered secret values, authorization headers, or connection exceptions. Secret values belong in Secret Manager, not image layers, YAML literals, command-line arguments, or receipts. The template references numeric versions so a release does not silently follow secret rotation. [Cloud Run secret version guidance](https://docs.cloud.google.com/run/docs/configuring/jobs/secrets).

## Release and acceptance gates

1. Verify the intended project, active billing, APIs and existing Cloud SQL/Cloud Run/Artifact Registry inventory. Record the chosen database tier, storage limit, backup policy, registry retention and current regional estimate. Keep headroom below GBP 200/month. Instance limits and budget alerts are not hard spending caps.
2. Inspect the exact Linux `amd64` image and entrypoint, record its immutable registry digest, and retain the prior accepted image for rollback. The service and migration must use that same digest.
3. Render and review the two manifests. Check distinct identities and DSNs, numeric secret versions, socket name, schema, bounded settings, enabled IAM checks and exact hosts. Use the explicit update or first-creation traffic shape above. For an existing service, pin the observed accepted revision at 100% and test the candidate at its 0% tag URL. For a first service, a loopback-only allowlist rejects external application requests while its TCP startup probe can succeed.
4. Create/update the migration definition separately from execution. Execute it once as the migration identity, verify successful exit and schema version, then test that runtime credentials cannot perform DDL. A failed or interrupted migration requires inspection before another explicitly chosen execution; zero task retries prevents automatic reattempts. [Cloud Run job execution](https://docs.cloud.google.com/run/docs/execute/jobs).
5. Start the private candidate, discover its actual service/tag URL, and render its exact hostname into `PROOFKEY_ALLOWED_HOSTS`. No-port and `:443` entries are different; add only the authority observed in real requests. Keep the literal loopback health entries. A TCP startup or internal `/healthz` success is not a database or application acceptance test. **Do not use external `/healthz` for Cloud Run acceptance**: Google reserves some paths ending in `z` and can return an edge 404 before the container. The cloud smoke uses authenticated `/v1/capabilities` and actual case routes. [Reserved URL paths](https://docs.cloud.google.com/run/docs/known-issues#reserved_url_paths).
6. Verify both authorization layers through the real HTTPS route. Send a Google ID token with the service URL as audience in `X-Serverless-Authorization`, and the independent application token in `Authorization`. Confirm unauthenticated and wrong-identity requests are denied at the gateway; missing/wrong app token, duplicate app authorization and any `Origin` are denied by the application. The app must never treat a caller-supplied identity header as verified identity. [Two-header authentication](https://docs.cloud.google.com/run/docs/authenticating/service-to-service).
7. Use synthetic cases to check create, append, exact retries, immutable revision history, pending outbox state and restart persistence. Confirm no model calls or operational effects. Repeat negative Host and Origin checks, verify content-free logs, and exercise database interruption/recovery and revision rollback before full production qualification. The local [`smoke.py`](../postgres/smoke.py) is loopback-only; use the separate [`smoke_case.py`](smoke_case.py) for the explicitly approved HTTPS pilot. Its `--expect-existing` flag checks replay after deployment. The pilot completed revision rollback, not database interruption or backup restoration.
8. Retain a redacted receipt with service/revision, image digest, region, identities and secret version numbers, database schema version, actual test results, cost estimate, backup/restore evidence and unresolved limits. A rollback routes to a prior compatible revision; do not drop tables or assume a code rollback reverses a schema migration.

Count database connections across overlapping revisions and any administrative or migration connections. Four connections times one process times the intended instance limit is a steady-state planning input, not a global database quota. Transient rollout overlap and platform behavior require headroom. Database storage growth, backups, egress, registry storage and other project resources also count toward the approved budget.

## Local verification on 10 October 2026

The profile was developed red-first: 19 test methods initially produced 66 failing subcases with zero test errors. After implementation, all 19 passed against disposable PostgreSQL and real HTTP. An independent read-only review reran them: 19 methods and 93 subtests passed with no findings. The complete service suite passed 106 tests, including existing model-worker and local-host guards. Related source suites passed 74 model tests, 58 case tests and 82 bridge tests; 30 optional runtime bridge tests were explicitly skipped because that runtime environment was not selected.

The service suite command was:

```sh
PROOFKEY_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:63119/proofkey \
  /tmp/proofkey-postgres-tests-20261010/bin/python -B -m unittest discover \
  -s tools/dwelly_service/tests -p 'test_*.py' -v
```

The synthetic database and test-only credentials in that command are local verification inputs. They are not Cloud SQL settings. Local profile tests verify the marker matrix, exact hosts, token bounds, loopback probes, retained authorization and pending case behavior; they do not establish live Cloud Run acceptance. Cloud operations and resulting deployment status belong in the coordinator's live release receipt.

Both YAML templates passed a duplicate-key-rejecting parse and an in-memory render with synthetic replacement values. The checks covered no unresolved manifest values, explicit accepted-revision 100% / candidate 0% update traffic, same digest-pinned image, numeric secret versions, distinct service accounts and DSN secrets, no application token in the migration, matching socket attachments, entrypoints, profile, exact hosts, resource bounds and health probes. This was structural local validation, not Cloud Run API validation. Independent review identified the missing traffic block in the first draft; the final template includes it and documents a separate first-creation path.

The locally built `proofkey-case-api:cloud-candidate` image was independently inspected as `linux/amd64`; its local image ID was `sha256:9e53394d896b6db76e61597d973b91afc851c705f61639ae1682a3500e1f032e`. Running Python in that image successfully imported the case API. Its `/app/tools/dwelly_service/case_api.py` SHA-256 matched the checkout: `8e9f7815b9a919b6d51cf89c0aaec3dba9161f6f28ed70d8ae56ed0f77f69d5f`. A local image ID is not a registry manifest digest; resolve and record the registry digest after publication before rendering the release manifests.
