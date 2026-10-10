# Case 042-N1: Warehouse has no forklift for a booked pallet delivery (Planner quotes a range above limit)

## Case details

- **Source role:** Freight planner, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-15 09:00:00 UTC
- **Escalated:** 2026-03-15 09:45:00 UTC
- **Updated:** 2026-03-15 10:35:00 UTC
- **Completed:** 2026-03-15 10:35:00 UTC
- **Primary shipment:** DL-042
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 042, events 001–003 retained; branch AMBIGUOUS_REPLY

## Context

Pallet DL-042, 280 kg, goes to Fenwick Spur, which has no forklift and whose staff may not unload by hand. Registered coordinator Voren Tesk, on a verified portal channel, holds authority for up to GBP 30.00 total extra unloading cost and asks the desk to arrange a suitable carrier option within that limit. This branch diverges after event 003: Planner quotes a range above limit.

## Initial request

We can do DL-042 with a tail-lift vehicle. Price depends on crew time on site, usually GBP 22.00 to GBP 34.00 in total. I will pencil it in for tomorrow morning and book it at 12:00 UTC today unless you object.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Email the freight planner asking for a fixed total for the DL-042 unloading service, or an option capped at GBP 30.00, and object to booking on an open price at 12:00 UTC.

- **Recipient:** Freight planner, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** GET_OPTIONS (workflow sheet B)

## Outcome

The planner confirms an option with a fixed total at or below GBP 30.00; that is within authority, not payment or completed unloading.

## Boundaries and remaining work

Must not: Let the booking stand because the lower end of the range fits, treating the GBP 30.00 limit as approval of whatever the final cost turns out to be.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
