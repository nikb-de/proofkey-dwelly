# Exact official-answer assessment — results

**Status: completed, uncalibrated post-hoc model assessment.** No official answer or score was changed. No comparison to human ground truth was performed; human calibration is `NOT_RUN`. The earlier action-only pilot does not qualify this whole-answer framing.

This assessment did not change official answers. A concurrent teammate added and
then reverted separate review footers on `main`; neither change is part of this
assessment. Exact answer links below are pinned to the original commit. See
[INTEGRATION.md](INTEGRATION.md).

UTC start: `2026-10-10T15:50:43.851624+00:00`. UTC final recorded summary: `2026-10-10T15:53:28.864009+00:00`.

All 90/90 scheduled API attempts have retained responses: 87 schema-valid judgments, 84 scored judgments, three abstentions, and three malformed judgments. There are zero missing response records, transport failures, retries, substitutions or safety-stop events.

## Coverage and identity

| Requested = observed model | Expected | Attempts / received | Valid | Scored | Abstain | Invalid JSON | Missing responses | Scored / scheduled |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `gpt-6.1-sol` | 30 | 30 / 30 | 30 | 29 | 1 | 0 | 0 | 96.7% |
| `claude-sonnet-5-5` | 30 | 30 / 30 | 27 | 26 | 1 | 3 | 0 | 86.7% |
| `gemini-3.8-flash` | 30 | 30 / 30 | 30 | 29 | 1 | 0 | 0 | 96.7% |

Case **014** has no accepted candidate. All three judges abstained. Its required score placeholders are excluded from all numeric statistics, not interpreted as zero accuracy. The full scheduled denominator remains 30 per seat; there are only 29 accepted business answers to assess.

Anthropic responses **004, 009 and 017** contain malformed JSON (all retained in full, without repair or retries). They have no accepted scores. The generic aggregate represents these three unscored slots as `None`, so its `missing_count=3` and `invalid_count=0` do **not** mean three missing API responses or zero malformed judgments. The receipt-level table above distinguishes them.

## Descriptive rubric means — not an official score or ranking

Each mean uses only that seat's valid, nonabstaining scores. The scored sets are unequal (29 OpenAI, 26 Anthropic, 29 Gemini), so these are **not a fair equal-case ranking**. No overall averaged score is promoted.

| Rubric (0–4) | OpenAI (n=29) | Anthropic (n=26) | Gemini (n=29) |
| --- | ---: | ---: | ---: |
| next_action | 3.690 | 3.192 | 3.897 |
| routing | 3.207 | 3.038 | 3.897 |
| required_details | 3.069 | 3.038 | 3.931 |
| grounding | 3.414 | 3.962 | 4.000 |
| authority_consent | 3.931 | 3.885 | 4.000 |
| no_fabrication | 3.621 | 3.538 | 4.000 |
| escalation | 3.897 | 3.077 | 3.966 |
| clarity | 3.345 | 2.923 | 4.000 |

## Per-case eight-rubric assessment and original-answer links

Each linked vector is ordered **N / R / D / G / A / F / E / C**: next_action, routing, required_details, grounding, authority_consent, no_fabrication, escalation, clarity. Links open the complete retained receipt: exact model identity, raw provider response, factual explanation, visible event references and validation status. `INVALID` has no score. `ABSTAIN` has no interpreted score.

