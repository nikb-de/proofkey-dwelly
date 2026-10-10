# Case 035-N1: Merchant has received the return but the refund review has not started (Review form errors on receipt upload)

## Case details

- **Source role:** Refunds team, Tallowmere Goods
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-08 09:00:00 UTC
- **Escalated:** 2026-03-08 09:31:00 UTC
- **Updated:** 2026-03-08 10:15:00 UTC
- **Completed:** 2026-03-08 10:15:00 UTC
- **Primary task reference:** TG-035
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 035, events 001–003 retained; branch CHANNEL_FAILURE

## Context

Tallowmere Goods' warehouse issued inline receipt WH-035 for return RT-035 / TG-035 at 08:10 UTC, but its receiving role does not approve refunds and no refund review exists. Melli Orven asks the desk to pass the receipt to the team that handles refunds. This branch diverges after event 003: Review form errors on receipt upload.

## Initial request

Automated notice. Your message about TG-035 reached the refunds mailbox, but the review form returned error RVW-422 when attaching WH-035. The notice cannot show whether a review case was saved.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Email the Refunds team and ask whether a review is registered for TG-035 with WH-035, stating that the request will not be resubmitted until it answers.

- **Recipient:** Refunds team, Tallowmere Goods
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** VERIFY_FIRST (workflow sheet R)

## Outcome

The Refunds team confirms one registered review, or none and one resubmission confirmed once; a registered review is not an approved refund or payment.

## Boundaries and remaining work

Must not: Do not resubmit or tell Melli a review has started; a second submission can open two reviews on one return.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
