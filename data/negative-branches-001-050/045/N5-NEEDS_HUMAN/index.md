# Case 045-N5: Import shipment is waiting for the shipper's commercial invoice (Broker needs compliance officer review)

## Case details

- **Source role:** Ossmere Trade Desk, appointed customs broker
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-18 09:00:00 UTC
- **Escalated:** 2026-03-18 10:00:00 UTC
- **Updated:** 2026-03-19 11:30:00 UTC
- **Completed:** 2026-03-19 11:30:00 UTC
- **Primary shipment:** DL-045
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 045, events 001–004 retained; branch NEEDS_HUMAN

## Context

Appointed customs broker Ossmere Trade Desk lacks the shipper's commercial invoice fields for DL-045 / OS-045 and has made no clearance decision. It asks the desk to request the complete invoice from authorised shipper Mavelle Export Studio and not to fill in values or origin on their behalf. This branch diverges after event 004: Broker needs compliance officer review.

## Initial request

CI-045 for DL-045 states origin Aster Reach. Our procedure sends goods declared from Aster Reach to a compliance officer before we accept a package. I cannot mark the file complete or reject it. No officer review is booked yet.

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Escalate to the desk operator with the facts and sources: CI-045 received, origin Aster Reach, Ossmere's compliance hold, and the open question of who books the officer review and when.

- **Recipient:** Desk operator, Rivet Delivery Desk
- **Channel:** Email
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** ESCALATE_OPERATOR (workflow sheet E)

## Outcome

The operator owns the escalation and Ossmere records an officer outcome; neither establishes completeness or clearance.

## Boundaries and remaining work

Must not: Ask Fera to change the stated origin, or tell anyone the document package is complete.

## History

[Read the complete dated history](history.md).

## Attachments

- [commercial-invoice.pdf](attachments/commercial-invoice.pdf)
