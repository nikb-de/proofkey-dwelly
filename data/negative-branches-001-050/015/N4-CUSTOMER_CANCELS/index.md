# Case 015-N4: Parcel has been routed to the wrong local depot (Recipient stops transfer to collect)

## Case details

- **Source role:** Kiva Rell, recipient
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-16 09:00:00 UTC
- **Escalated:** 2026-02-16 10:30:00 UTC
- **Updated:** 2026-02-16 11:15:00 UTC
- **Completed:** 2026-02-16 11:15:00 UTC
- **Primary shipment:** DL-015
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 015, events 001–003 retained; branch CUSTOMER_CANCELS

## Context

Routing control confirms that DL-015 is at North Sedgeglass depot by routing error, while its destination Merrow Quay is served by East Copperfin depot, and no delivery attempt is scheduled. Kiva Rell, the recipient, asks for the parcel to reach the local depot before delivery is arranged. This branch diverges after event 003: Recipient stops transfer to collect.

## Initial request

Please stop the transfer. North Sedgeglass is near my work and I would rather collect DL-015 there today. Do not move it.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Record the stop with Routing control by email, forbid new transfer actions on DL-015, and ask what had already been executed before the stop.

- **Recipient:** Routing control, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** RECORD_STOP (workflow sheet F)

## Outcome

Routing control confirms the stop and the actual state of DL-015; this does not authorise collection at North Sedgeglass or undo any movement already executed.

## Boundaries and remaining work

Must not: Do not tell Kiva that collection at North Sedgeglass is possible, and do not ask Routing control to reverse a movement already under way.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
