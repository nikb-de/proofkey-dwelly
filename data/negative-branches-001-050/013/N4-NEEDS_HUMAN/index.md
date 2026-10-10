# Case 013-N4: Recipient disputes a recorded failed delivery attempt (Code change needs supervisor sign-off)

## Case details

- **Source role:** Dispatch review team, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-14 09:00:00 UTC
- **Escalated:** 2026-02-14 10:05:00 UTC
- **Updated:** 2026-02-14 11:00:00 UTC
- **Completed:** 2026-02-14 11:00:00 UTC
- **Primary shipment:** DL-013
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 013, events 001–003 retained; branch NEEDS_HUMAN

## Context

Tracking support reports a failed-attempt scan for DL-013 at 08:40 UTC on 2026-02-14, with the route record not yet reviewed. Yara Elt, the recipient, was at home but did not hear the intercom, and asks for a review and a new visit on the morning of 2026-02-15. This branch diverges after event 003: Code change needs supervisor sign-off.

## Initial request

We can book a repeat attempt, but changing or annotating a disputed failed-attempt code needs operations supervisor sign-off. We have not changed the record and will not issue a finding until a supervisor decides.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Register DL-013 with the Operations supervisor queue by email, giving the 08:40 scan, Yara's statement, the source events, the exact question of whether the attempt code stands, and that the 2026-02-15 morning attempt is pending.

- **Recipient:** Operations supervisor queue, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** ESCALATE_OPERATOR (workflow sheet E)

## Outcome

The supervisor queue accepts the case with a reference and a next-update time; nothing is decided, and the repeat attempt still needs its own confirmation.

## Boundaries and remaining work

Must not: Do not ask the review team to change the exception code without sign-off, and do not tell Yara that the attempt record was wrong.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
