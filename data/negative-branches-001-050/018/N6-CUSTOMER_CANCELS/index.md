# Case 018-N6: Shipment is approaching its return-to-sender deadline (Recipient withdraws choice, wants money back)

## Case details

- **Source role:** Nalo Vere, recipient
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-19 09:00:00 UTC
- **Escalated:** 2026-02-19 10:20:00 UTC
- **Updated:** 2026-02-19 11:00:00 UTC
- **Completed:** 2026-02-19 11:00:00 UTC
- **Primary shipment:** DL-018
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 018, events 001–004 retained; branch CUSTOMER_CANCELS

## Context

The Exception desk reports that DL-018 enters return-to-sender processing at 16:00 UTC on 2026-02-19 unless the customer selects redelivery or depot collection on 2026-02-20, both currently available. No choice is recorded, and the desk asks Iona to contact authorised recipient Nalo Vere before the cutoff. This branch diverges after event 004: Recipient withdraws choice, wants money back.

## Initial request

I've changed my mind. Don't arrange the collection. Let it go back to the sender; I will ask the seller for my money back.

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Record Nalo's stop with the Exception desk in Dispatch chat, forbid any new action on DL-018, and ask whether the collection choice had already been applied and what the return status now shows.

- **Recipient:** Exception desk, Plover Arc Logistics
- **Channel:** Dispatch chat
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** RECORD_STOP (workflow sheet F)

## Outcome

The Exception desk reports the actual state of DL-018; the return, any refund from the seller and collection remain separate matters.

## Boundaries and remaining work

Must not: Do not tell Nalo that a return means a refund, and do not ask the Exception desk to reinstate a return its records may already have cancelled.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
