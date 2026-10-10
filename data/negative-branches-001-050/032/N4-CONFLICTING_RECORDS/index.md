# Case 032-N4: Customer cannot print a return label (Counter scanner rejects the issued token)

## Case details

- **Source role:** Oska Vey, customer
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-05 09:00:00 UTC
- **Escalated:** 2026-03-05 10:40:00 UTC
- **Updated:** 2026-03-05 11:20:00 UTC
- **Completed:** 2026-03-05 11:20:00 UTC
- **Primary shipment:** DL-032
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 032, events 001–004 retained; branch CONFLICTING_RECORDS

## Context

Return RT-032 for TG-032 / DL-032 is approved, and Tallowmere Goods offers a printer-free QR token, issued only by its returns team, for presentation at Copperfin Returns Counter, 10:00–18:00 UTC. Oska Vey has no printer and asks for the QR option and the accepting counter. This branch diverges after event 004: Counter scanner rejects the issued token.

## Initial request

I am at Copperfin Returns Counter now. Staff scanned DL032R and the screen says token not recognised. They say I can leave the parcel without a label and they will sort it out later. Should I?

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Tell Oska in the Customer portal to keep the parcel, and email the Printer-free returns team with both statements, token DL032R issued as valid and the counter's not recognised result, asking it to check the token's saved status.

- **Recipient:** Printer-free returns team, Tallowmere Goods
- **Channel:** Email
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** RECONCILE_CONFLICT (workflow sheet E)

## Outcome

The returns team reports the token's saved status and whether Copperfin can accept it; this still does not prove drop-off, carrier custody or refund.

## Boundaries and remaining work

Must not: Do not tell Oska to leave the parcel without a scanned token, printed label and receipt, and do not request a new token before the returns team has checked.

## History

[Read the complete dated history](history.md).

## Attachments

- [return-qr.png](attachments/return-qr.png)
