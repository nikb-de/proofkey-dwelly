# Production Readiness Visual Implementation Plan

> **For agentic workers:** Use parallel evidence/documentation work; the coordinator owns the architecture asset and verification. Cloud provisioning is separately tracked in `2026-10-10-cloud-case-profile.md` after the user confirmed project, region, budget and completed login.

**Goal:** Show exactly what is ready while exposing the concrete blockers to the requested production deployment.

**Architecture:** One lightweight SVG/PNG separates connected local case storage from disconnected model/runtime components and missing production links. A separate deployment handoff preserves explicit authority, credential and cost gates.

**Tech Stack:** SVG, local Chromium layout checks, Sharp rasterization, Markdown, OpenSpec.

**Spec:** `openspec/changes/archive/2026-10-10-production-readiness-visual/design.md` and `openspec/specs/production-readiness-visual/spec.md`.

## Global Constraints
- This documentation task makes no cloud changes; reflect verified results of the separately authorized release without exposing credentials or implying public access.
- Do not remove or bypass the Cloud Run guard.
- Complete-product status remains blocked; historical test receipts are not new tests. Label any newly accepted case-only deployment separately.
- Preserve untracked `docs/dataset-drafts/`.

## Review Focus
- No solid connection from outbox to a model worker, browser to backend, or simulated adapters to real operations.
- No labels outside component bounds.
- No inference that invalid credentials imply an empty project.
- Runtime source exists but is not connected to case intake.
- Training inputs and labels remain distinct from live runtime authority.

### Task 1: Preflight and handoff
**Owner:** cloud_handoff; read-only audits by cloud_preflight and production_gap_review.
**Files:** `deploy/cloud-run/production-readiness.md`, one stale sentence in `README.md`.
- [x] Run exact read-only identity/project/resource checks and inspect guarded startup.
- [x] Record failures, explicit unknowns and the smallest safe deployment scope; supersede failed-login inventory with fresh checks after reauthentication.

### Task 2: Architecture graphic and QA
**Owner:** coordinator.
**Files:** `docs/architecture/proofkey-readiness-2026-10-10.svg`, `.png`, and verification receipt.
- [x] Add layout/status verification before producing the graphic.
- [x] Draw the source-backed architecture; use fixed node bounds and short wrapped labels.
- [x] Render PNG locally; inspect image and all text bounds.
- [x] Validate/archive OpenSpec and commit only task-owned files.

The production deployment request itself is not complete when this documentation increment completes.
