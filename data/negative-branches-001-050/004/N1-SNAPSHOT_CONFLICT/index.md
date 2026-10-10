# Case 004-N1: Recipient requests a call shortly before arrival (Recipient asks for an unverified new number)

## Case details

- **Source role:** Oren Sile, recipient
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-05 09:00:00 UTC
- **Escalated:** 2026-02-05 09:16:00 UTC
- **Updated:** 2026-02-05 09:55:00 UTC
- **Completed:** 2026-02-05 09:55:00 UTC
- **Primary shipment:** DL-004
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 004, events 001–002 retained; branch SNAPSHOT_CONFLICT

## Context

DL-004 is on the 2026-02-06 afternoon route; Dispatch can add a call request to the verified number already in the order record but cannot guarantee an exact advance interval. Oren Sile asks for a call shortly before arrival on his saved order contact. This branch diverges after event 002: Recipient asks for an unverified new number.

## Initial request

Correction: please do not use my saved number, that phone stays switched off at work. Have the driver call the studio's front desk line instead. It is not on the order yet; I can send it here.

## Overview

The escalation snapshot comprises history events 001–003. Event 004 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Tell Oren in the Customer portal that Dispatch can add a call request only to the verified number already in the order record, and ask whether he wants it on that number.

- **Recipient:** Oren Sile, recipient
- **Channel:** Customer portal
- **Recorded action:** [History event 004](history.md#event-004)
- **Expected decision:** DECLINE_EXPLAIN (workflow sheet A)

## Outcome

Oren accepts or declines the call request on the verified number; no unverified number reaches the order, and no call has occurred.

## Boundaries and remaining work

Must not: Collect the studio line and pass it to Dispatch or the driver, or record it on the route card.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
