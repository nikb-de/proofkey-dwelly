# Case 032-N1: Customer cannot print a return label (Token service errors during issue)

## Case details

- **Source role:** Printer-free returns team, Tallowmere Goods
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-05 09:00:00 UTC
- **Escalated:** 2026-03-05 09:33:00 UTC
- **Updated:** 2026-03-05 10:10:00 UTC
- **Completed:** 2026-03-05 10:10:00 UTC
- **Primary shipment:** DL-032
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 032, events 001–003 retained; branch CHANNEL_FAILURE

## Context

Return RT-032 for TG-032 / DL-032 is approved, and Tallowmere Goods offers a printer-free QR token, issued only by its returns team, for presentation at Copperfin Returns Counter, 10:00–18:00 UTC. Oska Vey has no printer and asks for the QR option and the accepting counter. This branch diverges after event 003: Token service errors during issue.

## Initial request

System notice. Token issue for RT-032 stopped at 09:32 with error QR-503. The notice cannot show whether a token was saved against the return. No token or counter details are attached.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Email the Printer-free returns team and ask what the RT-032 record now shows for a saved token, stating that no second token request will be sent until that is known.

- **Recipient:** Printer-free returns team, Tallowmere Goods
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** VERIFY_FIRST (workflow sheet R)

## Outcome

The team reports one saved token, or none and then one reissue confirmed once; a token in hand is still not drop-off or refund.

## Boundaries and remaining work

Must not: Do not resend the request or tell Oska a token is on its way; two live tokens for one return become a reconciliation problem at the counter.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
