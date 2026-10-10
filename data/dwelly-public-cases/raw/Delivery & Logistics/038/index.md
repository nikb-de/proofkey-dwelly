# Case 038: Failed delivery has returned to sender and the customer still wants the order

## Case details

- **Source role:** Sella Nove, customer
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-11 09:00:00 UTC
- **Escalated:** 2026-03-11 09:10:00 UTC
- **Updated:** 2026-03-11 09:50:00 UTC
- **Completed:** 2026-03-11 09:50:00 UTC
- **Primary shipment:** DL-038
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC

## Context

The failed original delivery is physically back at the merchant. The recipient still wants the item and has confirmed the existing delivery details.

## Initial request

I still want the order. I checked my authenticated order details: Apartment 2, 31 Rillstone Walk, Merrow Quay is correct. Please ask for reshipment there.

## Overview

The escalation snapshot comprises history events 001–002. Event 003 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask the merchant to approve reshipment to the customer's verified delivery details.

- **Recipient:** Reshipment authorisations, Tallowmere Goods
- **Channel:** Email
- **Recorded action:** [History event 003](history.md#event-003)

## Outcome

The merchant confirms a new shipment reference; receipt remains pending.

## Boundaries and remaining work

New shipment reference does not prove dispatch or receipt; do not reuse the old delivered status.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
