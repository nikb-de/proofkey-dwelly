# Case 001-N2: Recipient cannot attend the scheduled delivery window (Chosen afternoon slot taken before booking)

## Case details

- **Source role:** Dispatch, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-02 09:00:00 UTC
- **Escalated:** 2026-02-02 10:02:00 UTC
- **Updated:** 2026-02-02 10:55:00 UTC
- **Completed:** 2026-02-02 10:55:00 UTC
- **Primary shipment:** DL-001
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 001, events 001–004 retained; branch STALE_STATE

## Context

DL-001 is booked for 2026-02-03, 09:00–12:00 UTC, and Dispatch has two no-charge alternatives: 2026-02-03 15:00–18:00 or 2026-02-04 10:00–13:00. Vessa Lorne cannot attend the morning slot and asks the desk, in the order-linked portal thread, to move it. This branch diverges after event 004: Chosen afternoon slot taken before booking.

## Initial request

We received your booking request for DL-001 with Vessa's choice of 2026-02-03 15:00–18:00. That slot was allocated to another stop at 09:41 and is no longer in our inventory. 2026-02-04 10:00–13:00 is still open at no charge. DL-001 stays booked for 2026-02-03, 09:00–12:00.

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Tell Vessa in the order-linked Customer portal thread that 2026-02-03 15:00–18:00 is no longer available and ask whether she wants 2026-02-04 10:00–13:00 instead.

- **Recipient:** Vessa Lorne, recipient
- **Channel:** Customer portal
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** ASK_CUSTOMER (workflow sheet B)

## Outcome

Vessa's new choice in the thread and Dispatch's reservation confirmation close the branch; a reservation is not a completed delivery.

## Boundaries and remaining work

Must not: Ask Dispatch to book 2026-02-04 10:00–13:00 on the strength of her earlier choice, or tell her the afternoon slot is reserved.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
