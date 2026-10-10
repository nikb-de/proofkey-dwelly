# Case 045-N4: Import shipment is waiting for the shipper's commercial invoice (Tracker shows released after invoice)

## Case details

- **Source role:** Shipment tracking, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-18 09:00:00 UTC
- **Escalated:** 2026-03-18 09:58:00 UTC
- **Updated:** 2026-03-18 10:45:00 UTC
- **Completed:** 2026-03-18 10:45:00 UTC
- **Primary shipment:** DL-045
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 045, events 001–004 retained; branch CONFLICTING_RECORDS

## Context

Appointed customs broker Ossmere Trade Desk lacks the shipper's commercial invoice fields for DL-045 / OS-045 and has made no clearance decision. It asks the desk to request the complete invoice from authorised shipper Mavelle Export Studio and not to fill in values or origin on their behalf. This branch diverges after event 004: Tracker shows released after invoice.

## Initial request

Tracking update DL-045: status changed to Customs released at 09:52 UTC. Trigger: commercial invoice received in file. Next step: onward transport planning.

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask Ossmere Trade Desk in the broker portal whether any clearance decision exists for DL-045, keeping the tracking status and the broker's record both on file.

- **Recipient:** Ossmere Trade Desk, appointed customs broker
- **Channel:** Broker portal
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** RECONCILE_CONFLICT (workflow sheet E)

## Outcome

Ossmere states the clearance position from its own record; receipt of an invoice is still not clearance.

## Boundaries and remaining work

Must not: Tell anyone DL-045 is cleared because the tracker says released after the invoice arrived.

## History

[Read the complete dated history](history.md).

## Attachments

- [commercial-invoice.pdf](attachments/commercial-invoice.pdf)