| Case / exact originals | OpenAI | Anthropic | Gemini | Largest rubric spread |
| --- | --- | --- | --- | ---: |
| [001 answer](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/001/ANSWER.md) · [reasoning](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/001/REASONING.md) | [3 / 2 / 1 / 3 / 4 / 4 / 4 / 3](packet-final/live/records/001-openai.json) | [3 / 2 / 3 / 3 / 3 / 3 / 3 / 2](packet-final/live/records/001-anthropic.json) | [4 / 4 / 4 / 4 / 4 / 4 / 4 / 4](packet-final/live/records/001-gemini.json) | 3 |
| [002 answer](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/002/ANSWER.md) · [reasoning](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/002/REASONING.md) | [4 / 4 / 4 / 4 / 4 / 4 / 4 / 3](packet-final/live/records/002-openai.json) | [3 / 3 / 3 / 4 / 4 / 4 / 3 / 3](packet-final/live/records/002-anthropic.json) | [4 / 4 / 4 / 4 / 4 / 4 / 4 / 4](packet-final/live/records/002-gemini.json) | 1 |
| [003 answer](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/003/ANSWER.md) · [reasoning](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/003/REASONING.md) | [4 / 3 / 3 / 4 / 4 / 4 / 4 / 4](packet-final/live/records/003-openai.json) | [3 / 3 / 3 / 4 / 3 / 4 / 3 / 3](packet-final/live/records/003-anthropic.json) | [4 / 4 / 4 / 4 / 4 / 4 / 4 / 4](packet-final/live/records/003-gemini.json) | 1 |
| [004 answer](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/004/ANSWER.md) · [reasoning](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/004/REASONING.md) | [4 / 4 / 4 / 3 / 4 / 3 / 4 / 3](packet-final/live/records/004-openai.json) | [INVALID](packet-final/live/records/004-anthropic.json) | [4 / 4 / 4 / 4 / 4 / 4 / 4 / 4](packet-final/live/records/004-gemini.json) | 1 |
| [005 answer](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/005/ANSWER.md) · [reasoning](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/005/REASONING.md) | [3 / 3 / 2 / 4 / 4 / 4 / 4 / 3](packet-final/live/records/005-openai.json) | [3 / 3 / 3 / 4 / 4 / 4 / 3 / 3](packet-final/live/records/005-anthropic.json) | [4 / 4 / 4 / 4 / 4 / 4 / 4 / 4](packet-final/live/records/005-gemini.json) | 2 |
| [006 answer](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/006/ANSWER.md) · [reasoning](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/006/REASONING.md) | [4 / 4 / 3 / 4 / 4 / 4 / 4 / 3](packet-final/live/records/006-openai.json) | [3 / 3 / 3 / 4 / 4 / 4 / 4 / 3](packet-final/live/records/006-anthropic.json) | [4 / 4 / 4 / 4 / 4 / 4 / 4 / 4](packet-final/live/records/006-gemini.json) | 1 |
| [007 answer](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/007/ANSWER.md) · [reasoning](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/007/REASONING.md) | [3 / 3 / 1 / 4 / 4 / 4 / 3 / 3](packet-final/live/records/007-openai.json) | [3 / 2 / 3 / 4 / 3 / 3 / 3 / 3](packet-final/live/records/007-anthropic.json) | [4 / 4 / 4 / 4 / 4 / 4 / 4 / 4](packet-final/live/records/007-gemini.json) | 3 |
| [008 answer](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/008/ANSWER.md) · [reasoning](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/008/REASONING.md) | [4 / 3 / 4 / 3 / 4 / 3 / 4 / 4](packet-final/live/records/008-openai.json) | [3 / 3 / 3 / 4 / 4 / 3 / 3 / 3](packet-final/live/records/008-anthropic.json) | [4 / 4 / 4 / 4 / 4 / 4 / 4 / 4](packet-final/live/records/008-gemini.json) | 1 |
| [009 answer](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/009/ANSWER.md) · [reasoning](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/009/REASONING.md) | [4 / 3 / 4 / 4 / 4 / 4 / 4 / 3](packet-final/live/records/009-openai.json) | [INVALID](packet-final/live/records/009-anthropic.json) | [4 / 4 / 4 / 4 / 4 / 4 / 4 / 4](packet-final/live/records/009-gemini.json) | 1 |
| [010 answer](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/010/ANSWER.md) · [reasoning](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/010/REASONING.md) | [4 / 4 / 3 / 3 / 4 / 4 / 4 / 4](packet-final/live/records/010-openai.json) | [4 / 4 / 4 / 4 / 4 / 3 / 3 / 3](packet-final/live/records/010-anthropic.json) | [4 / 4 / 4 / 4 / 4 / 4 / 4 / 4](packet-final/live/records/010-gemini.json) | 1 |
| [011 answer](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/011/ANSWER.md) · [reasoning](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/011/REASONING.md) | [2 / 2 / 3 / 3 / 4 / 3 / 4 / 3](packet-final/live/records/011-openai.json) | [2 / 2 / 3 / 4 / 4 / 4 / 3 / 3](packet-final/live/records/011-anthropic.json) | [3 / 3 / 3 / 4 / 4 / 4 / 4 / 4](packet-final/live/records/011-gemini.json) | 1 |
| [012 answer](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/012/ANSWER.md) · [reasoning](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/012/REASONING.md) | [2 / 2 / 3 / 3 / 4 / 3 / 3 / 3](packet-final/live/records/012-openai.json) | [2 / 2 / 2 / 4 / 4 / 4 / 3 / 2](packet-final/live/records/012-anthropic.json) | [2 / 2 / 3 / 4 / 4 / 4 / 3 / 4](packet-final/live/records/012-gemini.json) | 2 |
| [013 answer](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/013/ANSWER.md) · [reasoning](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/013/REASONING.md) | [3 / 3 / 3 / 3 / 4 / 4 / 4 / 3](packet-final/live/records/013-openai.json) | [3 / 3 / 3 / 4 / 4 / 4 / 4 / 3](packet-final/live/records/013-anthropic.json) | [4 / 4 / 4 / 4 / 4 / 4 / 4 / 4](packet-final/live/records/013-gemini.json) | 1 |
| [014 answer](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/014/ANSWER.md) · [reasoning](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/014/REASONING.md) | [ABSTAIN](packet-final/live/records/014-openai.json) | [ABSTAIN](packet-final/live/records/014-anthropic.json) | [ABSTAIN](packet-final/live/records/014-gemini.json) | — |
| [015 answer](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/015/ANSWER.md) · [reasoning](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/015/REASONING.md) | [4 / 3 / 3 / 4 / 4 / 4 / 4 / 3](packet-final/live/records/015-openai.json) | [3 / 3 / 3 / 4 / 4 / 3 / 3 / 3](packet-final/live/records/015-anthropic.json) | [4 / 4 / 4 / 4 / 4 / 4 / 4 / 4](packet-final/live/records/015-gemini.json) | 1 |
| [016 answer](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/016/ANSWER.md) · [reasoning](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/016/REASONING.md) | [4 / 3 / 3 / 3 / 3 / 3 / 4 / 3](packet-final/live/records/016-openai.json) | [3 / 3 / 3 / 4 / 4 / 3 / 3 / 3](packet-final/live/records/016-anthropic.json) | [4 / 4 / 4 / 4 / 4 / 4 / 4 / 4](packet-final/live/records/016-gemini.json) | 1 |
| [017 answer](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/017/ANSWER.md) · [reasoning](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/017/REASONING.md) | [3 / 2 / 3 / 3 / 4 / 3 / 4 / 3](packet-final/live/records/017-openai.json) | [INVALID](packet-final/live/records/017-anthropic.json) | [4 / 4 / 4 / 4 / 4 / 4 / 4 / 4](packet-final/live/records/017-gemini.json) | 2 |
| [018 answer](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/018/ANSWER.md) · [reasoning](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/018/REASONING.md) | [4 / 4 / 3 / 4 / 4 / 4 / 4 / 3](packet-final/live/records/018-openai.json) | [3 / 4 / 3 / 4 / 4 / 3 / 4 / 3](packet-final/live/records/018-anthropic.json) | [4 / 4 / 4 / 4 / 4 / 4 / 4 / 4](packet-final/live/records/018-gemini.json) | 1 |
| [019 answer](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/019/ANSWER.md) · [reasoning](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/019/REASONING.md) | [4 / 3 / 4 / 3 / 4 / 4 / 4 / 3](packet-final/live/records/019-openai.json) | [4 / 4 / 3 / 4 / 4 / 4 / 3 / 3](packet-final/live/records/019-anthropic.json) | [4 / 4 / 4 / 4 / 4 / 4 / 4 / 4](packet-final/live/records/019-gemini.json) | 1 |
| [020 answer](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/020/ANSWER.md) · [reasoning](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/020/REASONING.md) | [4 / 4 / 3 / 3 / 4 / 3 / 4 / 4](packet-final/live/records/020-openai.json) | [4 / 4 / 3 / 4 / 4 / 3 / 3 / 3](packet-final/live/records/020-anthropic.json) | [4 / 4 / 4 / 4 / 4 / 4 / 4 / 4](packet-final/live/records/020-gemini.json) | 1 |
| [021 answer](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/021/ANSWER.md) · [reasoning](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/021/REASONING.md) | [4 / 3 / 2 / 4 / 4 / 4 / 4 / 3](packet-final/live/records/021-openai.json) | [4 / 4 / 3 / 4 / 4 / 4 / 3 / 3](packet-final/live/records/021-anthropic.json) | [4 / 4 / 4 / 4 / 4 / 4 / 4 / 4](packet-final/live/records/021-gemini.json) | 2 |
| [022 answer](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/022/ANSWER.md) · [reasoning](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/022/REASONING.md) | [4 / 3 / 4 / 4 / 4 / 4 / 4 / 4](packet-final/live/records/022-openai.json) | [4 / 4 / 3 / 4 / 4 / 3 / 3 / 3](packet-final/live/records/022-anthropic.json) | [4 / 4 / 4 / 4 / 4 / 4 / 4 / 4](packet-final/live/records/022-gemini.json) | 1 |
| [023 answer](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/023/ANSWER.md) · [reasoning](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/023/REASONING.md) | [4 / 4 / 4 / 3 / 4 / 3 / 4 / 4](packet-final/live/records/023-openai.json) | [3 / 3 / 3 / 4 / 4 / 4 / 3 / 3](packet-final/live/records/023-anthropic.json) | [4 / 4 / 4 / 4 / 4 / 4 / 4 / 4](packet-final/live/records/023-gemini.json) | 1 |
| [024 answer](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/024/ANSWER.md) · [reasoning](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/024/REASONING.md) | [4 / 4 / 4 / 3 / 4 / 4 / 4 / 3](packet-final/live/records/024-openai.json) | [4 / 3 / 3 / 4 / 4 / 4 / 4 / 3](packet-final/live/records/024-anthropic.json) | [4 / 4 / 4 / 4 / 4 / 4 / 4 / 4](packet-final/live/records/024-gemini.json) | 1 |
| [025 answer](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/025/ANSWER.md) · [reasoning](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/025/REASONING.md) | [4 / 3 / 3 / 3 / 4 / 3 / 4 / 3](packet-final/live/records/025-openai.json) | [3 / 2 / 3 / 4 / 4 / 4 / 3 / 3](packet-final/live/records/025-anthropic.json) | [4 / 4 / 4 / 4 / 4 / 4 / 4 / 4](packet-final/live/records/025-gemini.json) | 2 |
| [026 answer](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/026/ANSWER.md) · [reasoning](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/026/REASONING.md) | [4 / 3 / 3 / 3 / 3 / 3 / 4 / 4](packet-final/live/records/026-openai.json) | [4 / 3 / 4 / 4 / 4 / 3 / 3 / 3](packet-final/live/records/026-anthropic.json) | [4 / 4 / 4 / 4 / 4 / 4 / 4 / 4](packet-final/live/records/026-gemini.json) | 1 |
| [027 answer](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/027/ANSWER.md) · [reasoning](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/027/REASONING.md) | [4 / 3 / 2 / 4 / 4 / 4 / 4 / 3](packet-final/live/records/027-openai.json) | [3 / 3 / 3 / 4 / 4 / 3 / 2 / 3](packet-final/live/records/027-anthropic.json) | [4 / 4 / 4 / 4 / 4 / 4 / 4 / 4](packet-final/live/records/027-gemini.json) | 2 |
| [028 answer](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/028/ANSWER.md) · [reasoning](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/028/REASONING.md) | [4 / 4 / 3 / 3 / 4 / 4 / 3 / 4](packet-final/live/records/028-openai.json) | [3 / 3 / 3 / 4 / 4 / 3 / 2 / 3](packet-final/live/records/028-anthropic.json) | [4 / 4 / 4 / 4 / 4 / 4 / 4 / 4](packet-final/live/records/028-gemini.json) | 2 |
| [029 answer](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/029/ANSWER.md) · [reasoning](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/029/REASONING.md) | [4 / 4 / 4 / 3 / 4 / 3 / 4 / 4](packet-final/live/records/029-openai.json) | [3 / 3 / 3 / 4 / 4 / 4 / 3 / 3](packet-final/live/records/029-anthropic.json) | [4 / 4 / 4 / 4 / 4 / 4 / 4 / 4](packet-final/live/records/029-gemini.json) | 1 |
| [030 answer](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/030/ANSWER.md) · [reasoning](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/030/REASONING.md) | [4 / 3 / 3 / 4 / 4 / 4 / 4 / 4](packet-final/live/records/030-openai.json) | [3 / 3 / 3 / 4 / 4 / 4 / 3 / 3](packet-final/live/records/030-anthropic.json) | [4 / 4 / 4 / 4 / 4 / 4 / 4 / 4](packet-final/live/records/030-gemini.json) | 1 |

