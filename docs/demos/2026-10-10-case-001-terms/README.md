# Main mobile demo — Case 001: changed delivery terms

Status: **source and 50-second storyboard prepared; scripted HTTP/PostgreSQL backend replay implemented; recording and model-driven E2E not yet produced for this case.**

## Implemented backend replay

The [coordination API contract](../../api/delivery-terms-coordination-v1.md) implements cancellation, replacement terms, source-bound consent, booking request and correlated local confirmation. Run `python -m tools.dwelly_platform.terms_demo --base-url http://127.0.0.1:8105 --case-id terms-demo-fresh --anchor-date 2026-10-10` against a migrated local platform with a fresh case ID. The chosen anchor must leave the offered slot in the future.

This derivative retains all 11 source message IDs and adds one labelled context event, seven atomic command audits and two explicitly synthetic, correlated Dispatch readbacks. It is a **scripted local-operator backend check**, not a live model decision or a genuine carrier interaction. Unknown original charge/handover facts are preserved; offered no-charge terms do not invent a currency. The runner rejects inconsistent final database readback. A model-driven mobile UI recording remains separate work.

## Frozen source

- [Original source on GitHub](https://github.com/nikb-de/proofkey-dwelly/blob/15ec6c7faa1d48b0bd6ac9093936d2cc8f69a53c/docs/dataset-drafts/2026-10-10-decision-episodes/examples/case-001-terms.json)
- [Exact local copy](source.case-001-terms.json), from commit `15ec6c7faa1d48b0bd6ac9093936d2cc8f69a53c`.
- SHA-256: `fc1f55e8258346b53f77b5cce03ae6fb7e0b227433daab19894caa4da8d160cf`.
- Format: `case-step-viewer/1.0`; 11 events and 12 visible cutoffs including the initial state.
- The `state_after` values and explanatory text are authored reference states, **not model predictions or execution receipts**.

## Story and success boundary

Vessa cannot attend her original delivery. Iona coordinates with Dispatch, which owns cancellation and booking. After confirmed cancellation, Vessa requests an evening window and concierge handover. Dispatch cannot provide either; it offers a different day, recipient present, no charge. Vessa explicitly accepts those new terms. Only Dispatch's final confirmation completes the coordination goal.

Final screen: **Booking confirmed. Delivery still pending.**

Do not show a delivered parcel, invented photo, fabricated ASR, payment, or real outbound message. This source contains text messages only. Preserve the original February 2026 timestamps for historical replay. A future-dated sandbox derivative must be separately labelled and record its exact date transformation; it must not overwrite this source.

## 50-second mobile storyboard

Target: portrait 390 × 844 viewport; English interface and captions. Time compression must be labelled: the source covers 81 minutes, not a 50-second autonomous resolution.

| Video time | Source events | Visible moment | State/evidence condition |
|---|---|---|---|
| 00–07 | 001 | Customer cannot attend; original booking context | `ready`; no cancellation claimed |
| 07–15 | 002–003 | Cancellation request, then Dispatch confirmation | `waiting → ready`; no slot reserved |
| 15–23 | 004–006 | Customer requests evening delivery and concierge fallback; request sent to Dispatch | `waiting → ready → waiting` |
| 23–32 | 007–008 | Dispatch's different date, recipient present, no charge; ask customer to accept | `ready → waiting`; no automatic acceptance |
| 32–40 | 009–010 | Customer accepts exact terms; booking request sent | `ready → waiting`; not booked yet |
| 40–47 | 011 | Dispatch confirms accepted booking | `completed`, supported by event 011 |
| 47–50 | 011 | End card / source-bound audit result | Booking confirmed; physical delivery pending |

Short English narration (optional):

> A customer cannot attend her delivery. The agent first asks Dispatch to cancel the old booking and waits for confirmation. She requests an evening slot and concierge handover. Dispatch cannot offer either: the available window is Friday morning, the customer must be present, and there is no charge. The agent explains every changed term and asks for explicit agreement. Only after she accepts does it request the booking. Sending that request is not success. The case closes when Dispatch confirms the reservation. The delivery itself is still pending. Every decision links back to the evidence available at that step.

## Two distinct recording claims

1. **Scenario replay:** the existing step viewer can render the authored snapshots. Label it `Scenario replay · authored states · no live actions`. This does not prove LLM or operational E2E behavior.
2. **Platform E2E:** the preferred final demonstration must show source ingestion, actual model proposals, deterministic authorization, explicit customer acceptance, sandbox Dispatch effect/readback and final evidence. Label sandbox connectors; do not replace actual model output with reference states.

No recording or live model invocation was made during preparation of this packet.

## Required platform work before an honest full E2E recording

| Gap | Required behavior / verification |
|---|---|
| Source not registered | Register the frozen source as a development/demo case; keep all 12 cutoffs available without future-message leakage. This public demo is not a held-out benchmark. |
| Early context missing in model projection | Supply original shipment/booking facts as source-bound case context. The original actor list lacks Dispatch before event 002: either supply a separately declared, provenance-labelled directory in a derived fixture or require operator routing. Never leak future actors backwards silently. |
| Authored states vs model output | Keep expected states, explanations, success labels and later messages outside inference inputs. Retain real model response, receipt, model identity and source revision. |
| Cancellation and Dispatch effects absent | Model proposes; deterministic rules admit only current, authorized requests; local pseudo-Dispatch records request and readback separately. No actual carrier connection is required. |
| Terms too narrow | Preserve date/window, handover recipient, presence requirement and price status as a single versioned offer. A material change invalidates previous consent. |
| Customer UI incomplete | Show changed terms and their source; explicit acceptance must bind to the exact offer/revision. Customer acceptance is not carrier confirmation. |
| Historical dates | Inject a fixed scenario clock for historical replay, or produce a disclosed future-dated sandbox derivative. Do not weaken production future-slot validation. |
| Completion conflated | Resolve the coordination goal only after Dispatch confirmation. Physical delivery remains pending. |
| Mobile recording readiness | Run a 390 × 844 browser flow, focus the active case, check overflow and readable terms, capture actual UI interactions, verify final video duration and source-bound receipts. |

## Minimum E2E assertions

- All 11 messages are ingested once, in order, with stable source event IDs.
- Cancellation request 002 alone does not count as cancelled; confirmation 003 does.
- The rejected evening/concierge request is not presented as bookable.
- The different date, recipient-presence requirement and no-charge term survive offer, consent and booking request without omission.
- There is no booking before explicit acceptance 009, and no completion before Dispatch confirmation 011.
- A stale or changed offer cannot reuse prior consent; idempotent replay cannot duplicate an action.
- `completed` refers to the coordination goal, not a completed delivery.
- Backend histories and the visible UI agree; mock/replay data and actual model receipts stay clearly separated.

## Preparation verification

The initial read-only audit found only local sandbox rescheduling. The new coordination API adds the cancellation/negotiation sequence with durable PostgreSQL history and fail-closed preconditions. There is still no connected Dispatch provider; locally configured model credentials do not establish successful inference.

The source passes the current viewer document validator and all 12 current projections. That structural result does not resolve the missing-context or runtime gaps above. Existing source, provider fixes and operational cases were left untouched.
