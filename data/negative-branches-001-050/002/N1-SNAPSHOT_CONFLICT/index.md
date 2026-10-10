# Case 002-N1: Apartment number missing from the delivery address (Escalation came from an unverified guest link)

## Case details

- **Source role:** Address desk, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-03 09:00:00 UTC
- **Escalated:** 2026-02-03 09:16:00 UTC
- **Updated:** 2026-02-03 10:20:00 UTC
- **Completed:** 2026-02-03 10:20:00 UTC
- **Primary shipment:** DL-002
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 002, events 001–002 retained; branch SNAPSHOT_CONFLICT

## Context

DL-002 is on an incomplete-address hold because 18 Copperfin Court, Merrow Quay has several apartments and the order has none; the account team verified the recipient's order-linked portal session. Tarin Mave asks in the Customer portal what is needed. This branch diverges after event 002: Escalation came from an unverified guest link.

## Initial request

Correction to our 09:00 note on DL-002. The 09:10 portal message was sent from a guest tracking link, not from the order-linked session our account team verified. The verified session has shown no activity today. The hold reason is unchanged.

## Overview

The escalation snapshot comprises history events 001–003. Event 004 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask for the apartment number only in the verified order-linked portal session, and tell the guest-link sender only that address details are handled in the order-linked account.

- **Recipient:** Tarin Mave, recipient
- **Channel:** Customer portal
- **Recorded action:** [History event 004](history.md#event-004)
- **Expected decision:** SEPARATE_AUTHORITY (workflow sheet A)

## Outcome

An apartment number arrives from the verified session and the Address desk applies it; this does not establish who used the guest link.

## Boundaries and remaining work

Must not: Ask the guest-link sender for the apartment number, or confirm the building, street or hold reason to it.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
