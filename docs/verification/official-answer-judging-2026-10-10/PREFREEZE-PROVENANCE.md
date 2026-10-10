# Pre-freeze judging and replacement provenance

## Finding

The tracked repository **did contain generic three-provider judging before the 16:30 freeze**. It does **not establish a pre-existing automatic judge-feedback → revised official answer → replacement loop**. The current exact-30 whole-answer judging adapter is new post-hoc work, not that older judging path. This is a code/history finding, **not a ruling on what the organiser permits**.

## Historical anchor and scope

Inspected Git object: `fd8533297d259f4a997710045852e4eb2f3ef771`, subject `Match README sections to hackathon requirements`. Git records both author and commit time as **2026-10-10 16:26:51 +01:00**. All line references below are to that object, obtained with `git show fd85332:<path>`, not mutable working-tree lines. Git timestamps are repository metadata, not independent time attestation.

The generic evaluator was added in ancestor `35e5dbd` (`2026-10-10 10:56:29 +01:00`, `feat: add three-provider model evaluation CLI and compact architecture`). The tracked pre-freeze tree contains neither `tools/dwelly_reality/runner.py`, nor `docs/verification/official-answer-judging-2026-10-10/judge.py`, nor `ANSWERS/001/ANSWER.md`.

## What demonstrably existed

| Pre-freeze evidence | What it establishes | What it does not establish |
| --- | --- | --- |
| `tools/dwelly_model/runner.py:20–59` | A proposer and exactly three judge seats, covering OpenAI, Anthropic and Gemini, are configured explicitly. | That the current official-30 whole-report adapter existed. |
| `tools/dwelly_model/runner.py:268–299` | Proposer calls run; proposals are persisted and a proposal-set hash is frozen **before** references or judges are used. | An iterative generation loop after grading. |
| `tools/dwelly_model/runner.py:301–361` | Judges assess the frozen candidate/baseline variants; repeat passes grade the same proposals; judgments and aggregates are written. | Any judge result being fed back to the proposer, candidate rewrite or replacement of a prior answer. |
| `tools/dwelly_model/semantic.py:220–227` | The older judge payload contains a visible snapshot and `proposal.action`, optionally a historical reference action. | Whole-report review of published `ANSWER.md`, `REASONING.md` and host status. |
| `tools/dwelly_model/README.md:29,48–54` | Repeated judging is described as verdict-variability measurement on identical proposals; no automatic retry; invalid JSON is not repaired. | A retry/repair policy for failed official answers. |
| `tools/dwelly_analysis/model.py:201–214,248–255` and `tools/dwelly_analysis/worker.py:122–145` | The application path makes one bounded proposal call, parses it locally, optionally computes a mechanical comparison, then stores the result or failure. | A semantic judge-driven rewrite stage. |
| `tools/dwelly_analysis/evaluation.py:1–20` | Reference comparison reports literal state/wait-target agreement with `accuracy_score: null`. | Three-model judging, corrective feedback or automatic answer improvement. |

## Other apparent “revision”, “feedback” and “repair” paths

A read-only search of the pre-freeze tracked Python/JavaScript/TypeScript/shell sources for `judge`, `feedback`, `refine`, `regenerat` and `repair`, followed by inspection of relevant hits, did not locate another implemented judge-to-answer replacement path.

- `runtime/src/proofkey/assessment/coverage.py:270–292` captures judgments of existing output bytes. Its control path (`320–332`) separately captures executions and judgments; it does not construct a corrected answer. Repeatability checks require an unchanged candidate (`351–353`).
- `runtime/src/proofkey/assessment/ledger.py:59–69` uses a `feedback` flag to adjust evaluation split treatment. That is dataset-exposure accounting, not generation feedback.
- `tools/dwelly_platform/models.py:93–110` replays an existing admitted job and repairs its history link; the comment explicitly rejects creating a replacement job during historical replay. Case revision counters bind new evidence and jobs to snapshots; they are not answer-revision rounds.
- `tools/dwelly_analysis/worker.py:147–172` repeatedly polls for work but does not automatically retry an already-dispatched call. A worker service loop is not an answer-improvement loop.

This bounded search supports **“automatic judge-based replacement not found in the inspected pre-freeze tree,” not proof that no separate untracked/external script ever existed**.

## Official-output boundary already documented before freeze

Pre-freeze `ANSWERS/README.md:14–16` requires preserving failures, partial outcomes and no-output states; it says answers must be produced by the frozen submitted system and must not be replaced with corrected human-written answers. Lines 22–25 retain unsuccessful development examples without inventing missing results. This is evidence of the repository's own declared workflow, not independent organiser approval or interpretation.

The current `judge.py` instead explicitly assesses the **exact published** answer/candidate/status, preserves original bytes in a frozen packet, and does not generate or overwrite answers. It reuses the older rubric and provider utilities, but its whole-answer payload and execution adapter are post-hoc additions. Therefore:

1. **“Judging already existed before 16:30” — confirmed, in the generic action-judging sense.**
2. **“This exact official-30 whole-answer assessment already existed before 16:30” — not supported; the adapter/path is absent from the anchored tree.**
3. **“The frozen system automatically replaced answers based on judges” — not found in the inspected code; the demonstrated flow freezes, grades and reports.**
4. **“Replacement is permitted by the event” — unresolved by this audit; that requires the actual event rules/organiser interpretation, not a code inference.**

## Reproducibility fingerprints

SHA-256 of historical file bytes at `fd85332`:

- `tools/dwelly_model/runner.py`: `e3c06a8bc817e57a9bec9e2fea8ffc6c292e7bdc684f849eb65010cd11f8ec19`
- `tools/dwelly_model/semantic.py`: `880ec02bc535280e10e13efed05230def4fed33da0e160fa92c0bb68229ba988`
- `tools/dwelly_analysis/model.py`: `94bfb4578dd7a6eedf42de8ef6abe29b4ddcb53b2cd50a23f04690540b0bc9f3`
- `ANSWERS/README.md`: `b93ca2435c33085b20814b00d14d1ae0f851d46de34f50587f9109d33e98ffa0`

No API calls, official-answer changes, source changes or runtime changes were made for this audit.
