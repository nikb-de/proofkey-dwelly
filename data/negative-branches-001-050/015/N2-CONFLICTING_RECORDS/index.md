# Case 015-N2: Parcel has been routed to the wrong local depot (Linehaul record contradicts shelf check)

## Case details

- **Source role:** Routing control, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-16 09:00:00 UTC
- **Escalated:** 2026-02-16 16:40:00 UTC
- **Updated:** 2026-02-16 18:20:00 UTC
- **Completed:** 2026-02-16 18:20:00 UTC
- **Primary shipment:** DL-015
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 015, events 001–003 retained; branch CONFLICTING_RECORDS

## Context

Routing control confirms that DL-015 is at North Sedgeglass depot by routing error, while its destination Merrow Quay is served by East Copperfin depot, and no delivery attempt is scheduled. Kiva Rell, the recipient, asks for the parcel to reach the local depot before delivery is arranged. This branch diverges after event 003: Linehaul record contradicts shelf check.

## Initial request

Our transfer record shows DL-015 loaded on the 14:30 UTC linehaul from North Sedgeglass to East Copperfin. The North Sedgeglass shelf check at 15:50 UTC still lists DL-015 on its outbound shelf. We have not resolved which is correct.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Keep both records and ask Routing control by email for a physical scan of DL-015 at North Sedgeglass, or on arrival at East Copperfin, before anything is reported to Kiva.

- **Recipient:** Routing control, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** RECONCILE_CONFLICT (workflow sheet E)

## Outcome

A physical scan at one depot fixes the location; only an East Copperfin receipt scan proves the transfer, and neither proves delivery.

## Boundaries and remaining work

Must not: Do not tell Kiva that the parcel is on its way to East Copperfin because the linehaul record says it was loaded.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
