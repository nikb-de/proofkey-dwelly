# Case 050-N2: Customer requests reimbursement of a guaranteed-delivery surcharge after confirmed delay (Billing scan contradicts route record)

## Case details

- **Source role:** Guarantee billing, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-23 09:00:00 UTC
- **Escalated:** 2026-03-23 09:45:00 UTC
- **Updated:** 2026-03-23 10:45:00 UTC
- **Completed:** 2026-03-23 10:45:00 UTC
- **Primary shipment:** DL-050
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 050, events 001–003 retained; branch CONFLICTING_RECORDS

## Context

DL-050 was guaranteed by 2026-03-23 08:00 UTC with a GBP 7.50 surcharge and was handed over at 08:40 after a carrier sorting delay, with no exclusion recorded. Customer Nella Voss asks the desk to request the GBP 7.50 under the booking terms, which allow a credit after billing review. This branch diverges after event 003: Billing scan contradicts route record.

## Initial request

Our handover scan for DL-050 shows 07:55 UTC on 2026-03-23, inside the guarantee. On that basis the request is declined. No credit will be posted.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask Guarantee billing by email to check its 07:55 UTC scan against the service guarantees route record of 08:40 UTC and say which record it relies on.

- **Recipient:** Guarantee billing, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** RECONCILE_CONFLICT (workflow sheet E)

## Outcome

Billing confirms one handover time with its source and decides on that; even a reversed decline yields a credit, not cash.

## Boundaries and remaining work

Must not: Accept the decline and close, or tell Nella either time is wrong before billing answers.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
