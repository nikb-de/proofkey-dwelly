# Case 012-N6: Promised delivery day missed after vehicle breakdown (Customer notice shows a different window)

## Case details

- **Source role:** Fenn Azel, recipient
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-13 09:00:00 UTC
- **Escalated:** 2026-02-13 10:00:00 UTC
- **Updated:** 2026-02-13 10:45:00 UTC
- **Completed:** 2026-02-13 10:45:00 UTC
- **Primary shipment:** DL-012
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 012, events 001–004 retained; branch CONFLICTING_RECORDS

## Context

Dispatch confirms that vehicle fault V-12 ended DL-012's route at 08:20 UTC on 2026-02-12, so the 08:00–09:00 window was missed and the parcel is back in depot custody. Fenn Azel, the recipient, asks for a replacement slot and is free on the afternoon of 2026-02-14. This branch diverges after event 004: Customer notice shows a different window.

## Initial request

The revised booking I received says 2026-02-14, 08:00–11:00 UTC, not the afternoon. I asked for the afternoon. Which one is right?

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Keep both records and ask Dispatch by email which window is saved in the DL-012 booking record and to correct the notice sent to Fenn, telling Fenn only that the window is being checked.

- **Recipient:** Dispatch, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** RECONCILE_CONFLICT (workflow sheet E)

## Outcome

Dispatch confirms one saved window and reissues a matching notice; this settles the booking record, not delivery.

## Boundaries and remaining work

Must not: Do not tell Fenn that the afternoon window is correct because Dispatch's email says so, or that the notice can be ignored.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
