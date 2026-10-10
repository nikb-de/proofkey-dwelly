# Case 040-N1: Cancelled order is packed but has not left the merchant warehouse (Parcel handed over before the stop)

## Case details

- **Source role:** Warehouse dispatch, Tallowmere Goods
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-13 09:00:00 UTC
- **Escalated:** 2026-03-13 09:41:00 UTC
- **Updated:** 2026-03-13 10:40:00 UTC
- **Completed:** 2026-03-13 10:40:00 UTC
- **Primary shipment:** DL-040
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 040, events 001–003 retained; branch STALE_STATE

## Context

Tallowmere Goods authorised cancellation CAN-040 for TG-040 at 08:45 UTC while DL-040 sits packed in outbound cage O7 with no carrier handover scan; refund processing is a separate task. Order control asks the desk to get the warehouse to stop DL-040 before the next outbound sweep. This branch diverges after event 003: Parcel handed over before the stop.

## Initial request

Cage O7 was swept at 09:30, before the stop task was picked up. DL-040 was loaded onto the Plover Arc trailer and has a carrier handover scan at 09:32. We can no longer stop it in the warehouse.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask Dispatch, Plover Arc Logistics, by email for the intercept or return options and any charge for DL-040, changing nothing until Order control accepts one.

- **Recipient:** Dispatch, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** GET_OPTIONS (workflow sheet B)

## Outcome

The carrier's options reach Order control and it chooses one; an intercept request is not a parcel back in the warehouse, and refund stays separate.

## Boundaries and remaining work

Must not: Do not report the dispatch as stopped, and do not order an intercept on the strength of CAN-040; the warehouse stop it covered is no longer possible.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
