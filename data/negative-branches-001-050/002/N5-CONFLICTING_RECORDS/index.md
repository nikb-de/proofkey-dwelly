# Case 002-N5: Apartment number missing from the delivery address (Stated apartment missing from building register)

## Case details

- **Source role:** Address desk, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-03 09:00:00 UTC
- **Escalated:** 2026-02-03 10:08:00 UTC
- **Updated:** 2026-02-03 11:40:00 UTC
- **Completed:** 2026-02-03 11:40:00 UTC
- **Primary shipment:** DL-002
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 002, events 001–004 retained; branch CONFLICTING_RECORDS

## Context

DL-002 is on an incomplete-address hold because 18 Copperfin Court, Merrow Quay has several apartments and the order has none; the account team verified the recipient's order-linked portal session. Tarin Mave asks in the Customer portal what is needed. This branch diverges after event 004: Stated apartment missing from building register.

## Initial request

We have the correction request for DL-002, Apartment 4B. Our building register for 18 Copperfin Court lists apartments 1A to 3D only, with no fourth floor. We have not applied the correction. The address hold remains.

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Email the Address desk keeping the recipient's statement and the register entry both on file, unchanged, and ask which verification step it uses when a stated apartment is missing from its register.

- **Recipient:** Address desk, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** RECONCILE_CONFLICT (workflow sheet A)

## Outcome

The Address desk reports its verification result and the address held on DL-002; this does not show which record was wrong, and nothing is delivered.

## Boundaries and remaining work

Must not: Tell Tarin that 4B does not exist or show her the register's apartment list, or ask the Address desk to apply 4B regardless.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
