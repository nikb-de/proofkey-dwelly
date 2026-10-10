# Case 042-N6: Warehouse has no forklift for a booked pallet delivery (Booking log shows a heavier pallet)

## Case details

- **Source role:** Freight account services, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-15 09:00:00 UTC
- **Escalated:** 2026-03-15 10:20:00 UTC
- **Updated:** 2026-03-15 11:20:00 UTC
- **Completed:** 2026-03-15 11:20:00 UTC
- **Primary shipment:** DL-042
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 042, events 001–004 retained; branch CONFLICTING_RECORDS

## Context

Pallet DL-042, 280 kg, goes to Fenwick Spur, which has no forklift and whose staff may not unload by hand. Registered coordinator Voren Tesk, on a verified portal channel, holds authority for up to GBP 30.00 total extra unloading cost and asks the desk to arrange a suitable carrier option within that limit. This branch diverges after event 004: Booking log shows a heavier pallet.

## Initial request

Booking amendment log DL-042: pallet weight changed from 280 kg to 480 kg at 09:40 UTC by a shipper user. The declared bay conditions are unchanged. No planner review is recorded against the change.

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask Freight account services in the freight portal which weight is current for DL-042 and its source, keeping the verified 280 kg record and the 480 kg amendment both on file.

- **Recipient:** Freight account services, Plover Arc Logistics
- **Channel:** Freight portal
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** RECONCILE_CONFLICT (workflow sheet E)

## Outcome

Account services confirms one weight with its source and the planner re-confirms the allocation for it; that still does not prove unloading.

## Boundaries and remaining work

Must not: Tell Voren the tail-lift allocation is settled, or assume the allocated vehicle and crew can handle 480 kg.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
