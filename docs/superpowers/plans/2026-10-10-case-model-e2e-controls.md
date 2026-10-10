# Case-model E2E controls implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox syntax for tracking.

**Goal:** Prove observable model and state behavior through the actual platform on existing authored cases.
**Architecture:** Source-to-canonical replay and an external expectation ledger feed a bounded HTTP E2E runner; the existing platform remains the system under test. UI adds read-only monitoring, not execution authority.
**Tech Stack:** Python stdlib/psycopg, existing model worker, browser ES modules, pytest and Playwright.
**Spec:** `openspec/specs/case-model-e2e/spec.md`; design archived at `openspec/changes/archive/2026-10-10-case-model-e2e-controls/design.md`.

**Result:** Local implementation and scripted E2E are complete. Live preflight was unavailable; zero live provider calls. See `docs/verification/case-model-e2e-2026-10-10/README.md` for measured coverage and limits.

## Global Constraints
- Work only in the existing `codex/proofkey-runtime` worktree. Preserve `docs/dataset-drafts/`.
- Source has 16 cutoffs but only one logistics family plus one UI control. Keep author labels unvalidated and outside inference.
- All new UI/machine labels are English. Preserve original source text.
- Frozen v1 contract and business policy are unchanged. Model state is not business authority; external effects remain zero.
- Modes are explicitly `simulated` or `live`. No simulated result is live evidence; unavailable output is never a pass.
- No live calls without configured credentials and explicit live mode. Maximum 16 source cutoffs per profile, one attempt each, existing USD25 per provider/model/experiment cap. No automatic retry of uncertain dispatch.
- No public push, production deployment, secret values in reports or source, or automatic source/reference replacement.

## Review Focus
- Future actor leakage through a union of all source participants: each cutoff must declare only currently visible actors (Task 1).
- Reference text accidentally becoming source context: context only contains original goal and visible names/roles, not answer fields (Task 1).
- A transport failure counted as semantic success or hidden by aggregate score: explicit unavailable rows and mode qualification (Task 2).
- A poll for a previously selected case replacing current state or triggering POST after reload (Task 3).
- A live profile quietly substituted by fixtures or an old result accepted for the wrong input/profile (Tasks 2 and 4).

### Task 1: Replay and independently specified checks
**Files:** Create `tools/dwelly_e2e/__init__.py`, `cases.py`, `checks.py`, `tests/test_cases.py`, `tests/test_checks.py`, `tests/fixtures/good-candidates.json`.
**Interfaces:** `build_case(source_id,step_index,run_id)->dict`; `case_plans(run_id)->list[dict]`; plan keys `case_id,source,declaration,events,expectation`. `source` contains `source_id,step_index,family_id,source_sha256,qualification`. Declaration is frozen-v1; events are appendable exact canonical events. First event ID `source-context` is internal JSON text with goal and visible actor id/name/role only. Context timestamp is the earliest source message timestamp or `2026-02-03T00:00:00+00:00` when absent. Additional participant `e2e-observer` is allowed only for source control lacking a distinct customer; it must be explicitly marked in source metadata. IDs fit 64 characters; validate run ID bounded alphanumeric/hyphen. Source messages retain original IDs, sender/recipient, text and normalized timestamp. Unsupported channel becomes internal with original channel recorded in source metadata. Never select body_ru over an available body.
`evaluate(job,detail,plan)->list[dict]` check keys `name,category,status,expected,actual`. `summarize(records,mode)->dict`. Record keys `plan,job,detail,checks`; report must keep semantic/operational counts and unavailable separate. Hand-written expectation fields `allowed_states`, `allowed_actions`, `waiting_for`, `completion_allowed`, `qualification`. Model candidate is parsed `proofkey-step-candidate-v1`.
- [x] Write RED tests: 16 cutoffs, distinct valid case IDs, source hashes, source initial goal and visible roles present, no future actor at earlier cutoff, source text/event/direction fidelity, no author labels in upload; malformed run IDs rejected.
```python
p = build_case('case-002-n4', 4, 'canary')
assert 'correction_form' not in p['declaration']['participants']
assert p['source']['step_index'] == 4
assert 'agent_state' not in p['events'][0]['text']
assert p['expectation']['completion_allowed'] is False
```
- [x] Implement mapping and literal expectation table by inspecting every source cutoff. Initial context-only cutoffs are insufficient-evidence controls. Provide hand-authored valid candidate fixtures separately from expectation computations.
- [x] Write checker RED/GREEN controls for premature completed, wrong wait target, invented evidence, missing output, wrong input hash and nonzero effects. Good fixtures separate from output of checker. Simulated semantic totals are explicitly fixture-only.
- [x] Run focused tests; report RED/GREEN output and any source ambiguities. No commit by subagent.

