# Case 045-N2: Import shipment is waiting for the shipper's commercial invoice (Invoice supplied without origin declaration)

## Case details

- **Source role:** Fera Noll, Mavelle Export Studio shipping lead
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-18 09:00:00 UTC
- **Escalated:** 2026-03-18 09:45:00 UTC
- **Updated:** 2026-03-18 11:00:00 UTC
- **Completed:** 2026-03-18 11:00:00 UTC
- **Primary shipment:** DL-045
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 045, events 001–003 retained; branch AMBIGUOUS_REPLY

## Context

Appointed customs broker Ossmere Trade Desk lacks the shipper's commercial invoice fields for DL-045 / OS-045 and has made no clearance decision. It asks the desk to request the complete invoice from authorised shipper Mavelle Export Studio and not to fill in values or origin on their behalf. This branch diverges after event 003: Invoice supplied without origin declaration.

## Initial request

Our invoice for DL-045 / OS-045 is attached with seller, buyer, date, reference, goods, quantity and values. We do not normally put an origin statement on it, as the goods come from more than one workshop. Is that enough?

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Reply to Fera Noll by email that the broker's list includes an origin declaration and ask her to provide one on the invoice.

- **Recipient:** Fera Noll, Mavelle Export Studio shipping lead
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** ASK_CUSTOMER (workflow sheet A)

## Outcome

Fera supplies an invoice with her own origin declaration; the broker still decides completeness, and nothing about clearance follows.

## Boundaries and remaining work

Must not: Write in an origin yourself, or tell the broker the invoice is complete.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
