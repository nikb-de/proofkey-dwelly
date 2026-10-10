# Case 046-N3: Import broker needs the consignee to appoint it before processing (Signatory's acceptance click times out)

## Case details

- **Source role:** Mara Vesk, Celand Arc authorised director
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-19 09:00:00 UTC
- **Escalated:** 2026-03-19 09:43:00 UTC
- **Updated:** 2026-03-19 10:20:00 UTC
- **Completed:** 2026-03-19 10:20:00 UTC
- **Primary shipment:** DL-046
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 046, events 001–003 retained; branch CHANNEL_FAILURE

## Context

Customs broker Ossmere cannot act on DL-046 until the registered authorised signatory accepts its shipment-specific mandate in the verified business portal. Celand Arc's account administrator supplies a register excerpt naming director Mara Vesk as signatory and states that the operator account cannot sign. This branch diverges after event 003: Signatory's acceptance click times out.

## Initial request

I pressed accept on Ossmere's DL-046 mandate at 09:40 UTC and the portal showed a timeout page. I cannot see whether it saved. Should I press accept again?

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask Ossmere Trade Desk in the broker portal whether the DL-046 mandate shows an acceptance, and from which user, before Mara does anything again.

- **Recipient:** Ossmere Trade Desk, customs broker
- **Channel:** Broker portal
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** VERIFY_FIRST (workflow sheet R)

## Outcome

Ossmere confirms whether an acceptance by Mara is saved; that settles the appointment question, not clearance.

## Boundaries and remaining work

Must not: Tell Mara to press accept again, which may create a second acceptance, or tell Ossmere the mandate is accepted.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
