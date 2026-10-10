# Case 005-N1: Recipient asks for an authorised household member to receive the parcel (Recipient verification found incomplete at escalation)

## Case details

- **Source role:** Recipient services, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-06 09:00:00 UTC
- **Escalated:** 2026-02-06 09:15:00 UTC
- **Updated:** 2026-02-06 11:10:00 UTC
- **Completed:** 2026-02-06 11:10:00 UTC
- **Primary shipment:** DL-005
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 005, events 001–002 retained; branch SNAPSHOT_CONFLICT

## Context

DL-005 uses the ordinary household parcel service, under which a verified recipient may nominate an adult household member by name in the order portal before the route is released. Lira Venn will be out during the window and asks whether her adult brother, not yet named on the booking, can receive it. This branch diverges after event 002: Recipient verification found incomplete at escalation.

## Initial request

Further to our 09:00 note on DL-005: the order portal shows Lira Venn's recipient verification as incomplete. The identity step was started at checkout but not finished. Our nomination rule applies only to verified recipients.

## Overview

The escalation snapshot comprises history events 001–003. Event 004 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Tell Lira in the Customer portal that a receiver can be nominated only once her recipient verification is complete, and that until then DL-005 stays addressed to her alone.

- **Recipient:** Lira Venn, recipient
- **Channel:** Customer portal
- **Recorded action:** [History event 004](history.md#event-004)
- **Expected decision:** DECLINE_EXPLAIN (workflow sheet A)

## Outcome

Recipient services reports Lira as verified, or the booking stays unchanged; verification nominates no one and delivers nothing.

## Boundaries and remaining work

Must not: Ask for the brother's name, or submit a nomination to Recipient services from an unverified account.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
