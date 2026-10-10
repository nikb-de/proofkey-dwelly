# Case 040-N4: Cancelled order is packed but has not left the merchant warehouse (Carrier scan contradicts warehouse stop)

## Case details

- **Source role:** Tracking support, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-13 09:00:00 UTC
- **Escalated:** 2026-03-13 10:05:00 UTC
- **Updated:** 2026-03-13 10:45:00 UTC
- **Completed:** 2026-03-13 10:45:00 UTC
- **Primary shipment:** DL-040
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 040, events 001–004 retained; branch CONFLICTING_RECORDS

## Context

Tallowmere Goods authorised cancellation CAN-040 for TG-040 at 08:45 UTC while DL-040 sits packed in outbound cage O7 with no carrier handover scan; refund processing is a separate task. Order control asks the desk to get the warehouse to stop DL-040 before the next outbound sweep. This branch diverges after event 004: Carrier scan contradicts warehouse stop.

## Initial request

DL-040 shows a collection scan at the Tallowmere outbound dock at 09:48 UTC today, on the trailer manifest for the 10:00 departure. No exception has been recorded against it.

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Record both statements and ask Warehouse dispatch in the Warehouse work queue for a physical check of cancellation stock for DL-040, quoting the carrier's 09:48 collection scan, overwriting neither record.

- **Recipient:** Warehouse dispatch, Tallowmere Goods
- **Channel:** Warehouse work queue
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** RECONCILE_CONFLICT (workflow sheet E)

## Outcome

Warehouse dispatch reports where DL-040 physically is, with the carrier scan kept on record beside it; refund and customer communication stay separate.

## Boundaries and remaining work

Must not: Do not tell Order control the dispatch is stopped on the warehouse record alone, and do not request a carrier intercept before the physical check.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
