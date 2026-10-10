# Case 050-N4: Customer requests reimbursement of a guaranteed-delivery surcharge after confirmed delay (Customer filed her own claim too)

## Case details

- **Source role:** Nella Voss, customer
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-23 09:00:00 UTC
- **Escalated:** 2026-03-23 09:40:00 UTC
- **Updated:** 2026-03-23 10:20:00 UTC
- **Completed:** 2026-03-23 10:20:00 UTC
- **Primary shipment:** DL-050
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 050, events 001–003 retained; branch DUPLICATE_REQUEST

## Context

DL-050 was guaranteed by 2026-03-23 08:00 UTC with a GBP 7.50 surcharge and was handed over at 08:40 after a carrier sorting delay, with no exclusion recorded. Customer Nella Voss asks the desk to request the GBP 7.50 under the booking terms, which allow a credit after billing review. This branch diverges after event 003: Customer filed her own claim too.

## Initial request

I also filed a guarantee claim for DL-050 myself in the carrier's customer portal at 09:15 UTC, before you replied. I hope that speeds things up.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Email Guarantee billing that Nella's 09:15 UTC claim and the desk's 09:25 UTC request concern the same GBP 7.50 surcharge and ask that they be handled as one.

- **Recipient:** Guarantee billing, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** RESOLVE_DUPLICATE (workflow sheet F)

## Outcome

Billing confirms one claim for DL-050; that is not yet an approval or a credit.

## Boundaries and remaining work

Must not: Let both run, which could post two GBP 7.50 credits, GBP 15.00 in total.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
