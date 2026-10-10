# Case 010-N1: Recipient wants delivery held during a short absence (Return date exceeds the hold limit)

## Case details

- **Source role:** Daro Lusk, recipient
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-11 09:00:00 UTC
- **Escalated:** 2026-02-11 09:16:00 UTC
- **Updated:** 2026-02-11 10:30:00 UTC
- **Completed:** 2026-02-11 10:30:00 UTC
- **Primary shipment:** DL-010
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 010, events 001–002 retained; branch SNAPSHOT_CONFLICT

## Context

DL-010 is in depot stock, and the service allows a hold of up to three calendar days before routing with a confirmed release date. Daro Lusk is away until 2026-02-14 and asks for the parcel to be held and released on that date, not earlier. This branch diverges after event 002: Return date exceeds the hold limit.

## Initial request

Correction to my last message: my return has moved. I am now back on 2026-02-16. Please hold DL-010 until then and release it on 2026-02-16, not before.

## Overview

The escalation snapshot comprises history events 001–003. Event 004 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Tell Daro in the verified order thread that this service allows a hold of up to three calendar days before routing, so a release on 2026-02-16 is outside it, and ask whether he wants the longest permitted hold instead.

- **Recipient:** Daro Lusk, recipient
- **Channel:** Customer portal
- **Recorded action:** [History event 004](history.md#event-004)
- **Expected decision:** DECLINE_EXPLAIN (workflow sheet A)

## Outcome

Daro confirms a release date within the limit and Dispatch confirms the hold; a release date is not a delivery date.

## Boundaries and remaining work

Must not: Ask Dispatch for a hold to 2026-02-16 or an exception, or request any hold before Daro confirms a release date within the limit.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
