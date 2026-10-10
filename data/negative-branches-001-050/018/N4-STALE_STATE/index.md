# Case 018-N4: Shipment is approaching its return-to-sender deadline (Chosen depot collection withdrawn)

## Case details

- **Source role:** Exception desk, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-19 09:00:00 UTC
- **Escalated:** 2026-02-19 10:00:00 UTC
- **Updated:** 2026-02-19 10:45:00 UTC
- **Completed:** 2026-02-19 10:45:00 UTC
- **Primary shipment:** DL-018
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 018, events 001–004 retained; branch STALE_STATE

## Context

The Exception desk reports that DL-018 enters return-to-sender processing at 16:00 UTC on 2026-02-19 unless the customer selects redelivery or depot collection on 2026-02-20, both currently available. No choice is recorded, and the desk asks Iona to contact authorised recipient Nalo Vere before the cutoff. This branch diverges after event 004: Chosen depot collection withdrawn.

## Initial request

Before applying the choice: depot collection on 2026-02-20 was withdrawn at 09:52 UTC because the collection counter is closed that day for stocktake. Redelivery on 2026-02-20 remains available. The 16:00 UTC cutoff is unchanged.

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Call Nalo Vere on the verified number, state that depot collection on 2026-02-20 is no longer available, and ask whether to choose redelivery on 2026-02-20 before 16:00 UTC.

- **Recipient:** Nalo Vere, recipient
- **Channel:** Call transcript
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** ASK_CUSTOMER (workflow sheet B)

## Outcome

Nalo chooses and the Exception desk confirms the return is cancelled before 16:00 UTC; that is not delivery or collection.

## Boundaries and remaining work

Must not: Do not switch Nalo to redelivery because it is the only remaining option; Nalo's consent was for depot collection.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
