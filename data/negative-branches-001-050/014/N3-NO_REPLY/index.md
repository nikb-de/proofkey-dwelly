# Case 014-N3: Driver arrives after the business receiving desk closes (No window before route booking cut-off)

## Case details

- **Source role:** Business dispatch, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-15 09:00:00 UTC
- **Escalated:** 2026-02-15 15:00:00 UTC
- **Updated:** 2026-02-15 16:35:00 UTC
- **Completed:** 2026-02-15 16:35:00 UTC
- **Primary shipment:** DL-014
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 014, events 001–003 retained; branch NO_REPLY

## Context

Business dispatch reports that DL-014 reached Vellum Rack Supplies after its receiving desk closed, the driver retained the parcel, and a staffed receiving window is needed to retry. Rellin Vos, the receiving coordinator, says the shop may be open late but the receiving desk is not, and asks to be consulted before any booking. This branch diverges after event 003: No window before route booking cut-off.

## Initial request

No staffed window for DL-014 has reached us. Bookings for the next business route close at 16:30 UTC today. After that, the next planning run is for 2026-02-17. The parcel stays in depot custody.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Send Rellin Vos one reminder in the Business portal that a staffed window and entrance are needed before 16:30 UTC today for the next business route, and record Rellin as owner of the reply.

- **Recipient:** Rellin Vos, Vellum Rack receiving coordinator
- **Channel:** Business portal
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** WAIT_WITH_DEADLINE (workflow sheet B)

## Outcome

Rellin's window arrives before 16:30 UTC and is relayed, or Business dispatch records the missed cut-off; neither is a booking or a receipt.

## Boundaries and remaining work

Must not: Do not book an attempt on the shop's opening hours or a guessed window; Rellin asked to be consulted before any booking.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
