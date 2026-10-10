# Case 036-N2: Business sender needs collection of several labelled cartons (Booking save times out, manifest unknown)

## Case details

- **Source role:** Collection planner, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-09 09:00:00 UTC
- **Escalated:** 2026-03-09 09:36:00 UTC
- **Updated:** 2026-03-09 10:20:00 UTC
- **Completed:** 2026-03-09 10:20:00 UTC
- **Primary task reference:** OF-036
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 036, events 001–003 retained; branch CHANNEL_FAILURE

## Context

Orris Fold Studio has four labelled cartons on packing list OF-036, each 40 × 30 × 25 cm and 5 kg, 20 kg in total, ready at dispatch door S1 from 10:00 UTC on 2026-03-10. Fesk Rowan asks for confirmation that one vehicle takes all four, since a partial consignment cannot be released. This branch diverges after event 003: Booking save times out, manifest unknown.

## Initial request

System notice. Saving the OF-036 booking failed at 09:35 with a timeout. No booking or manifest number was returned. The collection plan may hold a partial entry.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Email the Collection planner and ask what the collection plan shows for OF-036, including any booking and which cartons sit on any manifest, stating that no second booking will be requested until that is known.

- **Recipient:** Collection planner, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** VERIFY_FIRST (workflow sheet R)

## Outcome

The planner confirms one booking with all four cartons on one manifest, or none and one resubmission confirmed once; this still does not prove pickup.

## Boundaries and remaining work

Must not: Do not resend the booking request; a second entry can produce two vehicles or a manifest that splits A to D.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
