# Case 019-N2: Severe weather suspends the delivery route (Driver offers run during suspension)

## Case details

- **Source role:** Route driver, route MQ-19, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-20 09:00:00 UTC
- **Escalated:** 2026-02-20 09:50:00 UTC
- **Updated:** 2026-02-20 10:35:00 UTC
- **Completed:** 2026-02-20 10:35:00 UTC
- **Primary shipment:** DL-019
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 019, events 001–003 retained; branch UNAUTHORISED_REPLY

## Context

Route safety control has suspended route MQ-19 for severe weather, DL-019 is secure in depot stock, and Dispatch will review conditions at 15:00 UTC with no approved delivery estimate. Tessa Jorn, the recipient, asks whether the parcel is coming today and when to expect an update. This branch diverges after event 003: Driver offers run during suspension.

## Initial request

I'm at the depot with the MQ-19 load. The main road looks passable now. I can take DL-019 out at 13:00 if the customer really needs it. Want me to go?

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Give the driver no instruction, leave the route decision with Dispatch and route safety control, and tell Tessa nothing until Dispatch's approved update arrives.

- **Recipient:** Dispatch, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** SEPARATE_AUTHORITY (workflow sheet A)

## Outcome

Dispatch issues approved wording or a route decision; the driver's offer authorises nothing.

## Boundaries and remaining work

Must not: Do not tell the driver to go, and do not tell Tessa that DL-019 may arrive at 13:00; a driver's offer does not lift a route suspension.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
