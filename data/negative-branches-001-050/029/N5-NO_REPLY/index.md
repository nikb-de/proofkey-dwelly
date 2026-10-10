# Case 029-N5: Refrigerated food arrives outside the merchant's documented temperature conditions (No disposition before customer leaves)

## Case details

- **Source role:** Enna Vosk, recipient
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-02 09:00:00 UTC
- **Escalated:** 2026-03-02 11:30:00 UTC
- **Updated:** 2026-03-02 12:20:00 UTC
- **Completed:** 2026-03-02 12:20:00 UTC
- **Primary shipment:** DL-029
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 029, events 001–003 retained; branch NO_REPLY

## Context

Brineleaf Pantry's documented chilled range for BP-029 / DL-029 is 0 to 5 °C at handover, logger BL-29 recorded 9.2 °C at 08:50 UTC, and only food-safety staff may authorise disposition. Enna Vosk has eaten nothing from the box and asks what to do and whether it will be replaced. This branch diverges after event 003: No disposition before customer leaves.

## Initial request

Still no word from the merchant. The box is on my kitchen floor. I leave for work at 13:00 UTC and nobody will be home until 19:00 UTC. I need to know what to do with it before I go.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Send the Brineleaf Pantry food-safety lead one email reminder citing Enna's 13:00 UTC departure, record the lead as owner and 13:00 UTC as the deadline, and tell Enna the instruction is still pending.

- **Recipient:** Brineleaf Pantry food-safety lead
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** WAIT_WITH_DEADLINE (workflow sheet B)

## Outcome

The food-safety lead issues its disposition; the reminder itself decides nothing.

## Boundaries and remaining work

Must not: Do not give Enna your own instruction to refrigerate, use or throw away the food to meet her deadline.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
