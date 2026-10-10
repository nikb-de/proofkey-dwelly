# Explicit cloud profile design

## Scope
Only the stateless case API and explicit SQL migration command are eligible. Default profile is `local`; opt-in value is `cloud-run-case-v1`, read from `PROOFKEY_DEPLOYMENT_PROFILE`. Unknown values fail closed. Existing model/server/worker guards stay intact. The cloud profile is a supported configuration, not proof of IAM, database role permissions or deployment correctness.

## API and configuration
Add `deployment_profile='local'` to `create_case_server`. In local mode, keep current K_SERVICE/CLOUD_RUN_JOB rejection and explicit host:port rules. In cloud mode, server construction permits K_SERVICE but rejects CLOUD_RUN_JOB; the CLI migration command permits CLOUD_RUN_JOB but not K_SERVICE. A non-managed local simulation of the profile is allowed for tests.

Cloud serve defaults to `0.0.0.0`; migration does not bind. Require an explicit nonempty `allowed_hosts` list and at least 32 printable ASCII characters in the application token for cloud serve. Exact hostnames without ports may be admitted only in the cloud profile. No wildcard, whitespace, path, empty label, userinfo, IPv6 literal or out-of-range port. Preserve literal loopback authorities for container health checks. No-port and :443 are distinct allowlist entries; do not normalize them into one another.

All application routes still require the application bearer token; Origin remains rejected. Cloud Run IAM is an independent gateway requirement: callers use a Google ID token in X-Serverless-Authorization and the application token in Authorization. Do not trust an unverified user-supplied identity header. Capability output reports the selected profile; its name must not assert a verified deployment or worker availability.

## Release design
Prepare private service and migration-job templates using digest-pinned Linux AMD64 images. Separate migration/runtime service identities and version-pinned DSN secrets; only runtime receives the application token. Keep min instances 0, max instances 1, pool max 4, HTTP concurrency 8, 1 CPU, 512 MiB memory. A maximum-instance setting is a scaling bound, not a hard cost guarantee. Resource sizing/Cloud SQL selection requires successful inventory and a documented budget estimate before creation.

For an existing service, keep its accepted revision at 100% and the new tagged candidate at 0%. For first creation only, after verifying that no service exists, a private bootstrap revision may have 100% traffic with only loopback Host allowed: TCP startup can succeed but external application requests fail closed. Discover the actual candidate/default service URL, explicitly configure only those hostnames, then verify unauthenticated rejection and authenticated synthetic behavior before promoting the candidate. Do not grant allUsers/allAuthenticatedUsers. Do not migrate with the runtime DSN. Existing SQLite data is not transferred.

The initial credentials failed with invalid_grant. After the user completed login, fresh inventory and billing checks succeeded, the project/region and £200/month budget were confirmed, and scoped resource provisioning was authorized. No credential failure was bypassed. The desired complete product remains blocked by missing UI/worker/media/native integrations; this release is case-storage API only.

## Verification
Test local defaults unchanged, opt-in marker matrix, exact cloud host parsing, missing host/token failures, Origin/auth denial, bound host defaults and profile capabilities. Existing service and related-source regression must pass. Validate manifests mechanically and build the Linux AMD64 image locally; neither proves live IAM or Cloud SQL connectivity.
