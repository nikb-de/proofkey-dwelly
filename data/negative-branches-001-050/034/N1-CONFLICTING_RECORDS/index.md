# Case 034-N1: Returned parcel has reached the carrier depot but not the merchant warehouse (Carrier delivery scan, no merchant receipt)

## Case details

- **Source role:** Warehouse receiving, Tallowmere Goods
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-07 09:00:00 UTC
- **Escalated:** 2026-03-08 08:30:00 UTC
- **Updated:** 2026-03-08 11:30:00 UTC
- **Completed:** 2026-03-08 11:30:00 UTC
- **Primary task reference:** RT-034
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 034, events 001–003 retained; branch CONFLICTING_RECORDS

## Context

The last scan for return RT-034 is at the carrier's return depot at 07:40 UTC on 2026-03-07, with no merchant receiving scan, so Plover Arc Logistics still holds it. Elrin Kove asks for a trace through to the moment the merchant actually has it. This branch diverges after event 003: Carrier delivery scan, no merchant receipt.

## Initial request

We have no RT-034 carton at our returns bay and no receiving record for TG-034. We are told the carrier portal shows RT-034 delivered to us at 16:20 UTC yesterday. Nothing here matches that scan.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Email the Returns trace team with both records, its 16:20 delivery scan and the warehouse's statement that nothing was received, and ask for the proof of delivery: location, time and who signed.

- **Recipient:** Returns trace team, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** RECONCILE_CONFLICT (workflow sheet E)

## Outcome

The trace team's proof of delivery is registered and reported as it stands; merchant receipt is established only by a warehouse receipt, and inspection and refund stay open.

## Boundaries and remaining work

Must not: Do not tell Elrin the merchant has the return because the carrier scanned it delivered, and do not declare it lost.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
