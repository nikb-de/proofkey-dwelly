# Case 048-N4: International shipment is cleared but awaiting last-mile handover (Recipient switches to hub collection)

## Case details

- **Source role:** Ari Veld, recipient
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-21 09:00:00 UTC
- **Escalated:** 2026-03-21 09:35:00 UTC
- **Updated:** 2026-03-21 10:15:00 UTC
- **Completed:** 2026-03-21 10:15:00 UTC
- **Primary shipment:** DL-048
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 048, events 001–003 retained; branch CUSTOMER_CANCELS

## Context

Harbor Thread records DL-048 released under CLR-048 at 07:30 UTC with Plover Arc assigned for the last mile, but no last-mile receipt is visible. Recipient Ari Veld asks whether the local carrier actually has the parcel and for its tracking reference. This branch diverges after event 003: Recipient switches to hub collection.

## Initial request

Please stop chasing the handover. I want to collect DL-048 from Harbor Thread's hub myself today, so it should not go to the local carrier. Can you cancel the transfer?

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Record Ari's stop, tell the Harbor Thread transfer team of it by email, and ask whether DL-048 has already been handed to Plover Arc.

- **Recipient:** Harbor Thread International transfer team
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** RECORD_STOP (workflow sheet F)

## Outcome

The transfer team states whether the handover already happened; the stop does not undo it or arrange a collection.

## Boundaries and remaining work

Must not: Promise Ari a hub collection, or assume the handover has not happened and cancel anything with Plover Arc yourself.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
