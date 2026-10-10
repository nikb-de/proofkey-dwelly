# Live model evaluation rerun — 2026-10-10

## Result

Real OpenAI, Anthropic and Gemini requests reached the retained local worker and PostgreSQL ledger. This is **not a model-correctness pass**: 15 provider attempts produced 13 retained responses and 12 accepted candidates. The run found a rejected OpenAI state/action contradiction, incorrect or mismatching coordination states, and two Gemini incomplete responses. No external operational actions were executed.

This rerun used the existing code, prompts, profiles, expectations and author references. No production file, dataset, label, provider setting or budget was changed. The reference quality remains `author_labels_unvalidated`; there is no held-out accuracy or calibrated grader claim.

## Coverage and two evaluation paths

Fresh catalog inspection found **16 legacy cutoffs / 3 documents / 2 catalog families** (one logistics family plus a UI fixture) and **286 team cutoffs / 51 documents / 50 families**. The separate canonical handoff package contains **9 synthetic seed decisions**; those were inventoried but not run.

Six cutoffs were selected per provider before dispatch:

| Path | Selected cutoffs | Purpose |
|---|---|---|
| Canonical platform HTTP | `case-002-n4:6`, `case-002:5`, `case-002-n4:5` | Visible outgoing readback/wait; confirmed coordination completion; unknown form-save result |
| Existing analysis worker | `team-001:4`, `team-003:4`, `team-025:3` | Chosen rescheduling slot; gate-access intent awaiting driver confirmation; merchant replacement approval pending |

The legacy path uses the unchanged `tools.dwelly_e2e` replay, strict state/action/target/wait ledger and canonical-case HTTP routes. Unique `e2e-r2-*` case IDs isolate it from existing user cases. The team path uses unchanged `step_record`, `ModelRuntime.submit/get`, and `evaluation.compare`, with original catalog inputs and references. It shares the active platform worker's **same database schema and budget scope**, but it is not a team-through-canonical-platform/UI test. The existing team comparison checks **state and wait targets only**; action, detail and authority observations are separately reviewed below.

The legacy run stops on invalid/unavailable output. Its stopped reports remain unchanged. OpenAI and Gemini then received the three separately selected team inputs as a distinct bounded batch, without retrying a failed input. A failed team output stops that provider's team batch. There were no direct provider diagnostics, extra canaries or provider retries.

| Provider | Legacy attempted / selected | Legacy valid / attempted | Strict complete legacy ledger match / valid | Team attempted / selected | Team valid / attempted | Team state agreement / valid | Team wait agreement / valid |
|---|---:|---:|---:|---:|---:|---:|---:|
| OpenAI | 2/3 | 1/2 | 1/1 | 3/3 | 3/3 | 1/3 | 2/3 |
| Anthropic | 3/3 | 3/3 | 2/3 | 3/3 | 3/3 | 1/3 | 3/3 |
| Gemini | 3/3 | 2/3 | 2/2 | 1/3 | 0/1 | not available | not available |

These denominators are intentionally separate. Across 18 selected provider/cutoff pairs, 15 were attempted, 12 accepted, 1 rejected, 2 incomplete and 3 not run. A valid JSON candidate is not a correct decision. The legacy runner's generic coverage string mentions a UI control; **no UI fixture was selected in this rerun**.

On accepted legacy candidates, **exact state agreement and exact action-type agreement are each OpenAI 1/1, Claude 2/3 and Gemini 2/2**. The team author reference stores the next action as prose, not an action-type enum, so there is no existing exact action-type score for that path. Its original exact state/wait scores above and the separate action-quality review must not be merged.

## Findings with retained evidence

1. **OpenAI completion contradiction.** On `case-002:5`, the raw response was syntactically valid JSON but combined `state="ready"` with `next_action.type="none"`. The current parser permits `none` only with `completed`. The worker retained the response and returned `invalid_model_output`, with no accepted candidate. Its description correctly recognised the corrected address and cleared hold, so this is a state/action contract failure, not a failed network call. See [retained job and response](accounting.json), job `ceb9e98dd5ff4239813efdd79d7a098c`.
2. **OpenAI gate-access mistake.** On `team-003:4`, it chose `waiting / wait / driver`, although no request to the driver after the recipient's call is visible. It also wrote “Recipient has released the gate” in `uncertainty`; the source only says the recipient **will** release it. This is an unsupported conversion of intent into a completed event. It did not claim parcel handover or execute anything. See [exact team record](openai-gpt-4-1-mini/team/team-003-4.json).
3. **Ready/acting mismatch recurred on new families.** Both OpenAI and Claude chose `acting` on `team-001:4`, where the author reference is `ready`. Claude also chose `acting` on `team-003:4`; its proposed driver readback is appropriate, but no executed action is visible. The current system prompt enumerates `ready` and `acting` without defining the distinction, as noted in the prior run. That is a plausible contributor, not an experimentally isolated cause. References and scores were not changed. See [OpenAI slot response](openai-gpt-4-1-mini/team/team-001-4.json), [Claude slot response](anthropic-claude-sonnet-4-6/team/team-001-4.json), and [Claude gate response](anthropic-claude-sonnet-4-6/team/team-003-4.json).
4. **Claude unknown-result routing differs from the strict ledger.** On `case-002-n4:5`, Claude selected `unknown / operator_review / null`, while the unchanged ledger requires `ready / request_readback / address_desk`. It recognised that the form may not have saved and explicitly prohibited a repeat before verification. The measured ledger mismatch is retained; this conservative escalation is not evidence of an unsafe repeated operation. See [legacy report](anthropic-claude-sonnet-4-6/report.json).
5. **Gemini completion failures recurred.** `case-002-n4:5` and `team-001:4` each finished `outcome_unknown` with `incomplete_response`. No response text, observed model identity, token usage or provider request ID was retained for those attempts. The configured output maximum was unchanged at 2,048 tokens. Token exhaustion remains a hypothesis: this receipt does not establish the finish reason. No attempt was retried. See [legacy record](gemini-2-5-flash/report.json), [team record](gemini-2-5-flash/team/team-001-4.json), and [database evidence](accounting.json).
6. **Replacement authority was respected in the available team outputs.** OpenAI and Claude both waited for merchant approval on `team-025:3`; neither claimed a replacement order existed, approved it on the merchant's behalf, or inferred shipment/delivery. This is evidence for these two visible outputs only. See the [semantic review](semantic-review.md).

