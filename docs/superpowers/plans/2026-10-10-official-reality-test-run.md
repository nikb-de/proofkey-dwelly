# Official Reality Test Execution Plan

> **For agentic workers:** Use parallel subagents for extraction, execution and
> judge reliability; root coordinates frozen inputs, budgets and publication.

**Goal:** Produce auditable organiser-format answers for all 30 official
Delivery & Logistics cases using existing prompts and explicit model profiles.

**Architecture:** Keep the input adapter and extraction separate from inference.
Retain the selected baseline bytes, provider wire records and original outputs.
The existing development campaign and a development-only judge reliability
pilot run independently; official outputs never select prompt revisions.

**Tech Stack:** Existing Python provider/model contract, local PDF text extraction,
native macOS Vision OCR and append-only local budget records.

**Living spec:** `openspec/specs/reality-test-execution/spec.md`.

## Global constraints
- Source revision: `ce84e8c0d8f7f8ddacd8d8fcfe53516c22885db7`.
- Baseline prompt SHA-256: `61592fb429180e7da972a572ffc17e0379944c8bd7f2a84f049f725e510cbf80`.
- Primary model: explicitly selected Claude Sonnet 5.5, high effort.
- USD 25 maximum per provider/model per experiment; no automatic retry.
- No real messages, delivery changes, refunds or other external business effects.
- Missing results are not passing results; machine formatting is not manual correction.

## Review focus
- Future-known evidence is excluded by decision time, not by the execution date.
- Every attachment is preserved; absent/failed extraction remains explicit.
- Actor declarations and OCR text do not establish identity or authority.
- Existing intents prevent duplicate paid dispatch after interruption.
- Every answer links to the actual input and result, including failed calls.

## Parallel execution
- [x] Extraction: tests first for traversal, symlinks, overwrite and extraction errors;
  run `python3 -m unittest discover -s tools/dwelly_evidence_extract/tests -v`.
- [x] Runner: tests first for chronology, hidden/future evidence, input integrity,
  retries and failure export; run
  `python3 -m unittest discover -s tools/dwelly_reality/tests -v`.
- [x] Preparation: freeze all 30 cases, exact baseline prompt, profiles and sidecars;
  verify source counts, hashes and missing extraction inventory before paid calls.
- [x] Execution: explicit live opt-in, maximum three concurrent calls, retain
  every intent and response, export `ANSWERS/001` through `ANSWERS/030`.
- [x] Calibration: repeat fixed development controls, report valid coverage,
  critical-failure flips, abstentions and score spread; no official-case tuning.
- [x] Publication: scan new artifacts for credentials, verify answer/source links,
  update submission status from receipts, commit source and actual outputs,
  then archive the completed OpenSpec change.

Published results in commit `8f74816` to `main`. Unauthenticated readback of
cases 001, 014, 030 and the judge report returned HTTP 200 with exact local
bytes. Official run: 30 calls, 29 parsed candidates, one retained failure;
judge pilot: 108 valid judgments, 105 scored and three abstentions. No business
effects. Nine runner, six extraction, nine pilot, 75 model and 58 case tests
passed. Source/output whitespace remains untouched for evidence fidelity.
The archived change's new living specification passes strict validation. The
repository-wide specification check is 33/34: the unchanged older
`mobile-case-recording` specification lacks a required Purpose heading.
