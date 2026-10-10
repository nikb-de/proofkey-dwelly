# Case 040-N2: Cancelled order is packed but has not left the merchant warehouse (Stop task fails to sync)

## Case details

- **Source role:** Warehouse dispatch, Tallowmere Goods
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-13 09:00:00 UTC
- **Escalated:** 2026-03-13 09:27:00 UTC
- **Updated:** 2026-03-13 09:55:00 UTC
- **Completed:** 2026-03-13 09:55:00 UTC
- **Primary shipment:** DL-040
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 040, events 001–003 retained; branch CHANNEL_FAILURE

## Context

Tallowmere Goods authorised cancellation CAN-040 for TG-040 at 08:45 UTC while DL-040 sits packed in outbound cage O7 with no carrier handover scan; refund processing is a separate task. Order control asks the desk to get the warehouse to stop DL-040 before the next outbound sweep. This branch diverges after event 003: Stop task fails to sync.

## Initial request

Queue notice. The task for DL-040 hit a sync error at 09:26 and shows no assignee. The queue cannot confirm whether the stop instruction reached the cage O7 team.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask Warehouse dispatch in the Warehouse work queue whether a stop task for DL-040 is saved and assigned, stating that no second task will be posted until it answers and that the next outbound sweep is the limit.

- **Recipient:** Warehouse dispatch, Tallowmere Goods
- **Channel:** Warehouse work queue
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** VERIFY_FIRST (workflow sheet R)

## Outcome

Warehouse dispatch confirms one assigned stop task, or none and one resubmission; a saved task is not physical removal, and refund stays separate.

## Boundaries and remaining work

Must not: Do not post a second stop task or ask the carrier to refuse the parcel; parallel instructions can leave DL-040 in two states.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
