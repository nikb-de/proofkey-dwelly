# Case 016-N4: Pickup locker is full (Counter full after recipient accepted)

## Case details

- **Source role:** Locker routing, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-17 09:00:00 UTC
- **Escalated:** 2026-02-17 11:00:00 UTC
- **Updated:** 2026-02-17 15:30:00 UTC
- **Completed:** 2026-02-17 15:30:00 UTC
- **Primary shipment:** DL-016
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 016, events 001–003 retained; branch STALE_STATE

## Context

Locker routing reports that Copperfin Locker has no suitable free compartment for DL-016, the parcel is in depot stock, and the options are staffed Sedgeglass Counter or a locker retry after two days. Zerin Pave, the recipient, needs the parcel before the retry date and asks for the alternative collection option. This branch diverges after event 003: Counter full after recipient accepted.

## Initial request

Zerin accepted Sedgeglass Counter this morning in the verified thread. Before transfer, the counter reported at 10:40 UTC that it is at capacity until 2026-02-19. A Copperfin Locker compartment freed at 10:45 UTC; we can place DL-016 there today.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask Zerin in the Customer portal whether to take the Copperfin Locker compartment today or wait for Sedgeglass Counter capacity on 2026-02-19, and route nothing until Zerin answers.

- **Recipient:** Zerin Pave, recipient
- **Channel:** Customer portal
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** ASK_CUSTOMER (workflow sheet B)

## Outcome

Zerin's new choice is recorded and the chosen location's receipt scan confirms readiness; collection remains open.

## Boundaries and remaining work

Must not: Do not place DL-016 in Copperfin Locker on the strength of Zerin's acceptance of Sedgeglass Counter; that consent was for a different location.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
