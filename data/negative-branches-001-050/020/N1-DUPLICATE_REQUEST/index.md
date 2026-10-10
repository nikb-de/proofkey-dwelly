# Case 020-N1: A multi-parcel order arrives with one parcel still outstanding (Order-level trace duplicates carton trace)

## Case details

- **Source role:** Parcel trace team, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-21 09:00:00 UTC
- **Escalated:** 2026-02-21 09:40:00 UTC
- **Updated:** 2026-02-21 10:30:00 UTC
- **Completed:** 2026-02-21 10:30:00 UTC
- **Primary task reference:** TG-020
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 020, events 001–003 retained; branch DUPLICATE_REQUEST

## Context

Parcel support reports that order TG-020 consists of DL-020-A, DL-020-B and DL-020-C, that A and B have delivery scans while C has only an inbound depot scan, and that all three are required. Eris Kael, the recipient, has two cartons, names DL-020-C as missing, and is available on 2026-02-22. This branch diverges after event 003: Order-level trace duplicates carton trace.

## Initial request

We now have two open traces: yours for DL-020-C and one opened by Parcel support at 09:15 UTC for the whole order TG-020. Each trace can arrange a delivery.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask the Parcel trace team by email to link the order-level trace to the DL-020-C trace and run one trace with one delivery arrangement for DL-020-C.

- **Recipient:** Parcel trace team, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** RESOLVE_DUPLICATE (workflow sheet F)

## Outcome

The trace team confirms one open trace for DL-020-C with the other linked; this settles the duplicate, not the carton's location.

## Boundaries and remaining work

Must not: Do not let both traces book a delivery, and do not let the order-level trace close TG-020 on the A and B delivery scans.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
