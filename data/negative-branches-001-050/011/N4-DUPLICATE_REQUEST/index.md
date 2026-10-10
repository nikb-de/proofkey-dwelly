# Case 011-N4: Shipment tracking has not updated after depot arrival (Second locate task opened by phone)

## Case details

- **Source role:** Tracking support, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-12 09:00:00 UTC
- **Escalated:** 2026-02-12 09:40:00 UTC
- **Updated:** 2026-02-12 10:15:00 UTC
- **Completed:** 2026-02-12 10:15:00 UTC
- **Primary shipment:** DL-011
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 011, events 001–003 retained; branch DUPLICATE_REQUEST

## Context

Tracking support reports that DL-011's last public scan is the destination depot arrival at 06:15 UTC on 2026-02-12, with no sort or route scan and no confirmed storage position. Mera Olt, the recipient, asks whether the parcel is physically at the depot. This branch diverges after event 003: Second locate task opened by phone.

## Initial request

Mera Olt also called us at 09:30 UTC about DL-011. We raised a second locate task for the destination depot at 09:34 UTC. Both tasks are now open in the Depot work queue.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask the destination depot through the Depot work queue to link the 09:34 task to the 09:25 task, work DL-011 once and report one scan with one storage position.

- **Recipient:** Destination depot, Plover Arc Logistics
- **Channel:** Depot work queue
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** RESOLVE_DUPLICATE (workflow sheet F)

## Outcome

The depot confirms one open task with the other linked or closed; this settles the duplicate, not the parcel's location.

## Boundaries and remaining work

Must not: Do not let both tasks run and relay two separate answers to Mera, and do not cancel the original 09:25 request in favour of the copy.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
