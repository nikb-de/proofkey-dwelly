# PostgreSQL case API

This local deployment stores versioned `dwelly-local-case-v1` snapshots and pending analysis intents in PostgreSQL. It uses the separate `tools.dwelly_service.case_api` entrypoint. No model worker consumes these intents; case creation and append do not call a provider or authorize customer operations. The existing SQLite benchmark service remains a separate local-only program.

## Start locally

Requirements: Docker Engine with Docker Compose v2 and Python 3 for the host smoke script. Run from the repository root. The PostgreSQL 17.11 image and Python 3.12.15 base are pinned by digest; Python packages are pinned with artifact hashes in `requirements-postgres.lock`. First build may download images and wheels. Use a fresh project name for an isolated installation; reuse that name and the same database password for subsequent starts.

```sh
export COMPOSE_PROJECT_NAME=proofkey-case-local
export PROOFKEY_POSTGRES_PASSWORD="$(openssl rand -hex 32)"
export PROOFKEY_SERVICE_TOKEN="$(openssl rand -hex 32)"
export PROOFKEY_HTTP_PORT=8080
docker compose -f compose.postgres.yaml up --build -d --wait api
```

The password and token above stay in the shell environment. Record them in your private secret store if you need to restart from another shell. Alternatively copy `.env.postgres.example` to a private file outside the checkout, replace both placeholders with different random hexadecimal values, restrict it to your user, and add `--env-file /absolute/private/path` to every Compose command. Load the token separately into the smoke script's environment; `--env-file` is consumed by Compose, not host Python. Avoid printing `docker compose config` or container environment inspection: those expose interpolated credentials. `config --quiet` validates without printing them.

PostgreSQL has no published host port. Only `127.0.0.1:$PROOFKEY_HTTP_PORT` is exposed. Compose derives exact allowed Host authorities for the mapped port and internal health check. The default schema is `public` and each API process has a maximum of four database connections. The named `case-postgres-data` volume persists when services stop.

`migrate` waits for database health, applies the versioned schema explicitly, and exits. The API starts only after migration succeeds. To inspect status without secret values:

```sh
docker compose -f compose.postgres.yaml ps --all
docker compose -f compose.postgres.yaml logs --tail=20 migrate api
```

## Synthetic smoke and restart

The smoke only accepts a loopback HTTP origin and synthetic `smoke-` case IDs. It creates one case and event, verifies exact retries and revision-zero history, and checks both pending analysis intents. It prints no token, DSN or case content. Keep the same case ID across the restart:

```sh
PROOFKEY_SMOKE_CASE="smoke-$(openssl rand -hex 8)"
python3 deploy/postgres/smoke.py \
  --base-url "http://127.0.0.1:$PROOFKEY_HTTP_PORT" --case-id "$PROOFKEY_SMOKE_CASE"
docker compose -f compose.postgres.yaml restart api
# Wait until ps reports the API healthy before the second invocation.
docker compose -f compose.postgres.yaml ps
python3 deploy/postgres/smoke.py \
  --base-url "http://127.0.0.1:$PROOFKEY_HTTP_PORT" \
  --case-id "$PROOFKEY_SMOKE_CASE" --expect-existing
```

Repeat with `restart postgres api` to verify database restart persistence too; wait for both services to report healthy. The script requires 15 checks per pass and leaves its two immutable snapshots and two pending intents in the database. It never removes data. Stop with `docker compose -f compose.postgres.yaml stop`; bring services back with `up -d --wait api`. Do not use volume deletion commands for routine shutdown. Changing `POSTGRES_PASSWORD` after initialization does not change the existing database role's password.

## Direct process configuration

Install `requirements-postgres.lock` with `python -m pip install --require-hashes -r requirements-postgres.lock`. Supply `PROOFKEY_DATABASE_URL` privately using a PostgreSQL connection string. `python -m tools.dwelly_service.case_api migrate` requires database configuration but no API token. `python -m tools.dwelly_service.case_api serve` additionally requires `PROOFKEY_SERVICE_TOKEN`; optional variables are `PROOFKEY_DATABASE_SCHEMA`, `PROOFKEY_DB_POOL_MAX`, `HOST`, `PORT`, and `PROOFKEY_ALLOWED_HOSTS` (comma-separated exact `host:port` authorities). Do not put connection strings or credentials in process arguments.

`/healthz` reports process liveness; `/readyz` checks database availability. `/v1/capabilities`, case creation/append/read and analysis-job metadata require the operator bearer token. Browser Origin requests are rejected. There is no `/v1/jobs` execution endpoint. This token identifies one operator boundary, not multiple users or tenants.

The same image also includes the pinned decision-input exporter. Inspect its required explicit revision, expected snapshot hash and provenance fields with `docker run --rm --entrypoint python proofkey-case-api:local -m tools.dwelly_service.dataset_export --help`. Actual export additionally needs private database configuration and a writable output mount; the API's Compose root filesystem is read-only. Export creates model-visible input only and runs no evaluation or model calls.

## Future Cloud SQL deployment

No cloud resource or deployment is included here. The PostgreSQL schema is the shared target; the local Compose database is not a Cloud SQL test. A future private deployment must choose its project, region, network, database identity and backup/restore plan, then verify the deployed image and database together.

Cloud Run can reach Cloud SQL through its attached Unix socket or a configured private network; an attached Cloud SQL connection requires the service identity's Cloud SQL Client permission. Choose the connection method first and supply its libpq connection string through secret configuration. The present Python image does not install the Cloud SQL Python connector or implement IAM database-token refresh. See Google's [Cloud Run connection guide](https://docs.cloud.google.com/sql/docs/postgres/connect-run).

Budget database connections across all processes and simultaneously running revisions: `pool maximum × process count × maximum instances`, plus migrations and administration. The default pool maximum of four is per process, not a shared quota. Retain headroom and check the selected instance's limits; Google's [connection-management guide](https://docs.cloud.google.com/sql/docs/postgres/manage-connections) covers pooling and connection lifecycle.

Keep migration credentials separate from the eventual runtime role, which should receive only required table/sequence permissions. Run migration as a release step before routing traffic. Private authenticated ingress, TLS termination, secret delivery, autoscaling limits, health routing, least-privilege grants and backup recovery still need deployment-level verification. No production ingress or cloud manifest is supplied. The transactional outbox records pending work only; external queue workers, provider budget admission and exactly-once effects are outside this increment.
