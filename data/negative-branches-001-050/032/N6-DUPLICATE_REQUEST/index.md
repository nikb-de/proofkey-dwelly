# Case 032-N6: Customer cannot print a return label (Second token request from customer call)

## Case details

- **Source role:** Printer-free returns team, Tallowmere Goods
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-05 09:00:00 UTC
- **Escalated:** 2026-03-05 09:45:00 UTC
- **Updated:** 2026-03-05 10:15:00 UTC
- **Completed:** 2026-03-05 10:15:00 UTC
- **Primary shipment:** DL-032
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 032, events 001–003 retained; branch DUPLICATE_REQUEST

## Context

Return RT-032 for TG-032 / DL-032 is approved, and Tallowmere Goods offers a printer-free QR token, issued only by its returns team, for presentation at Copperfin Returns Counter, 10:00–18:00 UTC. Oska Vey has no printer and asks for the QR option and the accepting counter. This branch diverges after event 003: Second token request from customer call.

## Initial request

We now hold two token requests for RT-032: yours from 09:25 and one the customer opened by phone with returns support at 09:38. Should we issue a token on each?

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Reply to the Printer-free returns team that both requests concern the same return RT-032, link the phone request to the 09:25 request, and ask for exactly one token.

- **Recipient:** Printer-free returns team, Tallowmere Goods
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** RESOLVE_DUPLICATE (workflow sheet F)

## Outcome

The team closes the duplicate and confirms one token for RT-032; a token is still not drop-off or refund.

## Boundaries and remaining work

Must not: Do not let both requests run; two tokens for one return invite a double scan or a rejected token at the counter.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
