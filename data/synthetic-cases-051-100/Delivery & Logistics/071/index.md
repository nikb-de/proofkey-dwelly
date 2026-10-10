# Case 071: Reschedule request timed out in the dispatch system and the recipient asks whether it is booked

## Case details

- **Source role:** Halvi Maddren, recipient
- **Status:** Completed — specific coordination task only
- **Created:** 2026-04-13 09:00:00 UTC
- **Escalated:** 2026-04-13 09:10:00 UTC
- **Updated:** 2026-04-13 10:00:00 UTC
- **Completed:** 2026-04-13 10:00:00 UTC
- **Primary shipment:** DL-071
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC

## Context

DL-071 is at the depot before route release, and a reschedule request ended in a booking-tool timeout with no confirmation. Dispatch holds the saved booking and is the only party that can confirm or change it.

## Initial request

The order thread says my reschedule request timed out. Is DL-071 now booked for tomorrow afternoon or still for today? I do not want two deliveries or to lose the new slot.

## Overview

The escalation snapshot comprises history events 001–002. Event 003 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask dispatch what the saved booking shows before any resubmission of the reschedule.

- **Recipient:** Dispatch, Plover Arc Logistics
- **Channel:** Dispatch chat
- **Recorded action:** [History event 003](history.md#event-003)

## Outcome

Dispatch confirms the reschedule was applied once and no second change was made; delivery remains pending.

## Boundaries and remaining work

Check the saved booking before resubmitting; a timeout is not proof that the change failed. No duplicate booking is created, and a booking record is not a delivery.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
