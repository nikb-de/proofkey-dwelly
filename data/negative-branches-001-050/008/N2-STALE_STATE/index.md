# Case 008-N2: Recipient needs a defined delivery slot rather than an all-day estimate (Acceptance arrives after the quote lapsed)

## Case details

- **Source role:** Scheduling, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-09 09:00:00 UTC
- **Escalated:** 2026-02-09 16:25:00 UTC
- **Updated:** 2026-02-09 17:20:00 UTC
- **Completed:** 2026-02-09 17:20:00 UTC
- **Primary shipment:** DL-008
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 008, events 001–004 retained; branch STALE_STATE

## Context

DL-008 has an all-day booking for 2026-02-10; timed delivery may be available, but only Scheduling can quote live capacity and the upgrade charge. Nemi Thale cannot stay in all day and asks the desk to find a two-hour slot and its cost before any change. This branch diverges after event 004: Acceptance arrives after the quote lapsed.

## Initial request

Nemi accepted 12:00–14:00 in the booking thread at 16:18 UTC, after the 16:00 cut-off. That quote had lapsed and the window has since been taken. DL-008 remains on the all-day booking. We can now offer 2026-02-10, 14:00–16:00 for GBP 6.00 total.

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Tell Nemi in the Customer portal that the 12:00–14:00 quote lapsed and ask her to accept or decline 14:00–16:00 for GBP 6.00 in the verified booking thread.

- **Recipient:** Nemi Thale, recipient
- **Channel:** Customer portal
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** ASK_CUSTOMER (workflow sheet B)

## Outcome

Nemi's acceptance in the booking thread and Scheduling's booking confirmation close the branch; delivery and payment remain unproven.

## Boundaries and remaining work

Must not: Ask Scheduling to book 14:00–16:00 on the strength of her acceptance of 12:00–14:00, or tell her the earlier slot is confirmed.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