### Task 2: Bounded HTTP E2E runner
**Files:** Create `tools/dwelly_e2e/runner.py`, `__main__.py`, `tests/test_runner.py`.
**Interfaces:** `run(base_url,mode,profile_id,output,run_id,limit=16,poll_timeout=90)->dict`; HTTP JSON through `/api/platform`. Case writes require platform marker/idempotency. CLI `python -m tools.dwelly_e2e run --base-url http://127.0.0.1:8095 --mode live --profile openai-gpt-4-1-mini --output NEW_DIR --run-id canary [--limit N]`. Consume Task 1 interfaces exactly; output `report.json` and `report.md`, source/checkpoint records under output, with no secrets. Preflight report is still written on unavailable profile; exit 2 unavailable, 1 check failure, 0 permitted success; simulated success explicitly says fixture-only. Output directory must not exist; validate mode/base/limit before network. Loopback only, no HTTP redirects. Accept a simulated profile only when its provider/model is clearly prefixed SIMULATED and reject it in live mode.
- [x] Write RED tests for invalid origin/output/limit, unavailable and disabled profiles, fake-as-live refusal, partial output/timeout accounting. Local HTTP fake may cover error handling, but do not call it full E2E evidence.
- [x] Implement real API create/append/submit/poll/readback. Deterministic keys derived from run/source/cutoff. Poll terminal states by GET only, keep first returned run ID, verify case/hash/profile binding before success. Submit identical key after terminal and verify same run ID, dispatch count unchanged. Persist each raw job/receipt/check before moving on; stop affected run on auth/budget/unknown-dispatch errors. Do not send labels to API.
- [x] Probe last successfully processed case: append explicit synthetic later text, check analysis stale, reject old-revision fresh submit, replay original key to original job with no new attempt. Keep pre-probe detail as the semantic evidence and store probe separately. Example assertion: `new_detail['states']['analysis']=='stale'`; no action records may appear.
- [x] Run focused tests and report. No provider calls, no commit by subagent.

### Task 3: Visible model state and work monitoring
**Files:** Modify only `platform-ui/app.js`, `session.js`, `style.css`, `tests/session.test.mjs`; optionally create `tests/polling.test.mjs`.
**Interfaces:** Export pure `modelStatusView(job,snapshot)` with `current,transport,coordination,waitingFor,proposedAction,dispatchAttempts,automaticRetries,operationalEffects`. Never accept an unbound candidate as current. Export a small read-only polling controller if useful, with explicit dispose/generation guards. Existing API and page IDs stay compatible.
- [x] Write RED tests for pending/failed/current/stale display data, selected-case race, and terminal/reload behavior. No effect or submission may happen from polling.
- [x] Render compact English coordination state, waiting targets, proposed action and transaction counters in each job; retain provider receipt and full JSON. Poll nonterminal selected-case jobs by GET on a bounded interval, stop on terminal/error/selection change. Do not cause a feedback loop with render callbacks. Manual refresh remains available after error.
- [x] Run platform/session/widget Node tests and report. No commit by subagent.

### Task 4: Real integration, browser acceptance and handoff
**Files:** Controller creates `tools/dwelly_e2e/tests/fixture_server.py`, `platform-ui/tests/case-model-e2e.mjs`, `docs/case-model-e2e.md`, verification artifact directory and updates OpenSpec tasks.
- [x] Build isolated real PostgreSQL + actual platform/worker test fixture. Only `model.request` is scripted and visibly SIMULATED. Use hand-authored candidate fixtures from Task 1, never derive a simulated output by invoking the evaluator. Validate input event mapping in fixture; responses include explicit simulated observed model/request IDs.
- [x] Run runner through this fixture on all16 cutoffs. Keep case and model jobs real. Use fault controls for outcome_unknown and durable replay/recovery. Teardown only unique test schemas and verify absence.
- [x] Run browser acceptance: existing source case model submit, visible running→terminal coordination status, reload preserves ID/candidate, append makes prior result stale, waiting target and transaction counts visible, zero effects, no browser exceptions/mobile overflow. Save screenshots and report.
- [x] If keys are supplied, run a bounded OpenAI canary first through actual API + browser; inspect every state assertion. Then other available profiles under existing cap. Record exact failures rather than broad retries or prompt tuning. If no keys, create explicit live-unavailable receipt and do not claim live success.
- [x] Independent code review and fixes, selected canonical Python regression, Node suites, OpenSpec validation/archive, local commit and no push. Final report distinguishes semantic, operational, simulated and live evidence.
