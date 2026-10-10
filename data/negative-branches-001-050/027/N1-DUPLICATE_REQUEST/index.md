# Case 027-N1: Customer receives another customer's parcel (Two collection jobs for WP-027)

## Case details

- **Source role:** Misdelivery collections, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-28 09:00:00 UTC
- **Escalated:** 2026-02-28 09:50:00 UTC
- **Updated:** 2026-02-28 10:30:00 UTC
- **Completed:** 2026-02-28 10:30:00 UTC
- **Primary task reference:** MD-027
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 027, events 001–003 retained; branch DUPLICATE_REQUEST

## Context

Carrier intake record MD-027 matches the wrong parcel to label reference WP-027 and verifies Tovin Esk and the collection address; collection from the reporting customer is allowed, and the other recipient's address must not enter the thread. Tovin holds the unopened parcel, asks for collection, and says his own order has not arrived. This branch diverges after event 003: Two collection jobs for WP-027.

## Initial request

We now have two collection jobs for WP-027 at the same address: one raised by our intake team from MD-027 at 09:05 UTC and one from your 09:25 email. Which one should we run?

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Tell Misdelivery collections by email that both jobs are the same collection of WP-027 under MD-027, and ask them to keep the 09:05 job and link the desk's request to it.

- **Recipient:** Misdelivery collections, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** RESOLVE_DUPLICATE (workflow sheet F)

## Outcome

The carrier confirms one live collection job for WP-027; one live job is not a collection.

## Boundaries and remaining work

Must not: Do not cancel both jobs, let two drivers attend, or open a third request.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
