# Dwelly Model Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox syntax for tracking.

**Goal:** Publish an experimental three-provider model/evaluation CLI and Docker package.

**Architecture:** Separate API transport, semantic contracts and offline/live runner. Existing operational runtime is unchanged. Proposals are frozen before evaluator references are loaded.

**Tech Stack:** Python 3.12 standard library, unittest, Docker.

**Spec:** `openspec/changes/dwelly-model-release/design.md`.

## Global Constraints
- No operational effects; all outputs are proposed_unsent and effects=[]; no private source uploads.
- No live calls without explicit live mode and credentials; USD 25 maximum per provider/model per experiment, no retries.
- OpenAI/Anthropic/Gemini seats are never substituted. Missing seats remain missing.
- Eight integer 0..4 rubric scores remain provisional, with critical failures and abstentions separate.
- New team 10–20 eval and 10–20 live cases are pending, not synthesized as claimed real evidence.

## Review Focus
- Credentials leaked via HTTP errors, receipts or Docker context.
- Future reference content entering proposer prompts.
- Repeated/parallel calls bypassing spend reservation.
- Invalid or missing judge output inflating quality aggregates.
- Docker/CLI working only in original checkout rather than shipped files.

### Task 1: Provider transport
**Files:** `tools/dwelly_model/providers.py`, `tests/test_providers.py`.
**Interfaces:** `providers.complete` and `ProviderError` exactly as spec.
- [x] Add tests with injected network boundary responses and inspect outgoing provider envelopes; run to fail.
- [x] Implement fixed HTTPS, environment keys, bounded reads/timeouts, no redirect, response parsing and identity metadata.
- [x] Run `python -m unittest discover -s tools/dwelly_model/tests -p test_providers.py -v`; verify green.

### Task 2: Semantic contracts
**Files:** `tools/dwelly_model/semantic.py`, `tests/test_semantic.py`.
**Interfaces:** proposal_prompt, validate_proposal, judge_prompt, validate_judgment, aggregate exactly as spec.
- [x] Add tests for no future leakage, known invalid/fabricated outputs, exact rubric coverage, abstention and missing-seat aggregation; run to fail.
- [x] Implement snapshot-only prompt, anchored eight-rubric judge, strict schemas and provisional summaries.
- [x] Run `python -m unittest discover -s tools/dwelly_model/tests -p test_semantic.py -v`; verify green.

### Task 3: Runner and budget
**Files:** `tools/dwelly_model/budget.py`, `runner.py`, `tests/test_runner.py`.
**Interfaces:** run_experiment/preflight exactly as spec; consumes Task 1/2 APIs.
- [x] Add tests for reservation cutoff, errors retaining debit, proposal freeze, missing credentials and actual file outputs; run to fail.
- [x] Implement exclusive non-overwrite experiment, budgets, dry-run manifests, API receipts and structured report.
- [x] Run `python -m unittest discover -s tools/dwelly_model/tests -p test_runner.py -v`; verify green.

### Task 4: CLI, publication and review
**Files:** package `__init__.py`, `__main__.py`, `README.md`, `config.example.json`, root `Dockerfile`/`.dockerignore`, CLI tests and team intake document.
- [x] Write subprocess help/offline/preflight tests and run to fail.
- [x] Add commands preflight, dry-run and run with --live; support explicit model configs and bounded case count.
- [x] Run package suite plus existing 58 intake tests and Docker build/offline smoke.
- [ ] Independently review diff and source package; publish allowlisted files to private repo and verify bytes.
- [ ] Record live/API limitations and archive only completed scope.
