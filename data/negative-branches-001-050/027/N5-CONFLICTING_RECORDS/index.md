# Case 027-N5: Customer receives another customer's parcel (Receipt recorded, parcel still there)

## Case details

- **Source role:** Tovin Esk, reporting customer
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-28 09:00:00 UTC
- **Escalated:** 2026-03-01 12:05:00 UTC
- **Updated:** 2026-03-01 13:15:00 UTC
- **Completed:** 2026-03-01 13:15:00 UTC
- **Primary task reference:** MD-027
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 027, events 001–004 retained; branch CONFLICTING_RECORDS

## Context

Carrier intake record MD-027 matches the wrong parcel to label reference WP-027 and verifies Tovin Esk and the collection address; collection from the reporting customer is allowed, and the other recipient's address must not enter the thread. Tovin holds the unopened parcel, asks for collection, and says his own order has not arrived. This branch diverges after event 004: Receipt recorded, parcel still there.

## Initial request

I got a notice that the parcel was collected from me at 11:35 UTC. Nobody collected anything from me today. The other parcel is still sealed in my hallway.

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Keep both COL-027 and Tovin's report, and ask Misdelivery collections what evidence supports the 11:35 collection and which parcel the driver took.

- **Recipient:** Misdelivery collections, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** RECONCILE_CONFLICT (workflow sheet E)

## Outcome

The carrier confirms where WP-027 physically is and logs both accounts; this decides no fault and does not affect the trace of Tovin's own order.

## Boundaries and remaining work

Must not: Do not tell Tovin that the receipt proves he handed the parcel over, and do not treat WP-027 as back in carrier custody.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
