# Case 022-N5: A delivered household item is confirmed broken (Customer stops replacement, wants money)

## Case details

- **Source role:** Remi Dask, recipient
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-23 09:00:00 UTC
- **Escalated:** 2026-02-23 10:12:00 UTC
- **Updated:** 2026-02-23 10:55:00 UTC
- **Completed:** 2026-02-23 10:55:00 UTC
- **Primary shipment:** DL-022
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 022, events 001–004 retained; branch CUSTOMER_CANCELS

## Context

Tallowmere Goods has accepted damage on TG-022, a ceramic table lamp with a separated base, for replacement assessment, but no replacement approval is recorded. Remi Dask prefers the same lamp to a refund and asks for the merchant to approve a replacement. This branch diverges after event 004: Customer stops replacement, wants money.

## Initial request

Please stop my replacement request. I have decided I want my money back instead of another lamp. I do not want a second lamp delivered.

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Record Remi's stop against TG-022-R and email Replacement authorisations, Tallowmere Goods, asking them to hold the replacement and state what is already done, passing on his refund request for their decision.

- **Recipient:** Replacement authorisations, Tallowmere Goods
- **Channel:** Email
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** RECORD_STOP (workflow sheet F)

## Outcome

The merchant confirms the hold on TG-022-R and what was already executed; a stopped replacement is not a refund, and the refund decision stays with the merchant.

## Boundaries and remaining work

Must not: Do not tell Remi that TG-022-R is cancelled or that a refund is approved before the merchant confirms either.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
