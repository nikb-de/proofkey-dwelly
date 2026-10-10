# Case 013-N1: Recipient disputes a recorded failed delivery attempt (Handset and route sheet disagree)

## Case details

- **Source role:** Dispatch review team, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-14 09:00:00 UTC
- **Escalated:** 2026-02-14 09:45:00 UTC
- **Updated:** 2026-02-14 11:00:00 UTC
- **Completed:** 2026-02-14 11:00:00 UTC
- **Primary shipment:** DL-013
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 013, events 001–003 retained; branch CONFLICTING_RECORDS

## Context

Tracking support reports a failed-attempt scan for DL-013 at 08:40 UTC on 2026-02-14, with the route record not yet reviewed. Yara Elt, the recipient, was at home but did not hear the intercom, and asks for a review and a new visit on the morning of 2026-02-15. This branch diverges after event 003: Handset and route sheet disagree.

## Initial request

First check: the handset logs the 08:40 UTC attempt with reason 'Recipient absent'. The route sheet for the same stop records 'No access, gate locked'. The two reasons do not agree. No repeat attempt is booked yet.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Keep both entries and ask the Dispatch review team by email for the handset location record and the driver's statement for the 08:40 attempt, with the 2026-02-15 morning attempt booked as a separate step.

- **Recipient:** Dispatch review team, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** RECONCILE_CONFLICT (workflow sheet E)

## Outcome

The review team reports a finding supported by the location record, and the repeat attempt is confirmed separately; neither proves fault or a handover.

## Boundaries and remaining work

Must not: Do not pick one reason and tell Yara that the gate was locked or that nobody was home; neither entry is a review finding.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
