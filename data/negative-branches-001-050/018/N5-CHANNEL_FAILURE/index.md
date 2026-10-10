# Case 018-N5: Shipment is approaching its return-to-sender deadline (Hold system timed out applying choice)

## Case details

- **Source role:** Exception desk, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-19 09:00:00 UTC
- **Escalated:** 2026-02-19 10:02:00 UTC
- **Updated:** 2026-02-19 10:40:00 UTC
- **Completed:** 2026-02-19 10:40:00 UTC
- **Primary shipment:** DL-018
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 018, events 001–004 retained; branch CHANNEL_FAILURE

## Context

The Exception desk reports that DL-018 enters return-to-sender processing at 16:00 UTC on 2026-02-19 unless the customer selects redelivery or depot collection on 2026-02-20, both currently available. No choice is recorded, and the desk asks Iona to contact authorised recipient Nalo Vere before the cutoff. This branch diverges after event 004: Hold system timed out applying choice.

## Initial request

We received your relay of Nalo Vere's depot collection choice. Our hold system timed out when we applied it at 09:58 UTC. We cannot yet see whether the return is cancelled.

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask the Exception desk in Dispatch chat to read DL-018's saved return status and collection assignment before any second application, stating the 16:00 UTC cutoff.

- **Recipient:** Exception desk, Plover Arc Logistics
- **Channel:** Dispatch chat
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** VERIFY_FIRST (workflow sheet R)

## Outcome

The desk reports the saved state, and if the choice is absent, one re-application is confirmed before 16:00 UTC; this cancels the return, not collection.

## Boundaries and remaining work

Must not: Do not ask for the choice to be applied again straight away, and do not tell Nalo that the return is cancelled.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
