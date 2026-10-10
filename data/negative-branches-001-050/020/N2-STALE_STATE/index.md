# Case 020-N2: A multi-parcel order arrives with one parcel still outstanding (Next-day route full after locating carton)

## Case details

- **Source role:** Parcel trace team, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-21 09:00:00 UTC
- **Escalated:** 2026-02-21 10:30:00 UTC
- **Updated:** 2026-02-21 11:20:00 UTC
- **Completed:** 2026-02-21 11:20:00 UTC
- **Primary task reference:** TG-020
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 020, events 001–003 retained; branch STALE_STATE

## Context

Parcel support reports that order TG-020 consists of DL-020-A, DL-020-B and DL-020-C, that A and B have delivery scans while C has only an inbound depot scan, and that all three are required. Eris Kael, the recipient, has two cartons, names DL-020-C as missing, and is available on 2026-02-22. This branch diverges after event 003: Next-day route full after locating carton.

## Initial request

DL-020-C has been located in depot stock. Capacity on the 2026-02-22 route for this area filled at 10:15 UTC. Available: delivery on 2026-02-23, 09:00–13:00 UTC, or depot collection from 2026-02-22, 10:00 UTC. Nothing is booked.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask Eris in the Customer portal to choose between delivery on 2026-02-23, 09:00–13:00 UTC and depot collection from 2026-02-22, 10:00 UTC, and book nothing until Eris answers.

- **Recipient:** Eris Kael, recipient
- **Channel:** Customer portal
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** ASK_CUSTOMER (workflow sheet B)

## Outcome

Eris chooses and the trace team confirms the booking or collection readiness; neither reconciles the parcel count.

## Boundaries and remaining work

Must not: Do not book the 2026-02-23 delivery because Eris wants the carton; Eris said only that 2026-02-22 is available.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
