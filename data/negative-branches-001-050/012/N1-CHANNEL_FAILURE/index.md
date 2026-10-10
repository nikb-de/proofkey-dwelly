# Case 012-N1: Promised delivery day missed after vehicle breakdown (Booking tool timed out on reservation)

## Case details

- **Source role:** Dispatch, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-13 09:00:00 UTC
- **Escalated:** 2026-02-13 09:40:00 UTC
- **Updated:** 2026-02-13 10:20:00 UTC
- **Completed:** 2026-02-13 10:20:00 UTC
- **Primary shipment:** DL-012
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 012, events 001–003 retained; branch CHANNEL_FAILURE

## Context

Dispatch confirms that vehicle fault V-12 ended DL-012's route at 08:20 UTC on 2026-02-12, so the 08:00–09:00 window was missed and the parcel is back in depot custody. Fenn Azel, the recipient, asks for a replacement slot and is free on the afternoon of 2026-02-14. This branch diverges after event 003: Booking tool timed out on reservation.

## Initial request

We tried to reserve an afternoon window on 2026-02-14 for DL-012. The booking tool timed out before showing a confirmation. We cannot see whether the reservation saved and have sent nothing to Fenn.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask Dispatch by email to read the saved booking record for DL-012 and report whether a 2026-02-14 reservation exists, with no second reservation until that is known.

- **Recipient:** Dispatch, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** VERIFY_FIRST (workflow sheet R)

## Outcome

Dispatch reports one saved window or none, and if none, one resubmission is confirmed once; this closes the rebooking question, not delivery.

## Boundaries and remaining work

Must not: Do not ask Dispatch to try the booking again straight away, which could create two reservations, and do not tell Fenn that a slot is booked.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
