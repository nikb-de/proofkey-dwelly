# Case 019-N3: Severe weather suspends the delivery route (Recipient asks for roadside handover)

## Case details

- **Source role:** Tessa Jorn, recipient
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-20 09:00:00 UTC
- **Escalated:** 2026-02-20 09:45:00 UTC
- **Updated:** 2026-02-20 10:20:00 UTC
- **Completed:** 2026-02-20 10:20:00 UTC
- **Primary shipment:** DL-019
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 019, events 001–003 retained; branch OUT_OF_POLICY_ASK

## Context

Route safety control has suspended route MQ-19 for severe weather, DL-019 is secure in depot stock, and Dispatch will review conditions at 15:00 UTC with no approved delivery estimate. Tessa Jorn, the recipient, asks whether the parcel is coming today and when to expect an update. This branch diverges after event 003: Recipient asks for roadside handover.

## Initial request

If the van can reach the main road junction, I can meet the driver there this afternoon. Please ask them to bring DL-019 today.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Tell Tessa in the Customer portal that route safety control has suspended the route, so no delivery or roadside handover can be arranged, and that the next step is the 15:00 UTC review.

- **Recipient:** Tessa Jorn, recipient
- **Channel:** Customer portal
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** DECLINE_EXPLAIN (workflow sheet A)

## Outcome

Tessa acknowledges and the suspension stands; the 15:00 UTC review is not a restart time.

## Boundaries and remaining work

Must not: Do not ask Dispatch or a driver to arrange a roadside meeting, and do not promise delivery today.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
