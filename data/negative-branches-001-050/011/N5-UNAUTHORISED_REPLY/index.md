# Case 011-N5: Shipment tracking has not updated after depot arrival (Unverified caller asks for collection)

## Case details

- **Source role:** Caller giving the name Mera Olt, unregistered number
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-12 09:00:00 UTC
- **Escalated:** 2026-02-12 09:45:00 UTC
- **Updated:** 2026-02-12 10:25:00 UTC
- **Completed:** 2026-02-12 10:25:00 UTC
- **Primary shipment:** DL-011
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 011, events 001–003 retained; branch UNAUTHORISED_REPLY

## Context

Tracking support reports that DL-011's last public scan is the destination depot arrival at 06:15 UTC on 2026-02-12, with no sort or route scan and no confirmed storage position. Mera Olt, the recipient, asks whether the parcel is physically at the depot. This branch diverges after event 003: Unverified caller asks for collection.

## Initial request

I'm calling about DL-011. I'm Mera, but I can't log in to the portal from this phone. Tell me which cage it is in and hold it at the depot. My brother will collect it this afternoon.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Act on nothing from the call and ask Mera Olt in the verified Customer portal thread whether Mera made a collection request by phone.

- **Recipient:** Mera Olt, recipient
- **Channel:** Customer portal
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** SEPARATE_AUTHORITY (workflow sheet A)

## Outcome

Mera answers in the verified portal thread; that confirms who is asking, not that a hold or third-party collection is permitted.

## Boundaries and remaining work

Must not: Do not disclose DL-011's status or storage position to the caller, and do not ask the depot to hold the parcel for a third-party collector.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
