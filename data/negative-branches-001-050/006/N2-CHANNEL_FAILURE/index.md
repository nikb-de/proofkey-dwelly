# Case 006-N2: Customer requests collection from a staffed pickup point (Routing ticket creation failed)

## Case details

- **Source role:** Routing request system, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-07 09:00:00 UTC
- **Escalated:** 2026-02-07 09:27:00 UTC
- **Updated:** 2026-02-07 10:05:00 UTC
- **Completed:** 2026-02-07 10:05:00 UTC
- **Primary shipment:** DL-006
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 006, events 001–003 retained; branch CHANNEL_FAILURE

## Context

Routing says DL-006 can be redirected without charge before route release, Copperfin Counter has space and is open 10:00–18:00 UTC on 2026-02-08, and the customer's recorded choice is needed. Pella Rusk asks in the Customer portal to send DL-006 there instead of her home. This branch diverges after event 003: Routing ticket creation failed.

## Initial request

Automatic reply. Your message about DL-006 was received at 09:25. Ticket creation failed with a system error, so no reference number was issued. Your request may not appear in the Routing queue.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask Routing in Dispatch chat what DL-006's saved destination shows now, and state that no second redirect request will be sent until that is known.

- **Recipient:** Routing, Plover Arc Logistics
- **Channel:** Dispatch chat
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** VERIFY_FIRST (workflow sheet R)

## Outcome

Routing states DL-006's saved destination; if the redirect is absent, one request follows and is confirmed once, and none of this shows the counter has the parcel.

## Boundaries and remaining work

Must not: Email the redirect request again, or tell Pella the parcel is on its way to Copperfin Counter.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
