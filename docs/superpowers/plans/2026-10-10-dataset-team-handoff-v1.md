# Dataset Team Handoff v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Give colleagues a portable canonical dataset authoring kit now, without changing backend interfaces or claiming a qualified evaluation.

**Architecture:** Unchanged canonical inputs and labels plus separate evaluator criteria/manifest. Three synthetic development families exercise immutable revisions. Standalone schema/semantic validation and an integrity-checked ZIP establish reproducibility, not model quality.

**Tech Stack:** Python 3.9+, jsonschema 4.25.1, referencing 0.36.2, JSON/JSONL, Markdown, ZIP.

**Spec:** `openspec/changes/archive/2026-10-10-dataset-team-handoff-v1/specs/team-dataset-handoff/spec.md`

## Global Constraints

- Preserve `contracts/v1` byte-for-byte and leave `docs/dataset-drafts/` untouched.
- Keep labels, criteria, manifests, episodes and future events out of model inputs.
- All bundled examples are fictional, development-only and unreviewed.
- No providers, paid generation, training, network schema resolution or operational effects.
- One source family and all its revisions/branches stay in one split.

## Review Focus

- Matching JSON shapes with mismatching source IDs or hashes must fail.
- Modified historical prefixes must fail, even with rehashed files.
- Traversal/symlink inputs must not load arbitrary local files.
- Human-review and training-eligibility claims must match actual review fields.
- ZIP recipients must not depend on the original repository location.

## Tasks

### Task 1: Canonical examples and authoring docs
- [x] Copy the eight schemas unchanged; generate inputs/labels/criteria/episodes and root manifest with exact-byte hashes.
- [x] Validate all snapshots against isolated CaseStore create/append and regenerate byte-identically.
- [x] Write copy-ready collection/review guidance, eight rubric anchors and legacy compatibility limits.

### Task 2: Standalone validation
- [x] Write failing negative tests in `datasets/team-handoff-v1/tests/test_validate.py` for hashes, source mismatch, leakage, split crossing, references, traversal, review status and history changes.
- [x] Implement `scripts/validate.py` with local-only schema registry and explicit validation report.
- [x] Run `python3 -m unittest discover -s tests -v` and `python3 scripts/validate.py .` from the kit.

### Task 3: Independent review and distribution
- [x] Review generated examples, documentation, validator and tests together.
- [x] Package only the kit; include exact-file integrity inventory.
- [x] Extract into a temporary directory, check inventory and repeat the documented commands there.
- [x] Record evidence, archive the OpenSpec change, and provide ZIP plus a short team message.
