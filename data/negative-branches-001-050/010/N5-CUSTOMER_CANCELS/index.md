# Case 010-N5: Recipient wants delivery held during a short absence (Recipient withdraws the hold request)

## Case details

- **Source role:** Daro Lusk, recipient
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-11 09:00:00 UTC
- **Escalated:** 2026-02-11 09:35:00 UTC
- **Updated:** 2026-02-11 10:15:00 UTC
- **Completed:** 2026-02-11 10:15:00 UTC
- **Primary shipment:** DL-010
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 010, events 001–003 retained; branch CUSTOMER_CANCELS

## Context

DL-010 is in depot stock, and the service allows a hold of up to three calendar days before routing with a confirmed release date. Daro Lusk is away until 2026-02-14 and asks for the parcel to be held and released on that date, not earlier. This branch diverges after event 003: Recipient withdraws the hold request.

## Initial request

Please cancel my hold request. My sister will be at the flat this week after all, so normal delivery is fine. Do not hold DL-010.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Email Dispatch that Daro has withdrawn the hold request and no further change is to be made, and ask whether the hold was already applied to DL-010.

- **Recipient:** Dispatch, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** RECORD_STOP (workflow sheet F)

## Outcome

Dispatch reports DL-010's actual status; if the hold was applied, lifting it is a separate request, and no delivery date follows.

## Boundaries and remaining work

Must not: Ask Dispatch to lift an applied hold or release DL-010 to routing early, or tell Daro normal delivery goes ahead, before Dispatch reports what was executed.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
