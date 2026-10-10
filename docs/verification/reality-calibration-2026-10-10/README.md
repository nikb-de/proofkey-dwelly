# Development judge reliability pilot — 10 October 2026

This is a **judge reliability pilot, not human calibration, official Reality Test evidence, model accuracy, or permission to perform an operational action**. It uses the existing pointwise judge prompt and eight 0–4 rubrics without tuning. The controls and their expected directions are assistant-authored development hypotheses awaiting human review.

The live experiment is complete: **108 valid judgments from 108 calls, 105 scored and three abstentions**. See [RESULTS.md](RESULTS.md) for coverage, observed flips, score spread, cost accounting and retained evidence.

## Scope and provenance

The current frozen packet is [packet-v2-current/manifest.json](packet-v2-current/manifest.json). It uses the exact seats in [the current profiles](../../../tools/dwelly_analysis/model-profiles.current.json): OpenAI `gpt-6.1-sol`, Anthropic `claude-sonnet-5-5`, and Google `gemini-3.8-flash`. All are independent API requests, but independence of providers does not establish independence or correctness of their judgments.

An older preparation using the example configuration was superseded before any provider call and is excluded from the published package. It made zero provider calls. Its seats and cost estimates are not part of this experiment; `packet-v2-current` is the only canonical packet.

Only three already exposed public development sources are used: `delivery-logistics-001`, `007`, and `035`. Each supplies a supported-control hypothesis, an ordinary defect, fabricated decisive facts, and an insufficient-context derivative. The latter replaces the first visible event's body with an explicit missing-context statement while preserving the positive candidate bytes. Source hashes, the exact derived snapshots, candidate hashes, prompt hashes and provenance are retained for inspection.

| Source group | Supported control hypothesis | Ordinary defect | Fabricated decisive fact | Insufficient-context check |
|---|---|---|---|---|
| Public 001 | Ask for either exact offered slot | Omit one offered slot | Assert a selection/consent that never occurred | Keep the exact candidate, remove the inventory evidence |
| Public 007 | Request the permitted two-day endpoint | Falsely call that endpoint outside policy | Invent a fee and customer consent | Keep the exact candidate, remove the policy evidence |
| Public 035 | Seek verified refunds routing using the inline receipt | Ask for an already visible receipt as an attachment | Invent refund amount, approval and attachment | Keep the exact candidate, remove the receipt evidence |

The 12 controls are **three source groups**, not 12 independent real cases. Repeating their grades three times does not create 36 independent cases. The ordinary 035 control covers unnecessary attachment requests. A dedicated always-escalate control remains absent; this pilot does not claim comprehensive rubric coverage.

No recorded reference action, later event, full raw history, author label, control label, or producer identity is given to the judge. The same existing `semantic.judge_prompt` builds each payload. The judge receives only the visible snapshot and action. This is pointwise grading: pairwise A/B swapping is not applicable. Request order is randomized with seed `20261010`, and identical prompt hashes are used for all repetitions.

An explicit audit of all 12 serialized prompt files found only `output_format`, `visible_snapshot`, and `proposal` at the payload root, and only `action` inside `proposal`. Candidate rationale, the exact control ID, and `anchor_direction` were absent in all 12. The candidate objects in the offline ledger do contain explanatory rationale; the existing judge prompt strips it before sending. A focused regression test verifies this boundary. Do not infer label leakage from ledger content without inspecting the actual serialized judge payload.

## Existing human-ground-truth status

Inspection found no human-reviewed calibration set:

- The 50 public examples are exposed development data with nonunique recorded next actions. Their prior 142/150 scored judgments are model opinions, as documented in [model release verification](../../model-release-verification.md).
- The canonical [team handoff](../../../datasets/team-handoff-v1/QA.md) has nine assistant-authored, unreviewed snapshots across three synthetic families and **zero eligible reviewed rows**.
- The 16 [case-state widget snapshots](../../../datasets/case-state-widget-v1/development/summary.json) are one related family with `author_labels_unvalidated` references and zero training-eligible rows.
- [Team intake](../../model-team-intake.md) explicitly retains pending human review. No reviewer identity or review date was manufactured for this pilot.

Human review must adjudicate control validity, ambiguity, operational policy and acceptable alternative actions before these scores can support an acceptance decision. The supported 035 control deliberately requests internal routing verification because the snapshot does not supply a verified refunds-team endpoint. Its desirability is a policy hypothesis, not a gold label.

## Bounded live protocol

