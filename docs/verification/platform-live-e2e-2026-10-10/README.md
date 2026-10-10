# Platform E2E — live models, UI controls and backend

Date: 2026-10-10. Base commit: `8f6a530f9503e9ae30fbadcaef96033b317fa6ff`, plus the reviewed OpenAI JSON-input fix in this working tree.

## Decision

**Local integration works; model correctness is not release-ready.** Real OpenAI, Anthropic and Gemini requests reached the canonical-case backend. UI controls and PostgreSQL transaction checks passed. The live runs exposed one repaired transport defect, rejected model output, an incomplete provider response, and ambiguous/underspecified state expectations. No carrier, payment or outbound-message service was invoked.

## Results, without mixing verification layers

| Layer | Observed result | Evidence |
|---|---|---|
| Backend | 307 tests + 42 subtests passed, zero failures/skips | [Backend report](backend/REPORT.md), [JUnit](backend/junit.xml) |
| UI | Four browser E2Es passed; 28 targeted tests passed | [UI report and screenshots](ui/README.md) |
| Fix regression | 122 tests + 222 subtests passed; this overlaps other suites and is not an additional independent denominator | [Fix plan and results](../../superpowers/plans/2026-10-10-openai-json-input-envelope.md) |
| Live Claude | 16/16 model responses available; 8/16 cutoffs matched the strict current ledger; 432 operational assertions passed | [Full report](live/anthropic-claude-sonnet-4-6-full/report.md) |
| Live Gemini | 5/16 cutoffs attempted: 3 matched, 1 ledger mismatch, 1 incomplete response; 11 not run after stop | [Full report](live/gemini-2-5-flash-full/report.md) |
| Live OpenAI, after fix | 2/16 cutoffs attempted: 1 ledger mismatch, 1 invalid model output rejected; 14 not run after stop | [Full report](live/openai-gpt-4-1-mini-fixed-full/report.md) |

These are **16 development cutoffs from one logistics family plus a UI-control example**, not 16 independent delivery scenarios. The 51 current team documents / 286 team cutoffs were not run through live models in this experiment. The literal ledger remains unchanged and unvalidated; there is no held-out accuracy claim and no three-judge quality assessment in this run.

## Live attribution and accounting

| Provider | Requested model | Observed model | Backend dispatches, including canaries |
|---|---|---|---:|
| OpenAI | `gpt-4.1-mini` | `gpt-4.1-mini-2025-04-14` on returned responses | 4 |
| Anthropic | `claude-sonnet-4-6` | `claude-sonnet-4-6` | 17 |
| Google | `gemini-2.5-flash` | `gemini-2.5-flash` on returned responses | 6 |

PostgreSQL readback: **27 jobs, 27 dispatch attempts, 25 retained provider responses, 24 accepted candidates**. The other jobs are the original OpenAI HTTP 400, a Gemini `outcome_unknown` after `incomplete_response`, and an OpenAI validation failure with its response retained. Each job has at most one dispatch; automatic retries are zero. No pending jobs remained at the final readback. A failed ledger comparison is distinct from an invalid or unavailable model response.

Two additional, explicit OpenAI diagnostic requests were made outside the platform job ledger: (1) a minimal JSON request succeeded (23 input / 9 output tokens), and (2) reproduction of the original envelope returned HTTP 400. Thus **29 provider HTTP attempts total**, not 27. The diagnostics are not scored cases. Their metadata is in [transport diagnostics](live/transport-diagnostics.json).

All backend jobs used the same database budget scope, `platform-e2e-20261010`, across the server restart. Configured conservative reservations: Claude **$0.741693**, Gemini **$0.0378615**, OpenAI **$0.0186868**; cap **$25 per model**. Reservations are not invoice totals or independently verified billing limits. The two diagnostic requests are not included in these database reservations; incomplete/rejected requests do not establish their billed cost. No budget was reset to continue the experiment.

## What the run discovered

1. **Fixed: OpenAI JSON-mode envelope.** The provider rejected input lacking the word JSON, even though `instructions` requested JSON. The shared OpenAI adapter now prefixes the unchanged evidence with `Return a JSON object.\n`. A regression failed before the change, then passed; other provider envelopes remain unchanged. A fresh live canary returned a valid attributed response and passed the stale/replay probe. See [OpenAI JSON-mode documentation](https://developers.openai.com/api/docs/guides/structured-outputs#json-mode), [original failure](live/openai-gpt-4-1-mini-canary/report.json), and [post-fix canary](live/openai-gpt-4-1-mini-fixed-canary/report.json).
2. **Rejected, not repaired silently: OpenAI state contradiction.** At `case-002:1`, the model returned `state=waiting` together with `next_action.type=request_information`, and acknowledged that contact had not been confirmed. This violates the local state/action contract. The backend retained the response, returned `invalid_model_output`, produced no candidate, and stopped the run. [Exact retained response](live/openai-rejected-response.json).
3. **Stopped safely: Gemini incomplete response.** At `case-002:4`, the transport reported `incomplete_response`. The job remained `outcome_unknown`; no retry or candidate was created. The current receipt does not retain a detailed finish reason, so token exhaustion is a hypothesis, not an established cause.
4. **Ledger ambiguity at empty-correspondence cutoffs.** The input still includes a goal and actors as internal evidence. A proposed, unsent clarification request is defensible; `unknown/operator_review` is not uniquely forced by current instructions. Original failed scores are retained. No expectation was broadened to make a model pass.
5. **State semantics missing from the model prompt.** Claude selected `acting` for five cutoffs whose documented state semantics require actual in-progress execution, not a proposed action. The evaluator expects `ready`, but the prompt enumerates states without defining this distinction. One further target mismatch selects `correction_form` rather than `address_desk`, while the input lacks explicit readback capability mapping. [Independent code/data adjudication](adjudication.md).

## Verified controls

- Live results retain case/revision/snapshot/input/profile binding and real provider request IDs.
- Replaying the same request returns the existing job without another dispatch.
- Later evidence marks the old result stale; an old revision with a new key is rejected.
- UI reload preserves jobs and does not submit another run; current and stale live receipts match backend state.
- Photo and audio controls validate real PNG/WAV files, keep derived analysis separate from file storage, and require explicit adoption. Their providers were **test doubles**, not live image/ASR services.
- Communication import, quarantine, retry and dedup controls were exercised locally. No real email or phone connector was used.
- Sandbox rescheduling, approval, concurrency and rollback were verified without external carrier effects. Model analysis creates no approvals, actions or operational receipts by itself.

## Retained evidence and next gates

`live/` contains compact copies of all seven immutable run reports, preflights and completed replay/stale probes. The original per-cutoff and HTTP exchanges remain in `outputs/platform-live-e2e-2026-10-10/`. Known provider credential values were scanned against both artifact trees with zero matches before consolidation. No secret value is embedded in these reports.

Next: define and version `ready` versus `acting` in the prompt and rubric; independently adjudicate initial-context and readback-routing policy; add provider schema/consistency tests using the rejected response; investigate Gemini completion limits without automatic retry; then run a new explicitly versioned experiment, including the team's broader case families. Do not overwrite this baseline or call it production-ready.

The local inspection server is on `http://127.0.0.1:8105/`; its database and budget scope are retained. The older server on 8095 was not modified. This is a local operator sandbox, not a deployed authenticated service. Clicking a model-run control can make another paid request within the retained scope.

The earlier unrelated full runtime suite was explicitly interrupted: 782 tests and 906 subtests passed before interruption, exit 2. It is **not** a full-suite pass.
