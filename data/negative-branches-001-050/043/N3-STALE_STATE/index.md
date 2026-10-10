# Case 043-N3: Freight collection needs confirmed pallet dimensions and weight (Pallet rebuilt after it was measured)

## Case details

- **Source role:** Nessa Dray, Orris Span shipping coordinator
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-16 09:00:00 UTC
- **Escalated:** 2026-03-16 09:52:00 UTC
- **Updated:** 2026-03-16 10:45:00 UTC
- **Completed:** 2026-03-16 10:45:00 UTC
- **Primary shipment:** DL-043
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 043, events 001–004 retained; branch STALE_STATE

## Context

The carrier cannot allocate a collection vehicle for DL-043 because the pallet's dimension and weight fields are blank. Nessa Dray at Orris Span says the pallet is ready and asks which measurements the carrier needs. This branch diverges after event 004: Pallet rebuilt after it was measured.

## Initial request

Update on DL-043. After I measured, production added another layer of cartons to the pallet. It is now taller than 145 cm and heavier than 310 kg. I have not re-measured or re-weighed it yet.

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask Nessa in the business portal to re-measure the total height and re-weigh the gross weight of DL-043 as it now stands, before anything goes to the carrier.

- **Recipient:** Nessa Dray, Orris Span shipping coordinator
- **Channel:** Business portal
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** ASK_CUSTOMER (workflow sheet B)

## Outcome

Nessa supplies new measured height and weight for the pallet as built; that is still not a carrier check or an allocation.

## Boundaries and remaining work

Must not: Send the 120 x 100 x 145 cm, 310 kg values to the carrier, or add an estimate for the extra layer.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
