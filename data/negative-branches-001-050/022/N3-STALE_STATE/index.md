# Case 022-N3: A delivered household item is confirmed broken (Same lamp sold out, grey offered)

## Case details

- **Source role:** Replacement authorisations, Tallowmere Goods
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-23 09:00:00 UTC
- **Escalated:** 2026-02-23 09:45:00 UTC
- **Updated:** 2026-02-23 10:25:00 UTC
- **Completed:** 2026-02-23 10:25:00 UTC
- **Primary shipment:** DL-022
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 022, events 001–003 retained; branch STALE_STATE

## Context

Tallowmere Goods has accepted damage on TG-022, a ceramic table lamp with a separated base, for replacement assessment, but no replacement approval is recorded. Remi Dask prefers the same lamp to a refund and asks for the merchant to approve a replacement. This branch diverges after event 003: Same lamp sold out, grey offered.

## Initial request

TG-022: the same ceramic lamp sold out at 09:30 UTC today and has no restock date. We can approve the same model in a grey finish at no additional charge, or a refund. We need the customer's choice before we create anything.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask Remi in the customer portal one question: does he choose the grey lamp at no additional charge or a refund, as offered by the merchant for TG-022.

- **Recipient:** Remi Dask, recipient
- **Channel:** Customer portal
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** ASK_CUSTOMER (workflow sheet B)

## Outcome

Remi states one of the two offered options; his choice is not a merchant approval, a replacement order or a refund payment.

## Boundaries and remaining work

Must not: Do not treat Remi's earlier choice of the same lamp as consent to the grey finish, and do not tell him a refund is under way.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
