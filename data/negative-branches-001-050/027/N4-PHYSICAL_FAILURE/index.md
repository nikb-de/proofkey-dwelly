# Case 027-N4: Customer receives another customer's parcel (Collection attempt fails, card left)

## Case details

- **Source role:** Misdelivery collections, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-28 09:00:00 UTC
- **Escalated:** 2026-02-28 16:40:00 UTC
- **Updated:** 2026-02-28 17:30:00 UTC
- **Completed:** 2026-02-28 17:30:00 UTC
- **Primary task reference:** MD-027
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 027, events 001–003 retained; branch PHYSICAL_FAILURE

## Context

Carrier intake record MD-027 matches the wrong parcel to label reference WP-027 and verifies Tovin Esk and the collection address; collection from the reporting customer is allowed, and the other recipient's address must not enter the thread. Tovin holds the unopened parcel, asks for collection, and says his own order has not arrived. This branch diverges after event 003: Collection attempt fails, card left.

## Initial request

Collection of WP-027 was attempted at 16:15 UTC at the verified address. No one answered and a card was left. The parcel was not collected and no new attempt is booked.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask Misdelivery collections by email to book the next collection attempt under MD-027 and confirm the slot, then pass that slot to Tovin through the customer portal.

- **Recipient:** Misdelivery collections, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** REQUEST_ACTION (workflow sheet D)

## Outcome

The carrier confirms a booked attempt; a booked attempt is not a collection, and Tovin's own order stays a separate trace.

## Boundaries and remaining work

Must not: Do not ask Tovin to take the parcel to a depot or to the addressee, and do not record WP-027 as collected.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
