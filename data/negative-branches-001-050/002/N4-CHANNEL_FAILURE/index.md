# Case 002-N4: Apartment number missing from the delivery address (Correction form session expired mid-submission)

## Case details

- **Source role:** Address desk correction form, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-03 09:00:00 UTC
- **Escalated:** 2026-02-03 09:57:00 UTC
- **Updated:** 2026-02-03 10:40:00 UTC
- **Completed:** 2026-02-03 10:40:00 UTC
- **Primary shipment:** DL-002
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 002, events 001–004 retained; branch CHANNEL_FAILURE

## Context

DL-002 is on an incomplete-address hold because 18 Copperfin Court, Merrow Quay has several apartments and the order has none; the account team verified the recipient's order-linked portal session. Tarin Mave asks in the Customer portal what is needed. This branch diverges after event 004: Correction form session expired mid-submission.

## Initial request

Automatic response. Your address correction for DL-002, Apartment 4B, submitted at 09:54, ended with 'Session expired'. The form may have saved before the session closed. No correction reference was issued.

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Email the Address desk asking what DL-002's saved address and hold status show now, and state that no second correction will be submitted until that is known.

- **Recipient:** Address desk, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** VERIFY_FIRST (workflow sheet R)

## Outcome

The Address desk states the saved address; if 4B is absent, one correction follows and is confirmed once, and a corrected address is not a delivery.

## Boundaries and remaining work

Must not: Resubmit Apartment 4B through the form, or tell Tarin the hold is cleared.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
