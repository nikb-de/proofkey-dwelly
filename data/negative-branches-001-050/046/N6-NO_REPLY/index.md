# Case 046-N6: Import broker needs the consignee to appoint it before processing (No acceptance before processing cut-off)

## Case details

- **Source role:** Ossmere Trade Desk, customs broker
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-19 09:00:00 UTC
- **Escalated:** 2026-03-19 14:00:00 UTC
- **Updated:** 2026-03-19 17:05:00 UTC
- **Completed:** 2026-03-19 17:05:00 UTC
- **Primary shipment:** DL-046
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 046, events 001–003 retained; branch NO_REPLY

## Context

Customs broker Ossmere cannot act on DL-046 until the registered authorised signatory accepts its shipment-specific mandate in the verified business portal. Celand Arc's account administrator supplies a register excerpt naming director Mara Vesk as signatory and states that the operator account cannot sign. This branch diverges after event 003: No acceptance before processing cut-off.

## Initial request

DL-046 still has no mandate acceptance. Without one by 17:00 UTC today, the shipment misses tomorrow's processing run and stays in the inbound shed.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Send Mara Vesk one reminder through her verified business-portal channel naming the 17:00 UTC cut-off, and record her as owner with that deadline.

- **Recipient:** Mara Vesk, Celand Arc authorised director
- **Channel:** Business portal
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** WAIT_WITH_DEADLINE (workflow sheet B)

## Outcome

Mara accepts and Ossmere confirms by 17:00 UTC, or the missed run is recorded; the reminder appoints no one.

## Boundaries and remaining work

Must not: Let the operator account or another director accept the mandate to beat the cut-off.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
