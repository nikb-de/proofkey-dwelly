# Independent audit of post-hoc answer annotations

The user-authorized append completed on 2026-10-10. This audit made no model calls and changed no answer, reasoning, source, candidate, judge record, or runner.

## Preservation and provenance

- All **60 annotated files** (`ANSWER.md` and `REASONING.md` for cases 001–030) retain their exact frozen original bytes as a prefix. No original paragraph, candidate JSON, or original reasoning was replaced.
- [ANNOTATION-MANIFEST.json](ANNOTATION-MANIFEST.json) records every original SHA256 and byte length, extended SHA256, verified prefix match, and all 90 judge-record hashes. Its original hashes refer to the unchanged [frozen packet](packet-final/manifest.json), not to a newly generated answer set.
- All **152 frozen packet artifacts**, frozen code hashes, **90 raw judge records**, 90 dispatch intents, original results/summary and budget ledger match the prior trace fingerprints. The source inputs and raw candidates are unchanged.
- Of the 286 other files in `ANSWERS/`, **285 remain byte-identical** to the pre-assessment inventory. `ANSWERS/README.md` separately gained an explanatory reading guide; its original 4,619-byte content remains an exact prefix (verified against the matching original at commit `e78578c`).

## Content checks

Every addition has the explicit heading “Post-hoc judge assessment (not the original system output)” or “Post-hoc judge observations (not original model reasoning).” The text states that these are uncalibrated later opinions, not human ground truth, new original reasoning, operational execution, or replacement answers.

Independent comparisons against the retained records passed for:

- **720 rubric cells**: eight rubrics × three judges × 30 cases.
- **180 status labels**: the same 90 judgments shown in both document types.
- **87 verbatim explanations**, **87 ordered evidence-reference lists**, and **87 critical-failure lists**. Removing only Markdown quote markers reproduces the retained explanation strings exactly, including paragraph breaks.
- All 90 per-case raw receipt bindings and **390 local links in the added sections**.

Case 014 remains a failed original answer with a null candidate. All three reviewers are shown as abstained/unscored, with dashes rather than placeholder numeric scores. Anthropic's malformed judgments for 004, 009 and 017 remain invalid/unscored, without synthesized explanations or scores. Their raw receipts are linked and were not repaired or retried.

## Reproduction boundary

The original full-file verification command is expected to reject the now-annotated working-tree Markdown: its full-file bytes intentionally differ. Do not alter the frozen hashes to make that check pass. Verify the original prefixes and extended hashes using the annotation manifest, or reproduce the original evaluation from the frozen source revision described in [INTEGRATION.md](INTEGRATION.md).

This audit establishes faithful append-only transcription and retained provenance, not the correctness or calibration of the judge opinions. The completed-run accounting and its nested missing-count caveat remain documented in [AUDIT.md](AUDIT.md).
