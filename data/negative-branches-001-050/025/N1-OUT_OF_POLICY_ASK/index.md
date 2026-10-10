# Case 025-N1: Carrier confirms a parcel is lost after investigation (Customer asks desk to self-approve)

## Case details

- **Source role:** Aven Korrin, recipient
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-26 09:00:00 UTC
- **Escalated:** 2026-02-26 09:38:00 UTC
- **Updated:** 2026-02-26 10:15:00 UTC
- **Completed:** 2026-02-26 10:15:00 UTC
- **Primary shipment:** DL-025
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 025, events 001–003 retained; branch OUT_OF_POLICY_ASK

## Context

Carrier trace INV-025 confirms DL-025 lost, and that finding does not itself create a merchant replacement order. Aven Korrin still needs the kettle from TG-025, chooses a like-for-like replacement rather than a refund, and asks for the merchant to approve it. This branch diverges after event 003: Customer asks desk to self-approve.

## Initial request

The carrier has already confirmed the kettle is lost, so there is nothing left to check. Please approve the replacement yourself and book it on today's van. I do not want to wait for the merchant.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Reply to Aven in the customer portal that only Replacement authorisations, Tallowmere Goods, can approve and create the replacement, that her request is with them, and that the desk cannot book a shipment for an order that does not yet exist.

- **Recipient:** Aven Korrin, recipient
- **Channel:** Customer portal
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** DECLINE_EXPLAIN (workflow sheet A)

## Outcome

Aven acknowledges that approval rests with the merchant; the loss finding still creates no replacement order.

## Boundaries and remaining work

Must not: Do not approve the replacement or book a van on the strength of INV-025.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
