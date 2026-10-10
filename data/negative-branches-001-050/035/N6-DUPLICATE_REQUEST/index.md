# Case 035-N6: Merchant has received the return but the refund review has not started (Phone call opens a second review)

## Case details

- **Source role:** Refunds team, Tallowmere Goods
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-08 09:00:00 UTC
- **Escalated:** 2026-03-08 10:20:00 UTC
- **Updated:** 2026-03-08 11:00:00 UTC
- **Completed:** 2026-03-08 11:00:00 UTC
- **Primary task reference:** TG-035
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 035, events 001–004 retained; branch DUPLICATE_REQUEST

## Context

Tallowmere Goods' warehouse issued inline receipt WH-035 for return RT-035 / TG-035 at 08:10 UTC, but its receiving role does not approve refunds and no refund review exists. Melli Orven asks the desk to pass the receipt to the team that handles refunds. This branch diverges after event 004: Phone call opens a second review.

## Initial request

A second review, RF-035-B, was opened at 10:05 from the customer's phone call, also citing WH-035. TG-035 now has two open reviews. Please confirm how to proceed.

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Reply to the Refunds team that RF-035-B duplicates RF-035 for the same receipt WH-035, and ask it to link RF-035-B to RF-035 and keep RF-035 as the single review.

- **Recipient:** Refunds team, Tallowmere Goods
- **Channel:** Email
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** RESOLVE_DUPLICATE (workflow sheet F)

## Outcome

The Refunds team confirms RF-035-B is closed and RF-035 continues with its update due by 2026-03-10, 16:00 UTC; nothing is approved or paid.

## Boundaries and remaining work

Must not: Do not leave both reviews open; two reviews on one receipt can lead to two decisions or two payments.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
