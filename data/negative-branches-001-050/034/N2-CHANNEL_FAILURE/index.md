# Case 034-N2: Returned parcel has reached the carrier depot but not the merchant warehouse (Trace ticket creation fails)

## Case details

- **Source role:** Returns trace team, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-07 09:00:00 UTC
- **Escalated:** 2026-03-07 09:27:00 UTC
- **Updated:** 2026-03-07 10:15:00 UTC
- **Completed:** 2026-03-07 10:15:00 UTC
- **Primary task reference:** RT-034
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 034, events 001–003 retained; branch CHANNEL_FAILURE

## Context

The last scan for return RT-034 is at the carrier's return depot at 07:40 UTC on 2026-03-07, with no merchant receiving scan, so Plover Arc Logistics still holds it. Elrin Kove asks for a trace through to the moment the merchant actually has it. This branch diverges after event 003: Trace ticket creation fails.

## Initial request

Automated reply. Your message was received, but trace creation for RT-034 failed with error TRC-500. If no trace reference reaches you, the request may not be registered.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask the Returns trace team by email whether a trace is open for RT-034, stating that no second trace request will be raised until it answers.

- **Recipient:** Returns trace team, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** VERIFY_FIRST (workflow sheet R)

## Outcome

The trace team confirms one open trace, or none and one resubmission confirmed once; an open trace does not move the parcel or prove merchant receipt.

## Boundaries and remaining work

Must not: Do not open a second trace through another team or channel; two traces on one parcel split the search and the record.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
