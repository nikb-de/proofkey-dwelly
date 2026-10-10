# Case 043-N1: Freight collection needs confirmed pallet dimensions and weight (Shipper offers estimates, not measurements)

## Case details

- **Source role:** Nessa Dray, Orris Span shipping coordinator
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-16 09:00:00 UTC
- **Escalated:** 2026-03-16 09:40:00 UTC
- **Updated:** 2026-03-16 10:40:00 UTC
- **Completed:** 2026-03-16 10:40:00 UTC
- **Primary shipment:** DL-043
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 043, events 001–003 retained; branch AMBIGUOUS_REPLY

## Context

The carrier cannot allocate a collection vehicle for DL-043 because the pallet's dimension and weight fields are blank. Nessa Dray at Orris Span says the pallet is ready and asks which measurements the carrier needs. This branch diverges after event 003: Shipper offers estimates, not measurements.

## Initial request

It is a normal euro pallet, maybe 1.4 m high with the load. Weight is about 300 kg, I would guess; we have not put it on the scale. Can you enter that and get the collection moving?

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask Nessa in the business portal for the measured length, width and total height and the scale gross weight of DL-043, stating that estimates cannot go to the carrier.

- **Recipient:** Nessa Dray, Orris Span shipping coordinator
- **Channel:** Business portal
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** ASK_CUSTOMER (workflow sheet A)

## Outcome

Nessa supplies measured values with their source; that is still the shipper's measurement, not a carrier weighing or an allocation.

## Boundaries and remaining work

Must not: Enter 120 x 80 cm, 140 cm and 300 kg yourself from the euro-pallet description and the guess.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
