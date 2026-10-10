# Case 031-N3: Return approved but the customer has no return label (Carrier offers its own generic label)

## Case details

- **Source role:** Returns desk, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-04 09:00:00 UTC
- **Escalated:** 2026-03-04 09:52:00 UTC
- **Updated:** 2026-03-04 10:25:00 UTC
- **Completed:** 2026-03-04 10:25:00 UTC
- **Primary shipment:** DL-031
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 031, events 001–003 retained; branch UNAUTHORISED_REPLY

## Context

Tallowmere Goods approved return RT-031 for TG-031 / DL-031, but the label field is empty and only its authorised label team can issue the label. Kessa Ulm asks the desk to obtain the printable return label. This branch diverges after event 003: Carrier offers its own generic label.

## Initial request

We see RT-031 waiting in the shared returns queue. We can print a generic Plover Arc returns label without a Tallowmere label number and send it straight to the customer's email today. Reply yes and we will issue it.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Reply to the Returns desk by email that it must not issue or send any label to Kessa, and keep the request with the Return label team, Tallowmere Goods, the only authorised issuer for RT-031.

- **Recipient:** Returns desk, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** SEPARATE_AUTHORITY (workflow sheet A)

## Outcome

The Returns desk confirms it has issued nothing and the label team's response is still awaited; this does not prove any label exists for RT-031.

## Boundaries and remaining work

Must not: Do not accept the generic label or share Kessa's email address; a label not issued against RT-031 by the authorised team is not the approved return label.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
