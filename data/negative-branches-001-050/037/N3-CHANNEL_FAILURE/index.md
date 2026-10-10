# Case 037-N3: Customer needs an eligible heavy item collected from inside the home (Crew booking request times out)

## Case details

- **Source role:** Specialist returns scheduler, Tallowmere Goods
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-10 09:00:00 UTC
- **Escalated:** 2026-03-10 09:34:00 UTC
- **Updated:** 2026-03-10 10:20:00 UTC
- **Completed:** 2026-03-10 10:20:00 UTC
- **Primary task reference:** RT-037
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 037, events 001–003 retained; branch CHANNEL_FAILURE

## Context

Approved return RT-037 covers a 54 kg cabinet with in-home collection by Tallowmere Goods' two-person specialist crew, on an access record of ground floor, level entrance and 110 cm doorway; ordinary parcel collection is not suitable. Lorin Esh confirms the access record, is home on 2026-03-11 and cannot move the cabinet. This branch diverges after event 003: Crew booking request times out.

## Initial request

Automated notice. Booking request for RT-037 timed out at 09:33. The crew calendar may hold a provisional entry for 2026-03-11. No booking reference was issued.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Email the Specialist returns scheduler and ask what the crew calendar shows for RT-037 on 2026-03-11, stating that no second booking will be requested until that is known.

- **Recipient:** Specialist returns scheduler, Tallowmere Goods
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** VERIFY_FIRST (workflow sheet R)

## Outcome

The scheduler confirms one crew booking, or none followed by one resubmission; a booking does not prove safe collection.

## Boundaries and remaining work

Must not: Do not resend the booking or arrange an ordinary courier as a fallback; event 001 rules parcel collection out for this item.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
