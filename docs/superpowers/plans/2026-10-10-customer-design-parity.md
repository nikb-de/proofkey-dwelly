# Customer design parity implementation plan

> **For agentic workers:** Use superpowers:subagent-driven-development and TDD. The user approved restoring the supplied design and explicitly requested parallel live verification.

**Goal:** Restore the actual approved customer layout without weakening the operational contract.

**Architecture:** Keep CustomerSession and platform APIs; adapt presentation to the source HTML/CSS. Live evaluation is isolated from UI fixtures and keeps existing labels.

**Tech Stack:** Native modules, CSS, Node test runner, Playwright, Python/PostgreSQL platform.

**Spec:** `openspec/specs/product-workspace/spec.md` (delta archived under `openspec/changes/archive/2026-10-10-customer-design-parity/`).

## Global Constraints
- All UI copy is English; no fake availability, prices, bookings or permissions.
- No automatic provider retries, budget resets, external operational actions, push or deployment.
- Preserve snapshot/idempotency and distinguish stored proposal, human approval, sandbox receipt and real completion.
- Preserve unrelated dirty provider files.

## Review Focus
- No options: no mandatory technical form or invented defaults.
- Current proposal: exact window and valid references survive review.
- New evidence: stale proposal cannot be resubmitted as current.
- Lost response: safe replay and unknown status remain honest.
- Long IDs/mobile: order context stays in bounds and technical IDs stay secondary.

### Task 1: Restore Customer screen
**Files:** `platform-ui/customer.html`, `customer.css`, `customer.js`; optional narrowly scoped `customer-model.js`; customer browser tests.
**Interfaces:** Existing CustomerSession, offeredWindows, GET case, POST decisions only.
- [ ] Add a browser test that fails on current 700px shell/evidence form and requires approved 640px composition and safe empty state.
- [ ] Run it and retain the expected failure.
- [ ] Reuse source layout/styles and render the existing model through it. Keep technical evidence behind operator-only context; current proposal supplies existing references.
- [ ] Run customer unit/browser tests and save desktop/mobile screenshots.
- [ ] Report touched files, test evidence and remaining capability limitations. Do not commit independently.

### Task 2: Team visual and contract verification
**Files:** Team presentation only if the direct original comparison identifies a material mismatch; new verification artifacts.
- [ ] Compare original Team against current rendering, inspect selectors and no-options behavior.
- [ ] Correct only necessary presentation defects with a failing rendered test first.
- [ ] Run full frontend tests and backend platform suite; review Customer diff independently.

### Task 3: Live model verification
**Files:** New immutable run reports only.
- [ ] Inspect retained budget and provider readiness without exposing credentials.
- [ ] Run bounded existing evals across available OpenAI, Anthropic and Gemini providers; max six cutoffs/provider and $3/provider additional within the retained $25/provider scope.
- [ ] Report actual identities, completed responses, exact outcomes, safety/state checks, failures and unrun coverage. Never rewrite gold labels.

### Task 4: Handoff
- [ ] Inspect fresh desktop/mobile screenshots against source and archive OpenSpec after passing checks.
- [ ] Commit only this change and reports, leaving unrelated provider fixes intact.
- [ ] Open the revised local UI and give concise UI and LLM results with links and explicit limitations.
