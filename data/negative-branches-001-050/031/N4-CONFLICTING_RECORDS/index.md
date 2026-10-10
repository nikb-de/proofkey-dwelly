# Case 031-N4: Return approved but the customer has no return label (Issued label carries mismatched references)

## Case details

- **Source role:** Kessa Ulm, customer
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-04 09:00:00 UTC
- **Escalated:** 2026-03-04 10:02:00 UTC
- **Updated:** 2026-03-04 10:50:00 UTC
- **Completed:** 2026-03-04 10:50:00 UTC
- **Primary shipment:** DL-031
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 031, events 001–004 retained; branch CONFLICTING_RECORDS

## Context

Tallowmere Goods approved return RT-031 for TG-031 / DL-031, but the label field is empty and only its authorised label team can issue the label. Kessa Ulm asks the desk to obtain the printable return label. This branch diverges after event 004: Issued label carries mismatched references.

## Initial request

I opened RL-031. It shows RT-031, but the order line reads TG-013 and the original shipment reads DL-013. My order is TG-031. Is this the right label, or should I print it anyway?

## Overview

The escalation snapshot comprises history events 001–005. Event 006 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Email the Return label team in the verified returns thread with both readings, RL-031 showing TG-013 / DL-013 against approved RT-031 for TG-031 / DL-031, ask it to verify the label against the return record, and tell Kessa to hold the label until then.

- **Recipient:** Return label team, Tallowmere Goods
- **Channel:** Email
- **Recorded action:** [History event 006](history.md#event-006)
- **Expected decision:** RECONCILE_CONFLICT (workflow sheet E)

## Outcome

The label team states whether RL-031 is correct or replaced, with references that match RT-031; this still does not prove drop-off, merchant receipt or refund.

## Boundaries and remaining work

Must not: Do not tell Kessa to use RL-031 because RT-031 matches, and do not order a replacement label before the label team has checked which record is right.

## History

[Read the complete dated history](history.md).

## Attachments

- [return-label.pdf](attachments/return-label.pdf)
