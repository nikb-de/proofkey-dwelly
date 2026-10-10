# Google Cloud preparation: offline smoke only

This directory prepares a Cloud Run Job for a two-case, offline, proposal-only smoke check. It has not created or deployed a Google Cloud resource. The template does not call model providers, retain its output after the task stops, or run the local HTTP service. A successful cloud smoke would establish only container startup and offline execution on that platform.

The current local runner uses POSIX files for reservations and immutable evidence. Live CLI calls are rejected when `K_SERVICE` or `CLOUD_RUN_JOB` is present. The local HTTP service refuses both managed environments for all modes. Removing those environment markers would bypass a deployment guard; it would not make storage durable or the service supported.

## Prepared template

[`job.template.yaml`](job.template.yaml) uses the CLI image from the root `Dockerfile`, one task, parallelism one, zero failure retries, a ten-minute timeout, one CPU and 512 MiB memory. A 128 MiB memory volume holds temporary output. Its only cloud data mount is a read-only bucket containing the frozen bundle at its root. There are no provider secrets in this offline job.

Cloud Run Jobs run until the process exits and use its exit code. Job failure retries default to three, so the template explicitly sets zero. Task parallelism is scoped to an execution; it is not a campaign-wide admission lock. [Job configuration](https://docs.cloud.google.com/run/docs/create-jobs), [retry configuration](https://docs.cloud.google.com/run/docs/configuring/max-retries).

## Preparation and later approved deployment

1. Choose the project, region, dedicated job service account, Artifact Registry repository and input bucket. The job identity needs read access to the input bucket; it does not need provider keys or write access for this smoke. Keep the frozen bundle immutable to this identity. [Job identity](https://docs.cloud.google.com/run/docs/configuring/jobs/service-identity), [read-only bucket mounts](https://docs.cloud.google.com/run/docs/configuring/jobs/cloud-storage-volume-mounts).
2. Build a Linux `amd64` CLI image and record its digest. Cloud Run requires Linux x86_64; a local Apple Silicon build is not a Cloud Run compatibility check. The base tag in `Dockerfile` is not pinned, so record or pin the base digest as part of a reproducible release. [Container contract](https://docs.cloud.google.com/run/docs/container-contract).
3. Create a private copy of the template outside the repository, replace every `REPLACE_*` value, and pin the image by digest. Review the job settings before deployment. The example mount expects `manifest.json`, `ledger.jsonl` and `agent/` directly at the bucket root; existing bundle checks validate selected snapshots and attachments but do not pin the entire bucket generation.
4. Only after separate deployment authorization, create/update the job. Only after separate execution authorization, start it. The following commands are reference commands, not commands run by this change:

```sh
# Later approved deployment; this does not execute the job.
gcloud run jobs replace /absolute/private/path/proofkey-offline-job.yaml \
  --project REPLACE_PROJECT_ID --region REPLACE_REGION

# Later approved execution; this consumes cloud resources.
gcloud run jobs execute proofkey-offline-smoke \
  --project REPLACE_PROJECT_ID --region REPLACE_REGION --wait
```

Do not add `--execute-now` to a preparation/deployment step. Cloud Run distinguishes job creation from execution. [Execute jobs](https://docs.cloud.google.com/run/docs/execute/jobs).

The worker writes the full offline summary to stdout. Review the job exit status and logs; treat the `/work/offline-smoke` files as disposable. The template has no publisher for those files. Cloud Run's writable filesystem is memory-backed and disappears when the instance stops. [Filesystem and job lifecycle](https://docs.cloud.google.com/run/docs/container-contract).

## Required before any live cloud experiment

- Persist an authenticated, idempotent submission and a unique run claim outside the instance before acknowledging it. Separate executions must not recreate a budget or replay the same provider request. A create-only Cloud Storage object can protect a single run name using `ifGenerationMatch=0`; multi-record budget/admission updates need an atomic transactional design. [GCS preconditions](https://docs.cloud.google.com/storage/docs/request-preconditions).
- Make shared campaign reservations and dispatch identities durable before each provider call. Store outcomes and immutable artifacts continuously, then publish completion only after required writes succeed. A final upload or shutdown handler cannot recover files lost to abrupt termination. Treat unknown provider outcomes as spent; reconcile them without automatic replay. [Checkpoint guidance](https://docs.cloud.google.com/run/docs/jobs-retries).
- Keep SQLite, `flock`, and mutable budget journals off Cloud Storage FUSE. It lacks file locking and full POSIX semantics. Use an external transactional store for job state/budgets and object storage for immutable evidence. [FUSE limitations](https://docs.cloud.google.com/run/docs/configuring/jobs/cloud-storage-volume-mounts).
- Add authenticated Cloud Run admission with least-privilege identities, controlled payload sizes, input-generation/hash pinning, duplicate execution protection and cancellation/restart tests. A response must not leave an untracked in-process thread owning the job. Request-based billing can restrict CPU after the response, and instances can stop. [Background work](https://docs.cloud.google.com/run/docs/tips/general), [container lifecycle](https://docs.cloud.google.com/run/docs/container-contract).
- Put future provider secrets in Secret Manager and grant the worker identity access only to required secrets. Pin secret versions when exposed as environment variables. Use the attached service identity for Google APIs; do not ship a service-account key in the image. [Job secrets](https://docs.cloud.google.com/run/docs/configuring/jobs/secrets), [service identity](https://docs.cloud.google.com/run/docs/securing/service-identity).
- Verify Linux image execution, IAM, storage failure handling, race protection, cancellation, timeout/kill behavior and bounded provider access in the chosen project. Live receipt review and separate human quality review are still required; an offline smoke does not establish them.

The [local service guide](../../docs/model-service.md) describes the implemented single-operator service and the planned cloud architecture. No live cloud worker or durable cloud queue is included here.
