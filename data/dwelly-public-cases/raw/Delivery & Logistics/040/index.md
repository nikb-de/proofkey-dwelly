# Case 040: Cancelled order is packed but has not left the merchant warehouse

## Case details

- **Source role:** Order control, Tallowmere Goods
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-13 09:00:00 UTC
- **Escalated:** 2026-03-13 09:10:00 UTC
- **Updated:** 2026-03-13 09:50:00 UTC
- **Completed:** 2026-03-13 09:50:00 UTC
- **Primary shipment:** DL-040
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC

## Context

The merchant has authorised cancellation while the packed item is still in its warehouse. Warehouse stop confirmation is required before calling dispatch cancelled.

## Initial request

Please get the warehouse to stop DL-040 before the next outbound sweep. The cancellation is authorised, but the physical dispatch stop is not confirmed.

## Overview

The escalation snapshot comprises history events 001–002. Event 003 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask the warehouse to stop dispatch using the merchant's recorded cancellation authority.

- **Recipient:** Warehouse dispatch, Tallowmere Goods
- **Channel:** Warehouse work queue
- **Recorded action:** [History event 003](history.md#event-003)

## Outcome

The warehouse confirms the package was removed from outbound dispatch; refund processing remains separate.

## Boundaries and remaining work

Dispatch stop is not a refund approval, payment or completed customer communication.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
