# Case 025-N3: Carrier confirms a parcel is lost after investigation (Kettle out of stock, backorder offered)

## Case details

- **Source role:** Replacement authorisations, Tallowmere Goods
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-26 09:00:00 UTC
- **Escalated:** 2026-02-26 09:45:00 UTC
- **Updated:** 2026-02-26 10:30:00 UTC
- **Completed:** 2026-02-26 10:30:00 UTC
- **Primary shipment:** DL-025
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 025, events 001–003 retained; branch STALE_STATE

## Context

Carrier trace INV-025 confirms DL-025 lost, and that finding does not itself create a merchant replacement order. Aven Korrin still needs the kettle from TG-025, chooses a like-for-like replacement rather than a refund, and asks for the merchant to approve it. This branch diverges after event 003: Kettle out of stock, backorder offered.

## Initial request

TG-025: the same kettle went out of stock at 09:30 UTC today. We can approve a like-for-like replacement on backorder, with stock due 2026-03-06, or a refund now. We need the customer's choice first.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask Aven in the customer portal one question: does she choose the backordered kettle with stock due 2026-03-06 or a refund now.

- **Recipient:** Aven Korrin, recipient
- **Channel:** Customer portal
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** ASK_CUSTOMER (workflow sheet B)

## Outcome

Aven states one offered option; her choice is not an approval, an order or a payment.

## Boundaries and remaining work

Must not: Do not treat her earlier choice of a replacement as acceptance of a backorder, and do not tell her a replacement is approved.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
