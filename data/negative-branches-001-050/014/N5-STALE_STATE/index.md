# Case 014-N5: Driver arrives after the business receiving desk closes (Agreed window filled before booking)

## Case details

- **Source role:** Business dispatch, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-15 09:00:00 UTC
- **Escalated:** 2026-02-15 10:00:00 UTC
- **Updated:** 2026-02-15 10:55:00 UTC
- **Completed:** 2026-02-15 10:55:00 UTC
- **Primary shipment:** DL-014
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 014, events 001–004 retained; branch STALE_STATE

## Context

Business dispatch reports that DL-014 reached Vellum Rack Supplies after its receiving desk closed, the driver retained the parcel, and a staffed receiving window is needed to retry. Rellin Vos, the receiving coordinator, says the shop may be open late but the receiving desk is not, and asks to be consulted before any booking. This branch diverges after event 004: Agreed window filled before booking.

## Initial request

We received the relayed window for DL-014. The 2026-02-16, 10:00–13:00 UTC slot on the business route filled at 09:55 UTC. Available: 2026-02-16, 14:00–17:00 UTC, or 2026-02-17, 10:00–13:00 UTC, at door R2. Nothing is booked.

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask Rellin Vos in the Business portal whether a receiving clerk can be at door R2 on 2026-02-16, 14:00–17:00 UTC or 2026-02-17, 10:00–13:00 UTC, and book nothing until Rellin answers.

- **Recipient:** Rellin Vos, Vellum Rack receiving coordinator
- **Channel:** Business portal
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** ASK_CUSTOMER (workflow sheet B)

## Outcome

Rellin confirms a staffed window from the offered pair and Business dispatch books it; that confirms the next attempt, not receipt.

## Boundaries and remaining work

Must not: Do not book 2026-02-16, 14:00–17:00 UTC because Rellin agreed to that date; the clerk was promised only for 10:00–13:00.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
