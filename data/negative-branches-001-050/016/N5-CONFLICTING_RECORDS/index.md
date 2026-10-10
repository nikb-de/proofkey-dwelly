# Case 016-N5: Pickup locker is full (Locker notice contradicts counter scan)

## Case details

- **Source role:** Zerin Pave, recipient
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-17 09:00:00 UTC
- **Escalated:** 2026-02-17 15:20:00 UTC
- **Updated:** 2026-02-17 16:10:00 UTC
- **Completed:** 2026-02-17 16:10:00 UTC
- **Primary shipment:** DL-016
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 016, events 001–004 retained; branch CONFLICTING_RECORDS

## Context

Locker routing reports that Copperfin Locker has no suitable free compartment for DL-016, the parcel is in depot stock, and the options are staffed Sedgeglass Counter or a locker retry after two days. Zerin Pave, the recipient, needs the parcel before the retry date and asks for the alternative collection option. This branch diverges after event 004: Locker notice contradicts counter scan.

## Initial request

I accepted Sedgeglass Counter this morning, but the notice I just received says DL-016 is ready at Copperfin Locker, compartment 12. Which location actually has my parcel?

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Keep both records and ask Locker routing by email which location holds DL-016, citing the counter's 15:05 receipt scan and the Copperfin Locker notice, and tell Zerin only that it is being checked.

- **Recipient:** Locker routing, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** RECONCILE_CONFLICT (workflow sheet E)

## Outcome

Locker routing confirms one location with a current scan and a corrected notice; this settles readiness, not collection.

## Boundaries and remaining work

Must not: Do not send Zerin to Sedgeglass Counter on the strength of the scan alone, and do not tell Zerin to ignore the locker notice.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
