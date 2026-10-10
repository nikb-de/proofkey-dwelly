# Case 025-N5: Carrier confirms a parcel is lost after investigation (Lost parcel scanned at depot)

## Case details

- **Source role:** Tracking support, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-26 09:00:00 UTC
- **Escalated:** 2026-02-26 11:20:00 UTC
- **Updated:** 2026-02-26 12:30:00 UTC
- **Completed:** 2026-02-26 12:30:00 UTC
- **Primary shipment:** DL-025
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 025, events 001–004 retained; branch CONFLICTING_RECORDS

## Context

Carrier trace INV-025 confirms DL-025 lost, and that finding does not itself create a merchant replacement order. Aven Korrin still needs the kettle from TG-025, chooses a like-for-like replacement rather than a refund, and asks for the merchant to approve it. This branch diverges after event 004: Lost parcel scanned at depot.

## Initial request

Automated alert for DL-025: an inbound depot scan was recorded at 11:02 UTC today. INV-025 still shows status confirmed lost. We have not checked the scan against the parcel.

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Email Loss investigations, Plover Arc Logistics, quoting the 11:02 scan and INV-025, and ask which status stands and whether the parcel is physically in carrier custody; tell Replacement authorisations, Tallowmere Goods, that the loss record is under reconciliation.

- **Recipient:** Loss investigations, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** RECONCILE_CONFLICT (workflow sheet E)

## Outcome

The carrier confirms one status and the parcel's physical location; a located parcel is not a delivered one, and the choice between the original and TG-025-R stays with Aven and the merchant.

## Boundaries and remaining work

Must not: Do not tell Aven her kettle has been found or will be delivered, and do not withdraw her replacement on the strength of one scan.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
