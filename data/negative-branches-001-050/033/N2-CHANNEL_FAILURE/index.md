# Case 033-N2: Courier misses a booked return collection (Rebooking save times out)

## Case details

- **Source role:** Collections control, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-06 09:00:00 UTC
- **Escalated:** 2026-03-06 09:40:00 UTC
- **Updated:** 2026-03-06 10:20:00 UTC
- **Completed:** 2026-03-06 10:20:00 UTC
- **Primary task reference:** RT-033
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 033, events 001–003 retained; branch CHANNEL_FAILURE

## Context

Plover Arc Logistics missed the collection of approved return RT-033, the parcel is still with the customer and rebooking is free. Virin Lask asks for a new collection on 2026-03-07 within 10:00–14:00. This branch diverges after event 003: Rebooking save times out.

## Initial request

Automated reply. The rebooking request for RT-033 timed out at 09:39 while saving to the collection plan. The plan may or may not hold a new slot. No booking reference was generated in this message.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Email Collections control and ask what the collection plan shows for RT-033 now, stating that no second rebooking will be requested until that is known.

- **Recipient:** Collections control, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** VERIFY_FIRST (workflow sheet R)

## Outcome

Collections control reports one booking inside 10:00–14:00, or none and then one rebooking confirmed once; this still does not prove collection.

## Boundaries and remaining work

Must not: Do not send a second rebooking or tell Virin a slot is booked; a blind retry can put two collection jobs on the route.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
