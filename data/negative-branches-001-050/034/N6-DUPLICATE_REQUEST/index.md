# Case 034-N6: Returned parcel has reached the carrier depot but not the merchant warehouse (Customer opens a parallel trace)

## Case details

- **Source role:** Returns trace team, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-07 09:00:00 UTC
- **Escalated:** 2026-03-07 10:00:00 UTC
- **Updated:** 2026-03-07 10:45:00 UTC
- **Completed:** 2026-03-07 10:45:00 UTC
- **Primary task reference:** RT-034
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 034, events 001–003 retained; branch DUPLICATE_REQUEST

## Context

The last scan for return RT-034 is at the carrier's return depot at 07:40 UTC on 2026-03-07, with no merchant receiving scan, so Plover Arc Logistics still holds it. Elrin Kove asks for a trace through to the moment the merchant actually has it. This branch diverges after event 003: Customer opens a parallel trace.

## Initial request

The customer also opened a trace for RT-034 from the tracking page at 09:40. We now have two open traces for one parcel. Should both stay open?

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Reply to the Returns trace team that both traces concern RT-034, link the 09:40 trace to the desk's 09:25 request, and ask it to work one trace that ends in merchant receiving confirmation.

- **Recipient:** Returns trace team, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** RESOLVE_DUPLICATE (workflow sheet F)

## Outcome

The trace team closes the duplicate and confirms one live trace; the parcel's location and merchant receipt are still unconfirmed.

## Boundaries and remaining work

Must not: Do not keep both traces running, and do not close the one that carries the merchant receipt condition.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
