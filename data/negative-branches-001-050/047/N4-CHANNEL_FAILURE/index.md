# Case 047-N4: Customer asks for an explanation of a carrier-issued import charge (Billing ticketing outage, request unlogged)

## Case details

- **Source role:** Mail system, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-20 09:00:00 UTC
- **Escalated:** 2026-03-20 09:27:00 UTC
- **Updated:** 2026-03-20 10:20:00 UTC
- **Completed:** 2026-03-20 10:20:00 UTC
- **Primary shipment:** DL-047
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 047, events 001–003 retained; branch CHANNEL_FAILURE

## Context

Recipient Teren Osk asks what the GBP 32.00 on charge notice IC-047 for DL-047 consists of, handling versus import assessment, before deciding what to do. The itemisation is held by Plover Arc's billing team and no payment is confirmed. This branch diverges after event 003: Billing ticketing outage, request unlogged.

## Initial request

Automatic reply from Import billing: our ticketing system is unavailable between 09:20 and 10:00 UTC. Messages received in this period may not be logged. No ticket number has been issued for your message.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

After 10:00 UTC, ask Import billing by email whether a request for the IC-047 breakdown is logged, before sending it again.

- **Recipient:** Import billing, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** VERIFY_FIRST (workflow sheet R)

## Outcome

Billing confirms one logged request; that is not yet the breakdown.

## Boundaries and remaining work

Must not: Send a second request that could open two tickets, or tell Teren that billing is already working on it.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
