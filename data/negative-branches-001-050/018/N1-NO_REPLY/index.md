# Case 018-N1: Shipment is approaching its return-to-sender deadline (No recipient choice nearing cutoff)

## Case details

- **Source role:** Exception desk, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-19 09:00:00 UTC
- **Escalated:** 2026-02-19 13:30:00 UTC
- **Updated:** 2026-02-19 16:05:00 UTC
- **Completed:** 2026-02-19 16:05:00 UTC
- **Primary shipment:** DL-018
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 018, events 001–003 retained; branch NO_REPLY

## Context

The Exception desk reports that DL-018 enters return-to-sender processing at 16:00 UTC on 2026-02-19 unless the customer selects redelivery or depot collection on 2026-02-20, both currently available. No choice is recorded, and the desk asks Iona to contact authorised recipient Nalo Vere before the cutoff. This branch diverges after event 003: No recipient choice nearing cutoff.

## Initial request

Still no recipient choice recorded for DL-018 at 13:30 UTC. Nalo Vere has not contacted us. Return-to-sender processing starts at 16:00 UTC today. Both options remain available until then.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Make one reminder call to Nalo Vere on the verified number stating that DL-018 returns at 16:00 UTC unless an option is chosen, and record the Exception desk as owner of the deadline.

- **Recipient:** Nalo Vere, recipient
- **Channel:** Call transcript
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** WAIT_WITH_DEADLINE (workflow sheet B)

## Outcome

Nalo's choice is recorded before 16:00 UTC and applied by the Exception desk, or the desk records that the cutoff passed; a reminder is not a selection.

## Boundaries and remaining work

Must not: Do not select redelivery or collection on Nalo's behalf to stop the return, and do not ask the Exception desk to extend the cutoff.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
