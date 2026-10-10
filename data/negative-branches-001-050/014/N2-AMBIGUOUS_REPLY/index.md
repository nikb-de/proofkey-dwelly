# Case 014-N2: Driver arrives after the business receiving desk closes (Coordinator gives entrance but no window)

## Case details

- **Source role:** Rellin Vos, Vellum Rack receiving coordinator
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-15 09:00:00 UTC
- **Escalated:** 2026-02-15 09:50:00 UTC
- **Updated:** 2026-02-15 10:50:00 UTC
- **Completed:** 2026-02-15 10:50:00 UTC
- **Primary shipment:** DL-014
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 014, events 001–003 retained; branch AMBIGUOUS_REPLY

## Context

Business dispatch reports that DL-014 reached Vellum Rack Supplies after its receiving desk closed, the driver retained the parcel, and a staffed receiving window is needed to retry. Rellin Vos, the receiving coordinator, says the shop may be open late but the receiving desk is not, and asks to be consulted before any booking. This branch diverges after event 003: Coordinator gives entrance but no window.

## Initial request

Use the rear receiving door. We are usually around in the mornings, so a weekday morning should be fine. I cannot promise a clerk every day.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask Rellin once in the Business portal for one dated time window when a receiving clerk will be at the rear receiving door.

- **Recipient:** Rellin Vos, Vellum Rack receiving coordinator
- **Channel:** Business portal
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** ASK_CUSTOMER (workflow sheet A)

## Outcome

Rellin names a dated window with a clerk present and Business dispatch books it; the booking confirms the next attempt, not receipt.

## Boundaries and remaining work

Must not: Do not pass 'weekday mornings' to Business dispatch as a staffed window or book a morning attempt on a guess.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
