# Case 023-N4: A leaking parcel is reported at the depot (No acknowledgement before shift handover)

## Case details

- **Source role:** Depot shift coordinator, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-24 09:00:00 UTC
- **Escalated:** 2026-02-24 09:55:00 UTC
- **Updated:** 2026-02-24 10:22:00 UTC
- **Completed:** 2026-02-24 10:22:00 UTC
- **Primary shipment:** DL-023
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 023, events 001–003 retained; branch NO_REPLY

## Context

DL-023 is on receiving lane L3 with a visible wet patch under one carton; contents are unassessed and depot staff have stopped moving it and are keeping clear. The depot shift coordinator asks for the carrier's safety lead to take over and forbids routing it to a driver or asking the customer to collect it. This branch diverges after event 003: No acknowledgement before shift handover.

## Initial request

Thirty minutes and no acknowledgement from the safety lead. Lane L3 is still closed and staff remain clear. My shift hands over at 10:30 UTC and I need a named safety owner on record before then.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Send one urgent reminder to the Safety lead through the safety incident queue citing the 10:30 UTC handover, record the safety lead as owner and 10:30 UTC as the deadline, and tell the depot shift coordinator that nothing is acknowledged yet.

- **Recipient:** Safety lead, Plover Arc Logistics
- **Channel:** Safety incident queue
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** WAIT_WITH_DEADLINE (workflow sheet E)

## Outcome

The safety lead acknowledges the incident and takes ownership; acknowledgement does not confirm isolation or assess the contents.

## Boundaries and remaining work

Must not: Do not name the desk or a driver as safety owner, and do not suggest moving the parcel to free the lane.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
