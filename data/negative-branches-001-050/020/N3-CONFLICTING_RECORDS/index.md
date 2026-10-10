# Case 020-N3: A multi-parcel order arrives with one parcel still outstanding (Delivery scan but carton not received)

## Case details

- **Source role:** Eris Kael, recipient
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-21 09:00:00 UTC
- **Escalated:** 2026-02-22 11:10:00 UTC
- **Updated:** 2026-02-22 12:20:00 UTC
- **Completed:** 2026-02-22 12:20:00 UTC
- **Primary task reference:** TG-020
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 020, events 001–004 retained; branch CONFLICTING_RECORDS

## Context

Parcel support reports that order TG-020 consists of DL-020-A, DL-020-B and DL-020-C, that A and B have delivery scans while C has only an inbound depot scan, and that all three are required. Eris Kael, the recipient, has two cartons, names DL-020-C as missing, and is available on 2026-02-22. This branch diverges after event 004: Delivery scan but carton not received.

## Initial request

The tracker says DL-020-C was delivered at 10:55 UTC today. I have been home all morning and I still have only two cartons, A and B.

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Keep both records and ask the Parcel trace team by email for the evidence behind the 10:55 scan, including the handover location and the driver's record, keeping TG-020 open.

- **Recipient:** Parcel trace team, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** RECONCILE_CONFLICT (workflow sheet E)

## Outcome

The trace team returns evidence for the 10:55 scan; that clarifies the record, not where the carton is, and the order count stays at two of three.

## Boundaries and remaining work

Must not: Do not tell Eris that DL-020-C is delivered or mark TG-020 complete because the scan says so, and do not open a loss claim yet.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
