# Case 012-N3: Promised delivery day missed after vehicle breakdown (Dispatch silent before next-day window)

## Case details

- **Source role:** Fenn Azel, recipient
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-13 09:00:00 UTC
- **Escalated:** 2026-02-13 15:30:00 UTC
- **Updated:** 2026-02-13 16:30:00 UTC
- **Completed:** 2026-02-13 16:30:00 UTC
- **Primary shipment:** DL-012
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 012, events 001–003 retained; branch NO_REPLY

## Context

Dispatch confirms that vehicle fault V-12 ended DL-012's route at 08:20 UTC on 2026-02-12, so the 08:00–09:00 window was missed and the parcel is back in depot custody. Fenn Azel, the recipient, asks for a replacement slot and is free on the afternoon of 2026-02-14. This branch diverges after event 003: Dispatch silent before next-day window.

## Initial request

I have heard nothing about tomorrow afternoon. Is DL-012 booked or not? I will only keep the afternoon free if someone confirms a window today.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Send Dispatch one email reminder asking for a specific 2026-02-14 afternoon window and any charge before the end of today, record Dispatch as owner, and tell Fenn in the portal that no window is confirmed yet.

- **Recipient:** Dispatch, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** WAIT_WITH_DEADLINE (workflow sheet B)

## Outcome

Dispatch confirms a specific window and charge, or the missed deadline is recorded against Dispatch; neither is a delivery.

## Boundaries and remaining work

Must not: Do not tell Fenn that DL-012 is booked for tomorrow afternoon; a reminder to Dispatch is not a booking.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
