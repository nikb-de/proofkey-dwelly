# Case 017-N5: Delivery notification contains an unusable tracking link (Portal shows delivered, recipient has nothing)

## Case details

- **Source role:** Vela Morn, recipient
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-18 09:00:00 UTC
- **Escalated:** 2026-02-18 10:00:00 UTC
- **Updated:** 2026-02-18 11:00:00 UTC
- **Completed:** 2026-02-18 11:00:00 UTC
- **Primary shipment:** DL-017
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 017, events 001–004 retained; branch CONFLICTING_RECORDS

## Context

Notification support reports that the DL-017 notification path was truncated by its template, the account-linked notification belongs to this recipient, and the shipment reference is intact. Vela Morn, the recipient, asks for the correct way to find the parcel in the order portal. This branch diverges after event 004: Portal shows delivered, recipient has nothing.

## Initial request

I entered DL-017 under Shipments. The page shows the parcel as delivered yesterday at 17:20 UTC. I have not received any parcel.

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Keep both the portal status and Vela's statement, and ask Tracking support by email for the scan record behind the delivered status of DL-017, telling Vela only that it is being checked.

- **Recipient:** Tracking support, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** RECONCILE_CONFLICT (workflow sheet E)

## Outcome

Tracking support returns the scan record and any handover detail; that clarifies the record, not where the parcel is or who has it.

## Boundaries and remaining work

Must not: Do not tell Vela that DL-017 is delivered because the portal says so, and do not open a loss claim before the scan record is reviewed.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
