# Case 022-N4: A delivered household item is confirmed broken (Return logged versus returned-item inspection)

## Case details

- **Source role:** Replacement authorisations, Tallowmere Goods
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-23 09:00:00 UTC
- **Escalated:** 2026-02-23 09:48:00 UTC
- **Updated:** 2026-02-23 10:30:00 UTC
- **Completed:** 2026-02-23 10:30:00 UTC
- **Primary shipment:** DL-022
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 022, events 001–003 retained; branch CONFLICTING_RECORDS

## Context

Tallowmere Goods has accepted damage on TG-022, a ceramic table lamp with a separated base, for replacement assessment, but no replacement approval is recorded. Remi Dask prefers the same lamp to a refund and asks for the merchant to approve a replacement. This branch diverges after event 003: Return logged versus returned-item inspection.

## Initial request

We cannot approve TG-022 yet. A replacement needs the broken lamp back first, and no return is logged against TG-022 in our system. Please ask the customer to send it back.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Email Replacement authorisations and Damage assessor, Tallowmere Goods, quoting both records, and ask the damage assessor to confirm whether the lamp was returned and inspected under TG-022.

- **Recipient:** Damage assessor, Tallowmere Goods; Replacement authorisations, Tallowmere Goods
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** RECONCILE_CONFLICT (workflow sheet E)

## Outcome

The merchant states one return status for TG-022 with its source; that settles the record, not the replacement approval.

## Boundaries and remaining work

Must not: Do not ask Remi to send the lamp back, and do not decide which merchant record is correct.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
