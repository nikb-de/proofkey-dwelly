# Case 004-N2: Recipient requests a call shortly before arrival (Callback request lost in channel rebuild)

## Case details

- **Source role:** Dispatch chat system, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-05 09:00:00 UTC
- **Escalated:** 2026-02-05 09:26:00 UTC
- **Updated:** 2026-02-05 10:05:00 UTC
- **Completed:** 2026-02-05 10:05:00 UTC
- **Primary shipment:** DL-004
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 004, events 001–003 retained; branch CHANNEL_FAILURE

## Context

DL-004 is on the 2026-02-06 afternoon route; Dispatch can add a call request to the verified number already in the order record but cannot guarantee an exact advance interval. Oren Sile asks for a call shortly before arrival on his saved order contact. This branch diverges after event 003: Callback request lost in channel rebuild.

## Initial request

Message from Iona Quill, Rivet Delivery Desk, to Dispatch: send status unknown. The 2026-02-06 afternoon route channel was being rebuilt at 09:25, and messages from that minute may not have reached the route card queue. No read receipt is recorded.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Email Dispatch asking whether the DL-004 route card already shows a call request to the verified saved number, and state that no second request will be sent until that is known.

- **Recipient:** Dispatch, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** VERIFY_FIRST (workflow sheet R)

## Outcome

Dispatch states what the route card shows; if absent, one request follows and is confirmed once, and a saved instruction is not a call or an arrival.

## Boundaries and remaining work

Must not: Repost the call request in Dispatch chat, or tell Oren it has been recorded.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
