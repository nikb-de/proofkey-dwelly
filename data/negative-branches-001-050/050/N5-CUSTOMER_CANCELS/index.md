# Case 050-N5: Customer requests reimbursement of a guaranteed-delivery surcharge after confirmed delay (Customer withdraws after credit posted)

## Case details

- **Source role:** Nella Voss, customer
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-23 09:00:00 UTC
- **Escalated:** 2026-03-23 10:00:00 UTC
- **Updated:** 2026-03-23 10:50:00 UTC
- **Completed:** 2026-03-23 10:50:00 UTC
- **Primary shipment:** DL-050
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 050, events 001–004 retained; branch CUSTOMER_CANCELS

## Context

DL-050 was guaranteed by 2026-03-23 08:00 UTC with a GBP 7.50 surcharge and was handed over at 08:40 after a carrier sorting delay, with no exclusion recorded. Customer Nella Voss asks the desk to request the GBP 7.50 under the booking terms, which allow a credit after billing review. This branch diverges after event 004: Customer withdraws after credit posted.

## Initial request

Please withdraw my guarantee request for DL-050. The sender has already covered the surcharge for me, so I do not want to claim it twice.

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Record the stop with Nella as owner, tell her in the customer portal that GC-050 for GBP 7.50 was posted before her message, and inform Guarantee billing by email of the withdrawal for its decision on GC-050.

- **Recipient:** Nella Voss, customer
- **Channel:** Customer portal
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** RECORD_STOP (workflow sheet F)

## Outcome

Billing states what it does with GC-050; the stop prevents new steps but does not undo the posted credit.

## Boundaries and remaining work

Must not: Reverse GC-050 on the desk's own initiative, or tell Nella the request never went through.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
