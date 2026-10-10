# Product case showcase implementation plan

> **For agentic workers:** Use Superpowers TDD and parallel independent implementation. User has requested autonomous execution and a substantially more polished hackathon presentation.

**Goal:** Show the source case as a coherent customer/operator product experience, not a diagnostic console.

**Architecture:** Read-only replay bundles derived from captured backend/model receipts; dedicated static player on the existing platform; no mutation or new provider spend.

**Tech stack:** Python data validation, vanilla JavaScript/CSS, local fonts, Playwright, FFmpeg.

**Spec:** `openspec/specs/product-case-showcase/spec.md`; design archived in `openspec/changes/archive/2026-10-10-product-case-showcase/design.md`.

## Constraints and review focus

- Five scenes and English UI. Clearly distinguish scripted reference and recorded real LLM.
- Preserve changed delivery window and handover requirements; do not invent a price currency.
- Earlier scenes must not display later model advice or final receipts.
- Confirmation is a local sandbox booking, not completed delivery or an external carrier action.
- Navigation/acceptance is playback, not authenticated consent; unexpected data must fail closed.
- Mobile layout at 390px and desktop at 1440px; keyboard controls; reduced motion support.

## Task 1 — Evidence bundle

Files: `tools/dwelly_platform/showcase.py`, `tools/dwelly_platform/tests/test_showcase.py`.

- [x] Write failing tests for cutoffs, source/model binding, distinct synthetic/model modes and final receipt.
- [x] Run the targeted pytest suite, observe RED; implement extraction; run GREEN.
- [x] Generate `platform-ui/showcase-data-{synthetic,llm}.json` using the two successful capture reports.

## Task 2 — Product scenes

Files: `platform-ui/showcase.{html,css,js}`, `platform-ui/tests/showcase.test.mjs`.

- [x] Write failing tests for validation, scene progression and changed terms.
- [x] Implement the branded responsive player: request, review, changed offer, consent, confirmation.
- [x] Keep source/model details accessible in a drawer; label replay and sandbox persistently.
- [x] Run tests and visually inspect every scene at mobile and desktop widths.

## Task 3 — Platform and capture

Files: `tools/dwelly_platform/server.py`, `tools/dwelly_platform/tests/test_product_routes.py`, `docs/demos/2026-10-10-case-001-terms/`.

- [x] Add failing route tests: showcase files served with CSP and no-store, arbitrary paths remain 404.
- [x] Extend explicit allowlist only; serve the player and generated data.
- [x] Browser-test both modes, five scenes, next/back/play, zero POSTs, no page errors or overflow.
- [x] Record 50-second mobile videos, inspect representative frames, decode and probe both files.
- [x] Run platform Python and UI regressions; archive living spec. No publish or push was performed.

## Execution notes

Existing isolated branch `codex/proofkey-main-integration` is reused. Unrelated dirty provider work and previous recordings are preserved. The new presentation is explicitly a replay because reusing completed model calls as if they were live would misrepresent execution.

Completed verification: 380 Python tests and 371 subtests; 94 browser/UI tests; five scenes at three viewports; both MP4s full-decoded at 50 seconds and 1,500 frames. Evidence and export hashes are in `docs/demos/2026-10-10-case-001-terms/showcase-final-20261010/`.
