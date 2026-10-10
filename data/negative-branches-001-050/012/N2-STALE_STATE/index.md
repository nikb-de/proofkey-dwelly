# Case 012-N2: Promised delivery day missed after vehicle breakdown (Afternoon capacity filled before booking)

## Case details

- **Source role:** Dispatch, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-13 09:00:00 UTC
- **Escalated:** 2026-02-13 09:45:00 UTC
- **Updated:** 2026-02-13 10:40:00 UTC
- **Completed:** 2026-02-13 10:40:00 UTC
- **Primary shipment:** DL-012
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 012, events 001–003 retained; branch STALE_STATE

## Context

Dispatch confirms that vehicle fault V-12 ended DL-012's route at 08:20 UTC on 2026-02-12, so the 08:00–09:00 window was missed and the parcel is back in depot custody. Fenn Azel, the recipient, asks for a replacement slot and is free on the afternoon of 2026-02-14. This branch diverges after event 003: Afternoon capacity filled before booking.

## Initial request

Afternoon capacity on 2026-02-14 was filled at 09:30 UTC, before we reached your request. Available instead: 2026-02-14, 09:00–12:00 UTC, or 2026-02-15, 14:00–17:00 UTC. Neither carries a charge. Nothing is reserved yet.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask Fenn in the Customer portal to choose between 2026-02-14, 09:00–12:00 UTC and 2026-02-15, 14:00–17:00 UTC, both without charge, and pass only that choice to Dispatch.

- **Recipient:** Fenn Azel, recipient
- **Channel:** Customer portal
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** ASK_CUSTOMER (workflow sheet B)

## Outcome

Fenn chooses one window and Dispatch confirms the reservation; this is a booking, not a delivery.

## Boundaries and remaining work

Must not: Do not book the 2026-02-14 morning window because the date matches; Fenn offered only the afternoon.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
