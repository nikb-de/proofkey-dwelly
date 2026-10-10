# Case 022-N2: A delivered household item is confirmed broken (Warehouse offers dispatch without authorisation)

## Case details

- **Source role:** Warehouse dispatch, Tallowmere Goods
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-23 09:00:00 UTC
- **Escalated:** 2026-02-23 09:40:00 UTC
- **Updated:** 2026-02-23 10:20:00 UTC
- **Completed:** 2026-02-23 10:20:00 UTC
- **Primary shipment:** DL-022
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 022, events 001–003 retained; branch UNAUTHORISED_REPLY

## Context

Tallowmere Goods has accepted damage on TG-022, a ceramic table lamp with a separated base, for replacement assessment, but no replacement approval is recorded. Remi Dask prefers the same lamp to a refund and asks for the merchant to approve a replacement. This branch diverges after event 003: Warehouse offers dispatch without authorisation.

## Initial request

Saw your lamp request for TG-022. We have the same lamp on the shelf and can send it on the 11:00 van if you confirm the delivery address. No need to wait for Replacement authorisations.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Confirm nothing and share no address with Warehouse dispatch, tell Replacement authorisations, Tallowmere Goods, about the offer, and keep the approval request with them.

- **Recipient:** Replacement authorisations, Tallowmere Goods
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** SEPARATE_AUTHORITY (workflow sheet A)

## Outcome

Replacement authorisations confirms its own decision on TG-022; a warehouse offer is not an approval, and stock on a shelf is not a dispatch.

## Boundaries and remaining work

Must not: Do not confirm Remi's address or a dispatch on the warehouse's word, as that bypasses the party authorised to approve the replacement.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
