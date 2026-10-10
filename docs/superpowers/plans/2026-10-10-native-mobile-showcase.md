# Native Mobile Showcase Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver two source-backed, unmistakably mobile 40-second films.

**Architecture:** Retain the read-only showcase bundles and five-scene controller. Replace presentation chrome and centralize recorder/export timing in a tested module. The UI and recording work run independently, then meet at `window.proofkeyReplay.goTo(index)`.

**Tech Stack:** HTML/CSS/JavaScript, Playwright, Node test runner, ffmpeg.

**Spec:** `openspec/changes/native-mobile-showcase/specs/product-case-showcase/spec.md`

## Global Constraints
- Five scenes, eight seconds each, exactly 40 seconds / 1,200 frames at 30 fps.
- Preserve English content, source terms and separate scripted versus recorded-model identity.
- Minimum 44×44 logical-pixel controls; no clipped primary content.
- No new model calls, case writes, pushes, or source-data changes.
- Preserve unrelated dirty worktree edits.

## Review Focus
- Small viewport: all authoritative terms and CTA remain visible.
- Consent cutoff: future response/confirmation does not leak into earlier scenes.
- Tab navigation: destinations remain semantically distinct from replay steps.
- Timing: encoded duration, not a wall-clock assumption, proves 40 seconds.
- Recording: browser requests remain GET-only and source hashes remain fixed.

## Task 1: Mobile product surface
**Files:** `platform-ui/showcase.{html,css,js}`, `platform-ui/tests/showcase.test.mjs`.
**Interface:** Existing data bundles in; `window.proofkeyReplay.goTo(index)`, `play()`, `pause()` out.
- [x] Add failing geometry, navigation, content-fit and 8-second fake-clock tests; run the test file and retain failure evidence.
- [x] Implement the phone shell, safe areas, app header, cards and bottom destinations. Keep capture chrome separate.
- [x] Run the entire UI suite with browser checks enabled; visually review all ten mode/scene combinations.

## Task 2: Capture and export
**Files:** `record-showcase.mjs`, `export-showcase.mjs`, `showcase-capture-contract.mjs`, `platform-ui/tests/showcase-capture.test.mjs`.
**Interface:** Task 1 controller; immutable capture metadata and verified MP4s out.
- [x] Test `durationSeconds === sceneIds.length * sceneSeconds`, 40 seconds, 1,200 frames, and reject writes/errors/wrong timing before export.
- [x] Add the shared constants/validator and use them in capture/export; drive capture with `?capture=1` and the controller API.
- [x] Record both variants concurrently, end-anchor the cut and assert exact dimensions/rate/frame count/duration, then full decode and inspect midpoint stills.

## Task 3: Handoff
**Files:** `SHOWCASE.md`, OpenSpec change/living spec, unique output directory and Downloads copies.
- [x] Link the new films, label historical LLM replay accurately and mark the 50-second version superseded.
- [x] Independent read-only review, fix any load-bearing findings, archive the OpenSpec change and report actual evidence.

## Rulings
- Continue under the user's existing autonomous execution request; no additional approval cycle.
- The old 50-second files remain recoverable and are not overwritten.
- No commit/push this turn; shared branch changes require their own authorization.
- The initial DPR-only high-resolution capture padded three quarters of the video. Replaced it with a physical 900×1600 viewport and CSS zoom2; decoded probe verified full-frame composition.
- Independent review found declared duration alone did not establish five correctly timed scenes. Added ordered finite scene-mark validation against an eight-second grid (300ms scheduling tolerance) and exact logical/physical geometry.

## Verification receipt
- UI suite: 98 passed, zero failed/skipped; opt-in browser checks enabled.
- Source/route backend suite: 32 passed, 10 subtests passed with PostgreSQL configured.
- Independent review: no remaining blocker; both modes and five scenes inspected with narrow/full capture geometry.
- Both films: 40.000 seconds, 1080×1920, 30fps, 1,200 frames, full decode passed. Capture writes/errors: zero; frozen UI/data hashes unchanged.
- Evidence: `docs/demos/2026-10-10-case-001-terms/mobile-40s-final-20261010/{capture,exports}.json`.
