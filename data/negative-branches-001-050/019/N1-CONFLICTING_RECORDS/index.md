# Case 019-N1: Severe weather suspends the delivery route (Tracker shows arrival estimate during suspension)

## Case details

- **Source role:** Tessa Jorn, recipient
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-20 09:00:00 UTC
- **Escalated:** 2026-02-20 09:40:00 UTC
- **Updated:** 2026-02-20 10:30:00 UTC
- **Completed:** 2026-02-20 10:30:00 UTC
- **Primary shipment:** DL-019
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 019, events 001–003 retained; branch CONFLICTING_RECORDS

## Context

Route safety control has suspended route MQ-19 for severe weather, DL-019 is secure in depot stock, and Dispatch will review conditions at 15:00 UTC with no approved delivery estimate. Tessa Jorn, the recipient, asks whether the parcel is coming today and when to expect an update. This branch diverges after event 003: Tracker shows arrival estimate during suspension.

## Initial request

The tracker has just changed to 'Out for delivery, arriving 12:00–14:00'. The weather alert said the route is suspended. Which is right? Should I stay in?

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Keep both records and ask Dispatch by email which status of DL-019 is current and whether the 12:00–14:00 estimate is approved, telling Tessa only that it is being checked.

- **Recipient:** Dispatch, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** RECONCILE_CONFLICT (workflow sheet E)

## Outcome

Dispatch confirms the current status and approved wording; a tracker entry or review time is not a delivery time.

## Boundaries and remaining work

Must not: Do not tell Tessa to expect DL-019 between 12:00 and 14:00 because the tracker shows it.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
