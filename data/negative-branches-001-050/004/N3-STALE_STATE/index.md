# Case 004-N3: Recipient requests a call shortly before arrival (Parcel moved to another route)

## Case details

- **Source role:** Dispatch, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-05 09:00:00 UTC
- **Escalated:** 2026-02-05 09:41:00 UTC
- **Updated:** 2026-02-05 10:45:00 UTC
- **Completed:** 2026-02-05 10:45:00 UTC
- **Primary shipment:** DL-004
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 004, events 001–003 retained; branch STALE_STATE

## Context

DL-004 is on the 2026-02-06 afternoon route; Dispatch can add a call request to the verified number already in the order record but cannot guarantee an exact advance interval. Oren Sile asks for a call shortly before arrival on his saved order contact. This branch diverges after event 003: Parcel moved to another route.

## Initial request

Before we save anything: DL-004 was moved this morning from the 2026-02-06 afternoon route to the 2026-02-07 morning route after a vehicle change. Call requests are added per route. Nothing is on the new route card yet.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Tell Oren in the Customer portal that DL-004 is now on the 2026-02-07 morning route and ask whether he still wants the call request on that route.

- **Recipient:** Oren Sile, recipient
- **Channel:** Customer portal
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** ASK_CUSTOMER (workflow sheet B)

## Outcome

Oren answers and Dispatch confirms what the new route card holds; that is not a call or an arrival.

## Boundaries and remaining work

Must not: Add the call request to the 2026-02-07 route without his answer, or tell him the delivery is still on 2026-02-06.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
