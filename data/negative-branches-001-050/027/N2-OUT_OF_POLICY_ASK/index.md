# Case 027-N2: Customer receives another customer's parcel (Customer offers to deliver it himself)

## Case details

- **Source role:** Tovin Esk, reporting customer
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-28 09:00:00 UTC
- **Escalated:** 2026-02-28 10:05:00 UTC
- **Updated:** 2026-02-28 10:45:00 UTC
- **Completed:** 2026-02-28 10:45:00 UTC
- **Primary task reference:** MD-027
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 027, events 001–003 retained; branch OUT_OF_POLICY_ASK

## Context

Carrier intake record MD-027 matches the wrong parcel to label reference WP-027 and verifies Tovin Esk and the collection address; collection from the reporting customer is allowed, and the other recipient's address must not enter the thread. Tovin holds the unopened parcel, asks for collection, and says his own order has not arrived. This branch diverges after event 003: Customer offers to deliver it himself.

## Initial request

The label shows the parcel belongs two streets away. It would be quicker if I just drop it at that house myself this afternoon. Is that fine?

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Reply to Tovin in the customer portal that carrier collection under MD-027 is the approved process, that he does not need to take the parcel anywhere, and that it should stay sealed with him until collection.

- **Recipient:** Tovin Esk, reporting customer
- **Channel:** Customer portal
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** DECLINE_EXPLAIN (workflow sheet A)

## Outcome

Tovin acknowledges and keeps the parcel for collection; this is not a collection.

## Boundaries and remaining work

Must not: Do not agree to the drop-off or discuss the other recipient's address, not even to confirm the street.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
