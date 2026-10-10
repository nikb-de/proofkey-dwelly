# Case 040-N6: Cancelled order is packed but has not left the merchant warehouse (Warehouse silent as the sweep nears)

## Case details

- **Source role:** Order control, Tallowmere Goods
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-13 09:00:00 UTC
- **Escalated:** 2026-03-13 10:05:00 UTC
- **Updated:** 2026-03-13 10:28:00 UTC
- **Completed:** 2026-03-13 10:28:00 UTC
- **Primary shipment:** DL-040
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 040, events 001–003 retained; branch NO_REPLY

## Context

Tallowmere Goods authorised cancellation CAN-040 for TG-040 at 08:45 UTC while DL-040 sits packed in outbound cage O7 with no carrier handover scan; refund processing is a separate task. Order control asks the desk to get the warehouse to stop DL-040 before the next outbound sweep. This branch diverges after event 003: Warehouse silent as the sweep nears.

## Initial request

No reply from warehouse dispatch on DL-040 yet. The next outbound sweep of cage O7 is at 10:30. Is the stop in place?

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Post one reminder to Warehouse dispatch in the Warehouse work queue that CAN-040 requires DL-040 to be removed from cage O7 before the 10:30 sweep, and tell Order control that no stop is confirmed yet.

- **Recipient:** Warehouse dispatch, Tallowmere Goods; Order control, Tallowmere Goods
- **Channel:** Warehouse work queue
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** WAIT_WITH_DEADLINE (workflow sheet B)

## Outcome

Warehouse dispatch confirms removal before 10:30, or the sweep passes on record without it; either way refund stays separate.

## Boundaries and remaining work

Must not: Do not tell Order control the stop is in place, and do not ask the carrier to refuse the parcel; a reminder is not a stop.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
