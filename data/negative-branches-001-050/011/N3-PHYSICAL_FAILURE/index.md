# Case 011-N3: Shipment tracking has not updated after depot arrival (Depot search does not find parcel)

## Case details

- **Source role:** Destination depot, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-12 09:00:00 UTC
- **Escalated:** 2026-02-12 10:20:00 UTC
- **Updated:** 2026-02-12 11:10:00 UTC
- **Completed:** 2026-02-12 11:10:00 UTC
- **Primary shipment:** DL-011
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 011, events 001–003 retained; branch PHYSICAL_FAILURE

## Context

Tracking support reports that DL-011's last public scan is the destination depot arrival at 06:15 UTC on 2026-02-12, with no sort or route scan and no confirmed storage position. Mera Olt, the recipient, asks whether the parcel is physically at the depot. This branch diverges after event 003: Depot search does not find parcel.

## Initial request

We searched the inbound bay, the sort cages and the exceptions shelf for DL-011 between 09:40 and 10:15 UTC. The parcel was not found. The 06:15 arrival scan remains the last scan. We have not raised a trace.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask the Parcel trace team by email to open a trace for DL-011, citing the 06:15 arrival scan and the depot's negative search from 09:40 to 10:15 UTC, and to report a trace reference.

- **Recipient:** Parcel trace team, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** REQUEST_ACTION (workflow sheet C)

## Outcome

The trace team confirms an open trace with a reference; this proves a search is registered, not where DL-011 is or that it is lost.

## Boundaries and remaining work

Must not: Do not tell Mera that the parcel is lost or offer a claim or refund, and do not repeat that it is at the depot because the arrival scan says so.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
