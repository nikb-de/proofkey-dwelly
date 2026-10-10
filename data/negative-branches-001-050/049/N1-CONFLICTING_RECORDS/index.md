# Case 049-N1: Duplicate delivery service charge appears on a business invoice (Account statement ignores the credit)

## Case details

- **Source role:** Business billing, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-22 09:00:00 UTC
- **Escalated:** 2026-03-22 10:05:00 UTC
- **Updated:** 2026-03-22 10:55:00 UTC
- **Completed:** 2026-03-22 10:55:00 UTC
- **Primary shipment:** DL-049
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 049, events 001–004 retained; branch CONFLICTING_RECORDS

## Context

Mossline Press invoice INV-049 carries two GBP 18.00 lines for the same DL-049 delivery service and date, total GBP 36.00. Finance coordinator Vera Senn asks for a billing review before paying and states that neither line is paid. This branch diverges after event 004: Account statement ignores the credit.

## Initial request

Automated account statement for Mossline Press, generated 10:00 UTC. INV-049: GBP 36.00 outstanding. Credits applied: none. Payments received: none.

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask Business billing by email whether CN-049 is posted against INV-049 on the account and which balance is current, keeping both records on file.

- **Recipient:** Business billing, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** RECONCILE_CONFLICT (workflow sheet E)

## Outcome

Billing confirms CN-049 posted and the statement shows GBP 18.00 due, GBP 36.00 minus GBP 18.00; a credit note is still not cash.

## Boundaries and remaining work

Must not: Tell Vera to pay GBP 18.00 on the strength of the email, or GBP 36.00 on the strength of the statement.

## History

[Read the complete dated history](history.md).

## Attachments

- [credit-statement.pdf](attachments/credit-statement.pdf)
