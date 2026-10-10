# Case 049-N3: Duplicate delivery service charge appears on a business invoice (Invoice paid in full mid-review)

## Case details

- **Source role:** Vera Senn, Mossline Press finance coordinator
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-22 09:00:00 UTC
- **Escalated:** 2026-03-22 09:40:00 UTC
- **Updated:** 2026-03-22 10:45:00 UTC
- **Completed:** 2026-03-22 10:45:00 UTC
- **Primary shipment:** DL-049
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 049, events 001–003 retained; branch STALE_STATE

## Context

Mossline Press invoice INV-049 carries two GBP 18.00 lines for the same DL-049 delivery service and date, total GBP 36.00. Finance coordinator Vera Senn asks for a billing review before paying and states that neither line is paid. This branch diverges after event 003: Invoice paid in full mid-review.

## Initial request

Bad news. Our payment run released INV-049 in full, GBP 36.00, at 09:35 UTC before I could hold it. So both lines are now paid. What happens to the review?

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Email Business billing that the customer reports paying GBP 36.00 at 09:35 UTC and ask what settlement options apply if the duplicate is confirmed.

- **Recipient:** Business billing, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** GET_OPTIONS (workflow sheet B)

## Outcome

Billing states the options and Vera chooses; a credit on account and a refund are different outcomes, and neither is cash received yet.

## Boundaries and remaining work

Must not: Tell Vera a credit note will put the money back in her bank, or request a refund she has not chosen.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
