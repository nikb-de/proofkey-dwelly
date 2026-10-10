# Case 035-N5: Merchant has received the return but the refund review has not started (Customer wants the item back instead)

## Case details

- **Source role:** Melli Orven, customer
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-08 09:00:00 UTC
- **Escalated:** 2026-03-08 09:45:00 UTC
- **Updated:** 2026-03-08 10:30:00 UTC
- **Completed:** 2026-03-08 10:30:00 UTC
- **Primary task reference:** TG-035
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 035, events 001–003 retained; branch CUSTOMER_CANCELS

## Context

Tallowmere Goods' warehouse issued inline receipt WH-035 for return RT-035 / TG-035 at 08:10 UTC, but its receiving role does not approve refunds and no refund review exists. Melli Orven asks the desk to pass the receipt to the team that handles refunds. This branch diverges after event 003: Customer wants the item back instead.

## Initial request

I have changed my mind. I would rather have the item back than a refund. Please stop the refund review for TG-035.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Email the Refunds team to record Melli's stop on the review request for TG-035, ask it to register nothing further, and ask whether a review was already opened.

- **Recipient:** Refunds team, Tallowmere Goods
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** RECORD_STOP (workflow sheet F)

## Outcome

The Refunds team confirms the stop and the state of any review; the item is still with Tallowmere, and sending it back is a separate request for the merchant.

## Boundaries and remaining work

Must not: Do not ask the warehouse to send the item back to Melli; returning a received item is a new merchant decision, not part of the stop.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
