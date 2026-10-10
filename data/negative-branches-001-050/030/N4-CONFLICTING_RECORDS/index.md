# Case 030-N4: A high-value shipment lacks an accessible proof-of-delivery record (Two handover times disagree)

## Case details

- **Source role:** Iven Thoss, recipient
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-03 09:00:00 UTC
- **Escalated:** 2026-03-03 10:02:00 UTC
- **Updated:** 2026-03-03 10:50:00 UTC
- **Completed:** 2026-03-03 10:50:00 UTC
- **Primary shipment:** DL-030
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 030, events 001–004 retained; branch CONFLICTING_RECORDS

## Context

DL-030 belongs to authenticated recipient Iven Thoss; its delivery flag is present but the customer-facing handover record has not populated, and carrier support may release a redacted record through the verified thread. Iven confirms he received the camera accessory and asks for the matching handover record to reconcile the delivery time. This branch diverges after event 004: Two handover times disagree.

## Initial request

POD-030 says 08:20 UTC, but I signed for the parcel before I left home at about 07:55 UTC, and my order history shows delivered at 07:58 UTC. Which time is right?

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Keep both times on record and ask Secure shipment support which source produced the 08:20 UTC handover time and the 07:58 UTC order-history time.

- **Recipient:** Secure shipment support, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** RECONCILE_CONFLICT (workflow sheet E)

## Outcome

The carrier explains the source of each time; the explanation supports this handover only and is not universal proof.

## Boundaries and remaining work

Must not: Do not tell Iven that either time is correct, and do not edit or ask anyone to edit his order history to match POD-030.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
