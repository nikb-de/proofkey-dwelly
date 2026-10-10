# Case 015-N3: Parcel has been routed to the wrong local depot (Second transfer request from phone call)

## Case details

- **Source role:** Routing control, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-16 09:00:00 UTC
- **Escalated:** 2026-02-16 10:05:00 UTC
- **Updated:** 2026-02-16 10:50:00 UTC
- **Completed:** 2026-02-16 10:50:00 UTC
- **Primary shipment:** DL-015
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 015, events 001–003 retained; branch DUPLICATE_REQUEST

## Context

Routing control confirms that DL-015 is at North Sedgeglass depot by routing error, while its destination Merrow Quay is served by East Copperfin depot, and no delivery attempt is scheduled. Kiva Rell, the recipient, asks for the parcel to reach the local depot before delivery is arranged. This branch diverges after event 003: Second transfer request from phone call.

## Initial request

We now hold two transfer requests for DL-015: yours at 09:25 UTC and one from Tracking support at 09:40 UTC after a call from Kiva Rell. Both ask for transfer to East Copperfin. Both are open.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask Routing control by email to link the 09:40 request to the 09:25 request and run one transfer of DL-015 to East Copperfin.

- **Recipient:** Routing control, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** RESOLVE_DUPLICATE (workflow sheet F)

## Outcome

Routing control confirms one open transfer with the other linked or closed; this settles the duplicate, not East Copperfin receipt.

## Boundaries and remaining work

Must not: Do not let both requests run, which could book two linehaul movements, and do not close the original request in favour of the copy.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
