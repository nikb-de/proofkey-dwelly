# Case 031-N2: Return approved but the customer has no return label (Approval re-saved with two return methods)

## Case details

- **Source role:** Return label team, Tallowmere Goods
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-04 09:00:00 UTC
- **Escalated:** 2026-03-04 09:48:00 UTC
- **Updated:** 2026-03-04 10:45:00 UTC
- **Completed:** 2026-03-04 10:45:00 UTC
- **Primary shipment:** DL-031
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 031, events 001–003 retained; branch STALE_STATE

## Context

Tallowmere Goods approved return RT-031 for TG-031 / DL-031, but the label field is empty and only its authorised label team can issue the label. Kessa Ulm asks the desk to obtain the printable return label. This branch diverges after event 003: Approval re-saved with two return methods.

## Initial request

Returns support re-saved RT-031 at 09:35. The label type now depends on the return method, and the record offers two: drop-off at a staffed counter, or doorstep collection booked separately. We generate one label for the method the customer chooses. Nothing has been issued yet.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask Kessa in the Customer portal one question: staffed counter drop-off or doorstep collection for RT-031, noting that collection would still need its own booking.

- **Recipient:** Kessa Ulm, customer
- **Channel:** Customer portal
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** ASK_CUSTOMER (workflow sheet B)

## Outcome

Kessa's choice is recorded and the label team issues one label for that method; a collection label is not a booked collection, and neither proves the parcel has left Kessa.

## Boundaries and remaining work

Must not: Do not pick a method for Kessa or ask for both labels; the original request did not cover a method choice.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
