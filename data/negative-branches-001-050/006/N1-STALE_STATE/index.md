# Case 006-N1: Customer requests collection from a staffed pickup point (Parcel released before free redirect applied)

## Case details

- **Source role:** Routing, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-07 09:00:00 UTC
- **Escalated:** 2026-02-07 09:48:00 UTC
- **Updated:** 2026-02-07 10:45:00 UTC
- **Completed:** 2026-02-07 10:45:00 UTC
- **Primary shipment:** DL-006
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 006, events 001–003 retained; branch STALE_STATE

## Context

Routing says DL-006 can be redirected without charge before route release, Copperfin Counter has space and is open 10:00–18:00 UTC on 2026-02-08, and the customer's recorded choice is needed. Pella Rusk asks in the Customer portal to send DL-006 there instead of her home. This branch diverges after event 003: Parcel released before free redirect applied.

## Initial request

DL-006 was released to today's home-delivery route at 09:20, before your request reached us, so the free redirect no longer applies. We can still divert it to Copperfin Counter after release for GBP 4.50, or the home attempt goes ahead today.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Tell Pella in the Customer portal that the free redirect has lapsed and ask whether she wants the GBP 4.50 diversion to Copperfin Counter or the home attempt today.

- **Recipient:** Pella Rusk, recipient
- **Channel:** Customer portal
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** ASK_CUSTOMER (workflow sheet B)

## Outcome

Pella's choice in the portal and Routing's confirmation close the branch; neither shows the counter has received the parcel.

## Boundaries and remaining work

Must not: Accept the GBP 4.50 charge for her because she already chose the counter, or tell her the free redirect went through.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
