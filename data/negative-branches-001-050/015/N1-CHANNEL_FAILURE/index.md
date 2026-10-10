# Case 015-N1: Parcel has been routed to the wrong local depot (Transfer intake outage loses requests)

## Case details

- **Source role:** Routing control, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-16 09:00:00 UTC
- **Escalated:** 2026-02-16 11:20:00 UTC
- **Updated:** 2026-02-16 12:05:00 UTC
- **Completed:** 2026-02-16 12:05:00 UTC
- **Primary shipment:** DL-015
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 015, events 001–003 retained; branch CHANNEL_FAILURE

## Context

Routing control confirms that DL-015 is at North Sedgeglass depot by routing error, while its destination Merrow Quay is served by East Copperfin depot, and no delivery attempt is scheduled. Kiva Rell, the recipient, asks for the parcel to reach the local depot before delivery is arranged. This branch diverges after event 003: Transfer intake outage loses requests.

## Initial request

Notice: our transfer request intake failed between 09:00 and 11:00 UTC today. Emails received in that period may not have created transfer requests. Do not assume a request sent then is queued.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask Routing control by email whether a transfer request for DL-015 from North Sedgeglass to East Copperfin is saved, and submit it once only if it is absent.

- **Recipient:** Routing control, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** VERIFY_FIRST (workflow sheet R)

## Outcome

Routing control confirms one saved transfer request with a reference; this proves the request exists, not that DL-015 has left North Sedgeglass or reached East Copperfin.

## Boundaries and remaining work

Must not: Do not resend the transfer request without checking, which could create two transfer movements, and do not tell Kiva that the transfer is under way.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
