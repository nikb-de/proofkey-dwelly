# Case 020-N5: A multi-parcel order arrives with one parcel still outstanding (Recipient stops the remaining delivery)

## Case details

- **Source role:** Eris Kael, recipient
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-21 09:00:00 UTC
- **Escalated:** 2026-02-21 11:00:00 UTC
- **Updated:** 2026-02-21 11:50:00 UTC
- **Completed:** 2026-02-21 11:50:00 UTC
- **Primary task reference:** TG-020
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 020, events 001–004 retained; branch CUSTOMER_CANCELS

## Context

Parcel support reports that order TG-020 consists of DL-020-A, DL-020-B and DL-020-C, that A and B have delivery scans while C has only an inbound depot scan, and that all three are required. Eris Kael, the recipient, has two cartons, names DL-020-C as missing, and is available on 2026-02-22. This branch diverges after event 004: Recipient stops the remaining delivery.

## Initial request

Please stop the delivery of DL-020-C. I have asked the seller to cancel TG-020, and I plan to send A and B back.

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Record the stop with the Parcel trace team by email, forbid any new action on DL-020-C, and ask what had already been executed, including its allocation to the 2026-02-22 route.

- **Recipient:** Parcel trace team, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** RECORD_STOP (workflow sheet F)

## Outcome

The trace team confirms the stop and the actual state of DL-020-C; A and B stay delivered, and no return or refund is established.

## Boundaries and remaining work

Must not: Do not arrange a collection of A and B or promise a refund; the return and refund belong to the seller and the Returns desk.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
