# Case 003-N4: Driver cannot access a gated residential building (Driver pulled away before recipient arrives)

## Case details

- **Source role:** Dispatch, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-04 09:00:00 UTC
- **Escalated:** 2026-02-04 09:33:00 UTC
- **Updated:** 2026-02-04 10:20:00 UTC
- **Completed:** 2026-02-04 10:20:00 UTC
- **Primary shipment:** DL-003
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 003, events 001–003 retained; branch STALE_STATE

## Context

Route driver Fen Orlo is outside the shut pedestrian gate at 7 Sedgeglass Mews with DL-003 and has not left the parcel. Dispatch asks the desk to contact Elva Kesh on the verified order callback route, not to request a reusable gate code, and says the driver can wait until 10:00 UTC. This branch diverges after event 003: Driver pulled away before recipient arrives.

## Initial request

Update on DL-003: we pulled Fen Orlo away from 7 Sedgeglass Mews at 09:30 for an urgent collection on the same route. DL-003 is still on the van. The 10:00 UTC wait no longer applies.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask Dispatch in Dispatch chat for DL-003's next attempt options, and tell Elva on the verified callback route that the driver has left and she should not come to the gate.

- **Recipient:** Dispatch, Plover Arc Logistics
- **Channel:** Dispatch chat
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** GET_OPTIONS (workflow sheet B)

## Outcome

Dispatch's attempt options reach Elva and she chooses; nothing is delivered until a driver's handover scan exists.

## Boundaries and remaining work

Must not: Ask Fen Orlo to turn back on the desk's own instruction, or promise Elva a new attempt time before Dispatch offers one.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
