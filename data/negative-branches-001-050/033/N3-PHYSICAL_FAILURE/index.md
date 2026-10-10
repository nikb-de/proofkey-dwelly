# Case 033-N3: Courier misses a booked return collection (Driver declines an unsealed return carton)

## Case details

- **Source role:** Collection driver, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-06 09:00:00 UTC
- **Escalated:** 2026-03-07 11:50:00 UTC
- **Updated:** 2026-03-07 13:10:00 UTC
- **Completed:** 2026-03-07 13:10:00 UTC
- **Primary task reference:** RT-033
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 033, events 001–004 retained; branch PHYSICAL_FAILURE

## Context

Plover Arc Logistics missed the collection of approved return RT-033, the parcel is still with the customer and rebooking is free. Virin Lask asks for a new collection on 2026-03-07 within 10:00–14:00. This branch diverges after event 004: Driver declines an unsealed return carton.

## Initial request

At the address for RT-033 at 11:45. The carton is open and the item is loose inside, so it does not meet the return packaging requirements. I have not accepted it into custody. Customer still holds the parcel.

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Record the declined collection with Collections control by email, citing the driver's packaging reason, and ask for the driver's record of the attempt and the specific requirement not met.

- **Recipient:** Collections control, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** RECORD_REFUSAL (workflow sheet D)

## Outcome

The declined attempt and its reason are on record; the parcel is still with Virin, and a new booking, carrier custody and refund all remain separate steps.

## Boundaries and remaining work

Must not: Do not tell Virin the return has been collected, and do not rebook at once; carrier custody has not started and the packaging fault must be known first.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
