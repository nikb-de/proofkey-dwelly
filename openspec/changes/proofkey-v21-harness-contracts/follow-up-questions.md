# Ten additional design questions — Drive workflow v3

Status: nine choices confirmed by the user's numbered reply on 8 October 2026; question 5 needs clarification of “давай без”. The earlier 18 answers remain recorded in decisions.md. The original questions below are retained as context; their suggested defaults are not automatically approved where the reply is ambiguous. The resulting written design still requires review before the detailed implementation plan and product coding.

1. **Consent mode:** The new A2 requires exact-slot confirmation, while our earlier decision permits autonomous choice within an authenticated window. Should both be explicit profiles, and which is the main demo mode? Suggested default: authorized-window selection for the main positive profile; exact-slot confirmation when the profile/policy requires it.
2. **Stop/cancel while outcome is unknown:** Does cancel mean no further attempts, or a real cancellation/undo of the order or original operation? Suggested default: persist no-further-business-writes, reconcile the existing attempt and report what happened; no resend or compensating undo without a separate authorized capability.
3. **Early operator help:** May the operator only supply missing facts, or also authorize a change on the customer's behalf? Suggested default: facts return through completeness and current access checks; operator notes are not customer consent. Any delegated authority must be explicit in the profile.
4. **Pre-confirmation recovery:** Should restart resume extraction, clarification and access-check phases, rather than only prepared/dispatch states? Suggested default: restore the saved phase, question, next gate and budgets; revalidate material facts before any effect.
5. **Duplicate completed case:** Should it replay the saved verified result, refresh current status, or create a new request? Suggested default: authenticated saved-result replay without repeat writes/messages; explicit read-only refresh is separate, and genuinely new business intent uses a new authorized generation.
6. **Owner reassignment:** Does the current owner remain responsible until the new owner durably accepts the same case/packet, and what happens to a late old-owner decision? Suggested default: explicit pending transfer, accepted versioned ownership change and rejection of stale decisions; queue ID alone is insufficient.
7. **Waiting and reminders:** Are reminders/reassignment required in the first executable profile or initially described/simulated? What expiry, recipient, cadence and maximum reminder count apply? Suggested default: durable waiting/expiry first; no reminder or transfer effects without bounded profile rules, authorized recipients and receipts. All waits remain on the exercise clock.
8. **Open an internal case:** Is this a recorded operator disposition or a real creation effect in a connected system? If an effect, which of the six ports owns it? Suggested default: record-only initially; propose a separately scoped operator-inbox creation/readback contract if needed, with no financial execution.
9. **Original-evidence retention/access:** Who may read original photos, audio, PDFs and chats, and for how long after team revalidation/case closure? Suggested default: private scoped originals, synthetic/redacted public exports, no automatic publication or deletion; exact retention window needs a decision.
10. **Canonical process artifact:** Is the reviewed ProcessSpec the source of truth, with Draw.io/Figma as versioned explanatory views, or do we maintain a diagram-first workflow? Is native synchronization required now? Suggested default: reviewed ProcessSpec + contract tests is canonical; retain original diagrams and derive explanatory views, with native sync optional.

After answers: update decisions/design/spec deltas and task dependencies, revisit effort/workloads, review the revised written design and then prepare the detailed implementation plan. No recommendations here override financial, authority, safe-retry or publication boundaries.

## Recorded answers and scope

| # | User reply | Recorded consequence |
|---|---|---|
| 1 | “делай первым для демо, оставь оба” | Both consent profiles; authenticated-window agent choice is the main demo, exact-slot customer confirmation is the second mode. |
| 2 | “давай, отказ может быть как следующий шаг” | Persist stop/no-further-business-writes and reconcile the original; refusal may be a separate later authorized request, not an automatic undo or conversion. |
| 3 | “Давай твое предложение” | Operator supplies missing facts; re-enter completeness and current authority checks. Notes do not manufacture customer consent. |
| 4 | “Давай сохранять и продолжать” | Persist/resume pre-confirmation phases, awaited question/fields, next gate, versions and budgets. |
| 5 | “давай без” | **Pending:** what is omitted is not explicit. Asked whether this means saved-result replay without repeated effects/messages or automatic status refresh. Existing duplicate-effect prevention remains mandatory. |
| 6 | “да” | Old owner remains accountable until durable new-owner acceptance of the same case/packet; versioned ownership change rejects stale decisions. |
| 7 | “давай твое предложение” | Durable waiting/expiry first. Automatic reminders are off by default; transfer/reminder effects need bounded profile rules, scoped authority and independent receipts. No numeric expiry/cadence/maximum was supplied. |
| 8 | “Давай так и сделаем” | Internal-case disposition is record-only initially; actual creation is deferred, with no financial execution. |
| 9 | “Давай так и сделаем” | Private scoped originals, synthetic/redacted public derivatives; no automatic publication/deletion. Exact retention duration is still unknown. |
| 10 | “давай первой, пока интеграция не нужна” | Reviewed ProcessSpec + contract tests canonical; versioned explanatory diagrams. No native Draw.io/Figma synchronization now. The six logistics adapter surfaces remain in scope. |

Question 5 is the only ambiguous numbered answer. Native authority/guarantees, bounded waiting policy values and retention duration remain explicit environment/release gates, not answers inferred from “yes”.
