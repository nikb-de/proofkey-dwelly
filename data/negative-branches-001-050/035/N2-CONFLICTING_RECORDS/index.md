# Case 035-N2: Merchant has received the return but the refund review has not started (Refunds record shows return not received)

## Case details

- **Source role:** Refunds team, Tallowmere Goods
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-08 09:00:00 UTC
- **Escalated:** 2026-03-08 09:55:00 UTC
- **Updated:** 2026-03-08 10:50:00 UTC
- **Completed:** 2026-03-08 10:50:00 UTC
- **Primary task reference:** TG-035
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 035, events 001–003 retained; branch CONFLICTING_RECORDS

## Context

Tallowmere Goods' warehouse issued inline receipt WH-035 for return RT-035 / TG-035 at 08:10 UTC, but its receiving role does not approve refunds and no refund review exists. Melli Orven asks the desk to pass the receipt to the team that handles refunds. This branch diverges after event 003: Refunds record shows return not received.

## Initial request

Our order record for TG-035 shows RT-035 as not received and holds no WH-035. We register reviews only against a receipt posted to the order. We have not opened a review.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Email Warehouse receiving, Tallowmere Goods, with both records, its inline receipt WH-035 from 08:10 and the refunds record showing RT-035 not received, and ask it to confirm whether WH-035 is posted to the TG-035 order record.

- **Recipient:** Warehouse receiving, Tallowmere Goods
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** RECONCILE_CONFLICT (workflow sheet E)

## Outcome

Warehouse receiving confirms whether WH-035 is posted so the Refunds team can register against it; neither record is overwritten, and registration would still not be refund approval.

## Boundaries and remaining work

Must not: Do not ask the Refunds team to treat the desk's copy of WH-035 as posted, and do not tell Melli the return is missing.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
