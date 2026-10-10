# Case 017-N3: Delivery notification contains an unusable tracking link (Corrected reference send status unknown)

## Case details

- **Source role:** Notification support, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-18 09:00:00 UTC
- **Escalated:** 2026-02-18 09:45:00 UTC
- **Updated:** 2026-02-18 10:30:00 UTC
- **Completed:** 2026-02-18 10:30:00 UTC
- **Primary shipment:** DL-017
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 017, events 001–003 retained; branch CHANNEL_FAILURE

## Context

Notification support reports that the DL-017 notification path was truncated by its template, the account-linked notification belongs to this recipient, and the shipment reference is intact. Vela Morn, the recipient, asks for the correct way to find the parcel in the order portal. This branch diverges after event 003: Corrected reference send status unknown.

## Initial request

We sent the corrected DL-017 reference to Vela's verified order thread at 09:38 UTC. The template service timed out and the send status shows 'unknown'. We cannot confirm whether the message reached the thread.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask Notification support by email to check the saved message log of Vela's verified order thread for the 09:38 send before any resend.

- **Recipient:** Notification support, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** VERIFY_FIRST (workflow sheet R)

## Outcome

Notification support confirms one correct message in the thread, or one resend after finding none; this proves the reference was sent, not that the parcel is delivered.

## Boundaries and remaining work

Must not: Do not ask for an immediate resend, which could put a second, possibly truncated message in the thread, and do not send the reference to Vela by another channel.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
