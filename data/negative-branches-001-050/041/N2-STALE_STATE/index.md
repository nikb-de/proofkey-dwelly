# Case 041-N2: Pallet delivery lacks a receiving-dock appointment (Reserved dock slot withdrawn before carrier acceptance)

## Case details

- **Source role:** Ossa Rell, Arcloom receiving coordinator
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-14 09:00:00 UTC
- **Escalated:** 2026-03-14 09:58:00 UTC
- **Updated:** 2026-03-14 10:40:00 UTC
- **Completed:** 2026-03-14 10:40:00 UTC
- **Primary shipment:** DL-041
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 041, events 001–004 retained; branch STALE_STATE

## Context

Freight dispatch can reach Arcloom Components' dock with pallet DL-041 on 2026-03-15 afternoon but will not send the truck without a consignee appointment. It asks the desk to book with authorised receiving coordinator Ossa Rell and obtain the dock reference, time and receiving entrance. This branch diverges after event 004: Reserved dock slot withdrawn before carrier acceptance.

## Initial request

Change to ARC-041. A delayed inbound now occupies dock D3 until 16:00 UTC on 2026-03-15, so the 14:00 to 15:00 slot is released. I can hold 16:00 to 17:00 UTC at dock D1 under the same reference until 12:00 UTC today. Please confirm whether your carrier can make it.

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Email Freight dispatch whether its truck can reach Arcloom dock D1 at 16:00 to 17:00 UTC on 2026-03-15, stating that the 14:00 slot at D3 is withdrawn and the hold expires at 12:00 UTC today.

- **Recipient:** Freight dispatch, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** ASK_CUSTOMER (workflow sheet B)

## Outcome

Dispatch and Ossa Rell confirm the same reference, time and dock; matching records still do not prove delivery or receipt.

## Boundaries and remaining work

Must not: Confirm the D1 slot to Ossa on dispatch's behalf, or let dispatch accept ARC-041 for 14:00 to 15:00 at dock D3.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
