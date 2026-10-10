# Case 043-N2: Freight collection needs confirmed pallet dimensions and weight (Scale ticket contradicts stated weight)

## Case details

- **Source role:** Nessa Dray, Orris Span shipping coordinator
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-16 09:00:00 UTC
- **Escalated:** 2026-03-16 09:53:00 UTC
- **Updated:** 2026-03-16 10:35:00 UTC
- **Completed:** 2026-03-16 10:35:00 UTC
- **Primary shipment:** DL-043
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 043, events 001–004 retained; branch CONFLICTING_RECORDS

## Context

The carrier cannot allocate a collection vehicle for DL-043 because the pallet's dimension and weight fields are blank. Nessa Dray at Orris Span says the pallet is ready and asks which measurements the carrier needs. This branch diverges after event 004: Scale ticket contradicts stated weight.

## Initial request

Attaching our warehouse scale ticket ST-043 for DL-043 for your file. The ticket reads gross 370 kg, printed 09:44 UTC on 2026-03-16 from scale 2. Collection from our dock 1 as usual.

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask Nessa in the business portal which gross weight is correct for DL-043, 310 kg in her message or 370 kg on ticket ST-043, and send nothing to the carrier meanwhile.

- **Recipient:** Nessa Dray, Orris Span shipping coordinator
- **Channel:** Business portal
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** RECONCILE_CONFLICT (workflow sheet E)

## Outcome

Nessa confirms one measured weight with its source; it remains a shipper figure, not a carrier weighing or an allocation.

## Boundaries and remaining work

Must not: Pass 310 kg to the carrier because it came first, or average or round the two figures.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
