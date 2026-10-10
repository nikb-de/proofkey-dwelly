# Case 043-N5: Freight collection needs confirmed pallet dimensions and weight (Shipper silent before allocation cut-off)

## Case details

- **Source role:** Freight booking desk, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-16 09:00:00 UTC
- **Escalated:** 2026-03-16 13:00:00 UTC
- **Updated:** 2026-03-16 14:10:00 UTC
- **Completed:** 2026-03-16 14:10:00 UTC
- **Primary shipment:** DL-043
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 043, events 001–003 retained; branch NO_REPLY

## Context

The carrier cannot allocate a collection vehicle for DL-043 because the pallet's dimension and weight fields are blank. Nessa Dray at Orris Span says the pallet is ready and asks which measurements the carrier needs. This branch diverges after event 003: Shipper silent before allocation cut-off.

## Initial request

DL-043 still has blank dimension and weight fields. Collection allocations for 2026-03-17 close at 15:00 UTC today. After that, the earliest allocation we can consider is 2026-03-18.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Send Nessa one reminder in the business portal for the measured values, naming the 15:00 UTC cut-off, and record her as owner with that deadline.

- **Recipient:** Nessa Dray, Orris Span shipping coordinator
- **Channel:** Business portal
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** WAIT_WITH_DEADLINE (workflow sheet B)

## Outcome

Nessa supplies measured values before 15:00 UTC or the booking desk records the later date; the reminder allocates nothing.

## Boundaries and remaining work

Must not: Fill in typical pallet values to make the cut-off, or promise the booking desk a 2026-03-17 collection.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
