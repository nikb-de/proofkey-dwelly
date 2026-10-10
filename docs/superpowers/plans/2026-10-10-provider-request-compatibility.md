# Provider Request Compatibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox syntax for tracking.

**Goal:** Make the production evaluation runner use the request corrections proven by diagnostics.

**Architecture:** Keep corrections at existing semantic and transport boundaries. The outer prompt owns format metadata; only the Anthropic transport resolves workspace environment values. Keep private account setup outside Git.

**Tech Stack:** Python 3.11+, unittest, urllib, OpenSpec.

**Spec:** `openspec/changes/archive/2026-10-10-provider-request-compatibility/specs/dwelly-model-evaluation/spec.md`

## Global Constraints

- No retries, provider substitution, operational effects, or increased USD25 per-model cap.
- No credential values or actual workspace ID in source, public config or test fixtures.
- Persisted prompt equals the actual outbound input; future events and producer identity stay excluded.

## Review Focus

- Ordinary case text lacks the word JSON: the host payload must still satisfy JSON mode.
- Absent or malformed workspace values fail before HTTP; values never appear in errors.
- Workspace-scoped legacy keys keep working with the optional field omitted.
- OpenAI and Gemini must not accept the workspace option or receive its header.
- Offline preflight reports only environment names, not authentication/billing success.

## Task 1: JSON prompt compatibility

Files: `tools/dwelly_model/semantic.py`, `tests/test_semantic.py`, `tests/test_runner.py`.

- [x] Add tests with JSON-free case evidence and a network-boundary assertion that input contains `json` and equals persisted prompt.
- [x] Run those tests red before changing production code.
- [x] Add `"output_format": "json_object"` to both outer payloads before serialization.
- [x] Run semantic/runner tests; preserve visible-only and anonymized-input checks.

## Task 2: Workspace selection and setup

Files: `providers.py`, `runner.py`, `config.example.json`, `README.md`, provider tests and new `tests/test_workspace_config.py`.

- [x] Add failing transport and preflight tests for the five review-focus classes.
- [x] Accept optional `workspace_id_env` only on Anthropic; require environment-name syntax and strict workspace value syntax at dispatch.
- [x] Emit `anthropic-workspace-id` only on that provider, without changing the body.
- [x] Add missing workspace names to preflight and allowlist safe workspace errors in receipts.
- [x] Add the example field and document removal for scoped keys; set the observed ID only in private local env.
- [x] Run `python3 -B -m unittest discover -s tools/dwelly_model/tests -v` and the equivalent `tools/dwelly_cases/tests` suite.

## Task 3: Verify and deliver

- [x] First-smoke follow-up: add a model-only `_model_json` parser in `runner.py` accepting bare JSON or one outer JSON fence, retain exact raw receipts, and test rejection of prose/multiple blocks/duplicate keys/nonfinite numbers/trailing data in `tests/test_model_json.py`.
- [ ] Complete the documented runtime suite with `PYTHONPATH=src:tests` from `runtime`. The additional runtime regression attempt made during provider-compatibility verification was interrupted after more than five minutes; it remains incomplete, not passed, and the distinct original intake regression has no completed result.
- [x] Obtain independent review of the diff; resolve evidence-backed issues.
- [x] Run the real CLI with private environment, a new output directory, `--live --limit 2 --no-baseline`; retain exact model identities, errors, usage and reservations.
- [x] Record results without claiming accuracy, update tasks, and validate/archive OpenSpec.

Completion evidence is in [the provider compatibility record](../../verification/2026-10-10-provider-request-compatibility.md): 60 model tests, 58 intake tests, a 50-case offline Docker run and a two-case live smoke with eight received responses and six valid judge outputs. Publication remains a separate reviewed step; this status update does not claim a new publication or a completed runtime regression.