## Operational controls and attribution

- All 15 new jobs have exactly one dispatch and zero automatic retries. All retained candidates declare zero operational effects; legacy cases have no decisions, reviews or actions. Team jobs do not create canonical operational cases or invoke delivery/messaging adapters.
- Three fresh supplemental stale/replay probes passed **36/36 assertions** on each provider's accepted `case-002-n4:6` result: later evidence made the result stale, a new request against the old revision was rejected with `409 revision_conflict`, and the original key returned the identical terminal job with no additional dispatch. See each provider's `control-probe/probe.json`.
- Successful and rejected terminal jobs survived fresh database-backed reads and idempotent replay. This tests retained job persistence, **not process-crash recovery or a service restart**. No service was restarted for this rerun.
- The 27 preexisting jobs were unchanged at final comparison. There are no pending new jobs. The two Gemini jobs remain terminal `outcome_unknown`; that status does not establish whether the provider billed or completed internally.
- All provider calls were made by the already-running local service. The wrapper used the existing runtime's admission interface and loaded credential availability privately; credential values were never printed or stored in these artifacts.

| Provider | Requested model | Observed on retained responses | New dispatches | Retained responses | Accepted candidates |
|---|---|---|---:|---:|---:|
| OpenAI | `gpt-4.1-mini` | `gpt-4.1-mini-2025-04-14` | 5 | 5 | 4 |
| Anthropic | `claude-sonnet-4-6` | `claude-sonnet-4-6` | 6 | 6 | 6 |
| Gemini | `gemini-2.5-flash` | `gemini-2.5-flash` on 2; unavailable on 2 | 4 | 2 | 2 |

## Retained budget

Scope: `platform-e2e-20261010`. Model jobs schema: `proofkey_live_e2e_20261010_models`. Local service: `http://127.0.0.1:8105`. The existing **$25/provider** cap remained in place; the rerun's additional **$3/provider maximum** was never approached and no budget was reset.

| Provider | Reservation before | Added this rerun | Reservation after |
|---|---:|---:|---:|
| OpenAI | $0.0186868 | $0.0258192 | $0.0445060 |
| Anthropic | $0.741693 | $0.270771 | $1.012464 |
| Gemini | $0.0378615 | $0.0265178 | $0.0643793 |

Additional conservative reservations total **$0.323108**. These are configured-price reservations, not invoices or verified provider spend. Usage and real provider request IDs, when available, are retained in [accounting.json](accounting.json). The incomplete Gemini requests have no usage receipt, so actual billed cost is not known.

## Limits and reproducibility

Only 3/286 team cutoffs were selected; OpenAI and Claude attempted all three, Gemini one. Remaining team families/cutoffs, all nine canonical handoff seed decisions, live media/ASR, authentication, external carriers/messages/payments, and end-to-end team UI import were not tested. There is no training, independent human calibration, repeated grading, model ranking, or production-readiness certification.

[inventory.json](inventory.json) retains original selections, references, source hashes, profile availability and maximum reservation estimates. [database-before.json](database-before.json), [database-after.json](database-after.json) and [accounting.json](accounting.json) bind final accounting to the original shared ledger. The wrapper [rerun.py](rerun.py) invokes the existing harness/worker; its run commands intentionally refuse existing output directories. Running it again is a paid action and is not required to inspect this result.

One wrapper preflight failed before dispatch because saved evidence redacts `api_key_env` field values (environment variable names), while the comparison used the unsanitized in-memory config. Exact reproduction showed unchanged buckets and 27 unchanged jobs. The wrapper comparison was corrected to compare equally redacted objects; no provider request or production change resulted from that initial failure.
