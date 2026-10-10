# Case 035-N4: Merchant has received the return but the refund review has not started (Customer asks to confirm amount and approval)

## Case details

- **Source role:** Melli Orven, customer
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-08 09:00:00 UTC
- **Escalated:** 2026-03-08 10:10:00 UTC
- **Updated:** 2026-03-08 11:00:00 UTC
- **Completed:** 2026-03-08 11:00:00 UTC
- **Primary task reference:** TG-035
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 035, events 001–004 retained; branch OUT_OF_POLICY_ASK

## Context

Tallowmere Goods' warehouse issued inline receipt WH-035 for return RT-035 / TG-035 at 08:10 UTC, but its receiving role does not approve refunds and no refund review exists. Melli Orven asks the desk to pass the receipt to the team that handles refunds. This branch diverges after event 004: Customer asks to confirm amount and approval.

## Initial request

I can see RF-035 now. My bank needs written confirmation. Please confirm the refund of GBP 89.00 is approved and will be paid this week.

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Reply to Melli in the Customer portal that RF-035 is registered with WH-035, that the Refunds team has not decided eligibility, amount or payment, and that its next update is due by 2026-03-10, 16:00 UTC.

- **Recipient:** Melli Orven, customer
- **Channel:** Customer portal
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** DECLINE_EXPLAIN (workflow sheet A)

## Outcome

Melli acknowledges the registered status and update date; nothing about eligibility, amount or payment is established.

## Boundaries and remaining work

Must not: Do not confirm GBP 89.00, an approval or a payment week, and do not ask the Refunds team to decide early.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
