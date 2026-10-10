# Reality Test answers — official cases not yet supplied

This directory contains no official challenge answers. The two retained examples under `DEVELOPMENT/` demonstrate the export format using already-seen development inputs and past model jobs. They are not the unseen Reality Test and do not satisfy submission requirements C or D.

The required layout from the supplied event guide is:

```text
ANSWERS/
  <supplied-case-id>/
    ANSWER.md
    REASONING.md
```

Retain each supplied case, including failures, partial outcomes and no-output states. `ANSWER.md` should state what was received, attempted, produced, escalated and actually observed. `REASONING.md` should contain a concise evidence-backed rationale and uncertainty, not hidden model reasoning. Keep operational acceptance, verified state, physical receipt and payment distinct.

Answers must be produced by the frozen submitted system. Do not replace unsuccessful outputs with corrected human-written answers. Apply the organiser's exact case identifiers and any additional final schema when provided. Review the publishability of inputs, traces and outputs before inclusion.

## Retained development examples

| Example | Actual retained result | Evidence |
|---|---|---|
| [OpenAI: team-003, cutoff 4](DEVELOPMENT/openai/team-003/ANSWER.md) | A model candidate was accepted, but its state and wait target both disagree with the unvalidated author reference. Its unsupported claim that the gate had been released is preserved. No operational effect was recorded. | [Public rationale](DEVELOPMENT/openai/team-003/REASONING.md), [original record bytes](DEVELOPMENT/openai/team-003/SOURCE_RECORD.json), [hash receipt](DEVELOPMENT/openai/team-003/EXPORT.json) |
| [Gemini: team-001, cutoff 4](DEVELOPMENT/gemini/team-001/ANSWER.md) | `outcome_unknown` after `incomplete_response`, with no accepted candidate and no retained provider response. No replacement answer or retry was generated. | [Public rationale / missing-output note](DEVELOPMENT/gemini/team-001/REASONING.md), [original record bytes](DEVELOPMENT/gemini/team-001/SOURCE_RECORD.json), [hash receipt](DEVELOPMENT/gemini/team-001/EXPORT.json) |

Each bundle preserves the complete stored job input, original record bytes, statuses, attempts, receipts, errors and available checks. An accepted candidate is not proof of a correct answer or completed delivery. The existing records do not contain raw provider wire requests or all raw response text; missing evidence is not reconstructed.

The offline exporter is [documented here](../tools/dwelly_submission/README.md). These exact commands produced the examples without new model calls:

```sh
python3 -m tools.dwelly_submission \
  --record docs/verification/platform-live-e2e-2026-10-10-rerun/openai-gpt-4-1-mini/team/team-003-4.json \
  --output ANSWERS/DEVELOPMENT/openai

python3 -m tools.dwelly_submission \
  --record docs/verification/platform-live-e2e-2026-10-10-rerun/gemini-2-5-flash/team/team-001-4.json \
  --output ANSWERS/DEVELOPMENT/gemini
```

The commands refuse existing case directories so reproduction must use a fresh output directory. They package retained development evidence; they do not rerun the original model or certify provenance. Official case collection, execution through the final frozen system and complete official output packaging remain outstanding.
