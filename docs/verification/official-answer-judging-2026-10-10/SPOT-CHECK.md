# Non-exhaustive evidence spot-check

This companion distinguishes observations about the exact published answer from opinions in the retained judge records. It is **not** a corrected answer set, exhaustive review, human calibration, official correctness verdict, or permission to replace submissions. No grades or original answers were changed.

## 1. Structured target versus prose destination

| Case | Observed difference in the submitted candidate | Judge treatment and evidentiary limit |
| --- | --- | --- |
| [001 answer](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/001/ANSWER.md) | `propose_forwarding` targets `actor-01` (dispatch register), while the prose says to forward to the sender account `routing@opaline.example`. The candidate itself acknowledges that the sender is not a visible actor and that the register was chosen as the nearest available actor. | [Anthropic](packet-final/live/records/001-anthropic.json) and [OpenAI](packet-final/live/records/001-openai.json) treat this as routing ambiguity; [Gemini](packet-final/live/records/001-gemini.json) accepts the documented proxy and scores all dimensions 4. E01/E05 contain the stored sender channel, E02 requires sender-controlled approval, and E04/E06 contain the reroute request. The representation difference is observable; whether the proxy is operationally acceptable is not established by any executed forwarding. |
| [007 answer](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/007/ANSWER.md) | `propose_forwarding` targets `actor-04` (operations), while the prose refers to the locker operations/team. The candidate explicitly says the locker team is absent from the actor roster and operations is the closest visible target. | [Anthropic](packet-final/live/records/007-anthropic.json) and [OpenAI](packet-final/live/records/007-openai.json) identify routing/completeness limitations; [Gemini](packet-final/live/records/007-gemini.json) accepts operations and gives all 4s. E01 supplies the locker contact and identifiers, E02 assigns corrections to the locker team, and E03/E05 record failed deposit/null compartment. This is a disclosed proxy mapping, not proof of a misdirected message. |
| [025 answer](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/025/ANSWER.md) | `propose_forwarding` targets `actor-02` (the escalation desk), but the prose begins with a reply to Lyra Fen (`actor-05`) and separately describes routing a payout request to billing. | [Anthropic](packet-final/live/records/025-anthropic.json) calls out the mixed target/action. [Gemini](packet-final/live/records/025-gemini.json) accepts the response and gives all 4s. E01 supplies the billing address; E02/E03/E05 establish the offset and separate payout-authorisation boundary. The structured target does not name either prose recipient, but no actual dispatch occurred. |

The cross-field differences above are concrete. Calling them harmful misrouting would go beyond the evidence, because the published run executed no business operations and some candidates expressly disclose the actor-roster limitation.

## 2. `none` plus `completed`: correct analysis versus unfinished communication

| Case | Observed evidence | What the judges say |
| --- | --- | --- |
| [011 answer](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/011/ANSWER.md) | State is `completed`, action is `none`, target is null. The time conversion is 10:20+02:00 = 09:20+01:00, before the 10:00+01:00 deadline (E02/E03). The latest customer request is E06; retained uncertainty says no customer notification is recorded. | [OpenAI](packet-final/live/records/011-openai.json), [Anthropic](packet-final/live/records/011-anthropic.json), and [Gemini](packet-final/live/records/011-gemini.json) all accept the substantive calculation but criticize the absent next contact. None reports a critical failure. |
| [012 answer](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/012/ANSWER.md) | State is `completed`, action is `none`, target is null. E02/E03 support 12 kg dimensional weight per carton, 24 kg total at GBP 2/kg, matching GBP 48. E06 asks for charge correction; retained uncertainty says no reply is visible. | [OpenAI](packet-final/live/records/012-openai.json), [Anthropic](packet-final/live/records/012-anthropic.json), and [Gemini](packet-final/live/records/012-gemini.json) accept the calculation but criticize leaving the request without a routed response. None reports a critical failure. |

`completed` is a model-inferred coordination state, not a claim that the host sent a reply or performed an adjustment. The relevant review question is whether `none` is adequate for the declared goal; the absence of a sent message is explicit, not a concealed operational success.

## 3. Concrete evaluator false-positive: case 025 balance wording

The [Anthropic case 025 judgment](packet-final/live/records/025-anthropic.json) says: “The message also does not state that the credit reduced her balance”. It immediately describes the GBP 90 amount as missing from the message's account of the customer's obligation.

But the [exact published candidate](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/025/ANSWER.md) explicitly says CN-025 was applied as an **unpaid-invoice offset** and that **“INV-025 shows GBP 90 still due”**. The retained [source result](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/025/SOURCE_RESULT.json) contains the same wording, supported by ledger E03 and billing E05 in the [original input](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/025/INPUT.json).

Therefore the alleged omission of the remaining balance is contradicted by the submitted text. This does not invalidate every part of that judgment: its separate structured-target/prose-recipient observation remains visible. No score has been repaired or reinterpreted as a new grade.

## 4. Availability is not substantive correctness

Case [014](https://github.com/nikb-de/proofkey-dwelly/blob/cebf1b2b9520bcae260f1b8c2a50443490f97969/ANSWERS/014/ANSWER.md) has no accepted candidate. All three retained judges abstain: [OpenAI](packet-final/live/records/014-openai.json), [Anthropic](packet-final/live/records/014-anthropic.json), [Gemini](packet-final/live/records/014-gemini.json). Gemini additionally places the missing-output condition in `critical_failures`; the other two do not. That is a real reporting disagreement about failure classification, not a scored substantive answer. Required zero placeholders must be excluded from rubric means, while the original failure remains visible in the full 30-case denominator.

These examples demonstrate why the judges' explanations are evidence to inspect, not ground truth. Their findings, disagreements, abstentions and malformed outputs remain part of the retained assessment, with no claim of calibration or official scoring.
