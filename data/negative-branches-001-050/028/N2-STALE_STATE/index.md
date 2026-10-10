# Case 028-N2: Wrong item inside a correctly addressed parcel (Morning slots full, two offered)

## Case details

- **Source role:** Returns authorisations, Tallowmere Goods
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-01 09:00:00 UTC
- **Escalated:** 2026-03-01 09:45:00 UTC
- **Updated:** 2026-03-01 10:20:00 UTC
- **Completed:** 2026-03-01 10:20:00 UTC
- **Primary shipment:** DL-028
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 028, events 001–003 retained; branch STALE_STATE

## Context

Tallowmere Goods has verified that Riva Solt received a red kitchen caddy SKU RC-2 instead of the blue desk organiser SKU BO-4 she ordered, with the address and DL-028 matching the order, and exchange authority sits with its returns team. Riva wants the blue organiser and can be home on the morning of 2026-03-02. This branch diverges after event 003: Morning slots full, two offered.

## Initial request

We can approve the exchange for TG-028. Collection slots on 2026-03-02 morning are now full. Available slots are 2026-03-02 13:00 to 17:00 UTC or 2026-03-03 09:00 to 12:00 UTC. Please confirm which the customer wants.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask Riva in the customer portal one question: does she choose the 2026-03-02 afternoon slot or the 2026-03-03 morning slot for the collection of the red caddy.

- **Recipient:** Riva Solt, recipient
- **Channel:** Customer portal
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** ASK_CUSTOMER (workflow sheet B)

## Outcome

Riva picks one offered slot; her choice is not a booking until the returns team confirms it, and a booking is not a completed exchange.

## Boundaries and remaining work

Must not: Do not pick the 2026-03-02 afternoon slot for her because she named that date, and do not tell her a morning collection is booked.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
