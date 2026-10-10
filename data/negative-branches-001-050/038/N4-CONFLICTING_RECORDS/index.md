# Case 038-N4: Failed delivery has returned to sender and the customer still wants the order (New shipment shows delivered too soon)

## Case details

- **Source role:** Sella Nove, customer
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-11 09:00:00 UTC
- **Escalated:** 2026-03-11 15:10:00 UTC
- **Updated:** 2026-03-11 16:30:00 UTC
- **Completed:** 2026-03-11 16:30:00 UTC
- **Primary shipment:** DL-038
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 038, events 001–004 retained; branch CONFLICTING_RECORDS

## Context

DL-038 for TG-038 is back in Tallowmere Goods' stock after a failed delivery and accepted as reshippable; the account team has authenticated Sella Nove's order session with stored destination Apartment 2, 31 Rillstone Walk, Merrow Quay, and a new dispatch needs merchant approval. Sella still wants the order and confirms that destination. This branch diverges after event 004: New shipment shows delivered too soon.

## Initial request

My order page now shows DL-038-R as Delivered. Nothing has arrived at Apartment 2 and nobody has called. Is it delivered or not?

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Email Reshipment authorisations with both records, the Delivered status on DL-038-R and its own 09:50 statement that the parcel was not yet handed to the carrier, and ask for the handover and delivery scan evidence behind the status.

- **Recipient:** Reshipment authorisations, Tallowmere Goods
- **Channel:** Email
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** RECONCILE_CONFLICT (workflow sheet E)

## Outcome

The merchant reports the actual scans for DL-038-R; only a carrier handover and delivery scan would change the picture, and receipt by Sella is still unconfirmed.

## Boundaries and remaining work

Must not: Do not tell Sella the parcel is delivered, and do not ask for another reshipment; the old DL-038 status may have carried over.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
