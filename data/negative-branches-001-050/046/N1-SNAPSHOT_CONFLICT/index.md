# Case 046-N1: Import broker needs the consignee to appoint it before processing (Current register names a different signatory)

## Case details

- **Source role:** Account register, business portal
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-19 09:00:00 UTC
- **Escalated:** 2026-03-19 09:15:00 UTC
- **Updated:** 2026-03-19 09:55:00 UTC
- **Completed:** 2026-03-19 09:55:00 UTC
- **Primary shipment:** DL-046
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 046, events 001–002 retained; branch SNAPSHOT_CONFLICT

## Context

Customs broker Ossmere cannot act on DL-046 until the registered authorised signatory accepts its shipment-specific mandate in the verified business portal. Celand Arc's account administrator supplies a register excerpt naming director Mara Vesk as signatory and states that the operator account cannot sign. This branch diverges after event 002: Current register names a different signatory.

## Initial request

Register record for Celand Arc Imports, version of 2026-03-19 08:30 UTC. Authorised signatory for broker appointment: Osric Lunn, director. Mara Vesk: director; signing authority for broker appointment removed on 2026-03-18.

## Overview

The escalation snapshot comprises history events 001–003. Event 004 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask the Celand Arc account administrator in the business portal one question: which register version their excerpt came from, given the 08:30 UTC record names Osric Lunn, and send no mandate request meanwhile.

- **Recipient:** Celand Arc Imports account administrator
- **Channel:** Business portal
- **Recorded action:** [History event 004](history.md#event-004)
- **Expected decision:** ASK_CUSTOMER (workflow sheet A)

## Outcome

The administrator or register owner confirms one current signatory and the request goes to that person; that does not appoint the broker or clear DL-046.

## Boundaries and remaining work

Must not: Send the mandate request to Mara Vesk on the strength of the administrator's excerpt when the current register removes her signing authority.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
