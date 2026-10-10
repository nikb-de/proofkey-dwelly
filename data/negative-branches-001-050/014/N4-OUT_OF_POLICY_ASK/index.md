# Case 014-N4: Driver arrives after the business receiving desk closes (Fallback asks for unattended cage drop)

## Case details

- **Source role:** Rellin Vos, Vellum Rack receiving coordinator
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-15 09:00:00 UTC
- **Escalated:** 2026-02-15 09:55:00 UTC
- **Updated:** 2026-02-15 10:45:00 UTC
- **Completed:** 2026-02-15 10:45:00 UTC
- **Primary shipment:** DL-014
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 014, events 001–003 retained; branch OUT_OF_POLICY_ASK

## Context

Business dispatch reports that DL-014 reached Vellum Rack Supplies after its receiving desk closed, the driver retained the parcel, and a staffed receiving window is needed to retry. Rellin Vos, the receiving coordinator, says the shop may be open late but the receiving desk is not, and asks to be consulted before any booking. This branch diverges after event 003: Fallback asks for unattended cage drop.

## Initial request

A clerk can be at the rear receiving door on 2026-02-16, 08:00–11:00 UTC. If the driver arrives outside that window, leave DL-014 in the unlocked cage beside the door.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Tell Rellin in the Business portal that the retry needs a staffed receiving window, so an unattended cage drop cannot be arranged, and relay only the 2026-02-16, 08:00–11:00 UTC staffed window to Business dispatch.

- **Recipient:** Rellin Vos, Vellum Rack receiving coordinator
- **Channel:** Business portal
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** DECLINE_EXPLAIN (workflow sheet A)

## Outcome

Rellin acknowledges and Business dispatch books the staffed window only; that confirms the next attempt, not receipt, and no unattended drop is authorised.

## Boundaries and remaining work

Must not: Do not pass the cage instruction to Business dispatch or the driver as a fallback; an unattended drop is not a staffed handover.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
