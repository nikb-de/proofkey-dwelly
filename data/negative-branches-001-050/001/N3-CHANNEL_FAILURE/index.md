# Case 001-N3: Recipient cannot attend the scheduled delivery window (Booking request email unacknowledged by Dispatch)

## Case details

- **Source role:** Mail delivery system, Rivet Delivery Desk
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-02 09:00:00 UTC
- **Escalated:** 2026-02-02 10:30:00 UTC
- **Updated:** 2026-02-02 11:05:00 UTC
- **Completed:** 2026-02-02 11:05:00 UTC
- **Primary shipment:** DL-001
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 001, events 001–004 retained; branch CHANNEL_FAILURE

## Context

DL-001 is booked for 2026-02-03, 09:00–12:00 UTC, and Dispatch has two no-charge alternatives: 2026-02-03 15:00–18:00 or 2026-02-04 10:00–13:00. Vessa Lorne cannot attend the morning slot and asks the desk, in the order-linked portal thread, to move it. This branch diverges after event 004: Booking request email unacknowledged by Dispatch.

## Initial request

Delivery status notification. Your message to Dispatch, Plover Arc Logistics, subject 'DL-001 booking request: 2026-02-03 15:00–18:00', sent at 09:55, has not been accepted by the receiving server after 35 minutes. The server reported a temporary error. Retries continue automatically. Delivery status: unknown.

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask Dispatch in Dispatch chat what DL-001's saved booking shows now, and say that no second booking request will be sent until that is known.

- **Recipient:** Dispatch, Plover Arc Logistics
- **Channel:** Dispatch chat
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** VERIFY_FIRST (workflow sheet R)

## Outcome

Dispatch reports DL-001's saved slot; if the change is absent, one request follows and is confirmed once, and a reservation is still not a delivery.

## Boundaries and remaining work

Must not: Resend the booking request by chat or email while the first may still arrive, or tell Vessa her afternoon slot is booked.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
