# Case 029-N4: Refrigerated food arrives outside the merchant's documented temperature conditions (Van log contradicts merchant logger)

## Case details

- **Source role:** Dispatch, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-02 09:00:00 UTC
- **Escalated:** 2026-03-02 09:45:00 UTC
- **Updated:** 2026-03-02 10:25:00 UTC
- **Completed:** 2026-03-02 10:25:00 UTC
- **Primary shipment:** DL-029
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 029, events 001–003 retained; branch CONFLICTING_RECORDS

## Context

Brineleaf Pantry's documented chilled range for BP-029 / DL-029 is 0 to 5 °C at handover, logger BL-29 recorded 9.2 °C at 08:50 UTC, and only food-safety staff may authorise disposition. Enna Vosk has eaten nothing from the box and asks what to do and whether it will be replaced. This branch diverges after event 003: Van log contradicts merchant logger.

## Initial request

For DL-029, our van chiller log shows 3.8 °C at the 08:50 UTC handover stop. We hold no record of the merchant's BL-29 sensor reading. Please note our log before any carrier fault is assumed.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Send the carrier's 3.8 °C van log to the Brineleaf Pantry food-safety lead with the 9.2 °C BL-29 reading, keeping both on record for its assessment.

- **Recipient:** Brineleaf Pantry food-safety lead
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** RECONCILE_CONFLICT (workflow sheet E)

## Outcome

The food-safety lead confirms it holds both readings; that decides neither the disposition nor who is at fault.

## Boundaries and remaining work

Must not: Do not decide which reading is right, tell Enna the food stayed cold, or assign fault to the carrier or the merchant.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
