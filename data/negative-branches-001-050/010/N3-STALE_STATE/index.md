# Case 010-N3: Recipient wants delivery held during a short absence (Parcel loaded before hold request)

## Case details

- **Source role:** Dispatch, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-11 09:00:00 UTC
- **Escalated:** 2026-02-11 09:38:00 UTC
- **Updated:** 2026-02-11 10:30:00 UTC
- **Completed:** 2026-02-11 10:30:00 UTC
- **Primary shipment:** DL-010
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 010, events 001–003 retained; branch STALE_STATE

## Context

DL-010 is in depot stock, and the service allows a hold of up to three calendar days before routing with a confirmed release date. Daro Lusk is away until 2026-02-14 and asks for the parcel to be held and released on that date, not earlier. This branch diverges after event 003: Parcel loaded before hold request.

## Initial request

Your hold request for DL-010 arrived after the parcel was loaded. It left depot stock on the 2026-02-11 morning route at 09:15. Holds apply only before routing. It is out for delivery to Daro's address today.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask Dispatch by Email which options exist for DL-010 now that it is on today's route, and make no change until Daro chooses.

- **Recipient:** Dispatch, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** GET_OPTIONS (workflow sheet B)

## Outcome

Dispatch's options reach Daro and he chooses; no hold exists, and no delivery is claimed.

## Boundaries and remaining work

Must not: Tell Daro the parcel is held, or ask the driver to bring it back to the depot on the desk's own instruction.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
