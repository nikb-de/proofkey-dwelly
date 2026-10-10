# PostgreSQL deployment verification — 2026-10-10

## Observed result

The final dedicated case API image, rebuilt after the final PostgreSQL logging fix and addition of the dataset exporter, ran against real PostgreSQL 17.11 in Docker on this host. Fresh HTTP smoke and the same smoke after API restart and database/API restart each passed all 15 checks (45 checks on the final image). These checks used synthetic case `smoke-final-frozen-20261010`. Its revision-zero and revision-one snapshots, exact retry responses and two pending analysis intents survived both restart paths. Earlier image checks used `smoke-compose-20261010` and `smoke-compose-final-20261010`; those synthetic cases remain preserved too. All five service/migration source hashes stayed unchanged during the final run and matched the running image afterward.

This verifies the local Linux ARM64 deployment only. It does not verify Linux AMD64 execution, Cloud SQL, Cloud Run ingress, real customer data, a model worker, provider calls or business effects. No cloud resources or provider calls were made. The existing SQLite service and unrelated containers were not changed.

## Environment and artifacts

- Docker client/server: 28.3.2; Docker Compose: v2.38.2-desktop.1.
- Container platform: `linux/arm64`; host test interpreter: system Python 3.
- Database: PostgreSQL 17.11, Debian 17.11-1.pgdg12+2, aarch64.
- PostgreSQL image: `postgres:17.11-bookworm@sha256:639ab7ceb90e13123085b741fb31ef493fba25463002f6da665352e7b534b652`.
- Python base: `python:3.12.15-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1`.
- Final built API image: `proofkey-case-api:local`, manifest `sha256:08de13c2475bc7327d9bf2012db9bd57971db160d8f4899b89d46be3353ab68f`.
- Hash-verified dependency install: psycopg 3.3.6, psycopg-binary 3.3.6, psycopg-pool 3.3.3, typing-extensions 4.16.0.
- Compose project: `proofkey-case-verify-20261010`.
- Host API: `http://127.0.0.1:18082`; PostgreSQL has no published host port.
- Persistent volume: `proofkey-case-verify-20261010_case-postgres-data`.

The final built image contains `tools.dwelly_service.case_api`, `postgres` and `dataset_export`; an import-spec probe confirmed `tools.dwelly_service.worker`, `tools.dwelly_service.server` and `tools.dwelly_model` are absent. `docker run --rm --entrypoint python proofkey-case-api:local -m tools.dwelly_service.dataset_export --help` exited zero and listed the required explicit revision, expected hash, provenance and cutoff options. The final incremental Docker context was approximately 12 KB. The image runs as UID/GID 10002, with a read-only root filesystem and dropped Linux capabilities under Compose.

Direct SHA-256 checks before and after the final smoke confirmed these workspace files remained unchanged and match the running image:

| Source under `tools/dwelly_service/` | SHA-256 |
| --- | --- |
| `postgres.py` | `096ffca3ae173ac209f844f91d37bd96539ef2aebdf6002438a38bca3962bf74` |
| `case_api.py` | `82b4436883013761af7baf55e9088aacf40085f3d67234c317cbe6454fda8bca` |
| `cases.py` | `8fc13611a8379a0246a67018aab76b70c269b1237f39aac415d6ec7a69d328bd` |
| `dataset_export.py` | `76039efb01aa7d00c95fc9b583f453d62b52df158f07e508be71023aecfc2c49` |
| `migrations/001_case_backend.sql` | `8b073386376b5cd55f514cdf217eaa66d00c7e236f1189b8e7ef9e991f91b8b2` |

## Commands and checks

`docker build -f Dockerfile.case-api -t proofkey-case-api:local .` exited zero. The install used `--require-hashes`. `docker compose -f compose.postgres.yaml config --quiet` passed with non-secret validation placeholders, including a nondefault host port. `python3 -m py_compile deploy/postgres/smoke.py`, the hash-locked dependency audit and `git diff --check` passed.

An isolated private environment file was generated with fresh local test credentials, mode 0600, and passed through Compose's `--env-file`. No credential values were printed or committed. Its host path is:

`/var/folders/z3/7xw9ny8s7nl3hg_zdw7_8_5r0000gn/T/proofkey-case-compose-uei0l6ng/local.env`

The full command prefix was:

```sh
docker compose --project-name proofkey-case-verify-20261010 \
  --env-file /var/folders/z3/7xw9ny8s7nl3hg_zdw7_8_5r0000gn/T/proofkey-case-compose-uei0l6ng/local.env \
  -f compose.postgres.yaml
```

| Operation | Result |
| --- | --- |
| `up -d --force-recreate --wait --wait-timeout 60 api` | Exit 0; final image deployed; database healthy; explicit migration exit 0; API healthy |
| `smoke.py --base-url http://127.0.0.1:18082 --case-id smoke-final-frozen-20261010` | 15/15; initial create and append HTTP 201 |
| `restart api`, wait healthy, same smoke with `--expect-existing` | 15/15; both exact retries HTTP 200; history and outbox unchanged |
| `restart postgres api`, wait healthy, same smoke with `--expect-existing` | 15/15; both exact retries HTTP 200; history and outbox unchanged |

Each smoke covers unauthenticated liveness/readiness, authenticated capabilities, create, empty revision zero, exact create retry, append, previous-hash chaining, exact append retry, frozen historical read, latest read, outbox identity/effects, two pending statuses, revision set and snapshot hashes. The script reads its token from the environment and prints only result metadata.

## Retained state and limits

At handoff, the isolated API and database remain running and healthy; the migration container is exited successfully. The private environment file and named database volume are retained for reproducibility. No volumes or case records were deleted. Stop the stack with the command prefix above plus `stop`; retain the private file and volume for later restart. The temporary credentials file may not survive host cleanup, so move it into a private secret store before relying on this test stack long term.

The guide in `deploy/postgres/README.md` includes future Cloud SQL connection and pool-budget considerations with links to Google's documentation. It supplies no cloud deployment manifest or provisioning command. The case CLI still explicitly refuses managed Cloud Run environment markers. Pending outbox rows are not completed analysis, and this deployment does not make the legacy benchmark worker cloud-safe.
