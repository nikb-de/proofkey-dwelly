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

**Spec:** `openspec/changes/official-reality-test-run/specs/reality-test-execution/spec.md`.

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
- [ ] Extraction: tests first for traversal, symlinks, overwrite and extraction errors;
  run `python3 -m unittest discover -s tools/dwelly_evidence_extract/tests -v`.
- [ ] Runner: tests first for chronology, hidden/future evidence, input integrity,
  retries and failure export; run
  `python3 -m unittest discover -s tools/dwelly_reality/tests -v`.
- [ ] Preparation: freeze all 30 cases, exact baseline prompt, profiles and sidecars;
  verify source counts, hashes and missing extraction inventory before paid calls.
- [ ] Execution: explicit live opt-in, maximum three concurrent calls, retain
  every intent and response, export `ANSWERS/001` through `ANSWERS/030`.
- [ ] Calibration: repeat fixed development controls, report valid coverage,
  critical-failure flips, abstentions and score spread; no official-case tuning.
- [ ] Publication: scan new artifacts for credentials, verify answer/source links,
  update submission status from receipts, commit source and actual outputs,
  then archive the completed OpenSpec change.
