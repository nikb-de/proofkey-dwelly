# Case 038-N6: Failed delivery has returned to sender and the customer still wants the order (Customer's own reshipment request approved first)

## Case details

- **Source role:** Reshipment authorisations, Tallowmere Goods
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-11 09:00:00 UTC
- **Escalated:** 2026-03-11 09:42:00 UTC
- **Updated:** 2026-03-11 10:20:00 UTC
- **Completed:** 2026-03-11 10:20:00 UTC
- **Primary shipment:** DL-038
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 038, events 001–003 retained; branch DUPLICATE_REQUEST

## Context

DL-038 for TG-038 is back in Tallowmere Goods' stock after a failed delivery and accepted as reshippable; the account team has authenticated Sella Nove's order session with stored destination Apartment 2, 31 Rillstone Walk, Merrow Quay, and a new dispatch needs merchant approval. Sella still wants the order and confirms that destination. This branch diverges after event 003: Customer's own reshipment request approved first.

## Initial request

We already approved a reshipment for TG-038 at 09:20 from the customer's own portal request to the same address. Your email would create a second shipment record. Should we proceed?

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Reply to Reshipment authorisations to link the desk's request to the 09:20 approval and create no second shipment record.

- **Recipient:** Reshipment authorisations, Tallowmere Goods
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** RESOLVE_DUPLICATE (workflow sheet F)

## Outcome

One shipment record remains for TG-038 to Apartment 2; the duplicate is closed, and dispatch and receipt are still pending.

## Boundaries and remaining work

Must not: Do not let a second shipment record be created; two dispatches would go out for one order.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
