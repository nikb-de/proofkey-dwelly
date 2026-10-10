# Case 042-N3: Warehouse has no forklift for a booked pallet delivery (Planner mailbox migration loses the request)

## Case details

- **Source role:** Mail system, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-15 09:00:00 UTC
- **Escalated:** 2026-03-15 09:31:00 UTC
- **Updated:** 2026-03-15 10:10:00 UTC
- **Completed:** 2026-03-15 10:10:00 UTC
- **Primary shipment:** DL-042
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 042, events 001–003 retained; branch CHANNEL_FAILURE

## Context

Pallet DL-042, 280 kg, goes to Fenwick Spur, which has no forklift and whose staff may not unload by hand. Registered coordinator Voren Tesk, on a verified portal channel, holds authority for up to GBP 30.00 total extra unloading cost and asks the desk to arrange a suitable carrier option within that limit. This branch diverges after event 003: Planner mailbox migration loses the request.

## Initial request

Automatic notice: the freight planner mailbox is being migrated. Messages received between 09:00 and 10:00 UTC may not reach the planning queue. No request number has been issued for your message of 09:25 UTC. Check request status in the freight portal.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask the freight planner through the freight portal whether an unloading request for DL-042 exists in the planning queue, before sending it again.

- **Recipient:** Freight planner, Plover Arc Logistics
- **Channel:** Freight portal
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** VERIFY_FIRST (workflow sheet R)

## Outcome

The planner confirms one DL-042 request on file; that shows the request is logged, not that a vehicle or cost is agreed.

## Boundaries and remaining work

Must not: Send a second unloading request that could produce two allocations and two service charges against one GBP 30.00 authority.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
