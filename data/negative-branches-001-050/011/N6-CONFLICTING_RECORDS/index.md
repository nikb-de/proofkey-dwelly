# Case 011-N6: Shipment tracking has not updated after depot arrival (Tracker says out for delivery)

## Case details

- **Source role:** Tracking support, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-12 09:00:00 UTC
- **Escalated:** 2026-02-12 10:10:00 UTC
- **Updated:** 2026-02-12 10:50:00 UTC
- **Completed:** 2026-02-12 10:50:00 UTC
- **Primary shipment:** DL-011
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 011, events 001–004 retained; branch CONFLICTING_RECORDS

## Context

Tracking support reports that DL-011's last public scan is the destination depot arrival at 06:15 UTC on 2026-02-12, with no sort or route scan and no confirmed storage position. Mera Olt, the recipient, asks whether the parcel is physically at the depot. This branch diverges after event 004: Tracker says out for delivery.

## Initial request

Public tracking for DL-011 now shows 'Out for delivery' timestamped 09:48 UTC. The depot's 09:45 scan places it in sort cage C-17, not allocated to a van. We have not checked which entry is correct.

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Keep both records and ask the destination depot through the Depot work queue for a fresh physical check of cage C-17 and any van allocation record for DL-011, telling Mera only that the status is being checked.

- **Recipient:** Destination depot, Plover Arc Logistics
- **Channel:** Depot work queue
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** RECONCILE_CONFLICT (workflow sheet E)

## Outcome

The depot confirms one current physical location with a new scan; this resolves the location record, not a delivery time.

## Boundaries and remaining work

Must not: Do not tell Mera that DL-011 is out for delivery today because the public tracker says so, and do not discard the depot's 09:45 cage scan.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
