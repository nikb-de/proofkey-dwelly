# Case 033-N6: Courier misses a booked return collection (No rebooking reply before the day ends)

## Case details

- **Source role:** Virin Lask, customer
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-06 09:00:00 UTC
- **Escalated:** 2026-03-06 16:30:00 UTC
- **Updated:** 2026-03-06 17:20:00 UTC
- **Completed:** 2026-03-06 17:20:00 UTC
- **Primary task reference:** RT-033
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 033, events 001–003 retained; branch NO_REPLY

## Context

Plover Arc Logistics missed the collection of approved return RT-033, the parcel is still with the customer and rebooking is free. Virin Lask asks for a new collection on 2026-03-07 within 10:00–14:00. This branch diverges after event 003: No rebooking reply before the day ends.

## Initial request

It is 16:30 and I still have no booking for tomorrow. I have arranged to be home 10:00–14:00 only. Is someone coming?

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Send Collections control one email reminder that RT-033 needs a booking inside 2026-03-07, 10:00–14:00 UTC, the only window Virin gave, and tell Virin in the Customer portal that no booking is confirmed yet.

- **Recipient:** Collections control, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** WAIT_WITH_DEADLINE (workflow sheet B)

## Outcome

Collections control replies with a booking inside the window or states it cannot; the deadline is on record, and nothing is collected.

## Boundaries and remaining work

Must not: Do not tell Virin a collection is booked or try to book through another team; a reminder is not a booking.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
