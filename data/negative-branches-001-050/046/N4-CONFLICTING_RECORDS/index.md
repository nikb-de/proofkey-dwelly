# Case 046-N4: Import broker needs the consignee to appoint it before processing (Broker record shows operator-account acceptance)

## Case details

- **Source role:** Ossmere Trade Desk, customs broker
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-19 09:00:00 UTC
- **Escalated:** 2026-03-19 09:58:00 UTC
- **Updated:** 2026-03-19 10:50:00 UTC
- **Completed:** 2026-03-19 10:50:00 UTC
- **Primary shipment:** DL-046
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 046, events 001–004 retained; branch CONFLICTING_RECORDS

## Context

Customs broker Ossmere cannot act on DL-046 until the registered authorised signatory accepts its shipment-specific mandate in the verified business portal. Celand Arc's account administrator supplies a register excerpt naming director Mara Vesk as signatory and states that the operator account cannot sign. This branch diverges after event 004: Broker record shows operator-account acceptance.

## Initial request

Our record for MND-046 shows an acceptance at 09:42 UTC from portal user celand-ops, the Celand Arc operator account, not from Mara Vesk's verified user. We cannot match it to the registered signatory yet.

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Keep both records and ask Mara Vesk through her verified business-portal channel which login she used to accept MND-046 at 09:42 UTC.

- **Recipient:** Mara Vesk, Celand Arc authorised director
- **Channel:** Business portal
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** RECONCILE_CONFLICT (workflow sheet E)

## Outcome

Ossmere records an acceptance from Mara's verified user; that appoints the broker for DL-046 only, and clearance stays pending.

## Boundaries and remaining work

Must not: Treat Mara's message as the acceptance, or ask Ossmere to record the operator-account acceptance as hers.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
