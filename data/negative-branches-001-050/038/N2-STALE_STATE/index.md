# Case 038-N2: Failed delivery has returned to sender and the customer still wants the order (Returned unit reallocated before approval)

## Case details

- **Source role:** Reshipment authorisations, Tallowmere Goods
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-11 09:00:00 UTC
- **Escalated:** 2026-03-11 09:44:00 UTC
- **Updated:** 2026-03-11 10:40:00 UTC
- **Completed:** 2026-03-11 10:40:00 UTC
- **Primary shipment:** DL-038
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 038, events 001–003 retained; branch STALE_STATE

## Context

DL-038 for TG-038 is back in Tallowmere Goods' stock after a failed delivery and accepted as reshippable; the account team has authenticated Sella Nove's order session with stored destination Apartment 2, 31 Rillstone Walk, Merrow Quay, and a new dispatch needs merchant approval. Sella still wants the order and confirms that destination. This branch diverges after event 003: Returned unit reallocated before approval.

## Initial request

The returned unit for TG-038 was released to general stock at 09:30 and has been allocated to another order. We can approve dispatch of a new unit when stock arrives on 2026-03-14, or cancel TG-038. We will not choose for the customer.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask Sella in the Customer portal one question: wait for a new unit from 2026-03-14, or cancel TG-038.

- **Recipient:** Sella Nove, customer
- **Channel:** Customer portal
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** ASK_CUSTOMER (workflow sheet B)

## Outcome

Sella's choice is recorded and the merchant confirms it; a later dispatch date is not dispatch, and any refund after cancellation is a separate merchant step.

## Boundaries and remaining work

Must not: Do not tell Sella the reshipment is approved on the earlier premise that the returned item is ready, and do not describe cancellation as a refund.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
