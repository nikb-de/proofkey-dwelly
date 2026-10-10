# Case 008-N3: Recipient needs a defined delivery slot rather than an all-day estimate (Recipient's acceptance email may have failed)

## Case details

- **Source role:** Nemi Thale, recipient
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-09 09:00:00 UTC
- **Escalated:** 2026-02-09 10:12:00 UTC
- **Updated:** 2026-02-09 10:50:00 UTC
- **Completed:** 2026-02-09 10:50:00 UTC
- **Primary shipment:** DL-008
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 008, events 001–004 retained; branch CHANNEL_FAILURE

## Context

DL-008 has an all-day booking for 2026-02-10; timed delivery may be available, but only Scheduling can quote live capacity and the upgrade charge. Nemi Thale cannot stay in all day and asks the desk to find a two-hour slot and its cost before any change. This branch diverges after event 004: Recipient's acceptance email may have failed.

## Initial request

I replied 'accept' to Scheduling's email at 10:05, but my mail app showed 'sending failed' and the message then vanished from my outbox. Did they get it? I do not want to be charged twice.

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask Scheduling by Email whether an acceptance from Nemi is in the DL-008 booking thread and what the booking now shows, and tell Nemi not to resend until that is known.

- **Recipient:** Scheduling, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** VERIFY_FIRST (workflow sheet R)

## Outcome

Scheduling states whether the acceptance and booking exist; if absent, Nemi accepts once in the thread before 16:00 UTC, and neither proves delivery or payment.

## Boundaries and remaining work

Must not: Forward an acceptance to Scheduling on her behalf, or ask her to send it again before Scheduling answers.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
