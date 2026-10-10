# Case 002-N3: Apartment number missing from the delivery address (No apartment number before label cut-off)

## Case details

- **Source role:** Address desk, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-03 09:00:00 UTC
- **Escalated:** 2026-02-03 13:00:00 UTC
- **Updated:** 2026-02-03 16:05:00 UTC
- **Completed:** 2026-02-03 16:05:00 UTC
- **Primary shipment:** DL-002
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 002, events 001–003 retained; branch NO_REPLY

## Context

DL-002 is on an incomplete-address hold because 18 Copperfin Court, Merrow Quay has several apartments and the order has none; the account team verified the recipient's order-linked portal session. Tarin Mave asks in the Customer portal what is needed. This branch diverges after event 003: No apartment number before label cut-off.

## Initial request

DL-002 still has no apartment number. Route labels for tomorrow's loading close at 16:00 UTC today. If no correction is recorded by then, DL-002 stays on hold in the depot and misses that loading.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Send Tarin one reminder in the Customer portal asking for the apartment number before 16:00 UTC, stating that otherwise DL-002 stays on hold, and record the Address desk as owner of that deadline.

- **Recipient:** Tarin Mave, recipient
- **Channel:** Customer portal
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** WAIT_WITH_DEADLINE (workflow sheet B)

## Outcome

Tarin's apartment number is recorded before 16:00, or the Address desk records the missed loading; neither is a delivery.

## Boundaries and remaining work

Must not: Chase Tarin through another channel or number, or ask the Address desk to release DL-002 with the building address only.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
