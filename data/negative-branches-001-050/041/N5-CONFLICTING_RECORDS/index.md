# Case 041-N5: Pallet delivery lacks a receiving-dock appointment (Automatic notice gives a different date)

## Case details

- **Source role:** Arcloom dock schedule, automatic notice
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-14 09:00:00 UTC
- **Escalated:** 2026-03-14 09:55:00 UTC
- **Updated:** 2026-03-14 10:35:00 UTC
- **Completed:** 2026-03-14 10:35:00 UTC
- **Primary shipment:** DL-041
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 041, events 001–004 retained; branch CONFLICTING_RECORDS

## Context

Freight dispatch can reach Arcloom Components' dock with pallet DL-041 on 2026-03-15 afternoon but will not send the truck without a consignee appointment. It asks the desk to book with authorised receiving coordinator Ossa Rell and obtain the dock reference, time and receiving entrance. This branch diverges after event 004: Automatic notice gives a different date.

## Initial request

Automatic confirmation. Appointment ARC-041, consignment DL-041, dock D3, 2026-03-16, 14:00 to 15:00 UTC. Report to the receiving entrance 15 minutes before the slot. This message is generated from the Arcloom dock schedule.

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask Ossa Rell in the business portal which date the Arcloom dock schedule holds for ARC-041, 2026-03-15 or 2026-03-16, keeping both records on file.

- **Recipient:** Ossa Rell, Arcloom receiving coordinator
- **Channel:** Business portal
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** RECONCILE_CONFLICT (workflow sheet E)

## Outcome

Ossa confirms one date and the dock schedule shows it; that settles the booking date, not that the pallet is received.

## Boundaries and remaining work

Must not: Pass 2026-03-15 to dispatch because it matches the truck plan, or dismiss the automatic notice as a typo.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
