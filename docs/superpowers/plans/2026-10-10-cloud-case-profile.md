# Cloud Case Profile Implementation Plan

> **For agentic workers:** Use test-driven implementation with disjoint owners; preserve the existing local profile and all model guards.

**Goal:** Make the case-only API deliberately configurable for a private Cloud Run release without implying the release has happened.

**Architecture:** Opt-in profile handles managed marker, bind and exact-host differences; Cloud Run IAM plus the existing app token supplies two authorization layers. PostgreSQL remains external; migration and runtime credentials are separate.

**Tech Stack:** Existing Python service, unittest/pytest, Cloud Run YAML, Docker Buildx.

**Spec:** `openspec/changes/archive/2026-10-10-cloud-case-profile/design.md` and `openspec/specs/cloud-case-profile/spec.md`.

## Global Constraints
- Default local behavior and old worker guards unchanged.
- No cloud mutation while credential refresh fails; no real provider or operational calls. Login was subsequently restored and fresh inventory succeeded before provisioning.
- Confirmed target: genaide/europe-west2; GBP 200/month budget, not an enforceable automatic cutoff.
- Do not touch user-owned dataset drafts or frozen schema/data files.

## Review Focus
- Managed marker without opt-in must still fail before DB access.
- Allowlist must reject wildcards, paths, whitespace, malformed labels and spoofed Origins.
- Secret, image, identity and scaling settings must be explicit.
- A manifest and a built container are not verified cloud identity/connectivity.
- No future model result or real action may be advertised as enabled.

### Task 1: Case API profile (cloud_profile agent)
**Files:** `tools/dwelly_service/case_api.py`, `tools/dwelly_service/tests/test_cloud_case_profile.py`.
**Interface:** `create_case_server(..., deployment_profile='local')`; env `PROOFKEY_DEPLOYMENT_PROFILE=cloud-run-case-v1`.
- [x] Write failures for local-vs-cloud marker matrix, malformed cloud hosts, weak token, Origin/auth and config defaults.
- [x] Implement only the profile differences in the approved design.
- [x] Run focused tests and existing HTTP/service tests; report actual commands.

### Task 2: Private release templates (coordinator)
**Files:** `deploy/cloud-run/case-service.template.yaml`, `case-migration.template.yaml`, `case-release.md`.
- [x] Add private service and zero-retry migration configuration with distinct secrets/identities.
- [x] Validate strict values and locally build the case image for linux/amd64.
- [x] Independently review and run related-source regression before committing.

External deployment is authorized for `genaide/europe-west2` within £200/month. Fresh login, inventory and cost verification passed; private pilot provisioning and acceptance are complete. Live acceptance and rollback are recorded separately in `docs/verification/cloud-case-pilot-2026-10-10.md`; backup restore and HA failover have not been tested.

### Task 3: Authorized private pilot release (coordinator)
- [x] Revalidate login, billing, empty target inventory and current GBP prices.
- [x] Create bounded configuration, separate identities/versioned secrets and a project-scoped £200 alert-only budget.
- [x] Complete Cloud SQL provisioning and restricted database-role bootstrap.
- [x] Execute the separate Cloud Run migration, then grant runtime table permissions without DDL ownership.
- [x] Deploy private case API; verify IAM/application/Origin denials plus synthetic case lifecycle.
- [x] Verify immutable history and idempotency after a fresh service revision; record image, revisions and limitations.
- [x] Update the readiness diagram from observed results; archive completed specification changes.

No synthetic smoke establishes real-customer readiness, human authorization, model quality, a connected UI, or disaster-recovery qualification. Full backup-restore/failover drills remain explicit follow-up work unless actually executed.