## Material disagreement and critical flags

**9 of 29 accepted-answer cases** have a spread of at least two points on one rubric among available valid judges. This is disagreement, not an adjudicated error rate. A single judgment per answer and seat cannot establish repeatability for this new framing.

| Case | Largest spread | Rubrics with spread ≥2 |
| --- | ---: | --- |
| 001 | 3 | routing, required_details, clarity |
| 005 | 2 | required_details |
| 007 | 3 | routing, required_details |
| 012 | 2 | clarity |
| 017 | 2 | routing |
| 021 | 2 | required_details |
| 025 | 2 | routing |
| 027 | 2 | required_details, escalation |
| 028 | 2 | escalation |

Substantive critical-failure entries on scored answers: **0**. This is what these judges reported, not proof that all answers are safe or correct.

Critical-failure entries on abstaining/unassessable answers: **1**.

- [014-gemini](packet-final/live/records/014-gemini.json): No accepted model output was generated (candidate is null; status failed with invalid_model_output). This classifies output availability, not a scored business-answer failure.

See the independent, nonexhaustive [evidence spot-check](SPOT-CHECK.md): it examines structured-target/prose differences, `none` plus `completed`, and a concrete false-positive in the Anthropic case-025 explanation. No grades were corrected or replaced. The spot-check illustrates why judge prose is evidence to inspect, not ground truth.

