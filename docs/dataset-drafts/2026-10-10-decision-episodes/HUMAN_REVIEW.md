# Review queue and expansion plan

## Review before these become references

| Decision | Question for the workflow/policy owner |
|---|---|
| Damage evidence | Is a readable photo mandatory, optional, or impossible for this claim category? What alternatives are accepted? |
| Inline warehouse confirmation | Is a verified warehouse message enough to open review, and what is required before payment? |
| Refund authority | Who may approve, within what limits, for which exact amount/currency/case revision? |
| Rescheduling | Can a customer choose an offered slot without operator approval? Which fees, address changes or deadlines alter that? |
| Refusal | Does refusal of current slots mean propose more, keep existing booking, or ask dispatch? Never infer cancellation. |
| Timeout | How many attempts, on which channel, after what duration, then which fallback? |
| Evidence conflict | Who is authoritative for physical receipt versus refund eligibility? |
| Monitoring | Who watches an automatic effect, with what response window and ability to stop/recover it? |
| Readback | Which system is authoritative for a completed booking/payment? Does it expose durable operation IDs? |
| Identity | How are actors bound to this case and how are permissions checked? |
| Sensitive inputs | What must be redacted, and what evidence retention is permitted? |
| Risk/safety | What requires immediate human escalation, independent of completeness? |

All policies in the seed fixtures are synthetic assumptions to make examples decidable. Changing them may change the labels. Photo evidence does not establish liability by itself.

## For each existing source case

Record source ID and lawful-use provenance; cutoff before curator action; curator contribution; facts already visible; missing evidence; missing authority; affected parties; allowed actions; prohibited effects; risk; authoritative readback; ambiguities; proposed variants.

Do not copy future resolution into agent input. Do not treat the historical resolution or an LLM label as verified truth.

## Expansion

1. Audit the 50 existing known cases for intervention types (not completed by this package).
2. Choose 12 priority independent families and author 5 useful variants each; total target 60 decision points.
3. Include refusal, contradiction, timeout, unverified actor, missing policy and urgent-risk coverage; seed examples do not cover every category.
4. Team supplies 10–20 genuinely independent real/realistic cases, redacted and authorised for use.
5. Group related cases before assigning splits. Decide allocation before tuning; record family IDs and a seed.
6. Review labels; promote individual reviewed records with reviewer ID/time and rationale. Preserve uncertain records as ambiguous or exclude with a reason.
7. Run frozen controls and calibrate judges before reporting model improvements.

## Known limitations

- 3 synthetic families only; correlated decisions are not independent samples.
- All current rows are development; no sealed test set exists.
- No real images/audio, only synthetic message text and one explicitly simulated media extraction.
- No runtime adapter, transition matcher, deployed gate, training run or external integration.
- No actual API generation or judge receipts.
- Safety escalation, unknown policy, identity spoofing and multilingual variation are requirements for expansion, not proven current coverage.
