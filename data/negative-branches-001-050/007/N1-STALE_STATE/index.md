# Case 007-N1: Pickup deadline is too short for the recipient (Counter capacity gone before approval)

## Case details

- **Source role:** Sedgeglass Counter supervisor
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-08 09:00:00 UTC
- **Escalated:** 2026-02-08 11:30:00 UTC
- **Updated:** 2026-02-08 12:30:00 UTC
- **Completed:** 2026-02-08 12:30:00 UTC
- **Primary shipment:** DL-007
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 007, events 001–003 retained; branch STALE_STATE

## Context

Sedgeglass Counter holds DL-007 until 2026-02-09, 18:00 UTC; its local policy allows a single two-day extension if requested before expiry and stock capacity permits, and it currently has capacity. Ciro Fale's trip ends on 2026-02-10 and he asks for DL-007 to be kept until 2026-02-11, not returned. This branch diverges after event 003: Counter capacity gone before approval.

## Initial request

We cannot extend DL-007. We had capacity this morning, but a bulk intake at 10:40 has filled our shelves. The parcel keeps its deadline of 2026-02-09, 18:00 UTC, after which the return timer runs.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask Routing by Email which options exist for DL-007 before its 2026-02-09, 18:00 UTC deadline, and make no change until Ciro chooses.

- **Recipient:** Routing, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** GET_OPTIONS (workflow sheet B)

## Outcome

Routing's options reach Ciro and he chooses; no extension exists, and nothing is collected.

## Boundaries and remaining work

Must not: Tell Ciro the deadline is 2026-02-11 because the counter had capacity at 09:00, or press the supervisor for an exception.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
