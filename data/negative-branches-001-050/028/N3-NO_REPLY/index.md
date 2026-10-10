# Case 028-N3: Wrong item inside a correctly addressed parcel (No answer, customer needs plan today)

## Case details

- **Source role:** Riva Solt, recipient
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-01 09:00:00 UTC
- **Escalated:** 2026-03-01 15:30:00 UTC
- **Updated:** 2026-03-01 16:25:00 UTC
- **Completed:** 2026-03-01 16:25:00 UTC
- **Primary shipment:** DL-028
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 028, events 001–003 retained; branch NO_REPLY

## Context

Tallowmere Goods has verified that Riva Solt received a red kitchen caddy SKU RC-2 instead of the blue desk organiser SKU BO-4 she ordered, with the address and DL-028 matching the order, and exchange authority sits with its returns team. Riva wants the blue organiser and can be home on the morning of 2026-03-02. This branch diverges after event 003: No answer, customer needs plan today.

## Initial request

Any news on the exchange? I need to know today whether someone is coming tomorrow morning, otherwise I will arrange to go out.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Send Returns authorisations, Tallowmere Goods, one email reminder that Riva's availability on the morning of 2026-03-02 needs an answer by the end of today, record the returns team as owner with that deadline, and tell Riva nothing is booked yet.

- **Recipient:** Returns authorisations, Tallowmere Goods
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** WAIT_WITH_DEADLINE (workflow sheet B)

## Outcome

The returns team approves and confirms a collection slot, or the deadline passes and Riva is told; a reminder is not a booking.

## Boundaries and remaining work

Must not: Do not tell Riva that a collection is booked for tomorrow morning, and do not arrange a carrier collection without the returns team's authorisation.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
