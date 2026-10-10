# Case 015-N5: Parcel has been routed to the wrong local depot (Torn label blocks relabelling)

## Case details

- **Source role:** Routing control, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-16 09:00:00 UTC
- **Escalated:** 2026-02-16 13:10:00 UTC
- **Updated:** 2026-02-16 14:40:00 UTC
- **Completed:** 2026-02-16 14:40:00 UTC
- **Primary shipment:** DL-015
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 015, events 001–003 retained; branch PHYSICAL_FAILURE

## Context

Routing control confirms that DL-015 is at North Sedgeglass depot by routing error, while its destination Merrow Quay is served by East Copperfin depot, and no delivery attempt is scheduled. Kiva Rell, the recipient, asks for the parcel to reach the local depot before delivery is arranged. This branch diverges after event 003: Torn label blocks relabelling.

## Initial request

North Sedgeglass found DL-015 for the transfer, but the address label is torn and the destination line is unreadable. It cannot be relabelled for East Copperfin until the Address desk confirms the destination from the order record. It has not moved.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask the Address desk by email to confirm DL-015's destination from the order record directly to Routing control so the parcel can be relabelled for East Copperfin.

- **Recipient:** Address desk, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** REQUEST_ACTION (workflow sheet C)

## Outcome

The Address desk confirms the destination and Routing control reports the relabel; this does not prove the transfer or East Copperfin receipt.

## Boundaries and remaining work

Must not: Do not ask Kiva to type the address into the portal for relabelling, and do not pass Routing control an address taken from the case messages.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
