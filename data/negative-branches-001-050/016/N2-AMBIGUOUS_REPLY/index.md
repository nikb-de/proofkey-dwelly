# Case 016-N2: Pickup locker is full (Recipient rejects locker without choosing)

## Case details

- **Source role:** Locker routing, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-17 09:00:00 UTC
- **Escalated:** 2026-02-17 09:55:00 UTC
- **Updated:** 2026-02-17 10:50:00 UTC
- **Completed:** 2026-02-17 10:50:00 UTC
- **Primary shipment:** DL-016
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 016, events 001–003 retained; branch AMBIGUOUS_REPLY

## Context

Locker routing reports that Copperfin Locker has no suitable free compartment for DL-016, the parcel is in depot stock, and the options are staffed Sedgeglass Counter or a locker retry after two days. Zerin Pave, the recipient, needs the parcel before the retry date and asks for the alternative collection option. This branch diverges after event 003: Recipient rejects locker without choosing.

## Initial request

Zerin replied in the verified order thread: 'Not the locker again. Is there anything closer than Sedgeglass?' Zerin did not accept or decline Sedgeglass Counter. DL-016 is still in depot stock.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask Zerin once in the Customer portal to choose between Sedgeglass Counter now and Copperfin Locker after the two-day retry, the only two options Locker routing offers.

- **Recipient:** Zerin Pave, recipient
- **Channel:** Customer portal
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** ASK_CUSTOMER (workflow sheet A)

## Outcome

Zerin chooses one offered option in the verified thread and Locker routing records it; a choice is not readiness for collection.

## Boundaries and remaining work

Must not: Do not route DL-016 to Sedgeglass Counter because Zerin rejected the locker, and do not promise a closer location that Locker routing has not offered.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
