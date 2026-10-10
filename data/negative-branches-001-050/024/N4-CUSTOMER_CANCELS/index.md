# Case 024-N4: Tracking says delivered but the recipient has no parcel (Recipient found parcel, cancels investigation)

## Case details

- **Source role:** Sorin Vaal, recipient
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-25 09:00:00 UTC
- **Escalated:** 2026-02-25 12:30:00 UTC
- **Updated:** 2026-02-25 13:20:00 UTC
- **Completed:** 2026-02-25 13:20:00 UTC
- **Primary shipment:** DL-024
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 024, events 001–004 retained; branch CUSTOMER_CANCELS

## Context

DL-024 shows delivered at 08:10 UTC, but tracking support has not reviewed the handover record or route stop and has verified only the shipment and recipient account match. Sorin Vaal says no one in his household has the parcel and asks for a carrier investigation. This branch diverges after event 004: Recipient found parcel, cancels investigation.

## Initial request

Found it. A neighbour two doors down took it in this morning and has just handed it to me. Please cancel the investigation.

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Record Sorin's stop on INV-024 and email Delivery investigations, Plover Arc Logistics, that the recipient withdraws the request and now holds the parcel, asking what has already been done on the case.

- **Recipient:** Delivery investigations, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** RECORD_STOP (workflow sheet F)

## Outcome

The carrier confirms INV-024 is withdrawn and states what was already done; this does not establish where or to whom the parcel was handed over.

## Boundaries and remaining work

Must not: Do not close INV-024 yourself or report the 08:10 delivered scan as confirmed; the withdrawal is the recipient's statement, not a carrier finding.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
