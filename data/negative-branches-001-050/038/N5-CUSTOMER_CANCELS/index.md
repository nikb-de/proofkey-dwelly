# Case 038-N5: Failed delivery has returned to sender and the customer still wants the order (Customer cancels the approved reshipment)

## Case details

- **Source role:** Sella Nove, customer
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-11 09:00:00 UTC
- **Escalated:** 2026-03-11 10:30:00 UTC
- **Updated:** 2026-03-11 11:15:00 UTC
- **Completed:** 2026-03-11 11:15:00 UTC
- **Primary shipment:** DL-038
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 038, events 001–004 retained; branch CUSTOMER_CANCELS

## Context

DL-038 for TG-038 is back in Tallowmere Goods' stock after a failed delivery and accepted as reshippable; the account team has authenticated Sella Nove's order session with stored destination Apartment 2, 31 Rillstone Walk, Merrow Quay, and a new dispatch needs merchant approval. Sella still wants the order and confirms that destination. This branch diverges after event 004: Customer cancels the approved reshipment.

## Initial request

I bought the same item elsewhere this morning. Please cancel the reshipment of TG-038 and refund me for the order.

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Email Reshipment authorisations to record Sella's stop on DL-038-R, ask that it is not handed to the carrier, and ask what state it is in now.

- **Recipient:** Reshipment authorisations, Tallowmere Goods
- **Channel:** Email
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** RECORD_STOP (workflow sheet F)

## Outcome

The merchant confirms the stop and whether DL-038-R left the warehouse; the refund request is still for the merchant to decide.

## Boundaries and remaining work

Must not: Do not tell Sella a refund is approved or started; cancellation and refund are separate merchant decisions.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
