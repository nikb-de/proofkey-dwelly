# Reality Test answers — Delivery & Logistics

Folders `001/` through `030/` contain actual system-generated results for the
30 official Delivery & Logistics cases from
[DwellyOrg/HackatonChallenges](https://github.com/DwellyOrg/HackatonChallenges/tree/ce84e8c0d8f7f8ddacd8d8fcfe53516c22885db7/Delivery%20%26%20Logistics).
Source revision: `ce84e8c0d8f7f8ddacd8d8fcfe53516c22885db7`.

The fixed run used **Claude Sonnet 5.5, high effort**, with the existing baseline
prompt, and finished on 10 October 2026 at **16:37:51 Europe/London**.
All 30 calls returned; 29 outputs passed the existing parser. **Case 014 failed
JSON parsing** and retains its original failed response, not a repaired answer.
These counts measure transport/format coverage, not decision accuracy.

Each folder contains `ANSWER.md`, `REASONING.md`, the exact `INPUT.json`, original
source files, `SOURCE_RESULT.json`, `WIRE.JSON`, `INTENT.JSON` and provenance.
The [complete run](../docs/verification/reality-test-2026-10-10/README.md)
also preserves frozen prompts, profiles, budget records and extraction receipts.
No external customer message, carrier operation, refund or other business effect
was executed: the results are proposed decisions and next actions.
States such as `ready` describe the model's coordination state, not successful
delivery, an approved refund or a completed carrier operation. Official case
wording is preserved; the cases are not replaced by our synthetic fixtures.

The two retained examples under `DEVELOPMENT/` are separate already-seen
development examples, not official challenge results.

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

The commands refuse existing case directories so reproduction must use a fresh output directory. They package retained development evidence; they do not rerun the original model or certify provenance. The official run uses the separate [reality runner](../tools/dwelly_reality/README.md), not this development exporter.
