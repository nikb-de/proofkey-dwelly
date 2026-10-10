# Case 002-N2: Apartment number missing from the delivery address (Door description instead of apartment number)

## Case details

- **Source role:** Tarin Mave, recipient
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-03 09:00:00 UTC
- **Escalated:** 2026-02-03 09:42:00 UTC
- **Updated:** 2026-02-03 10:15:00 UTC
- **Completed:** 2026-02-03 10:15:00 UTC
- **Primary shipment:** DL-002
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 002, events 001–003 retained; branch AMBIGUOUS_REPLY

## Context

DL-002 is on an incomplete-address hold because 18 Copperfin Court, Merrow Quay has several apartments and the order has none; the account team verified the recipient's order-linked portal session. Tarin Mave asks in the Customer portal what is needed. This branch diverges after event 003: Door description instead of apartment number.

## Initial request

It is the top-floor flat on the left as you come up the stairs, the one with the green door. There is no number on the door itself, but the driver cannot miss it.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask Tarin in the Customer portal for the apartment number or name as shown on the building's bell panel or post boxes, and nothing else.

- **Recipient:** Tarin Mave, recipient
- **Channel:** Customer portal
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** ASK_CUSTOMER (workflow sheet A)

## Outcome

Tarin gives an apartment identifier in the thread; the hold stays until the Address desk applies it, and nothing is delivered.

## Boundaries and remaining work

Must not: Send 'top floor, left, green door' to the Address desk as the apartment, or ask for an entry code, phone number or floor plan.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
