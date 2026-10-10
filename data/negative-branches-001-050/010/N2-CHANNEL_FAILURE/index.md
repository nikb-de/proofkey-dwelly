# Case 010-N2: Recipient wants delivery held during a short absence (Hold request transfer timed out)

## Case details

- **Source role:** Dispatch auto-acknowledgement, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-11 09:00:00 UTC
- **Escalated:** 2026-02-11 09:27:00 UTC
- **Updated:** 2026-02-11 10:05:00 UTC
- **Completed:** 2026-02-11 10:05:00 UTC
- **Primary shipment:** DL-010
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 010, events 001–003 retained; branch CHANNEL_FAILURE

## Context

DL-010 is in depot stock, and the service allows a hold of up to three calendar days before routing with a confirmed release date. Daro Lusk is away until 2026-02-14 and asks for the parcel to be held and released on that date, not earlier. This branch diverges after event 003: Hold request transfer timed out.

## Initial request

Automatic acknowledgement. Your email about DL-010 was received at 09:25. Its transfer to the depot hold queue failed with a timeout at 09:26. The stock record may or may not show a hold. No reference has been issued.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask Dispatch in Dispatch chat what DL-010's saved stock status and release date show now, and state that no second hold request will be sent until that is known.

- **Recipient:** Dispatch, Plover Arc Logistics
- **Channel:** Dispatch chat
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** VERIFY_FIRST (workflow sheet R)

## Outcome

Dispatch reports the saved status; if no hold exists, one request follows and is confirmed once, and a release date is not a delivery date.

## Boundaries and remaining work

Must not: Send the hold request again, or tell Daro the parcel is held.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
