# Case 007-N2: Pickup deadline is too short for the recipient (No supervisor decision on expiry day)

## Case details

- **Source role:** Ciro Fale, recipient
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-08 09:00:00 UTC
- **Escalated:** 2026-02-09 08:30:00 UTC
- **Updated:** 2026-02-09 11:20:00 UTC
- **Completed:** 2026-02-09 11:20:00 UTC
- **Primary shipment:** DL-007
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 007, events 001–003 retained; branch NO_REPLY

## Context

Sedgeglass Counter holds DL-007 until 2026-02-09, 18:00 UTC; its local policy allows a single two-day extension if requested before expiry and stock capacity permits, and it currently has capacity. Ciro Fale's trip ends on 2026-02-10 and he asks for DL-007 to be kept until 2026-02-11, not returned. This branch diverges after event 003: No supervisor decision on expiry day.

## Initial request

Has the counter agreed to keep DL-007? My tracking page still shows a collection deadline of 2026-02-09, 18:00 UTC, and I am away until tomorrow. I do not want it sent back.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Send the Sedgeglass Counter supervisor one reminder by Email that the extension was requested before expiry and needs a decision before 18:00 UTC today, when the return timer runs, and tell Ciro no answer has arrived yet.

- **Recipient:** Sedgeglass Counter supervisor
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** WAIT_WITH_DEADLINE (workflow sheet E)

## Outcome

The supervisor's written decision before 18:00 or the recorded expiry closes the branch; neither proves collection.

## Boundaries and remaining work

Must not: Tell Ciro the parcel is kept until 2026-02-11, or treat the supervisor's silence as approval.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
