# Case 045: Import shipment is waiting for the shipper's commercial invoice

## Case details

- **Source role:** Ossmere Trade Desk, appointed customs broker
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-18 09:00:00 UTC
- **Escalated:** 2026-03-18 09:10:00 UTC
- **Updated:** 2026-03-18 10:05:00 UTC
- **Completed:** 2026-03-18 10:05:00 UTC
- **Primary shipment:** DL-045
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC

## Context

A fictional import broker is appointed, but its requested commercial-invoice fields are incomplete. Shipper provision and broker receipt are distinct from customs clearance.

## Initial request

Please request the complete invoice from authorised shipper Mavelle Export Studio. Do not fill in values or origin on their behalf.

## Overview

The escalation snapshot comprises history events 001–002. Event 003 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Request the missing invoice fields specified by the appointed customs broker from the shipper.

- **Recipient:** Fera Noll, Mavelle Export Studio shipping lead
- **Channel:** Email
- **Recorded action:** [History event 003](history.md#event-003)

## Outcome

The broker confirms receipt of a complete document package; customs clearance is not claimed.

## Boundaries and remaining work

Fictional broker requirements are not universal customs law; document completeness is not clearance.

## History

[Read the complete dated history](history.md).

## Attachments

- [commercial-invoice.pdf](attachments/commercial-invoice.pdf)
