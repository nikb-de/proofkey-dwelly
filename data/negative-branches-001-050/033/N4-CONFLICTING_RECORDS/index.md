# Case 033-N4: Courier misses a booked return collection (Collected status but carton still home)

## Case details

- **Source role:** Virin Lask, customer
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-06 09:00:00 UTC
- **Escalated:** 2026-03-07 13:30:00 UTC
- **Updated:** 2026-03-07 15:20:00 UTC
- **Completed:** 2026-03-07 15:20:00 UTC
- **Primary task reference:** RT-033
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 033, events 001–004 retained; branch CONFLICTING_RECORDS

## Context

Plover Arc Logistics missed the collection of approved return RT-033, the parcel is still with the customer and rebooking is free. Virin Lask asks for a new collection on 2026-03-07 within 10:00–14:00. This branch diverges after event 004: Collected status but carton still home.

## Initial request

The return portal now says RT-033 was collected at 12:05. Nobody came to my door between 11:00 and 13:00 and the sealed carton is still in my hall. There is no receipt in my portal.

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Email Collections control with both statements, the 12:05 collected status and Virin's report that the sealed carton is still at home, and ask for the driver's scan evidence and receipt for RT-033.

- **Recipient:** Collections control, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** RECONCILE_CONFLICT (workflow sheet E)

## Outcome

Collections control produces the scan evidence or corrects the status; only an actual receipt would establish carrier custody, and merchant receipt and refund stay open.

## Boundaries and remaining work

Must not: Do not tell Virin the parcel is in carrier custody because of the status, and do not book a further collection before the scan is explained.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
