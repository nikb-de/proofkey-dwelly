# Case 033-N1: Courier misses a booked return collection (Requested window fills before booking)

## Case details

- **Source role:** Collections control, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-06 09:00:00 UTC
- **Escalated:** 2026-03-06 09:48:00 UTC
- **Updated:** 2026-03-06 10:45:00 UTC
- **Completed:** 2026-03-06 10:45:00 UTC
- **Primary task reference:** RT-033
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 033, events 001–003 retained; branch STALE_STATE

## Context

Plover Arc Logistics missed the collection of approved return RT-033, the parcel is still with the customer and rebooking is free. Virin Lask asks for a new collection on 2026-03-07 within 10:00–14:00. This branch diverges after event 003: Requested window fills before booking.

## Initial request

The 2026-03-07 route for that area filled at 09:40. No slot is left inside 10:00–14:00. Open slots: 2026-03-07, 14:00–16:00, or 2026-03-09, 10:00–12:00, both at no charge. Nothing is booked for RT-033.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask Virin in the Customer portal to choose one of the two offered slots, 2026-03-07 14:00–16:00 or 2026-03-09 10:00–12:00, stating that neither is inside the window Virin gave.

- **Recipient:** Virin Lask, customer
- **Channel:** Customer portal
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** ASK_CUSTOMER (workflow sheet B)

## Outcome

Virin's choice is booked and confirmed by Collections control; a booking is still not a collection, and no receipt exists yet.

## Boundaries and remaining work

Must not: Do not book 14:00–16:00 because it is close to the stated window; Virin's availability covered 10:00–14:00 only.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
