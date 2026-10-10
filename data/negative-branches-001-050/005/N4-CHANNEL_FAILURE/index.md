# Case 005-N4: Recipient asks for an authorised household member to receive the parcel (Nomination submission timed out)

## Case details

- **Source role:** Recipient services request form, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-06 09:00:00 UTC
- **Escalated:** 2026-02-06 09:57:00 UTC
- **Updated:** 2026-02-06 10:35:00 UTC
- **Completed:** 2026-02-06 10:35:00 UTC
- **Primary shipment:** DL-005
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 005, events 001–004 retained; branch CHANNEL_FAILURE

## Context

DL-005 uses the ordinary household parcel service, under which a verified recipient may nominate an adult household member by name in the order portal before the route is released. Lira Venn will be out during the window and asks whether her adult brother, not yet named on the booking, can receive it. This branch diverges after event 004: Nomination submission timed out.

## Initial request

Automatic response. The nomination submission for DL-005 sent at 09:53 returned 'Request timed out' before a reference was issued. The route record may or may not have been updated.

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Email Recipient services asking whether DL-005's route record now shows Halen Venn as alternate receiver, and state that no second nomination will be submitted until that is known.

- **Recipient:** Recipient services, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** VERIFY_FIRST (workflow sheet R)

## Outcome

Recipient services states the saved receiver record; if absent, one submission follows and is confirmed once, and an approved receiver is not a handover.

## Boundaries and remaining work

Must not: Resubmit the nomination, or tell Lira that Halen Venn is approved.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
