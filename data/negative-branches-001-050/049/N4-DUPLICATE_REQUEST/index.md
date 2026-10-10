# Case 049-N4: Duplicate delivery service charge appears on a business invoice (Two review tickets risk double credit)

## Case details

- **Source role:** Business billing, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-22 09:00:00 UTC
- **Escalated:** 2026-03-22 09:45:00 UTC
- **Updated:** 2026-03-22 10:20:00 UTC
- **Completed:** 2026-03-22 10:20:00 UTC
- **Primary shipment:** DL-049
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 049, events 001–003 retained; branch DUPLICATE_REQUEST

## Context

Mossline Press invoice INV-049 carries two GBP 18.00 lines for the same DL-049 delivery service and date, total GBP 36.00. Finance coordinator Vera Senn asks for a billing review before paying and states that neither line is paid. This branch diverges after event 003: Two review tickets risk double credit.

## Initial request

We hold two review requests for INV-049: ticket BR-049, raised by Mossline Press in our billing portal at 09:05 UTC, and your email of 09:25 UTC. Unless told otherwise, each will be reviewed and credited separately.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask Business billing by email to link the desk's request to ticket BR-049 and run one review, with at most one GBP 18.00 credit.

- **Recipient:** Business billing, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** RESOLVE_DUPLICATE (workflow sheet F)

## Outcome

Billing confirms one ticket for INV-049; the merge does not decide whether a duplicate exists.

## Boundaries and remaining work

Must not: Let both requests run, which could post two GBP 18.00 credits and show INV-049 at GBP 0.00.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
