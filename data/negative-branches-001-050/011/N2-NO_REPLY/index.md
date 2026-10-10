# Case 011-N2: Shipment tracking has not updated after depot arrival (Depot leaves locate task unstarted)

## Case details

- **Source role:** Depot work queue, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-12 09:00:00 UTC
- **Escalated:** 2026-02-12 13:30:00 UTC
- **Updated:** 2026-02-12 13:58:00 UTC
- **Completed:** 2026-02-12 13:58:00 UTC
- **Primary shipment:** DL-011
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 011, events 001–003 retained; branch NO_REPLY

## Context

Tracking support reports that DL-011's last public scan is the destination depot arrival at 06:15 UTC on 2026-02-12, with no sort or route scan and no confirmed storage position. Mera Olt, the recipient, asks whether the parcel is physically at the depot. This branch diverges after event 003: Depot leaves locate task unstarted.

## Initial request

DL-011 locate task, opened 09:25 UTC: status open, not started. No comment from the destination depot. Tasks not started by the 14:00 UTC shift change are carried to the next shift.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Send one reminder on the same Depot work queue task asking the destination depot for the physical scan and storage position before the 14:00 UTC shift change, and record the depot as owner with that deadline.

- **Recipient:** Destination depot, Plover Arc Logistics
- **Channel:** Depot work queue
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** WAIT_WITH_DEADLINE (workflow sheet B)

## Outcome

The depot posts a fresh physical scan with a storage position, or the queue records the task passing to the next shift; neither proves dispatch or delivery.

## Boundaries and remaining work

Must not: Do not open a second task, and do not tell Mera the parcel is at the depot on the strength of the 06:15 arrival scan.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
