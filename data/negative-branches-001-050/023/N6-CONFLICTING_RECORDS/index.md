# Case 023-N6: A leaking parcel is reported at the depot (Lane board shows parcel moved)

## Case details

- **Source role:** Depot shift coordinator, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-24 09:00:00 UTC
- **Escalated:** 2026-02-24 10:10:00 UTC
- **Updated:** 2026-02-24 10:50:00 UTC
- **Completed:** 2026-02-24 10:50:00 UTC
- **Primary shipment:** DL-023
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 023, events 001–004 retained; branch CONFLICTING_RECORDS

## Context

DL-023 is on receiving lane L3 with a visible wet patch under one carton; contents are unassessed and depot staff have stopped moving it and are keeping clear. The depot shift coordinator asks for the carrier's safety lead to take over and forbids routing it to a driver or asking the customer to collect it. This branch diverges after event 004: Lane board shows parcel moved.

## Initial request

Our lane board shows DL-023 scanned off L3 to the returns cage at 09:40 UTC by a loader. The safety queue says the parcel is isolated from normal operations. I cannot see it on L3 now. Which record is right?

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Send both records to the Safety lead through the safety incident queue under SAFE-023, ask where the parcel physically is and who moved it, and tell the depot shift coordinator that the question is with the safety lead.

- **Recipient:** Safety lead, Plover Arc Logistics
- **Channel:** Safety incident queue
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** RECONCILE_CONFLICT (workflow sheet E)

## Outcome

The safety lead confirms the parcel's location under SAFE-023 control; this establishes neither the contents, nor fault, nor liability.

## Boundaries and remaining work

Must not: Do not decide which record is right, blame the loader, or ask anyone to go and check the returns cage.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
