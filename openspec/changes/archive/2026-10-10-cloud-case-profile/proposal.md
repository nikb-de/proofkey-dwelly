# Explicit cloud case-service profile

## Why
The user authorizes deployment to `genaide`, London `europe-west2`, with an infrastructure budget of GBP 200 per month. The existing service intentionally rejects Cloud Run. Credential refresh currently fails, so deployment remains blocked; local preparation must not be called a deployment.

## What Changes
- Introduce an explicit, opt-in `cloud-run-case-v1` profile for the case-only service and its migration command.
- Keep legacy model/worker managed-cloud guards unchanged.
- Support exact no-port Cloud Run host authorities without allowing arbitrary hosts or browser access.
- Prepare private IAM-only service/migration templates, distinct secret references, bounded scaling and a release checklist.
- No resource creation while credentials fail or resource sizing is unverified.

## Capabilities
### New Capabilities
- `cloud-case-profile`: opt-in cloud-compatible case API configuration, not a claim of deployed operation.

## Impact
Small case API configuration change and tests; cloud release templates/documentation. No model pipeline or real integration is activated.
