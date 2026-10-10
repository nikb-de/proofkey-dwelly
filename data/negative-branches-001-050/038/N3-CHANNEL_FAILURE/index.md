# Case 038-N3: Failed delivery has returned to sender and the customer still wants the order (Approval form errors mid-creation)

## Case details

- **Source role:** Reshipment authorisations, Tallowmere Goods
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-11 09:00:00 UTC
- **Escalated:** 2026-03-11 09:39:00 UTC
- **Updated:** 2026-03-11 10:20:00 UTC
- **Completed:** 2026-03-11 10:20:00 UTC
- **Primary shipment:** DL-038
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 038, events 001–003 retained; branch CHANNEL_FAILURE

## Context

DL-038 for TG-038 is back in Tallowmere Goods' stock after a failed delivery and accepted as reshippable; the account team has authenticated Sella Nove's order session with stored destination Apartment 2, 31 Rillstone Walk, Merrow Quay, and a new dispatch needs merchant approval. Sella still wants the order and confirms that destination. This branch diverges after event 003: Approval form errors mid-creation.

## Initial request

System notice. The approval form for TG-038 errored at 09:38 while creating the shipment record. The notice cannot show whether a new shipment was created. No shipment reference was returned.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Email Reshipment authorisations and ask whether a new shipment record exists for TG-038, stating that no second approval request will be sent until it answers.

- **Recipient:** Reshipment authorisations, Tallowmere Goods
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** VERIFY_FIRST (workflow sheet R)

## Outcome

Reshipment authorisations confirms one new shipment reference, or none and one resubmission confirmed once; a reference is not dispatch or receipt.

## Boundaries and remaining work

Must not: Do not resend the approval request; a second record can dispatch two parcels for one order.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
