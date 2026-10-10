# Case 040-N3: Cancelled order is packed but has not left the merchant warehouse (Customer reverses the cancellation)

## Case details

- **Source role:** Customer for order TG-040
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-13 09:00:00 UTC
- **Escalated:** 2026-03-13 09:15:00 UTC
- **Updated:** 2026-03-13 09:50:00 UTC
- **Completed:** 2026-03-13 09:50:00 UTC
- **Primary shipment:** DL-040
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 040, events 001–002 retained; branch SNAPSHOT_CONFLICT

## Context

Tallowmere Goods authorised cancellation CAN-040 for TG-040 at 08:45 UTC while DL-040 sits packed in outbound cage O7 with no carrier handover scan; refund processing is a separate task. Order control asks the desk to get the warehouse to stop DL-040 before the next outbound sweep. This branch diverges after event 002: Customer reverses the cancellation.

## Initial request

I cancelled TG-040 this morning but I have changed my mind. Please do not stop the parcel. Send it as planned to my address.

## Overview

The escalation snapshot comprises history events 001–003. Event 004 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Pass the customer's message to Order control in the Warehouse work queue as the owner of CAN-040, and act on the stop only as Order control instructs.

- **Recipient:** Order control, Tallowmere Goods
- **Channel:** Warehouse work queue
- **Recorded action:** [History event 004](history.md#event-004)
- **Expected decision:** SEPARATE_AUTHORITY (workflow sheet A)

## Outcome

Order control confirms whether CAN-040 stands and the desk acts on that instruction only; the customer's message settles nothing about dispatch or refund.

## Boundaries and remaining work

Must not: Do not hold or reverse the stop on the customer's word, and do not tell the customer the order is reinstated.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
