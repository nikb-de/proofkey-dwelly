# Case 013-N3: Recipient disputes a recorded failed delivery attempt (Requested morning no longer available)

## Case details

- **Source role:** Dispatch review team, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-14 09:00:00 UTC
- **Escalated:** 2026-02-14 10:00:00 UTC
- **Updated:** 2026-02-14 10:55:00 UTC
- **Completed:** 2026-02-14 10:55:00 UTC
- **Primary shipment:** DL-013
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 013, events 001–003 retained; branch STALE_STATE

## Context

Tracking support reports a failed-attempt scan for DL-013 at 08:40 UTC on 2026-02-14, with the route record not yet reviewed. Yara Elt, the recipient, was at home but did not hear the intercom, and asks for a review and a new visit on the morning of 2026-02-15. This branch diverges after event 003: Requested morning no longer available.

## Initial request

Review started. Morning capacity on 2026-02-15 for this route was filled at 09:35 UTC. Available repeat attempts: 2026-02-15, 13:00–17:00 UTC, or 2026-02-16, 09:00–12:00 UTC, both at no charge. Nothing is booked.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask Yara in the Customer portal to choose between 2026-02-15, 13:00–17:00 UTC and 2026-02-16, 09:00–12:00 UTC, and pass only that choice to the review team.

- **Recipient:** Yara Elt, recipient
- **Channel:** Customer portal
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** ASK_CUSTOMER (workflow sheet B)

## Outcome

Yara chooses one window and the review team confirms the booking; this is a repeat attempt booking, not a handover or a review finding.

## Boundaries and remaining work

Must not: Do not book the 2026-02-15 afternoon because the date matches; Yara offered the morning only.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
