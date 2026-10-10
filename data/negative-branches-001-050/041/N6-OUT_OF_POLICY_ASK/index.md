# Case 041-N6: Pallet delivery lacks a receiving-dock appointment (Consignee suggests turning up unbooked)

## Case details

- **Source role:** Ossa Rell, Arcloom receiving coordinator
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-14 09:00:00 UTC
- **Escalated:** 2026-03-14 09:45:00 UTC
- **Updated:** 2026-03-14 10:25:00 UTC
- **Completed:** 2026-03-14 10:25:00 UTC
- **Primary shipment:** DL-041
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 041, events 001–003 retained; branch OUT_OF_POLICY_ASK

## Context

Freight dispatch can reach Arcloom Components' dock with pallet DL-041 on 2026-03-15 afternoon but will not send the truck without a consignee appointment. It asks the desk to book with authorised receiving coordinator Ossa Rell and obtain the dock reference, time and receiving entrance. This branch diverges after event 003: Consignee suggests turning up unbooked.

## Initial request

Tomorrow afternoon is busy and I would rather not lock a slot for one pallet. Tell your driver to turn up after 13:00 UTC on 2026-03-15 and we will fit DL-041 in between booked vehicles. You do not need a reference for that.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Reply to Ossa Rell in the business portal that the carrier will not send DL-041 without a consignee appointment, and ask for a reserved slot with reference, time and entrance.

- **Recipient:** Ossa Rell, Arcloom receiving coordinator
- **Channel:** Business portal
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** DECLINE_EXPLAIN (workflow sheet A)

## Outcome

Ossa issues a reserved slot with reference and entrance; that meets the carrier's condition but is not receipt of the pallet.

## Boundaries and remaining work

Must not: Tell dispatch that turning up after 13:00 counts as an appointment and let the truck go without a reference.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
