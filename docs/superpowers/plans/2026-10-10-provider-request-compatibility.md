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

- [ ] Add tests with JSON-free case evidence and a network-boundary assertion that input contains `json` and equals persisted prompt.
- [ ] Run those tests red before changing production code.
- [ ] Add `"output_format": "json_object"` to both outer payloads before serialization.
- [ ] Run semantic/runner tests; preserve visible-only and anonymized-input checks.

## Task 2: Workspace selection and setup

Files: `providers.py`, `runner.py`, `config.example.json`, `README.md`, provider tests and new `tests/test_workspace_config.py`.

- [ ] Add failing transport and preflight tests for the five review-focus classes.
- [ ] Accept optional `workspace_id_env` only on Anthropic; require environment-name syntax and strict workspace value syntax at dispatch.
- [ ] Emit `anthropic-workspace-id` only on that provider, without changing the body.
- [ ] Add missing workspace names to preflight and allowlist safe workspace errors in receipts.
- [ ] Add the example field and document removal for scoped keys; set the observed ID only in private local env.
- [ ] Run `python3 -B -m unittest discover -s tools/dwelly_model/tests -v` and the equivalent `tools/dwelly_cases/tests` suite.

## Task 3: Verify and deliver

- [ ] First-smoke follow-up: add a model-only `_model_json` parser in `runner.py` accepting bare JSON or one outer JSON fence, retain exact raw receipts, and test rejection of prose/multiple blocks/duplicate keys/nonfinite numbers/trailing data in `tests/test_model_json.py`.
- [ ] Run the documented runtime suite with `PYTHONPATH=src:tests` from `runtime`.
- [ ] Obtain independent review of the diff; resolve evidence-backed issues.
- [ ] Run the real CLI with private environment, a new output directory, `--live --limit 2`; retain exact model identities, errors, usage and reservations.
- [ ] Record results without claiming accuracy, update tasks, validate/archive OpenSpec, and publish only reviewed source/docs.
