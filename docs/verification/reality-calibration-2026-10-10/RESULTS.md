# Judge reliability pilot results — 10 October 2026

The bounded pilot completed **108/108 requested API calls**, with **108 valid judgments, 105 scored judgments, and three abstentions**. There were zero missing responses, invalid judgments, transport errors, substitutions, retries, proposer calls, or business effects. All returned model identities exactly matched the requested current profiles.

This is an **unqualified development judge reliability pilot**, not human calibration, official Reality Test evidence, task accuracy, or a release decision. It has 12 assistant-authored controls from **three source groups**; three repetitions per control are repeated measurements, not independent cases. The original prompt, eight 0–4 rubrics, frozen inputs and declared control directions were unchanged throughout the live experiment.

| Requested and observed model | Valid / planned | Scored / planned | Abstentions | Critical-flag flips | Score-vector flips | Largest rubric range |
|---|---:|---:|---:|---:|---:|---:|
| `gpt-6.1-sol` | 36/36 | 33/36 (91.7%) | 3 | 0/36 (0%) | 15/33 (45.5%) | 2 points |
| `claude-sonnet-5-5` | 36/36 | 36/36 (100%) | 0 | 2/36 (5.6%) | 17/36 (47.2%) | 1 point |
| `gemini-3.8-flash` | 36/36 | 36/36 (100%) | 0 | 2/36 (5.6%) | 20/36 (55.6%) | 1 point |

Each flip denominator is the number of within-control pairs of valid repeated judgments; three repeats create three pairs. Score-vector comparison excludes a pair when either judgment abstains. Each OpenAI abstention was on the same insufficient-context control, so abstention-flip rate was 0/36 for every seat. The rubric range is max–min for the same control and dimension across non-abstaining repeats. Per-control population standard deviations and all dimensions remain in the [full status record](packet-v2-current/live/status-remaining.json). These figures do not rank model quality.

## Control signal and observed disagreement

Across the 27 supported-control judgments, `next_action` and `grounding` were each 3–4, with no critical flags or abstentions. Across the 27 deliberately fabricated-control judgments, every judge flagged a critical failure, with `grounding` 0–1. Across the 27 insufficient-context judgments, three abstained and the remaining 24 flagged unsupported facts; grounding was at most 2. These results show separation for the declared development controls, whose labels still need independent human review.

The ordinary-defect controls exposed differences in severity classification. For the exact same request to upload an already visible warehouse receipt, Claude returned the **same numeric score vector** three times but alternated the critical flag between present, absent, and present. See [repeat 0](packet-v2-current/live/records/dev-035-negative-r0-anthropic.json), [repeat 1](packet-v2-current/live/records/dev-035-negative-r1-anthropic.json), and [repeat 2](packet-v2-current/live/records/dev-035-negative-r2-anthropic.json). For the false claim that a permitted two-day endpoint exceeded policy, Gemini returned a critical flag twice and no critical flag once, along with changed scores. See [repeat 0](packet-v2-current/live/records/dev-007-negative-r0-gemini.json), [repeat 1](packet-v2-current/live/records/dev-007-negative-r1-gemini.json), and [repeat 2](packet-v2-current/live/records/dev-007-negative-r2-gemini.json).

OpenAI consistently abstained on the missing rescheduling-inventory input, while Claude and Gemini consistently scored its unsupported details. An abstention and a low-grounding score represent different grader behavior; neither is silently counted as a successful quality assessment. Human adjudication is needed to choose the desired policy for missing evidence and critical-failure severity before assigning acceptance thresholds.

## Bounds, spend and audit

The first nine calls passed the predeclared canary gate; only then were the remaining 99 dispatched. The runner used at most three concurrent requests, one per seat. The dedicated ledger retained **USD 8.18061150 in conservative reservations**: OpenAI USD 3.444468, Anthropic USD 3.444468, and Gemini USD 1.29167550. Each is below the USD 25 per-model cap. Reservations are admission accounting under configured prices, not a provider invoice. All 108 reservations and outcomes are retained in [calibration-budget.jsonl](packet-v2-current/live/calibration-budget.jsonl).

The frozen [manifest](packet-v2-current/manifest.json), [schedule](packet-v2-current/schedule.json), [canary gate](packet-v2-current/live/canary-gate.json), [canary status](packet-v2-current/live/status-canary.json), [final status](packet-v2-current/live/status-remaining.json), and [all raw result envelopes](packet-v2-current/live/results-remaining.json) retain the evidence. Individual intents and raw provider responses are in `packet-v2-current/live/intents/` and `packet-v2-current/live/records/`.

The [payload audit](payload-boundary-audit.json) inspected all 12 actual serialized judge prompts: only `output_format`, `visible_snapshot`, and `proposal.action` were sent. Control IDs, anchor directions and candidate rationale were absent. The offline ledger's explanatory rationale did not cross the existing judge-prompt boundary. The semantic-source SHA-256 still matched the frozen manifest after the run.

The focused software checks passed: **9 pilot tests, 75 existing model-package tests, and 58 existing case-package tests**. The two orchestration tests use simulated transport failures and contribute zero live observations. Commands, source provenance, limitations and the exact reproduction procedure are in [README.md](README.md).

No official challenge data was used to construct, tune or grade these controls. No human reviewer has accepted the control labels, no held-out comparison was run, no minimum useful improvement was established, and there is no claim of statistical power from three source groups. The result permits reporting actual repeatability, coverage and control separation; it does not qualify an automated grader or establish production readiness.
