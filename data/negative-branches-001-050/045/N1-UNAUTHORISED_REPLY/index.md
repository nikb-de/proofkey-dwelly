# Case 045-N1: Import shipment is waiting for the shipper's commercial invoice (Third party sends invoice for shipper)

## Case details

- **Source role:** Corvin Fask, forwarding agent
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-18 09:00:00 UTC
- **Escalated:** 2026-03-18 09:40:00 UTC
- **Updated:** 2026-03-18 14:10:00 UTC
- **Completed:** 2026-03-18 14:10:00 UTC
- **Primary shipment:** DL-045
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 045, events 001–003 retained; branch UNAUTHORISED_REPLY

## Context

Appointed customs broker Ossmere Trade Desk lacks the shipper's commercial invoice fields for DL-045 / OS-045 and has made no clearance decision. It asks the desk to request the complete invoice from authorised shipper Mavelle Export Studio and not to fill in values or origin on their behalf. This branch diverges after event 003: Third party sends invoice for shipper.

## Initial request

We handle export paperwork for Mavelle. A commercial invoice for DL-045 is attached, prepared from their order. Please forward it to the broker as the shipper's invoice so the file can move today. Fera is out of the office.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Forward nothing and ask Fera Noll at Mavelle's known email whether Mavelle issued or authorised this document, or will send its own invoice.

- **Recipient:** Fera Noll, Mavelle Export Studio shipping lead
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** SEPARATE_AUTHORITY (workflow sheet A)

## Outcome

Mavelle supplies or confirms its own invoice; the broker's review is still needed and clearance is not decided.

## Boundaries and remaining work

Must not: Pass the agent's document to Ossmere as Mavelle's commercial invoice because it looks complete.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
