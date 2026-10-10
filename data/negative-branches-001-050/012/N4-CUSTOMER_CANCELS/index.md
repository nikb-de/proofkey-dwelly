# Case 012-N4: Promised delivery day missed after vehicle breakdown (Recipient withdraws the rebooking request)

## Case details

- **Source role:** Fenn Azel, recipient
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-13 09:00:00 UTC
- **Escalated:** 2026-02-13 09:40:00 UTC
- **Updated:** 2026-02-13 10:20:00 UTC
- **Completed:** 2026-02-13 10:20:00 UTC
- **Primary shipment:** DL-012
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 012, events 001–003 retained; branch CUSTOMER_CANCELS

## Context

Dispatch confirms that vehicle fault V-12 ended DL-012's route at 08:20 UTC on 2026-02-12, so the 08:00–09:00 window was missed and the parcel is back in depot custody. Fenn Azel, the recipient, asks for a replacement slot and is free on the afternoon of 2026-02-14. This branch diverges after event 003: Recipient withdraws the rebooking request.

## Initial request

Please stop the rebooking for DL-012. I have asked the seller to cancel the order and refund me. I do not want another delivery attempt.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Record the stop with Dispatch by email, forbid any new booking for DL-012, and ask what had already been reserved or sent to Fenn before the stop.

- **Recipient:** Dispatch, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** RECORD_STOP (workflow sheet F)

## Outcome

Dispatch confirms the stop and reports the actual state of DL-012; this does not cancel the order, start a return or establish a refund.

## Boundaries and remaining work

Must not: Do not request a return to sender or promise Fenn a refund; the seller owns the cancellation and refund, and a return is a separate step.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
