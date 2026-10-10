# Case 012-A1: Promised delivery day missed after vehicle breakdown (recipient availability not stated)

## Case details

- **Source role:** Fenn Azel, recipient
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-13 09:00:00 UTC
- **Escalated:** 2026-02-13 09:10:00 UTC
- **Updated:** 2026-02-13 10:20:00 UTC
- **Completed:** 2026-02-13 10:20:00 UTC
- **Primary shipment:** DL-012
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 012; the escalation omits the recipient's availability (A2-MISSING_DETAIL). The desk must first ask for the missing prerequisite instead of sending the rebooking request.

## Context

DL-012 was due on 2026-02-12 and a vehicle fault ended that route; the parcel is back in depot custody. Dispatch, not the desk, controls rebooking.

## Initial request

Yesterday's booked window was missed and I still have no parcel. Please arrange a replacement slot.

## Overview

The escalation snapshot comprises history events 001–002. Event 003 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask the recipient for the day and time range when they can receive the parcel.

- **Recipient:** Fenn Azel, recipient
- **Channel:** Customer portal
- **Recorded action:** [History event 003](history.md#event-003)
- **Expected decision:** ASK_CUSTOMER (the missing prerequisite is the availability)

## Outcome

Dispatch confirms a replacement booking after the desk receives the recipient's availability; delivery itself remains pending.

## Boundaries and remaining work

Must not: request a rebooking without a stated availability, promise any window before Dispatch confirms, or treat a stated availability as a booking. A booking confirmation is not a completed delivery.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
