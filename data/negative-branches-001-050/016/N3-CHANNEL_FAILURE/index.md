# Case 016-N3: Pickup locker is full (Transfer instruction returned system error)

## Case details

- **Source role:** Locker routing, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-17 09:00:00 UTC
- **Escalated:** 2026-02-17 10:20:00 UTC
- **Updated:** 2026-02-17 11:00:00 UTC
- **Completed:** 2026-02-17 11:00:00 UTC
- **Primary shipment:** DL-016
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 016, events 001–003 retained; branch CHANNEL_FAILURE

## Context

Locker routing reports that Copperfin Locker has no suitable free compartment for DL-016, the parcel is in depot stock, and the options are staffed Sedgeglass Counter or a locker retry after two days. Zerin Pave, the recipient, needs the parcel before the retry date and asks for the alternative collection option. This branch diverges after event 003: Transfer instruction returned system error.

## Initial request

Zerin accepted Sedgeglass Counter in the verified order thread. Our transfer instruction for DL-016 returned a system error at 10:12 UTC. We cannot see whether the transfer saved. The parcel has not been scanned out of depot stock.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask Locker routing in Dispatch chat to read the saved transfer record for DL-016 and report whether a transfer to Sedgeglass Counter exists, issuing one instruction only if it does not.

- **Recipient:** Locker routing, Plover Arc Logistics
- **Channel:** Dispatch chat
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** VERIFY_FIRST (workflow sheet R)

## Outcome

Locker routing confirms exactly one saved transfer; readiness still needs the counter's receipt scan, and collection remains open.

## Boundaries and remaining work

Must not: Do not ask for the transfer to be issued again at once, and do not tell Zerin that DL-016 is ready at Sedgeglass Counter.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