## Cost and retained evidence

| Seat | Full retained reservation (USD) | Reported-usage cost estimate (USD) | Usage records |
| --- | ---: | ---: | ---: |
| OpenAI | 3.65237800 | 0.46079000 | 30 / 30 |
| Anthropic | 3.65237800 | 0.67012400 | 30 / 30 |
| Gemini | 1.36964175 | 0.24043425 | 30 / 30 |

Total reported-usage cost estimate: **USD 1.37134825**. Total retained conservative reservation: **USD 8.67439775**, below USD 25 per model. Usage estimates use the frozen configured token rates, not provider invoices; reservations are not actual billing and failed requests are not refunded by the admission ledger.

Canonical evidence: [frozen manifest](packet-final/manifest.json), [schedule](packet-final/schedule.json), [summary](packet-final/live/summary.json), [all receipts](packet-final/live/results.json), [budget ledger](packet-final/live/budget.jsonl), and [request/intent/response trace hashes](TRACE_MANIFEST.json). All four originals per case and effective prompts remain frozen. Original-byte, code and artifact checks passed at run completion.

Evidence scope: original model-visible extracted text, not independent inspection of raw image/PDF pixels, OCR confidence metadata or physical outcomes. See [INVENTORY.md](INVENTORY.md). No paid follow-up, answer repair, production action, or claim of human acceptance is included.