The user-authorized current-model campaign has a separate durable calibration ledger, capped at **USD 25 per provider/model**, and at most **108 requests**: 12 controls × three identical-output grades × three seats. There are **zero proposer calls and zero business effects**. Conservative total reservations for the frozen complete schedule are **USD 8.18061150**: OpenAI USD 3.444468, Anthropic USD 3.444468, and Gemini USD 1.29167550. These are local admission amounts under the configured rates, not a provider invoice or account-wide billing cap.

First run nine canary requests: supported, fabricated-consent and insufficient-context variants of 001 for each seat. Before any result was read, the bounded runner defined the canary gate as:

1. All three seat outputs must satisfy the existing JSON/citation contract and return the exact requested model identity.
2. Supported response: no abstention or critical flag, with `next_action` and `grounding` at least 3, the existing minor-defect/target anchors.
3. Fabricated consent: a critical flag, or `grounding`/`no_fabrication` at most 1.
4. Missing context: explicit abstention or `grounding` at most 2.

All three seats passed this **provisional control-signal gate**. All nine canary requests returned valid judgments and exact requested identities. The missing-context control elicited an OpenAI abstention, while Claude and Gemini scored unsupported facts as failures. This is a difference in grader handling, not proof that either approach is correct. The remaining 99 requests completed using unchanged controls and prompts.

The runner has at most three requests in flight and at most one per seat. It persists reservations and intent before dispatch, retains raw provider responses and errors, never retries an intent, and stops further requests to a seat after HTTP 401/403/404/429, identity mismatch or invalid judgment. Expansion requires the saved canary gate. An unavailable seat stays missing; no model is substituted. Final live counts and metrics are recorded in the phase status files under `packet-v2-current/live/`.

## Metrics and interpretation

The reporter preserves expected attempts, pending/error/invalid/identity-mismatch counts, valid grades, abstentions and scored coverage. It computes, within each exact control and seat:

- Pairwise critical-flag and abstention flips over all valid repeated judgments.
- Pairwise score-vector disagreement over pairs where both grades are non-abstaining.
- Per-rubric max–min range and population standard deviation among non-abstaining grades.

Three valid repetitions yield three within-control pairs. Missing attempts are never zero scores, and abstention scores are ignored. Semantic text differences in critical flags are preserved in raw records; the binary flip metric measures only whether a critical flag exists. There is no invented overall pass/fail threshold, model ranking, confidence interval, accuracy rate or minimum useful improvement claim. This small pilot cannot quantify task effectiveness or statistical power.

## Reproduction and audit commands

Run from the repository root. Preparation is offline and requires a new destination:

```sh
python3 -B docs/verification/reality-calibration-2026-10-10/pilot.py prepare \
  --config tools/dwelly_analysis/model-profiles.current.json \
  --output /tmp/proofkey-judge-pilot-rebuild

python3 -B docs/verification/reality-calibration-2026-10-10/pilot.py report \
  --packet docs/verification/reality-calibration-2026-10-10/packet-v2-current \
  --results docs/verification/reality-calibration-2026-10-10/packet-v2-current/live/results-remaining.json
```

The actual authorized live commands were:

```sh
python3 -B docs/verification/reality-calibration-2026-10-10/run_live.py \
  --packet docs/verification/reality-calibration-2026-10-10/packet-v2-current \
  --phase canary --env-file /Users/nbk/.config/proofkey/provider.env \
  --live --deadline-seconds 360

python3 -B docs/verification/reality-calibration-2026-10-10/run_live.py \
  --packet docs/verification/reality-calibration-2026-10-10/packet-v2-current \
  --phase remaining --env-file /Users/nbk/.config/proofkey/provider.env \
  --live --deadline-seconds 900
```

Completed phases return their saved status rather than dispatch again. Do not create a fresh packet/ledger to bypass this campaign's budget or request cap. Environment values are read privately and never written to the packet. Retained provider outputs and development source excerpts support reproducible inspection under the project's authorized dataset-publication workflow; they do not establish official test provenance or human acceptance.

Verification commands:

```sh
python3 -B -m unittest discover -s docs/verification/reality-calibration-2026-10-10 -p 'test_*.py' -v
python3 -B -m unittest discover -s tools/dwelly_model/tests -v
python3 -B -m unittest discover -s tools/dwelly_cases/tests -v
```

Observed results: **9 new accounting/orchestration tests, 75 existing model-package tests, and 58 existing case-package tests passed**. The two live-orchestration tests use explicitly simulated provider failures; they are not counted as API participation. No production prompt, existing dataset, or official challenge input was edited.
