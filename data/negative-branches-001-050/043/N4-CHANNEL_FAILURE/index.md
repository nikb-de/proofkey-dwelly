# Case 043-N4: Freight collection needs confirmed pallet dimensions and weight (Booking update errors, save unknown)

## Case details

- **Source role:** Freight portal, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-16 09:00:00 UTC
- **Escalated:** 2026-03-16 09:58:00 UTC
- **Updated:** 2026-03-16 10:35:00 UTC
- **Completed:** 2026-03-16 10:35:00 UTC
- **Primary shipment:** DL-043
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 043, events 001–004 retained; branch CHANNEL_FAILURE

## Context

The carrier cannot allocate a collection vehicle for DL-043 because the pallet's dimension and weight fields are blank. Nessa Dray at Orris Span says the pallet is ready and asks which measurements the carrier needs. This branch diverges after event 004: Booking update errors, save unknown.

## Initial request

Error on booking update DL-043 submitted 09:56 UTC: server error 500. Your changes to the dimension and weight fields may not have been saved. No confirmation number was issued.

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask the freight booking desk by email what the DL-043 dimension and weight fields now show, before submitting anything again.

- **Recipient:** Freight booking desk, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** VERIFY_FIRST (workflow sheet R)

## Outcome

The booking desk confirms which values are saved; saved values are not the planner's acceptance or a collection allocation.

## Boundaries and remaining work

Must not: Resubmit the update blind, risking a duplicate or part-saved booking, or tell Nessa the data has been accepted.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
