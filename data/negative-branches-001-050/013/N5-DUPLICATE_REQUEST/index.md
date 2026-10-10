# Case 013-N5: Recipient disputes a recorded failed delivery attempt (Tracker redelivery request runs in parallel)

## Case details

- **Source role:** Tracking support, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-14 09:00:00 UTC
- **Escalated:** 2026-02-14 09:50:00 UTC
- **Updated:** 2026-02-14 10:40:00 UTC
- **Completed:** 2026-02-14 10:40:00 UTC
- **Primary shipment:** DL-013
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 013, events 001–003 retained; branch DUPLICATE_REQUEST

## Context

Tracking support reports a failed-attempt scan for DL-013 at 08:40 UTC on 2026-02-14, with the route record not yet reviewed. Yara Elt, the recipient, was at home but did not hear the intercom, and asks for a review and a new visit on the morning of 2026-02-15. This branch diverges after event 003: Tracker redelivery request runs in parallel.

## Initial request

Yara Elt also used the public tracker at 09:15 UTC to request a redelivery for DL-013. That request is queued with Scheduling. Your review request to the Dispatch review team is a separate item.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask the Dispatch review team by email to link the 09:15 tracker request to the review request and confirm that exactly one repeat attempt is booked for DL-013.

- **Recipient:** Dispatch review team, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** RESOLVE_DUPLICATE (workflow sheet F)

## Outcome

The review team confirms one booked attempt with the other request linked or closed; this does not prove the attempt will succeed or settle the review.

## Boundaries and remaining work

Must not: Do not let Scheduling and the review team each book an attempt, and do not cancel Yara's own request without linking it.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
