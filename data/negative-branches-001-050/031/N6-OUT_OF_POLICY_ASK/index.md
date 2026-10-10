# Case 031-N6: Return approved but the customer has no return label (Customer asks to count label as return)

## Case details

- **Source role:** Kessa Ulm, customer
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-04 09:00:00 UTC
- **Escalated:** 2026-03-04 10:00:00 UTC
- **Updated:** 2026-03-04 10:40:00 UTC
- **Completed:** 2026-03-04 10:40:00 UTC
- **Primary shipment:** DL-031
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 031, events 001–004 retained; branch OUT_OF_POLICY_ASK

## Context

Tallowmere Goods approved return RT-031 for TG-031 / DL-031, but the label field is empty and only its authorised label team can issue the label. Kessa Ulm asks the desk to obtain the printable return label. This branch diverges after event 004: Customer asks to count label as return.

## Initial request

I have RL-031 now. I will not get to a drop-off until next week. Can you mark the return as received today so my refund starts now?

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Reply to Kessa in the Customer portal that the desk cannot record a return as received or start a refund, that RL-031 only lets the parcel be prepared under RT-031, and that receipt and refund follow from the merchant once the parcel goes by the approved drop-off route.

- **Recipient:** Kessa Ulm, customer
- **Channel:** Customer portal
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** DECLINE_EXPLAIN (workflow sheet A)

## Outcome

Kessa acknowledges and the parcel is still with Kessa; nothing about drop-off, merchant receipt or refund is established.

## Boundaries and remaining work

Must not: Do not record receipt, ask Tallowmere to start a refund, or suggest a refund date; a printed label is not a return.

## History

[Read the complete dated history](history.md).

## Attachments

- [return-label.pdf](attachments/return-label.pdf)
